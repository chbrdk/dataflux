#!/bin/bash
# DataFlux Backup Scheduling System
# Automated backup scheduling with cron integration

set -euo pipefail

# Configuration
BACKUP_ROOT="/opt/dataflux/backups"
LOG_FILE="/var/log/dataflux/backup-scheduler.log"
CRON_FILE="/etc/cron.d/dataflux-backups"
SCHEDULE_CONFIG="/etc/dataflux/backup-schedule.conf"

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

# Default backup schedule configuration
create_default_schedule() {
    log "Creating default backup schedule configuration..."
    
    mkdir -p "$(dirname "$SCHEDULE_CONFIG")"
    
    cat > "$SCHEDULE_CONFIG" << 'EOF'
# DataFlux Backup Schedule Configuration
# Format: SCHEDULE_NAME:TYPE:FREQUENCY:TIME:COMPONENTS:RETENTION_DAYS

# Daily full backup at 2 AM
DAILY_FULL:full:daily:02:00:postgresql,redis,minio,neo4j,weaviate,clickhouse:30

# Weekly full backup on Sunday at 1 AM
WEEKLY_FULL:full:weekly:sunday:01:00:postgresql,redis,minio,neo4j,weaviate,clickhouse:90

# Monthly full backup on 1st at midnight
MONTHLY_FULL:full:monthly:1:00:00:postgresql,redis,minio,neo4j,weaviate,clickhouse:365

# Hourly incremental backup
HOURLY_INCREMENTAL:incremental:hourly::postgresql,redis:7

# Daily incremental backup at 6 AM
DAILY_INCREMENTAL:incremental:daily:06:00:postgresql,redis:14

# Weekly incremental backup on Wednesday at 3 AM
WEEKLY_INCREMENTAL:incremental:weekly:wednesday:03:00:postgresql,redis:30

# Database-only backup every 4 hours
DB_FREQUENT:database:4hours::postgresql:3

# MinIO-only backup daily at 4 AM
MINIO_DAILY:minio:daily:04:00:minio:60

# Neo4j-only backup weekly on Monday at 5 AM
NEO4J_WEEKLY:neo4j:weekly:monday:05:00:neo4j:180

# Weaviate-only backup weekly on Tuesday at 6 AM
WEAVIATE_WEEKLY:weaviate:weekly:tuesday:06:00:weaviate:180

# ClickHouse-only backup weekly on Thursday at 7 AM
CLICKHOUSE_WEEKLY:clickhouse:weekly:thursday:07:00:clickhouse:180
EOF
    
    log "Default backup schedule configuration created: $SCHEDULE_CONFIG"
}

