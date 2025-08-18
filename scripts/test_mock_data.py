#!/usr/bin/env python3
"""
Test script to run the options monitor with pure mock data
"""
import sys
import os
import time
import threading
from pathlib import Path

# Add src to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from data.mock_data_generator import MockDataGenerator
from data.options_screener import OptionsScreener, ScreeningCriteria
from data.black_scholes import BlackScholesCalculator
import json
from datetime import datetime

def test_mock_data_generation():
    """Test mock data generation and screening"""
    print("🚀 Testing SPX/XSP Options Mock Data Generation")
    print("=" * 50)
    
    # Initialize components with relaxed criteria for testing
    mock_gen = MockDataGenerator()
    criteria = ScreeningCriteria(
        min_volume=100,  # Reduced from 1000
        min_open_interest=50,  # Reduced from 500
        min_mid_price=0.10  # Reduced from 0.20
    )
    screener = OptionsScreener(criteria)
    
    # Generate mock data
    print("📊 Generating mock underlying data...")
    underlying_data = mock_gen.generate_underlying_data()
    
    # Extract prices
    underlying_prices = {}
    for symbol, data in underlying_data.items():
        underlying_prices[symbol] = data.last
        print(f"   {symbol}: ${data.last:.2f} (bid: ${data.bid:.2f}, ask: ${data.ask:.2f})")
    
    print("\n📈 Generating mock options data...")
    options_data = mock_gen.generate_options_data(underlying_prices)
    print(f"   Generated {len(options_data)} options contracts")
    
    print("\n🔍 Screening options with criteria:")
    print(f"   - DTE: 10-50 days")
    print(f"   - Strike range: ±9% around ATM")
    print(f"   - Spread width: ≤10% of mid")
    print(f"   - Min mid price: ≥$0.20")
    print(f"   - Min volume: ≥1,000")
    print(f"   - Min OI: ≥500")
    
    # Screen options
    screened_options = screener.screen_options(options_data, underlying_prices)
    print(f"   ✅ {len(screened_options)} options passed screening")
    
    if screened_options:
        print("\n📋 Sample screened options:")
        print("Symbol | Strike | Type | DTE | Mid    | Volume | OI    | IV    | Delta")
        print("-" * 75)
        
        # Show top 10 by volume
        top_options = sorted(screened_options, key=lambda x: x.option_data.volume, reverse=True)[:10]
        
        for opt in top_options:
            data = opt.option_data
            print(f"{data.symbol:6} | {data.strike:6.0f} | {data.option_type:4} | {opt.dte:3d} | "
                  f"${data.midpoint:5.2f} | {data.volume:6d} | {data.open_interest:5d} | "
                  f"{data.implied_vol:5.1%} | {data.delta:6.3f}")
    
    # Generate summary stats
    stats = screener.get_summary_stats(screened_options)
    print(f"\n📊 Summary Statistics:")
    print(f"   Total options: {stats.get('total_options', 0)}")
    print(f"   Calls: {stats.get('calls', 0)}")
    print(f"   Puts: {stats.get('puts', 0)}")
    print(f"   Avg volume: {stats.get('avg_volume', 0):,.0f}")
    print(f"   Avg OI: {stats.get('avg_open_interest', 0):,.0f}")
    print(f"   Avg IV: {stats.get('avg_implied_vol', 0):.1%}")
    
    # Export sample data
    snapshot = {
        'timestamp': datetime.now().isoformat(),
        'underlying_data': {
            symbol: {
                'bid': data.bid,
                'ask': data.ask,
                'last': data.last,
                'timestamp': data.timestamp.isoformat()
            }
            for symbol, data in underlying_data.items()
        },
        'screened_options_count': len(screened_options),
        'sample_options': []
    }
    
    if screened_options:
        top_options = sorted(screened_options, key=lambda x: x.option_data.volume, reverse=True)[:5]
        snapshot['sample_options'] = [
            {
                'symbol': opt.option_data.symbol,
                'strike': opt.option_data.strike,
                'expiry': opt.option_data.expiry,
                'option_type': opt.option_data.option_type,
                'dte': opt.dte,
                'bid': opt.option_data.bid,
                'ask': opt.option_data.ask,
                'midpoint': opt.option_data.midpoint,
                'volume': opt.option_data.volume,
                'open_interest': opt.option_data.open_interest,
                'implied_vol': opt.option_data.implied_vol,
                'delta': opt.option_data.delta,
                'gamma': opt.option_data.gamma,
                'theta': opt.option_data.theta,
                'vega': opt.option_data.vega
            }
            for opt in top_options
        ]
    
    # Save to file
    filename = f"mock_test_snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w') as f:
        json.dump(snapshot, f, indent=2, default=str)
    
    print(f"\n💾 Sample data exported to: {filename}")
    print("\n✅ Mock data test completed successfully!")
    
    return True

def run_continuous_mock():
    """Run continuous mock data generation (like the real system)"""
    print("\n🔄 Running continuous mock data generation...")
    print("Press Ctrl+C to stop")
    
    mock_gen = MockDataGenerator()
    screener = OptionsScreener(ScreeningCriteria())
    
    try:
        for i in range(10):  # Run 10 iterations (50 seconds total)
            print(f"\n--- Snapshot {i+1} ---")
            
            # Generate fresh data
            underlying_data = mock_gen.generate_underlying_data()
            underlying_prices = {symbol: data.last for symbol, data in underlying_data.items()}
            
            options_data = mock_gen.generate_options_data(underlying_prices)
            screened_options = screener.screen_options(options_data, underlying_prices)
            
            print(f"SPX: ${underlying_prices.get('SPX', 0):.2f} | "
                  f"VIX: {underlying_prices.get('VIX', 0):.1f} | "
                  f"Screened: {len(screened_options)} options")
            
            if screened_options:
                top_vol = max(screened_options, key=lambda x: x.option_data.volume)
                print(f"Top volume: {top_vol.option_data.symbol} "
                      f"{top_vol.option_data.strike}{top_vol.option_data.option_type} "
                      f"({top_vol.option_data.volume:,} contracts)")
            
            time.sleep(5)  # 5-second intervals like the real system
            
    except KeyboardInterrupt:
        print("\n🛑 Stopped by user")

if __name__ == "__main__":
    # Change to project root
    os.chdir(project_root)
    
    # Run basic test
    if test_mock_data_generation():
        
        # Ask if user wants continuous mode
        response = input("\nRun continuous mock mode? (y/n): ").lower().strip()
        if response == 'y':
            run_continuous_mock()
    
    print("\n🎉 Test completed!")
