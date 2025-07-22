#!/bin/bash

# QUANTUM-PCI Monitoring Web Interface Startup Script
# This script properly starts the web interface with monitoring

set -e  # Exit on any error

echo "🚀 QUANTUM-PCI Monitoring Web Interface"
echo "======================================="

# Check if we're in the right directory
if [ ! -f "main.py" ]; then
    echo "❌ Error: main.py not found. Please run this script from the refactored_quantum_pci directory."
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies if needed
echo "📥 Installing dependencies..."
pip install -r requirements.txt -q

# Kill any existing process on port 8000
echo "🧹 Cleaning up existing processes on port 8000..."
fuser -k 8000/tcp 2>/dev/null || true
sleep 1

# Start the web interface
echo "🌐 Starting QUANTUM-PCI Monitoring Web Interface..."
echo ""
echo "   📡 Web Interface: http://localhost:8000/"
echo "   📚 API Docs:      http://localhost:8000/docs"
echo "   🔍 API Explorer:  http://localhost:8000/redoc"
echo "   💓 Health Check:  http://localhost:8000/api/health"
echo ""
echo "⚠️  Note: Running in limited mode (no hardware device detected)"
echo "   The interface will show simulated data and allow configuration testing."
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Start the server
python main.py --web --port 8000