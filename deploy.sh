#!/bin/bash

# 🚀 CanillitaBot Manual Deployment Script
# Usage: ./deploy.sh

set -e  # Exit on any error

echo "🚀 Starting CanillitaBot deployment..."

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if we can connect to the server
echo "🔍 Testing SSH connection..."
if ssh -o ConnectTimeout=5 bot 'echo "Connection successful"' >/dev/null 2>&1; then
    print_status "SSH connection established"
else
    print_error "Cannot connect to server. Check your SSH configuration."
    exit 1
fi

# Deploy to server
echo "📦 Deploying to production server..."
ssh bot << 'EOF'
set -e

cd canillitabot

echo "📂 Current directory: $(pwd)"
echo "🔍 Current commit: $(git log --oneline -n 1)"

# Backup current state
echo "💾 Creating backup..."
git stash push -m "Pre-deployment backup $(date)"

# Pull latest changes
echo "📥 Pulling latest changes..."
git fetch origin
git reset --hard origin/main

echo "✅ Updated to commit: $(git log --oneline -n 1)"

# Check if Docker is running
if ! docker compose ps >/dev/null 2>&1; then
    echo "⚠️  Docker Compose not running, starting fresh..."
fi

# Stop containers
echo "🛑 Stopping containers..."
docker compose down

# Rebuild with no cache to ensure fresh build
echo "🔨 Rebuilding containers..."
docker compose build --no-cache

# Start containers
echo "🚀 Starting containers..."
docker compose up -d

# Wait for health check
echo "🏥 Waiting for services to be healthy..."
sleep 30

# Check status
echo "📊 Deployment status:"
docker compose ps

# Show recent logs
echo "📜 Recent logs:"
docker compose logs --tail=10 canillitabot

# Check if bot is healthy
if docker compose ps | grep -q "healthy"; then
    echo "✅ Deployment successful! Bot is healthy and running."
else
    echo "⚠️  Deployment completed but health check pending..."
fi

EOF

print_status "Deployment completed!"
echo ""
echo "🔍 To monitor the bot:"
echo "  ssh bot 'cd canillitabot && docker compose logs -f canillitabot'"
echo ""
echo "📊 To check status:"
echo "  ssh bot 'cd canillitabot && docker compose ps'"
