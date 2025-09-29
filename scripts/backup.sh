#!/bin/bash
# DataFlux Automated Backup System
# Comprehensive backup solution for all DataFlux components

set -euo pipefail

# Configuration
BACKUP_ROOT="/opt/dataflux/backups"
LOG_FILE="/var/log/dataflux/backup.log"
RETENTION_DAYS=30
COMPRESSION_LEVEL=6
PARALLEL_JOBS=4

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

# Create backup directory structure
create_backup_dirs() {
    local timestamp=$(date '+%Y%m%d_%H%M%S')
    BACKUP_DIR="$BACKUP_ROOT/$timestamp"
    
    mkdir -p "$BACKUP_DIR"/{postgresql,redis,minio,neo4j,weaviate,clickhouse,configs,logs}
    
    log "Created backup directory: $BACKUP_DIR"
}

# PostgreSQL backup
backup_postgresql() {
    log "Starting PostgreSQL backup..."
    
    local pg_dump_file="$BACKUP_DIR/postgresql/dataflux_backup.sql"
    local pg_dump_compressed="$BACKUP_DIR/postgresql/dataflux_backup.sql.gz"
    
    # Set password for pg_dump
    export PGPASSWORD="$POSTGRES_PASSWORD"
    
    # Create database dump
    if pg_dump -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" \
               -d "$POSTGRES_DB" --verbose --no-password --format=plain \
               --exclude-table-data=audit_logs \
               --exclude-table-data=performance_metrics \
               > "$pg_dump_file" 2>> "$LOG_FILE"; then
        
        # Compress the dump
        gzip -"$COMPRESSION_LEVEL" "$pg_dump_file"
        
        # Get backup size
        local backup_size=$(du -h "$pg_dump_compressed" | cut -f1)
        log "PostgreSQL backup completed: $backup_size"
        
        # Verify backup integrity
        if gzip -t "$pg_dump_compressed"; then
            log "PostgreSQL backup integrity verified"
        else
            log_error "PostgreSQL backup integrity check failed"
            return 1
        fi
    else
        log_error "PostgreSQL backup failed"
        return 1
    fi
    
    # Backup database configuration
    pg_dump -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" \
            -d "$POSTGRES_DB" --schema-only --no-password \
            > "$BACKUP_DIR/postgresql/schema.sql" 2>> "$LOG_FILE"
    
    # Backup database statistics
    psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" \
         -d "$POSTGRES_DB" -c "SELECT * FROM pg_stat_database WHERE datname = '$POSTGRES_DB';" \
         > "$BACKUP_DIR/postgresql/database_stats.txt" 2>> "$LOG_FILE"
    
    unset PGPASSWORD
}

# Redis backup
backup_redis() {
    log "Starting Redis backup..."
    
    local redis_backup_file="$BACKUP_DIR/redis/redis_backup.rdb"
    
    # Create Redis dump
    if redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" -a "$REDIS_PASSWORD" \
                 --rdb "$redis_backup_file" 2>> "$LOG_FILE"; then
        
        # Get backup size
        local backup_size=$(du -h "$redis_backup_file" | cut -f1)
        log "Redis backup completed: $backup_size"
        
        # Verify backup integrity
        if file "$redis_backup_file" | grep -q "Redis"; then
            log "Redis backup integrity verified"
        else
            log_error "Redis backup integrity check failed"
            return 1
        fi
    else
        log_error "Redis backup failed"
        return 1
    fi
    
    # Backup Redis configuration
    redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" -a "$REDIS_PASSWORD" \
              CONFIG GET "*" > "$BACKUP_DIR/redis/redis_config.txt" 2>> "$LOG_FILE"
    
    # Backup Redis info
    redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" -a "$REDIS_PASSWORD" \
              INFO > "$BACKUP_DIR/redis/redis_info.txt" 2>> "$LOG_FILE"
}

# MinIO backup
backup_minio() {
    log "Starting MinIO backup..."
    
    local minio_backup_dir="$BACKUP_DIR/minio"
    
    # Create MinIO backup directory
    mkdir -p "$minio_backup_dir"
    
    # Use mc (MinIO Client) for backup
    if command -v mc &> /dev/null; then
        # Configure MinIO client
        mc alias set backup-minio "http://$MINIO_ENDPOINT" "$MINIO_ACCESS_KEY" "$MINIO_SECRET_KEY" 2>> "$LOG_FILE"
        
        # Sync MinIO bucket to local directory
        if mc mirror backup-minio/"$MINIO_BUCKET" "$minio_backup_dir" 2>> "$LOG_FILE"; then
            local backup_size=$(du -sh "$minio_backup_dir" | cut -f1)
            log "MinIO backup completed: $backup_size"
        else
            log_error "MinIO backup failed"
            return 1
        fi
    else
        log_warn "MinIO client (mc) not found, skipping MinIO backup"
        return 0
    fi
}

