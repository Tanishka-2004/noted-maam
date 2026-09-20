# ==============================================================================
# Stage 1: Dependency Builder
# ==============================================================================
FROM python:3.12-slim-bookworm AS builder

WORKDIR /build

# Install system compilation packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Cache dependency layer
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt


# ==============================================================================
# Stage 2: Runtime Production Image
# ==============================================================================
FROM python:3.12-slim-bookworm AS final

# Standard environment settings
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/home/appuser/.local/bin:${PATH}"

# Install postgres lib runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Add non-root system user
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g 10001 -m -s /sbin/nologin appuser

WORKDIR /app

# Copy python dependencies from builder stage
COPY --from=builder --chown=appuser:appgroup /root/.local /home/appuser/.local
COPY --chown=appuser:appgroup . .

# Set running context to non-root user
USER appuser

# Expose FastAPI default port
EXPOSE 8000

# Docker-native Healthcheck using native python library (no external curl dependency)
HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=3)"

# Run command
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
