# Use Python 3.11 slim image as base
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV DOCKER_CONTAINER=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libgl1-mesa-dev \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgthread-2.0-0 \
    libgtk-3-0 \
    libgstreamer1.0-0 \
    libgstreamer-plugins-base1.0-0 \
    libavcodec-dev \
    libavformat-dev \
    libswscale-dev \
    libv4l-dev \
    libxvidcore-dev \
    libx264-dev \
    ffmpeg \
    git \
    wget \
    curl \
    ca-certificates \
    python3-dbus \
    dbus-x11  \
    && rm -rf /var/lib/apt/lists/*

# Create app directory and non-root user
RUN useradd -m -u 1000 appuser
WORKDIR /app

# Create necessary directories
RUN mkdir -p /app/data/recordings \
    /app/data/logs \
    /app/data/cache \
    && chown -R appuser:appuser /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Change ownership of app directory and all subfolders after copying code
RUN chown -R appuser:appuser /app /app/data /app/data/recordings /app/data/logs /app/data/cache

# Switch to non-root user
USER appuser

ENV YOLO_CONFIG_DIR=/app/data/cache/ultralytics
RUN mkdir -p /app/data/cache/ultralytics && chown -R appuser:appuser /app/data/cache/ultralytics

# Create .env file template if it doesn't exist
RUN if [ ! -f .env ]; then \
    echo "RTSP_USERNAME=username" > .env && \
    echo "RTSP_PASSWORD=password" >> .env && \
    echo "RTSP_IP=192.168.1.3" >> .env && \
    echo "RTSP_PORT=554" >> .env && \
    echo "RTSP_STREAM=stream1" >> .env; \
    fi

# Expose Flask port (using less common port)
EXPOSE 8847

# Create snapshots directory for web app
RUN mkdir -p /app/snapshots && chown -R appuser:appuser /app/snapshots

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8847/ || exit 1

# Default command - run Flask in production mode with Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8847", "--timeout", "120", "app:app"]
