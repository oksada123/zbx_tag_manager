#!/usr/bin/env python3

import requests
import json
from dotenv import load_dotenv
import os

load_dotenv()

def test_zabbix_api():
    """Test różnych formatów Zabbix API"""

    base_url = "http://localhost:8080"
    username = os.getenv('ZABBIX_USER')
    password = os.getenv('ZABBIX_PASSWORD')

    # Różne możliwe endpointy API dla Zabbix 7
    api_urls = [
        f"{base_url}/api_jsonrpc.php",
        f"{base_url}/zabbix/api_jsonrpc.php",
        f"{base_url}/api/jsonrpc",
        f"{base_url}/zabbix/api/jsonrpc"
    ]

    # Różne formaty parametrów logowania
    login_formats = [
        {"username": username, "password": password},
        {"user": username, "password": password},
        {"login": username, "password": password}
    ]

    for api_url in api_urls:
        print(f"\n=== Testowanie URL: {api_url} ===")

        for i, params in enumerate(login_formats):
            print(f"\nFormat {i+1}: {params}")

            payload = {
                "jsonrpc": "2.0",
                "method": "user.login",
                "params": params,
                "id": 1
            }

            try:
                headers = {'Content-Type': 'application/json'}
                response = requests.post(api_url, json=payload, headers=headers, timeout=10)

                print(f"Status: {response.status_code}")

                if response.status_code == 200:
                    result = response.json()
                    if 'result' in result:
                        print(f"✅ SUKCES! Token: {result['result'][:20]}...")
                        return api_url, params
                    else:
                        error = result.get('error', {})
                        print(f"❌ Błąd API: {error.get('data', error.get('message', 'Unknown'))}")
                else:
                    print(f"❌ HTTP Error: {response.status_code}")

            except requests.RequestException as e:
                print(f"❌ Błąd połączenia: {e}")

    print(f"\n❌ Żaden format nie zadziałał")
    return None, None

if __name__ == "__main__":
    print("=== Test połączenia z Zabbix API ===")
    print(f"Username: {os.getenv('ZABBIX_USER')}")
    print(f"Password: {'*' * len(os.getenv('ZABBIX_PASSWORD', ''))}")

    success_url, success_params = test_zabbix_api()

    if success_url:
        print(f"\n🎉 Znaleziono działającą konfigurację:")
        print(f"URL: {success_url}")
        print(f"Parametry: {success_params}")
        print(f"\nZaktualizuj plik .env:")
        print(f"ZABBIX_URL={success_url}")
    else:
        print("\n💡 Sprawdź:")
        print("1. Czy Zabbix działa na porcie 8080")
        print("2. Czy użytkownik i hasło są poprawne")
        print("3. Czy Zabbix Frontend jest dostępny")
        print("4. Spróbuj zalogować się przez interfejs web")