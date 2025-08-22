#!/usr/bin/env python3
"""
Demo script to show enhanced mock data capabilities
"""
import sys
import os
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.data.enhanced_mock_generator import enhanced_mock

def print_separator(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)

def demo_underlying_data():
    """Demonstrate realistic underlying data"""
    print_separator("UNDERLYING MARKET DATA")
    
    for i in range(3):
        data = enhanced_mock.generate_underlying_snapshot()
        
        print(f"\nSnapshot #{i+1}:")
        for symbol, info in data.items():
            print(f"{symbol:>4}: ${info['last']:>8.2f} "
                  f"({info['change']:+6.2f}, {info['change_pct']:+5.1f}%) "
                  f"Vol: {info['volume']:,}")
        
        # Small delay to show price movement
        import time
        time.sleep(1)

def demo_options_data():
    """Demonstrate options chain data"""
    print_separator("OPTIONS CHAIN DATA")
    
    underlying = enhanced_mock.generate_underlying_snapshot()
    options = enhanced_mock.generate_options_snapshot(underlying)
    
    # Filter to show interesting options
    spx_options = [opt for opt in options if opt['symbol'] == 'SPX'][:10]
    
    print(f"\nSPX Options (showing {len(spx_options)} of {len(options)} total):")
    print(f"{'Strike':>6} {'Type':>4} {'Bid':>6} {'Ask':>6} {'IV':>6} {'Delta':>7} {'Volume':>8}")
    print("-" * 50)
    
    for opt in spx_options:
        print(f"{opt['strike']:>6.0f} {opt['type']:>4} "
              f"{opt['bid']:>6.2f} {opt['ask']:>6.2f} "
              f"{opt['implied_vol']:>6.3f} {opt['delta']:>7.3f} "
              f"{opt['volume']:>8,}")

def demo_trading_signals():
    """Demonstrate trading signals"""
    print_separator("TRADING SIGNALS")
    
    underlying = enhanced_mock.generate_underlying_snapshot()
    options = enhanced_mock.generate_options_snapshot(underlying)
    signals = enhanced_mock.generate_trading_signals(underlying, options)
    
    print(f"\nCurrent Market Conditions:")
    print(f"Market Sentiment: {enhanced_mock.market_sentiment:+.3f}")
    print(f"Volatility Regime: {enhanced_mock.volatility_regime}")
    
    if signals:
        print(f"\nActive Signals ({len(signals)}):")
        for signal in signals:
            print(f"• {signal['type'].upper()} - {signal['description']} "
                  f"[{signal['strength']}]")
    else:
        print("\nNo active signals")

def demo_positions():
    """Demonstrate position tracking"""
    print_separator("CURRENT POSITIONS")
    
    positions = enhanced_mock.generate_positions()
    
    print(f"{'Symbol':>6} {'Strike':>6} {'Type':>4} {'Qty':>5} "
          f"{'Entry':>8} {'Current':>8} {'P&L':>10} {'P&L%':>6}")
    print("-" * 65)
    
    total_pnl = 0
    for pos in positions:
        total_pnl += pos['pnl']
        print(f"{pos['symbol']:>6} {pos['strike']:>6.0f} {pos['type']:>4} "
              f"{pos['quantity']:>5} {pos['entry_price']:>8.2f} "
              f"{pos['current_price']:>8.2f} {pos['pnl']:>10.2f} "
              f"{pos['pnl_pct']:>5.1f}%")
    
    print("-" * 65)
    print(f"{'TOTAL P&L:':>55} {total_pnl:>10.2f}")

def demo_live_updates():
    """Demonstrate live data updates"""
    print_separator("LIVE DATA SIMULATION")
    print("Simulating 10 seconds of live market data...")
    print("Press Ctrl+C to stop early\n")
    
    try:
        for i in range(10):
            data = enhanced_mock.generate_underlying_snapshot()
            spx = data['SPX']
            vix = data['VIX']
            
            print(f"Update {i+1:2}/10: SPX ${spx['last']:7.2f} "
                  f"({spx['change_pct']:+5.1f}%) | "
                  f"VIX {vix['last']:5.1f} "
                  f"({vix['change_pct']:+5.1f}%) | "
                  f"Sentiment: {enhanced_mock.market_sentiment:+.2f}")
            
            import time
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nStopped by user")

def main():
    """Run all demonstrations"""
    print("🎯 HESTON TRADING SYSTEM - ENHANCED MOCK DATA DEMO")
    print("This demonstrates the realistic market data simulation")
    
    try:
        demo_underlying_data()
        demo_options_data()
        demo_trading_signals()
        demo_positions()
        demo_live_updates()
        
        print_separator("DEMO COMPLETE")
        print("✅ Enhanced mock data is generating realistic trading scenarios!")
        print("🌐 Visit http://localhost:8050 to see this data in the dashboard")
        print("📊 Visit http://localhost:9090/metrics for system metrics")
        
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user")
    except Exception as e:
        print(f"\n❌ Error during demo: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()