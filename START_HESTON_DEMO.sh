#!/bin/bash
# Ultimate Heston Trading Demo - One-Click Start
# This script starts everything you need to see the Heston strategy in action

clear
echo "🎯 HESTON TRADING STRATEGY - ULTIMATE DEMO"
echo "=========================================="
echo ""
echo "This will start:"
echo "✅ Complete Heston trading system"
echo "✅ Professional dashboard with live data"  
echo "✅ Real-time strategy execution"
echo "✅ Enhanced mock data generation"
echo ""

# Check if we're in the right directory
if [ ! -f "src/strategy/mispricing_strategy.py" ]; then
    echo "❌ Error: Please run this from the Heston-trading directory"
    echo "Example: cd /path/to/Heston-trading && ./START_HESTON_DEMO.sh"
    exit 1
fi

echo "🚀 Starting Heston Trading Demo..."
echo ""

# Option 1: Full integrated demo
echo "Choose your demo experience:"
echo ""
echo "1) 🎪 COMPLETE INTEGRATED DEMO (Recommended)"
echo "   • Starts full trading system + dashboard"
echo "   • Shows live strategy execution"
echo "   • Opens browser automatically"
echo "   • Guided demonstration"
echo ""
echo "2) 🔧 DASHBOARD DATA DEMO"
echo "   • Shows strategy components in detail"
echo "   • Command-line demonstration"
echo "   • See exactly what powers the dashboard"
echo ""
echo "3) 🚀 JUST START THE SYSTEM"
echo "   • Start trading system only"
echo "   • Manual dashboard access"
echo "   • No guided demo"
echo ""

read -p "Enter your choice (1-3): " choice

case $choice in
    1)
        echo ""
        echo "🎪 Starting Complete Integrated Demo..."
        echo "This will run the full Heston trading system with guided demo"
        echo ""
        python run_heston_demo.py
        ;;
    2)
        echo ""
        echo "🔧 Starting Dashboard Data Demo..."
        echo "This shows the strategy components that power the dashboard"
        echo ""
        python dashboard_demo.py
        ;;
    3)
        echo ""
        echo "🚀 Starting Trading System..."
        echo "Dashboard will be available at: http://localhost:8050"
        echo "Press Ctrl+C to stop"
        echo ""
        
        # Check for virtual environment
        if [ -d "heston_env_311" ]; then
            source heston_env_311/bin/activate
        fi
        
        make run-dev
        ;;
    *)
        echo ""
        echo "❌ Invalid choice. Please run the script again and choose 1, 2, or 3"
        exit 1
        ;;
esac

echo ""
echo "🎉 Demo session complete!"
echo ""
echo "📖 Want to run again? Just execute:"
echo "   ./START_HESTON_DEMO.sh"
echo ""
echo "📚 For detailed setup instructions, see:"
echo "   • README_SIMPLE.md"
echo "   • QUICK_START.md"
echo ""
echo "Thank you for exploring the Heston Trading Strategy! 🚀"