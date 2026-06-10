FROM python:3.11-slim

WORKDIR /app

# System deps for PDF generation.
# Chromium is the PRIMARY engine: WeasyPrint takes 30+ min of CPU on Railway's
# shared vCPU for the full training guide (verified Jun 2026 — every order
# timed out), while Chromium renders it in seconds. WeasyPrint libs stay as a
# time-boxed fallback only.
RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium \
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
    && rm -rf /var/lib/apt/lists/* \
    && chromium --version

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

# Run with gunicorn.
# Worker timeout MUST exceed PIPELINE_TIMEOUT (app.py, default 480s) so the
# failure notification email can send before gunicorn kills the worker.
# A killed worker = no FAILED email AND Stripe retries hit the idempotency
# mark and return "duplicate" — the order dies silently.
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "--timeout", "600", "--graceful-timeout", "30", "app:app"]
