#!/bin/bash
# Heston Trading System - Clean Setup and Run Script
# Requires Python 3.11

set -e  # Exit on any error

echo "============================================================"
echo "       HESTON TRADING SYSTEM - SETUP SCRIPT"
echo "============================================================"

# Check Python version
python_version=$(python3.11 --version 2>/dev/null | grep -o '3\.11' || echo "")
if [ -z "$python_version" ]; then
    echo "❌ Error: Python 3.11 is required but not found"
    echo "Please install Python 3.11:"
    echo "  macOS: brew install python@3.11"
    echo "  Ubuntu: sudo apt install python3.11 python3.11-venv"
    exit 1
fi

echo "✓ Python 3.11 found"

# Create virtual environment
echo "Creating virtual environment..."
if [ -d "heston_venv" ]; then
    echo "Removing existing virtual environment..."
    rm -rf heston_venv
fi

python3.11 -m venv heston_venv
echo "✓ Virtual environment created"

# Activate virtual environment
echo "Activating virtual environment..."
source heston_venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install core dependencies first
echo "Installing core dependencies..."
pip install numpy scipy pandas pyyaml click dash plotly flask

# Install remaining requirements
echo "Installing remaining requirements..."
if [ -f "requirements-working.txt" ]; then
    pip install -r requirements-working.txt
    echo "✓ All dependencies installed from requirements-working.txt"
else
    echo "⚠️  requirements-working.txt not found, using fallback requirements"
    pip install \
        ibapi \
        prometheus-client \
        psutil \
        requests \
        websocket-client \
        python-dotenv \
        colorama \
        tabulate
fi

echo "============================================================"
echo "✓ Setup complete!"
echo "============================================================"

# Run the system
echo "Starting Heston Trading System..."
echo "Dashboard will be available at: http://localhost:8050"
echo "Metrics will be available at: http://localhost:9090/metrics"
echo ""
echo "Press Ctrl+C to stop the system"
echo "============================================================"

# Set Python path and run
export PYTHONPATH=$(pwd):$PYTHONPATH
python scripts/start_system.py --env=development --mock

echo ""
echo "============================================================"
echo "System stopped. To restart:"
echo "  source heston_venv/bin/activate"
echo "  make run-dev"
echo "============================================================"