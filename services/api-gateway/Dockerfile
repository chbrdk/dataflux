# DataFlux API Gateway Dockerfile
FROM nginx:1.25-alpine

# Install additional tools
RUN apk add --no-cache \
    curl \
    openssl \
    bash

# Create necessary directories
RUN mkdir -p /etc/nginx/ssl \
    /var/log/nginx \
    /usr/share/nginx/html

# Copy configuration files
COPY nginx.conf /etc/nginx/nginx.conf
COPY configs/ /etc/nginx/conf.d/
COPY start.sh /usr/local/bin/start.sh

# Copy SSL certificates (if available)
COPY ssl/ /etc/nginx/ssl/

# Create self-signed certificate for development
RUN if [ ! -f /etc/nginx/ssl/cert.pem ]; then \
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/nginx/ssl/key.pem \
    -out /etc/nginx/ssl/cert.pem \
    -subj "/C=DE/ST=Local/L=Local/O=DataFlux/OU=Development/CN=localhost"; \
fi

# Create custom error pages
RUN echo '<!DOCTYPE html><html><head><title>DataFlux - Service Unavailable</title></head><body><h1>Service Temporarily Unavailable</h1><p>The DataFlux service is currently undergoing maintenance.</p></body></html>' > /usr/share/nginx/html/50x.html

RUN echo '<!DOCTYPE html><html><head><title>DataFlux - Not Found</title></head><body><h1>404 - Not Found</h1><p>The requested resource was not found.</p></body></html>' > /usr/share/nginx/html/404.html

# Set proper permissions
RUN chown -R nginx:nginx /var/log/nginx /etc/nginx/ssl
RUN chmod 600 /etc/nginx/ssl/key.pem
RUN chmod 644 /etc/nginx/ssl/cert.pem

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost/health || exit 1

# Expose ports
EXPOSE 80 443

# Make startup script executable
RUN chmod +x /usr/local/bin/start.sh

# Start API Gateway
CMD ["/usr/local/bin/start.sh"]