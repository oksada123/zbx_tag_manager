#!/usr/bin/env python3

import requests
import json
from dotenv import load_dotenv
import os

load_dotenv()

def test_api_info():
    """Test informacji o API i wersji Zabbix"""

    url = os.getenv('ZABBIX_URL')
    username = os.getenv('ZABBIX_USER')
    password = os.getenv('ZABBIX_PASSWORD')

    # Test 1: apiinfo.version (nie wymaga autoryzacji)
    print("=== Test 1: Wersja API ===")
    version_payload = {
        "jsonrpc": "2.0",
        "method": "apiinfo.version",
        "params": {},
        "id": 1
    }

    try:
        response = requests.post(url, json=version_payload)
        result = response.json()
        print(f"Odpowiedź apiinfo.version: {result}")

        if 'result' in result:
            print(f"✅ Wersja Zabbix API: {result['result']}")
    except Exception as e:
        print(f"❌ Błąd apiinfo.version: {e}")

    # Test 2: Logowanie
    print(f"\n=== Test 2: Logowanie ===")
    login_payload = {
        "jsonrpc": "2.0",
        "method": "user.login",
        "params": {
            "username": username,
            "password": password
        },
        "id": 1
    }

    try:
        response = requests.post(url, json=login_payload)
        login_result = response.json()
        print(f"Odpowiedź user.login: {login_result}")

        if 'result' not in login_result:
            print("❌ Logowanie nie powiodło się")
            return

        token = login_result['result']
        print(f"✅ Token autoryzacji: {token}")

        # Test 3: Sprawdzenie sesji
        print(f"\n=== Test 3: Sprawdzenie sesji ===")
        session_payload = {
            "jsonrpc": "2.0",
            "method": "user.checkAuthentication",
            "params": {
                "sessionid": token
            },
            "id": 1
        }

        response = requests.post(url, json=session_payload)
        session_result = response.json()
        print(f"Odpowiedź user.checkAuthentication: {session_result}")

        # Test 4: Najprostsze zapytanie z auth
        print(f"\n=== Test 4: Test podstawowego zapytania ===")
        simple_payload = {
            "jsonrpc": "2.0",
            "method": "host.get",
            "params": {
                "output": ["hostid", "name"],
                "limit": 1
            },
            "auth": token,
            "id": 1
        }

        response = requests.post(url, json=simple_payload)
        simple_result = response.json()
        print(f"Odpowiedź host.get (prosty): {simple_result}")

        # Test 5: Sprawdzenie uprawnień użytkownika
        print(f"\n=== Test 5: Uprawnienia użytkownika ===")
        user_payload = {
            "jsonrpc": "2.0",
            "method": "user.get",
            "params": {
                "output": ["userid", "username", "name", "type"],
                "userids": [],
                "selectUsrgrps": "extend"
            },
            "auth": token,
            "id": 1
        }

        response = requests.post(url, json=user_payload)
        user_result = response.json()
        print(f"Odpowiedź user.get: {user_result}")

    except Exception as e:
        print(f"❌ Błąd: {e}")

if __name__ == "__main__":
    test_api_info()