"""
Options screening and filtering engine for SPX/XSP options
"""
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import numpy as np

from .providers.ib_provider import OptionData, UnderlyingData

logger = logging.getLogger(__name__)

@dataclass
class ScreeningCriteria:
    """Options screening criteria"""
    # DTE range
    min_dte: int = 10
    max_dte: int = 50
    
    # Strike range (percentage around ATM)
    strike_range_pct: float = 0.09  # ±9%
    
    # Spread width (percentage of mid)
    max_spread_width_pct: float = 0.10  # ≤10% of mid
    
    # Minimum mid price
    min_mid_price: float = 0.20  # ≥$0.20
    
    # Volume and open interest
    min_volume: int = 1000  # ≥1,000
    min_open_interest: int = 500  # ≥500
    
    # Symbols to screen
    symbols: List[str] = None
    
    def __post_init__(self):
        if self.symbols is None:
            self.symbols = ["SPX", "XSP"]

@dataclass
class ScreenedOption:
    """Screened option with additional metrics"""
    option_data: OptionData
    
    # Screening metrics
    dte: int
    moneyness: float  # Strike / Spot
    spread_width_pct: float
    distance_from_atm_pct: float
    
    # Risk metrics
    notional_value: float
    daily_theta_decay: float
    
    def __post_init__(self):
        """Calculate derived metrics"""
        if self.option_data.midpoint > 0:
            self.notional_value = self.option_data.midpoint * 100  # Options are per 100 shares
            self.daily_theta_decay = abs(self.option_data.theta) * self.notional_value

