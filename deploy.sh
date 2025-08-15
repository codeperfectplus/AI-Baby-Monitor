#!/bin/bash
# End-to-end Docker setup and run script for RTSP Baby Monitor

set -e

echo "🐳 RTSP Baby Monitor Docker End-to-End Setup"
echo "==========================================="

# Check if container is already running
if docker ps --format '{{.Names}}' | grep -q '^rtsp-baby-monitor$'; then
    echo "⚠️  Container 'rtsp-baby-monitor' is already running."
    echo "Stopping container..."
    docker-compose down
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📄 Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env file with your RTSP camera credentials"
else
    echo "✅ .env file already exists"
fi


# Create directories on host
echo "📁 Creating host directories..."
mkdir -p "$HOME/baby-monitor/recordings"
mkdir -p "$HOME/baby-monitor/snapshots"
mkdir -p "$HOME/baby-monitor/logs"
mkdir -p "$HOME/baby-monitor/cache"
mkdir -p "$HOME/baby-monitor/database"

# Build Docker image
echo "🔨 Building Docker image..."
docker-compose build

# Start the application
echo "🚀 Starting the application..."
docker-compose up -d

# Show status
echo ""
echo "🎉 Setup and server startup complete!"
echo ""
echo "To view logs:"
echo "  docker-compose logs -f"
echo ""
echo "To stop the application:"
echo "  docker-compose down"
echo ""
echo "📝 Don't forget to:"
echo "  1. Edit .env file with your RTSP camera settings"
echo "  2. Adjust docker-compose.yml if needed"
echo "  3. For GUI display, run: xhost +local:docker"
echo ""
