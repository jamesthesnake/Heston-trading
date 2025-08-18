"""
Mock data generator for testing the options monitor
"""
import random
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List
from dataclasses import dataclass

from data.providers.ib_provider import OptionData, UnderlyingData
from data.black_scholes import BlackScholesCalculator

class MockDataGenerator:
    """Generate realistic mock options and underlying data"""
    
    def __init__(self):
        self.bs_calc = BlackScholesCalculator()
        self.risk_free_rate = 0.05
        
        # Base underlying prices
        self.underlying_prices = {
            'SPX': 5000.0,
            'SPY': 500.0,
            'VIX': 15.5,
            'ES': 5010.0
        }
        
        # Generate expiry dates
        self.expiries = self._generate_expiries()
        
    def _generate_expiries(self) -> List[str]:
        """Generate realistic expiry dates"""
        expiries = []
        today = datetime.now()
        
        # Generate expiries every 7 days for next 50 days
        for days_ahead in range(14, 51, 7):  # Start at 14 days, go to 50
            expiry_date = today + timedelta(days=days_ahead)
            expiries.append(expiry_date.strftime("%Y%m%d"))
                
        return expiries[:6]  # Limit to 6 expiries
    
    def generate_underlying_data(self) -> Dict[str, UnderlyingData]:
        """Generate mock underlying data with realistic movements"""
        data = {}
        
        for symbol, base_price in self.underlying_prices.items():
            # Add some random movement
            price_change = random.uniform(-0.02, 0.02)  # ±2%
            current_price = base_price * (1 + price_change)
            
            # Generate bid/ask spread
            spread_pct = random.uniform(0.0001, 0.001)  # 0.01% to 0.1%
            spread = current_price * spread_pct
            
            bid = current_price - spread/2
            ask = current_price + spread/2
            
            data[symbol] = UnderlyingData(
                symbol=symbol,
                bid=bid,
                ask=ask,
                last=current_price,
                timestamp=datetime.now()
            )
            
            # Update base price for next iteration
            self.underlying_prices[symbol] = current_price
            
        return data
    
    def generate_options_data(self, underlying_prices: Dict[str, float]) -> List[OptionData]:
        """Generate mock options data with realistic pricing"""
        options = []
        
        for symbol in ['SPX', 'XSP']:
            if symbol not in underlying_prices:
                continue
                
            spot_price = underlying_prices[symbol]
            
            # Generate strikes around ATM (±10%)
            strike_range = 0.10
            min_strike = spot_price * (1 - strike_range)
            max_strike = spot_price * (1 + strike_range)
            
            # Strike increment based on symbol
            strike_increment = 25 if symbol == 'SPX' else 5
            
            strikes = []
            strike = round(min_strike / strike_increment) * strike_increment
            while strike <= max_strike:
                strikes.append(strike)
                strike += strike_increment
                
            for expiry in self.expiries[:4]:  # Use first 4 expiries
                T = self.bs_calc.time_to_expiry(expiry)
                if T <= 0:
                    continue
                    
                for strike in strikes:
                    for option_type in ['C', 'P']:
                        option = self._generate_single_option(
                            symbol, strike, expiry, option_type, spot_price, T
                        )
                        if option:
                            options.append(option)
                            
        return options
    
    def _generate_single_option(self, symbol: str, strike: float, expiry: str, 
                               option_type: str, spot_price: float, T: float) -> OptionData:
        """Generate a single option with realistic data"""
        
        # Generate realistic IV based on moneyness and time
        moneyness = strike / spot_price
        
        # Base IV with smile/skew
        if option_type == 'C':
            base_iv = 0.15 + 0.05 * max(0, moneyness - 1.0)  # Call skew
        else:
            base_iv = 0.15 + 0.08 * max(0, 1.0 - moneyness)  # Put skew
            
        # Add time decay effect
        base_iv += 0.02 * (1 / max(T, 0.01))  # Higher IV for shorter time
        
        # Add some randomness
        iv = base_iv + random.uniform(-0.02, 0.02)
        iv = max(0.05, min(0.50, iv))  # Bound between 5% and 50%
        
        # Calculate theoretical price using Black-Scholes
        theoretical_price = self.bs_calc.option_price(
            spot_price, strike, T, self.risk_free_rate, iv, option_type
        )
        
        if theoretical_price < 0.10:  # Skip very cheap options
            return None
            
        # Generate bid/ask around theoretical price
        spread_pct = random.uniform(0.02, 0.08)  # 2-8% spread
        spread = theoretical_price * spread_pct
        
        bid = max(0.01, theoretical_price - spread/2)
        ask = theoretical_price + spread/2
        midpoint = (bid + ask) / 2
        
        # Generate Greeks
        greeks = self.bs_calc.calculate_all_greeks(
            spot_price, strike, T, self.risk_free_rate, iv, option_type
        )
        
        # Generate volume and OI based on moneyness
        distance_from_atm = abs(moneyness - 1.0)
        volume_factor = max(0.1, 1.0 - distance_from_atm * 2)
        
        volume = int(random.uniform(500, 5000) * volume_factor)
        open_interest = int(random.uniform(1000, 10000) * volume_factor)
        
        # Generate sizes
        bid_size = random.randint(1, 50)
        ask_size = random.randint(1, 50)
        
        # Last trade
        last_price = random.uniform(bid, ask)
        last_size = random.randint(1, 20)
        
        option = OptionData(
            symbol=symbol,
            strike=strike,
            expiry=expiry,
            option_type=option_type
        )
        
        option.update_nbbo(bid, ask, bid_size, ask_size)
        option.last_price = last_price
        option.last_size = last_size
        option.volume = volume
        option.open_interest = open_interest
        option.implied_vol = iv
        option.delta = greeks['delta']
        option.gamma = greeks['gamma']
        option.theta = greeks['theta']
        option.vega = greeks['vega']
        option.last_trade_timestamp = datetime.now()
        
        return option
