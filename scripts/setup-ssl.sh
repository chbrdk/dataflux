#!/bin/bash

# SSL Certificate Setup Script for DataFlux
# Automated SSL certificate generation and renewal with Let's Encrypt

set -e

# Configuration
DOMAIN="dataflux.local"
EMAIL="admin@dataflux.local"
NGINX_CONF_DIR="/etc/nginx/conf.d"
CERTBOT_DIR="/etc/letsencrypt"
WEBROOT="/var/www/certbot"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root"
        exit 1
    fi
}

# Install required packages
install_dependencies() {
    log_info "Installing dependencies..."
    
    # Update package list
    apt-get update
    
    # Install certbot and nginx
    apt-get install -y certbot python3-certbot-nginx nginx
    
    # Install curl for health checks
    apt-get install -y curl
    
    log_info "Dependencies installed successfully"
}

# Create webroot directory
create_webroot() {
    log_info "Creating webroot directory..."
    mkdir -p $WEBROOT
    chown -R www-data:www-data $WEBROOT
    log_info "Webroot directory created"
}

# Generate self-signed certificate for development
generate_self_signed() {
    log_info "Generating self-signed certificate for development..."
    
    # Create certificate directory
    mkdir -p $CERTBOT_DIR/live/$DOMAIN
    
    # Generate private key
    openssl genrsa -out $CERTBOT_DIR/live/$DOMAIN/privkey.pem 2048
    
    # Generate certificate
    openssl req -new -x509 -key $CERTBOT_DIR/live/$DOMAIN/privkey.pem \
        -out $CERTBOT_DIR/live/$DOMAIN/fullchain.pem \
        -days 365 \
        -subj "/C=US/ST=State/L=City/O=Organization/CN=$DOMAIN"
    
    # Create symlink for certbot compatibility
    ln -sf $CERTBOT_DIR/live/$DOMAIN/fullchain.pem $CERTBOT_DIR/live/$DOMAIN/cert.pem
    
    log_info "Self-signed certificate generated"
}

# Generate Let's Encrypt certificate
generate_letsencrypt() {
    log_info "Generating Let's Encrypt certificate..."
    
    # Stop nginx if running
    systemctl stop nginx || true
    
    # Generate certificate
    certbot certonly \
        --webroot \
        --webroot-path=$WEBROOT \
        --email $EMAIL \
        --agree-tos \
        --no-eff-email \
        --domains $DOMAIN,api.$DOMAIN \
        --non-interactive
    
    if [ $? -eq 0 ]; then
        log_info "Let's Encrypt certificate generated successfully"
    else
        log_error "Failed to generate Let's Encrypt certificate"
        exit 1
    fi
}

# Setup nginx configuration
setup_nginx() {
    log_info "Setting up nginx configuration..."
    
    # Copy SSL configuration
    cp /app/nginx-ssl.conf $NGINX_CONF_DIR/dataflux-ssl.conf
    
    # Test nginx configuration
    nginx -t
    
    if [ $? -eq 0 ]; then
        log_info "Nginx configuration is valid"
    else
        log_error "Nginx configuration is invalid"
        exit 1
    fi
}

# Setup certificate renewal
setup_renewal() {
    log_info "Setting up certificate renewal..."
    
    # Create renewal script
    cat > /etc/cron.d/certbot-renew << EOF
# Renew Let's Encrypt certificates twice daily
0 */12 * * * root certbot renew --quiet --post-hook "systemctl reload nginx"
EOF
    
    # Make script executable
    chmod +x /etc/cron.d/certbot-renew
    
    log_info "Certificate renewal setup completed"
}

# Start services
start_services() {
    log_info "Starting services..."
    
    # Start nginx
    systemctl enable nginx
    systemctl start nginx
    
    # Check nginx status
    if systemctl is-active --quiet nginx; then
        log_info "Nginx started successfully"
    else
        log_error "Failed to start nginx"
        exit 1
    fi
}

# Test SSL configuration
test_ssl() {
    log_info "Testing SSL configuration..."
    
    # Wait for nginx to start
    sleep 5
    
    # Test HTTPS connection
    if curl -k -s -o /dev/null -w "%{http_code}" https://$DOMAIN | grep -q "200\|301\|302"; then
        log_info "SSL configuration test passed"
    else
        log_warn "SSL configuration test failed - this might be expected if services are not running"
    fi
}

# Main function
main() {
    log_info "Starting SSL certificate setup for DataFlux..."
    
    # Check if running as root
    check_root
    
    # Install dependencies
    install_dependencies
    
    # Create webroot
    create_webroot
    
    # Check if we're in production or development
    if [ "$1" = "production" ]; then
        log_info "Setting up for production with Let's Encrypt..."
        generate_letsencrypt
    else
        log_info "Setting up for development with self-signed certificate..."
        generate_self_signed
    fi
    
    # Setup nginx
    setup_nginx
    
    # Setup renewal (only for Let's Encrypt)
    if [ "$1" = "production" ]; then
        setup_renewal
    fi
    
    # Start services
    start_services
    
    # Test SSL
    test_ssl
    
    log_info "SSL certificate setup completed successfully!"
    
    if [ "$1" = "production" ]; then
        log_info "Let's Encrypt certificate is active"
        log_info "Certificate will auto-renew twice daily"
    else
        log_info "Self-signed certificate is active"
        log_warn "This certificate will show as untrusted in browsers"
        log_warn "For production, run: $0 production"
    fi
}

# Show usage
usage() {
    echo "Usage: $0 [production|development]"
    echo ""
    echo "  production   - Generate Let's Encrypt certificate for production"
    echo "  development  - Generate self-signed certificate for development (default)"
    echo ""
    echo "Examples:"
    echo "  $0                    # Development setup"
    echo "  $0 development        # Development setup"
    echo "  $0 production         # Production setup"
}

# Handle command line arguments
case "${1:-development}" in
    production)
        main production
        ;;
    development|dev)
        main development
        ;;
    -h|--help)
        usage
        exit 0
        ;;
    *)
        log_error "Invalid argument: $1"
        usage
        exit 1
        ;;
esac
