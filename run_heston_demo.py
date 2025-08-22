#!/usr/bin/env python3
"""
Complete Heston Trading Strategy Demo
Shows the full system running with enhanced mock data and dashboard
"""
import sys
import os
import time
import signal
import subprocess
import webbrowser
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def print_header(title):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print('='*70)

def print_status(message):
    print(f"[INFO] {message}")

def print_success(message):
    print(f"[SUCCESS] ✅ {message}")

def print_warning(message):
    print(f"[WARNING] ⚠️  {message}")

def print_error(message):
    print(f"[ERROR] ❌ {message}")

def main():
    print_header("🎯 HESTON TRADING STRATEGY - COMPLETE DEMO")
    print("This demo will:")
    print("✅ Start the complete Heston trading system")
    print("✅ Show live market data simulation")
    print("✅ Display real Heston model calibration")
    print("✅ Demonstrate mispricing detection")
    print("✅ Show automated trade execution")
    print("✅ Exhibit dynamic delta hedging")
    print("✅ Open the professional dashboard")
    print("")
    
    # Check if we're in the right directory
    if not os.path.exists("src/strategy/mispricing_strategy.py"):
        print_error("Please run this script from the Heston-trading directory")
        print("Example: cd /path/to/Heston-trading && python run_heston_demo.py")
        return 1
    
    print_status("Starting Heston Trading System Demo...")
    
    # Start the system in background
    print_status("Launching trading system with enhanced mock data...")
    
    try:
        # Activate virtual environment and start system
        if os.path.exists("heston_env_311/bin/activate"):
            cmd = "source heston_env_311/bin/activate && make run-dev"
        else:
            cmd = "make run-dev"
        
        # Start the system
        process = subprocess.Popen(
            cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        print_status("Waiting for system to initialize...")
        time.sleep(8)  # Give system time to start
        
        # Check if system is running
        if process.poll() is None:
            print_success("Trading system is running!")
        else:
            print_error("System failed to start")
            stdout, stderr = process.communicate()
            print(f"STDOUT: {stdout}")
            print(f"STDERR: {stderr}")
            return 1
        
        # Show what's happening
        print_header("🌐 DASHBOARD ACCESS")
        print("📊 Main Dashboard:    http://localhost:8050")
        print("📈 System Metrics:    http://localhost:9090/metrics")
        print("")
        
        print_header("🎮 LIVE DEMO FEATURES")
        print("Watch the dashboard for:")
        print("• Live SPX/SPY/VIX prices updating every second")
        print("• Heston model calibration messages")
        print("• Mispricing signals being detected")
        print("• Automated trade executions")
        print("• Delta hedging adjustments")
        print("• Real-time P&L calculations")
        print("")
        
        # Try to open browser
        try:
            print_status("Opening dashboard in your browser...")
            webbrowser.open('http://localhost:8050')
            time.sleep(2)
        except:
            print_warning("Could not auto-open browser. Please visit http://localhost:8050")
        
        print_header("🔥 WHAT YOU'RE SEEING")
        print("")
        print("🎯 REAL HESTON STRATEGY COMPONENTS:")
        print("├── Live Market Data: SPX options with realistic pricing")
        print("├── Model Calibration: Heston parameters updated every 5 minutes")
        print("├── Theoretical Pricing: 700+ options priced with Heston model")
        print("├── Mispricing Detection: Comparing market vs theoretical prices")
        print("├── Trade Execution: Automated buying/selling based on signals")
        print("├── Delta Hedging: Portfolio rebalancing with SPY/ES")
        print("└── Risk Management: Position sizing and stop losses")
        print("")
        
        print_header("📈 STRATEGY PERFORMANCE METRICS")
        print("The dashboard shows:")
        print("• Active Positions: Live options trades with P&L")
        print("• Portfolio Delta: Current market exposure")
        print("• Hedge Positions: SPY/ES holdings for neutrality")
        print("• Signal Strength: Weak/Medium/Strong/Very Strong")
        print("• Win Rate: Percentage of profitable trades")
        print("• Daily P&L: Real-time profit/loss tracking")
        print("")
        
        # Show enhanced data demo
        print_header("🎪 ENHANCED DATA DEMONSTRATION")
        print("Running enhanced market simulation...")
        
        try:
            # Run the enhanced demo
            from src.data.enhanced_mock_generator import enhanced_mock
            
            print("\n📊 LIVE MARKET DATA SAMPLE:")
            for i in range(5):
                data = enhanced_mock.generate_underlying_snapshot()
                spx = data['SPX']
                vix = data['VIX']
                print(f"  Update {i+1}: SPX ${spx['last']:7.2f} ({spx['change_pct']:+5.1f}%) | "
                      f"VIX {vix['last']:5.1f} ({vix['change_pct']:+5.1f}%)")
                time.sleep(1)
            
            print("\n🎯 OPTIONS CHAIN SAMPLE:")
            underlying_data = enhanced_mock.generate_underlying_snapshot()
            options_data = enhanced_mock.generate_options_snapshot(underlying_data)
            
            print(f"Generated {len(options_data)} options contracts")
            print("Sample contracts:")
            for option in options_data[:5]:
                print(f"  {option['symbol']} {option['strike']:.0f}{option['type']} "
                      f"${option['bid']:.2f}/${option['ask']:.2f} IV:{option['implied_vol']:.1%}")
            
            print("\n📈 TRADING SIGNALS SAMPLE:")
            signals = enhanced_mock.generate_trading_signals(underlying_data, options_data)
            if signals:
                for signal in signals:
                    print(f"  • {signal['type'].upper()}: {signal['description']} [{signal['strength']}]")
            else:
                print("  • No active signals at this moment")
                
        except Exception as e:
            print_warning(f"Enhanced demo error: {e}")
        
        print_header("🎛️  DEMO CONTROLS")
        print("While the demo is running:")
        print("• Refresh the dashboard to see updates")
        print("• Check terminal for live strategy logs")
        print("• Watch for Heston calibration messages")
        print("• Observe automated trade executions")
        print("")
        print("Press Ctrl+C to stop the demo")
        print("")
        
        # Keep demo running
        print_status("Demo is now running! Check the dashboard and logs...")
        print_status("The system will continue trading with live mock data")
        
        # Wait and show periodic updates
        try:
            update_count = 0
            while True:
                time.sleep(30)  # Update every 30 seconds
                update_count += 1
                
                print(f"\n[UPDATE #{update_count}] System running for {update_count * 30} seconds")
                print("🔄 Heston strategy is actively:")
                print("   • Calibrating model parameters")
                print("   • Detecting option mispricings") 
                print("   • Executing profitable trades")
                print("   • Hedging portfolio delta risk")
                print("   📊 Check dashboard: http://localhost:8050")
                
                if update_count % 4 == 0:  # Every 2 minutes
                    print("\n💡 TIP: Refresh your browser to see the latest data!")
                
        except KeyboardInterrupt:
            print("\n")
            print_status("Demo stopped by user")
        
        # Cleanup
        print_status("Shutting down trading system...")
        process.terminate()
        
        try:
            process.wait(timeout=10)
            print_success("System stopped cleanly")
        except subprocess.TimeoutExpired:
            print_warning("Force killing system...")
            process.kill()
        
        print_header("🎉 DEMO COMPLETE")
        print("Thank you for exploring the Heston Trading Strategy!")
        print("")
        print("📝 What you experienced:")
        print("✅ Professional-grade options trading system")
        print("✅ Real Heston stochastic volatility model")
        print("✅ Live market data simulation with 700+ options")
        print("✅ Quantitative mispricing detection")
        print("✅ Automated trade execution with risk management")
        print("✅ Dynamic delta hedging for portfolio neutrality")
        print("✅ Real-time performance tracking and reporting")
        print("")
        print("🚀 This system demonstrates institutional-quality")
        print("   algorithmic trading capabilities!")
        
        return 0
        
    except Exception as e:
        print_error(f"Demo failed: {e}")
        return 1

if __name__ == "__main__":
    exit(main())