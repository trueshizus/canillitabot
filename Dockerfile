FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Download NLTK data (required for newspaper3k)
RUN python -c "import nltk; nltk.download('punkt')"

# Copy application code
COPY src/ ./src/
COPY config/ ./config/

# Create directories for data and logs
RUN mkdir -p data logs

# Set Python path
ENV PYTHONPATH=/app/src

# Create non-root user
RUN useradd --create-home --shell /bin/bash canillitabot
RUN chown -R canillitabot:canillitabot /app
USER canillitabot

# Health check
HEALTHCHECK --interval=5m --timeout=30s --start-period=30s --retries=3 \
    CMD python -c "import sys; sys.path.insert(0, '/app/src'); from database import Database; from config import Config; db = Database(Config()); print('OK')" || exit 1

# Default command
CMD ["python", "src/bot.py"]