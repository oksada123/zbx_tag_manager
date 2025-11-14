#!/bin/bash

# Run Zabbix Tag Manager using Docker

echo "Creating Docker image..."

# Create Dockerfile
cat > Dockerfile << 'EOF'
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy application files
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Application port
EXPOSE 5000

# Startup command
CMD ["python", "app.py"]
EOF

echo "Building Docker image..."
docker build -t zabbix-tag-manager .

if [ $? -eq 0 ]; then
    echo "Docker image created successfully!"
    echo ""
    echo "Starting container..."
    echo "Remember to configure .env file before running"

    if [ ! -f ".env" ]; then
        echo "WARNING: .env file does not exist. Creating from template..."
        cp .env.example .env
        echo "Edit .env file and fill in Zabbix credentials before running"
    fi

    echo ""
    echo "To run the application:"
    echo "   docker run -p 5000:5000 --env-file .env zabbix-tag-manager"
    echo ""
    echo "Application will be available at http://localhost:5000"
else
    echo "ERROR: Error during Docker image build"
    echo "Check if Docker is installed: docker --version"
fi