class OptionsScreener:
    """Options screening engine"""
    
    def __init__(self, criteria: ScreeningCriteria = None):
        self.criteria = criteria or ScreeningCriteria()
        self.expiry_cache: Dict[str, datetime] = {}
        
    def screen_options(self, options: List[OptionData], underlying_prices: Dict[str, float]) -> List[ScreenedOption]:
        """Screen options based on criteria"""
        screened = []
        
        for option in options:
            try:
                # Get underlying price
                underlying_price = underlying_prices.get(option.symbol)
                if not underlying_price:
                    continue
                    
                # Apply screening filters
                if self._passes_screening(option, underlying_price):
                    screened_option = self._create_screened_option(option, underlying_price)
                    screened.append(screened_option)
                    
            except Exception as e:
                logger.warning(f"Error screening option {option.symbol} {option.strike}: {e}")
                continue
                
        # Sort by volume descending, then by distance from ATM
        screened.sort(key=lambda x: (-x.option_data.volume, abs(x.distance_from_atm_pct)))
        
        return screened
        
    def _passes_screening(self, option: OptionData, underlying_price: float) -> bool:
        """Check if option passes all screening criteria"""
        
        # Symbol filter
        if option.symbol not in self.criteria.symbols:
            return False
            
        # DTE filter
        dte = self._calculate_dte(option.expiry)
        if not (self.criteria.min_dte <= dte <= self.criteria.max_dte):
            return False
            
        # Strike range filter (±9% around ATM)
        distance_from_atm_pct = abs(option.strike - underlying_price) / underlying_price
        if distance_from_atm_pct > self.criteria.strike_range_pct:
            return False
            
        # Spread width filter
        if option.bid <= 0 or option.ask <= 0:
            return False
            
        spread_width = option.ask - option.bid
        spread_width_pct = spread_width / option.midpoint if option.midpoint > 0 else float('inf')
        if spread_width_pct > self.criteria.max_spread_width_pct:
            return False
            
        # Minimum mid price filter
        if option.midpoint < self.criteria.min_mid_price:
            return False
            
        # Volume filter
        if option.volume < self.criteria.min_volume:
            return False
            
        # Open interest filter
        if option.open_interest < self.criteria.min_open_interest:
            return False
            
        return True
        
    def _create_screened_option(self, option: OptionData, underlying_price: float) -> ScreenedOption:
        """Create screened option with additional metrics"""
        dte = self._calculate_dte(option.expiry)
        moneyness = option.strike / underlying_price
        
        spread_width = option.ask - option.bid
        spread_width_pct = spread_width / option.midpoint if option.midpoint > 0 else 0
        
        distance_from_atm_pct = abs(option.strike - underlying_price) / underlying_price
        
        # Calculate risk metrics
        notional_value = option.midpoint * 100 if option.midpoint > 0 else 0  # Options are per 100 shares
        daily_theta_decay = abs(option.theta) * notional_value if option.theta else 0
        
        return ScreenedOption(
            option_data=option,
            dte=dte,
            moneyness=moneyness,
            spread_width_pct=spread_width_pct,
            distance_from_atm_pct=distance_from_atm_pct,
            notional_value=notional_value,
            daily_theta_decay=daily_theta_decay
        )
        
    def _calculate_dte(self, expiry_str: str) -> int:
        """Calculate days to expiration"""
        if expiry_str in self.expiry_cache:
            expiry_date = self.expiry_cache[expiry_str]
        else:
            # Parse expiry string (format: YYYYMMDD)
            try:
                expiry_date = datetime.strptime(expiry_str, "%Y%m%d")
                self.expiry_cache[expiry_str] = expiry_date
            except ValueError:
                logger.warning(f"Invalid expiry format: {expiry_str}")
                return 0
                
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        dte = (expiry_date - today).days
        
        return max(0, dte)
        
    def get_atm_strikes(self, underlying_prices: Dict[str, float], 
                       strike_increment: float = 5.0) -> Dict[str, List[float]]:
        """Get ATM strikes for each underlying"""
        atm_strikes = {}
        
        for symbol, price in underlying_prices.items():
            if symbol in self.criteria.symbols:
                # Round to nearest strike increment
                atm_strike = round(price / strike_increment) * strike_increment
                
                # Generate strikes around ATM
                max_distance = price * self.criteria.strike_range_pct
                strikes = []
                
                strike = atm_strike
                while strike <= price + max_distance:
                    strikes.append(strike)
                    strike += strike_increment
                    
                strike = atm_strike - strike_increment
                while strike >= price - max_distance:
                    strikes.append(strike)
                    strike -= strike_increment
                    
                atm_strikes[symbol] = sorted(strikes)
                
        return atm_strikes
        
    def generate_option_chain_requests(self, underlying_prices: Dict[str, float]) -> List[Tuple[str, float, str, str]]:
        """Generate list of option contracts to request"""
        requests = []
        
        # Get ATM strikes
        atm_strikes = self.get_atm_strikes(underlying_prices)
        
        # Generate expiry dates within DTE range
        expiries = self._generate_expiry_dates()
        
        for symbol in self.criteria.symbols:
            if symbol not in atm_strikes:
                continue
                
            strikes = atm_strikes[symbol]
            
            for expiry in expiries:
                for strike in strikes:
                    for option_type in ['C', 'P']:
                        requests.append((symbol, strike, expiry, option_type))
                        
        return requests
        
    def _generate_expiry_dates(self) -> List[str]:
        """Generate expiry dates within DTE range"""
        expiries = []
        today = datetime.now()
        
        # Look ahead for expiries
        for days_ahead in range(self.criteria.min_dte, self.criteria.max_dte + 30):
            future_date = today + timedelta(days=days_ahead)
            
            # Options typically expire on Fridays (weekday 4) or third Friday of month
            if future_date.weekday() == 4:  # Friday
                expiry_str = future_date.strftime("%Y%m%d")
                expiries.append(expiry_str)
                
        return expiries
        
    def update_criteria(self, **kwargs):
        """Update screening criteria"""
        for key, value in kwargs.items():
            if hasattr(self.criteria, key):
                setattr(self.criteria, key, value)
                logger.info(f"Updated screening criteria: {key} = {value}")
            else:
                logger.warning(f"Unknown criteria: {key}")
                
    def get_summary_stats(self, screened_options: List[ScreenedOption]) -> Dict:
        """Get summary statistics of screened options"""
        if not screened_options:
            return {}
            
        volumes = [opt.option_data.volume for opt in screened_options]
        ois = [opt.option_data.open_interest for opt in screened_options]
        ivs = [opt.option_data.implied_vol for opt in screened_options if opt.option_data.implied_vol > 0]
        spreads = [opt.spread_width_pct for opt in screened_options]
        
        stats = {
            'total_options': len(screened_options),
            'avg_volume': np.mean(volumes) if volumes else 0,
            'avg_open_interest': np.mean(ois) if ois else 0,
            'avg_implied_vol': np.mean(ivs) if ivs else 0,
            'avg_spread_width_pct': np.mean(spreads) if spreads else 0,
            'calls': len([opt for opt in screened_options if opt.option_data.option_type == 'C']),
            'puts': len([opt for opt in screened_options if opt.option_data.option_type == 'P']),
        }
        
        return stats
