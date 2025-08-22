#!/bin/bash
# Heston Trading System - Advanced Setup Script v3
# Enhanced with Interactive Brokers integration and demo modes

set -e  # Exit immediately on any error

# Colors for better output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
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
    echo -e "\n${BOLD}${BLUE}============================================================${NC}"
    echo -e "${BOLD}${BLUE}  $1${NC}"
    echo -e "${BOLD}${BLUE}============================================================${NC}\n"
}

print_option() {
    echo -e "${CYAN}$1${NC} $2"
}

# Welcome message and mode selection
print_header "🎯 HESTON TRADING SYSTEM - ADVANCED SETUP v3"
echo "Choose your trading experience:"
echo ""
print_option "1)" "🎪 ENHANCED DEMO MODE (Recommended for first-time users)"
echo "   • 700+ simulated options with realistic pricing"
echo "   • Complete Heston strategy demonstration"
echo "   • Professional dashboard with live mock data"
echo "   • No external connections required"
echo ""
print_option "2)" "🚀 LIVE TRADING MODE (Interactive Brokers)"
echo "   • Real market data from Interactive Brokers"
echo "   • Live options chains and pricing"
echo "   • Paper trading or live trading capability"
echo "   • Requires IB Gateway/TWS setup"
echo ""
print_option "3)" "🔧 HYBRID MODE"
echo "   • Enhanced mock data with IB connection testing"
echo "   • Fallback to simulation if IB unavailable"
echo "   • Best of both worlds"
echo ""

read -p "Enter your choice (1-3): " MODE_CHOICE

case $MODE_CHOICE in
    1)
        TRADING_MODE="demo"
        print_success "✓ Enhanced Demo Mode selected"
        ;;
    2)
        TRADING_MODE="live"
        print_success "✓ Live Trading Mode selected"
        ;;
    3)
        TRADING_MODE="hybrid"
        print_success "✓ Hybrid Mode selected"
        ;;
    *)
        print_error "Invalid choice. Defaulting to Demo Mode."
        TRADING_MODE="demo"
        ;;
esac

print_header "SYSTEM SETUP BEGINNING"

# Check if we're in the right directory
if [ ! -f "setup_and_run_v3.sh" ]; then
    print_error "Please run this script from the Heston-trading directory"
    echo "Example:"
    echo "  cd /path/to/Heston-trading"
    echo "  ./setup_and_run_v3.sh"
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
if [ -d "heston_venv_v3" ]; then
    print_status "Removing old virtual environment..."
    rm -rf heston_venv_v3
fi

# Create virtual environment
print_status "Creating fresh virtual environment..."
$PYTHON_CMD -m venv heston_venv_v3
print_success "✓ Virtual environment created"

# Activate virtual environment
print_status "Activating virtual environment..."
source heston_venv_v3/bin/activate
print_success "✓ Virtual environment activated"

# Upgrade pip
print_status "Upgrading pip to latest version..."
pip install --upgrade pip --quiet
print_success "✓ pip upgraded"

# Install core dependencies first
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
    requests \
    websocket-client

print_success "✓ Core dependencies installed"

# Install mode-specific dependencies
if [ "$TRADING_MODE" = "live" ] || [ "$TRADING_MODE" = "hybrid" ]; then
    print_status "Installing Interactive Brokers dependencies..."
    pip install --quiet ibapi ib_insync
    print_success "✓ Interactive Brokers dependencies installed"
fi

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
        python-dotenv \
        colorama \
        tabulate
    print_success "✓ Additional requirements installed manually"
fi

# Test imports
print_status "Testing installation..."
python -c "
import numpy, pandas, scipy, yaml, click, flask, dash, plotly
print('✓ All core packages import successfully')
"

if [ "$TRADING_MODE" = "live" ] || [ "$TRADING_MODE" = "hybrid" ]; then
    python -c "
try:
    import ibapi
    print('✓ Interactive Brokers API available')
except ImportError:
    print('⚠️  Interactive Brokers API not available')
