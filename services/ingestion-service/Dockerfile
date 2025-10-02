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

# Create storage directory
RUN mkdir -p /tmp/dataflux_storage

# Expose port
EXPOSE 2013

# Set environment variables
ENV DATABASE_URL=postgresql://dataflux_user:secure_password_here@dataflux-postgres:5432/dataflux
ENV REDIS_URL=redis://dataflux-redis:6379

# Run the application
CMD ["python", "-B", "src/main_simple.py"]