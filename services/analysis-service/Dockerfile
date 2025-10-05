FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libjpeg-dev \
    libpng-dev \
    libtiff-dev \
    python3-dev \
    libglib2.0-dev \
    libgtk-3-dev \
    libavcodec-dev \
    libavformat-dev \
    libswscale-dev \
    libv4l-dev \
    libxvidcore-dev \
    libx264-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY analyzers/ ./analyzers/

# Expose port
EXPOSE 2014

# Set environment variables
ENV DATABASE_URL=postgresql://dataflux_user:secure_password_here@dataflux-postgres:5432/dataflux
ENV REDIS_URL=redis://dataflux-redis:6379
ENV INGESTION_SERVICE_URL=http://dataflux-ingestion:2013

# Run the application
CMD ["python", "-B", "src/api_processor.py"]