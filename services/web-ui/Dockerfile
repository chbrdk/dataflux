# DataFlux Web UI Dockerfile
FROM node:18-alpine

# Install dependencies
RUN apk add --no-cache curl

# Set working directory
WORKDIR /app

# Copy package files first for better caching
COPY package*.json ./
COPY next.config.js ./

# Install dependencies
RUN npm install

# Copy source code
COPY . .

# Build the application
RUN npm run build

# Set environment variables for Docker networking
ENV NEXT_PUBLIC_API_URL=http://dataflux-ingestion:2013
ENV NEXT_PUBLIC_INGESTION_URL=http://dataflux-ingestion:2013
ENV NEXT_PUBLIC_QUERY_URL=http://dataflux-query:8003

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:3000 || exit 1

# Start production server
CMD ["npm", "start"]