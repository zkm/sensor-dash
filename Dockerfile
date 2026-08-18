# Multi-stage build for Raspberry Pi deployment
# Supports ARM32v7 (Pi 3/4/Zero) and ARM64v8 (Pi 4 with 64-bit OS)

FROM python:3.11-alpine

# Install system dependencies for sensor reading
RUN apk add --no-cache \
    lm-sensors \
    curl

# Set working directory
WORKDIR /app

# Copy requirements first for better layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY sensor_dash_server.py .
COPY sensor_dash.html .
COPY sensor_dash_kiosk.html .
COPY docs/TEMPERATURE_MAPPING.md .

# Create non-root user for security
RUN adduser -D -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/api/sensors || exit 1

# Run the application
CMD ["python3", "sensor_dash_server.py"]
