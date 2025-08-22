# Heston Trading System - Setup Guide

## Quick Start (Recommended)

### Prerequisites
- **Python 3.11** (required)
- macOS, Linux, or Windows with WSL

### One-Command Setup
```bash
./setup_and_run.sh
```

This script will:
1. ✅ Check Python 3.11 installation
2. ✅ Create a clean virtual environment
3. ✅ Install all dependencies
4. ✅ Start the system in development mode

## Manual Setup

### 1. Install Python 3.11
```bash
# macOS
brew install python@3.11

# Ubuntu/Debian
sudo apt install python3.11 python3.11-venv

# Verify installation
python3.11 --version
```

### 2. Create Virtual Environment
```bash
python3.11 -m venv heston_venv
source heston_venv/bin/activate  # On Windows: heston_venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements-working.txt
```

### 4. Run the System
```bash
# Development mode (mock data)
make run-dev

# Or directly:
python scripts/start_system.py --env=development --mock
```

## Access Points

Once running, access:
- **Dashboard**: http://localhost:8050
- **Metrics**: http://localhost:9090/metrics

## File Structure

```
├── setup_and_run.sh           # One-command setup script
├── requirements-working.txt    # Tested dependencies
├── requirements.txt           # Original requirements
├── SETUP_GUIDE.md            # This file
├── scripts/start_system.py   # Main entry point
├── src/                      # Source code
└── config/                   # Configuration files
```

## Troubleshooting

### Python Version Issues
```bash
# Check available Python versions
ls /usr/bin/python* 

# Use specific Python version
python3.11 -m venv heston_venv
```

### Import Errors
```bash
# Ensure you're in the project directory
cd /path/to/Heston-trading

# Set Python path
export PYTHONPATH=$(pwd):$PYTHONPATH
```

### Port Conflicts
Edit `config/config.yaml` to change ports:
```yaml
monitoring:
  dashboard_port: 8051  # Change from 8050
  prometheus_port: 9091  # Change from 9090
```

## Development

### Running Tests
```bash
source heston_venv/bin/activate
python src/tests/test_basic.py
```

### Code Formatting
```bash
make format  # Requires black and isort
```

### Linting
```bash
make lint    # Requires pylint and mypy
```

## Production Deployment

For live trading, see:
- `deployment/` directory for Docker/Kubernetes configs
- `config/config.live.yaml` for production settings
- Interactive Brokers Gateway setup requirements

## Support

For issues or questions:
1. Check the logs in `logs/` directory
2. Verify all dependencies are installed
3. Ensure Python 3.11 is being used
4. Review configuration files in `config/`