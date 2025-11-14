#!/bin/bash

# Script to run Zabbix Tag Manager

echo "Uruchamianie Zabbix Tag Manager..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "BŁĄD: Środowisko wirtualne nie istnieje. Uruchom najpierw:"
    echo "   ./install_and_run.sh"
    exit 1
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "BŁĄD: Plik .env nie istnieje. Skopiuj i skonfiguruj:"
    echo "   cp .env.example .env"
    echo "   nano .env"
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Check if requirements are installed
python -c "import flask, requests, dotenv" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "BŁĄD: Zależności nie są zainstalowane. Uruchom:"
    echo "   ./install_and_run.sh"
    exit 1
fi

echo "Uruchamianie aplikacji na http://localhost:5000"
echo "Naciśnij Ctrl+C aby zatrzymać"
echo ""

# Run the application
python app.py