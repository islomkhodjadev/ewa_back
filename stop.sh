#!/bin/bash

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}🛑 Stopping all services...${NC}"

# Stop containers
docker-compose -f docker-compose.prod.yml down

echo -e "${GREEN}✅ All services stopped${NC}"

# Optional: Remove volumes (uncomment if you want to reset data)
# echo -e "${YELLOW}🗑️  Removing volumes...${NC}"
# docker volume rm ewa_back_db_data ewa_back_redis_data