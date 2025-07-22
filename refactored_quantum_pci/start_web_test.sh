#!/bin/bash
# Script to start QUANTUM-PCI Web Interface with test device

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

# Set test device path
TEST_DEVICE="$SCRIPT_DIR/test_device"

echo -e "${PURPLE}============================================================${NC}"
echo -e "${GREEN}🚀 Starting QUANTUM-PCI Web Interface (Test Mode)${NC}"
echo -e "${PURPLE}============================================================${NC}"
echo -e "${YELLOW}📂 Using test device at: $TEST_DEVICE${NC}"
echo -e "${PURPLE}============================================================${NC}"

# Start the web server with test device
./start_web.sh --device "$TEST_DEVICE" "$@"