#!/bin/bash
# DataFlux Data Retention Management System
# Automated data lifecycle management and cleanup

set -euo pipefail

# Configuration
LOG_FILE="/var/log/dataflux/retention.log"
RETENTION_POLICIES_FILE="/etc/dataflux/retention-policies.conf"

# Database configuration
POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
POSTGRES_PORT="${POSTGRES_PORT:-2001}"
POSTGRES_USER="${POSTGRES_USER:-dataflux_user}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-dataflux_pass}"
POSTGRES_DB="${POSTGRES_DB:-dataflux}"

# MinIO configuration
MINIO_ENDPOINT="${MINIO_ENDPOINT:-localhost:2003}"
MINIO_ACCESS_KEY="${MINIO_ACCESS_KEY:-minioadmin}"
MINIO_SECRET_KEY="${MINIO_SECRET_KEY:-minioadmin}"
MINIO_BUCKET="${MINIO_BUCKET:-dataflux-assets}"

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

# Default retention policies
create_default_policies() {
    log "Creating default retention policies..."
    
    mkdir -p "$(dirname "$RETENTION_POLICIES_FILE")"
    
    cat > "$RETENTION_POLICIES_FILE" << 'EOF'
# DataFlux Retention Policies Configuration
# Format: COMPONENT:RETENTION_DAYS:ACTION:CONDITIONS

# Database tables
ASSETS:365:ARCHIVE:status=inactive
SEGMENTS:180:DELETE:confidence_score<0.3
FEATURES:180:DELETE:confidence_score<0.3
EMBEDDINGS:365:ARCHIVE:model_name=old_model
RELATIONSHIPS:365:ARCHIVE:confidence_score<0.5
COLLECTIONS:730:ARCHIVE:is_active=false
USERS:3650:ARCHIVE:is_active=false
AUDIT_LOGS:90:DELETE:level=info
PERFORMANCE_METRICS:30:DELETE:metric_type=system
FEEDBACK:180:DELETE:feedback_type=negative

# MinIO objects
MINIO_ASSETS:365:ARCHIVE:size>100MB
MINIO_THUMBNAILS:180:DELETE:parent_asset_deleted=true
MINIO_PROXIES:90:DELETE:parent_asset_deleted=true

# Log files
APPLICATION_LOGS:30:DELETE:level=debug
ACCESS_LOGS:90:DELETE:status_code=200
ERROR_LOGS:180:ARCHIVE:level=error
AUDIT_LOGS:365:ARCHIVE:action=delete

# Backup files
BACKUP_FILES:30:DELETE:type=incremental
BACKUP_FILES:90:DELETE:type=differential
BACKUP_FILES:365:DELETE:type=full
EOF
    
    log "Default retention policies created: $RETENTION_POLICIES_FILE"
}

# Load retention policies
load_policies() {
    if [ ! -f "$RETENTION_POLICIES_FILE" ]; then
        create_default_policies
    fi
    
    log "Loading retention policies from: $RETENTION_POLICIES_FILE"
    
    # Read policies and store in associative array
    declare -g -A RETENTION_POLICIES
    
    while IFS=':' read -r component retention_days action conditions; do
        # Skip comments and empty lines
        if [[ "$component" =~ ^#.*$ ]] || [[ -z "$component" ]]; then
            continue
        fi
        
        RETENTION_POLICIES["$component"]="$retention_days:$action:$conditions"
        log_info "Loaded policy: $component -> $retention_days days, $action, $conditions"
    done < "$RETENTION_POLICIES_FILE"
}

# Cleanup database tables
cleanup_database() {
    log "Starting database cleanup..."
    
    # Set password for psql
    export PGPASSWORD="$POSTGRES_PASSWORD"
    
    local total_deleted=0
    local total_archived=0
    
    for component in "${!RETENTION_POLICIES[@]}"; do
        if [[ "$component" =~ ^(ASSETS|SEGMENTS|FEATURES|EMBEDDINGS|RELATIONSHIPS|COLLECTIONS|USERS|AUDIT_LOGS|PERFORMANCE_METRICS|FEEDBACK)$ ]]; then
            local policy="${RETENTION_POLICIES[$component]}"
            local retention_days=$(echo "$policy" | cut -d':' -f1)
            local action=$(echo "$policy" | cut -d':' -f2)
            local conditions=$(echo "$policy" | cut -d':' -f3)
            
            log "Processing $component: $retention_days days, $action, $conditions"
            
            case "$action" in
                "DELETE")
                    local deleted_count=$(delete_database_records "$component" "$retention_days" "$conditions")
                    total_deleted=$((total_deleted + deleted_count))
                    ;;
                "ARCHIVE")
                    local archived_count=$(archive_database_records "$component" "$retention_days" "$conditions")
                    total_archived=$((total_archived + archived_count))
                    ;;
                *)
                    log_warn "Unknown action for $component: $action"
                    ;;
            esac
        fi
    done
    
    log "Database cleanup completed: $total_deleted deleted, $total_archived archived"
    unset PGPASSWORD
}

