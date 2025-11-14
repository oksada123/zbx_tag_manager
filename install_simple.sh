#!/bin/bash

# Prosta instalacja bez środowiska wirtualnego
# Używa --break-system-packages jako ostateczność

echo "=== Zabbix Tag Manager - Prosta instalacja ==="
echo "UWAGA: Ta metoda instaluje pakiety globalnie"

echo "Instalacja zależności..."

# Próba instalacji do katalogu użytkownika
if pip3 install --user -r requirements.txt 2>/dev/null; then
    echo "Instalacja do katalogu użytkownika zakończona pomyślnie!"
    PYTHON_CMD="python3"
elif pip3 install --break-system-packages -r requirements.txt; then
    echo "Instalacja z --break-system-packages zakończona pomyślnie!"
    PYTHON_CMD="python3"
else
    echo "BŁĄD: Instalacja nie powiodła się"
    echo ""
    echo "Alternatywy:"
    echo "1. Użyj Docker: ./run_with_docker.sh"
    echo "2. Zainstaluj python3-venv: sudo apt install python3.12-venv"
    echo "3. Użyj conda/miniconda"
    exit 1
fi

echo ""
echo "Instalacja zakończona pomyślnie!"
echo ""
echo "=== Następne kroki ==="
echo "1. Skopiuj .env.example do .env:"
echo "   cp .env.example .env"
echo ""
echo "2. Edytuj plik .env i uzupełnij dane Zabbix:"
echo "   nano .env"
echo ""
echo "3. Uruchom aplikację:"
echo "   $PYTHON_CMD app.py"
echo ""
echo "4. Otwórz http://localhost:5000 w przeglądarce"