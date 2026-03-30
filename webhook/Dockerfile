FROM python:3.11-slim

WORKDIR /app

# Install dependencies first (better caching)
COPY webhook/requirements.txt ./webhook/
RUN pip install --no-cache-dir -r webhook/requirements.txt

# Copy application code
COPY webhook/ ./webhook/
COPY athletes/ ./athletes/

# Set environment variables
ENV ATHLETES_DIR=/app/athletes
ENV SCRIPTS_DIR=/app/athletes/scripts
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
