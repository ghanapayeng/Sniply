# Production Dockerfile for Sniply Backend
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app:/app/backend \
    PORT=5000 \
    FLASK_ENV=production

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create application user
RUN useradd -m -u 1000 appuser

WORKDIR /app

# Copy dependency requirements
COPY requirements.txt ./backend/

# Install Python packages
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r ./backend/requirements.txt

# Copy backend application code into /app/backend
COPY . /app/backend/

# Set ownership to appuser
RUN chown -R appuser:appuser /app

USER appuser
WORKDIR /app/backend

EXPOSE 5000

# Container healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Start via production WSGI server Gunicorn
CMD ["gunicorn", "--config", "gunicorn.conf.py", "wsgi:app"]
