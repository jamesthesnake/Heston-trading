#!/usr/bin/env python3
"""
SPX/XSP Options Mispricing Strategy - Main Execution Script
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

import asyncio
import logging
import yaml
from datetime import datetime, timedelta
from typing import Dict, Any

# Import strategy components
from data.mock_data_generator import MockDataGenerator
from data.options_screener import OptionsScreener
from strategy.mispricing_strategy import MispricingStrategy
from monitoring.dashboard import Dashboard
from monitoring.metrics import MetricsServer
from strategy.monitoring_system import MonitoringSystem, email_alert_handler, slack_alert_handler

def setup_logging():
    """Setup basic logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('logs/strategy.log')
        ]
    )
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)

async def mock_market_data_feed(mock_gen):
    """Generate mock market data feed for testing"""
    
    while True:
        # Generate underlying data
        underlying_data = mock_gen.generate_underlying_data()
        underlying_prices = {symbol: data.last for symbol, data in underlying_data.items()}
        
        # Generate options data
        options_data = mock_gen.generate_options_data(underlying_prices)
        
        # Create market snapshot
        snapshot = {
            'timestamp': underlying_data['SPX'].timestamp,
            'underlying': {
                symbol: {
                    'bid': data.bid,
                    'ask': data.ask,
                    'last': data.last
                }
                for symbol, data in underlying_data.items()
            },
            'options': options_data,
            'rates': {0.05: 0.05},  # 5% flat rate curve
            'futures': {
                'ES': {
                    'bid': underlying_prices['ES'] - 0.25,
                    'ask': underlying_prices['ES'] + 0.25,
                    'last': underlying_prices['ES']
                }
            }
        }
        
        yield snapshot
        await asyncio.sleep(5)  # 5-second intervals

async def main():
    """Main execution function"""
    
    # Get project root
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(project_root)
    
    # Setup logging
    setup_logging()
    
    # Load configuration
    config_path = os.path.join(project_root, "config", "mispricing_strategy.yaml")
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    print("🚀 SPX/XSP Options Mispricing Strategy")
    print("=" * 50)
    print(f"Configuration loaded from: {config_path}")
    print(f"Strategy: {config['strategy']['name']} v{config['strategy']['version']}")
    print()
    
    # Initialize strategy
    strategy = MispricingStrategy(config)
    
    # Initialize monitoring
    monitoring = MonitoringSystem(config)
    monitoring.add_alert_handler(email_alert_handler)
    monitoring.add_alert_handler(slack_alert_handler)
    
    # Initialize mock data generator
    mock_gen = MockDataGenerator()
    
    print("📊 System Components Initialized:")
    print("   ✅ Heston Model Calibration")
    print("   ✅ Signal Generation Engine")
    print("   ✅ Dividend Yield Extraction")
    print("   ✅ Position Sizing with VIX Scaling")
    print("   ✅ Delta Hedging (ES/SPY Selection)")
    print("   ✅ Risk Management (Stop Losses)")
    print("   ✅ Macro Event Handling")
    print("   ✅ Monitoring & Alerting")
    print()
    
    print("🎯 Strategy Parameters:")
    print(f"   • DTE Range: {config['screening']['min_dte']}-{config['screening']['max_dte']} days")
    print(f"   • Strike Range: ±{config['screening']['strike_range_pct']:.0%} around ATM")
    print(f"   • Min Volume: {config['screening']['min_volume']:,} contracts")
    print(f"   • Min OI: {config['screening']['min_open_interest']:,} contracts")
    print(f"   • Calibration: Every {config['strategy']['calibration_interval_min']} minutes")
    print(f"   • Signals: Every {config['strategy']['signal_interval_sec']} seconds")
    print(f"   • Risk Limits: {config['risk_management']['soft_stop_pct']:.1%} soft / {config['risk_management']['hard_stop_pct']:.1%} hard stop")
    print()
    
    try:
        print("🔄 Starting strategy execution...")
        print("   Press Ctrl+C to stop")
        print()
        
        # Create market data feed
        market_feed = mock_market_data_feed(mock_gen)
        
        # Run strategy
        await strategy.run_strategy_loop(market_feed)
        
    except KeyboardInterrupt:
        print("\n🛑 Strategy stopped by user")
    except Exception as e:
        print(f"\n❌ Strategy error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Print final status
        status = strategy.get_strategy_status()
        print(f"\n📈 Final Status:")
        print(f"   • Positions: {status['position_count']}")
        print(f"   • Daily P&L: ${status['daily_pnl']:,.2f}")
        print(f"   • Risk Level: {status['risk_level']}")
        print(f"   • Model Available: {status['model_available']}")
        
        # Export monitoring data
        dashboard_data = monitoring.get_dashboard_data()
        print(f"\n📊 Performance Summary:")
        print(f"   • Sharpe Ratio: {dashboard_data['performance']['sharpe_ratio']:.2f}")
        print(f"   • Max Drawdown: {dashboard_data['performance']['max_drawdown']:.2%}")
        print(f"   • Hit Rate: {dashboard_data['performance']['hit_rate']:.1%}")
        print(f"   • Total Trades: {dashboard_data['performance']['total_trades']}")
        
        alert_summary = monitoring.get_alert_summary()
        print(f"\n🚨 Alerts: {alert_summary['unacknowledged']} unacknowledged")
        print(f"   • Critical: {alert_summary['critical']}")
        print(f"   • High: {alert_summary['high']}")
        print(f"   • Medium: {alert_summary['medium']}")

if __name__ == "__main__":
    asyncio.run(main())
