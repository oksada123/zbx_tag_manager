import json
import requests
import os
from typing import List, Dict, Any, Optional

def debug_print(message: str):
    """Displays DEBUG message only if DEBUG_ENABLED=true in .env"""
    if os.getenv('DEBUG_ENABLED', 'false').lower() in ['true', '1', 'yes', 'on']:
        print(f"DEBUG: {message}")

def validate_tag_input(tag_name: str, tag_value: str = "") -> bool:
    """Validate tag name and value"""
    if not tag_name or not isinstance(tag_name, str):
        return False
    if tag_name.strip() == "":
        return False
    if len(tag_name) > 255:  # Zabbix limit
        return False
    if tag_value and len(tag_value) > 255:  # Zabbix limit
        return False
    return True

# Maximum number of items for bulk operations
MAX_BULK_SIZE = int(os.getenv('MAX_BULK_SIZE', '1000'))

# Object type configurations for generic methods
OBJECT_CONFIGS = {
    'host': {
        'id_field': 'hostid',
        'api_get': 'host.get',
        'api_update': 'host.update',
        'name_field': 'name'
    },
    'trigger': {
        'id_field': 'triggerid',
        'api_get': 'trigger.get',
        'api_update': 'trigger.update',
        'name_field': 'description'
    },
    'item': {
        'id_field': 'itemid',
        'api_get': 'item.get',
        'api_update': 'item.update',
        'name_field': 'name'
    }
}

