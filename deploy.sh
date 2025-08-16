#!/bin/bash

# YouTube Automation System - Deployment Script
echo "🚀 Deploying YouTube Automation System..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    echo "✅ Docker installed. Please log out and back in, then run this script again."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose not found. Installing..."
    sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
fi

# Create necessary directories
mkdir -p media/videos media/audio media/images database logs

# Set proper permissions
chmod +x deploy.sh

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
    echo "✅ Environment variables loaded"
else
    echo "❌ .env file not found. Please create it with your API keys."
    exit 1
fi

# Build and start the application
echo "🔨 Building Docker image..."
docker-compose build

echo "🚀 Starting YouTube Automation System..."
docker-compose up -d

# Wait for application to start
echo "⏳ Waiting for application to start..."
sleep 30

# Check if application is running
if curl -f http://localhost:5000/api/automation/status > /dev/null 2>&1; then
    echo "🎉 SUCCESS! YouTube Automation System is running!"
    echo ""
    echo "📊 Dashboard: http://localhost:5000"
    echo "📋 Status: http://localhost:5000/api/automation/status"
    echo ""
    echo "🔧 Management Commands:"
    echo "  View logs:    docker-compose logs -f"
    echo "  Stop system:  docker-compose down"
    echo "  Restart:      docker-compose restart"
    echo "  Update:       git pull && docker-compose up -d --build"
    echo ""
    echo "🎯 Your YouTube automation is now running 24/7!"
else
    echo "❌ Application failed to start. Check logs with: docker-compose logs"
    exit 1
fi

