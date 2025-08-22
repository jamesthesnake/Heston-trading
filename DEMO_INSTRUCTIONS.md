# 🎯 Heston Trading Strategy - Live Demo Instructions

## 🚀 **One-Click Demo (Easiest)**

```bash
./START_HESTON_DEMO.sh
```

**Choose from 3 demo modes:**
1. **Complete Integrated Demo** - Full system + guided tour
2. **Dashboard Data Demo** - See strategy components in detail  
3. **Just Start System** - Manual exploration

---

## 🎪 **Demo Option 1: Complete Experience**

### Quick Start:
```bash
python run_heston_demo.py
```

**What it does:**
- ✅ Starts complete Heston trading system
- ✅ Opens dashboard automatically in browser
- ✅ Shows live strategy execution 
- ✅ Guided demonstration with explanations
- ✅ Real-time market data with 700+ options
- ✅ Live Heston model calibration
- ✅ Automated mispricing detection & trading
- ✅ Dynamic delta hedging

**You'll see:**
- Professional dashboard at http://localhost:8050
- Live market data updating every second
- Real options trading with P&L tracking
- Heston model parameters updating
- Automated trade executions
- Portfolio delta hedging

---

## 🔧 **Demo Option 2: Strategy Deep Dive**

### Technical Demo:
```bash
python dashboard_demo.py
```

**What it shows:**
- 🔬 **Heston Model Calibration** - Live parameter estimation
- 📊 **Market Data Generation** - 700+ realistic options
- 🎯 **Mispricing Detection** - Comparing market vs theoretical
- 💼 **Trade Execution** - Automated buying/selling
- ⚖️ **Delta Hedging** - Portfolio risk management
- 📈 **Performance Tracking** - Real-time P&L

**Perfect for:**
- Understanding how the strategy works
- Seeing the quantitative components
- Learning about Heston model implementation

---

## 🚀 **Demo Option 3: Manual Exploration**

### Start System Only:
```bash
# With virtual environment
source heston_env_311/bin/activate
make run-dev

# OR automated setup
./setup_and_run_v2.sh
```

**Then visit:**
- **Dashboard**: http://localhost:8050
- **Metrics**: http://localhost:9090/metrics

---

## 📊 **What You'll Experience**

### **Professional Trading Dashboard:**
```
Market Data:
SPX: $5,000.25 (+0.1%)
SPY: $500.15 (+0.1%)  
VIX: 15.3 (-2.1%)

Current Positions:
SPX 5000C x10 - P&L: +$1,250 (+4.9%)
SPX 4975P x-10 - P&L: +$1,500 (+8.0%)
SPY 500C x50 - P&L: +$8,630 (+14.1%)

Portfolio Status:
Total P&L: +$11,380
Active Positions: 3
Delta Exposure: $2,450
Hedge Position: 150 SPY shares
```

### **Live Strategy Logs:**
```
[INFO] Heston model calibrated - RMSE: 0.0187
[INFO] Found 8 mispricing signals  
[INFO] Signal: SELL SPX 5025C - 12.4% overpriced (strong)
[INFO] Executed: SOLD 5 SPX 5025C @ $18.75
[INFO] Delta hedge: Bought 125 SPY @ $500.15
[INFO] Portfolio delta: $1,250 (within band)
```

### **Real Heston Components:**
- **θ (theta)**: 0.0425 - Long-run variance
- **κ (kappa)**: 1.95 - Mean reversion speed  
- **ξ (xi)**: 0.315 - Volatility of volatility
- **ρ (rho)**: -0.68 - Asset-vol correlation
- **v₀ (v0)**: 0.041 - Initial variance

---

## 🎮 **Interactive Features**

### **While Demo is Running:**
- ✅ **Refresh dashboard** to see live updates
- ✅ **Watch terminal logs** for strategy activity  
- ✅ **See options pricing** update in real-time
- ✅ **Monitor P&L changes** as positions move
- ✅ **Observe hedging activity** maintaining neutrality

### **Data Updates Every:**
- **Market prices**: 1 second
- **Strategy cycle**: 5 seconds  
- **Model calibration**: 5 minutes
- **Dashboard refresh**: 2 seconds

---

## 🔍 **What Makes This Special**

### **Real Institutional Features:**
1. **Heston Stochastic Volatility Model** - Advanced mathematical pricing
2. **Live Parameter Calibration** - Model adapts to market conditions
3. **Quantitative Signal Generation** - 5-25% mispricing thresholds
4. **Automated Risk Management** - Position sizing and stop losses
5. **Dynamic Delta Hedging** - Portfolio neutrality with SPY/ES
6. **Professional Dashboard** - Real-time monitoring and control

### **Industry-Standard Capabilities:**
- 700+ options contracts with realistic pricing
- Microsecond-level timestamp accuracy
- Risk-adjusted position sizing
- Portfolio Greeks calculation
- Real-time P&L attribution
- Regulatory-compliant reporting

---

## 🛑 **How to Stop**

Press `Ctrl+C` in any running terminal window.

---

## 🎯 **Success Checklist**

**Your demo is working perfectly when you see:**
- ✅ Browser opens to http://localhost:8050
- ✅ Live SPX/SPY/VIX prices updating
- ✅ Options positions with changing P&L
- ✅ Strategy logs showing calibration
- ✅ Mispricing signals being detected
- ✅ Automated trades executing
- ✅ Delta hedging adjustments

---

## 💡 **Pro Tips**

1. **Let it run for 5+ minutes** to see full strategy cycle
2. **Refresh browser** to see latest data
3. **Watch terminal logs** for detailed activity
4. **Try different demo modes** for various perspectives
5. **Check metrics page** for system health

---

## 🎉 **You're Experiencing**

A **professional-grade algorithmic trading system** using:
- Advanced stochastic volatility modeling
- Real-time quantitative analysis  
- Automated execution with risk management
- Institutional-quality dashboard and reporting

**This is what $10,000+ trading platforms look like!** 🚀

---

**Ready to start? Run:** `./START_HESTON_DEMO.sh`