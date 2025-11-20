#!/bin/bash
set -e

# Source environment variables
source /app/env.sh

echo "=========================================="
echo "Starting Document Services"
echo "=========================================="
echo "Classification API Port: 8000"
echo "Extraction API Port: 8001"
echo "Landing Page Port: 8080"
echo "Classification UI Port: 8502"
echo "Extraction UI Port: 8501"
echo "Database Path: ${DATABASE_PATH}"
echo "=========================================="

# Create database directory if it doesn't exist
echo "Setting up SQLite database..."
mkdir -p $(dirname "${DATABASE_PATH:-/app/data/document_services.db}")
echo "SQLite database directory ready!"

# Wait time for initialization
MAX_RETRIES=30

# Start Classification API (port 8000) in background
echo "Starting Classification API on port 8000..."
cd /app/backend
PORT=8000 python classification_main.py &
CLASSIFICATION_PID=$!
echo "Classification API started with PID: ${CLASSIFICATION_PID}"

# Start Extraction API (port 8001) in background
echo "Starting Extraction API on port 8001..."
PORT=8001 python extraction_main.py &
EXTRACTION_PID=$!
echo "Extraction API started with PID: ${EXTRACTION_PID}"

# Wait for Classification API to be ready
echo "Waiting for Classification API to be ready..."
RETRY_COUNT=0
until curl -s http://localhost:8000/ > /dev/null 2>&1; do
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ ${RETRY_COUNT} -ge ${MAX_RETRIES} ]; then
        echo "Classification API failed to start after ${MAX_RETRIES} retries"
        exit 1
    fi
    echo "Waiting for Classification API... (${RETRY_COUNT}/${MAX_RETRIES})"
    sleep 2
done
echo "Classification API is ready!"

# Wait for Extraction API to be ready
echo "Waiting for Extraction API to be ready..."
RETRY_COUNT=0
until curl -s http://localhost:8001/ > /dev/null 2>&1; do
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ ${RETRY_COUNT} -ge ${MAX_RETRIES} ]; then
        echo "Extraction API failed to start after ${MAX_RETRIES} retries"
        exit 1
    fi
    echo "Waiting for Extraction API... (${RETRY_COUNT}/${MAX_RETRIES})"
    sleep 2
done
echo "Extraction API is ready!"

# Start simple HTTP server for landing page (port 8080) in background
echo "Starting landing page server on port 8080..."
cd /app/frontend
python3 -m http.server 8080 &
LANDING_PID=$!
echo "Landing page started with PID: ${LANDING_PID}"

# Start Classification Streamlit UI (port 8502) in background
echo "Starting Classification UI (Streamlit) on port 8502..."
export CLASSIFICATION_API_URL="http://localhost:8000"
streamlit run classification_app.py --server.port=8502 --server.address=0.0.0.0 --logger.level=error > /dev/null 2>&1 &
CLASSIFICATION_UI_PID=$!
echo "Classification UI started with PID: ${CLASSIFICATION_UI_PID}"

# Start Extraction Streamlit UI (port 8501) in foreground
echo "Starting Extraction UI (Streamlit) on port 8501..."
echo "Container logs will show uvicorn API logs only (streamlit logs suppressed)"
# Update API_BASE_URL to point to extraction API on port 8001
export API_BASE_URL="http://localhost:8001"
exec streamlit run extraction_app.py --server.port=8501 --server.address=0.0.0.0 --logger.level=error > /dev/null 2>&1

