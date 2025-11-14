#!/bin/bash

# Script to install and run Zabbix Tag Manager
# This script handles the virtual environment setup

echo "=== Zabbix Tag Manager - Installation ==="

# Check if python3-venv is available
if ! python3 -c "import venv" 2>/dev/null; then
    echo "ERROR: python3-venv is missing. Run:"
    echo "   sudo apt update && sudo apt install python3.12-venv"
    exit 1
fi

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "ERROR: Failed to create virtual environment"
        echo "Try: sudo apt install python3-full python3.12-venv"
        exit 1
    fi
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install requirements
echo "Installing dependencies..."
pip install --upgrade pip

# Try normal installation first, then with break-system-packages if needed
pip install -r requirements.txt 2>/dev/null || {
    echo "WARNING: Standard installation failed, using --break-system-packages..."
    pip install --break-system-packages -r requirements.txt
}

if [ $? -eq 0 ]; then
    echo "Installation completed successfully!"
    echo ""
    echo "=== Next steps ==="
    echo "1. Copy .env.example to .env:"
    echo "   cp .env.example .env"
    echo ""
    echo "2. Edit .env file and fill in Zabbix credentials:"
    echo "   nano .env"
    echo ""
    echo "3. Run the application:"
    echo "   source venv/bin/activate"
    echo "   python app.py"
    echo ""
    echo "4. Open http://localhost:5000 in your browser"
else
    echo "ERROR: Error during dependencies installation"
    exit 1
fi