" 2>/dev/null || print_warning "IB API test failed"
fi

print_success "✓ Installation test passed"

# Interactive Brokers setup for live/hybrid modes
if [ "$TRADING_MODE" = "live" ] || [ "$TRADING_MODE" = "hybrid" ]; then
    print_header "📡 INTERACTIVE BROKERS SETUP"
    
    echo "For live market data, you need:"
    echo "1. Interactive Brokers account (paper or live)"
    echo "2. IB Gateway or TWS running"
    echo "3. API connections enabled"
    echo ""
    print_option "Do you have IB Gateway/TWS running? (y/n):"
    read -p "" IB_READY
    
    if [[ $IB_READY =~ ^[Yy]$ ]]; then
        print_status "Testing Interactive Brokers connection..."
        
        # Test IB connection
        python -c "
import sys
sys.path.append('.')
try:
    from scripts.test_connection import test_ib_connection
    if test_ib_connection():
        print('✅ Interactive Brokers connection successful')
        exit(0)
    else:
        print('⚠️  Interactive Brokers connection failed')
        exit(1)
except Exception as e:
    print(f'⚠️  IB connection test error: {e}')
    exit(1)
" && IB_CONNECTED=true || IB_CONNECTED=false

        if [ "$IB_CONNECTED" = "true" ]; then
            print_success "✓ Interactive Brokers connection verified"
            USE_LIVE_DATA=true
        else
            print_warning "IB connection failed. Will use enhanced mock data."
            USE_LIVE_DATA=false
            if [ "$TRADING_MODE" = "live" ]; then
                print_warning "Switching to hybrid mode due to connection issues"
                TRADING_MODE="hybrid"
            fi
        fi
    else
        print_warning "IB not ready. Will use enhanced mock data."
        USE_LIVE_DATA=false
        if [ "$TRADING_MODE" = "live" ]; then
            print_warning "Switching to demo mode. Set up IB and use live mode later."
            TRADING_MODE="demo"
        fi
    fi
fi

# Create configuration based on mode
print_status "Creating configuration for $TRADING_MODE mode..."

# Update config file based on trading mode
CONFIG_FILE="config/config.yaml"
if [ -f "$CONFIG_FILE" ]; then
    cp "$CONFIG_FILE" "$CONFIG_FILE.backup"
fi

cat > temp_config_update.py << 'EOF'
import yaml
import sys

mode = sys.argv[1]
use_live = sys.argv[2].lower() == 'true'

# Load existing config or create new
try:
    with open('config/config.yaml', 'r') as f:
        config = yaml.safe_load(f) or {}
except:
    config = {}

# Update based on mode
if mode == 'demo':
    config['data'] = {
        'use_mock': True,
        'enhanced_mock': True,
        'ib_connection': False
    }
elif mode == 'live':
    config['data'] = {
        'use_mock': not use_live,
        'enhanced_mock': not use_live,
        'ib_connection': use_live,
        'ib_host': '127.0.0.1',
        'ib_port': 7497,  # Paper trading port
        'ib_client_id': 1
    }
elif mode == 'hybrid':
    config['data'] = {
        'use_mock': not use_live,
        'enhanced_mock': True,
        'ib_connection': use_live,
        'fallback_to_mock': True,
        'ib_host': '127.0.0.1',
        'ib_port': 7497,
        'ib_client_id': 1
    }

# Enhanced strategy configuration
config['strategy'] = config.get('strategy', {})
config['strategy'].update({
    'strategy_loop_interval': 5.0,
    'use_heston_model': True,
    'auto_calibration': True
})

config['mispricing_detection'] = {
    'min_mispricing_pct': 5.0,
    'strong_mispricing_pct': 15.0,
    'very_strong_mispricing_pct': 25.0,
    'min_signal_confidence': 70.0,
    'min_volume': 10,
    'max_bid_ask_spread_pct': 10.0
}

