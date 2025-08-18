# Heston Trading System

A production-ready options trading system implementing the Heston stochastic volatility model for SPX/XSP options.

## Features

- **Heston Model Calibration**: Real-time calibration to market implied volatility surface
- **Signal Generation**: Statistical arbitrage signals based on mispricing detection
- **Real-time Data Feed**: 5-second snapshots from Interactive Brokers
- **Risk Management**: Position limits, stop-losses, and Greek exposure monitoring
- **Automated Execution**: Smart order routing with slippage control
- **Live Dashboard**: Real-time monitoring and visualization
- **Backtesting**: Comprehensive historical analysis framework

## Quick Start

### Prerequisites

- Python 3.8+
- Interactive Brokers Gateway or TWS
- Redis (optional, for caching)

### Installation

1. Install dependencies:
```bash
make install
```

2. Configure environment:
```bash
cp .env.example .env
# Edit .env with your settings
```

3. Test IB connection:
```bash
make test-ib
```

4. Run system:
```bash
make run
```

## Project Structure

```
heston-trading-system/
├── config/           # Configuration files
├── src/             # Source code
│   ├── strategy/    # Core Heston strategy
│   ├── data/        # Data feed management
│   ├── execution/   # Order execution
│   ├── risk/        # Risk management
│   └── monitoring/  # Dashboard and metrics
├── tests/           # Test suite
├── scripts/         # Utility scripts
├── notebooks/       # Analysis notebooks
├── data/            # Data storage
├── logs/            # Log files
└── docs/            # Documentation
```

## Configuration

The system uses YAML configuration files in the `config/` directory:

- `config.yaml`: Main configuration
- `config.dev.yaml`: Development settings
- `config.paper.yaml`: Paper trading settings
- `config.live.yaml`: Live trading settings

## Usage

### Development Mode
```bash
make run-dev
```

### Paper Trading
```bash
make run
```

### Live Trading
```bash
python scripts/start_system.py --env=live
```

### Dashboard

Access the dashboard at: http://localhost:8050

### Monitoring

Prometheus metrics available at: http://localhost:9090/metrics

## Testing

Run all tests:
```bash
make test
```

Test IB connection:
```bash
make test-ib
```

## Docker Deployment

Build and run with Docker:
```bash
make docker
make docker-up
```

## Documentation

See the `docs/` directory for detailed documentation:

- [Setup Guide](docs/setup.md)
- [Strategy Details](docs/strategy.md)
- [API Documentation](docs/api.md)
- [Troubleshooting](docs/troubleshooting.md)

## License

Proprietary - All rights reserved

## Support

For issues or questions, please contact the development team.
