FROM python:3.11-slim

WORKDIR /app

# System deps for WeasyPrint PDF generation
# WeasyPrint needs pango, cairo, gdk-pixbuf, and their font/text backends
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    libcairo2 \
    libglib2.0-0 \
    libharfbuzz0b \
    fonts-liberation \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies (including WeasyPrint for PDF generation)
COPY webhook/requirements.txt ./webhook/
RUN pip install --no-cache-dir -r webhook/requirements.txt && \
    python -c "import weasyprint; print(f'WeasyPrint {weasyprint.__version__} OK')"

# Copy application code (bust cache: 2026-03-31)
COPY webhook/ ./webhook/
COPY athletes/ ./athletes/

# Create persistent data directory (Railway volume mounts here)
RUN mkdir -p /data

# Set environment variables
ENV ATHLETES_DIR=/app/athletes
ENV SCRIPTS_DIR=/app/athletes/scripts
ENV DATA_DIR=/data
ENV PORT=8080
ENV FLASK_ENV=production

# Expose port
EXPOSE 8080

WORKDIR /app/webhook

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')" || exit 1

# Run with gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "--timeout", "300", "--graceful-timeout", "30", "app:app"]
