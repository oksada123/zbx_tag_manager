#!/bin/bash

# Simple installation without virtual environment
# Uses --break-system-packages as a last resort

echo "=== Zabbix Tag Manager - Simple installation ==="
echo "WARNING: This method installs packages globally"

echo "Installing dependencies..."

# Try installing to user directory
if pip3 install --user -r requirements.txt 2>/dev/null; then
    echo "Installation to user directory completed successfully!"
    PYTHON_CMD="python3"
elif pip3 install --break-system-packages -r requirements.txt; then
    echo "Installation with --break-system-packages completed successfully!"
    PYTHON_CMD="python3"
else
    echo "ERROR: Installation failed"
    echo ""
    echo "Alternatives:"
    echo "1. Use Docker: ./run_with_docker.sh"
    echo "2. Install python3-venv: sudo apt install python3.12-venv"
    echo "3. Use conda/miniconda"
    exit 1
fi

echo ""
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
echo "   $PYTHON_CMD app.py"
echo ""
echo "4. Open http://localhost:5000 in your browser"