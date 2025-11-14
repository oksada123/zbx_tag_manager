# Zabbix Tag Manager

Aplikacja webowa do zarządzania tagami hostów w Zabbix 7 z interfejsem Flask.

## Funkcjonalności

- 🏠 Przeglądanie wszystkich hostów z tagami
- 🏷️ Dodawanie i usuwanie tagów dla pojedynczych hostów
- 🔧 Operacje masowe na tagach (dodawanie/usuwanie dla wielu hostów)
- 🔍 Wyszukiwanie i filtrowanie hostów
- 🎨 Intuicyjny interfejs webowy
- 📱 Responsywny design

## Wymagania

- Python 3.8+
- Zabbix Server 7.x z włączonym API
- Dostęp do Zabbix API

## Instalacja

### Opcja 1: Prosta instalacja (jeśli masz problemy z venv)

```bash
./install_simple.sh
```

### Opcja 2: Docker (zalecana dla systemów z ograniczeniami)

```bash
./run_with_docker.sh
```

### Opcja 3: Automatyczna instalacja z venv

```bash
./install_and_run.sh
```

### Opcja 2: Ręczna instalacja

1. Zainstaluj wymagane pakiety systemowe:
```bash
sudo apt update && sudo apt install python3.12-venv
```

2. Utwórz środowisko wirtualne:
```bash
python3 -m venv venv
source venv/bin/activate
```

3. Zainstaluj zależności:
```bash
pip install -r requirements.txt
```

4. Skopiuj i skonfiguruj zmienne środowiskowe:
```bash
cp .env.example .env
nano .env
```

5. Edytuj plik `.env` i uzupełnij dane dostępowe do Zabbix:
```
ZABBIX_URL=http://your-zabbix-server/api_jsonrpc.php
ZABBIX_USER=your-username
ZABBIX_PASSWORD=your-password
SECRET_KEY=your-secret-key-here
```

## Uruchomienie

### Opcja 1: Używając skryptu
```bash
./run.sh
```

### Opcja 2: Ręcznie
```bash
source venv/bin/activate
python app.py
```

Aplikacja będzie dostępna pod adresem: http://localhost:5000

## Struktura projektu

```
tag_manage/
├── app.py                 # Główna aplikacja Flask
├── requirements.txt       # Zależności Python
├── .env.example          # Przykład konfiguracji
├── app/
│   ├── __init__.py
│   ├── zabbix_api.py     # Moduł komunikacji z Zabbix API
│   ├── templates/         # Szablony HTML
│   │   ├── base.html
│   │   ├── index.html
│   │   ├── hosts.html
│   │   └── host_tags.html
│   └── static/           # Pliki statyczne
│       ├── css/
│       │   └── style.css
│       └── js/
│           └── script.js
└── README.md
```

## Użycie

### Przeglądanie hostów
- Przejdź do sekcji "Hosty" aby zobaczyć wszystkie hosty z tagami
- Użyj pola wyszukiwania aby filtrować hosty po nazwie
- Użyj filtra tagów aby znaleźć hosty z określonymi tagami

### Zarządzanie tagami pojedynczego hosta
- Kliknij "Zarządzaj tagami" przy wybranym hoście
- Dodaj nowy tag podając nazwę i opcjonalną wartość
- Usuń istniejący tag klikając przycisk "Usuń"

### Operacje masowe
- Zaznacz hosty na liście (można użyć "Zaznacz wszystkie")
- Wprowadź nazwę tagu i opcjonalną wartość
- Wybierz operację: "Dodaj do zaznaczonych" lub "Usuń z zaznaczonych"

## API Endpoints

- `GET /` - Strona główna
- `GET /hosts` - Lista hostów
- `GET /host/<id>/tags` - Zarządzanie tagami hosta
- `POST /api/host/<id>/tags` - Dodanie tagu do hosta
- `DELETE /api/host/<id>/tags/<tag>` - Usunięcie tagu z hosta
- `POST /api/hosts/tags/bulk` - Operacje masowe na tagach

## Bezpieczeństwo

- Aplikacja używa zmiennych środowiskowych do przechowywania danych dostępowych
- Zalecane jest uruchomienie w środowisku produkcyjnym za reverse proxy (nginx)
- Należy używać HTTPS w środowisku produkcyjnym

## Rozwiązywanie problemów

### Błąd połączenia z Zabbix API
- Sprawdź poprawność URL do Zabbix API
- Zweryfikuj dane logowania
- Upewnij się, że użytkownik ma odpowiednie uprawnienia w Zabbix

### Błędy autoryzacji
- Sprawdź czy API jest włączone w Zabbix
- Zweryfikuj uprawnienia użytkownika
- Sprawdź czy hasło nie wygasło

## Licencja

MIT License