#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Load environment variables
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
    echo -e "${GREEN}✅ Environment variables loaded from .env${NC}"
else
    echo -e "${YELLOW}⚠️  No .env file found, using defaults${NC}"
fi

# Set scaling from .env or use defaults
BACKEND_SCALE=${BACKEND_SCALE:-8}
WORKER_FAST_SCALE=${WORKER_FAST_SCALE:-6}
GUNICORN_WORKERS=${GUNICORN_WORKERS:-8}
WORKER_FAST_CONCURRENCY=${WORKER_FAST_CONCURRENCY:-8}

echo -e "${BLUE}🚀 Starting application with scaling:${NC}"
echo -e "   - Backend instances: ${BACKEND_SCALE}"
echo -e "   - Worker-fast instances: ${WORKER_FAST_SCALE}"
echo -e "   - Gunicorn workers per backend: ${GUNICORN_WORKERS}"
echo -e "   - Worker concurrency: ${WORKER_FAST_CONCURRENCY}"

# Stop and remove existing containers
echo -e "\n${YELLOW}🛑 Stopping existing containers...${NC}"
docker-compose -f docker-compose.prod.yml down

# Build and start with scaling
echo -e "\n${BLUE}🔨 Building and starting containers...${NC}"
docker-compose -f docker-compose.prod.yml up -d --build --scale backend=$BACKEND_SCALE --scale worker-fast=$WORKER_FAST_SCALE

# Wait for services to start
echo -e "\n${YELLOW}⏳ Waiting for services to initialize (10 seconds)...${NC}"
sleep 10

# Health checks
echo -e "\n${BLUE}🔍 Running health checks...${NC}"

# Check container status
echo -e "\n${YELLOW}📊 Container Status:${NC}"
docker-compose -f docker-compose.prod.yml ps

# Check database connections
echo -e "\n${YELLOW}🗄️  Database Connections:${NC}"
for i in $(seq 1 $BACKEND_SCALE); do
    container_name="ewa_back-backend-${i}"
    if docker ps --format "table {{.Names}}" | grep -q "$container_name"; then
        echo -n "Backend-${i}: "
        docker exec $container_name python -c "
from django.db import connection
try:
    connection.ensure_connection()
    print('✅ DB OK')
except Exception as e:
    print('❌ DB FAIL')
" 2>/dev/null || echo -e "${RED}❌ Container not ready${NC}"
    else
        echo -e "Backend-${i}: ${RED}❌ Not running${NC}"
    fi
done

# Check worker status
echo -e "\n${YELLOW}👷 Worker Status:${NC}"
for i in $(seq 1 $WORKER_FAST_SCALE); do
    container_name="ewa_back-worker-fast-${i}"
    if docker ps --format "table {{.Names}}" | grep -q "$container_name"; then
        echo -e "Worker-fast-${i}: ${GREEN}✅ Running${NC}"
    else
        echo -e "Worker-fast-${i}: ${RED}❌ Not running${NC}"
    fi
done

# Check Redis connection
echo -e "\n${YELLOW}🔴 Redis Connection:${NC}"
docker exec ewa_redis redis-cli ping | grep -q "PONG" && echo -e "Redis: ${GREEN}✅ Connected${NC}" || echo -e "Redis: ${RED}❌ Failed${NC}"

# Display port mappings
echo -e "\n${YELLOW}🌐 Port Mappings:${NC}"
echo "Backend instances are available on ports: 8000-$((8000 + BACKEND_SCALE - 1))"
echo "Flower monitoring: http://localhost:5555"

# Show quick monitoring commands
echo -e "\n${GREEN}📈 Quick Monitoring Commands:${NC}"
echo -e "  ${BLUE}View all logs:${NC}    docker-compose -f docker-compose.prod.yml logs -f"
echo -e "  ${BLUE}View backend logs:${NC} docker-compose -f docker-compose.prod.yml logs -f backend"
echo -e "  ${BLUE}View worker logs:${NC}  docker-compose -f docker-compose.prod.yml logs -f worker-fast"
echo -e "  ${BLUE}Container status:${NC}  docker-compose -f docker-compose.prod.yml ps"
echo -e "  ${BLUE}Resource usage:${NC}    docker stats --no-stream"

echo -e "\n${GREEN}🎯 Application started successfully!${NC}"