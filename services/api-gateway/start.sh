#!/bin/bash
# DataFlux API Gateway Startup Script

set -e

echo "🚀 Starting DataFlux API Gateway..."

# Function to check if a service is ready
check_service() {
    local service_name=$1
    local service_url=$2
    local max_attempts=30
    local attempt=1

    echo "⏳ Waiting for $service_name to be ready..."
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s -f "$service_url" > /dev/null 2>&1; then
            echo "✅ $service_name is ready!"
            return 0
        fi
        
        echo "⏳ Attempt $attempt/$max_attempts: $service_name not ready yet..."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    echo "❌ $service_name failed to start after $max_attempts attempts"
    return 1
}

# Check if services are ready (optional - for development)
if [ "${CHECK_SERVICES:-true}" = "true" ]; then
    echo "🔍 Checking backend services..."
    
    # Check Ingestion Service
    check_service "Ingestion Service" "http://ingestion-service:8002/health" || true
    
    # Check Query Service  
    check_service "Query Service" "http://query-service:8003/health" || true
    
    # Check Analysis Service
    check_service "Analysis Service" "http://analysis-service:8004/health" || true
    
    # Check MCP Server
    check_service "MCP Server" "http://mcp-server:8004/health" || true
    
    # Check Web UI
    check_service "Web UI" "http://web-ui:3000" || true
fi

# Test Nginx configuration
echo "🔧 Testing Nginx configuration..."
nginx -t

# Start Nginx
echo "🚀 Starting Nginx..."
exec nginx -g "daemon off;"
