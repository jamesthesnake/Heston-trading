#!/usr/bin/env python3
"""
Launch Fancy Trading Dashboard
Start the beautiful, modern trading dashboard with real-time features
"""
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def main():
    """Launch the fancy dashboard"""
    print("🚀 LAUNCHING FANCY TRADING DASHBOARD")
    print("=" * 50)
    
    try:
        # Import the fancy dashboard
        from src.monitoring.fancy_dashboard import FancyTradingDashboard
        
        print("✅ Dashboard modules loaded successfully")
        print("🎨 Initializing fancy UI components...")
        
        # Create and run dashboard
        dashboard = FancyTradingDashboard(port=8050)
        
        print("\n🎉 Dashboard Ready!")
        print("=" * 50)
        print("📊 URL: http://localhost:8050")
        print("✨ Features:")
        print("  • 🎨 Modern dark theme with animations")
        print("  • 📈 Real-time charts and metrics") 
        print("  • 🎯 Interactive portfolio overview")
        print("  • 🛡️ Risk management dashboard")
        print("  • ⚙️ System health monitoring")
        print("  • 📱 Responsive design")
        print("\n💡 Tip: Press Ctrl+C to stop the dashboard")
        print("=" * 50)
        
        # Run the dashboard
        dashboard.run(debug=False, host='0.0.0.0')
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("\n💡 Solution:")
        print("1. Install missing dependencies:")
        print("   pip install dash-bootstrap-components")
        print("2. Ensure you're in the project root directory")
        
    except Exception as e:
        print(f"❌ Error launching dashboard: {e}")
        print("\n💡 Try running the quick start demo first:")
        print("   python quick_start.py")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ Dashboard stopped by user")
        print("👋 Thanks for using the Heston Trading System!")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)