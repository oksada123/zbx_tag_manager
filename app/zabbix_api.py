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
MAX_BULK_SIZE = 1000

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

    def add_tag_to_host(self, host_id: int, tag_name: str, tag_value: str = "") -> bool:
        """Add tag to host"""
        debug_print(f" add_tag_to_host() - host_id={host_id}, tag_name={tag_name}, tag_value={tag_value}")

        # Validate input
        if not validate_tag_input(tag_name, tag_value):
            debug_print(f" Invalid tag input: tag_name='{tag_name}', tag_value='{tag_value}'")
            return False

        if not isinstance(host_id, int) or host_id <= 0:
            debug_print(f" Invalid host_id: {host_id}")
            return False

        host = self.get_host_details(host_id)
        if not host:
            debug_print(f" Host with ID {host_id} not found")
            return False

        debug_print(f" Found host: {host.get('name', 'Unknown')}")
        current_tags = host.get('tags', [])
        debug_print(f" Current host tags: {current_tags}")

        # Check if tag already exists
        for tag in current_tags:
            if tag['tag'] == tag_name:
                debug_print(f" Tag '{tag_name}' already exists")
                return False

        # Add new tag
        new_tag = {"tag": tag_name, "value": tag_value}
        current_tags.append(new_tag)
        debug_print(f" New tags after adding: {current_tags}")

        # Remove 'automatic' field from tags - Zabbix API doesn't accept this field in host.update
        clean_tags = []
        for tag in current_tags:
            clean_tag = {"tag": tag["tag"], "value": tag["value"]}
            clean_tags.append(clean_tag)

        debug_print(f" Cleaned tags (without 'automatic'): {clean_tags}")

        params = {
            "hostid": host_id,
            "tags": clean_tags
        }

        debug_print(f" Sending host.update with parameters: {params}")
        result = self.make_request("host.update", params)
        debug_print(f" Result of host.update: {result}")

        return result is not None

    def remove_tag_from_host(self, host_id: int, tag_name: str) -> bool:
        """Remove tag from host"""
        debug_print(f" remove_tag_from_host() - host_id={host_id}, tag_name={tag_name}")

        # Validate input
        if not tag_name or not isinstance(tag_name, str) or tag_name.strip() == "":
            debug_print(f" Invalid tag_name: '{tag_name}'")
            return False

        if not isinstance(host_id, int) or host_id <= 0:
            debug_print(f" Invalid host_id: {host_id}")
            return False

        host = self.get_host_details(host_id)
        if not host:
            debug_print(f" Host with ID {host_id} not found")
            return False

        current_tags = host.get('tags', [])
        debug_print(f" Current host tags: {current_tags}")

        updated_tags = [tag for tag in current_tags if tag['tag'] != tag_name]
        debug_print(f" Tags after removal: {updated_tags}")

        if len(updated_tags) == len(current_tags):
            debug_print(f" Tag '{tag_name}' does not exist")
            return False

        # Remove 'automatic' field from tags - Zabbix API doesn't accept this field in host.update
        clean_tags = []
        for tag in updated_tags:
            clean_tag = {"tag": tag["tag"], "value": tag["value"]}
            clean_tags.append(clean_tag)

        debug_print(f" Cleaned tags (without 'automatic'): {clean_tags}")

        params = {
            "hostid": host_id,
            "tags": clean_tags
        }

        debug_print(f" Sending host.update with parameters: {params}")
        result = self.make_request("host.update", params)
        debug_print(f" Result of host.update: {result}")

        return result is not None

    def bulk_add_tags(self, host_ids: List[int], tag_name: str, tag_value: str = "") -> int:
        """Bulk add tags to hosts"""
        if not host_ids or len(host_ids) == 0:
            return 0

        if len(host_ids) > MAX_BULK_SIZE:
            debug_print(f" Bulk operation limited to {MAX_BULK_SIZE} items (requested: {len(host_ids)})")
            host_ids = host_ids[:MAX_BULK_SIZE]

        success_count = 0

        for host_id in host_ids:
            if self.add_tag_to_host(host_id, tag_name, tag_value):
                success_count += 1

        return success_count

    def bulk_add_tags_detailed(self, host_ids: List[int], tag_name: str, tag_value: str = "") -> dict:
        """Bulk add tags to hosts with detailed error reporting"""
        if not host_ids or len(host_ids) == 0:
            return {'success': 0, 'failed': 0, 'errors': []}

        if len(host_ids) > MAX_BULK_SIZE:
            debug_print(f" Bulk operation limited to {MAX_BULK_SIZE} hosts (requested: {len(host_ids)})")
            host_ids = host_ids[:MAX_BULK_SIZE]

        success_count = 0
        failed_count = 0
        errors = []

        for host_id in host_ids:
            if self.add_tag_to_host(host_id, tag_name, tag_value):
                success_count += 1
            else:
                failed_count += 1
                errors.append(host_id)

        return {
            'success': success_count,
            'failed': failed_count,
            'errors': errors
        }

    def bulk_remove_tags(self, host_ids: List[int], tag_name: str) -> int:
        """Bulk remove tags from hosts"""
        if not host_ids or len(host_ids) == 0:
            return 0

        if len(host_ids) > MAX_BULK_SIZE:
            debug_print(f" Bulk operation limited to {MAX_BULK_SIZE} items (requested: {len(host_ids)})")
            host_ids = host_ids[:MAX_BULK_SIZE]

        success_count = 0

        for host_id in host_ids:
            if self.remove_tag_from_host(host_id, tag_name):
                success_count += 1

        return success_count

    def bulk_remove_tags_detailed(self, host_ids: List[int], tag_name: str) -> dict:
        """Bulk remove tags from hosts with detailed error reporting"""
        if not host_ids or len(host_ids) == 0:
            return {'success': 0, 'failed': 0, 'errors': []}

        if len(host_ids) > MAX_BULK_SIZE:
            debug_print(f" Bulk operation limited to {MAX_BULK_SIZE} hosts (requested: {len(host_ids)})")
            host_ids = host_ids[:MAX_BULK_SIZE]

        success_count = 0
        failed_count = 0
        errors = []

        for host_id in host_ids:
            if self.remove_tag_from_host(host_id, tag_name):
                success_count += 1
            else:
                failed_count += 1
                errors.append(host_id)

        return {
            'success': success_count,
            'failed': failed_count,
            'errors': errors
        }

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
        debug_print(f" add_tag_to_trigger() - trigger_id={trigger_id}, tag_name={tag_name}, tag_value={tag_value}")

        # Validate input
        if not validate_tag_input(tag_name, tag_value):
            debug_print(f" Invalid tag input: tag_name='{tag_name}', tag_value='{tag_value}'")
            return False

        if not isinstance(trigger_id, int) or trigger_id <= 0:
            debug_print(f" Invalid trigger_id: {trigger_id}")
            return False

        trigger = self.get_trigger_details(trigger_id)
        if not trigger:
            debug_print(f" Trigger with ID {trigger_id} not found")
            return False

        debug_print(f" Found trigger: {trigger.get('description', 'Unknown')}")
        current_tags = trigger.get('tags', [])
        debug_print(f" Current trigger tags: {current_tags}")

        # Check if tag already exists
        for tag in current_tags:
            if tag['tag'] == tag_name:
                debug_print(f" Tag '{tag_name}' already exists")
                return False

        # Add new tag
        new_tag = {"tag": tag_name, "value": tag_value}
        current_tags.append(new_tag)
        debug_print(f" New tags after adding: {current_tags}")

        # Remove 'automatic' field from tags - Zabbix API doesn't accept this field in trigger.update
        clean_tags = []
        for tag in current_tags:
            clean_tag = {"tag": tag["tag"], "value": tag["value"]}
            clean_tags.append(clean_tag)

        debug_print(f" Cleaned tags (without 'automatic'): {clean_tags}")

        params = {
            "triggerid": trigger_id,
            "tags": clean_tags
        }

        debug_print(f" Sending trigger.update with parameters: {params}")
        result = self.make_request("trigger.update", params)
        debug_print(f" Result of trigger.update: {result}")

        return result is not None

    def remove_tag_from_trigger(self, trigger_id: int, tag_name: str) -> bool:
        """Remove tag from trigger"""
        debug_print(f" remove_tag_from_trigger() - trigger_id={trigger_id}, tag_name={tag_name}")

        # Validate input
        if not tag_name or not isinstance(tag_name, str) or tag_name.strip() == "":
            debug_print(f" Invalid tag_name: '{tag_name}'")
            return False

        if not isinstance(trigger_id, int) or trigger_id <= 0:
            debug_print(f" Invalid trigger_id: {trigger_id}")
            return False

        trigger = self.get_trigger_details(trigger_id)
        if not trigger:
            debug_print(f" Trigger with ID {trigger_id} not found")
            return False

        current_tags = trigger.get('tags', [])
        debug_print(f" Current trigger tags: {current_tags}")

        updated_tags = [tag for tag in current_tags if tag['tag'] != tag_name]
        debug_print(f" Tags after removal: {updated_tags}")

        if len(updated_tags) == len(current_tags):
            debug_print(f" Tag '{tag_name}' does not exist")
            return False

        # Remove 'automatic' field from tags
        clean_tags = []
        for tag in updated_tags:
            clean_tag = {"tag": tag["tag"], "value": tag["value"]}
            clean_tags.append(clean_tag)

        debug_print(f" Cleaned tags (without 'automatic'): {clean_tags}")

        params = {
            "triggerid": trigger_id,
            "tags": clean_tags
        }

        debug_print(f" Sending trigger.update with parameters: {params}")
        result = self.make_request("trigger.update", params)
        debug_print(f" Result of trigger.update: {result}")

        return result is not None

    def bulk_add_tags_to_triggers(self, trigger_ids: List[int], tag_name: str, tag_value: str = "") -> int:
        """Bulk add tags to triggers"""
        if not trigger_ids or len(trigger_ids) == 0:
            return 0

        if len(trigger_ids) > MAX_BULK_SIZE:
            debug_print(f" Bulk operation limited to {MAX_BULK_SIZE} items (requested: {len(trigger_ids)})")
            trigger_ids = trigger_ids[:MAX_BULK_SIZE]

        success_count = 0

        for trigger_id in trigger_ids:
            if self.add_tag_to_trigger(trigger_id, tag_name, tag_value):
                success_count += 1

        return success_count

    def bulk_add_tags_to_triggers_detailed(self, trigger_ids: List[int], tag_name: str, tag_value: str = "") -> dict:
        """Bulk add tags to triggers with detailed error reporting"""
        if not trigger_ids or len(trigger_ids) == 0:
            return {'success': 0, 'failed': 0, 'errors': []}

        if len(trigger_ids) > MAX_BULK_SIZE:
            debug_print(f" Bulk operation limited to {MAX_BULK_SIZE} triggers (requested: {len(trigger_ids)})")
            trigger_ids = trigger_ids[:MAX_BULK_SIZE]

        success_count = 0
        failed_count = 0
        errors = []

        for trigger_id in trigger_ids:
            if self.add_tag_to_trigger(trigger_id, tag_name, tag_value):
                success_count += 1
            else:
                failed_count += 1
                errors.append(trigger_id)

        return {
            'success': success_count,
            'failed': failed_count,
            'errors': errors
        }

    def bulk_remove_tags_from_triggers(self, trigger_ids: List[int], tag_name: str) -> int:
        """Bulk remove tags from triggers"""
        if not trigger_ids or len(trigger_ids) == 0:
            return 0

        if len(trigger_ids) > MAX_BULK_SIZE:
            debug_print(f" Bulk operation limited to {MAX_BULK_SIZE} items (requested: {len(trigger_ids)})")
            trigger_ids = trigger_ids[:MAX_BULK_SIZE]

        success_count = 0

        for trigger_id in trigger_ids:
            if self.remove_tag_from_trigger(trigger_id, tag_name):
                success_count += 1

        return success_count

    def bulk_remove_tags_from_triggers_detailed(self, trigger_ids: List[int], tag_name: str) -> dict:
        """Bulk remove tags from triggers with detailed error reporting"""
        if not trigger_ids or len(trigger_ids) == 0:
            return {'success': 0, 'failed': 0, 'errors': []}

        if len(trigger_ids) > MAX_BULK_SIZE:
            debug_print(f" Bulk operation limited to {MAX_BULK_SIZE} triggers (requested: {len(trigger_ids)})")
            trigger_ids = trigger_ids[:MAX_BULK_SIZE]

        success_count = 0
        failed_count = 0
        errors = []

        for trigger_id in trigger_ids:
            if self.remove_tag_from_trigger(trigger_id, tag_name):
                success_count += 1
            else:
                failed_count += 1
                errors.append(trigger_id)

        return {
            'success': success_count,
            'failed': failed_count,
            'errors': errors
        }

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
        debug_print(f" add_tag_to_item() - item_id={item_id}, tag_name={tag_name}, tag_value={tag_value}")

        # Validate input
        if not validate_tag_input(tag_name, tag_value):
            debug_print(f" Invalid tag input: tag_name='{tag_name}', tag_value='{tag_value}'")
            return False

        if not isinstance(item_id, int) or item_id <= 0:
            debug_print(f" Invalid item_id: {item_id}")
            return False

        item = self.get_item_details(item_id)
        if not item:
            debug_print(f" Item with ID {item_id} not found")
            return False

        debug_print(f" Found item: {item.get('name', 'Unknown')}")
        current_tags = item.get('tags', [])
        debug_print(f" Current item tags: {current_tags}")

        # Check if tag already exists
        for tag in current_tags:
            if tag['tag'] == tag_name:
                debug_print(f" Tag '{tag_name}' already exists")
                return False

        # Add new tag
        new_tag = {"tag": tag_name, "value": tag_value}
        current_tags.append(new_tag)
        debug_print(f" New tags after adding: {current_tags}")

        # Remove 'automatic' field from tags - Zabbix API doesn't accept this field in item.update
        clean_tags = []
        for tag in current_tags:
            clean_tag = {"tag": tag["tag"], "value": tag["value"]}
            clean_tags.append(clean_tag)

        debug_print(f" Cleaned tags (without 'automatic'): {clean_tags}")

        params = {
            "itemid": item_id,
            "tags": clean_tags
        }

        debug_print(f" Sending item.update with parameters: {params}")
        result = self.make_request("item.update", params)
        debug_print(f" Result of item.update: {result}")

        return result is not None

    def remove_tag_from_item(self, item_id: int, tag_name: str) -> bool:
        """Remove tag from item"""
        debug_print(f" remove_tag_from_item() - item_id={item_id}, tag_name={tag_name}")

        # Validate input
        if not tag_name or not isinstance(tag_name, str) or tag_name.strip() == "":
            debug_print(f" Invalid tag_name: '{tag_name}'")
            return False

        if not isinstance(item_id, int) or item_id <= 0:
            debug_print(f" Invalid item_id: {item_id}")
            return False

        item = self.get_item_details(item_id)
        if not item:
            debug_print(f" Item with ID {item_id} not found")
            return False

        current_tags = item.get('tags', [])
        debug_print(f" Current item tags: {current_tags}")

        updated_tags = [tag for tag in current_tags if tag['tag'] != tag_name]
        debug_print(f" Tags after removal: {updated_tags}")

        if len(updated_tags) == len(current_tags):
            debug_print(f" Tag '{tag_name}' does not exist")
            return False

        # Remove 'automatic' field from tags
        clean_tags = []
        for tag in updated_tags:
            clean_tag = {"tag": tag["tag"], "value": tag["value"]}
            clean_tags.append(clean_tag)

        debug_print(f" Cleaned tags (without 'automatic'): {clean_tags}")

        params = {
            "itemid": item_id,
            "tags": clean_tags
        }

        debug_print(f" Sending item.update with parameters: {params}")
        result = self.make_request("item.update", params)
        debug_print(f" Result of item.update: {result}")

        return result is not None

    def bulk_add_tags_to_items(self, item_ids: List[int], tag_name: str, tag_value: str = "") -> int:
        """Bulk add tags to items"""
        if not item_ids or len(item_ids) == 0:
            return 0

        if len(item_ids) > MAX_BULK_SIZE:
            debug_print(f" Bulk operation limited to {MAX_BULK_SIZE} items (requested: {len(item_ids)})")
            item_ids = item_ids[:MAX_BULK_SIZE]

        success_count = 0

        for item_id in item_ids:
            if self.add_tag_to_item(item_id, tag_name, tag_value):
                success_count += 1

        return success_count

    def bulk_add_tags_to_items_detailed(self, item_ids: List[int], tag_name: str, tag_value: str = "") -> dict:
        """Bulk add tags to items with detailed error reporting"""
        if not item_ids or len(item_ids) == 0:
            return {'success': 0, 'failed': 0, 'errors': []}

        if len(item_ids) > MAX_BULK_SIZE:
            debug_print(f" Bulk operation limited to {MAX_BULK_SIZE} items (requested: {len(item_ids)})")
            item_ids = item_ids[:MAX_BULK_SIZE]

        success_count = 0
        failed_count = 0
        errors = []

        for item_id in item_ids:
            if self.add_tag_to_item(item_id, tag_name, tag_value):
                success_count += 1
            else:
                failed_count += 1
                errors.append(item_id)

        return {
            'success': success_count,
            'failed': failed_count,
            'errors': errors
        }

    def bulk_remove_tags_from_items(self, item_ids: List[int], tag_name: str) -> int:
        """Bulk remove tags from items"""
        if not item_ids or len(item_ids) == 0:
            return 0

        if len(item_ids) > MAX_BULK_SIZE:
            debug_print(f" Bulk operation limited to {MAX_BULK_SIZE} items (requested: {len(item_ids)})")
            item_ids = item_ids[:MAX_BULK_SIZE]

        success_count = 0

        for item_id in item_ids:
            if self.remove_tag_from_item(item_id, tag_name):
                success_count += 1

        return success_count

    def bulk_remove_tags_from_items_detailed(self, item_ids: List[int], tag_name: str) -> dict:
        """Bulk remove tags from items with detailed error reporting"""
        if not item_ids or len(item_ids) == 0:
            return {'success': 0, 'failed': 0, 'errors': []}

        if len(item_ids) > MAX_BULK_SIZE:
            debug_print(f" Bulk operation limited to {MAX_BULK_SIZE} items (requested: {len(item_ids)})")
            item_ids = item_ids[:MAX_BULK_SIZE]

        success_count = 0
        failed_count = 0
        errors = []

        for item_id in item_ids:
            if self.remove_tag_from_item(item_id, tag_name):
                success_count += 1
            else:
                failed_count += 1
                errors.append(item_id)

        return {
            'success': success_count,
            'failed': failed_count,
            'errors': errors
        }

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