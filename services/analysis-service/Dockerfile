FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/

# Expose port
EXPOSE 2014

# Set environment variables
ENV DATABASE_URL=postgresql://dataflux_user:secure_password_here@dataflux-postgres:5432/dataflux
ENV REDIS_URL=redis://dataflux-redis:6379
ENV INGESTION_SERVICE_URL=http://dataflux-ingestion:2013

# Run the application
CMD ["python", "-B", "src/api_processor.py"]