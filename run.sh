#!/bin/bash

# Script to run both backend and frontend services
# Usage: ./run.sh [--no-backend] [--no-frontend] [--detach]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
RUN_BACKEND=true
RUN_FRONTEND=true
DETACH=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --no-backend)
            RUN_BACKEND=false
            shift
            ;;
        --no-frontend)
            RUN_FRONTEND=false
            shift
            ;;
        --detach)
            DETACH=true
            shift
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Usage: $0 [--no-backend] [--no-frontend] [--detach]"
            exit 1
            ;;
    esac
done

# Get the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Function to check if a port is in use
check_port() {
    local port=$1
    # Try multiple methods to check port availability
    if command -v lsof >/dev/null 2>&1; then
        if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1 ; then
            return 0  # Port is in use
        fi
    elif command -v netstat >/dev/null 2>&1; then
        if netstat -tuln 2>/dev/null | grep -q ":$port " ; then
            return 0  # Port is in use
        fi
    elif command -v ss >/dev/null 2>&1; then
        if ss -tuln 2>/dev/null | grep -q ":$port " ; then
            return 0  # Port is in use
        fi
    fi
    return 1  # Port appears to be free (or we can't check)
}

# Function to cleanup on exit
cleanup() {
    echo -e "\n${YELLOW}Shutting down services...${NC}"
    
    if [ ! -z "$BACKEND_PID" ]; then
        echo -e "${BLUE}Stopping backend (PID: $BACKEND_PID)...${NC}"
        kill $BACKEND_PID 2>/dev/null || true
        wait $BACKEND_PID 2>/dev/null || true
    fi
    
    if [ ! -z "$FRONTEND_PID" ]; then
        echo -e "${BLUE}Stopping frontend (PID: $FRONTEND_PID)...${NC}"
        kill $FRONTEND_PID 2>/dev/null || true
        wait $FRONTEND_PID 2>/dev/null || true
    fi
    
    echo -e "${GREEN}All services stopped.${NC}"
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM EXIT

# Check if virtual environment exists
if [ "$RUN_BACKEND" = true ]; then
    if [ ! -d "venv" ]; then
        echo -e "${YELLOW}Virtual environment not found. Creating one...${NC}"
        python3 -m venv venv
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Check if uvicorn is installed
    if ! python -c "import uvicorn" 2>/dev/null; then
        echo -e "${YELLOW}Installing backend dependencies...${NC}"
        pip install -r requirements.txt
    fi
    
    # Check if port 8000 is available
    if check_port 8000; then
        echo -e "${RED}Port 8000 is already in use. Please stop the service using that port.${NC}"
        exit 1
    fi
fi

# Check frontend setup
if [ "$RUN_FRONTEND" = true ]; then
    if [ ! -d "frontend/node_modules" ]; then
        echo -e "${YELLOW}Frontend dependencies not found. Installing...${NC}"
        cd frontend
        npm install
        cd ..
    fi
    
    # Check if port 3000 (Vite configured port) is available
    if check_port 3000; then
        echo -e "${YELLOW}Port 3000 is already in use. Vite will use the next available port.${NC}"
    fi
fi

# Start backend
if [ "$RUN_BACKEND" = true ]; then
    echo -e "${GREEN}Starting backend server...${NC}"
    if [ "$DETACH" = true ]; then
        uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 > backend.log 2>&1 &
        BACKEND_PID=$!
        echo -e "${GREEN}Backend started in background (PID: $BACKEND_PID)${NC}"
        echo -e "${BLUE}Backend logs: tail -f backend.log${NC}"
    else
        uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
        BACKEND_PID=$!
        echo -e "${GREEN}Backend started (PID: $BACKEND_PID)${NC}"
    fi
    
    # Wait a moment for backend to start
    sleep 2
    
    # Check if backend started successfully
    if ! kill -0 $BACKEND_PID 2>/dev/null; then
        echo -e "${RED}Backend failed to start. Check the logs above.${NC}"
        exit 1
    fi
fi

# Start frontend
if [ "$RUN_FRONTEND" = true ]; then
    echo -e "${GREEN}Starting frontend server...${NC}"
    cd frontend
    
    if [ "$DETACH" = true ]; then
        npm run dev > ../frontend.log 2>&1 &
        FRONTEND_PID=$!
        echo -e "${GREEN}Frontend started in background (PID: $FRONTEND_PID)${NC}"
        echo -e "${BLUE}Frontend logs: tail -f frontend.log${NC}"
    else
        npm run dev &
        FRONTEND_PID=$!
        echo -e "${GREEN}Frontend started (PID: $FRONTEND_PID)${NC}"
    fi
    
    cd ..
    
    # Wait a moment for frontend to start
    sleep 2
    
    # Check if frontend started successfully
    if ! kill -0 $FRONTEND_PID 2>/dev/null; then
        echo -e "${RED}Frontend failed to start. Check the logs above.${NC}"
        exit 1
    fi
fi

# Print status
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Services are running!${NC}"
echo -e "${GREEN}========================================${NC}"
if [ "$RUN_BACKEND" = true ]; then
    echo -e "${BLUE}Backend API:${NC} http://localhost:8000"
    echo -e "${BLUE}API Docs:${NC} http://localhost:8000/docs"
fi
if [ "$RUN_FRONTEND" = true ]; then
    echo -e "${BLUE}Frontend:${NC} http://localhost:3000"
fi
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}"
echo ""

# If not detached, wait for processes
if [ "$DETACH" = false ]; then
    # Wait for both processes
    wait
else
    # In detached mode, just wait a bit then exit (processes run in background)
    sleep 1
    echo -e "${GREEN}Services are running in the background.${NC}"
    echo -e "${YELLOW}To stop them, use: pkill -f 'uvicorn app.main:app' && pkill -f 'vite'${NC}"
    exit 0
fi

