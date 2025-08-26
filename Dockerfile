# Multi-stage build for optimized production images

# Build stage - includes build dependencies
FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Download NLTK data
RUN python -c "import nltk; nltk.download('punkt', download_dir='/tmp/nltk_data')"

# Production stage - minimal runtime image
FROM python:3.11-slim as production

# Install minimal runtime dependencies
RUN apt-get update && apt-get install -y \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user
RUN useradd --create-home --shell /bin/bash canillitabot

# Set working directory
WORKDIR /app

# Copy Python packages from builder
COPY --from=builder /root/.local /home/canillitabot/.local

# Copy NLTK data from builder
COPY --from=builder /tmp/nltk_data /home/canillitabot/nltk_data

# Create directories for data and logs
RUN mkdir -p data logs

# Copy application code
COPY src/ ./src/
COPY config/ ./config/
COPY run.py ./

# Set permissions
RUN chown -R canillitabot:canillitabot /app

# Set environment variables
ENV PYTHONPATH=/app
ENV PATH="/home/canillitabot/.local/bin:$PATH"
ENV NLTK_DATA="/home/canillitabot/nltk_data"

# Switch to non-root user
USER canillitabot

# Health check
HEALTHCHECK --interval=5m --timeout=30s --start-period=30s --retries=3 \
    CMD python -c "import sys; sys.path.insert(0, '/app/src'); from database import Database; from config import Config; db = Database(Config()); print('OK')" || exit 1

# Default command
CMD ["python", "run.py"]

# Development stage - includes all development tools
FROM builder as development

# Install development dependencies
RUN pip install --no-cache-dir \
    pytest \
    flake8 \
    black \
    mypy

# Create non-root user
RUN useradd --create-home --shell /bin/bash canillitabot

# Set working directory
WORKDIR /app

# Create directories
RUN mkdir -p data logs tests

# Copy application code
COPY . .

# Set permissions
RUN chown -R canillitabot:canillitabot /app

# Set environment variables
ENV PYTHONPATH=/app
ENV NLTK_DATA="/tmp/nltk_data"

# Switch to non-root user
USER canillitabot

# Default command for development
CMD ["python", "run.py"]