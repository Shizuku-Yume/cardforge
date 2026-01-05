# CardForge Multi-stage Dockerfile
# Stage 1: Frontend build
# Stage 2: Backend + Frontend static serving

# ============================================
# Stage 1: Build frontend assets
# ============================================
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

# Copy package files first for layer caching
COPY frontend/package*.json ./

# Install dependencies
RUN npm ci --only=production=false

# Copy frontend source
COPY frontend/ ./

# Build production assets
RUN npm run build

# ============================================
# Stage 2: Python backend with static files
# ============================================
FROM python:3.11-slim AS production

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    CARDFORGE_LOG_LEVEL=INFO \
    CARDFORGE_LOG_REDACT=true

WORKDIR /app

# Install system dependencies (for Pillow with full image format support)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libjpeg62-turbo \
    libpng16-16 \
    libwebp7 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY backend/ ./

# Copy frontend build output from Stage 1
COPY --from=frontend-builder /app/frontend/dist ./static

# Create non-root user for security
RUN groupadd -r cardforge && useradd -r -g cardforge cardforge \
    && chown -R cardforge:cardforge /app

USER cardforge

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" || exit 1

# Run uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
