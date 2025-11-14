import json
import requests
import os
from typing import List, Dict, Any, Optional

def debug_print(message: str):
    """Wyświetla wiadomość DEBUG tylko jeśli DEBUG_ENABLED=true w .env"""
    if os.getenv('DEBUG_ENABLED', 'false').lower() in ['true', '1', 'yes', 'on']:
        print(f"DEBUG: {message}")

class ZabbixAPI:
    def __init__(self):
        self.url = os.getenv('ZABBIX_URL')
        self.username = os.getenv('ZABBIX_USER')
        self.password = os.getenv('ZABBIX_PASSWORD')
        self.auth_token = None
        self.session = requests.Session()

        debug_print(f"Inicjalizacja ZabbixAPI:")
        debug_print(f"URL: {self.url}")
        debug_print(f"Username: {self.username}")
        debug_print(f"Password: {'*' * len(self.password) if self.password else 'None'}")
        debug_print(f"Auth token na starcie: {self.auth_token}")

    def authenticate(self) -> bool:
        """Autoryzacja w Zabbix API"""
        # Dla Zabbix 7.x - spróbuj różne formaty
        payload = {
            "jsonrpc": "2.0",
            "method": "user.login",
            "params": {
                "username": self.username,
                "password": self.password
            },
            "id": 1
        }

        try:
            debug_print(f"Wysyłam zapytanie logowania: {payload}")
            debug_print(f"URL: {self.url}")

            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'Zabbix Tag Manager'
            }

            response = self.session.post(self.url, json=payload, headers=headers)
            response.raise_for_status()
            result = response.json()
            debug_print(f"Odpowiedź logowania: {result}")

            if 'result' in result:
                self.auth_token = result['result']
                return True
            else:
                error_info = result.get('error', {})
                print(f"Błąd autoryzacji: {error_info.get('data', error_info.get('message', 'Nieznany błąd'))}")
                return False
        except requests.RequestException as e:
            print(f"Błąd połączenia: {e}")
            return False

    def make_request(self, method: str, params: Dict[str, Any]) -> Optional[Any]:
        """Wykonanie zapytania do Zabbix API"""
        debug_print(f"make_request() method={method}, auth_token={self.auth_token}")

        if method != "user.login" and not self.auth_token and not self.authenticate():
            return None

        # Dla Zabbix 7.x - autoryzacja przez nagłówek Authorization
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": 1
        }

        # Przygotuj nagłówki
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Zabbix Tag Manager'
        }

        # Dodaj token autoryzacji do nagłówka (nie do payload!)
        if method != "user.login" and self.auth_token:
            headers['Authorization'] = f'Bearer {self.auth_token}'
            debug_print(f"Dodano Authorization header dla metody {method}")

        debug_print(f"Payload dla {method}: {payload}")
        debug_print(f"Headers dla {method}: {headers}")

        try:
            response = self.session.post(self.url, json=payload, headers=headers)
            response.raise_for_status()
            result = response.json()

            if 'result' in result:
                return result['result']
            else:
                error = result.get('error', {})
                error_message = error.get('data', error.get('message', 'Nieznany błąd'))
                print(f"Błąd API: {error_message}")

                # Jeśli błąd autoryzacji, wyczyść token i spróbuj ponownie
                if 'authentication' in error_message.lower() or 'session' in error_message.lower():
                    self.auth_token = None
                    if method != "user.login":
                        return self.make_request(method, params)

                return None
        except requests.RequestException as e:
            print(f"Błąd połączenia: {e}")
            return None

    def get_hosts(self, limit: int = None, offset: int = None) -> List[Dict[str, Any]]:
        """Pobieranie listy hostów z tagami z opcjonalną paginacją"""
        params = {
            "output": ["hostid", "host", "name", "status"],
            "selectTags": "extend",
            "sortfield": "name"
        }

        # Dodaj paginację jeśli podano
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["sortorder"] = "ASC"  # Potrzebne dla stabilnej paginacji

        hosts = self.make_request("host.get", params)
        return hosts if hosts else []

    def get_hosts_count(self) -> int:
        """Pobieranie liczby hostów"""
        params = {
            "countOutput": True
        }

        count = self.make_request("host.get", params)
        return int(count) if count else 0

    def get_host_details(self, host_id: int) -> Dict[str, Any]:
        """Pobieranie szczegółów hosta z tagami"""
        params = {
            "output": ["hostid", "host", "name", "status"],
            "selectTags": "extend",
            "hostids": [host_id]
        }

        hosts = self.make_request("host.get", params)
        return hosts[0] if hosts else {}

    def add_tag_to_host(self, host_id: int, tag_name: str, tag_value: str = "") -> bool:
        """Dodawanie tagu do hosta"""
        debug_print(f" add_tag_to_host() - host_id={host_id}, tag_name={tag_name}, tag_value={tag_value}")

        host = self.get_host_details(host_id)
        if not host:
            debug_print(f" Nie znaleziono hosta o ID {host_id}")
            return False

        debug_print(f" Znaleziono hosta: {host.get('name', 'Unknown')}")
        current_tags = host.get('tags', [])
        debug_print(f" Obecne tagi hosta: {current_tags}")

        # Sprawdź czy tag już istnieje
        for tag in current_tags:
            if tag['tag'] == tag_name:
                debug_print(f" Tag '{tag_name}' już istnieje")
                return False

        # Dodaj nowy tag
        new_tag = {"tag": tag_name, "value": tag_value}
        current_tags.append(new_tag)
        debug_print(f" Nowe tagi po dodaniu: {current_tags}")

        # Usuń pole 'automatic' z tagów - Zabbix API nie akceptuje tego pola w host.update
        clean_tags = []
        for tag in current_tags:
            clean_tag = {"tag": tag["tag"], "value": tag["value"]}
            clean_tags.append(clean_tag)

        debug_print(f" Oczyszczone tagi (bez 'automatic'): {clean_tags}")

        params = {
            "hostid": host_id,
            "tags": clean_tags
        }

        debug_print(f" Wysyłam host.update z parametrami: {params}")
        result = self.make_request("host.update", params)
        debug_print(f" Wynik host.update: {result}")

        return result is not None

    def remove_tag_from_host(self, host_id: int, tag_name: str) -> bool:
        """Usuwanie tagu z hosta"""
        debug_print(f" remove_tag_from_host() - host_id={host_id}, tag_name={tag_name}")

        host = self.get_host_details(host_id)
        if not host:
            debug_print(f" Nie znaleziono hosta o ID {host_id}")
            return False

        current_tags = host.get('tags', [])
        debug_print(f" Obecne tagi hosta: {current_tags}")

        updated_tags = [tag for tag in current_tags if tag['tag'] != tag_name]
        debug_print(f" Tagi po usunięciu: {updated_tags}")

        if len(updated_tags) == len(current_tags):
            debug_print(f" Tag '{tag_name}' nie istnieje")
            return False

        # Usuń pole 'automatic' z tagów - Zabbix API nie akceptuje tego pola w host.update
        clean_tags = []
        for tag in updated_tags:
            clean_tag = {"tag": tag["tag"], "value": tag["value"]}
            clean_tags.append(clean_tag)

        debug_print(f" Oczyszczone tagi (bez 'automatic'): {clean_tags}")

        params = {
            "hostid": host_id,
            "tags": clean_tags
        }

        debug_print(f" Wysyłam host.update z parametrami: {params}")
        result = self.make_request("host.update", params)
        debug_print(f" Wynik host.update: {result}")

        return result is not None

    def bulk_add_tags(self, host_ids: List[int], tag_name: str, tag_value: str = "") -> int:
        """Masowe dodawanie tagów do hostów"""
        success_count = 0

        for host_id in host_ids:
            if self.add_tag_to_host(host_id, tag_name, tag_value):
                success_count += 1

        return success_count

    def bulk_remove_tags(self, host_ids: List[int], tag_name: str) -> int:
        """Masowe usuwanie tagów z hostów"""
        success_count = 0

        for host_id in host_ids:
            if self.remove_tag_from_host(host_id, tag_name):
                success_count += 1

        return success_count

    def get_all_tags(self) -> List[str]:
        """Pobieranie wszystkich używanych tagów w systemie"""
        hosts = self.get_hosts()
        tags = set()

        for host in hosts:
            for tag in host.get('tags', []):
                tags.add(tag['tag'])

        return sorted(list(tags))

    def search_hosts_by_tag(self, tag_name: str, tag_value: str = None) -> List[Dict[str, Any]]:
        """Wyszukiwanie hostów po tagu"""
        params = {
            "output": ["hostid", "host", "name", "status"],
            "selectTags": "extend",
            "tags": [{"tag": tag_name}]
        }

        if tag_value:
            params["tags"][0]["value"] = tag_value

        hosts = self.make_request("host.get", params)
        return hosts if hosts else []

    # ===============================
    # METODY DLA TRIGGERÓW
    # ===============================

    def get_triggers(self, limit: int = None, offset: int = None) -> List[Dict[str, Any]]:
        """Pobieranie listy triggerów z tagami z opcjonalną paginacją"""
        params = {
            "output": ["triggerid", "description", "status", "priority", "url", "expression"],
            "selectTags": "extend",
            "selectHosts": ["hostid", "name"],
            "sortfield": "description",
            "expandDescription": True
        }

        # Dodaj paginację jeśli podano
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["sortorder"] = "ASC"  # Potrzebne dla stabilnej paginacji

        triggers = self.make_request("trigger.get", params)
        return triggers if triggers else []

    def get_triggers_count(self) -> int:
        """Pobieranie liczby triggerów"""
        params = {
            "countOutput": True
        }

        count = self.make_request("trigger.get", params)
        return int(count) if count else 0

    def get_trigger_details(self, trigger_id: int) -> Dict[str, Any]:
        """Pobieranie szczegółów triggera z tagami"""
        params = {
            "output": ["triggerid", "description", "status", "priority", "url", "expression"],
            "selectTags": "extend",
            "selectHosts": ["hostid", "name"],
            "triggerids": [trigger_id],
            "expandDescription": True
        }

        triggers = self.make_request("trigger.get", params)
        return triggers[0] if triggers else {}

    def add_tag_to_trigger(self, trigger_id: int, tag_name: str, tag_value: str = "") -> bool:
        """Dodawanie tagu do triggera"""
        debug_print(f" add_tag_to_trigger() - trigger_id={trigger_id}, tag_name={tag_name}, tag_value={tag_value}")

        trigger = self.get_trigger_details(trigger_id)
        if not trigger:
            debug_print(f" Nie znaleziono triggera o ID {trigger_id}")
            return False

        debug_print(f" Znaleziono trigger: {trigger.get('description', 'Unknown')}")
        current_tags = trigger.get('tags', [])
        debug_print(f" Obecne tagi triggera: {current_tags}")

        # Sprawdź czy tag już istnieje
        for tag in current_tags:
            if tag['tag'] == tag_name:
                debug_print(f" Tag '{tag_name}' już istnieje")
                return False

        # Dodaj nowy tag
        new_tag = {"tag": tag_name, "value": tag_value}
        current_tags.append(new_tag)
        debug_print(f" Nowe tagi po dodaniu: {current_tags}")

        # Usuń pole 'automatic' z tagów - Zabbix API nie akceptuje tego pola w trigger.update
        clean_tags = []
        for tag in current_tags:
            clean_tag = {"tag": tag["tag"], "value": tag["value"]}
            clean_tags.append(clean_tag)

        debug_print(f" Oczyszczone tagi (bez 'automatic'): {clean_tags}")

        params = {
            "triggerid": trigger_id,
            "tags": clean_tags
        }

        debug_print(f" Wysyłam trigger.update z parametrami: {params}")
        result = self.make_request("trigger.update", params)
        debug_print(f" Wynik trigger.update: {result}")

        return result is not None

    def remove_tag_from_trigger(self, trigger_id: int, tag_name: str) -> bool:
        """Usuwanie tagu z triggera"""
        debug_print(f" remove_tag_from_trigger() - trigger_id={trigger_id}, tag_name={tag_name}")

        trigger = self.get_trigger_details(trigger_id)
        if not trigger:
            debug_print(f" Nie znaleziono triggera o ID {trigger_id}")
            return False

        current_tags = trigger.get('tags', [])
        debug_print(f" Obecne tagi triggera: {current_tags}")

        updated_tags = [tag for tag in current_tags if tag['tag'] != tag_name]
        debug_print(f" Tagi po usunięciu: {updated_tags}")

        if len(updated_tags) == len(current_tags):
            debug_print(f" Tag '{tag_name}' nie istnieje")
            return False

        # Usuń pole 'automatic' z tagów
        clean_tags = []
        for tag in updated_tags:
            clean_tag = {"tag": tag["tag"], "value": tag["value"]}
            clean_tags.append(clean_tag)

        debug_print(f" Oczyszczone tagi (bez 'automatic'): {clean_tags}")

        params = {
            "triggerid": trigger_id,
            "tags": clean_tags
        }

        debug_print(f" Wysyłam trigger.update z parametrami: {params}")
        result = self.make_request("trigger.update", params)
        debug_print(f" Wynik trigger.update: {result}")

        return result is not None

    def bulk_add_tags_to_triggers(self, trigger_ids: List[int], tag_name: str, tag_value: str = "") -> int:
        """Masowe dodawanie tagów do triggerów"""
        success_count = 0

        for trigger_id in trigger_ids:
            if self.add_tag_to_trigger(trigger_id, tag_name, tag_value):
                success_count += 1

        return success_count

    def bulk_remove_tags_from_triggers(self, trigger_ids: List[int], tag_name: str) -> int:
        """Masowe usuwanie tagów z triggerów"""
        success_count = 0

        for trigger_id in trigger_ids:
            if self.remove_tag_from_trigger(trigger_id, tag_name):
                success_count += 1

        return success_count

    def search_triggers_by_tag(self, tag_name: str, tag_value: str = None) -> List[Dict[str, Any]]:
        """Wyszukiwanie triggerów po tagu"""
        params = {
            "output": ["triggerid", "description", "status", "priority"],
            "selectTags": "extend",
            "selectHosts": ["hostid", "name"],
            "tags": [{"tag": tag_name}],
            "expandDescription": True
        }

        if tag_value:
            params["tags"][0]["value"] = tag_value

        triggers = self.make_request("trigger.get", params)
        return triggers if triggers else []