config['trade_execution'] = {
    'max_position_size': 10,
    'base_position_size': 1,
    'max_daily_risk': 5000.0,
    'max_risk_per_trade': 1000.0,
    'min_signal_confidence': 70.0,
    'stop_loss_pct': 50.0,
    'take_profit_pct': 100.0
}

config['delta_hedging'] = {
    'target_delta': 0.0,
    'delta_band': 0.05,
    'account_equity': 1000000,
    'calibration_interval_minutes': 5
}

config['monitoring'] = {
    'dashboard_port': 8050,
    'prometheus_port': 9090
}

# Save updated config
with open('config/config.yaml', 'w') as f:
    yaml.dump(config, f, default_flow_style=False)

print(f"✓ Configuration updated for {mode} mode")
EOF

python temp_config_update.py "$TRADING_MODE" "${USE_LIVE_DATA:-false}"
rm temp_config_update.py

print_success "✓ Configuration created for $TRADING_MODE mode"

# Set up environment
print_status "Setting up environment..."
export PYTHONPATH=$(pwd):$PYTHONPATH

# Kill any existing processes
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
print_header "🚀 STARTING HESTON TRADING SYSTEM"

case $TRADING_MODE in
    "demo")
        print_status "Launching in Enhanced Demo Mode..."
        START_CMD="python scripts/start_system.py --env=development --mock"
        ;;
    "live")
        if [ "${USE_LIVE_DATA:-false}" = "true" ]; then
            print_status "Launching in Live Trading Mode with IB connection..."
            START_CMD="python scripts/start_system.py --env=paper --live"
        else
            print_status "Launching in Demo Mode (IB connection failed)..."
            START_CMD="python scripts/start_system.py --env=development --mock"
        fi
        ;;
    "hybrid")
        print_status "Launching in Hybrid Mode..."
        if [ "${USE_LIVE_DATA:-false}" = "true" ]; then
            START_CMD="python scripts/start_system.py --env=paper --hybrid"
        else
            START_CMD="python scripts/start_system.py --env=development --mock"
        fi
        ;;
esac

# Start the system in the background
$START_CMD &
SYSTEM_PID=$!

# Wait for startup
print_status "Waiting for system to initialize..."
sleep 8

# Check if system is running
if kill -0 $SYSTEM_PID 2>/dev/null; then
    print_success "✓ Trading system is running (PID: $SYSTEM_PID)"
else
    print_error "System failed to start properly"
    exit 1
fi

# Test dashboard accessibility
print_status "Testing dashboard accessibility..."
for i in {1..15}; do
    if curl -s http://localhost:8050 >/dev/null 2>&1; then
        print_success "✓ Dashboard is accessible"
        break
    else
        if [ $i -eq 15 ]; then
            print_error "Dashboard not accessible after 15 attempts"
            print_error "Please check the terminal output above for errors"
            exit 1
        fi
        print_status "Waiting for dashboard... (attempt $i/15)"
        sleep 2
    fi
done

# Success message
print_header "🎉 HESTON TRADING SYSTEM READY! 🎉"
echo ""
print_success "🌐 Trading Dashboard: http://localhost:8050"
print_success "📊 System Metrics:    http://localhost:9090/metrics"
echo ""

