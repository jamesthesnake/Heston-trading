"""
Dividend Yield Extraction using Put-Call Parity
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
import logging
from datetime import datetime, timedelta
from collections import deque

logger = logging.getLogger(__name__)

class DividendExtractor:
    """
    Extracts implied dividend yields using put-call parity on near-ATM options
    """
    
    def __init__(self, config: dict):
        self.config = config
        self.div_config = config.get('dividend_extraction', {})
        
        # Extraction parameters
        self.atm_tolerance = self.div_config.get('atm_tolerance', 0.01)  # |log(K/S)| <= 0.01
        self.min_dte = self.div_config.get('min_dte', 25)
        self.max_dte = self.div_config.get('max_dte', 35)
        self.ema_halflife = self.div_config.get('ema_halflife_min', 30)  # 30-minute half-life
        self.min_yield = self.div_config.get('min_yield', -0.05)  # -5% annually
        self.max_yield = self.div_config.get('max_yield', 0.05)   # +5% annually
        
        # History for EMA smoothing
        self.yield_history = deque(maxlen=1000)
        self.last_yield = 0.02  # Default 2% dividend yield
        
    def extract_dividend_yield(self, options_data: pd.DataFrame, spot: float, 
                              r_curve: Dict[float, float]) -> float:
        """
        Extract implied dividend yield using put-call parity
        
        Formula: q(T) = -(1/T) × ln[(C - P + Ke^(-rT))/S]
        
        Args:
            options_data: DataFrame with options data
            spot: Current spot price
            r_curve: Risk-free rate curve {T: rate}
            
        Returns:
            Implied dividend yield
        """
        logger.debug(f"Extracting dividend yield from {len(options_data)} options")
        
        # Filter for near-ATM options in target DTE range
        filtered_options = self._filter_atm_options(options_data, spot)
        
        if len(filtered_options) == 0:
            logger.warning("No suitable options for dividend extraction")
            return self.last_yield
        
        # Extract yields from put-call pairs
        yields = []
        
        for expiry, group in filtered_options.groupby('expiry'):
            # Calculate time to expiry
            if isinstance(expiry, str):
                expiry_date = datetime.strptime(expiry, "%Y%m%d")
            else:
                expiry_date = expiry
                
            T = (expiry_date - datetime.now()).days / 365.0
            
            if T <= 0:
                continue
                
            # Get risk-free rate
            r = r_curve.get(T, 0.05)
            
            # Find put-call pairs at same strike
            strikes = group['strike'].unique()
            
            for strike in strikes:
                strike_options = group[group['strike'] == strike]
                
                calls = strike_options[strike_options['option_type'] == 'C']
                puts = strike_options[strike_options['option_type'] == 'P']
                
                if len(calls) == 0 or len(puts) == 0:
                    continue
                    
                # Use best bid/ask for put-call parity
                call = calls.iloc[0]
                put = puts.iloc[0]
                
                # Calculate implied dividend yield
                try:
                    yield_val = self._calculate_yield_from_pair(
                        call, put, spot, strike, T, r
                    )
                    
                    if yield_val is not None:
                        yields.append({
                            'yield': yield_val,
                            'strike': strike,
                            'expiry': T,
                            'weight': min(call['volume'], put['volume'])  # Weight by min volume
                        })
                        
                except Exception as e:
                    logger.debug(f"Error calculating yield for K={strike}, T={T}: {e}")
                    continue
        
        if not yields:
            logger.warning("No valid dividend yields extracted")
            return self.last_yield
        
        # Calculate weighted average
        total_weight = sum(y['weight'] for y in yields)
        if total_weight == 0:
            raw_yield = np.mean([y['yield'] for y in yields])
        else:
            raw_yield = sum(y['yield'] * y['weight'] for y in yields) / total_weight
        
        # Clamp to reasonable bounds
        clamped_yield = np.clip(raw_yield, self.min_yield, self.max_yield)
        
        # Apply EMA smoothing
        smoothed_yield = self._apply_ema_smoothing(clamped_yield)
        
        # Update history
        self.yield_history.append({
            'timestamp': datetime.now(),
            'raw_yield': raw_yield,
            'clamped_yield': clamped_yield,
            'smoothed_yield': smoothed_yield,
            'sample_count': len(yields)
        })
        
        self.last_yield = smoothed_yield
        
        logger.info(f"Extracted dividend yield: {smoothed_yield:.4f} "
                   f"(raw: {raw_yield:.4f}, samples: {len(yields)})")
        
        return smoothed_yield
    
    def _filter_atm_options(self, options_data: pd.DataFrame, spot: float) -> pd.DataFrame:
        """Filter for near-ATM options in target DTE range"""
        
        # Calculate moneyness
        options_data = options_data.copy()
        options_data['log_moneyness'] = np.log(options_data['strike'] / spot)
        
        # Calculate DTE
        if 'dte' not in options_data.columns:
            options_data['dte'] = options_data['expiry'].apply(
                lambda x: self._calculate_dte(x)
            )
        
        # Apply filters
        filtered = options_data[
            (abs(options_data['log_moneyness']) <= self.atm_tolerance) &
            (options_data['dte'] >= self.min_dte) &
            (options_data['dte'] <= self.max_dte) &
            (options_data['bid'] > 0) &
            (options_data['ask'] > 0) &
            (options_data['volume'] > 0)
        ]
        
        logger.debug(f"Filtered {len(filtered)} ATM options from {len(options_data)} total")
        
        return filtered
    
    def _calculate_dte(self, expiry) -> int:
        """Calculate days to expiry"""
        if isinstance(expiry, str):
            expiry_date = datetime.strptime(expiry, "%Y%m%d")
        else:
            expiry_date = expiry
            
        return (expiry_date - datetime.now()).days
    
    def _calculate_yield_from_pair(self, call: pd.Series, put: pd.Series, 
                                  spot: float, strike: float, T: float, r: float) -> Optional[float]:
        """
        Calculate implied dividend yield from put-call pair
        
        Formula: q = -(1/T) × ln[(C - P + Ke^(-rT))/S]
        """
        # Use midpoint prices
        C = (call['bid'] + call['ask']) / 2
        P = (put['bid'] + put['ask']) / 2
        
        # Sanity checks
        if C <= 0 or P <= 0:
            return None
            
        if T <= 0 or spot <= 0 or strike <= 0:
            return None
        
        # Calculate put-call parity term
        K_discounted = strike * np.exp(-r * T)
        parity_term = (C - P + K_discounted) / spot
        
        # Check for valid parity term
        if parity_term <= 0:
            logger.debug(f"Invalid parity term: {parity_term}")
            return None
        
        # Calculate implied dividend yield
        q = -np.log(parity_term) / T
        
        # Sanity check on yield
        if not np.isfinite(q) or abs(q) > 0.5:  # |q| > 50% is unrealistic
            return None
        
        return q
    
    def _apply_ema_smoothing(self, new_yield: float) -> float:
        """Apply exponential moving average smoothing"""
        
        if not self.yield_history:
            return new_yield
        
        # Calculate EMA decay factor
        # Half-life in minutes, convert to decay per observation
        # Assuming observations every 5 seconds = 12 per minute
        observations_per_minute = 12
        alpha = 1 - np.exp(-np.log(2) / (self.ema_halflife * observations_per_minute))
        
        # Get last smoothed value
        last_smoothed = self.yield_history[-1]['smoothed_yield'] if self.yield_history else new_yield
        
        # Apply EMA
        smoothed = alpha * new_yield + (1 - alpha) * last_smoothed
        
        return smoothed
    
    def get_yield_curve(self, expiries: List[float]) -> Dict[float, float]:
        """
        Generate dividend yield curve for given expiries
        
        For now, returns flat curve at current yield
        Could be enhanced to extract term structure
        """
        current_yield = self.last_yield
        
        return {T: current_yield for T in expiries}
    
    def get_statistics(self) -> Dict:
        """Get dividend extraction statistics"""
        if not self.yield_history:
            return {}
        
        recent_yields = [h['smoothed_yield'] for h in list(self.yield_history)[-100:]]
        
        return {
            'current_yield': self.last_yield,
            'mean_yield': np.mean(recent_yields),
            'std_yield': np.std(recent_yields),
            'min_yield': np.min(recent_yields),
            'max_yield': np.max(recent_yields),
            'sample_count': len(self.yield_history),
            'last_update': self.yield_history[-1]['timestamp'] if self.yield_history else None
        }