class ZabbixAPI:
    def __init__(self):
        self.url = os.getenv('ZABBIX_URL')
        self.api_token = os.getenv('ZABBIX_API_TOKEN')
        self.username = os.getenv('ZABBIX_USER')
        self.password = os.getenv('ZABBIX_PASSWORD')
        self.auth_token = None
        self.session = requests.Session()

        debug_print(f"Initializing ZabbixAPI:")
        debug_print(f"URL: {self.url}")
        debug_print(f"API Token: {'*' * 8 + self.api_token[-8:] if self.api_token and len(self.api_token) > 8 else ('Set' if self.api_token else 'None')}")
        debug_print(f"Username: {self.username}")
        debug_print(f"Password: {'*' * len(self.password) if self.password else 'None'}")
        debug_print(f"Auth token at start: {self.auth_token}")

    def authenticate(self) -> bool:
        """Authentication in Zabbix API"""
        # Priority 1: Use API token if available (no need to call user.login)
        if self.api_token:
            debug_print(f"Using API token for authentication (skipping user.login)")
            self.auth_token = self.api_token
            return True

        # Priority 2: Fall back to username/password authentication
        if not self.username or not self.password:
            print("Authentication error: No API token or username/password configured")
            return False

        # For Zabbix 7.x - try different formats
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
            debug_print(f"Sending login request: {payload}")
            debug_print(f"URL: {self.url}")

            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'Zabbix Tag Manager'
            }

            response = self.session.post(self.url, json=payload, headers=headers)
            response.raise_for_status()
            result = response.json()
            debug_print(f"Login response: {result}")

            if 'result' in result:
                self.auth_token = result['result']
                return True
            else:
                error_info = result.get('error', {})
                print(f"Authorization error: {error_info.get('data', error_info.get('message', 'Unknown error'))}")
                return False
        except requests.RequestException as e:
            print(f"Connection error: {e}")
            return False

    def make_request(self, method: str, params: Dict[str, Any], retry_count: int = 0) -> Optional[Any]:
        """Execute request to Zabbix API"""
        debug_print(f"make_request() method={method}, auth_token={self.auth_token}")

        if method != "user.login" and not self.auth_token and not self.authenticate():
            return None

        # For Zabbix 7.x - authorization via Authorization header
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": 1
        }

        # Prepare headers
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Zabbix Tag Manager'
        }

        # Add authorization token to header (not to payload!)
        if method != "user.login" and self.auth_token:
            headers['Authorization'] = f'Bearer {self.auth_token}'
            debug_print(f"Added Authorization header for method {method}")

        debug_print(f"Payload for {method}: {payload}")
        debug_print(f"Headers for {method}: {headers}")

        try:
            response = self.session.post(self.url, json=payload, headers=headers)
            response.raise_for_status()
            result = response.json()

            if 'result' in result:
                return result['result']
            else:
                error = result.get('error', {})
                error_message = error.get('data', error.get('message', 'Unknown error'))
                print(f"API error: {error_message}")

                # If authentication error, clear token and try again (max 1 retry)
                # But only retry if using username/password auth (not API token)
                if retry_count < 1 and ('authentication' in error_message.lower() or 'session' in error_message.lower()):
                    if self.api_token:
                        # API token is invalid or expired - cannot retry
                        print("API token authentication failed. Please check if the token is valid and not expired.")
                    else:
                        self.auth_token = None
                        if method != "user.login":
                            return self.make_request(method, params, retry_count + 1)

                return None
        except requests.RequestException as e:
            print(f"Connection error: {e}")
            return None

    def get_hosts(self, limit: int = None, offset: int = None) -> List[Dict[str, Any]]:
        """Fetch list of hosts with tags with optional pagination"""
        params = {
            "output": ["hostid", "host", "name", "status", "flags"],
            "selectTags": "extend",
            "sortfield": "name",
            "sortorder": "ASC"  # Required for stable pagination
        }

        # Add pagination if provided
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset

        hosts = self.make_request("host.get", params)
        return hosts if hosts else []

    def get_hosts_count(self) -> int:
        """Fetch number of hosts"""
        params = {
            "countOutput": True
        }

        count = self.make_request("host.get", params)
        return int(count) if count else 0

    def get_host_details(self, host_id: int) -> Dict[str, Any]:
        """Fetch host details with tags"""
        params = {
            "output": ["hostid", "host", "name", "status"],
            "selectTags": "extend",
            "hostids": [host_id]
        }

        hosts = self.make_request("host.get", params)
        return hosts[0] if hosts else {}

    # ===============================
    # GENERIC TAG OPERATIONS
    # ===============================

    def _add_tag_to_object(self, object_type: str, object_id: int, tag_name: str, tag_value: str = "") -> bool:
        """Generic method to add tag to any object (host/trigger/item)"""
        config = OBJECT_CONFIGS.get(object_type)
        if not config:
            debug_print(f" Unknown object type: {object_type}")
            return False

        debug_print(f" _add_tag_to_object() - {object_type}_id={object_id}, tag_name={tag_name}, tag_value={tag_value}")

        if not validate_tag_input(tag_name, tag_value):
            debug_print(f" Invalid tag input: tag_name='{tag_name}', tag_value='{tag_value}'")
            return False

        if not isinstance(object_id, int) or object_id <= 0:
            debug_print(f" Invalid {object_type}_id: {object_id}")
            return False

        # Get object details
        if object_type == 'host':
            obj = self.get_host_details(object_id)
        elif object_type == 'trigger':
            obj = self.get_trigger_details(object_id)
        elif object_type == 'item':
            obj = self.get_item_details(object_id)
        else:
            return False

        if not obj:
            debug_print(f" {object_type.capitalize()} with ID {object_id} not found")
            return False

        debug_print(f" Found {object_type}: {obj.get(config['name_field'], 'Unknown')}")
        current_tags = obj.get('tags', [])
        debug_print(f" Current {object_type} tags: {current_tags}")

        # Check if tag already exists
        for tag in current_tags:
            if tag['tag'] == tag_name:
                debug_print(f" Tag '{tag_name}' already exists - treating as success")
                return True  # Tag is already present, goal achieved

        # Add new tag
        new_tag = {"tag": tag_name, "value": tag_value}
        current_tags.append(new_tag)
        debug_print(f" New tags after adding: {current_tags}")

        # Remove 'automatic' field from tags
        clean_tags = [{"tag": tag["tag"], "value": tag["value"]} for tag in current_tags]
        debug_print(f" Cleaned tags (without 'automatic'): {clean_tags}")

        params = {
            config['id_field']: object_id,
            "tags": clean_tags
        }

        debug_print(f" Sending {config['api_update']} with parameters: {params}")
        result = self.make_request(config['api_update'], params)
        debug_print(f" Result of {config['api_update']}: {result}")

        return result is not None

    def _remove_tag_from_object(self, object_type: str, object_id: int, tag_name: str) -> bool:
        """Generic method to remove tag from any object (host/trigger/item)"""
        config = OBJECT_CONFIGS.get(object_type)
        if not config:
            debug_print(f" Unknown object type: {object_type}")
            return False

        debug_print(f" _remove_tag_from_object() - {object_type}_id={object_id}, tag_name={tag_name}")

        if not tag_name or not isinstance(tag_name, str) or tag_name.strip() == "":
            debug_print(f" Invalid tag_name: '{tag_name}'")
            return False

        if not isinstance(object_id, int) or object_id <= 0:
            debug_print(f" Invalid {object_type}_id: {object_id}")
            return False

        # Get object details
        if object_type == 'host':
            obj = self.get_host_details(object_id)
        elif object_type == 'trigger':
            obj = self.get_trigger_details(object_id)
        elif object_type == 'item':
            obj = self.get_item_details(object_id)
        else:
            return False

        if not obj:
            debug_print(f" {object_type.capitalize()} with ID {object_id} not found")
            return False

        current_tags = obj.get('tags', [])
        debug_print(f" Current {object_type} tags: {current_tags}")

        updated_tags = [tag for tag in current_tags if tag['tag'] != tag_name]
        debug_print(f" Tags after removal: {updated_tags}")

        if len(updated_tags) == len(current_tags):
            debug_print(f" Tag '{tag_name}' does not exist - treating as success")
            return True  # Tag is already absent, goal achieved

        # Remove 'automatic' field from tags
        clean_tags = [{"tag": tag["tag"], "value": tag["value"]} for tag in updated_tags]
        debug_print(f" Cleaned tags (without 'automatic'): {clean_tags}")

        params = {
            config['id_field']: object_id,
            "tags": clean_tags
        }

        debug_print(f" Sending {config['api_update']} with parameters: {params}")
        result = self.make_request(config['api_update'], params)
        debug_print(f" Result of {config['api_update']}: {result}")

        return result is not None

    def _bulk_add_tags_to_objects(self, object_type: str, object_ids: List[int], tag_name: str, tag_value: str = "") -> int:
        """Generic bulk add tags"""
        if not object_ids or len(object_ids) == 0:
            return 0

        if len(object_ids) > MAX_BULK_SIZE:
            debug_print(f" Bulk operation limited to {MAX_BULK_SIZE} {object_type}s (requested: {len(object_ids)})")
            object_ids = object_ids[:MAX_BULK_SIZE]

        success_count = 0
        for obj_id in object_ids:
            if self._add_tag_to_object(object_type, obj_id, tag_name, tag_value):
                success_count += 1

        return success_count

    def _bulk_add_tags_to_objects_detailed(self, object_type: str, object_ids: List[int], tag_name: str, tag_value: str = "") -> dict:
        """Generic bulk add tags with detailed reporting"""
        if not object_ids or len(object_ids) == 0:
            return {'success': 0, 'failed': 0, 'errors': []}

        if len(object_ids) > MAX_BULK_SIZE:
            debug_print(f" Bulk operation limited to {MAX_BULK_SIZE} {object_type}s (requested: {len(object_ids)})")
            object_ids = object_ids[:MAX_BULK_SIZE]

        success_count = 0
        failed_count = 0
        errors = []

        for obj_id in object_ids:
            if self._add_tag_to_object(object_type, obj_id, tag_name, tag_value):
                success_count += 1
            else:
                failed_count += 1
                errors.append(obj_id)

        return {'success': success_count, 'failed': failed_count, 'errors': errors}

    def _bulk_remove_tags_from_objects(self, object_type: str, object_ids: List[int], tag_name: str) -> int:
        """Generic bulk remove tags"""
        if not object_ids or len(object_ids) == 0:
            return 0

        if len(object_ids) > MAX_BULK_SIZE:
            debug_print(f" Bulk operation limited to {MAX_BULK_SIZE} {object_type}s (requested: {len(object_ids)})")
            object_ids = object_ids[:MAX_BULK_SIZE]

        success_count = 0
        for obj_id in object_ids:
            if self._remove_tag_from_object(object_type, obj_id, tag_name):
                success_count += 1

        return success_count

    def _bulk_remove_tags_from_objects_detailed(self, object_type: str, object_ids: List[int], tag_name: str) -> dict:
        """Generic bulk remove tags with detailed reporting"""
        if not object_ids or len(object_ids) == 0:
            return {'success': 0, 'failed': 0, 'errors': []}

        if len(object_ids) > MAX_BULK_SIZE:
            debug_print(f" Bulk operation limited to {MAX_BULK_SIZE} {object_type}s (requested: {len(object_ids)})")
            object_ids = object_ids[:MAX_BULK_SIZE]

        success_count = 0
        failed_count = 0
        errors = []

        for obj_id in object_ids:
            if self._remove_tag_from_object(object_type, obj_id, tag_name):
                success_count += 1
            else:
                failed_count += 1
                errors.append(obj_id)

        return {'success': success_count, 'failed': failed_count, 'errors': errors}

    # ===============================
    # HOST TAG OPERATIONS (wrappers)
    # ===============================

    def add_tag_to_host(self, host_id: int, tag_name: str, tag_value: str = "") -> bool:
        """Add tag to host"""
        return self._add_tag_to_object('host', host_id, tag_name, tag_value)

    def remove_tag_from_host(self, host_id: int, tag_name: str) -> bool:
        """Remove tag from host"""
        return self._remove_tag_from_object('host', host_id, tag_name)

    def bulk_add_tags(self, host_ids: List[int], tag_name: str, tag_value: str = "") -> int:
        """Bulk add tags to hosts"""
        return self._bulk_add_tags_to_objects('host', host_ids, tag_name, tag_value)

    def bulk_add_tags_detailed(self, host_ids: List[int], tag_name: str, tag_value: str = "") -> dict:
        """Bulk add tags to hosts with detailed error reporting"""
        return self._bulk_add_tags_to_objects_detailed('host', host_ids, tag_name, tag_value)

    def bulk_remove_tags(self, host_ids: List[int], tag_name: str) -> int:
        """Bulk remove tags from hosts"""
        return self._bulk_remove_tags_from_objects('host', host_ids, tag_name)

    def bulk_remove_tags_detailed(self, host_ids: List[int], tag_name: str) -> dict:
        """Bulk remove tags from hosts with detailed error reporting"""
        return self._bulk_remove_tags_from_objects_detailed('host', host_ids, tag_name)

    def get_all_tags(self) -> List[str]:
        """Fetch all used tags in the system"""
        hosts = self.get_hosts()
        tags = set()

        for host in hosts:
            for tag in host.get('tags', []):
                tags.add(tag['tag'])

        return sorted(list(tags))

    def search_hosts_by_tag(self, tag_name: str, tag_value: str = None) -> List[Dict[str, Any]]:
        """Search hosts by tag"""
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
    # METHODS FOR TRIGGERS
    # ===============================

    def get_triggers(self, limit: int = None, offset: int = None) -> List[Dict[str, Any]]:
        """Fetch list of triggers with tags with optional pagination"""
        params = {
            "output": ["triggerid", "description", "status", "priority", "url", "expression", "flags"],
            "selectTags": "extend",
            "selectHosts": ["hostid", "name"],
            "sortfield": "description",
            "sortorder": "ASC",  # Required for stable pagination
            "expandDescription": True
        }

        # Add pagination if provided
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset

        triggers = self.make_request("trigger.get", params)
        return triggers if triggers else []

    def get_triggers_count(self) -> int:
        """Fetch number of triggers"""
        params = {
            "countOutput": True
        }

        count = self.make_request("trigger.get", params)
        return int(count) if count else 0

    def get_trigger_details(self, trigger_id: int) -> Dict[str, Any]:
        """Fetch trigger details with tags"""
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
        """Add tag to trigger"""
        return self._add_tag_to_object('trigger', trigger_id, tag_name, tag_value)

    def remove_tag_from_trigger(self, trigger_id: int, tag_name: str) -> bool:
        """Remove tag from trigger"""
        return self._remove_tag_from_object('trigger', trigger_id, tag_name)

    def bulk_add_tags_to_triggers(self, trigger_ids: List[int], tag_name: str, tag_value: str = "") -> int:
        """Bulk add tags to triggers"""
        return self._bulk_add_tags_to_objects('trigger', trigger_ids, tag_name, tag_value)

    def bulk_add_tags_to_triggers_detailed(self, trigger_ids: List[int], tag_name: str, tag_value: str = "") -> dict:
        """Bulk add tags to triggers with detailed error reporting"""
        return self._bulk_add_tags_to_objects_detailed('trigger', trigger_ids, tag_name, tag_value)

    def bulk_remove_tags_from_triggers(self, trigger_ids: List[int], tag_name: str) -> int:
        """Bulk remove tags from triggers"""
        return self._bulk_remove_tags_from_objects('trigger', trigger_ids, tag_name)

    def bulk_remove_tags_from_triggers_detailed(self, trigger_ids: List[int], tag_name: str) -> dict:
        """Bulk remove tags from triggers with detailed error reporting"""
        return self._bulk_remove_tags_from_objects_detailed('trigger', trigger_ids, tag_name)

    def search_triggers_by_tag(self, tag_name: str, tag_value: str = None) -> List[Dict[str, Any]]:
        """Search triggers by tag"""
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

    # ===============================
    # METHODS FOR ITEMS
    # ===============================

    def get_items(self, limit: int = None, offset: int = None) -> List[Dict[str, Any]]:
        """Fetch list of items with tags with optional pagination"""
        params = {
            "output": ["itemid", "name", "key_", "type", "status", "value_type", "delay", "flags"],
            "selectTags": "extend",
            "selectHosts": ["hostid", "name"],
            "sortfield": "name",
            "sortorder": "ASC",  # Required for stable pagination
            "monitored": True
        }

        # Add pagination if provided
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset

        items = self.make_request("item.get", params)
        return items if items else []

    def get_items_count(self) -> int:
        """Fetch number of items"""
        params = {
            "countOutput": True,
            "monitored": True
        }

        count = self.make_request("item.get", params)
        return int(count) if count else 0

    def get_item_details(self, item_id: int) -> Dict[str, Any]:
        """Fetch item details with tags"""
        params = {
            "output": ["itemid", "name", "key_", "type", "status", "value_type", "delay", "units", "description"],
            "selectTags": "extend",
            "selectHosts": ["hostid", "name"],
            "itemids": [item_id]
        }

        items = self.make_request("item.get", params)
        return items[0] if items else {}

    def add_tag_to_item(self, item_id: int, tag_name: str, tag_value: str = "") -> bool:
        """Add tag to item"""
        return self._add_tag_to_object('item', item_id, tag_name, tag_value)

    def remove_tag_from_item(self, item_id: int, tag_name: str) -> bool:
        """Remove tag from item"""
        return self._remove_tag_from_object('item', item_id, tag_name)

    def bulk_add_tags_to_items(self, item_ids: List[int], tag_name: str, tag_value: str = "") -> int:
        """Bulk add tags to items"""
        return self._bulk_add_tags_to_objects('item', item_ids, tag_name, tag_value)

    def bulk_add_tags_to_items_detailed(self, item_ids: List[int], tag_name: str, tag_value: str = "") -> dict:
        """Bulk add tags to items with detailed error reporting"""
        return self._bulk_add_tags_to_objects_detailed('item', item_ids, tag_name, tag_value)

    def bulk_remove_tags_from_items(self, item_ids: List[int], tag_name: str) -> int:
        """Bulk remove tags from items"""
        return self._bulk_remove_tags_from_objects('item', item_ids, tag_name)

    def bulk_remove_tags_from_items_detailed(self, item_ids: List[int], tag_name: str) -> dict:
        """Bulk remove tags from items with detailed error reporting"""
        return self._bulk_remove_tags_from_objects_detailed('item', item_ids, tag_name)

    def search_items_by_tag(self, tag_name: str, tag_value: str = None) -> List[Dict[str, Any]]:
        """Search items by tag"""
        params = {
            "output": ["itemid", "name", "key_", "type", "status"],
            "selectTags": "extend",
            "selectHosts": ["hostid", "name"],
            "tags": [{"tag": tag_name}],
            "monitored": True
        }

        if tag_value:
            params["tags"][0]["value"] = tag_value

        items = self.make_request("item.get", params)
        return items if items else []