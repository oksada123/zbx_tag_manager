#!/bin/bash

# Script to run Zabbix Tag Manager

echo "Starting Zabbix Tag Manager..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "ERROR: Virtual environment does not exist. Run first:"
    echo "   ./install_and_run.sh"
    exit 1
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "ERROR: .env file does not exist. Copy and configure:"
    echo "   cp .env.example .env"
    echo "   nano .env"
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Check if requirements are installed
python -c "import flask, requests, dotenv" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "ERROR: Dependencies are not installed. Run:"
    echo "   ./install_and_run.sh"
    exit 1
fi

echo "Starting application at http://localhost:5000"
echo "Press Ctrl+C to stop"
echo ""

# Run the application
python app.py