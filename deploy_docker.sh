#!/usr/bin/env bash
# ==============================================================================
# Docker Management Helper Script for TuyulVB Bot
# Usage: ./deploy_docker.sh [start|stop|restart|logs|status|build]
# ==============================================================================

set -e

ACTION="${1:-status}"

case "$ACTION" in
    start)
        echo "🚀 Starting TuyulVB Backend Bot Container..."
        docker compose up -d --build
        echo "✅ Container started successfully! Run './deploy_docker.sh logs' to view output."
        ;;
    stop)
        echo "🛑 Stopping TuyulVB Backend Bot Container..."
        docker compose down
        echo "✅ Container stopped."
        ;;
    restart)
        echo "🔄 Restarting TuyulVB Backend Bot Container..."
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