# Load backup schedule configuration
load_schedule_config() {
    if [ ! -f "$SCHEDULE_CONFIG" ]; then
        create_default_schedule
    fi
    
    log "Loading backup schedule configuration from: $SCHEDULE_CONFIG"
    
    # Read schedule configuration
    while IFS=':' read -r schedule_name schedule_type frequency time components retention_days; do
        # Skip comments and empty lines
        if [[ "$schedule_name" =~ ^#.*$ ]] || [[ -z "$schedule_name" ]]; then
            continue
        fi
        
        log_info "Loaded schedule: $schedule_name -> $schedule_type, $frequency, $time, $components, $retention_days days"
    done < "$SCHEDULE_CONFIG"
}

# Generate cron entries
generate_cron_entries() {
    log "Generating cron entries..."
    
    local cron_entries=()
    
    while IFS=':' read -r schedule_name schedule_type frequency time components retention_days; do
        # Skip comments and empty lines
        if [[ "$schedule_name" =~ ^#.*$ ]] || [[ -z "$schedule_name" ]]; then
            continue
        fi
        
        local cron_time=""
        local cron_frequency=""
        
        case "$frequency" in
            "hourly")
                cron_frequency="0 * * * *"
                ;;
            "4hours")
                cron_frequency="0 */4 * * *"
                ;;
            "daily")
                if [ -n "$time" ]; then
                    local hour=$(echo "$time" | cut -d':' -f1)
                    local minute=$(echo "$time" | cut -d':' -f2)
                    cron_frequency="$minute $hour * * *"
                else
                    cron_frequency="0 0 * * *"
                fi
                ;;
            "weekly")
                if [ -n "$time" ]; then
                    local day=$(echo "$time" | cut -d':' -f1)
                    local hour=$(echo "$time" | cut -d':' -f2)
                    local minute=$(echo "$time" | cut -d':' -f3)
                    
                    case "$day" in
                        "sunday") day_num="0" ;;
                        "monday") day_num="1" ;;
                        "tuesday") day_num="2" ;;
                        "wednesday") day_num="3" ;;
                        "thursday") day_num="4" ;;
                        "friday") day_num="5" ;;
                        "saturday") day_num="6" ;;
                        *) day_num="0" ;;
                    esac
                    
                    cron_frequency="$minute $hour * * $day_num"
                else
                    cron_frequency="0 0 * * 0"
                fi
                ;;
            "monthly")
                if [ -n "$time" ]; then
                    local day=$(echo "$time" | cut -d':' -f1)
                    local hour=$(echo "$time" | cut -d':' -f2)
                    local minute=$(echo "$time" | cut -d':' -f3)
                    cron_frequency="$minute $hour $day * *"
                else
                    cron_frequency="0 0 1 * *"
                fi
                ;;
            *)
                log_warn "Unknown frequency: $frequency"
                continue
                ;;
        esac
        
        # Create cron entry
        local cron_entry="$cron_frequency root /opt/dataflux/scripts/backup.sh $schedule_type >> $LOG_FILE 2>&1"
        cron_entries+=("$cron_entry")
        
        log_info "Generated cron entry for $schedule_name: $cron_frequency"
    done < "$SCHEDULE_CONFIG"
    
    # Write cron file
    cat > "$CRON_FILE" << EOF
# DataFlux Backup Schedule
# Generated: $(date)
# Do not edit this file manually - use backup-scheduler.sh instead

EOF
    
    for entry in "${cron_entries[@]}"; do
        echo "$entry" >> "$CRON_FILE"
    done
    
    log "Cron entries written to: $CRON_FILE"
}

# Install cron schedule
install_cron_schedule() {
    log "Installing cron schedule..."
    
    if [ ! -f "$CRON_FILE" ]; then
        log_error "Cron file not found: $CRON_FILE"
        return 1
    fi
    
    # Install cron file
    if crontab -u root "$CRON_FILE"; then
        log "✓ Cron schedule installed successfully"
    else
        log_error "✗ Failed to install cron schedule"
        return 1
    fi
    
    # Verify installation
    if crontab -u root -l | grep -q "dataflux"; then
        log "✓ Cron schedule verified"
    else
        log_error "✗ Cron schedule verification failed"
        return 1
    fi
}

# Uninstall cron schedule
uninstall_cron_schedule() {
    log "Uninstalling cron schedule..."
    
    # Remove DataFlux cron entries
    crontab -u root -l | grep -v "dataflux" | crontab -u root -
    
    log "✓ Cron schedule uninstalled"
}

# Show current cron schedule
show_cron_schedule() {
    log "Current cron schedule:"
    
    if crontab -u root -l | grep -q "dataflux"; then
        crontab -u root -l | grep "dataflux"
    else
        log_warn "No DataFlux cron entries found"
    fi
}

