#!/bin/bash

# DATAFLUX - Lokales Stop-Script für Mac Mini M4
echo "🛑 Stopping DATAFLUX services..."

# Stoppe Python Services
pkill -f "main_simple.py"
pkill -f "api_processor.py"

# Stoppe Go Service
pkill -f "main_simple.go"

# Stoppe Web-UI
pkill -f "npm run dev"
pkill -f "next dev"

# Optional: Stoppe Docker Container
# docker stop dataflux-postgres dataflux-redis

echo "✅ All DATAFLUX services stopped"
echo ""
echo "💡 Docker containers (PostgreSQL, Redis) are still running"
echo "   To stop them: docker stop dataflux-postgres dataflux-redis"
