#!/bin/bash

# Simple script to run both backend and frontend services
# This version runs both in the foreground with output

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Function to cleanup on exit
cleanup() {
    echo -e "\n${YELLOW}Shutting down services...${NC}"
    jobs -p | xargs -r kill 2>/dev/null || true
    echo -e "${GREEN}All services stopped.${NC}"
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM EXIT

# Check and setup backend
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo -e "${YELLOW}Virtual environment not found. Please create it first:${NC}"
    echo "  python3 -m venv venv"
    echo "  source venv/bin/activate"
    echo "  pip install -r requirements.txt"
    exit 1
fi

# Check and setup frontend
if [ ! -d "frontend/node_modules" ]; then
    echo -e "${YELLOW}Frontend dependencies not found. Installing...${NC}"
    cd frontend
    npm install
    cd ..
fi

# Start backend
echo -e "${GREEN}Starting backend server on http://localhost:8000${NC}"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Wait a moment for backend to start
sleep 2

# Start frontend
echo -e "${GREEN}Starting frontend server...${NC}"
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

# Wait a moment for frontend to start
sleep 2

# Print status
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Services are running!${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "${BLUE}Backend API:${NC} http://localhost:8000"
echo -e "${BLUE}API Docs:${NC} http://localhost:8000/docs"
echo -e "${BLUE}Frontend:${NC} http://localhost:5173"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}"
echo ""

# Wait for all background jobs
wait

