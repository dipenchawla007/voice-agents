FROM python:3.11-slim

WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create a directory for GCP credentials
RUN mkdir -p /app/gcp-credentials

# Set environment variable for GCP credentials
ENV GOOGLE_APPLICATION_CREDENTIALS=/app/gcp-credentials/service-account.json

# Create a non-root user to run the application
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# The service account JSON should be mounted at runtime:
# docker run -v /path/to/service-account.json:/app/gcp-credentials/service-account.json ...

# For Cloud Run or GKE, use the provided service account
# No need to mount credentials as the container service account will be used

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"] 