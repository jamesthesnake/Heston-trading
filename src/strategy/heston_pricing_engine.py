"""
Heston Pricing Engine for theoretical option prices
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
import logging
from datetime import datetime
from .heston_strategy import HestonModel
from .calibration import HestonCalibrator

logger = logging.getLogger(__name__)

class HestonPricingEngine:
    """
    Theoretical option pricing using calibrated Heston model
    """
    
    def __init__(self, config: dict):
        self.config = config
        self.heston_model = HestonModel()
        self.calibrator = HestonCalibrator(config)
        
        # Current calibrated parameters
        self.current_params = None
        self.last_calibration_time = None
        self.calibration_interval = config.get('calibration_interval_minutes', 5)
        
        # Risk-free rate and dividend assumptions
        self.risk_free_rate = config.get('risk_free_rate', 0.05)
        self.dividend_yield = config.get('dividend_yield', 0.02)
        
        logger.info("HestonPricingEngine initialized")
    
    def get_theoretical_prices(self, options_data: List[Dict], underlying_data: Dict) -> Dict[str, float]:
        """
        Calculate theoretical option prices using Heston model
        
        Args:
            options_data: List of option contracts
            underlying_data: Current underlying prices
            
        Returns:
            Dictionary mapping option keys to theoretical prices
        """
        try:
            # Check if we need to recalibrate
            if self._should_recalibrate():
                logger.info("Recalibrating Heston model to current market data")
                calibration_result = self.calibrator.calibrate_to_live_data(options_data, underlying_data)
                
                if calibration_result.get('status') == 'success':
                    self.current_params = calibration_result['params']
                    self.last_calibration_time = datetime.now()
                    
                    # Update Heston model with new parameters
                    self.heston_model.theta = self.current_params['theta']
                    self.heston_model.kappa = self.current_params['kappa']
                    self.heston_model.xi = self.current_params['xi']
                    self.heston_model.rho = self.current_params['rho']
                    self.heston_model.v0 = self.current_params['v0']
                    
                    logger.info(f"Calibration successful - RMSE: {calibration_result.get('rmse', 'N/A'):.4f}")
                else:
                    logger.warning(f"Calibration failed: {calibration_result.get('message', 'Unknown error')}")
            
            # Get current spot price
            spot = underlying_data.get('SPX', {}).get('last', 5000.0)
            
            # Calculate theoretical prices for all options
            theoretical_prices = {}
            
            for option in options_data:
                if option.get('symbol') != 'SPX':
                    continue
                    
                try:
                    option_key = self._get_option_key(option)
                    theoretical_price = self._calculate_heston_price(option, spot)
                    
                    if theoretical_price and theoretical_price > 0:
                        theoretical_prices[option_key] = theoretical_price
                        
                except Exception as e:
                    logger.debug(f"Failed to price option {option.get('strike')} {option.get('type')}: {e}")
                    continue
            
            logger.info(f"Calculated theoretical prices for {len(theoretical_prices)} options")
            return theoretical_prices
            
        except Exception as e:
            logger.error(f"Error calculating theoretical prices: {e}")
            return {}
    
    def _should_recalibrate(self) -> bool:
        """Check if we should recalibrate the model"""
        if self.current_params is None:
            return True
            
        if self.last_calibration_time is None:
            return True
            
        minutes_since_calibration = (datetime.now() - self.last_calibration_time).total_seconds() / 60
        return minutes_since_calibration >= self.calibration_interval
    
    def _calculate_heston_price(self, option: Dict, spot: float) -> Optional[float]:
        """Calculate theoretical price for a single option using Heston model"""
        try:
            strike = option.get('strike', 0)
            if strike <= 0:
                return None
                
            # Calculate time to expiry
            expiry_str = option.get('expiry', '')
            if not expiry_str:
                return None
                
            expiry_date = datetime.strptime(expiry_str, "%Y%m%d")
            days_to_expiry = (expiry_date - datetime.now()).days
            if days_to_expiry <= 0:
                return None
                
            time_to_expiry = days_to_expiry / 365.0
            option_type = option.get('type', 'C')
            
            # Use Heston model to calculate price
            if self.current_params:
                # Calculate using calibrated Heston parameters
                heston_price = self.heston_model.option_price(
                    spot=spot,
                    strike=strike,
                    T=time_to_expiry,
                    r=self.risk_free_rate,
                    q=self.dividend_yield,
                    option_type=option_type
                )
                return heston_price
            else:
                # Fallback to Black-Scholes if no calibration available
                return self._black_scholes_fallback(spot, strike, time_to_expiry, option_type)
                
        except Exception as e:
            logger.debug(f"Heston pricing failed for option: {e}")
            return None
    
    def _black_scholes_fallback(self, spot: float, strike: float, T: float, option_type: str) -> float:
        """Fallback to Black-Scholes pricing when Heston fails"""
        try:
            from scipy.stats import norm
            
            # Use a reasonable volatility estimate
            vol = 0.20  # 20% volatility
            
            d1 = (np.log(spot / strike) + (self.risk_free_rate - self.dividend_yield + 0.5 * vol**2) * T) / (vol * np.sqrt(T))
            d2 = d1 - vol * np.sqrt(T)
            
            if option_type == 'C':
                price = (spot * np.exp(-self.dividend_yield * T) * norm.cdf(d1) - 
                        strike * np.exp(-self.risk_free_rate * T) * norm.cdf(d2))
            else:  # Put
                price = (strike * np.exp(-self.risk_free_rate * T) * norm.cdf(-d2) - 
                        spot * np.exp(-self.dividend_yield * T) * norm.cdf(-d1))
            
            return max(0.01, price)  # Minimum price of $0.01
            
        except Exception as e:
            logger.debug(f"Black-Scholes fallback failed: {e}")
            return 0.01
    
    def _get_option_key(self, option: Dict) -> str:
        """Generate unique key for option"""
        symbol = option.get('symbol', '')
        strike = option.get('strike', 0)
        expiry = option.get('expiry', '')
        option_type = option.get('type', '')
        return f"{symbol}_{strike}_{expiry}_{option_type}"
    
    def get_calibration_status(self) -> Dict:
        """Get current calibration status"""
        if self.current_params is None:
            return {
                'status': 'not_calibrated',
                'message': 'Model not yet calibrated'
            }
        
        minutes_since = 0
        if self.last_calibration_time:
            minutes_since = (datetime.now() - self.last_calibration_time).total_seconds() / 60
        
        return {
            'status': 'calibrated',
            'parameters': self.current_params,
            'last_calibration': self.last_calibration_time,
            'minutes_since_calibration': minutes_since,
            'next_calibration_in': max(0, self.calibration_interval - minutes_since)
        }
    
    def force_recalibration(self, options_data: List[Dict], underlying_data: Dict) -> Dict:
        """Force immediate recalibration"""
        logger.info("Forcing model recalibration")
        calibration_result = self.calibrator.calibrate_to_live_data(options_data, underlying_data)
        
        if calibration_result.get('status') == 'success':
            self.current_params = calibration_result['params']
            self.last_calibration_time = datetime.now()
            
            # Update Heston model
            self.heston_model.theta = self.current_params['theta']
            self.heston_model.kappa = self.current_params['kappa']
            self.heston_model.xi = self.current_params['xi']
            self.heston_model.rho = self.current_params['rho']
            self.heston_model.v0 = self.current_params['v0']
        
        return calibration_result