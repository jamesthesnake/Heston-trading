#!/bin/bash
# Heston Trading System - Foolproof Setup Script
# This script does EVERYTHING needed to get the system running

set -e  # Exit immediately on any error

# Colors for better output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "\n${BLUE}============================================================${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}============================================================${NC}\n"
}

# Welcome message
print_header "HESTON TRADING SYSTEM - AUTOMATED SETUP"
echo "This script will:"
echo "✅ Check Python 3.11 installation"
echo "✅ Create a clean virtual environment" 
echo "✅ Install all required dependencies"
echo "✅ Start the trading system with live data"
echo "✅ Open the dashboard in your browser"
echo ""

# Check if we're in the right directory
if [ ! -f "setup_and_run_v2.sh" ]; then
    print_error "Please run this script from the Heston-trading directory"
    echo "Example:"
    echo "  cd /path/to/Heston-trading"
    echo "  ./setup_and_run_v2.sh"
    exit 1
fi

print_success "✓ Found Heston-trading directory"

# Check Python 3.11
print_status "Checking Python 3.11 installation..."

if command -v python3.11 &> /dev/null; then
    PYTHON_VERSION=$(python3.11 --version 2>&1)
    print_success "✓ Found: $PYTHON_VERSION"
    PYTHON_CMD="python3.11"
elif command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1)
    if [[ $PYTHON_VERSION == *"3.11"* ]]; then
        print_success "✓ Found: $PYTHON_VERSION (using python3)"
        PYTHON_CMD="python3"
    else
        print_warning "Found Python 3, but not version 3.11: $PYTHON_VERSION"
        print_error "Python 3.11 is required for this system"
        echo ""
        echo "Please install Python 3.11:"
        echo "  On macOS: brew install python@3.11"
        echo "  On Ubuntu: sudo apt install python3.11 python3.11-venv"
        echo "  Then run this script again"
        exit 1
    fi
else
    print_error "Python 3.11 not found!"
    echo ""
    echo "Please install Python 3.11:"
    echo "  On macOS: brew install python@3.11"  
    echo "  On Ubuntu: sudo apt install python3.11 python3.11-venv"
    echo "  Then run this script again"
    exit 1
fi

# Clean up any existing environment
print_status "Cleaning up any existing virtual environment..."
if [ -d "heston_venv_auto" ]; then
    print_status "Removing old virtual environment..."
    rm -rf heston_venv_auto
fi

# Create virtual environment
print_status "Creating fresh virtual environment..."
$PYTHON_CMD -m venv heston_venv_auto
print_success "✓ Virtual environment created"

# Activate virtual environment
print_status "Activating virtual environment..."
source heston_venv_auto/bin/activate
print_success "✓ Virtual environment activated"

# Upgrade pip
print_status "Upgrading pip to latest version..."
pip install --upgrade pip --quiet
print_success "✓ pip upgraded"

# Install core dependencies first (most likely to succeed)
print_status "Installing core dependencies..."
pip install --quiet \
    numpy \
    scipy \
    pandas \
    pyyaml \
    click \
    flask \
    dash \
    plotly \
    requests

print_success "✓ Core dependencies installed"

# Install additional requirements
print_status "Installing additional requirements..."
if [ -f "requirements-working.txt" ]; then
    print_status "Installing from requirements-working.txt..."
    pip install -r requirements-working.txt --quiet
    print_success "✓ All requirements installed from requirements-working.txt"
else
    print_warning "requirements-working.txt not found, installing manually..."
    pip install --quiet \
        prometheus-client \
        psutil \
        websocket-client \
        python-dotenv \
        colorama \
        tabulate
    print_success "✓ Additional requirements installed manually"
fi

# Test imports to make sure everything works
print_status "Testing installation..."
python -c "
import numpy, pandas, scipy, yaml, click, flask, dash, plotly
print('✓ All core packages import successfully')
"
print_success "✓ Installation test passed"

# Set up environment
print_status "Setting up environment..."
export PYTHONPATH=$(pwd):$PYTHONPATH

# Kill any existing processes on our ports
print_status "Checking for existing processes..."
if lsof -Pi :8050 -sTCP:LISTEN -t >/dev/null 2>&1; then
    print_warning "Port 8050 is in use, attempting to free it..."
    pkill -f "python.*start_system" 2>/dev/null || true
    sleep 2
fi

if lsof -Pi :9090 -sTCP:LISTEN -t >/dev/null 2>&1; then
    print_warning "Port 9090 is in use, attempting to free it..."
    pkill -f "python.*start_system" 2>/dev/null || true
    sleep 2
fi

# Start the system
print_header "STARTING HESTON TRADING SYSTEM"
print_status "Launching trading system with enhanced mock data..."

# Start the system in the background and capture the PID
python scripts/start_system.py --env=development --mock &
SYSTEM_PID=$!

# Wait a moment for startup
print_status "Waiting for system to initialize..."
sleep 5

# Check if the system is running
if kill -0 $SYSTEM_PID 2>/dev/null; then
    print_success "✓ Trading system is running (PID: $SYSTEM_PID)"
else
    print_error "System failed to start properly"
    exit 1
fi

# Test dashboard accessibility
print_status "Testing dashboard accessibility..."
for i in {1..10}; do
    if curl -s http://localhost:8050 >/dev/null 2>&1; then
        print_success "✓ Dashboard is accessible"
        break
    else
        if [ $i -eq 10 ]; then
            print_error "Dashboard not accessible after 10 attempts"
            print_error "Please check the terminal output above for errors"
            exit 1
        fi
        print_status "Waiting for dashboard... (attempt $i/10)"
        sleep 2
    fi
done

# Success message
print_header "🎉 SETUP COMPLETE! 🎉"
echo ""
print_success "🌐 Trading Dashboard: http://localhost:8050"
print_success "📊 System Metrics:    http://localhost:9090/metrics"
echo ""
echo -e "${GREEN}Your Heston Trading System is now running with:${NC}"
echo "✅ Live SPX/SPY/VIX price simulation"
echo "✅ 700+ options contracts with real pricing"
echo "✅ Active trading positions with P&L tracking"
echo "✅ Real-time risk monitoring"
echo "✅ Professional trading dashboard"
echo ""
echo -e "${YELLOW}🎮 Try the demo:${NC}"
echo "  python demo_data.py"
echo ""
echo -e "${YELLOW}🛑 To stop the system:${NC}"
echo "  Press Ctrl+C in this terminal"
echo ""
echo -e "${BLUE}📖 For help, see README_SIMPLE.md${NC}"
echo ""

# Try to open browser (optional)
if command -v open &> /dev/null; then
    print_status "Opening dashboard in your default browser..."
    open http://localhost:8050
elif command -v xdg-open &> /dev/null; then
    print_status "Opening dashboard in your default browser..."
    xdg-open http://localhost:8050
else
    print_warning "Could not auto-open browser. Please visit http://localhost:8050 manually"
fi

# Keep the script running and show live status
echo ""
print_status "System is running. Press Ctrl+C to stop..."
echo ""

# Function to cleanup on exit
cleanup() {
    echo ""
    print_status "Shutting down trading system..."
    kill $SYSTEM_PID 2>/dev/null || true
    wait $SYSTEM_PID 2>/dev/null || true
    print_success "✓ System stopped"
    print_status "Thank you for using Heston Trading System!"
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Wait for the system process
wait $SYSTEM_PID