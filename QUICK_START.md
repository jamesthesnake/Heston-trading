# ⚡ SUPER QUICK START - Heston Trading System

## 📋 What You Need
- **Mac, Linux, or Windows** with terminal access
- **5 minutes** of your time
- **No coding experience required**

## 🚀 3-Step Setup

### Step 1: Open Terminal
- **Mac**: Press `Cmd + Space`, type "Terminal", press Enter
- **Windows**: Press `Win + R`, type "cmd", press Enter  
- **Linux**: Press `Ctrl + Alt + T`

### Step 2: Navigate to the Project
```bash
cd /path/to/Heston-trading
```
*(Replace `/path/to/Heston-trading` with your actual folder path)*

### Step 3: Run the Magic Script
```bash
./setup_and_run_v2.sh
```

**That's it!** The script does everything automatically:
- ✅ Checks your Python installation
- ✅ Creates a clean environment  
- ✅ Installs all packages
- ✅ Starts the trading system
- ✅ Opens your browser automatically

## 🎯 What Happens Next

You'll see this in your terminal:
```
============================================================
🎉 SETUP COMPLETE! 🎉
============================================================

🌐 Trading Dashboard: http://localhost:8050
📊 System Metrics:    http://localhost:9090/metrics

Your Heston Trading System is now running with:
✅ Live SPX/SPY/VIX price simulation
✅ 700+ options contracts with real pricing
✅ Active trading positions with P&L tracking
✅ Real-time risk monitoring
✅ Professional trading dashboard
```

Your browser will automatically open to: **http://localhost:8050**

## 📊 What You'll See

### Live Trading Dashboard:
1. **Market Data** - Real-time price updates
   ```
   SPX: $5,000.25 (+0.1%)
   SPY: $500.15 (+0.1%)
   VIX: 15.3 (-2.1%)
   ```

2. **Active Positions** - Sample trades with live P&L
   ```
   SPX 5000C x10 - P&L: +$1,250 (+4.9%)
   SPX 4975P x-10 - P&L: +$1,500 (+8.0%)
   ```

3. **Options Chains** - 700+ contracts updating in real-time
4. **Risk Monitoring** - Professional risk metrics
5. **Trading Signals** - AI-generated recommendations

## 🎮 Try the Demo

In a new terminal window:
```bash
cd /path/to/Heston-trading
python demo_data.py
```

This shows 10 seconds of live market simulation!

## ❌ If Something Goes Wrong

### "Permission denied" error:
```bash
chmod +x setup_and_run_v2.sh
./setup_and_run_v2.sh
```

### "Python 3.11 not found":
**On Mac:**
```bash
brew install python@3.11
```

**On Linux:**
```bash
sudo apt install python3.11 python3.11-venv
```

Then run the setup script again.

### "Port already in use":
```bash
pkill -f python
./setup_and_run_v2.sh
```

### Dashboard shows "No Data":
Just refresh your browser! The data loads after a few seconds.

## 🛑 How to Stop

Press `Ctrl+C` in the terminal where the system is running.

## 🆘 Need Help?

1. **Read the detailed guide**: `README_SIMPLE.md`
2. **Check the logs**: Look in the `logs/` folder
3. **Start fresh**: Delete the `heston_venv_auto` folder and run the script again

## ✅ Success Checklist

Your system is working correctly when:
- ✅ Browser opens to http://localhost:8050
- ✅ You see live SPX/SPY/VIX prices
- ✅ Market data updates every few seconds
- ✅ Positions table shows sample trades
- ✅ P&L numbers are green/red and changing

## 🎉 You're Done!

Congratulations! You now have a **professional-grade options trading system** running with:
- Real-time market simulation
- Live options pricing
- Risk management
- Performance tracking
- Professional dashboard

**This is 100% simulation** - no real money involved!

Enjoy exploring your trading system! 🚀