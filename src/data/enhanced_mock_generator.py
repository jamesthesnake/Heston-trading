"""
Enhanced Mock Data Generator for Realistic Trading Simulation
Creates dynamic, realistic options and equity data with market-like behavior
"""
import random
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import math
import time

class EnhancedMockGenerator:
    """Generate highly realistic mock trading data with dynamic behavior"""
    
    def __init__(self):
        # Market state
        self.current_time = datetime.now()
        self.market_session_start = self.current_time.replace(hour=9, minute=30, second=0)
        self.market_session_end = self.current_time.replace(hour=16, minute=0, second=0)
        
        # Base underlying data
        self.underlying_data = {
            'SPX': {
                'price': 5000.0,
                'daily_vol': 0.015,  # 1.5% daily volatility
                'trend': 0.0001,     # Slight upward trend
                'last_update': datetime.now()
            },
            'SPY': {
                'price': 500.0,
                'daily_vol': 0.014,
                'trend': 0.0001,
                'last_update': datetime.now()
            },
            'VIX': {
                'price': 15.5,
                'daily_vol': 0.08,   # More volatile
                'trend': -0.0002,    # Slight downward trend
                'last_update': datetime.now()
            }
        }
        
        # Trading activity simulation
        self.trade_frequency = 2.0  # Trades per second
        self.volume_profile = self._create_volume_profile()
        
        # Options chain structure
        self.expiries = self._generate_expiry_dates()
        self.strike_chains = {}
        self._initialize_strike_chains()
        
        # Position tracking for simulation
        self.current_positions = []
        self.trade_history = []
        self.pnl_history = []
        
        # Market indicators
        self.market_sentiment = 0.0  # -1 (bearish) to 1 (bullish)
        self.volatility_regime = 'normal'  # 'low', 'normal', 'high', 'crisis'
    
    def _create_volume_profile(self) -> List[float]:
        """Create realistic intraday volume profile"""
        # U-shaped volume profile - high at open/close, lower at lunch
        hours = np.linspace(0, 6.5, 390)  # 6.5 hours in 1-minute intervals
        
        # Morning volume spike
        morning_spike = np.exp(-((hours - 0) / 0.5) ** 2)
        
        # Lunch lull
        lunch_lull = 1 - 0.3 * np.exp(-((hours - 3.25) / 0.5) ** 2)
        
        # Close spike
        close_spike = np.exp(-((hours - 6.5) / 0.3) ** 2)
        
        profile = (morning_spike + close_spike + 0.3) * lunch_lull
        return profile / np.max(profile)  # Normalize to [0, 1]
    
    def _generate_expiry_dates(self) -> List[str]:
        """Generate realistic options expiry dates"""
        expiries = []
        today = datetime.now()
        
        # Weekly expiries for next 8 weeks
        for weeks in range(1, 9):
            # Friday expiry
            days_ahead = (4 - today.weekday()) + 7 * weeks  # Next Friday
            if days_ahead <= 0:
                days_ahead += 7
            expiry_date = today + timedelta(days=days_ahead)
            expiries.append(expiry_date.strftime("%Y%m%d"))
        
        # Monthly expiries (3rd Friday of month)
        for months in [1, 2, 3, 6, 12]:
            target_date = today + timedelta(days=30 * months)
            # Find 3rd Friday
            first_day = target_date.replace(day=1)
            first_friday = (4 - first_day.weekday()) % 7 + 1
            third_friday = first_friday + 14
            expiry_date = first_day.replace(day=third_friday)
            expiries.append(expiry_date.strftime("%Y%m%d"))
        
        return sorted(list(set(expiries)))[:12]  # Keep 12 expiries
    
    def _initialize_strike_chains(self):
        """Initialize strike chains for each underlying"""
        for symbol in self.underlying_data.keys():
            if symbol == 'VIX':
                continue  # VIX doesn't have standard options
                
            current_price = self.underlying_data[symbol]['price']
            
            # Generate strikes ±20% from current price
            if symbol == 'SPX':
                increment = 25
            else:
                increment = 5
                
            strikes = []
            for i in range(-20, 21):  # 40 strikes total
                strike = round((current_price + i * increment) / increment) * increment
                if strike > 0:
                    strikes.append(strike)
            
            self.strike_chains[symbol] = sorted(strikes)
    
    def update_market_state(self):
        """Update overall market conditions"""
        # Update market sentiment (mean reverting random walk)
        sentiment_change = np.random.normal(0, 0.01) - 0.1 * self.market_sentiment
        self.market_sentiment = np.clip(self.market_sentiment + sentiment_change, -1, 1)
        
        # Update volatility regime based on market moves
        spx_returns = []
        if len(self.trade_history) > 20:
            recent_prices = [t['price'] for t in self.trade_history[-20:]]
            spx_returns = np.diff(recent_prices) / recent_prices[:-1]
            realized_vol = np.std(spx_returns) * np.sqrt(252)
            
            if realized_vol < 0.12:
                self.volatility_regime = 'low'
            elif realized_vol > 0.25:
                self.volatility_regime = 'high'
            else:
                self.volatility_regime = 'normal'
    
    def generate_underlying_snapshot(self) -> Dict:
        """Generate realistic underlying price snapshot"""
        self.update_market_state()
        snapshot = {}
        
        for symbol, data in self.underlying_data.items():
            # Time-based price evolution
            time_delta = (datetime.now() - data['last_update']).total_seconds() / 60
            
            # Generate realistic price movement
            dt = time_delta / (60 * 24 * 365)  # Convert to years
            
            # Geometric Brownian Motion with drift
            drift = data['trend']
            vol = data['daily_vol']
            
            # Add market sentiment impact
            if symbol in ['SPX', 'SPY']:
                drift += self.market_sentiment * 0.0005
                
            # Volatility clustering
            if self.volatility_regime == 'high':
                vol *= 1.5
            elif self.volatility_regime == 'low':
                vol *= 0.7
            
            # Price update
            random_shock = np.random.normal(0, 1)
            price_change = data['price'] * (drift * dt + vol * np.sqrt(dt) * random_shock)
            new_price = data['price'] + price_change
            
            # Ensure reasonable bounds
            if symbol == 'VIX':
                new_price = max(5.0, min(80.0, new_price))
            else:
                new_price = max(new_price, data['price'] * 0.95)  # No more than 5% drop
                new_price = min(new_price, data['price'] * 1.05)  # No more than 5% rise
            
            # Generate bid/ask spread
            if symbol == 'VIX':
                spread = 0.05
            elif symbol == 'SPX':
                spread = 0.25
            else:
                spread = 0.01
                
            bid = new_price - spread / 2
            ask = new_price + spread / 2
            
            # Volume based on time of day
            current_minute = (datetime.now() - self.market_session_start).total_seconds() / 60
            volume_multiplier = 1.0
            if 0 <= current_minute < len(self.volume_profile):
                volume_multiplier = self.volume_profile[int(current_minute)]
            
            base_volume = 100000 if symbol == 'SPY' else 50000
            volume = int(base_volume * volume_multiplier * random.uniform(0.5, 2.0))
            
            snapshot[symbol] = {
                'bid': round(bid, 2),
                'ask': round(ask, 2),
                'last': round(new_price, 2),
                'volume': volume,
                'timestamp': datetime.now(),
                'change': round(new_price - data['price'], 2),
                'change_pct': round((new_price - data['price']) / data['price'] * 100, 2)
            }
            
            # Update stored data
            self.underlying_data[symbol]['price'] = new_price
            self.underlying_data[symbol]['last_update'] = datetime.now()
            
            # Add to trade history
            self.trade_history.append({
                'symbol': symbol,
                'price': new_price,
                'timestamp': datetime.now()
            })
            
            # Keep only recent history
            if len(self.trade_history) > 1000:
                self.trade_history = self.trade_history[-500:]
        
        return snapshot
    
    def generate_options_snapshot(self, underlying_prices: Dict) -> List[Dict]:
        """Generate realistic options chain snapshot"""
        options = []
        
        for symbol in ['SPX', 'SPY']:
            if symbol not in underlying_prices:
                continue
                
            spot = underlying_prices[symbol]['last']
            
            for expiry in self.expiries[:6]:  # Use first 6 expiries
                days_to_expiry = self._days_to_expiry(expiry)
                if days_to_expiry <= 0:
                    continue
                    
                T = days_to_expiry / 365.0
                
                # Focus on ATM strikes ±10%
                atm_strikes = [s for s in self.strike_chains[symbol] 
                              if 0.9 * spot <= s <= 1.1 * spot]
                
                for strike in atm_strikes:
                    for option_type in ['C', 'P']:
                        option_data = self._generate_option_data(
                            symbol, strike, expiry, option_type, spot, T
                        )
                        if option_data:
                            options.append(option_data)
        
        return options
    
    def _generate_option_data(self, symbol: str, strike: float, expiry: str, 
                             option_type: str, spot: float, T: float) -> Optional[Dict]:
        """Generate individual option data with realistic Greeks and pricing"""
        
        # Moneyness
        moneyness = strike / spot
        
        # Implied volatility with skew/smile
        base_iv = 0.20  # Base IV of 20%
        
        # Volatility smile/skew
        if option_type == 'P':
            # Put skew - higher IV for OTM puts
            skew_adjustment = 0.05 * max(0, 1.0 - moneyness)
        else:
            # Call skew - slight increase for OTM calls
            skew_adjustment = 0.02 * max(0, moneyness - 1.0)
        
        # Term structure - higher IV for shorter expiries
        term_adjustment = 0.03 * (1 / max(T, 0.01))
        
        # Volatility regime adjustment
        regime_multiplier = {
            'low': 0.8,
            'normal': 1.0,
            'high': 1.3
        }.get(self.volatility_regime, 1.0)
        
        iv = (base_iv + skew_adjustment + term_adjustment * 0.1) * regime_multiplier
        iv = max(0.05, min(0.60, iv))  # Bound IV
        
        # Black-Scholes pricing (simplified)
        risk_free_rate = 0.05
        d1 = (np.log(spot / strike) + (risk_free_rate + 0.5 * iv**2) * T) / (iv * np.sqrt(T))
        d2 = d1 - iv * np.sqrt(T)
        
        from scipy.stats import norm
        
        if option_type == 'C':
            theoretical_price = (spot * norm.cdf(d1) - 
                               strike * np.exp(-risk_free_rate * T) * norm.cdf(d2))
            delta = norm.cdf(d1)
        else:
            theoretical_price = (strike * np.exp(-risk_free_rate * T) * norm.cdf(-d2) - 
                               spot * norm.cdf(-d1))
            delta = -norm.cdf(-d1)
        
        if theoretical_price < 0.05:  # Skip very cheap options
            return None
        
        # Greeks
        gamma = norm.pdf(d1) / (spot * iv * np.sqrt(T))
        theta = (-(spot * norm.pdf(d1) * iv) / (2 * np.sqrt(T)) - 
                risk_free_rate * strike * np.exp(-risk_free_rate * T) * 
                (norm.cdf(d2) if option_type == 'C' else norm.cdf(-d2))) / 365
        vega = spot * norm.pdf(d1) * np.sqrt(T) / 100
        
        # Market making spread
        spread_pct = 0.02 + 0.03 / max(T, 0.1)  # Wider spreads for shorter expiries
        spread = theoretical_price * spread_pct
        
        bid = max(0.01, theoretical_price - spread / 2)
        ask = theoretical_price + spread / 2
        
        # Volume and Open Interest based on activity
        distance_from_atm = abs(moneyness - 1.0)
        activity_factor = max(0.1, 1.0 - distance_from_atm * 3)
        
        # Time-based volume scaling
        current_minute = (datetime.now() - self.market_session_start).total_seconds() / 60
        volume_multiplier = 1.0
        if 0 <= current_minute < len(self.volume_profile):
            volume_multiplier = self.volume_profile[int(current_minute)]
        
        volume = max(1, int(random.uniform(10, 500) * activity_factor * volume_multiplier))
        open_interest = max(volume, int(random.uniform(100, 5000) * activity_factor))
        
        # Last trade
        last = random.uniform(bid, ask)
        
        return {
            'symbol': symbol,
            'strike': strike,
            'expiry': expiry,
            'type': option_type,
            'bid': round(bid, 2),
            'ask': round(ask, 2),
            'last': round(last, 2),
            'volume': volume,
            'open_interest': open_interest,
            'implied_vol': round(iv, 4),
            'delta': round(delta, 4),
            'gamma': round(gamma, 6),
            'theta': round(theta, 4),
            'vega': round(vega, 4),
            'timestamp': datetime.now()
        }
    
    def _days_to_expiry(self, expiry_str: str) -> int:
        """Calculate days to expiry"""
        expiry_date = datetime.strptime(expiry_str, "%Y%m%d")
        return (expiry_date - datetime.now()).days
    
    def generate_trading_signals(self, underlying_data: Dict, options_data: List[Dict]) -> List[Dict]:
        """Generate realistic trading signals"""
        signals = []
        
        # Simple signals based on market conditions
        spx_data = underlying_data.get('SPX', {})
        if not spx_data:
            return signals
        
        spx_price = spx_data['last']
        spx_change = spx_data.get('change_pct', 0)
        
        # Volatility signal
        vix_data = underlying_data.get('VIX', {})
        if vix_data:
            vix_level = vix_data['last']
            
            if vix_level < 12:  # Low volatility - sell volatility
                signals.append({
                    'type': 'sell_volatility',
                    'description': f'VIX at {vix_level:.1f} - Consider selling volatility',
                    'strength': 'medium',
                    'timestamp': datetime.now()
                })
            elif vix_level > 25:  # High volatility - buy volatility
                signals.append({
                    'type': 'buy_volatility',
                    'description': f'VIX at {vix_level:.1f} - Consider buying volatility',
                    'strength': 'strong',
                    'timestamp': datetime.now()
                })
        
        # Momentum signal
        if abs(spx_change) > 1.0:
            signal_type = 'bullish' if spx_change > 0 else 'bearish'
            signals.append({
                'type': signal_type,
                'description': f'SPX {spx_change:+.1f}% - Strong momentum',
                'strength': 'strong' if abs(spx_change) > 2.0 else 'medium',
                'timestamp': datetime.now()
            })
        
        return signals
    
    def generate_positions(self) -> List[Dict]:
        """Generate mock positions"""
        positions = []
        
        # Sample positions
        sample_positions = [
            {'symbol': 'SPX', 'strike': 5000, 'expiry': self.expiries[0], 'type': 'C', 'quantity': 10, 'entry_price': 25.50},
            {'symbol': 'SPX', 'strike': 4975, 'expiry': self.expiries[0], 'type': 'P', 'quantity': -10, 'entry_price': 18.75},
            {'symbol': 'SPY', 'strike': 500, 'expiry': self.expiries[1], 'type': 'C', 'quantity': 50, 'entry_price': 12.25},
        ]
        
        for pos in sample_positions:
            # Add some random P&L
            current_price = random.uniform(pos['entry_price'] * 0.8, pos['entry_price'] * 1.2)
            pnl = (current_price - pos['entry_price']) * pos['quantity'] * 100
            
            positions.append({
                **pos,
                'current_price': round(current_price, 2),
                'pnl': round(pnl, 2),
                'pnl_pct': round((current_price - pos['entry_price']) / pos['entry_price'] * 100, 1)
            })
        
        return positions

# Global instance for the application
enhanced_mock = EnhancedMockGenerator()