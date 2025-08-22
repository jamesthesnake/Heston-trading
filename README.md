# Heston Trading System

A professional-grade options trading system implementing the Heston stochastic volatility model with advanced risk management, service-oriented architecture, and comprehensive monitoring capabilities.

## 🚀 Features

### Core Trading
- **Heston Stochastic Volatility Model**: Advanced options pricing with calibration to market data
- **Multi-Model Pricing**: Heston, Black-Scholes, and custom pricing models
- **Signal Generation**: Statistical arbitrage based on mispricing detection
- **Smart Execution**: Order routing with risk controls and slippage management
- **Delta Hedging**: Automated portfolio delta neutrality maintenance

### Architecture
- **Service-Oriented Design**: Microservices architecture with unified interface
- **Enhanced Risk Management**: 4-tier risk system (position, portfolio, compliance, engine)
- **Modular Strategy Components**: Orchestrator, engine, portfolio manager, lifecycle manager
- **Data Provider Abstraction**: Multiple data sources with failover capability
- **Configuration Management**: Centralized YAML-based configuration system

### Monitoring & Operations
- **Real-Time Dashboard**: Live monitoring with Plotly Dash interface
- **Multi-Channel Notifications**: Email, Slack, console, and file notifications
- **Health Monitoring**: Service health checks and performance metrics
- **Comprehensive Logging**: Structured logging with configurable levels
- **Risk Alerts**: Real-time risk monitoring with automated alerts

## 📋 Prerequisites

### System Requirements
- **Python**: 3.8 or higher
- **Operating System**: Windows, macOS, or Linux
- **Memory**: Minimum 4GB RAM (8GB recommended)
- **Disk Space**: 1GB free space

### Optional Dependencies
- **Interactive Brokers Gateway/TWS**: For live market data and execution
- **Redis**: For advanced caching (not required for basic operation)

## 🛠️ Installation

### 1. Clone the Repository
```bash
git clone <repository-url>
cd Heston-trading
```

### 2. Set Up Python Environment
Using conda (recommended):
```bash
conda create -n heston-trading python=3.9
conda activate heston-trading
```

Using venv:
```bash
python -m venv heston-trading-env
source heston-trading-env/bin/activate  # On Windows: heston-trading-env\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

**Note**: If you don't have a `requirements.txt` file, install the core dependencies:
```bash
pip install numpy pandas scipy matplotlib plotly dash asyncio pyyaml dataclasses-json
```

### 4. Verify Installation

**Option A: Quick Setup Script (Recommended)**
```bash
python setup.py
```
This script will:
- Check Python version compatibility
- Verify all dependencies are installed  
- Test configuration files
- Run basic system tests

**Option B: Manual Verification**
```bash
python test_enhanced_risk.py
```

**Option C: Quick Start Demo**
```bash
python quick_start.py
```
This runs an interactive demo of all major system components.

## ⚙️ Configuration

### Default Configuration Files
The system includes several pre-configured files in the `config/` directory:

- `demo_config.yaml`: Demo/development configuration with mock data
- `live_config.yaml`: Live trading configuration template

### Environment Setup
1. **Demo Mode** (no external connections required):
   ```bash
   # Uses mock data - perfect for testing and development
   # No additional setup needed
   ```

2. **Live Trading Mode**:
   ```bash
   # Copy and customize the live configuration
   cp config/live_config.yaml config/my_config.yaml
   # Edit my_config.yaml with your specific settings
   ```

### Key Configuration Sections

#### Market Data
```yaml
market_data:
  primary_provider:
    type: "mock"  # or "interactive_brokers" for live data
    update_interval: 1.0
    volatility_factor: 1.5
  
  enable_cache: true
  cache_duration: 30
```

#### Risk Management
```yaml
risk_management:
  max_position_size: 100
  max_daily_loss: 5000
  var_confidence_level: 0.95
  enable_alerts: true
```

#### Execution
```yaml
execution:
  enable_risk_checks: true
  max_order_value: 10000
  commission_rate: 0.001
```

## 🏃‍♂️ Quick Start

### 🚀 For New Users (Start Here!)
1. **Interactive Demo** (5 minutes):
   ```bash
   python quick_start.py
   ```
   This shows all major features working together.

2. **Setup Verification**:
   ```bash
   python setup.py
   ```
   Automatically checks and installs everything you need.

### 🧪 For Developers
1. **Complete System Test**:
   ```bash
   python test_service_layer.py
   ```
   Tests all services: Market Data, Options Pricing, Execution, Notification

2. **Risk Management Test**:
   ```bash
   python test_enhanced_risk.py
   ```
   Comprehensive risk system validation

### 🛠️ For Advanced Users
For development, you can start individual components:

**Market Data Service**:
```python
from src.services import MarketDataService, ServiceConfig
from src.config.config_manager import get_config_manager

