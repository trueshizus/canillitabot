FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies (rarely changes)
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching (changes less frequently)
COPY requirements.txt .

# Install Python dependencies (cached unless requirements.txt changes)
RUN pip install --no-cache-dir -r requirements.txt

# Download NLTK data (cached unless requirements change)
RUN python -c "import nltk; nltk.download('punkt')"

# Create directories for data and logs
RUN mkdir -p data logs

# Create non-root user (rarely changes)
RUN useradd --create-home --shell /bin/bash canillitabot

# Copy application code (changes frequently - keep at end)
COPY src/ ./src/
COPY config/ ./config/
COPY run.py ./

# Set permissions
RUN chown -R canillitabot:canillitabot /app

# Set Python path
ENV PYTHONPATH=/app

# Switch to non-root user
USER canillitabot

# Health check (matches docker-compose)
HEALTHCHECK --interval=5m --timeout=30s --start-period=30s --retries=3 \
    CMD python -c "import sys; sys.path.insert(0, '/app/src'); from database import Database; from config import Config; db = Database(Config()); print('OK')" || exit 1

# Default command
CMD ["python", "run.py"]