# Delete database records
delete_database_records() {
    local table="$1"
    local retention_days="$2"
    local conditions="$3"
    
    local cutoff_date=$(date -d "$retention_days days ago" '+%Y-%m-%d')
    
    # Build WHERE clause
    local where_clause="created_at < '$cutoff_date'"
    if [ "$conditions" != "none" ]; then
        where_clause="$where_clause AND $conditions"
    fi
    
    # Get count before deletion
    local count_query="SELECT COUNT(*) FROM $table WHERE $where_clause"
    local count=$(psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" \
                      -d "$POSTGRES_DB" -t -c "$count_query" | tr -d ' ')
    
    if [ "$count" -gt 0 ]; then
        # Delete records
        local delete_query="DELETE FROM $table WHERE $where_clause"
        psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" \
             -d "$POSTGRES_DB" -c "$delete_query" 2>> "$LOG_FILE"
        
        log "Deleted $count records from $table"
    fi
    
    echo "$count"
}

# Archive database records
archive_database_records() {
    local table="$1"
    local retention_days="$2"
    local conditions="$3"
    
    local cutoff_date=$(date -d "$retention_days days ago" '+%Y-%m-%d')
    
    # Build WHERE clause
    local where_clause="created_at < '$cutoff_date'"
    if [ "$conditions" != "none" ]; then
        where_clause="$where_clause AND $conditions"
    fi
    
    # Get count before archiving
    local count_query="SELECT COUNT(*) FROM $table WHERE $where_clause"
    local count=$(psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" \
                      -d "$POSTGRES_DB" -t -c "$count_query" | tr -d ' ')
    
    if [ "$count" -gt 0 ]; then
        # Create archive table if it doesn't exist
        local archive_table="${table}_archive"
        psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" \
             -d "$POSTGRES_DB" -c "CREATE TABLE IF NOT EXISTS $archive_table (LIKE $table INCLUDING ALL);" 2>> "$LOG_FILE"
        
        # Move records to archive table
        local archive_query="INSERT INTO $archive_table SELECT * FROM $table WHERE $where_clause"
        psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" \
             -d "$POSTGRES_DB" -c "$archive_query" 2>> "$LOG_FILE"
        
        # Delete original records
        local delete_query="DELETE FROM $table WHERE $where_clause"
        psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" \
             -d "$POSTGRES_DB" -c "$delete_query" 2>> "$LOG_FILE"
        
        log "Archived $count records from $table to $archive_table"
    fi
    
    echo "$count"
}

# Cleanup MinIO objects
cleanup_minio() {
    log "Starting MinIO cleanup..."
    
    if ! command -v mc &> /dev/null; then
        log_warn "MinIO client (mc) not found, skipping MinIO cleanup"
        return 0
    fi
    
    # Configure MinIO client
    mc alias set cleanup-minio "http://$MINIO_ENDPOINT" "$MINIO_ACCESS_KEY" "$MINIO_SECRET_KEY" 2>> "$LOG_FILE"
    
    local total_deleted=0
    local total_archived=0
    
    for component in "${!RETENTION_POLICIES[@]}"; do
        if [[ "$component" =~ ^MINIO_ ]]; then
            local policy="${RETENTION_POLICIES[$component]}"
            local retention_days=$(echo "$policy" | cut -d':' -f1)
            local action=$(echo "$policy" | cut -d':' -f2)
            local conditions=$(echo "$policy" | cut -d':' -f3)
            
            log "Processing $component: $retention_days days, $action, $conditions"
            
            case "$action" in
                "DELETE")
                    local deleted_count=$(delete_minio_objects "$retention_days" "$conditions")
                    total_deleted=$((total_deleted + deleted_count))
                    ;;
                "ARCHIVE")
                    local archived_count=$(archive_minio_objects "$retention_days" "$conditions")
                    total_archived=$((total_archived + archived_count))
                    ;;
                *)
                    log_warn "Unknown action for $component: $action"
                    ;;
            esac
    done
    
    log "MinIO cleanup completed: $total_deleted deleted, $total_archived archived"
}

