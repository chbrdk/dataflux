#!/bin/bash
# DataFlux Kubernetes Deployment Script
# Deploys DataFlux to Kubernetes cluster

set -euo pipefail

# Configuration
NAMESPACE="dataflux"
KUBECTL_CMD="kubectl"
HELM_CMD="helm"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"
}

log_error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1"
}

log_info() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')] INFO:${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check kubectl
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed"
        exit 1
    fi
    
    # Check helm
    if ! command -v helm &> /dev/null; then
        log_warn "helm is not installed, some features may not work"
    fi
    
    # Check cluster connection
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot connect to Kubernetes cluster"
        exit 1
    fi
    
    log "✓ Prerequisites check passed"
}

# Create namespace
create_namespace() {
    log "Creating namespace: $NAMESPACE"
    
    if kubectl get namespace "$NAMESPACE" &> /dev/null; then
        log_info "Namespace $NAMESPACE already exists"
    else
        kubectl create namespace "$NAMESPACE"
        log "✓ Namespace created"
    fi
}

# Deploy database services
deploy_databases() {
    log "Deploying database services..."
    
    kubectl apply -f k8s/database-services.yaml
    log "✓ Database services deployed"
    
    # Wait for databases to be ready
    log "Waiting for databases to be ready..."
    kubectl wait --for=condition=ready pod -l app=postgres -n "$NAMESPACE" --timeout=300s
    kubectl wait --for=condition=ready pod -l app=redis -n "$NAMESPACE" --timeout=300s
    kubectl wait --for=condition=ready pod -l app=kafka -n "$NAMESPACE" --timeout=300s
    kubectl wait --for=condition=ready pod -l app=minio -n "$NAMESPACE" --timeout=300s
}

# Deploy AI/ML services
deploy_ai_ml() {
    log "Deploying AI/ML services..."
    
    kubectl apply -f k8s/ai-ml-services.yaml
    log "✓ AI/ML services deployed"
    
    # Wait for AI/ML services to be ready
    log "Waiting for AI/ML services to be ready..."
    kubectl wait --for=condition=ready pod -l app=weaviate -n "$NAMESPACE" --timeout=300s
    kubectl wait --for=condition=ready pod -l app=neo4j -n "$NAMESPACE" --timeout=300s
    kubectl wait --for=condition=ready pod -l app=clickhouse -n "$NAMESPACE" --timeout=300s
}

# Deploy application services
deploy_applications() {
    log "Deploying application services..."
    
    kubectl apply -f k8s/application-services.yaml
    log "✓ Application services deployed"
    
    # Wait for application services to be ready
    log "Waiting for application services to be ready..."
    kubectl wait --for=condition=ready pod -l app=ingestion-service -n "$NAMESPACE" --timeout=300s
    kubectl wait --for=condition=ready pod -l app=query-service -n "$NAMESPACE" --timeout=300s
    kubectl wait --for=condition=ready pod -l app=analysis-service -n "$NAMESPACE" --timeout=300s
    kubectl wait --for=condition=ready pod -l app=auth-service -n "$NAMESPACE" --timeout=300s
    kubectl wait --for=condition=ready pod -l app=mcp-server -n "$NAMESPACE" --timeout=300s
    kubectl wait --for=condition=ready pod -l app=web-ui -n "$NAMESPACE" --timeout=300s
}

# Deploy API gateway and monitoring
deploy_gateway_monitoring() {
    log "Deploying API gateway and monitoring..."
    
    kubectl apply -f k8s/api-gateway-monitoring.yaml
    log "✓ API gateway and monitoring deployed"
    
    # Wait for services to be ready
    log "Waiting for API gateway and monitoring to be ready..."
    kubectl wait --for=condition=ready pod -l app=api-gateway -n "$NAMESPACE" --timeout=300s
    kubectl wait --for=condition=ready pod -l app=prometheus -n "$NAMESPACE" --timeout=300s
    kubectl wait --for=condition=ready pod -l app=grafana -n "$NAMESPACE" --timeout=300s
}

# Deploy scaling policies
deploy_scaling() {
    log "Deploying scaling policies..."
    
    kubectl apply -f k8s/scaling-policies.yaml
    log "✓ Scaling policies deployed"
}

# Deploy all services
deploy_all() {
    log "Starting DataFlux deployment..."
    
    check_prerequisites
    create_namespace
    deploy_databases
    deploy_ai_ml
    deploy_applications
    deploy_gateway_monitoring
    deploy_scaling
    
    log "🎉 DataFlux deployment completed successfully!"
    
    # Show deployment status
    show_status
}

