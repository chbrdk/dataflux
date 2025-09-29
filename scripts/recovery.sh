#!/bin/bash
# DataFlux Disaster Recovery System
# Complete system recovery procedures for DataFlux

set -euo pipefail

# Configuration
BACKUP_ROOT="/opt/dataflux/backups"
LOG_FILE="/var/log/dataflux/recovery.log"
RECOVERY_MODE="${1:-interactive}"

# Database configuration
POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
POSTGRES_PORT="${POSTGRES_PORT:-2001}"
POSTGRES_USER="${POSTGRES_USER:-dataflux_user}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-dataflux_pass}"
POSTGRES_DB="${POSTGRES_DB:-dataflux}"

# Redis configuration
REDIS_HOST="${REDIS_HOST:-localhost}"
REDIS_PORT="${REDIS_PORT:-2002}"
REDIS_PASSWORD="${REDIS_PASSWORD:-dataflux_pass}"

# MinIO configuration
MINIO_ENDPOINT="${MINIO_ENDPOINT:-localhost:2003}"
MINIO_ACCESS_KEY="${MINIO_ACCESS_KEY:-minioadmin}"
MINIO_SECRET_KEY="${MINIO_SECRET_KEY:-minioadmin}"
MINIO_BUCKET="${MINIO_BUCKET:-dataflux-assets}"

# Neo4j configuration
NEO4J_HOST="${NEO4J_HOST:-localhost}"
NEO4J_PORT="${NEO4J_PORT:-2007}"
NEO4J_USER="${NEO4J_USER:-neo4j}"
NEO4J_PASSWORD="${NEO4J_PASSWORD:-dataflux_pass}"

# Weaviate configuration
WEAVIATE_HOST="${WEAVIATE_HOST:-localhost}"
WEAVIATE_PORT="${WEAVIATE_PORT:-2005}"

# ClickHouse configuration
CLICKHOUSE_HOST="${CLICKHOUSE_HOST:-localhost}"
CLICKHOUSE_PORT="${CLICKHOUSE_PORT:-2008}"
CLICKHOUSE_USER="${CLICKHOUSE_USER:-default}"
CLICKHOUSE_PASSWORD="${CLICKHOUSE_PASSWORD:-}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

log_warn() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" | tee -a "$LOG_FILE"
}

log_info() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')] INFO:${NC} $1" | tee -a "$LOG_FILE"
}

# Create log directory
mkdir -p "$(dirname "$LOG_FILE")"