# Neo4j backup
backup_neo4j() {
    log "Starting Neo4j backup..."
    
    local neo4j_backup_file="$BACKUP_DIR/neo4j/neo4j_backup.dump"
    
    # Create Neo4j dump
    if command -v neo4j-admin &> /dev/null; then
        if neo4j-admin dump --database=neo4j --to="$neo4j_backup_file" 2>> "$LOG_FILE"; then
            local backup_size=$(du -h "$neo4j_backup_file" | cut -f1)
            log "Neo4j backup completed: $backup_size"
        else
            log_error "Neo4j backup failed"
            return 1
        fi
    else
        log_warn "Neo4j admin tool not found, skipping Neo4j backup"
        return 0
    fi
    
    # Backup Neo4j configuration
    if [ -d "/var/lib/neo4j/conf" ]; then
        cp -r /var/lib/neo4j/conf "$BACKUP_DIR/neo4j/"
    fi
}

# Weaviate backup
backup_weaviate() {
    log "Starting Weaviate backup..."
    
    local weaviate_backup_dir="$BACKUP_DIR/weaviate"
    
    # Create Weaviate backup directory
    mkdir -p "$weaviate_backup_dir"
    
    # Backup Weaviate data directory
    if [ -d "/var/lib/weaviate" ]; then
        if cp -r /var/lib/weaviate/* "$weaviate_backup_dir/" 2>> "$LOG_FILE"; then
            local backup_size=$(du -sh "$weaviate_backup_dir" | cut -f1)
            log "Weaviate backup completed: $backup_size"
        else
            log_error "Weaviate backup failed"
            return 1
        fi
    else
        log_warn "Weaviate data directory not found, skipping Weaviate backup"
        return 0
    fi
}

# ClickHouse backup
backup_clickhouse() {
    log "Starting ClickHouse backup..."
    
    local clickhouse_backup_file="$BACKUP_DIR/clickhouse/clickhouse_backup.sql"
    
    # Create ClickHouse dump
    if command -v clickhouse-client &> /dev/null; then
        if clickhouse-client --host "$CLICKHOUSE_HOST" --port "$CLICKHOUSE_PORT" \
                            --user "$CLICKHOUSE_USER" --password "$CLICKHOUSE_PASSWORD" \
                            --query "SHOW DATABASES" > "$BACKUP_DIR/clickhouse/databases.txt" 2>> "$LOG_FILE"; then
            
            # Backup each database
            while IFS= read -r database; do
                if [ "$database" != "system" ] && [ "$database" != "information_schema" ]; then
                    clickhouse-client --host "$CLICKHOUSE_HOST" --port "$CLICKHOUSE_PORT" \
                                     --user "$CLICKHOUSE_USER" --password "$CLICKHOUSE_PASSWORD" \
                                     --query "SHOW CREATE DATABASE $database" >> "$clickhouse_backup_file" 2>> "$LOG_FILE"
                fi
            done < "$BACKUP_DIR/clickhouse/databases.txt"
            
            local backup_size=$(du -h "$clickhouse_backup_file" | cut -f1)
            log "ClickHouse backup completed: $backup_size"
        else
            log_error "ClickHouse backup failed"
            return 1
        fi
    else
        log_warn "ClickHouse client not found, skipping ClickHouse backup"
        return 0
    fi
}

# Configuration backup
backup_configs() {
    log "Starting configuration backup..."
    
    local config_backup_dir="$BACKUP_DIR/configs"
    
    # Backup Docker Compose files
    if [ -f "docker/docker-compose.yml" ]; then
        cp docker/docker-compose.yml "$config_backup_dir/"
    fi
    
    # Backup environment files
    if [ -f ".env" ]; then
        cp .env "$config_backup_dir/"
    fi
    
    # Backup Nginx configurations
    if [ -d "services/api-gateway" ]; then
        cp -r services/api-gateway/*.conf "$config_backup_dir/" 2>/dev/null || true
    fi
    
    # Backup service configurations
    for service in services/*/; do
        if [ -d "$service" ]; then
            service_name=$(basename "$service")
            mkdir -p "$config_backup_dir/$service_name"
            cp -r "$service"*.conf "$service"*.yml "$service"*.yaml "$config_backup_dir/$service_name/" 2>/dev/null || true
        fi
    done
    
    log "Configuration backup completed"
}