# Delete MinIO objects
delete_minio_objects() {
    local retention_days="$1"
    local conditions="$2"
    
    local cutoff_date=$(date -d "$retention_days days ago" '+%Y-%m-%d')
    local deleted_count=0
    
    # List objects older than cutoff date
    while IFS= read -r object; do
        if [ -n "$object" ]; then
            # Check if object meets conditions
            if check_minio_conditions "$object" "$conditions"; then
                # Delete object
                mc rm "cleanup-minio/$MINIO_BUCKET/$object" 2>> "$LOG_FILE"
                deleted_count=$((deleted_count + 1))
            fi
        fi
    done < <(mc ls "cleanup-minio/$MINIO_BUCKET" --recursive | awk '{print $5}' | while read -r object; do
        # Get object modification time
        local mod_time=$(mc stat "cleanup-minio/$MINIO_BUCKET/$object" --json | jq -r '.lastModified' 2>/dev/null)
        if [ "$mod_time" != "null" ] && [ "$mod_time" != "" ]; then
            local mod_date=$(date -d "$mod_time" '+%Y-%m-%d')
            if [ "$mod_date" < "$cutoff_date" ]; then
                echo "$object"
            fi
        fi
    done)
    
    if [ $deleted_count -gt 0 ]; then
        log "Deleted $deleted_count MinIO objects"
    fi
    
    echo "$deleted_count"
}

# Archive MinIO objects
archive_minio_objects() {
    local retention_days="$1"
    local conditions="$2"
    
    local cutoff_date=$(date -d "$retention_days days ago" '+%Y-%m-%d')
    local archived_count=0
    
    # Create archive bucket if it doesn't exist
    mc mb "cleanup-minio/${MINIO_BUCKET}-archive" 2>/dev/null || true
    
    # List objects older than cutoff date
    while IFS= read -r object; do
        if [ -n "$object" ]; then
            # Check if object meets conditions
            if check_minio_conditions "$object" "$conditions"; then
                # Move object to archive bucket
                mc mv "cleanup-minio/$MINIO_BUCKET/$object" "cleanup-minio/${MINIO_BUCKET}-archive/$object" 2>> "$LOG_FILE"
                archived_count=$((archived_count + 1))
            fi
        fi
    done < <(mc ls "cleanup-minio/$MINIO_BUCKET" --recursive | awk '{print $5}' | while read -r object; do
        # Get object modification time
        local mod_time=$(mc stat "cleanup-minio/$MINIO_BUCKET/$object" --json | jq -r '.lastModified' 2>/dev/null)
        if [ "$mod_time" != "null" ] && [ "$mod_time" != "" ]; then
            local mod_date=$(date -d "$mod_time" '+%Y-%m-%d')
            if [ "$mod_date" < "$cutoff_date" ]; then
                echo "$object"
            fi
        fi
    done)
    
    if [ $archived_count -gt 0 ]; then
        log "Archived $archived_count MinIO objects"
    fi
    
    echo "$archived_count"
}

