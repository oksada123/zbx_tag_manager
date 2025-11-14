#!/usr/bin/env python3

import requests
import json
from dotenv import load_dotenv
import os

load_dotenv()

def test_host_get():
    """Test zapytania host.get na żywym Zabbix API"""

    url = os.getenv('ZABBIX_URL')
    username = os.getenv('ZABBIX_USER')
    password = os.getenv('ZABBIX_PASSWORD')

    # Krok 1: Logowanie
    login_payload = {
        "jsonrpc": "2.0",
        "method": "user.login",
        "params": {
            "username": username,
            "password": password
        },
        "id": 1
    }

    print("=== KROK 1: Logowanie ===")
    print(f"Payload: {login_payload}")

    response = requests.post(url, json=login_payload)
    login_result = response.json()
    print(f"Odpowiedź: {login_result}")

    if 'result' not in login_result:
        print("❌ Logowanie nie powiodło się")
        return

    token = login_result['result']
    print(f"✅ Token: {token}")

    # Krok 2: Test różnych formatów host.get
    host_params = {
        "output": ["hostid", "host", "name", "status"],
        "selectTags": "extend",
        "sortfield": "name"
    }

    test_formats = [
        # Format 1: auth na końcu
        {
            "jsonrpc": "2.0",
            "method": "host.get",
            "params": host_params,
            "id": 1,
            "auth": token
        },
        # Format 2: auth przed params
        {
            "jsonrpc": "2.0",
            "method": "host.get",
            "auth": token,
            "params": host_params,
            "id": 1
        },
        # Format 3: auth w params
        {
            "jsonrpc": "2.0",
            "method": "host.get",
            "params": {
                **host_params,
                "auth": token
            },
            "id": 1
        }
    ]

    for i, payload in enumerate(test_formats, 1):
        print(f"\n=== KROK 2.{i}: Test formatu {i} ===")
        print(f"Payload: {payload}")

        try:
            response = requests.post(url, json=payload)
            result = response.json()
            print(f"Odpowiedź: {result}")

            if 'result' in result:
                hosts = result['result']
                print(f"✅ SUKCES! Znaleziono {len(hosts)} hostów")
                if hosts:
                    print(f"Przykład hosta: {hosts[0]}")
                return payload  # Zwróć działający format

        except Exception as e:
            print(f"❌ Błąd: {e}")

    print("\n❌ Żaden format nie zadziałał")
    return None

if __name__ == "__main__":
    working_format = test_host_get()