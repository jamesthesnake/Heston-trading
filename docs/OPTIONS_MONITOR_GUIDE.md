# SPX/XSP Options Real-Time Monitor Guide

## Overview

The SPX/XSP Options Real-Time Monitor provides comprehensive real-time options data with 5-second snapshots, including:

- **NBBO bid/ask and sizes**
- **Midpoint calculations**
- **Implied volatility and Greeks** (Delta, Gamma, Theta, Vega)
- **Last trade and size**
- **Today's volume and open interest**
- **NBBO timestamps**
- **Underlying data**: SPX index, SPY, ES futures, VIX levels

## Filtering Criteria

The system automatically filters options based on your specifications:

- **DTE**: 10-50 days to expiration
- **Strike Range**: ±9% around ATM
- **Spread Width**: ≤10% of midpoint
- **Minimum Mid Price**: ≥$0.20
- **Volume**: ≥1,000 contracts
- **Open Interest**: ≥500 contracts

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Setup Interactive Brokers
- Install IB Gateway or TWS
- Configure for paper trading (port 7497) or live trading (port 7496)
- Enable API connections in IB settings

### 3. Run the Monitor

**Development Mode (Mock Data):**
```bash
python scripts/start_options_monitor.py --config config/config.dev.yaml
```

**Paper Trading Mode (Real Data):**
```bash
python scripts/start_options_monitor.py --config config/config.paper.yaml
```

**Custom Configuration:**
```bash
python scripts/start_options_monitor.py --config config/config.paper.yaml --host 0.0.0.0 --port 8080
```

### 4. Access Dashboard
Open your browser to: http://localhost:8050

## Dashboard Features

### Market Overview
- Total screened options count
- Average implied volatility
- Real-time underlying prices (SPX, SPY, VIX, ES)

### Options Table
- Sortable and filterable table with all option data
- Color-coded calls (green) and puts (red)
- Real-time updates every 5 seconds

### Analytics Charts
- **IV Surface**: 3D implied volatility surface
- **Volume Chart**: Top 20 options by volume
- **Greeks Distribution**: Delta histogram
- **Moneyness vs IV**: Scatter plot analysis

## Configuration

### Screening Criteria
Edit `config/config.paper.yaml` to adjust filtering:

```yaml
options:
  screening:
    min_dte: 10
    max_dte: 50
    strike_range_pct: 0.09  # ±9%
    max_spread_width_pct: 0.10  # ≤10%
    min_mid_price: 0.20  # ≥$0.20
    min_volume: 1000  # ≥1,000
    min_open_interest: 500  # ≥500
    symbols: ["SPX", "XSP"]
```

### IB Connection
```yaml
ib:
  host: "127.0.0.1"
  port: 7497  # Paper trading
  client_id: 1
```

## Data Export

The system can export snapshots to JSON:
```python
# Programmatically export current snapshot
monitor.export_snapshot_to_json("my_snapshot.json")
```

## Architecture

### Components
1. **IBProvider**: Interactive Brokers data connection
2. **OptionsScreener**: Filtering and screening engine
3. **BlackScholesCalculator**: IV and Greeks calculation
4. **RealTimeMonitor**: Coordination and 5-second snapshots
5. **OptionsDashboard**: Web-based visualization

### Data Flow
```
IB API → IBProvider → OptionsScreener → RealTimeMonitor → Dashboard
                  ↓
            BlackScholes Calculator
```

## Troubleshooting

### Common Issues

**Connection Failed**
- Ensure IB Gateway/TWS is running
- Check port configuration (7497 for paper, 7496 for live)
- Verify API is enabled in IB settings

**No Options Data**
- Check market hours (options trade 9:30 AM - 4:00 PM ET)
- Verify screening criteria aren't too restrictive
- Ensure sufficient market data subscriptions

**Performance Issues**
- Reduce `max_contracts` in configuration
- Increase `update_interval` for slower updates
- Use development mode with mock data for testing

### Logs
Check logs in `logs/options_monitor.log` for detailed debugging information.

## Advanced Usage

### Custom Screening
```python
from src.data.options_screener import ScreeningCriteria

# Create custom criteria
criteria = ScreeningCriteria(
    min_dte=15,
    max_dte=45,
    min_volume=2000
)

monitor.update_screening_criteria(**criteria.__dict__)
```

### Real-time Alerts
Implement custom callbacks for real-time alerts:
```python
def alert_callback(snapshot):
    high_volume_options = [
        opt for opt in snapshot['screened_options'] 
        if opt['volume'] > 5000
    ]
    if high_volume_options:
        print(f"High volume alert: {len(high_volume_options)} options")

monitor = RealTimeOptionsMonitor(config, callback=alert_callback)
```

## Support

For issues or questions:
1. Check the logs first
2. Verify IB connection and permissions
3. Review configuration settings
4. Test with mock data in development mode