# Test backup schedule
test_backup_schedule() {
    local schedule_name="${1:-DAILY_FULL}"
    
    log "Testing backup schedule: $schedule_name"
    
    # Find schedule in configuration
    local schedule_line=""
    while IFS=':' read -r name type frequency time components retention_days; do
        if [ "$name" = "$schedule_name" ]; then
            schedule_line="$name:$type:$frequency:$time:$components:$retention_days"
            break
        fi
    done < "$SCHEDULE_CONFIG"
    
    if [ -z "$schedule_line" ]; then
        log_error "Schedule not found: $schedule_name"
        return 1
    fi
    
    local schedule_type=$(echo "$schedule_line" | cut -d':' -f2)
    local components=$(echo "$schedule_line" | cut -d':' -f5)
    
    log "Running test backup: $schedule_type with components: $components"
    
    # Run backup
    if /opt/dataflux/scripts/backup.sh "$schedule_type"; then
        log "✓ Test backup completed successfully"
    else
        log_error "✗ Test backup failed"
        return 1
    fi
}

# Monitor backup schedule
monitor_backup_schedule() {
    log "Monitoring backup schedule..."
    
    local monitoring_active=true
    
    while [ "$monitoring_active" = true ]; do
        # Check if cron is running
        if ! pgrep cron > /dev/null; then
            log_error "Cron daemon is not running"
        fi
        
        # Check last backup time
        local last_backup=$(find "$BACKUP_ROOT" -name "*.tar.gz" -printf '%T@ %p\n' 2>/dev/null | sort -n | tail -1)
        if [ -n "$last_backup" ]; then
            local last_backup_time=$(echo "$last_backup" | cut -d' ' -f1)
            local last_backup_file=$(echo "$last_backup" | cut -d' ' -f2-)
            local last_backup_age=$(($(date +%s) - ${last_backup_time%.*}))
            
            if [ $last_backup_age -gt 86400 ]; then  # 24 hours
                log_warn "Last backup is older than 24 hours: $last_backup_file"
            else
                log_info "Last backup: $last_backup_file (age: ${last_backup_age}s)"
            fi
        else
            log_warn "No backups found"
        fi
        
        # Check backup directory size
        if [ -d "$BACKUP_ROOT" ]; then
            local backup_size=$(du -sh "$BACKUP_ROOT" | cut -f1)
            log_info "Backup directory size: $backup_size"
        fi
        
        # Wait 5 minutes
        sleep 300
    done
}

# Backup schedule statistics
backup_statistics() {
    log "Backup schedule statistics:"
    
    if [ ! -d "$BACKUP_ROOT" ]; then
        log_warn "Backup directory not found: $BACKUP_ROOT"
        return 1
    fi
    
    # Count backups by type
    local full_backups=$(find "$BACKUP_ROOT" -name "*full*.tar.gz" | wc -l)
    local incremental_backups=$(find "$BACKUP_ROOT" -name "*incremental*.tar.gz" | wc -l)
    local database_backups=$(find "$BACKUP_ROOT" -name "*database*.tar.gz" | wc -l)
    local minio_backups=$(find "$BACKUP_ROOT" -name "*minio*.tar.gz" | wc -l)
    local neo4j_backups=$(find "$BACKUP_ROOT" -name "*neo4j*.tar.gz" | wc -l)
    local weaviate_backups=$(find "$BACKUP_ROOT" -name "*weaviate*.tar.gz" | wc -l)
    local clickhouse_backups=$(find "$BACKUP_ROOT" -name "*clickhouse*.tar.gz" | wc -l)
    
    echo "  Full backups: $full_backups"
    echo "  Incremental backups: $incremental_backups"
    echo "  Database backups: $database_backups"
    echo "  MinIO backups: $minio_backups"
    echo "  Neo4j backups: $neo4j_backups"
    echo "  Weaviate backups: $weaviate_backups"
    echo "  ClickHouse backups: $clickhouse_backups"
    
    # Total size
    local total_size=$(du -sh "$BACKUP_ROOT" | cut -f1)
    echo "  Total backup size: $total_size"
    
    # Oldest and newest backups
    local oldest_backup=$(find "$BACKUP_ROOT" -name "*.tar.gz" -printf '%T@ %p\n' | sort -n | head -1)
    local newest_backup=$(find "$BACKUP_ROOT" -name "*.tar.gz" -printf '%T@ %p\n' | sort -n | tail -1)
    
    if [ -n "$oldest_backup" ]; then
        local oldest_time=$(echo "$oldest_backup" | cut -d' ' -f1)
        local oldest_file=$(echo "$oldest_backup" | cut -d' ' -f2-)
        local oldest_date=$(date -d "@${oldest_time%.*}" '+%Y-%m-%d %H:%M:%S')
        echo "  Oldest backup: $oldest_file ($oldest_date)"
    fi
    
    if [ -n "$newest_backup" ]; then
        local newest_time=$(echo "$newest_backup" | cut -d' ' -f1)
        local newest_file=$(echo "$newest_backup" | cut -d' ' -f2-)
        local newest_date=$(date -d "@${newest_time%.*}" '+%Y-%m-%d %H:%M:%S')
        echo "  Newest backup: $newest_file ($newest_date)"
    fi
}

