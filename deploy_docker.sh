#!/usr/bin/env bash
# ==============================================================================
# Docker Management Helper Script for Auto-OC Bot
# Usage: ./deploy_docker.sh [up|down|start|stop|restart|logs|status|build]
# ==============================================================================

set -e

ACTION="${1:-status}"

case "$ACTION" in
    up)
        echo "🚀 Building and starting Auto-OC containers..."
        docker compose up -d --build
        echo "✅ Containers started successfully!"
        ;;
    start)
        echo "🚀 Starting Auto-OC Backend Bot Container..."
        docker compose start bot
        ;;
    stop|down)
        echo "🛑 Stopping Auto-OC Backend Bot Container..."
        docker compose down
        echo "✅ Container stopped."
        ;;
    restart)
        echo "🔄 Restarting Auto-OC Backend Bot Container..."
        docker compose restart
        echo "✅ Container restarted."
        ;;
    logs)
        echo "📋 Displaying real-time container logs (Press Ctrl+C to exit)..."
        docker compose logs -f --tail=100
        ;;
    status)
        echo "🔍 Checking Docker Container Status..."
        docker compose ps
        ;;
    build)
        echo "🔨 Building Docker Image..."
        docker compose build --no-cache
        echo "✅ Build completed."
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|logs|status|build}"
        exit 1
        ;;
esac
