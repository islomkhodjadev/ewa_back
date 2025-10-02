#!/bin/bash

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Load environment
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

BACKEND_SCALE=${BACKEND_SCALE:-8}
WORKER_FAST_SCALE=${WORKER_FAST_SCALE:-6}

monitor_services() {
    echo -e "${BLUE}🔄 Monitoring Services - $(date)${NC}"
    echo "=========================================="
    
    # Container status
    echo -e "\n${YELLOW}📦 Container Status:${NC}"
    docker-compose -f docker-compose.prod.yml ps
    
    # Resource usage
    echo -e "\n${YELLOW}💾 Resource Usage:${NC}"
    docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}" | head -n $((BACKEND_SCALE + WORKER_FAST_SCALE + 6))
    
    # Database connections
    echo -e "\n${YELLOW}🗄️  Database Connections:${NC}"
    docker exec ewa_db_postgres psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} -c "
SELECT 
    application_name,
    COUNT(*) as connections,
    string_agg(client_addr::text, ', ') as clients
FROM pg_stat_activity 
WHERE datname = '${POSTGRES_DB}' AND application_name LIKE '%backend%'
GROUP BY application_name
ORDER BY connections DESC;" 2>/dev/null || echo "Database not accessible"
    
    # Redis info
    echo -e "\n${YELLOW}🔴 Redis Info:${NC}"
    docker exec ewa_redis redis-cli info memory | grep -E "(used_memory_human|used_memory_peak_human)" | while read line; do
        echo "  $line"
    done
    
    # Queue status (if Flower is running)
    echo -e "\n${YELLOW}📋 Celery Queue Status:${NC}"
    curl -s http://localhost:5555/api/queues | python -m json.tool 2>/dev/null | grep -E '(name|messages|consumers)' | head -12 || echo "  Flower not accessible"
}

# Continuous monitoring
if [ "$1" = "continuous" ]; then
    echo -e "${GREEN}Starting continuous monitoring (5 second intervals)...${NC}"
    echo "Press Ctrl+C to stop"
    while true; do
        clear
        monitor_services
        sleep 5
    done
else
    # Single monitoring run
    monitor_services
fi