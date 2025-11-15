#!/bin/bash

# Installation script for Zabbix Tag Manager
# Installs system Python packages via apt-get

set -e

echo "=== Zabbix Tag Manager - Installation ==="
echo ""

# Check if running as root or with sudo
if [ "$EUID" -ne 0 ]; then
    echo "This script requires sudo privileges to install system packages."
    echo "You may be prompted for your password."
    echo ""
    SUDO="sudo"
else
    SUDO=""
fi

echo "Updating package list..."
$SUDO apt-get update

echo ""
echo "Installing Python dependencies..."

# Install Python packages from requirements.txt
PACKAGES=(
    "python3-flask"
    "python3-requests"
    "python3-dotenv"
    "python3-werkzeug"
)

for package in "${PACKAGES[@]}"; do
    echo "Installing $package..."
    $SUDO apt-get install -y "$package"
done

echo ""
echo "=== Installation completed successfully! ==="
echo ""
echo "Next steps:"
echo "1. Configure .env file (if not done already):"
echo "   cp .env.example .env"
echo "   nano .env"
echo ""
echo "2. Run the application:"
echo "   ./run.sh"
echo ""
echo "3. Open http://localhost:5000 in your browser"
echo ""
