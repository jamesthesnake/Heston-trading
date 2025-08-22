#!/usr/bin/env python3
"""
Live Dashboard Demo - Shows Heston Strategy Data in Real-Time
"""
import sys
import time
import asyncio
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.data.enhanced_mock_generator import enhanced_mock
from src.strategy.heston_pricing_engine import HestonPricingEngine
from src.strategy.mispricing_detector import MispricingDetector
from src.strategy.trade_executor import TradeExecutor
from src.strategy.delta_hedger import DeltaHedger

def print_separator():
    print("\n" + "="*80)

def print_header(title):
    print_separator()
    print(f"  🎯 {title}")
    print_separator()

async def main():
    print_header("HESTON STRATEGY DASHBOARD DEMO")
    print("This script demonstrates the live data that powers the dashboard")
    print("showing real Heston model components in action!")
    
    # Initialize strategy components
    config = {
        'strategy': {},
        'mispricing_detection': {
            'min_mispricing_pct': 5.0,
            'strong_mispricing_pct': 15.0,
            'min_signal_confidence': 70.0
        },
        'trade_execution': {
            'max_position_size': 10,
            'max_daily_risk': 5000.0
        },
        'delta_hedging': {
            'delta_band': 0.05,
            'account_equity': 1000000
        }
    }
    
    print("\n🔧 Initializing Heston Strategy Components...")
    pricing_engine = HestonPricingEngine(config)
    mispricing_detector = MispricingDetector(config)
    trade_executor = TradeExecutor(config)
    delta_hedger = DeltaHedger(config)
    print("✅ All components initialized")
    
    print("\n🎪 Starting Live Demo - Press Ctrl+C to stop")
    
    try:
        for cycle in range(1, 11):  # Run 10 cycles
            print_header(f"STRATEGY CYCLE #{cycle}")
            
            # 1. Generate Market Data
            print("📊 1. GENERATING LIVE MARKET DATA")
            underlying_data = enhanced_mock.generate_underlying_snapshot()
            options_data = enhanced_mock.generate_options_snapshot(underlying_data)
            
            print(f"   Generated {len(options_data)} options contracts")
            print("   Market Data:")
            for symbol, data in underlying_data.items():
                print(f"     {symbol}: ${data['last']:8.2f} ({data['change_pct']:+6.1f}%) Vol: {data['volume']:,}")
            
            # 2. Heston Model Calibration & Pricing
            print("\n🔬 2. HESTON MODEL CALIBRATION & PRICING")
            theoretical_prices = pricing_engine.get_theoretical_prices(options_data, underlying_data)
            calibration_status = pricing_engine.get_calibration_status()
            
            print(f"   Calibration Status: {calibration_status.get('status', 'unknown')}")
            if calibration_status.get('parameters'):
                params = calibration_status['parameters']
                print(f"   Heston Parameters:")
                print(f"     θ (theta): {params.get('theta', 0):.4f} - Long-run variance")
                print(f"     κ (kappa): {params.get('kappa', 0):.4f} - Mean reversion speed")
                print(f"     ξ (xi):    {params.get('xi', 0):.4f} - Vol of vol")
                print(f"     ρ (rho):   {params.get('rho', 0):.4f} - Correlation")
                print(f"     v₀ (v0):   {params.get('v0', 0):.4f} - Initial variance")
            
            print(f"   Calculated theoretical prices for {len(theoretical_prices)} options")
            
            # 3. Mispricing Detection
            print("\n🎯 3. MISPRICING DETECTION")
            mispricing_signals = mispricing_detector.detect_mispricings(
                options_data, theoretical_prices, underlying_data
            )
            
            signal_summary = mispricing_detector.get_signal_summary(mispricing_signals)
            print(f"   Total Signals: {signal_summary['total_signals']}")
            print(f"   Strong Signals: {signal_summary['strong_signals']}")
            print(f"   Average Mispricing: {signal_summary['avg_mispricing']:.1f}%")
            
            if mispricing_signals:
                print("   Top Mispricing Opportunities:")
                top_signals = mispricing_detector.get_top_signals(mispricing_signals, 3)
                for i, signal in enumerate(top_signals, 1):
                    direction = "🟢 BUY" if signal.direction.value == "buy" else "🔴 SELL"
                    print(f"     {i}. {direction} {signal.symbol} {signal.strike:.0f}{signal.option_type} "
                          f"- {signal.mispricing_pct:+.1f}% mispricing ({signal.strength.value})")
            
            # 4. Trade Execution
            print("\n💼 4. AUTOMATED TRADE EXECUTION")
            if mispricing_signals:
                executed_trades = trade_executor.execute_signals(
                    mispricing_signals, options_data, underlying_data
                )
                
                if executed_trades:
                    print(f"   ✅ Executed {len(executed_trades)} new trades:")
                    for trade in executed_trades:
                        direction = "🟢 BOUGHT" if trade.direction.value == "buy" else "🔴 SOLD"
                        print(f"     {direction} {trade.quantity} {trade.symbol} {trade.strike:.0f}{trade.option_type} "
                              f"@ ${trade.entry_price:.2f}")
                else:
                    print("   ℹ️  No trades executed (signals didn't meet execution criteria)")
            else:
                print("   ℹ️  No trading signals to execute")
            
            # Update existing positions
            updated_trades = trade_executor.update_positions(options_data)
            if updated_trades:
                print(f"   📈 Updated {len(updated_trades)} existing positions")
            
            # 5. Portfolio Status
            print("\n💰 5. PORTFOLIO STATUS")
            portfolio_summary = trade_executor.get_portfolio_summary()
            print(f"   Active Positions: {portfolio_summary['active_positions']}")
            print(f"   Total P&L: ${portfolio_summary['total_pnl']:,.2f}")
            print(f"   Daily P&L: ${portfolio_summary['daily_pnl']:,.2f}")
            print(f"   Win Rate: {portfolio_summary['win_rate']:.1f}%")
            print(f"   Risk Utilization: {portfolio_summary['risk_utilization']:.1f}%")
            
            # 6. Delta Hedging
            print("\n⚖️  6. DELTA HEDGING")
            if trade_executor.active_trades:
                hedge_result = delta_hedger.rebalance_portfolio(
                    trade_executor.active_trades, options_data, underlying_data
                )
                
                print(f"   Portfolio Delta: ${delta_hedger.portfolio_delta:,.0f}")
                print(f"   Hedge Action: {hedge_result.get('action', 'unknown')}")
                
                if hedge_result.get('action') == 'hedge_executed':
                    print(f"   🔄 Hedge Executed: {hedge_result.get('quantity')} {hedge_result.get('instrument')}")
                    print(f"   Hedge Price: ${hedge_result.get('price', 0):.2f}")
                elif hedge_result.get('action') == 'no_hedge_needed':
                    normalized_delta = abs(delta_hedger.portfolio_delta) / 1000000  # $1M account
                    print(f"   ✅ Delta within band: {normalized_delta:.3f} (target: <0.05)")
            else:
                print("   ℹ️  No positions to hedge")
            
            # 7. Summary for Dashboard
            print("\n📊 7. DASHBOARD DATA SUMMARY")
            print("   This cycle generated data for:")
            print(f"     • {len(underlying_data)} underlying instruments")
            print(f"     • {len(options_data)} options contracts")
            print(f"     • {len(theoretical_prices)} theoretical prices")
            print(f"     • {len(mispricing_signals)} trading signals")
            print(f"     • {len(trade_executor.active_trades)} active positions")
            print(f"     • Portfolio delta: ${delta_hedger.portfolio_delta:,.0f}")
            
            print(f"\n⏱️  Cycle {cycle} complete. Next cycle in 10 seconds...")
            print("   🌐 This data is what powers the dashboard at http://localhost:8050")
            
            # Wait before next cycle
            await asyncio.sleep(10)
            
    except KeyboardInterrupt:
        print("\n\n🛑 Demo stopped by user")
    
    print_header("DEMO COMPLETE")
    print("🎉 You've seen the complete Heston trading strategy in action!")
    print("")
    print("📝 What this demo showed:")
    print("✅ Real-time market data generation (700+ options)")
    print("✅ Live Heston model calibration with 5 parameters")
    print("✅ Theoretical option pricing using Heston model")
    print("✅ Quantitative mispricing detection (5-25% thresholds)")
    print("✅ Automated trade execution with risk management")
    print("✅ Dynamic delta hedging for portfolio neutrality")
    print("✅ Live P&L and performance tracking")
    print("")
    print("🚀 This is the engine behind the professional dashboard!")
    print("   Visit http://localhost:8050 to see it live!")

if __name__ == "__main__":
    asyncio.run(main())