case $TRADING_MODE in
    "demo")
        echo -e "${GREEN}🎪 ENHANCED DEMO MODE ACTIVE${NC}"
        echo "Your system features:"
        echo "✅ 700+ simulated options with realistic pricing"
        echo "✅ Complete Heston stochastic volatility model"
        echo "✅ Live parameter calibration every 5 minutes"
        echo "✅ Quantitative mispricing detection (5-25% thresholds)"
        echo "✅ Automated trade execution with risk management"
        echo "✅ Dynamic delta hedging with SPY/ES"
        echo "✅ Real-time P&L and performance tracking"
        ;;
    "live")
        if [ "${USE_LIVE_DATA:-false}" = "true" ]; then
            echo -e "${GREEN}🚀 LIVE TRADING MODE ACTIVE${NC}"
            echo "Your system features:"
            echo "✅ Real Interactive Brokers market data"
            echo "✅ Live SPX options chains and pricing"
            echo "✅ Heston model calibration to real market"
            echo "✅ Real mispricing detection and trading"
            echo "✅ Paper trading environment (safe)"
            echo "✅ Professional risk management"
        else
            echo -e "${YELLOW}🎪 DEMO MODE (IB connection failed)${NC}"
            echo "System running with enhanced mock data"
        fi
        ;;
    "hybrid")
        if [ "${USE_LIVE_DATA:-false}" = "true" ]; then
            echo -e "${GREEN}🔧 HYBRID MODE ACTIVE${NC}"
            echo "Your system features:"
            echo "✅ Live IB data with mock data fallback"
            echo "✅ Real market data when available"
            echo "✅ Enhanced simulation when IB offline"
            echo "✅ Seamless switching between modes"
        else
            echo -e "${YELLOW}🔧 HYBRID MODE (Enhanced Mock)${NC}"
            echo "System using enhanced mock data with IB testing capability"
        fi
        ;;
esac

echo ""
echo -e "${CYAN}🎮 DEMO COMMANDS:${NC}"
echo "  python run_heston_demo.py      # Complete guided demo"
echo "  python dashboard_demo.py       # Strategy components demo"
echo "  python demo_data.py           # Basic data demonstration"
echo ""
echo -e "${CYAN}🔧 SYSTEM CONTROLS:${NC}"
echo "  View logs: tail -f logs/strategy.log"
echo "  Stop system: Press Ctrl+C in this terminal"
echo "  Restart: ./setup_and_run_v3.sh"
echo ""

# Try to open browser
if command -v open &> /dev/null; then
    print_status "Opening dashboard in your default browser..."
    open http://localhost:8050
elif command -v xdg-open &> /dev/null; then
    print_status "Opening dashboard in your default browser..."
    xdg-open http://localhost:8050
else
    print_warning "Could not auto-open browser. Please visit http://localhost:8050 manually"
fi

echo ""
print_status "System is running. Press Ctrl+C to stop..."

# Function to cleanup on exit
cleanup() {
    echo ""
    print_status "Shutting down trading system..."
    kill $SYSTEM_PID 2>/dev/null || true
    wait $SYSTEM_PID 2>/dev/null || true
    print_success "✓ System stopped cleanly"
    print_status "Thank you for using Heston Trading System v3!"
    
    echo ""
    echo "📝 To run again:"
    echo "  ./setup_and_run_v3.sh"
    echo ""
    echo "📚 Documentation:"
    echo "  • DEMO_INSTRUCTIONS.md - Complete demo guide"
    echo "  • README_SIMPLE.md - Detailed setup instructions"
    echo "  • QUICK_START.md - Fast setup guide"
    
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Wait for the system process and show periodic updates
update_count=0
while kill -0 $SYSTEM_PID 2>/dev/null; do
    sleep 30
    update_count=$((update_count + 1))
    
    echo ""
    echo -e "${BLUE}[UPDATE #$update_count]${NC} System running for $((update_count * 30)) seconds"
    case $TRADING_MODE in
        "demo")
            echo "🎪 Enhanced demo: Heston model actively trading with 700+ simulated options"
            ;;
        "live")
            if [ "${USE_LIVE_DATA:-false}" = "true" ]; then
                echo "🚀 Live trading: Real market data from Interactive Brokers"
            else
                echo "🎪 Demo mode: Enhanced mock data (IB connection unavailable)"
            fi
            ;;
        "hybrid")
            echo "🔧 Hybrid mode: Real IB data with intelligent mock fallback"
            ;;
    esac
    echo "   📊 Dashboard: http://localhost:8050"
    
    if [ $((update_count % 4)) -eq 0 ]; then
        echo ""
        echo "💡 TIP: Try running 'python run_heston_demo.py' in another terminal!"
    fi
done

# If we get here, the system stopped unexpectedly
print_warning "System process ended unexpectedly"
cleanup