#!/bin/bash

# Uruchomienie Zabbix Tag Manager za pomocą Dockera

echo "Tworzenie obrazu Docker..."

# Tworzymy Dockerfile
cat > Dockerfile << 'EOF'
FROM python:3.12-slim

WORKDIR /app

# Instalacja zależności systemowych
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Kopiowanie plików aplikacji
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Port aplikacji
EXPOSE 5000

# Komenda uruchomienia
CMD ["python", "app.py"]
EOF

echo "Budowanie obrazu Docker..."
docker build -t zabbix-tag-manager .

if [ $? -eq 0 ]; then
    echo "Obraz Docker został utworzony pomyślnie!"
    echo ""
    echo "Uruchamianie kontenera..."
    echo "Pamiętaj o skonfigurowaniu pliku .env przed uruchomieniem"

    if [ ! -f ".env" ]; then
        echo "UWAGA: Plik .env nie istnieje. Tworzę z szablonu..."
        cp .env.example .env
        echo "Edytuj plik .env i uzupełnij dane Zabbix przed uruchomieniem"
    fi

    echo ""
    echo "Aby uruchomić aplikację:"
    echo "   docker run -p 5000:5000 --env-file .env zabbix-tag-manager"
    echo ""
    echo "Aplikacja będzie dostępna na http://localhost:5000"
else
    echo "BŁĄD: Błąd podczas budowania obrazu Docker"
    echo "Sprawdź czy Docker jest zainstalowany: docker --version"
fi