# Show deployment status
show_status() {
    log "Deployment Status:"
    echo ""
    
    log_info "Pods:"
    kubectl get pods -n "$NAMESPACE"
    echo ""
    
    log_info "Services:"
    kubectl get services -n "$NAMESPACE"
    echo ""
    
    log_info "Ingress:"
    kubectl get ingress -n "$NAMESPACE" 2>/dev/null || log_warn "No ingress found"
    echo ""
    
    log_info "HPA:"
    kubectl get hpa -n "$NAMESPACE" 2>/dev/null || log_warn "No HPA found"
    echo ""
    
    # Get external IP
    EXTERNAL_IP=$(kubectl get service api-gateway -n "$NAMESPACE" -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "Pending")
    log_info "External IP: $EXTERNAL_IP"
    
    # Show access URLs
    echo ""
    log_info "Access URLs:"
    echo "  Web UI: http://$EXTERNAL_IP"
    echo "  API Gateway: http://$EXTERNAL_IP/api"
    echo "  Prometheus: http://$EXTERNAL_IP:9090"
    echo "  Grafana: http://$EXTERNAL_IP:3000"
    echo "  MinIO Console: http://$EXTERNAL_IP:9001"
    echo "  Neo4j Browser: http://$EXTERNAL_IP:7474"
}

# Undeploy all services
undeploy_all() {
    log "Undeploying DataFlux..."
    
    kubectl delete -f k8s/scaling-policies.yaml --ignore-not-found=true
    kubectl delete -f k8s/api-gateway-monitoring.yaml --ignore-not-found=true
    kubectl delete -f k8s/application-services.yaml --ignore-not-found=true
    kubectl delete -f k8s/ai-ml-services.yaml --ignore-not-found=true
    kubectl delete -f k8s/database-services.yaml --ignore-not-found=true
    kubectl delete -f k8s/namespace-configmaps.yaml --ignore-not-found=true
    
    log "✓ DataFlux undeployed"
}

# Scale services
scale_services() {
    local service=$1
    local replicas=$2
    
    log "Scaling $service to $replicas replicas..."
    
    kubectl scale deployment "$service" -n "$NAMESPACE" --replicas="$replicas"
    log "✓ $service scaled to $replicas replicas"
}

# Get logs
get_logs() {
    local service=$1
    local lines=${2:-100}
    
    log "Getting logs for $service (last $lines lines)..."
    
    kubectl logs -l app="$service" -n "$NAMESPACE" --tail="$lines"
}

# Port forward for local access
port_forward() {
    local service=$1
    local port=$2
    
    log "Port forwarding $service:$port to localhost:$port..."
    
    kubectl port-forward service/"$service" "$port:$port" -n "$NAMESPACE"
}

# Health check
health_check() {
    log "Performing health check..."
    
    # Check all pods are running
    local failed_pods=$(kubectl get pods -n "$NAMESPACE" --field-selector=status.phase!=Running --no-headers | wc -l)
    
    if [ "$failed_pods" -gt 0 ]; then
        log_error "Some pods are not running:"
        kubectl get pods -n "$NAMESPACE" --field-selector=status.phase!=Running
        return 1
    fi
    
    # Check services are accessible
    local services=("ingestion-service" "query-service" "analysis-service" "auth-service" "mcp-server" "web-ui")
    
    for service in "${services[@]}"; do
        if kubectl get service "$service" -n "$NAMESPACE" &> /dev/null; then
            log "✓ $service service is accessible"
        else
            log_error "$service service is not accessible"
            return 1
        fi
    done
    
    log "✓ Health check passed"
    return 0
}

# Main function
main() {
    case "${1:-deploy}" in
        "deploy")
            deploy_all
            ;;
        "undeploy")
            undeploy_all
            ;;
        "status")
            show_status
            ;;
        "scale")
            if [ $# -ne 3 ]; then
                log_error "Usage: $0 scale <service> <replicas>"
                exit 1
            fi
            scale_services "$2" "$3"
            ;;
        "logs")
            if [ $# -ne 2 ]; then
                log_error "Usage: $0 logs <service> [lines]"
                exit 1
            fi
            get_logs "$2" "${3:-100}"
            ;;
        "port-forward")
            if [ $# -ne 3 ]; then
                log_error "Usage: $0 port-forward <service> <port>"
                exit 1
            fi
            port_forward "$2" "$3"
            ;;
        "health")
            health_check
            ;;
        *)
            echo "Usage: $0 {deploy|undeploy|status|scale|logs|port-forward|health}"
            echo ""
            echo "Commands:"
            echo "  deploy        - Deploy DataFlux to Kubernetes"
            echo "  undeploy      - Remove DataFlux from Kubernetes"
            echo "  status        - Show deployment status"
            echo "  scale         - Scale a service (usage: scale <service> <replicas>)"
            echo "  logs          - Get logs for a service (usage: logs <service> [lines])"
            echo "  port-forward  - Port forward a service (usage: port-forward <service> <port>)"
            echo "  health        - Perform health check"
            exit 1
            ;;
    esac
}

main "$@"
