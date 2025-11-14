#!/bin/bash

# Script to install and run Zabbix Tag Manager
# This script handles the virtual environment setup

echo "=== Zabbix Tag Manager - Instalacja ==="

# Check if python3-venv is available
if ! python3 -c "import venv" 2>/dev/null; then
    echo "BŁĄD: Brakuje python3-venv. Uruchom:"
    echo "   sudo apt update && sudo apt install python3.12-venv"
    exit 1
fi

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "Tworzenie wirtualnego środowiska..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "BŁĄD: Nie udało się utworzyć środowiska wirtualnego"
        echo "Spróbuj: sudo apt install python3-full python3.12-venv"
        exit 1
    fi
fi

# Activate virtual environment
echo "Aktywacja środowiska wirtualnego..."
source venv/bin/activate

# Install requirements
echo "Instalacja zależności..."
pip install --upgrade pip

# Try normal installation first, then with break-system-packages if needed
pip install -r requirements.txt 2>/dev/null || {
    echo "UWAGA: Standardowa instalacja nie powiodła się, używam --break-system-packages..."
    pip install --break-system-packages -r requirements.txt
}

if [ $? -eq 0 ]; then
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
    echo "   source venv/bin/activate"
    echo "   python app.py"
    echo ""
    echo "4. Otwórz http://localhost:5000 w przeglądarce"
else
    echo "BŁĄD: Błąd podczas instalacji zależności"
    exit 1
fi