#!/bin/bash

echo "=========================================="
echo "Document Services Module Structure Check"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

check_file() {
    if [ -f "$1" ]; then
        echo -e "${GREEN}✓${NC} $1"
        return 0
    else
        echo -e "${RED}✗${NC} $1 (MISSING)"
        return 1
    fi
}

check_dir() {
    if [ -d "$1" ]; then
        echo -e "${GREEN}✓${NC} $1/"
        return 0
    else
        echo -e "${RED}✗${NC} $1/ (MISSING)"
        return 1
    fi
}

echo "Checking directory structure..."
echo ""

# Root files
echo "=== Root Files ==="
check_file "docker-compose.yml"
check_file "Dockerfile"
check_file "requirements.txt"
check_file "README.md"
check_file "env.sh"
check_file "run.sh"
check_file ".gitignore"
check_file "entrypoint.sh"
echo ""

# Backend structure
echo "=== Backend Structure ==="
check_dir "backend"
check_file "backend/main.py"
check_dir "backend/src"
check_dir "backend/src/db"
check_file "backend/src/db/__init__.py"
check_file "backend/src/db/connection.py"
check_file "backend/src/db/models.py"
check_dir "backend/src/extractors"
check_file "backend/src/extractors/__init__.py"
check_file "backend/src/extractors/classifier.py"
check_file "backend/src/extractors/universal.py"
check_file "backend/src/extractors/schema_generator.py"
check_dir "backend/src/config"
check_file "backend/src/config/__init__.py"
check_file "backend/src/config/llm_config.py"
check_dir "backend/src/schemas"
check_file "backend/src/schemas/classification.py"
check_dir "backend/src/utils"
check_file "backend/src/utils/__init__.py"
check_file "backend/src/utils/schema_operations.py"
echo ""

# Frontend structure
echo "=== Frontend Structure ==="
check_dir "frontend"
check_file "frontend/app.py"
echo ""

# Check environment
echo "=== Environment Check ==="
if [ -f "env.sh" ]; then
    echo -e "${GREEN}✓${NC} env.sh file exists"
    
    # Check for required variables
    if grep -q "GOOGLE_API_KEY" env.sh; then
        if grep -q 'GOOGLE_API_KEY="${GOOGLE_API_KEY:-your_api_key_here}"' env.sh; then
            echo -e "${YELLOW}⚠${NC} GOOGLE_API_KEY not configured (still has placeholder)"
        else
            echo -e "${GREEN}✓${NC} GOOGLE_API_KEY appears to be configured"
        fi
    else
        echo -e "${RED}✗${NC} GOOGLE_API_KEY not found in env.sh"
    fi
else
    echo -e "${RED}✗${NC} env.sh file not found"
fi
echo ""

# Check if Docker is running
echo "=== Docker Check ==="
if docker info >/dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Docker is running"
else
    echo -e "${RED}✗${NC} Docker is not running"
fi
echo ""

# Summary
echo "=========================================="
echo "Structure check complete!"
echo ""
echo "Next steps:"
echo "1. Edit env.sh and add your GOOGLE_API_KEY"
echo "2. Run: ./run.sh build"
echo "3. Run: ./run.sh up"
echo "4. Check status: ./run.sh status"
echo "5. Access frontend at: http://localhost:8501"
echo "6. Access API docs at: http://localhost:8000/docs"
echo "=========================================="