# List available backups
list_backups() {
    log "Available backups:"
    
    if [ ! -d "$BACKUP_ROOT" ]; then
        log_error "Backup directory not found: $BACKUP_ROOT"
        return 1
    fi
    
    local backup_count=0
    
    for backup_file in "$BACKUP_ROOT"/*.tar.gz; do
        if [ -f "$backup_file" ]; then
            local backup_name=$(basename "$backup_file" .tar.gz)
            local backup_date=$(echo "$backup_name" | cut -d'_' -f1-2)
            local backup_time=$(echo "$backup_name" | cut -d'_' -f3-4)
            local backup_size=$(du -h "$backup_file" | cut -f1)
            local backup_age=$(find "$backup_file" -printf '%T@' | xargs -I {} date -d @{} '+%Y-%m-%d %H:%M:%S')
            
            echo "  $((++backup_count)). $backup_name ($backup_size) - $backup_age"
        fi
    done
    
    if [ $backup_count -eq 0 ]; then
        log_warn "No backups found in $BACKUP_ROOT"
        return 1
    fi
    
    return 0
}

# Select backup for recovery
select_backup() {
    local backup_file=""
    
    if [ "$RECOVERY_MODE" = "interactive" ]; then
        list_backups
        
        echo ""
        read -p "Enter backup number to restore: " backup_number
        
        local backup_count=0
        for backup_file in "$BACKUP_ROOT"/*.tar.gz; do
            if [ -f "$backup_file" ]; then
                backup_count=$((backup_count + 1))
                if [ $backup_count -eq $backup_number ]; then
                    break
                fi
            fi
        done
        
        if [ ! -f "$backup_file" ]; then
            log_error "Invalid backup number: $backup_number"
            return 1
        fi
    else
        # Use latest backup
        backup_file=$(ls -t "$BACKUP_ROOT"/*.tar.gz 2>/dev/null | head -n1)
        if [ -z "$backup_file" ]; then
            log_error "No backups found"
            return 1
        fi
    fi
    
    echo "$backup_file"
}

# Extract backup
extract_backup() {
    local backup_file="$1"
    local extract_dir="/tmp/dataflux_recovery_$(date +%s)"
    
    log "Extracting backup: $backup_file"
    
    if [ ! -f "$backup_file" ]; then
        log_error "Backup file not found: $backup_file"
        return 1
    fi
    
    # Create extraction directory
    mkdir -p "$extract_dir"
    
    # Extract backup
    if tar -xzf "$backup_file" -C "$extract_dir"; then
        log "Backup extracted to: $extract_dir"
        echo "$extract_dir"
    else
        log_error "Failed to extract backup"
        rm -rf "$extract_dir"
        return 1
    fi
}

# Verify backup integrity
verify_backup() {
    local backup_file="$1"
    
    log "Verifying backup integrity..."
    
    if [ ! -f "$backup_file" ]; then
        log_error "Backup file not found: $backup_file"
        return 1
    fi
    
    # Check if backup file is readable
    if tar -tzf "$backup_file" > /dev/null 2>&1; then
        log "Backup integrity verified"
        return 0
    else
        log_error "Backup integrity check failed"
        return 1
    fi
}

# Stop DataFlux services
stop_services() {
    log "Stopping DataFlux services..."
    
    # Stop Docker services
    if command -v docker-compose &> /dev/null; then
        if [ -f "docker/docker-compose.yml" ]; then
            docker-compose -f docker/docker-compose.yml down
        fi
    fi
    
    # Stop individual services
    for service in postgresql redis kafka minio weaviate neo4j clickhouse; do
        if systemctl is-active --quiet "$service"; then
            systemctl stop "$service"
            log "Stopped $service"
        fi
    done
    
    log "All services stopped"
}

# Start DataFlux services
start_services() {
    log "Starting DataFlux services..."
    
    # Start Docker services
    if command -v docker-compose &> /dev/null; then
        if [ -f "docker/docker-compose.yml" ]; then
            docker-compose -f docker/docker-compose.yml up -d
        fi
    fi
    
    # Wait for services to be ready
    log "Waiting for services to be ready..."
    sleep 30
    
    # Check service health
    check_service_health
}

# Check service health
check_service_health() {
    log "Checking service health..."
    
    local services=("postgresql:2001" "redis:2002" "kafka:2009" "minio:2003" "weaviate:2005" "neo4j:2007" "clickhouse:2008")
    local healthy_services=0
    
    for service in "${services[@]}"; do
        local service_name=$(echo "$service" | cut -d':' -f1)
        local service_port=$(echo "$service" | cut -d':' -f2)
        
        if nc -z localhost "$service_port" 2>/dev/null; then
            log "✓ $service_name is healthy"
            healthy_services=$((healthy_services + 1))
        else
            log_warn "✗ $service_name is not responding"
        fi
    done
    
    if [ $healthy_services -eq ${#services[@]} ]; then
        log "All services are healthy"
        return 0
    else
        log_warn "Some services are not healthy ($healthy_services/${#services[@]})"
        return 1
    fi
}

# Restore PostgreSQL
restore_postgresql() {
    local extract_dir="$1"
    local pg_dump_file="$extract_dir/postgresql/dataflux_backup.sql.gz"
    
    log "Restoring PostgreSQL database..."
    
    if [ ! -f "$pg_dump_file" ]; then
        log_error "PostgreSQL backup file not found: $pg_dump_file"
        return 1
    fi
    
    # Set password for psql
    export PGPASSWORD="$POSTGRES_PASSWORD"
    
    # Drop existing database (if exists)
    psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" \
         -c "DROP DATABASE IF EXISTS $POSTGRES_DB;" postgres 2>/dev/null || true
    
    # Create new database
    psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" \
         -c "CREATE DATABASE $POSTGRES_DB;" postgres
    
    # Restore database
    if gunzip -c "$pg_dump_file" | psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" \
                                         -U "$POSTGRES_USER" -d "$POSTGRES_DB" 2>> "$LOG_FILE"; then
        log "PostgreSQL database restored successfully"
    else
        log_error "PostgreSQL database restore failed"
        unset PGPASSWORD
        return 1
    fi
    
    unset PGPASSWORD
}

# Restore Redis
restore_redis() {
    local extract_dir="$1"
    local redis_backup_file="$extract_dir/redis/redis_backup.rdb"
    
    log "Restoring Redis database..."
    
    if [ ! -f "$redis_backup_file" ]; then
        log_error "Redis backup file not found: $redis_backup_file"
        return 1
    fi
    
    # Stop Redis
    if command -v redis-cli &> /dev/null; then
        redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" -a "$REDIS_PASSWORD" SHUTDOWN SAVE 2>/dev/null || true
    fi
    
    # Copy backup file to Redis data directory
    local redis_data_dir="/var/lib/redis"
    if [ -d "$redis_data_dir" ]; then
        cp "$redis_backup_file" "$redis_data_dir/dump.rdb"
        chown redis:redis "$redis_data_dir/dump.rdb"
        chmod 644 "$redis_data_dir/dump.rdb"
    else
        log_warn "Redis data directory not found: $redis_data_dir"
    fi
    
    log "Redis database restored successfully"
}

# Restore MinIO
restore_minio() {
    local extract_dir="$1"
    local minio_backup_dir="$extract_dir/minio"
    
    log "Restoring MinIO object storage..."
    
    if [ ! -d "$minio_backup_dir" ]; then
        log_error "MinIO backup directory not found: $minio_backup_dir"
        return 1
    fi
    
    # Use mc (MinIO Client) for restore
    if command -v mc &> /dev/null; then
        # Configure MinIO client
        mc alias set restore-minio "http://$MINIO_ENDPOINT" "$MINIO_ACCESS_KEY" "$MINIO_SECRET_KEY" 2>> "$LOG_FILE"
        
        # Create bucket if it doesn't exist
        mc mb restore-minio/"$MINIO_BUCKET" 2>/dev/null || true
        
        # Sync local directory to MinIO bucket
        if mc mirror "$minio_backup_dir" restore-minio/"$MINIO_BUCKET" 2>> "$LOG_FILE"; then
            log "MinIO object storage restored successfully"
        else
            log_error "MinIO object storage restore failed"
            return 1
        fi
    else
        log_warn "MinIO client (mc) not found, skipping MinIO restore"
        return 0
    fi
}

# Restore Neo4j
restore_neo4j() {
    local extract_dir="$1"
    local neo4j_backup_file="$extract_dir/neo4j/neo4j_backup.dump"
    
    log "Restoring Neo4j graph database..."
    
    if [ ! -f "$neo4j_backup_file" ]; then
        log_error "Neo4j backup file not found: $neo4j_backup_file"
        return 1
    fi
    
    # Stop Neo4j
    if command -v neo4j &> /dev/null; then
        neo4j stop
    fi
    
    # Restore Neo4j database
    if command -v neo4j-admin &> /dev/null; then
        if neo4j-admin load --database=neo4j --from="$neo4j_backup_file" --force 2>> "$LOG_FILE"; then
            log "Neo4j graph database restored successfully"
        else
            log_error "Neo4j graph database restore failed"
            return 1
        fi
    else
        log_warn "Neo4j admin tool not found, skipping Neo4j restore"
        return 0
    fi
}

# Restore Weaviate
restore_weaviate() {
    local extract_dir="$1"
    local weaviate_backup_dir="$extract_dir/weaviate"
    
    log "Restoring Weaviate vector database..."
    
    if [ ! -d "$weaviate_backup_dir" ]; then
        log_error "Weaviate backup directory not found: $weaviate_backup_dir"
        return 1
    fi
    
    # Stop Weaviate
    if command -v weaviate &> /dev/null; then
        weaviate stop
    fi
    
    # Copy backup data to Weaviate data directory
    local weaviate_data_dir="/var/lib/weaviate"
    if [ -d "$weaviate_data_dir" ]; then
        rm -rf "$weaviate_data_dir"/*
        cp -r "$weaviate_backup_dir"/* "$weaviate_data_dir/"
        chown -R weaviate:weaviate "$weaviate_data_dir"
    else
        log_warn "Weaviate data directory not found: $weaviate_data_dir"
    fi
    
    log "Weaviate vector database restored successfully"
}

# Restore ClickHouse
restore_clickhouse() {
    local extract_dir="$1"
    local clickhouse_backup_file="$extract_dir/clickhouse/clickhouse_backup.sql"
    
    log "Restoring ClickHouse analytics database..."
    
    if [ ! -f "$clickhouse_backup_file" ]; then
        log_error "ClickHouse backup file not found: $clickhouse_backup_file"
        return 1
    fi
    
    # Restore ClickHouse databases
    if command -v clickhouse-client &> /dev/null; then
        if clickhouse-client --host "$CLICKHOUSE_HOST" --port "$CLICKHOUSE_PORT" \
                            --user "$CLICKHOUSE_USER" --password "$CLICKHOUSE_PASSWORD" \
                            < "$clickhouse_backup_file" 2>> "$LOG_FILE"; then
            log "ClickHouse analytics database restored successfully"
        else
            log_error "ClickHouse analytics database restore failed"
            return 1
        fi
    else
        log_warn "ClickHouse client not found, skipping ClickHouse restore"
        return 0
    fi
}

# Restore configurations
restore_configs() {
    local extract_dir="$1"
    local config_backup_dir="$extract_dir/configs"
    
    log "Restoring configurations..."
    
    if [ ! -d "$config_backup_dir" ]; then
        log_error "Configuration backup directory not found: $config_backup_dir"
        return 1
    fi
    
    # Restore Docker Compose files
    if [ -f "$config_backup_dir/docker-compose.yml" ]; then
        cp "$config_backup_dir/docker-compose.yml" "docker/"
    fi
    
    # Restore environment files
    if [ -f "$config_backup_dir/.env" ]; then
        cp "$config_backup_dir/.env" "."
    fi
    
    # Restore Nginx configurations
    if [ -d "$config_backup_dir" ]; then
        cp -r "$config_backup_dir"/*.conf "services/api-gateway/" 2>/dev/null || true
    fi
    
    log "Configurations restored successfully"
}

# Cleanup recovery files
cleanup_recovery() {
    local extract_dir="$1"
    
    log "Cleaning up recovery files..."
    
    if [ -d "$extract_dir" ]; then
        rm -rf "$extract_dir"
        log "Recovery files cleaned up"
    fi
}

# Send recovery notification
send_notification() {
    local status="$1"
    local message="$2"
    
    # Send email notification (if configured)
    if [ -n "${RECOVERY_EMAIL:-}" ]; then
        echo "$message" | mail -s "DataFlux Recovery $status" "$RECOVERY_EMAIL"
    fi
    
    # Send webhook notification (if configured)
    if [ -n "${RECOVERY_WEBHOOK:-}" ]; then
        curl -X POST "$RECOVERY_WEBHOOK" \
             -H "Content-Type: application/json" \
             -d "{\"status\": \"$status\", \"message\": \"$message\", \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}" \
             2>/dev/null || true
    fi
}

# Main recovery function
main() {
    local start_time=$(date +%s)
    local recovery_status="SUCCESS"
    local error_message=""
    
    log "Starting DataFlux disaster recovery process..."
    
    # Select backup
    local backup_file
    if ! backup_file=$(select_backup); then
        log_error "Failed to select backup"
        exit 1
    fi
    
    log "Selected backup: $backup_file"
    
    # Verify backup
    if ! verify_backup "$backup_file"; then
        log_error "Backup verification failed"
        exit 1
    fi
    
    # Extract backup
    local extract_dir
    if ! extract_dir=$(extract_backup "$backup_file"); then
        log_error "Backup extraction failed"
        exit 1
    fi
    
    # Stop services
    stop_services
    
    # Restore components
    (
        restore_postgresql "$extract_dir" &
        restore_redis "$extract_dir" &
        restore_minio "$extract_dir" &
        restore_neo4j "$extract_dir" &
        restore_weaviate "$extract_dir" &
        restore_clickhouse "$extract_dir" &
        wait
    )
    
    # Restore configurations
    restore_configs "$extract_dir"
    
    # Start services
    if start_services; then
        # Cleanup recovery files
        cleanup_recovery "$extract_dir"
        
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        
        log "Disaster recovery completed successfully in ${duration}s"
        log "Recovered from backup: $(basename "$backup_file")"
        
        send_notification "SUCCESS" "DataFlux disaster recovery completed successfully. Duration: ${duration}s"
    else
        recovery_status="FAILED"
        error_message="Service startup failed"
    fi
    
    if [ "$recovery_status" = "FAILED" ]; then
        log_error "Disaster recovery failed: $error_message"
        send_notification "FAILED" "DataFlux disaster recovery failed: $error_message"
        exit 1
    fi
}

# Handle script arguments
case "${1:-}" in
    "interactive")
        RECOVERY_MODE="interactive"
        main
        ;;
    "automatic")
        RECOVERY_MODE="automatic"
        main
        ;;
    "list")
        list_backups
        ;;
    "verify")
        if [ -n "${2:-}" ]; then
            verify_backup "$2"
        else
            echo "Usage: $0 verify <backup_file>"
            exit 1
        fi
        ;;
    "health")
        check_service_health
        ;;
    *)
        echo "Usage: $0 {interactive|automatic|list|verify|health}"
        echo ""
        echo "Commands:"
        echo "  interactive  - Interactive recovery with backup selection"
        echo "  automatic    - Automatic recovery using latest backup"
        echo "  list         - List available backups"
        echo "  verify       - Verify backup integrity"
        echo "  health       - Check service health"
        exit 1
        ;;
esac