# Log backup
backup_logs() {
    log "Starting log backup..."
    
    local log_backup_dir="$BACKUP_DIR/logs"
    
    # Backup application logs
    if [ -d "/var/log/dataflux" ]; then
        cp -r /var/log/dataflux/* "$log_backup_dir/" 2>/dev/null || true
    fi
    
    # Backup Docker logs
    if command -v docker &> /dev/null; then
        docker logs dataflux-postgres-1 > "$log_backup_dir/postgres.log" 2>/dev/null || true
        docker logs dataflux-redis-1 > "$log_backup_dir/redis.log" 2>/dev/null || true
        docker logs dataflux-kafka-1 > "$log_backup_dir/kafka.log" 2>/dev/null || true
    fi
    
    log "Log backup completed"
}

# Create backup manifest
create_backup_manifest() {
    log "Creating backup manifest..."
    
    local manifest_file="$BACKUP_DIR/backup_manifest.json"
    
    cat > "$manifest_file" << EOF
{
    "backup_id": "$(basename "$BACKUP_DIR")",
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "backup_type": "full",
    "components": {
        "postgresql": {
            "enabled": true,
            "backup_file": "postgresql/dataflux_backup.sql.gz",
            "size": "$(du -h "$BACKUP_DIR/postgresql/dataflux_backup.sql.gz" 2>/dev/null | cut -f1 || echo "N/A")"
        },
        "redis": {
            "enabled": true,
            "backup_file": "redis/redis_backup.rdb",
            "size": "$(du -h "$BACKUP_DIR/redis/redis_backup.rdb" 2>/dev/null | cut -f1 || echo "N/A")"
        },
        "minio": {
            "enabled": true,
            "backup_dir": "minio/",
            "size": "$(du -sh "$BACKUP_DIR/minio" 2>/dev/null | cut -f1 || echo "N/A")"
        },
        "neo4j": {
            "enabled": true,
            "backup_file": "neo4j/neo4j_backup.dump",
            "size": "$(du -h "$BACKUP_DIR/neo4j/neo4j_backup.dump" 2>/dev/null | cut -f1 || echo "N/A")"
        },
        "weaviate": {
            "enabled": true,
            "backup_dir": "weaviate/",
            "size": "$(du -sh "$BACKUP_DIR/weaviate" 2>/dev/null | cut -f1 || echo "N/A")"
        },
        "clickhouse": {
            "enabled": true,
            "backup_file": "clickhouse/clickhouse_backup.sql",
            "size": "$(du -h "$BACKUP_DIR/clickhouse/clickhouse_backup.sql" 2>/dev/null | cut -f1 || echo "N/A")"
        },
        "configs": {
            "enabled": true,
            "backup_dir": "configs/",
            "size": "$(du -sh "$BACKUP_DIR/configs" 2>/dev/null | cut -f1 || echo "N/A")"
        },
        "logs": {
            "enabled": true,
            "backup_dir": "logs/",
            "size": "$(du -sh "$BACKUP_DIR/logs" 2>/dev/null | cut -f1 || echo "N/A")"
        }
    },
    "total_size": "$(du -sh "$BACKUP_DIR" | cut -f1)",
    "retention_days": $RETENTION_DAYS,
    "compression_level": $COMPRESSION_LEVEL
}
EOF
    
    log "Backup manifest created: $manifest_file"
}

# Compress backup
compress_backup() {
    log "Compressing backup..."
    
    local compressed_backup="$BACKUP_DIR.tar.gz"
    
    if tar -czf "$compressed_backup" -C "$BACKUP_ROOT" "$(basename "$BACKUP_DIR")" 2>> "$LOG_FILE"; then
        local compressed_size=$(du -h "$compressed_backup" | cut -f1)
        log "Backup compressed: $compressed_size"
        
        # Remove uncompressed directory
        rm -rf "$BACKUP_DIR"
        
        # Update manifest path
        local manifest_file="$compressed_backup.manifest"
        mv "$BACKUP_DIR/backup_manifest.json" "$manifest_file"
        
        log "Backup compression completed"
    else
        log_error "Backup compression failed"
        return 1
    fi
}

# Cleanup old backups
cleanup_old_backups() {
    log "Cleaning up old backups..."
    
    local deleted_count=0
    
    # Find and delete old backups
    while IFS= read -r -d '' backup_file; do
        if [ -f "$backup_file" ]; then
            rm -f "$backup_file"
            deleted_count=$((deleted_count + 1))
        fi
    done < <(find "$BACKUP_ROOT" -name "*.tar.gz" -mtime +$RETENTION_DAYS -print0)
    
    log "Cleaned up $deleted_count old backups"
}

# Verify backup integrity
verify_backup() {
    log "Verifying backup integrity..."
    
    local backup_file="$BACKUP_DIR.tar.gz"
    local manifest_file="$backup_file.manifest"
    
    if [ -f "$backup_file" ] && [ -f "$manifest_file" ]; then
        # Check if backup file is readable
        if tar -tzf "$backup_file" > /dev/null 2>&1; then
            log "Backup integrity verified"
            return 0
        else
            log_error "Backup integrity check failed"
            return 1
        fi
    else
        log_error "Backup files not found"
        return 1
    fi
}

# Send backup notification
send_notification() {
    local status="$1"
    local message="$2"
    
    # Send email notification (if configured)
    if [ -n "${BACKUP_EMAIL:-}" ]; then
        echo "$message" | mail -s "DataFlux Backup $status" "$BACKUP_EMAIL"
    fi
    
    # Send webhook notification (if configured)
    if [ -n "${BACKUP_WEBHOOK:-}" ]; then
        curl -X POST "$BACKUP_WEBHOOK" \
             -H "Content-Type: application/json" \
             -d "{\"status\": \"$status\", \"message\": \"$message\", \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}" \
             2>/dev/null || true
    fi
}

# Main backup function
main() {
    local start_time=$(date +%s)
    local backup_status="SUCCESS"
    local error_message=""
    
    log "Starting DataFlux backup process..."
    
    # Create backup directories
    create_backup_dirs
    
    # Run backups in parallel where possible
    (
        backup_postgresql &
        backup_redis &
        backup_minio &
        backup_neo4j &
        backup_weaviate &
        backup_clickhouse &
        wait
    )
    
    # Run sequential backups
    backup_configs
    backup_logs
    
    # Create manifest
    create_backup_manifest
    
    # Compress backup
    if compress_backup; then
        # Verify backup
        if verify_backup; then
            # Cleanup old backups
            cleanup_old_backups
            
            local end_time=$(date +%s)
            local duration=$((end_time - start_time))
            local backup_size=$(du -h "$BACKUP_DIR.tar.gz" | cut -f1)
            
            log "Backup completed successfully in ${duration}s"
            log "Backup size: $backup_size"
            log "Backup location: $BACKUP_DIR.tar.gz"
            
            send_notification "SUCCESS" "DataFlux backup completed successfully. Size: $backup_size, Duration: ${duration}s"
        else
            backup_status="FAILED"
            error_message="Backup integrity verification failed"
        fi
    else
        backup_status="FAILED"
        error_message="Backup compression failed"
    fi
    
    if [ "$backup_status" = "FAILED" ]; then
        log_error "Backup failed: $error_message"
        send_notification "FAILED" "DataFlux backup failed: $error_message"
        exit 1
    fi
}

# Handle script arguments
case "${1:-}" in
    "full")
        main
        ;;
    "postgresql")
        create_backup_dirs
        backup_postgresql
        ;;
    "redis")
        create_backup_dirs
        backup_redis
        ;;
    "minio")
        create_backup_dirs
        backup_minio
        ;;
    "neo4j")
        create_backup_dirs
        backup_neo4j
        ;;
    "weaviate")
        create_backup_dirs
        backup_weaviate
        ;;
    "clickhouse")
        create_backup_dirs
        backup_clickhouse
        ;;
    "cleanup")
        cleanup_old_backups
        ;;
    "verify")
        verify_backup
        ;;
    *)
        echo "Usage: $0 {full|postgresql|redis|minio|neo4j|weaviate|clickhouse|cleanup|verify}"
        echo ""
        echo "Commands:"
        echo "  full        - Full backup of all components"
        echo "  postgresql  - Backup PostgreSQL database only"
        echo "  redis       - Backup Redis database only"
        echo "  minio       - Backup MinIO object storage only"
        echo "  neo4j       - Backup Neo4j graph database only"
        echo "  weaviate    - Backup Weaviate vector database only"
        echo "  clickhouse  - Backup ClickHouse analytics database only"
        echo "  cleanup     - Clean up old backups"
        echo "  verify      - Verify backup integrity"
        exit 1
        ;;
esac
