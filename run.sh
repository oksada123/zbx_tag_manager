#!/bin/bash

# Run script for Zabbix Tag Manager

set -e

echo "=== Zabbix Tag Manager ==="
echo ""

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "ERROR: .env file not found!"
    echo ""
    echo "Please create .env file:"
    echo "   cp .env.example .env"
    echo "   nano .env"
    echo ""
    exit 1
fi

# Check if required Python packages are installed
echo "Checking dependencies..."
python3 -c "import flask, requests, dotenv" 2>/dev/null

if [ $? -ne 0 ]; then
    echo "ERROR: Required Python packages not installed!"
    echo ""
    echo "Run installation script first:"
    echo "   ./install.sh"
    echo ""
    exit 1
fi

echo "Starting application..."
echo "Application will be available at: http://localhost:5000"
echo "Press Ctrl+C to stop"
echo ""

# Run the application
python3 ./app.py
