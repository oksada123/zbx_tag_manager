#!/usr/bin/env python3

import requests
import json
from dotenv import load_dotenv
import os

load_dotenv()

def test_auth_methods():
    """Test różnych metod autoryzacji w Zabbix 7.4.5"""

    url = os.getenv('ZABBIX_URL')
    username = os.getenv('ZABBIX_USER')
    password = os.getenv('ZABBIX_PASSWORD')

    # Logowanie
    login_payload = {
        "jsonrpc": "2.0",
        "method": "user.login",
        "params": {
            "username": username,
            "password": password
        },
        "id": 1
    }

    session = requests.Session()
    response = session.post(url, json=login_payload)
    login_result = response.json()

    if 'result' not in login_result:
        print("❌ Logowanie nie powiodło się")
        return

    token = login_result['result']
    print(f"✅ Token: {token}")

    # Test host.get
    host_payload = {
        "jsonrpc": "2.0",
        "method": "host.get",
        "params": {
            "output": ["hostid", "name"],
            "limit": 1
        },
        "id": 1
    }

    print("\n=== Test 1: Bez autoryzacji ===")
    response = session.post(url, json=host_payload)
    result = response.json()
    print(f"Odpowiedź: {result}")

    print("\n=== Test 2: Z nagłówkiem Authorization ===")
    headers = {"Authorization": f"Bearer {token}"}
    response = session.post(url, json=host_payload, headers=headers)
    result = response.json()
    print(f"Odpowiedź: {result}")

    print("\n=== Test 3: Z nagłówkiem X-Auth-Token ===")
    headers = {"X-Auth-Token": token}
    response = session.post(url, json=host_payload, headers=headers)
    result = response.json()
    print(f"Odpowiedź: {result}")

    print("\n=== Test 4: Z nagłówkiem Zabbix-Auth ===")
    headers = {"Zabbix-Auth": token}
    response = session.post(url, json=host_payload, headers=headers)
    result = response.json()
    print(f"Odpowiedź: {result}")

    print("\n=== Test 5: Sesja z ciasteczkami ===")
    # Sprawdź czy po logowaniu mamy ciasteczka
    print(f"Ciasteczka po logowaniu: {dict(session.cookies)}")
    response = session.post(url, json=host_payload)
    result = response.json()
    print(f"Odpowiedź z ciasteczkami: {result}")

    print("\n=== Test 6: Token w URL ===")
    auth_url = f"{url}?auth={token}"
    response = session.post(auth_url, json=host_payload)
    result = response.json()
    print(f"Odpowiedź z token w URL: {result}")

    # Test 7: Sprawdźmy co się dzieje gdy użyjemy sessida zamiast auth
    print("\n=== Test 7: sessionid zamiast auth ===")
    session_payload = {
        "jsonrpc": "2.0",
        "method": "host.get",
        "params": {
            "output": ["hostid", "name"],
            "limit": 1
        },
        "sessionid": token,
        "id": 1
    }
    response = session.post(url, json=session_payload)
    result = response.json()
    print(f"Odpowiedź z sessionid: {result}")

if __name__ == "__main__":
    test_auth_methods()