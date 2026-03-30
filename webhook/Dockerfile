FROM python:3.11-slim

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser -u 1001 appuser

WORKDIR /app

# Install dependencies first (better caching)
COPY webhook/requirements.txt ./webhook/
RUN pip install --no-cache-dir -r webhook/requirements.txt

# Copy application code
COPY webhook/ ./webhook/
COPY athletes/ ./athletes/

# Set base ownership
RUN chown -R appuser:appuser /app

# Set environment variables
ENV ATHLETES_DIR=/app/athletes
ENV SCRIPTS_DIR=/app/athletes/scripts
ENV PORT=8080
ENV FLASK_ENV=production

# Expose port
EXPOSE 8080

WORKDIR /app/webhook

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')" || exit 1

# Start as root to fix volume permissions, then drop to appuser via gunicorn
# Railway volumes mount as root, so appuser can't write without this
CMD chown -R appuser:appuser /app/athletes 2>/dev/null; \
    exec gunicorn --bind 0.0.0.0:8080 --workers 2 --timeout 300 --graceful-timeout 30 --user appuser --group appuser app:app
