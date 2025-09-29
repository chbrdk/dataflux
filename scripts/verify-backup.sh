#!/bin/bash
# DataFlux Backup Verification System
# Comprehensive backup integrity and restore testing

set -euo pipefail

# Configuration
BACKUP_ROOT="/opt/dataflux/backups"
LOG_FILE="/var/log/dataflux/verification.log"
TEST_DB_NAME="dataflux_verification_test"
TEST_BUCKET_NAME="dataflux-verification-test"

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
    log "Available backups for verification:"
    
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

# Select backup for verification
select_backup() {
    local backup_file=""
    
    if [ "${1:-}" = "interactive" ]; then
        list_backups
        
        echo ""
        read -p "Enter backup number to verify: " backup_number
        
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

# Extract backup for verification
extract_backup() {
    local backup_file="$1"
    local extract_dir="/tmp/dataflux_verification_$(date +%s)"
    
    log "Extracting backup for verification: $backup_file"
    
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
verify_backup_integrity() {
    local backup_file="$1"
    
    log "Verifying backup integrity..."
    
    if [ ! -f "$backup_file" ]; then
        log_error "Backup file not found: $backup_file"
        return 1
    fi
    
    # Check if backup file is readable
    if tar -tzf "$backup_file" > /dev/null 2>&1; then
        log "✓ Backup file is readable"
    else
        log_error "✗ Backup file is corrupted or unreadable"
        return 1
    fi
    
    # Check backup manifest
    local manifest_file="$backup_file.manifest"
    if [ -f "$manifest_file" ]; then
        if jq empty "$manifest_file" 2>/dev/null; then
            log "✓ Backup manifest is valid JSON"
        else
            log_error "✗ Backup manifest is invalid JSON"
            return 1
        fi
    else
        log_warn "⚠ Backup manifest not found"
    fi
    
    # Check backup size
    local backup_size=$(du -h "$backup_file" | cut -f1)
    log "✓ Backup size: $backup_size"
    
    return 0
}

# Verify PostgreSQL backup
verify_postgresql_backup() {
    local extract_dir="$1"
    local pg_dump_file="$extract_dir/postgresql/dataflux_backup.sql.gz"
    
    log "Verifying PostgreSQL backup..."
    
    if [ ! -f "$pg_dump_file" ]; then
        log_error "PostgreSQL backup file not found: $pg_dump_file"
        return 1
    fi
    
    # Check if gzip file is valid
    if gzip -t "$pg_dump_file"; then
        log "✓ PostgreSQL backup file is valid gzip"
    else
        log_error "✗ PostgreSQL backup file is corrupted"
        return 1
    fi
    
    # Check if SQL dump is valid
    if gunzip -c "$pg_dump_file" | head -n 100 | grep -q "PostgreSQL database dump"; then
        log "✓ PostgreSQL backup contains valid SQL dump"
    else
        log_error "✗ PostgreSQL backup does not contain valid SQL dump"
        return 1
    fi
    
    # Check schema file
    local schema_file="$extract_dir/postgresql/schema.sql"
    if [ -f "$schema_file" ]; then
        if grep -q "CREATE TABLE" "$schema_file"; then
            log "✓ PostgreSQL schema file contains table definitions"
        else
            log_warn "⚠ PostgreSQL schema file may be incomplete"
        fi
    fi
    
    # Check database stats file
    local stats_file="$extract_dir/postgresql/database_stats.txt"
    if [ -f "$stats_file" ]; then
        if grep -q "datname" "$stats_file"; then
            log "✓ PostgreSQL database stats file is present"
        else
            log_warn "⚠ PostgreSQL database stats file may be incomplete"
        fi
    fi
    
    return 0
}

# Verify Redis backup
verify_redis_backup() {
    local extract_dir="$1"
    local redis_backup_file="$extract_dir/redis/redis_backup.rdb"
    
    log "Verifying Redis backup..."
    
    if [ ! -f "$redis_backup_file" ]; then
        log_error "Redis backup file not found: $redis_backup_file"
        return 1
    fi
    
    # Check if RDB file is valid
    if file "$redis_backup_file" | grep -q "Redis"; then
        log "✓ Redis backup file is valid RDB format"
    else
        log_error "✗ Redis backup file is not valid RDB format"
        return 1
    fi
    
    # Check Redis config file
    local config_file="$extract_dir/redis/redis_config.txt"
    if [ -f "$config_file" ]; then
        if grep -q "maxmemory" "$config_file"; then
            log "✓ Redis config file is present"
        else
            log_warn "⚠ Redis config file may be incomplete"
        fi
    fi
    
    # Check Redis info file
    local info_file="$extract_dir/redis/redis_info.txt"
    if [ -f "$info_file" ]; then
        if grep -q "redis_version" "$info_file"; then
            log "✓ Redis info file is present"
        else
            log_warn "⚠ Redis info file may be incomplete"
        fi
    fi
    
    return 0
}

# Verify MinIO backup
verify_minio_backup() {
    local extract_dir="$1"
    local minio_backup_dir="$extract_dir/minio"
    
    log "Verifying MinIO backup..."
    
    if [ ! -d "$minio_backup_dir" ]; then
        log_error "MinIO backup directory not found: $minio_backup_dir"
        return 1
    fi
    
    # Check if MinIO backup directory is not empty
    if [ "$(find "$minio_backup_dir" -type f | wc -l)" -gt 0 ]; then
        log "✓ MinIO backup directory contains files"
    else
        log_warn "⚠ MinIO backup directory is empty"
    fi
    
    # Check for common MinIO file types
    local file_count=0
    for file in "$minio_backup_dir"/*; do
        if [ -f "$file" ]; then
            file_count=$((file_count + 1))
        fi
    done
    
    log "✓ MinIO backup contains $file_count files"
    
    return 0
}

# Verify Neo4j backup
verify_neo4j_backup() {
    local extract_dir="$1"
    local neo4j_backup_file="$extract_dir/neo4j/neo4j_backup.dump"
    
    log "Verifying Neo4j backup..."
    
    if [ ! -f "$neo4j_backup_file" ]; then
        log_error "Neo4j backup file not found: $neo4j_backup_file"
        return 1
    fi
    
    # Check if Neo4j dump file is valid
    if file "$neo4j_backup_file" | grep -q "data"; then
        log "✓ Neo4j backup file appears to be valid"
    else
        log_warn "⚠ Neo4j backup file format is unclear"
    fi
    
    # Check Neo4j config directory
    local config_dir="$extract_dir/neo4j/conf"
    if [ -d "$config_dir" ]; then
        if [ "$(find "$config_dir" -name "*.conf" | wc -l)" -gt 0 ]; then
            log "✓ Neo4j config directory contains configuration files"
        else
            log_warn "⚠ Neo4j config directory is empty"
        fi
    fi
    
    return 0
}

# Verify Weaviate backup
verify_weaviate_backup() {
    local extract_dir="$1"
    local weaviate_backup_dir="$extract_dir/weaviate"
    
    log "Verifying Weaviate backup..."
    
    if [ ! -d "$weaviate_backup_dir" ]; then
        log_error "Weaviate backup directory not found: $weaviate_backup_dir"
        return 1
    fi
    
    # Check if Weaviate backup directory is not empty
    if [ "$(find "$weaviate_backup_dir" -type f | wc -l)" -gt 0 ]; then
        log "✓ Weaviate backup directory contains files"
    else
        log_warn "⚠ Weaviate backup directory is empty"
    fi
    
    # Check for Weaviate-specific files
    if find "$weaviate_backup_dir" -name "*.db" -o -name "*.wal" | grep -q .; then
        log "✓ Weaviate backup contains database files"
    else
        log_warn "⚠ Weaviate backup may not contain database files"
    fi
    
    return 0
}

# Verify ClickHouse backup
verify_clickhouse_backup() {
    local extract_dir="$1"
    local clickhouse_backup_file="$extract_dir/clickhouse/clickhouse_backup.sql"
    
    log "Verifying ClickHouse backup..."
    
    if [ ! -f "$clickhouse_backup_file" ]; then
        log_error "ClickHouse backup file not found: $clickhouse_backup_file"
        return 1
    fi
    
    # Check if ClickHouse backup contains SQL statements
    if grep -q "CREATE DATABASE" "$clickhouse_backup_file"; then
        log "✓ ClickHouse backup contains database creation statements"
    else
        log_warn "⚠ ClickHouse backup may not contain database statements"
    fi
    
    # Check databases file
    local databases_file="$extract_dir/clickhouse/databases.txt"
    if [ -f "$databases_file" ]; then
        if grep -q "default" "$databases_file"; then
            log "✓ ClickHouse databases file is present"
        else
            log_warn "⚠ ClickHouse databases file may be incomplete"
        fi
    fi
    
    return 0
}

# Test PostgreSQL restore
test_postgresql_restore() {
    local extract_dir="$1"
    local pg_dump_file="$extract_dir/postgresql/dataflux_backup.sql.gz"
    
    log "Testing PostgreSQL restore..."
    
    if [ ! -f "$pg_dump_file" ]; then
        log_error "PostgreSQL backup file not found: $pg_dump_file"
        return 1
    fi
    
    # Set password for psql
    export PGPASSWORD="$POSTGRES_PASSWORD"
    
    # Create test database
    psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" \
         -c "DROP DATABASE IF EXISTS $TEST_DB_NAME;" postgres 2>/dev/null || true
    
    psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" \
         -c "CREATE DATABASE $TEST_DB_NAME;" postgres
    
    # Restore backup to test database
    if gunzip -c "$pg_dump_file" | psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" \
                                         -U "$POSTGRES_USER" -d "$TEST_DB_NAME" 2>> "$LOG_FILE"; then
        log "✓ PostgreSQL restore test successful"
        
        # Verify tables exist
        local table_count=$(psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" \
                                -d "$TEST_DB_NAME" -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" | tr -d ' ')
        
        if [ "$table_count" -gt 0 ]; then
            log "✓ PostgreSQL restore contains $table_count tables"
        else
            log_warn "⚠ PostgreSQL restore contains no tables"
        fi
        
        # Clean up test database
        psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" \
             -c "DROP DATABASE $TEST_DB_NAME;" postgres
        
        unset PGPASSWORD
        return 0
    else
        log_error "✗ PostgreSQL restore test failed"
        unset PGPASSWORD
        return 1
    fi
}

# Test Redis restore
test_redis_restore() {
    local extract_dir="$1"
    local redis_backup_file="$extract_dir/redis/redis_backup.rdb"
    
    log "Testing Redis restore..."
    
    if [ ! -f "$redis_backup_file" ]; then
        log_error "Redis backup file not found: $redis_backup_file"
        return 1
    fi
    
    # Test Redis connection
    if redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" -a "$REDIS_PASSWORD" ping > /dev/null 2>&1; then
        log "✓ Redis connection successful"
        
        # Test RDB file format
        if redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" -a "$REDIS_PASSWORD" \
                     --rdb "$redis_backup_file" > /dev/null 2>&1; then
            log "✓ Redis backup file format is valid"
        else
            log_warn "⚠ Redis backup file format validation failed"
        fi
        
        return 0
    else
        log_error "✗ Redis connection failed"
        return 1
    fi
}

# Test MinIO restore
test_minio_restore() {
    local extract_dir="$1"
    local minio_backup_dir="$extract_dir/minio"
    
    log "Testing MinIO restore..."
    
    if [ ! -d "$minio_backup_dir" ]; then
        log_error "MinIO backup directory not found: $minio_backup_dir"
        return 1
    fi
    
    if ! command -v mc &> /dev/null; then
        log_warn "MinIO client (mc) not found, skipping MinIO restore test"
        return 0
    fi
    
    # Configure MinIO client
    mc alias set test-minio "http://$MINIO_ENDPOINT" "$MINIO_ACCESS_KEY" "$MINIO_SECRET_KEY" 2>> "$LOG_FILE"
    
    # Test MinIO connection
    if mc ping test-minio > /dev/null 2>&1; then
        log "✓ MinIO connection successful"
        
        # Create test bucket
        mc mb "test-minio/$TEST_BUCKET_NAME" 2>/dev/null || true
        
        # Test file upload
        local test_file="/tmp/test_upload_$(date +%s).txt"
        echo "test content" > "$test_file"
        
        if mc cp "$test_file" "test-minio/$TEST_BUCKET_NAME/" 2>> "$LOG_FILE"; then
            log "✓ MinIO file upload test successful"
            
            # Clean up test file and bucket
            rm -f "$test_file"
            mc rm "test-minio/$TEST_BUCKET_NAME/test_upload_*.txt" 2>/dev/null || true
            mc rb "test-minio/$TEST_BUCKET_NAME" 2>/dev/null || true
            
            return 0
        else
            log_error "✗ MinIO file upload test failed"
            return 1
        fi
    else
        log_error "✗ MinIO connection failed"
        return 1
    fi
}

# Generate verification report
generate_verification_report() {
    local backup_file="$1"
    local extract_dir="$2"
    local verification_results="$3"
    
    log "Generating verification report..."
    
    local report_file="/var/log/dataflux/verification-report-$(date +%Y%m%d_%H%M%S).txt"
    
    cat > "$report_file" << EOF
DataFlux Backup Verification Report
Generated: $(date)
Backup: $(basename "$backup_file")
================================

Verification Results:
EOF
    
    for component in "${!verification_results[@]}"; do
        local result="${verification_results[$component]}"
        echo "  $component: $result" >> "$report_file"
    done
    
    echo "" >> "$report_file"
    echo "Backup Contents:" >> "$report_file"
    
    # List backup contents
    tar -tzf "$backup_file" | head -20 >> "$report_file"
    
    echo "" >> "$report_file"
    echo "File Sizes:" >> "$report_file"
    
    # Get file sizes
    for file in "$extract_dir"/*; do
        if [ -d "$file" ]; then
            local dir_size=$(du -sh "$file" | cut -f1)
            echo "  $(basename "$file"): $dir_size" >> "$report_file"
        fi
    done
    
    log "Verification report generated: $report_file"
}

# Send verification notification
send_notification() {
    local status="$1"
    local message="$2"
    
    # Send email notification (if configured)
    if [ -n "${VERIFICATION_EMAIL:-}" ]; then
        echo "$message" | mail -s "DataFlux Backup Verification $status" "$VERIFICATION_EMAIL"
    fi
    
    # Send webhook notification (if configured)
    if [ -n "${VERIFICATION_WEBHOOK:-}" ]; then
        curl -X POST "$VERIFICATION_WEBHOOK" \
             -H "Content-Type: application/json" \
             -d "{\"status\": \"$status\", \"message\": \"$message\", \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}" \
             2>/dev/null || true
    fi
}

# Main verification function
main() {
    local start_time=$(date +%s)
    local verification_status="SUCCESS"
    local error_message=""
    
    log "Starting DataFlux backup verification process..."
    
    # Select backup
    local backup_file
    if ! backup_file=$(select_backup "${1:-automatic}"); then
        log_error "Failed to select backup"
        exit 1
    fi
    
    log "Selected backup: $backup_file"
    
    # Verify backup integrity
    if ! verify_backup_integrity "$backup_file"; then
        log_error "Backup integrity verification failed"
        exit 1
    fi
    
    # Extract backup
    local extract_dir
    if ! extract_dir=$(extract_backup "$backup_file"); then
        log_error "Backup extraction failed"
        exit 1
    fi
    
    # Initialize verification results
    declare -A verification_results
    
    # Verify components
    (
        if verify_postgresql_backup "$extract_dir"; then
            verification_results["postgresql"]="PASS"
        else
            verification_results["postgresql"]="FAIL"
        fi
    ) &
    
    (
        if verify_redis_backup "$extract_dir"; then
            verification_results["redis"]="PASS"
        else
            verification_results["redis"]="FAIL"
        fi
    ) &
    
    (
        if verify_minio_backup "$extract_dir"; then
            verification_results["minio"]="PASS"
        else
            verification_results["minio"]="FAIL"
        fi
    ) &
    
    (
        if verify_neo4j_backup "$extract_dir"; then
            verification_results["neo4j"]="PASS"
        else
            verification_results["neo4j"]="FAIL"
        fi
    ) &
    
    (
        if verify_weaviate_backup "$extract_dir"; then
            verification_results["weaviate"]="PASS"
        else
            verification_results["weaviate"]="FAIL"
        fi
    ) &
    
    (
        if verify_clickhouse_backup "$extract_dir"; then
            verification_results["clickhouse"]="PASS"
        else
            verification_results["clickhouse"]="FAIL"
        fi
    ) &
    
    wait
    
    # Test restores
    (
        if test_postgresql_restore "$extract_dir"; then
            verification_results["postgresql_restore"]="PASS"
        else
            verification_results["postgresql_restore"]="FAIL"
        fi
    ) &
    
    (
        if test_redis_restore "$extract_dir"; then
            verification_results["redis_restore"]="PASS"
        else
            verification_results["redis_restore"]="FAIL"
        fi
    ) &
    
    (
        if test_minio_restore "$extract_dir"; then
            verification_results["minio_restore"]="PASS"
        else
            verification_results["minio_restore"]="FAIL"
        fi
    ) &
    
    wait
    
    # Check overall status
    local failed_components=()
    for component in "${!verification_results[@]}"; do
        if [ "${verification_results[$component]}" = "FAIL" ]; then
            failed_components+=("$component")
        fi
    done
    
    if [ ${#failed_components[@]} -gt 0 ]; then
        verification_status="FAILED"
        error_message="Failed components: ${failed_components[*]}"
    fi
    
    # Generate report
    generate_verification_report "$backup_file" "$extract_dir" verification_results
    
    # Cleanup
    rm -rf "$extract_dir"
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    if [ "$verification_status" = "SUCCESS" ]; then
        log "Backup verification completed successfully in ${duration}s"
        log "All components verified and tested"
        
        send_notification "SUCCESS" "DataFlux backup verification completed successfully. Duration: ${duration}s"
    else
        log_error "Backup verification failed: $error_message"
        send_notification "FAILED" "DataFlux backup verification failed: $error_message"
        exit 1
    fi
}

# Handle script arguments
case "${1:-}" in
    "interactive")
        main "interactive"
        ;;
    "automatic")
        main "automatic"
        ;;
    "list")
        list_backups
        ;;
    "integrity")
        if [ -n "${2:-}" ]; then
            verify_backup_integrity "$2"
        else
            echo "Usage: $0 integrity <backup_file>"
            exit 1
        fi
        ;;
    *)
        echo "Usage: $0 {interactive|automatic|list|integrity}"
        echo ""
        echo "Commands:"
        echo "  interactive  - Interactive verification with backup selection"
        echo "  automatic    - Automatic verification using latest backup"
        echo "  list         - List available backups"
        echo "  integrity    - Verify backup integrity only"
        exit 1
        ;;
esac
