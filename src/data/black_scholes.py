"""
Black-Scholes option pricing and Greeks calculation
"""
import numpy as np
from scipy.stats import norm
from scipy.optimize import brentq
from typing import Dict, Tuple
import logging

logger = logging.getLogger(__name__)

class BlackScholesCalculator:
    """Black-Scholes option pricing and Greeks calculator"""
    
    @staticmethod
    def d1(S: float, K: float, T: float, r: float, sigma: float, q: float = 0.0) -> float:
        """Calculate d1 parameter"""
        if T <= 0 or sigma <= 0:
            return 0.0
        return (np.log(S / K) + (r - q + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    
    @staticmethod
    def d2(S: float, K: float, T: float, r: float, sigma: float, q: float = 0.0) -> float:
        """Calculate d2 parameter"""
        if T <= 0 or sigma <= 0:
            return 0.0
        return BlackScholesCalculator.d1(S, K, T, r, sigma, q) - sigma * np.sqrt(T)
    
    @staticmethod
    def call_price(S: float, K: float, T: float, r: float, sigma: float, q: float = 0.0) -> float:
        """Calculate call option price"""
        if T <= 0:
            return max(S - K, 0)
        if sigma <= 0:
            return max(S * np.exp(-q * T) - K * np.exp(-r * T), 0)
            
        d1_val = BlackScholesCalculator.d1(S, K, T, r, sigma, q)
        d2_val = BlackScholesCalculator.d2(S, K, T, r, sigma, q)
        
        price = (S * np.exp(-q * T) * norm.cdf(d1_val) - 
                K * np.exp(-r * T) * norm.cdf(d2_val))
        
        return max(price, 0)
    
    @staticmethod
    def put_price(S: float, K: float, T: float, r: float, sigma: float, q: float = 0.0) -> float:
        """Calculate put option price"""
        if T <= 0:
            return max(K - S, 0)
        if sigma <= 0:
            return max(K * np.exp(-r * T) - S * np.exp(-q * T), 0)
            
        d1_val = BlackScholesCalculator.d1(S, K, T, r, sigma, q)
        d2_val = BlackScholesCalculator.d2(S, K, T, r, sigma, q)
        
        price = (K * np.exp(-r * T) * norm.cdf(-d2_val) - 
                S * np.exp(-q * T) * norm.cdf(-d1_val))
        
        return max(price, 0)
    
    @staticmethod
    def option_price(S: float, K: float, T: float, r: float, sigma: float, 
                    option_type: str, q: float = 0.0) -> float:
        """Calculate option price (call or put)"""
        if option_type.upper() == 'C':
            return BlackScholesCalculator.call_price(S, K, T, r, sigma, q)
        else:
            return BlackScholesCalculator.put_price(S, K, T, r, sigma, q)
    
    @staticmethod
    def delta(S: float, K: float, T: float, r: float, sigma: float, 
             option_type: str, q: float = 0.0) -> float:
        """Calculate delta (price sensitivity to underlying)"""
        if T <= 0 or sigma <= 0:
            if option_type.upper() == 'C':
                return 1.0 if S > K else 0.0
            else:
                return -1.0 if S < K else 0.0
                
        d1_val = BlackScholesCalculator.d1(S, K, T, r, sigma, q)
        
        if option_type.upper() == 'C':
            return np.exp(-q * T) * norm.cdf(d1_val)
        else:
            return -np.exp(-q * T) * norm.cdf(-d1_val)
    
    @staticmethod
    def gamma(S: float, K: float, T: float, r: float, sigma: float, q: float = 0.0) -> float:
        """Calculate gamma (delta sensitivity to underlying)"""
        if T <= 0 or sigma <= 0 or S <= 0:
            return 0.0
            
        d1_val = BlackScholesCalculator.d1(S, K, T, r, sigma, q)
        
        return (np.exp(-q * T) * norm.pdf(d1_val)) / (S * sigma * np.sqrt(T))
    
    @staticmethod
    def theta(S: float, K: float, T: float, r: float, sigma: float, 
             option_type: str, q: float = 0.0) -> float:
        """Calculate theta (time decay) - per day"""
        if T <= 0:
            return 0.0
        if sigma <= 0:
            return 0.0
            
        d1_val = BlackScholesCalculator.d1(S, K, T, r, sigma, q)
        d2_val = BlackScholesCalculator.d2(S, K, T, r, sigma, q)
        
        if option_type.upper() == 'C':
            theta_val = ((-S * np.exp(-q * T) * norm.pdf(d1_val) * sigma) / (2 * np.sqrt(T)) -
                        r * K * np.exp(-r * T) * norm.cdf(d2_val) +
                        q * S * np.exp(-q * T) * norm.cdf(d1_val))
        else:
            theta_val = ((-S * np.exp(-q * T) * norm.pdf(d1_val) * sigma) / (2 * np.sqrt(T)) +
                        r * K * np.exp(-r * T) * norm.cdf(-d2_val) -
                        q * S * np.exp(-q * T) * norm.cdf(-d1_val))
        
        # Convert to per-day theta
        return theta_val / 365.0
    
    @staticmethod
    def vega(S: float, K: float, T: float, r: float, sigma: float, q: float = 0.0) -> float:
        """Calculate vega (volatility sensitivity) - per 1% vol change"""
        if T <= 0 or S <= 0:
            return 0.0
            
        d1_val = BlackScholesCalculator.d1(S, K, T, r, sigma, q)
        
        vega_val = S * np.exp(-q * T) * norm.pdf(d1_val) * np.sqrt(T)
        
        # Convert to per 1% volatility change
        return vega_val / 100.0
    
    @staticmethod
    def rho(S: float, K: float, T: float, r: float, sigma: float, 
           option_type: str, q: float = 0.0) -> float:
        """Calculate rho (interest rate sensitivity) - per 1% rate change"""
        if T <= 0:
            return 0.0
            
        d2_val = BlackScholesCalculator.d2(S, K, T, r, sigma, q)
        
        if option_type.upper() == 'C':
            rho_val = K * T * np.exp(-r * T) * norm.cdf(d2_val)
        else:
            rho_val = -K * T * np.exp(-r * T) * norm.cdf(-d2_val)
        
        # Convert to per 1% rate change
        return rho_val / 100.0
    
    @staticmethod
    def implied_volatility(market_price: float, S: float, K: float, T: float, 
                          r: float, option_type: str, q: float = 0.0) -> float:
        """Calculate implied volatility using Brent's method"""
        if T <= 0:
            return 0.0
        if market_price <= 0:
            return 0.0
            
        # Intrinsic value
        if option_type.upper() == 'C':
            intrinsic = max(S * np.exp(-q * T) - K * np.exp(-r * T), 0)
        else:
            intrinsic = max(K * np.exp(-r * T) - S * np.exp(-q * T), 0)
            
        if market_price <= intrinsic:
            return 0.0
            
        def objective(sigma):
            try:
                theoretical_price = BlackScholesCalculator.option_price(
                    S, K, T, r, sigma, option_type, q
                )
                return theoretical_price - market_price
            except:
                return float('inf')
        
        try:
            # Use Brent's method to find IV
            iv = brentq(objective, 0.001, 5.0, xtol=1e-6, maxiter=100)
            return max(0.001, min(5.0, iv))  # Bound IV between 0.1% and 500%
        except:
            # Fallback to approximation if Brent fails
            return BlackScholesCalculator._iv_approximation(market_price, S, K, T, r, option_type, q)
    
    @staticmethod
    def _iv_approximation(market_price: float, S: float, K: float, T: float, 
                         r: float, option_type: str, q: float = 0.0) -> float:
        """Approximation for implied volatility when numerical methods fail"""
        try:
            # Simple approximation based on Brenner-Subrahmanyam
            forward = S * np.exp((r - q) * T)
            
            if option_type.upper() == 'C':
                if S > K:  # ITM call
                    return max(0.1, 2 * market_price / (S * np.sqrt(T)))
                else:  # OTM call
                    return max(0.1, np.sqrt(2 * np.pi / T) * market_price / S)
            else:  # Put
                if S < K:  # ITM put
                    return max(0.1, 2 * market_price / (S * np.sqrt(T)))
                else:  # OTM put
                    return max(0.1, np.sqrt(2 * np.pi / T) * market_price / S)
        except:
            return 0.2  # Default 20% vol
    
    @staticmethod
    def calculate_all_greeks(S: float, K: float, T: float, r: float, sigma: float, 
                           option_type: str, q: float = 0.0) -> Dict[str, float]:
        """Calculate all Greeks at once"""
        try:
            greeks = {
                'price': BlackScholesCalculator.option_price(S, K, T, r, sigma, option_type, q),
                'delta': BlackScholesCalculator.delta(S, K, T, r, sigma, option_type, q),
                'gamma': BlackScholesCalculator.gamma(S, K, T, r, sigma, q),
                'theta': BlackScholesCalculator.theta(S, K, T, r, sigma, option_type, q),
                'vega': BlackScholesCalculator.vega(S, K, T, r, sigma, q),
                'rho': BlackScholesCalculator.rho(S, K, T, r, sigma, option_type, q)
            }
            
            # Validate results
            for key, value in greeks.items():
                if not np.isfinite(value):
                    greeks[key] = 0.0
                    
            return greeks
            
        except Exception as e:
            logger.warning(f"Error calculating Greeks: {e}")
            return {
                'price': 0.0,
                'delta': 0.0,
                'gamma': 0.0,
                'theta': 0.0,
                'vega': 0.0,
                'rho': 0.0
            }
    
    @staticmethod
    def time_to_expiry(expiry_str: str) -> float:
        """Convert expiry string to time in years"""
        from datetime import datetime
        
        try:
            expiry_date = datetime.strptime(expiry_str, "%Y%m%d")
            now = datetime.now()
            
            # Calculate time to expiry in years
            time_diff = expiry_date - now
            T = time_diff.total_seconds() / (365.25 * 24 * 3600)
            
            return max(0.0, T)  # Ensure non-negative
            
        except Exception as e:
            logger.warning(f"Error parsing expiry {expiry_str}: {e}")
            return 0.0
