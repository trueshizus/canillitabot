# Multi-stage build for optimized production images

# Build stage - includes build dependencies and creates the venv
FROM python:3.11-slim AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Create and activate virtual environment
ENV VIRTUAL_ENV=/opt/venv
RUN python -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Copy requirements and install dependencies into the venv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install development dependencies
RUN pip install --no-cache-dir \
    flake8 \
    black \
    mypy \
    pytest

# Download NLTK data
RUN python -c "import nltk; nltk.download('punkt', download_dir='/tmp/nltk_data')"

# Set working directory
WORKDIR /app

# ---

# Production stage - minimal runtime image
FROM python:3.11-slim AS production

# Install minimal runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user
RUN useradd --create-home --shell /bin/bash canillitabot

# Set working directory
WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder --chown=canillitabot:canillitabot /opt/venv /opt/venv

# Copy NLTK data from builder
COPY --from=builder /tmp/nltk_data /home/canillitabot/nltk_data

# Create directories for data and logs
RUN mkdir -p data logs
RUN chown -R canillitabot:canillitabot data logs

# Copy application code
COPY src/ ./src/
COPY config/ ./config/
COPY run.py ./
COPY docker_run.py ./
RUN chown -R canillitabot:canillitabot /app

# Set environment variables
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
ENV NLTK_DATA="/home/canillitabot/nltk_data"

# Switch to non-root user
USER canillitabot

# Health check
HEALTHCHECK --interval=5m --timeout=30s --start-period=30s --retries=3 CMD python -c "from src.core.database import Database; from src.core.config import Config; db = Database(Config()); print('OK')" || exit 1

# Default command
CMD ["python", "run.py"]
