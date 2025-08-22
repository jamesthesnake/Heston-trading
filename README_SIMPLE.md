# 🎯 Heston Trading System - Quick Start Guide

## What This Is
A **professional options trading system** that simulates real SPX/XSP options trading with:
- Live market data simulation (SPX, SPY, VIX prices)
- Real options chains with 700+ contracts
- Trading signals and position tracking
- Professional web dashboard
- Risk management system

## 🚀 One-Click Setup (Recommended)

### Step 1: Check Python Version
Open Terminal and type:
```bash
python3.11 --version
```

**If you get an error**, install Python 3.11:
```bash
# On Mac:
brew install python@3.11

# On Ubuntu/Linux:
sudo apt install python3.11 python3.11-venv
```

### Step 2: Download and Run
```bash
# 1. Navigate to the project folder
cd /path/to/Heston-trading

# 2. Run the setup script (this does everything!)
./setup_and_run.sh
```

**That's it!** The script will:
- ✅ Create a clean Python environment
- ✅ Install all required packages  
- ✅ Start the trading system
- ✅ Open the dashboard automatically

## 🌐 Access Your Trading System

Once running, you'll see:
```
============================================================
Dashboard: http://localhost:8050
Metrics:   http://localhost:9090/metrics
Press Ctrl+C to stop
============================================================
```

### Open Your Browser:
- **Main Dashboard**: http://localhost:8050
- **System Metrics**: http://localhost:9090/metrics

## 📊 What You'll See

### Trading Dashboard Features:
1. **Live Market Data** - SPX, SPY, VIX prices updating every second
2. **Options Chains** - 700+ real options contracts with live pricing
3. **Active Positions** - Sample trades with live P&L (profit/loss)
4. **Trading Signals** - AI-generated buy/sell recommendations
5. **Risk Monitoring** - Real-time risk metrics
6. **Performance Charts** - P&L graphs and statistics

### Sample Display:
```
Market Data:
SPX: $5,000.25 (+0.1%)
SPY: $500.15 (+0.1%) 
VIX: 15.3 (-2.1%)

Current Positions:
SPX 5000C x10 - Entry: $25.50 - Current: $26.75 - P&L: +$1,250 (+4.9%)
SPX 4975P x-10 - Entry: $18.75 - Current: $17.25 - P&L: +$1,500 (+8.0%)
```

## 🎮 Demo Mode

To see enhanced data simulation:
```bash
# In a new terminal window:
python demo_data.py
```

This shows:
- 10 seconds of live market simulation
- Real options pricing
- Trading signals generation
- Position tracking

## ⚠️ Troubleshooting

### "Command not found" Error:
```bash
# Make the script executable:
chmod +x setup_and_run.sh
```

### "Python 3.11 not found":
```bash
# On Mac with Homebrew:
brew install python@3.11

# On Linux:
sudo apt update
sudo apt install python3.11 python3.11-venv

# Then try again:
./setup_and_run.sh
```

### Port Already in Use:
```bash
# Kill any existing processes:
pkill -f "python.*start_system"
# Then run again:
./setup_and_run.sh
```

### Dashboard Shows "No Data":
```bash
# Restart the system:
Ctrl+C  # Stop current system
./setup_and_run.sh  # Start again
```

## 🛑 How to Stop

Press `Ctrl+C` in the terminal where the system is running.

## 📁 Project Structure
```
Heston-trading/
├── setup_and_run.sh           ← ONE-CLICK SETUP SCRIPT
├── demo_data.py               ← Demo the enhanced data
├── README_SIMPLE.md           ← This file
├── requirements-working.txt   ← All required packages
├── src/                       ← Source code
│   ├── data/                  ← Market data simulation
│   ├── strategy/              ← Trading algorithms
│   ├── monitoring/            ← Dashboard & metrics
│   └── risk/                  ← Risk management
└── config/                    ← Configuration files
```

## 🎯 Success Indicators

✅ **System is working when you see:**
- Dashboard loads at http://localhost:8050
- Market data shows live prices
- Positions table shows sample trades
- P&L numbers are updating

❌ **Something's wrong if:**
- Browser shows "can't connect"
- Dashboard shows "No market data"
- Terminal shows error messages

## 💡 Tips for Newbies

1. **Keep the terminal open** - Don't close it while using the system
2. **Refresh the browser** if data looks stuck
3. **Run demo_data.py** to see how realistic the simulation is
4. **This is SIMULATION ONLY** - No real money involved
5. **Press Ctrl+C** to stop the system when done

## 🚀 Next Steps

Once running successfully:
1. Explore the dashboard features
2. Watch how prices change over time
3. See how P&L updates in real-time
4. Try the demo script for enhanced features
5. Check the system metrics page

**Need help?** The system logs everything to the `logs/` folder for debugging.

---
**🎉 Enjoy your professional trading system simulation!**