# Check MinIO object conditions
check_minio_conditions() {
    local object="$1"
    local conditions="$2"
    
    if [ "$conditions" = "none" ]; then
        return 0
    fi
    
    # Parse conditions
    if [[ "$conditions" =~ size>([0-9]+)MB ]]; then
        local min_size="${BASH_REMATCH[1]}"
        local object_size=$(mc stat "cleanup-minio/$MINIO_BUCKET/$object" --json | jq -r '.size' 2>/dev/null)
        local object_size_mb=$((object_size / 1024 / 1024))
        
        if [ "$object_size_mb" -gt "$min_size" ]; then
            return 0
        else
            return 1
        fi
    fi
    
    if [[ "$conditions" =~ parent_asset_deleted=true ]]; then
        # Check if parent asset exists in database
        local asset_id=$(echo "$object" | cut -d'/' -f1)
        local asset_exists=$(psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" \
                                -d "$POSTGRES_DB" -t -c "SELECT COUNT(*) FROM assets WHERE asset_id = '$asset_id';" | tr -d ' ')
        
        if [ "$asset_exists" -eq 0 ]; then
            return 0
        else
            return 1
        fi
    fi
    
    return 0
}

# Cleanup log files
cleanup_logs() {
    log "Starting log file cleanup..."
    
    local total_deleted=0
    local total_archived=0
    
    for component in "${!RETENTION_POLICIES[@]}"; do
        if [[ "$component" =~ ^(APPLICATION_LOGS|ACCESS_LOGS|ERROR_LOGS|AUDIT_LOGS)$ ]]; then
            local policy="${RETENTION_POLICIES[$component]}"
            local retention_days=$(echo "$policy" | cut -d':' -f1)
            local action=$(echo "$policy" | cut -d':' -f2)
            local conditions=$(echo "$policy" | cut -d':' -f3)
            
            log "Processing $component: $retention_days days, $action, $conditions"
            
            case "$action" in
                "DELETE")
                    local deleted_count=$(delete_log_files "$component" "$retention_days" "$conditions")
                    total_deleted=$((total_deleted + deleted_count))
                    ;;
                "ARCHIVE")
                    local archived_count=$(archive_log_files "$component" "$retention_days" "$conditions")
                    total_archived=$((total_archived + archived_count))
                    ;;
                *)
                    log_warn "Unknown action for $component: $action"
                    ;;
            esac
        fi
    done
    
    log "Log file cleanup completed: $total_deleted deleted, $total_archived archived"
}

# Delete log files
delete_log_files() {
    local log_type="$1"
    local retention_days="$2"
    local conditions="$3"
    
    local log_dirs=()
    case "$log_type" in
        "APPLICATION_LOGS")
            log_dirs=("/var/log/dataflux" "/opt/dataflux/logs")
            ;;
        "ACCESS_LOGS")
            log_dirs=("/var/log/nginx" "/var/log/apache2")
            ;;
        "ERROR_LOGS")
            log_dirs=("/var/log/dataflux" "/var/log/nginx" "/var/log/apache2")
            ;;
        "AUDIT_LOGS")
            log_dirs=("/var/log/dataflux" "/var/log/audit")
            ;;
    esac
    
    local deleted_count=0
    
    for log_dir in "${log_dirs[@]}"; do
        if [ -d "$log_dir" ]; then
            # Find and delete old log files
            while IFS= read -r log_file; do
                if [ -f "$log_file" ]; then
                    # Check conditions
                    if check_log_conditions "$log_file" "$conditions"; then
                        rm -f "$log_file"
                        deleted_count=$((deleted_count + 1))
                    fi
                fi
            done < <(find "$log_dir" -name "*.log" -mtime +$retention_days -type f)
        fi
    done
    
    if [ $deleted_count -gt 0 ]; then
        log "Deleted $deleted_count log files"
    fi
    
    echo "$deleted_count"
}

# Archive log files
archive_log_files() {
    local log_type="$1"
    local retention_days="$2"
    local conditions="$3"
    
    local log_dirs=()
    case "$log_type" in
        "APPLICATION_LOGS")
            log_dirs=("/var/log/dataflux" "/opt/dataflux/logs")
            ;;
        "ACCESS_LOGS")
            log_dirs=("/var/log/nginx" "/var/log/apache2")
            ;;
        "ERROR_LOGS")
            log_dirs=("/var/log/dataflux" "/var/log/nginx" "/var/log/apache2")
            ;;
        "AUDIT_LOGS")
            log_dirs=("/var/log/dataflux" "/var/log/audit")
            ;;
    esac
    
    local archived_count=0
    local archive_dir="/opt/dataflux/archives/logs"
    
    # Create archive directory
    mkdir -p "$archive_dir"
    
    for log_dir in "${log_dirs[@]}"; do
        if [ -d "$log_dir" ]; then
            # Find and archive old log files
            while IFS= read -r log_file; do
                if [ -f "$log_file" ]; then
                    # Check conditions
                    if check_log_conditions "$log_file" "$conditions"; then
                        # Create archive filename
                        local archive_filename=$(basename "$log_file")_$(date -r "$log_file" '+%Y%m%d_%H%M%S')
                        
                        # Compress and move to archive
                        gzip -c "$log_file" > "$archive_dir/$archive_filename.gz"
                        rm -f "$log_file"
                        archived_count=$((archived_count + 1))
                    fi
                fi
            done < <(find "$log_dir" -name "*.log" -mtime +$retention_days -type f)
        fi
    done
    
    if [ $archived_count -gt 0 ]; then
        log "Archived $archived_count log files"
    fi
    
    echo "$archived_count"
}

