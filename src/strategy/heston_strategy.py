"""
Heston Model Implementation with Fourier Pricing
"""
import numpy as np
from scipy.integrate import quad
from scipy.optimize import minimize
from scipy.stats import norm
from typing import Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

class HestonModel:
    """
    Heston stochastic volatility model
    dS = (r-q)*S*dt + sqrt(v)*S*dW_S
    dv = kappa*(theta-v)*dt + xi*sqrt(v)*dW_v
    corr(dW_S, dW_v) = rho
    """
    
    def __init__(self, theta: float = 0.04, kappa: float = 2.0, 
                 xi: float = 0.3, rho: float = -0.7, v0: float = 0.04):
        """
        Initialize Heston model parameters
        
        Args:
            theta: Long-run variance
            kappa: Mean reversion speed
            xi: Vol of vol
            rho: Correlation between asset and variance
            v0: Initial variance
        """
        self.theta = theta
        self.kappa = kappa
        self.xi = xi
        self.rho = rho
        self.v0 = v0
        
        # Cache for characteristic function
        self._cf_cache = {}
        
        # Validate Feller condition
        self._check_feller()
    
    def _check_feller(self) -> bool:
        """Check Feller condition: 2*kappa*theta >= xi^2"""
        feller = 2 * self.kappa * self.theta >= self.xi**2
        if not feller:
            logger.warning(f"Feller condition violated: 2κθ={2*self.kappa*self.theta:.4f} < ξ²={self.xi**2:.4f}")
        return feller
    
    def characteristic_function(self, u: complex, T: float, r: float = 0.05, q: float = 0.02) -> complex:
        """
        Heston characteristic function
        """
        # Check cache
        cache_key = (u, T, r, q, self.theta, self.kappa, self.xi, self.rho, self.v0)
        if cache_key in self._cf_cache:
            return self._cf_cache[cache_key]
        
        # Calculate characteristic function
        d = np.sqrt((self.rho * self.xi * u * 1j - self.kappa)**2 - 
                   self.xi**2 * (-u * 1j - u**2))
        
        g = (self.kappa - self.rho * self.xi * u * 1j - d) / \
            (self.kappa - self.rho * self.xi * u * 1j + d)
        
        exp_dt = np.exp(-d * T)
        
        A = (r - q) * u * 1j * T + \
            (self.kappa * self.theta / self.xi**2) * \
            ((self.kappa - self.rho * self.xi * u * 1j - d) * T - 
             2 * np.log((1 - g * exp_dt) / (1 - g)))
        
        B = (self.kappa - self.rho * self.xi * u * 1j - d) / self.xi**2 * \
            ((1 - exp_dt) / (1 - g * exp_dt))
        
        result = np.exp(A + B * self.v0)
        
        # Cache result
        self._cf_cache[cache_key] = result
        
        return result
    
    def price_option(self, S: float, K: float, T: float, r: float = 0.05, 
                    q: float = 0.02, option_type: str = 'C') -> float:
        """
        Price option using Fourier transform
        """
        # Fourier integral
        def integrand(u):
            cf = self.characteristic_function(u - 1j, T, r, q)
            return np.real(np.exp(-1j * u * np.log(K/S)) * cf / (1j * u))
        
        # Numerical integration
        integral, _ = quad(integrand, 0, 100)
        
        # Call price
        call_price = S * np.exp(-q * T) - K * np.exp(-r * T) / np.pi * integral
        
        if option_type == 'C':
            return call_price
        else:  # Put via put-call parity
            return call_price - S * np.exp(-q * T) + K * np.exp(-r * T)
    
    def implied_volatility_from_price(self, price: float, S: float, K: float, 
                                     T: float, r: float = 0.05, q: float = 0.02, 
                                     option_type: str = 'C') -> float:
        """
        Calculate IV from Heston price using Newton-Raphson
        """
        # Initial guess
        iv = 0.2
        
        for _ in range(20):
            # Black-Scholes price and vega
            d1 = (np.log(S/K) + (r - q + 0.5*iv**2)*T) / (iv * np.sqrt(T))
            d2 = d1 - iv * np.sqrt(T)
            
            if option_type == 'C':
                bs_price = S * np.exp(-q*T) * norm.cdf(d1) - K * np.exp(-r*T) * norm.cdf(d2)
            else:
                bs_price = K * np.exp(-r*T) * norm.cdf(-d2) - S * np.exp(-q*T) * norm.cdf(-d1)
            
            vega = S * np.exp(-q*T) * norm.pdf(d1) * np.sqrt(T)
            
            # Newton step
            if abs(vega) < 1e-10:
                break
            
            iv = iv - (bs_price - price) / vega
            iv = max(0.01, min(2.0, iv))  # Bound IV
        
        return iv
    
    def get_params(self) -> Dict[str, float]:
        """Get model parameters"""
        return {
            'theta': self.theta,
            'kappa': self.kappa,
            'xi': self.xi,
            'rho': self.rho,
            'v0': self.v0
        }
    
    def set_params(self, params: Dict[str, float]):
        """Set model parameters"""
        self.theta = params.get('theta', self.theta)
        self.kappa = params.get('kappa', self.kappa)
        self.xi = params.get('xi', self.xi)
        self.rho = params.get('rho', self.rho)
        self.v0 = params.get('v0', self.v0)
        
        # Clear cache when parameters change
        self._cf_cache.clear()
        
        # Check Feller condition
        self._check_feller()