# Send schedule notification
send_notification() {
    local status="$1"
    local message="$2"
    
    # Send email notification (if configured)
    if [ -n "${SCHEDULE_EMAIL:-}" ]; then
        echo "$message" | mail -s "DataFlux Backup Schedule $status" "$SCHEDULE_EMAIL"
    fi
    
    # Send webhook notification (if configured)
    if [ -n "${SCHEDULE_WEBHOOK:-}" ]; then
        curl -X POST "$SCHEDULE_WEBHOOK" \
             -H "Content-Type: application/json" \
             -d "{\"status\": \"$status\", \"message\": \"$message\", \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}" \
             2>/dev/null || true
    fi
}

# Main function
main() {
    local start_time=$(date +%s)
    local schedule_status="SUCCESS"
    local error_message=""
    
    log "Starting DataFlux backup schedule setup..."
    
    # Load schedule configuration
    load_schedule_config
    
    # Generate cron entries
    if generate_cron_entries; then
        # Install cron schedule
        if install_cron_schedule; then
            local end_time=$(date +%s)
            local duration=$((end_time - start_time))
            
            log "Backup schedule setup completed successfully in ${duration}s"
            
            # Show current schedule
            show_cron_schedule
            
            # Show statistics
            backup_statistics
            
            send_notification "SUCCESS" "DataFlux backup schedule setup completed successfully. Duration: ${duration}s"
        else
            schedule_status="FAILED"
            error_message="Failed to install cron schedule"
        fi
    else
        schedule_status="FAILED"
        error_message="Failed to generate cron entries"
    fi
    
    if [ "$schedule_status" = "FAILED" ]; then
        log_error "Backup schedule setup failed: $error_message"
        send_notification "FAILED" "DataFlux backup schedule setup failed: $error_message"
        exit 1
    fi
}

# Handle script arguments
case "${1:-}" in
    "setup")
        main
        ;;
    "install")
        load_schedule_config
        generate_cron_entries
        install_cron_schedule
        ;;
    "uninstall")
        uninstall_cron_schedule
        ;;
    "show")
        show_cron_schedule
        ;;
    "test")
        test_backup_schedule "${2:-DAILY_FULL}"
        ;;
    "monitor")
        monitor_backup_schedule
        ;;
    "stats")
        backup_statistics
        ;;
    "config")
        if [ "${2:-}" = "create" ]; then
            create_default_schedule
        else
            load_schedule_config
        fi
        ;;
    *)
        echo "Usage: $0 {setup|install|uninstall|show|test|monitor|stats|config}"
        echo ""
        echo "Commands:"
        echo "  setup       - Complete backup schedule setup"
        echo "  install     - Install cron schedule"
        echo "  uninstall   - Uninstall cron schedule"
        echo "  show        - Show current cron schedule"
        echo "  test        - Test backup schedule"
        echo "  monitor     - Monitor backup schedule"
        echo "  stats       - Show backup statistics"
        echo "  config      - Show or create schedule configuration"
        exit 1
        ;;
esac