# Check log file conditions
check_log_conditions() {
    local log_file="$1"
    local conditions="$2"
    
    if [ "$conditions" = "none" ]; then
        return 0
    fi
    
    # Parse conditions
    if [[ "$conditions" =~ level=([a-zA-Z]+) ]]; then
        local log_level="${BASH_REMATCH[1]}"
        # Check if log file contains the specified level
        if grep -q "$log_level" "$log_file" 2>/dev/null; then
            return 0
        else
            return 1
        fi
    fi
    
    if [[ "$conditions" =~ status_code=([0-9]+) ]]; then
        local status_code="${BASH_REMATCH[1]}"
        # Check if log file contains the specified status code
        if grep -q "$status_code" "$log_file" 2>/dev/null; then
            return 0
        else
            return 1
        fi
    fi
    
    if [[ "$conditions" =~ action=([a-zA-Z]+) ]]; then
        local action="${BASH_REMATCH[1]}"
        # Check if log file contains the specified action
        if grep -q "$action" "$log_file" 2>/dev/null; then
            return 0
        else
            return 1
        fi
    fi
    
    return 0
}

# Cleanup backup files
cleanup_backups() {
    log "Starting backup file cleanup..."
    
    local total_deleted=0
    
    for component in "${!RETENTION_POLICIES[@]}"; do
        if [[ "$component" =~ ^BACKUP_FILES$ ]]; then
            local policy="${RETENTION_POLICIES[$component]}"
            local retention_days=$(echo "$policy" | cut -d':' -f1)
            local action=$(echo "$policy" | cut -d':' -f2)
            local conditions=$(echo "$policy" | cut -d':' -f3)
            
            log "Processing $component: $retention_days days, $action, $conditions"
            
            if [ "$action" = "DELETE" ]; then
                local deleted_count=$(delete_backup_files "$retention_days" "$conditions")
                total_deleted=$((total_deleted + deleted_count))
            fi
        fi
    done
    
    log "Backup file cleanup completed: $total_deleted deleted"
}

# Delete backup files
delete_backup_files() {
    local retention_days="$1"
    local conditions="$2"
    
    local backup_dirs=("/opt/dataflux/backups" "/var/backups/dataflux")
    local deleted_count=0
    
    for backup_dir in "${backup_dirs[@]}"; do
        if [ -d "$backup_dir" ]; then
            # Find and delete old backup files
            while IFS= read -r backup_file; do
                if [ -f "$backup_file" ]; then
                    # Check conditions
                    if check_backup_conditions "$backup_file" "$conditions"; then
                        rm -f "$backup_file"
                        deleted_count=$((deleted_count + 1))
                    fi
                fi
            done < <(find "$backup_dir" -name "*.tar.gz" -mtime +$retention_days -type f)
        fi
    done
    
    if [ $deleted_count -gt 0 ]; then
        log "Deleted $deleted_count backup files"
    fi
    
    echo "$deleted_count"
}

# Check backup file conditions
check_backup_conditions() {
    local backup_file="$1"
    local conditions="$2"
    
    if [ "$conditions" = "none" ]; then
        return 0
    fi
    
    # Parse conditions
    if [[ "$conditions" =~ type=([a-zA-Z]+) ]]; then
        local backup_type="${BASH_REMATCH[1]}"
        # Check if backup filename contains the specified type
        if [[ "$backup_file" =~ $backup_type ]]; then
            return 0
        else
            return 1
        fi
    fi
    
    return 0
}

