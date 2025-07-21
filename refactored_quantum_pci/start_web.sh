#!/bin/bash
# QUANTUM-PCI Web Interface Quick Start Script

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Default values
HOST="0.0.0.0"
PORT="8000"
DEBUG=false
DEVICE=""

# Print banner
print_banner() {
    echo -e "${PURPLE}============================================================${NC}"
    echo -e "${PURPLE}🚀 QUANTUM-PCI Web Interface v2.0 - Quick Start${NC}"
    echo -e "${PURPLE}============================================================${NC}"
}

# Print help
print_help() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -h, --help       Show this help message"
    echo "  -p, --port PORT  Port to bind to (default: 8000)"
    echo "  -H, --host HOST  Host to bind to (default: 0.0.0.0)"
    echo "  -d, --debug      Enable debug mode"
    echo "  -D, --device DEV Device path (optional)"
    echo ""
    echo "Examples:"
    echo "  $0                    # Start on default port 8000"
    echo "  $0 -p 8080           # Start on port 8080"
    echo "  $0 -d                # Start in debug mode"
    echo "  $0 -H 127.0.0.1      # Bind to localhost only"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            print_help
            exit 0
            ;;
        -p|--port)
            PORT="$2"
            shift 2
            ;;
        -H|--host)
            HOST="$2"
            shift 2
            ;;
        -d|--debug)
            DEBUG=true
            shift
            ;;
        -D|--device)
            DEVICE="$2"
            shift 2
            ;;
        *)
            echo -e "${RED}❌ Unknown option: $1${NC}"
            print_help
            exit 1
            ;;
    esac
done

# Print banner
print_banner

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 is not installed or not in PATH${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Python 3 found${NC}"

# Add local bin to PATH if not already there
LOCAL_BIN="$HOME/.local/bin"
if [[ ":$PATH:" != *":$LOCAL_BIN:"* ]]; then
    export PATH="$PATH:$LOCAL_BIN"
    echo -e "${YELLOW}🔧 Added $LOCAL_BIN to PATH${NC}"
fi

# Check if web dependencies are installed
echo -e "${BLUE}🔍 Checking web dependencies...${NC}"

check_dependency() {
    local dep=$1
    if python3 -c "import $dep" 2>/dev/null; then
        echo -e "${GREEN}✅ $dep${NC}"
        return 0
    else
        echo -e "${RED}❌ $dep${NC}"
        return 1
    fi
}

deps_ok=true
check_dependency "fastapi" || deps_ok=false
check_dependency "uvicorn" || deps_ok=false
check_dependency "websockets" || deps_ok=false
check_dependency "jinja2" || deps_ok=false

if [ "$deps_ok" = false ]; then
    echo -e "${YELLOW}⚠️  Some web dependencies are missing${NC}"
    echo -e "${CYAN}📦 Installing dependencies...${NC}"
    
    if python3 install_web_deps.py; then
        echo -e "${GREEN}✅ Dependencies installed successfully${NC}"
    else
        echo -e "${RED}❌ Failed to install dependencies${NC}"
        echo -e "${YELLOW}💡 Try manual installation:${NC}"
        echo "pip3 install --break-system-packages fastapi uvicorn[standard] websockets jinja2 python-multipart"
        exit 1
    fi
fi

# Prepare arguments
ARGS=("--host" "$HOST" "--port" "$PORT")

if [ "$DEBUG" = true ]; then
    ARGS+=("--debug")
fi

if [ -n "$DEVICE" ]; then
    ARGS+=("--device" "$DEVICE")
fi

# Start the web server
echo -e "${PURPLE}============================================================${NC}"
echo -e "${GREEN}🚀 Starting QUANTUM-PCI Web Interface${NC}"
echo -e "${PURPLE}============================================================${NC}"
echo -e "${CYAN}📡 Web Interface: http://$HOST:$PORT/${NC}"
echo -e "${CYAN}📚 API Docs:      http://$HOST:$PORT/docs${NC}"
echo -e "${CYAN}🔍 API Explorer:  http://$HOST:$PORT/redoc${NC}"
echo -e "${CYAN}💓 Health Check:  http://$HOST:$PORT/api/health${NC}"
echo -e "${PURPLE}============================================================${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop the server${NC}"
echo ""

# Check if the port is already in use
if command -v netstat &> /dev/null; then
    if netstat -tuln | grep -q ":$PORT "; then
        echo -e "${YELLOW}⚠️  Port $PORT appears to be in use${NC}"
        echo -e "${YELLOW}   The server might not start properly${NC}"
        echo ""
    fi
fi

# Run the web server
exec python3 web_server.py "${ARGS[@]}"