# Load configuration
config_manager = get_config_manager()
config_manager.load_config("config/demo_config.yaml")
strategy_config = config_manager.get_strategy_config()

# Create and start service
service_config = ServiceConfig(name="market_data", enabled=True)
market_service = MarketDataService(service_config, strategy_config)

# Start service
import asyncio
asyncio.run(market_service.start())
```

## 🏗️ Project Structure

```
Heston-trading/
├── config/                    # Configuration files
│   ├── demo_config.yaml      # Demo/development config
│   └── live_config.yaml      # Live trading config template
├── src/                      # Source code
│   ├── services/             # Service layer architecture
│   │   ├── base_service.py   # Base service interface
│   │   ├── market_data_service.py
│   │   ├── options_pricing_service.py
│   │   ├── execution_service.py
│   │   └── notification_service.py
│   ├── risk/                 # Enhanced risk management
│   │   ├── risk_types.py     # Common risk types
│   │   ├── risk_engine.py    # Risk coordinator
│   │   ├── position_risk.py  # Position-level analysis
│   │   ├── portfolio_risk.py # Portfolio-level analysis
│   │   └── compliance.py     # Compliance monitoring
│   ├── strategy/             # Modular strategy components
│   │   ├── orchestrator.py   # Main coordinator
│   │   ├── strategy_engine.py # Trading logic
│   │   ├── portfolio_manager.py
│   │   └── lifecycle_manager.py
│   ├── data/                 # Data providers and utilities
│   │   ├── providers/        # Data provider abstraction
│   │   └── black_scholes.py  # Pricing models
│   ├── config/               # Configuration management
│   │   └── config_manager.py
│   └── monitoring/           # Dashboard and metrics
├── test_enhanced_risk.py     # Risk management tests
├── test_service_layer.py     # Service layer tests
├── setup.py                  # Automated setup script
├── quick_start.py            # Interactive demo script
├── requirements.txt          # Python dependencies
└── README.md                 # This file
```

## 🧪 Testing

### Comprehensive Test Suite
```bash
# Test risk management system
python test_enhanced_risk.py

# Test service layer architecture
python test_service_layer.py
```

### Expected Test Output
Both tests should show:
- ✅ All components initializing successfully
- ✅ Services starting and health checks passing
- ✅ Mock data processing and calculations working
- ✅ Risk assessments and alerts generating correctly

### Troubleshooting Tests
If tests fail:

1. **Import Errors**: Ensure all dependencies are installed
   ```bash
   pip install numpy pandas scipy matplotlib plotly dash pyyaml
   ```

2. **Configuration Issues**: Verify config files exist
   ```bash
   ls config/  # Should show demo_config.yaml and live_config.yaml
   ```

3. **Python Path Issues**: Run from the project root directory

## 📊 Usage Examples

### Basic Market Data Access
```python
import asyncio
from src.services import MarketDataService, ServiceConfig
from src.services.market_data_service import MarketDataRequest

# Setup
service_config = ServiceConfig(name="market_data")
market_service = MarketDataService(service_config, strategy_config)

async def get_market_data():
    await market_service.start()
    
    # Request market data
    request = MarketDataRequest(
        symbols=['SPY', 'QQQ'],
        data_types=['quotes', 'greeks'],
        use_cache=True
    )
    
    response = await market_service.get_market_data(request)
    print(f"Retrieved data for {len(response.symbols)} symbols")
    print(f"Latency: {response.latency_ms:.1f}ms")
    
    await market_service.stop()

asyncio.run(get_market_data())
```

### Options Pricing
```python
from src.services import OptionsPricingService
from src.services.options_pricing_service import OptionContract, PricingRequest
from datetime import datetime

# Create option contract
contract = OptionContract(
    symbol='SPY240315C00500000',
    underlying='SPY',
    option_type='C',
    strike=500.0,
    expiry_date=datetime(2024, 3, 15)
)

# Create pricing request
market_data = {
    'SPY': {'last': 505.0, 'implied_volatility': 0.18}
}

request = PricingRequest(
    contracts=[contract],
    market_data=market_data,
    include_greeks=True
)

# Price the option
async def price_option():
    pricing_service = OptionsPricingService(service_config, strategy_config)
    await pricing_service.start()
    
    response = await pricing_service.price_options(request)
    
    if response.results:
        result = response.results[0]
        print(f"Theoretical Price: ${result.theoretical_price:.2f}")
        print(f"Delta: {result.delta:.3f}")
        print(f"Gamma: {result.gamma:.3f}")
    
    await pricing_service.stop()

asyncio.run(price_option())
```

### Risk Assessment
```python
from src.risk.risk_engine import RiskEngine

# Sample positions
positions = [{
    'symbol': 'SPY',
    'quantity': 100,
    'market_value': 50000,
    'delta': 0.6,
    'gamma': 0.02
}]