# Generate retention report
generate_report() {
    log "Generating retention report..."
    
    local report_file="/var/log/dataflux/retention-report-$(date +%Y%m%d).txt"
    
    cat > "$report_file" << EOF
DataFlux Data Retention Report
Generated: $(date)
================================

Retention Policies:
EOF
    
    for component in "${!RETENTION_POLICIES[@]}"; do
        local policy="${RETENTION_POLICIES[$component]}"
        local retention_days=$(echo "$policy" | cut -d':' -f1)
        local action=$(echo "$policy" | cut -d':' -f2)
        local conditions=$(echo "$policy" | cut -d':' -f3)
        
        echo "  $component: $retention_days days, $action, $conditions" >> "$report_file"
    done
    
    echo "" >> "$report_file"
    echo "Database Statistics:" >> "$report_file"
    
    # Set password for psql
    export PGPASSWORD="$POSTGRES_PASSWORD"
    
    # Get table sizes
    psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" \
         -d "$POSTGRES_DB" -c "
         SELECT 
             schemaname,
             tablename,
             pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
         FROM pg_tables 
         WHERE schemaname = 'public'
         ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
         " >> "$report_file"
    
    unset PGPASSWORD
    
    echo "" >> "$report_file"
    echo "MinIO Statistics:" >> "$report_file"
    
    if command -v mc &> /dev/null; then
        mc alias set report-minio "http://$MINIO_ENDPOINT" "$MINIO_ACCESS_KEY" "$MINIO_SECRET_KEY" 2>> "$LOG_FILE"
        mc du "report-minio/$MINIO_BUCKET" >> "$report_file"
    fi
    
    log "Retention report generated: $report_file"
}

# Send retention notification
send_notification() {
    local status="$1"
    local message="$2"
    
    # Send email notification (if configured)
    if [ -n "${RETENTION_EMAIL:-}" ]; then
        echo "$message" | mail -s "DataFlux Retention $status" "$RETENTION_EMAIL"
    fi
    
    # Send webhook notification (if configured)
    if [ -n "${RETENTION_WEBHOOK:-}" ]; then
        curl -X POST "$RETENTION_WEBHOOK" \
             -H "Content-Type: application/json" \
             -d "{\"status\": \"$status\", \"message\": \"$message\", \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}" \
             2>/dev/null || true
    fi
}

# Main retention function
main() {
    local start_time=$(date +%s)
    local retention_status="SUCCESS"
    local error_message=""
    
    log "Starting DataFlux data retention process..."
    
    # Load retention policies
    load_policies
    
    # Run cleanup processes
    (
        cleanup_database &
        cleanup_minio &
        cleanup_logs &
        cleanup_backups &
        wait
    )
    
    # Generate report
    generate_report
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    log "Data retention process completed successfully in ${duration}s"
    
    send_notification "SUCCESS" "DataFlux data retention completed successfully. Duration: ${duration}s"
}

# Handle script arguments
case "${1:-}" in
    "run")
        main
        ;;
    "policies")
        if [ "${2:-}" = "create" ]; then
            create_default_policies
        else
            load_policies
            echo "Current retention policies:"
            for component in "${!RETENTION_POLICIES[@]}"; do
                echo "  $component: ${RETENTION_POLICIES[$component]}"
            done
        fi
        ;;
    "report")
        load_policies
        generate_report
        ;;
    "cleanup")
        case "${2:-}" in
            "database")
                load_policies
                cleanup_database
                ;;
            "minio")
                load_policies
                cleanup_minio
                ;;
            "logs")
                load_policies
                cleanup_logs
                ;;
            "backups")
                load_policies
                cleanup_backups
                ;;
            *)
                echo "Usage: $0 cleanup {database|minio|logs|backups}"
                exit 1
                ;;
        esac
        ;;
    *)
        echo "Usage: $0 {run|policies|report|cleanup}"
        echo ""
        echo "Commands:"
        echo "  run                    - Run full retention process"
        echo "  policies [create]      - Show or create retention policies"
        echo "  report                 - Generate retention report"
        echo "  cleanup {component}    - Cleanup specific component"
        echo ""
        echo "Components:"
        echo "  database               - Cleanup database tables"
        echo "  minio                  - Cleanup MinIO objects"
        echo "  logs                   - Cleanup log files"
        echo "  backups                - Cleanup backup files"
        exit 1
        ;;
esac
