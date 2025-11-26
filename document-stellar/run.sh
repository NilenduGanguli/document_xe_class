#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Document Services Management${NC}"
echo "=========================================="

# Function to display usage
usage() {
    echo "Usage: $0 {build|up|down|restart|logs|status|backend-logs|frontend-logs|db-info}"
    echo ""
    echo "Commands:"
    echo "  build           - Build the Docker images"
    echo "  up              - Start document services with embedded SQLite"
    echo "  down            - Stop and remove all services"
    echo "  restart         - Restart all services"
    echo "  logs            - Show all container logs"
    echo "  backend-logs    - Show backend logs only"
    echo "  frontend-logs   - Show frontend logs only"
    echo "  db-info         - Show SQLite database info"
    echo "  status          - Show container status"
    exit 1
}

# Check if command is provided
if [ $# -eq 0 ]; then
    usage
fi

# Source environment variables
if [ -f "./env.sh" ]; then
    source ./env.sh
fi

case "$1" in
    build)
        echo -e "${YELLOW}Building Docker images...${NC}"
        docker-compose build
        echo -e "${GREEN}Build complete!${NC}"
        ;;
    
    up)
        echo -e "${YELLOW}Starting document services...${NC}"
        docker-compose up -d
        
        echo -e "${GREEN}Services started!${NC}"
        echo -e "${GREEN}Landing Page: http://localhost:8080${NC}"
        echo -e "${GREEN}Classification API: http://localhost:8000/docs${NC}"
        echo -e "${GREEN}Classification UI: http://localhost:8502${NC}"
        echo -e "${GREEN}Extraction API: http://localhost:8001/docs${NC}"
        echo -e "${GREEN}Extraction UI: http://localhost:8501${NC}"
        echo -e "${GREEN}SQLite Database: Embedded in container volume${NC}"
        ;;
    
    down)
        echo -e "${YELLOW}Stopping and removing containers...${NC}"
        docker-compose down
        echo -e "${GREEN}Containers stopped and removed!${NC}"
        ;;
    
    restart)
        echo -e "${YELLOW}Restarting containers...${NC}"
        docker-compose restart
        echo -e "${GREEN}Containers restarted!${NC}"
        ;;
    
    logs)
        echo -e "${YELLOW}Showing all logs (Ctrl+C to exit)...${NC}"
        docker-compose logs -f
        ;;
    
    backend-logs)
        echo -e "${YELLOW}Showing backend logs (Ctrl+C to exit)...${NC}"
        docker logs -f document-stellar 2>&1 | grep -E "INFO|ERROR|WARNING|uvicorn"
        ;;
    
    frontend-logs)
        echo -e "${YELLOW}Showing frontend logs (Ctrl+C to exit)...${NC}"
        docker logs -f document-stellar 2>&1 | grep -i streamlit
        ;;
    
    db-info)
        echo -e "${YELLOW}SQLite Database Information${NC}"
        echo "Database location: Container volume /app/data/document_services.db"
        echo "Database type: SQLite (embedded)"
        echo "Schema loading: Automatic from schemas/ directory"
        echo ""
        echo "To check schemas in database:"
        echo "curl http://localhost:8001/download-schemas"
        ;;
    
    status)
        echo -e "${YELLOW}Container status:${NC}"
        docker-compose ps
        
        echo ""
        echo -e "${YELLOW}Testing endpoints:${NC}"
        
        # Test SQLite database (via API)
        if curl -s http://localhost:8001/ > /dev/null 2>&1; then
            echo -e "${GREEN}✓ SQLite Database (via API): Accessible${NC}"
        else
            echo -e "${RED}✗ SQLite Database (via API): Not accessible${NC}"
        fi
        
        # Test landing page
        if curl -s http://localhost:8080 > /dev/null 2>&1; then
            echo -e "${GREEN}✓ Landing Page (port 8080): Running${NC}"
        else
            echo -e "${RED}✗ Landing Page (port 8080): Not responding${NC}"
        fi
        
        # Test classification API
        if curl -s http://localhost:8000/ > /dev/null 2>&1; then
            echo -e "${GREEN}✓ Classification API (port 8000): Running${NC}"
        else
            echo -e "${RED}✗ Classification API (port 8000): Not responding${NC}"
        fi
        
        # Test extraction API
        if curl -s http://localhost:8001/ > /dev/null 2>&1; then
            echo -e "${GREEN}✓ Extraction API (port 8001): Running${NC}"
        else
            echo -e "${RED}✗ Extraction API (port 8001): Not responding${NC}"
        fi
        
        # Test extraction UI
        if curl -s http://localhost:8501/_stcore/health > /dev/null 2>&1; then
            echo -e "${GREEN}✓ Extraction UI (port 8501): Running${NC}"
        else
            echo -e "${RED}✗ Extraction UI (port 8501): Not responding${NC}"
        fi
        
        # Test classification UI
        if curl -s http://localhost:8502/_stcore/health > /dev/null 2>&1; then
            echo -e "${GREEN}✓ Classification UI (port 8502): Running${NC}"
        else
            echo -e "${RED}✗ Classification UI (port 8502): Not responding${NC}"
        fi
        ;;
    
    *)
        echo -e "${RED}Invalid command: $1${NC}"
        usage
        ;;
esac