market_data = {
    'SPY': {'last': 500, 'volume': 1000000},
    'VIX': {'last': 18.5}
}

portfolio_metrics = {
    'total_value': 100000,
    'daily_pnl': 1500
}

async def assess_risk():
    risk_engine = RiskEngine(strategy_config)
    
    assessment = await risk_engine.assess_risk(
        positions, market_data, portfolio_metrics
    )
    
    print(f"Risk Level: {assessment.overall_level.value}")
    print(f"Recommended Action: {assessment.recommended_action.value}")
    print(f"Alerts: {len(assessment.alerts)}")
    print(f"Confidence: {assessment.confidence_score:.2f}")

asyncio.run(assess_risk())
```

## 🔧 Advanced Configuration

### Interactive Brokers Setup
To use live data from Interactive Brokers:

1. **Install IB Gateway or TWS**
2. **Configure connection in your config file**:
   ```yaml
   market_data:
     primary_provider:
       type: "interactive_brokers"
       host: "127.0.0.1"
       port: 7497  # Paper trading port (7496 for live)
       client_id: 1
   ```

3. **Test connection**:
   ```python
   from src.data.providers.enhanced_ib_provider import IBDataProvider
   
   config = {'host': '127.0.0.1', 'port': 7497, 'client_id': 1}
   provider = IBDataProvider(config)
   # Connection test code here
   ```

### Custom Notifications
Configure notification channels:

```yaml
notifications:
  channels:
    email:
      enabled: true
      smtp_server: "smtp.gmail.com"
      smtp_port: 587
      username: "your-email@gmail.com"
      password: "your-password"
    
    slack:
      enabled: true
      webhook_url: "your-slack-webhook-url"
  
  templates:
    risk_alert:
      subject: "Risk Alert: {level}"
      body: "Alert: {message}\nAction: {action}"
      channels: ["email", "slack"]
```

### Performance Tuning
For high-frequency trading:

```yaml
market_data:
  update_interval: 0.1  # 100ms updates
  max_concurrent_requests: 50
  enable_cache: true
  cache_duration: 5     # 5 seconds

execution:
  max_order_value: 1000000
  enable_risk_checks: true
  risk_check_timeout: 0.05  # 50ms
```

## 🐛 Troubleshooting

### Common Issues

1. **"Module not found" errors**:
   ```bash
   # Ensure you're in the project root directory
   export PYTHONPATH="${PYTHONPATH}:$(pwd)"
   ```

2. **Configuration file not found**:
   ```bash
   # Check if config files exist
   ls config/
   # If missing, create from templates provided in the codebase
   ```

3. **Service startup failures**:
   ```bash
   # Check logs for specific error messages
   # Ensure all dependencies are installed
   pip install -r requirements.txt
   ```

4. **Interactive Brokers connection issues**:
   - Verify IB Gateway/TWS is running
   - Check port numbers (7497 for paper, 7496 for live)
   - Ensure client ID is unique
   - Check firewall settings

### Getting Help

For issues or questions:
1. Check the test output for specific error messages
2. Review configuration files for correct syntax
3. Ensure all dependencies are properly installed
4. Check that you're running from the correct directory

## 📈 Performance

### System Capabilities
- **Latency**: Sub-100ms risk assessments
- **Throughput**: 1000+ pricing calculations per second
- **Scalability**: Multi-service architecture supports horizontal scaling
- **Reliability**: Automatic failover and error recovery

### Monitoring
The system includes comprehensive monitoring:
- Service health checks every 30 seconds
- Performance metrics collection
- Real-time risk level monitoring
- Automated alert generation

## 🔒 Security

### Best Practices
- Configuration files contain no hardcoded credentials
- All external connections use secure protocols
- Risk limits prevent excessive exposure
- Comprehensive logging for audit trails

### Risk Controls
- Position size limits
- Daily loss limits
- Volatility-based scaling
- Real-time compliance monitoring

## 🚀 Deployment

### Development
```bash
# Run in demo mode with mock data
python test_service_layer.py
```

### Paper Trading
1. Configure IB connection for paper trading
2. Update config to use IB provider
3. Start services with paper trading config

### Production
1. Implement additional monitoring
2. Set up log rotation and backup procedures
3. Configure production risk limits
4. Establish operational procedures

## 📜 License

All rights reserved. This is proprietary software.

## 🤝 Contributing

This is a private repository. For internal development questions, please contact the development team.

---

## 🎯 Get Started in 60 Seconds!

**New to the system?** Run this single command:
```bash
python quick_start.py
```

This will demonstrate all major features and confirm everything is working correctly.

**Need help?** The setup script will check and fix common issues:
```bash
python setup.py
```

**Ready to trade?** Follow the Interactive Demo output for next steps!

---

*Built with ❤️ using advanced options trading techniques and professional software engineering practices.*