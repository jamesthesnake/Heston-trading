"""
Heston Model Calibration with Quality Control
"""
import numpy as np
import pandas as pd
from scipy.optimize import minimize, differential_evolution
from typing import Dict, List, Tuple, Optional
import logging
from datetime import datetime
from .heston_strategy import HestonModel
from .dividend_extractor import DividendExtractor

logger = logging.getLogger(__name__)

class HestonCalibrator:
    """
    Calibrates Heston model to market IV surface with QC checks
    """
    
    def __init__(self, config: dict):
        self.config = config
        self.calib_config = config.get('calibration', {})
        
        # Calibration parameters
        self.alpha0 = self.calib_config.get('alpha0', 1.0)
        self.resid_ref = self.calib_config.get('resid_ref', 1.0)
        
        # Last accepted calibration
        self.last_params = None
        self.last_rmse = float('inf')
        self.last_surface = None
        self.last_calibration_time = None
        
        # Rejection tracking
        self.rejection_count = 0
        self.rejection_reasons = []
        
    def calibrate(self, iv_surface: pd.DataFrame, spot: float, 
                 r_curve: Dict[float, float], q_curve: Dict[float, float]) -> Dict:
        """
        Calibrate Heston model to IV surface
        
        Args:
            iv_surface: DataFrame with columns [strike, expiry, iv, volume, bid, ask]
            spot: Current spot price
            r_curve: Risk-free rate curve {T: rate}
            q_curve: Dividend yield curve {T: yield}
            
        Returns:
            Calibration results with params, RMSE, and QC status
        """
        logger.info(f"Starting calibration with {len(iv_surface)} options")
        
        # Prepare data
        iv_data = self._prepare_iv_data(iv_surface, spot)
        
        # Set weights (volume-based)
        weights = self._calculate_weights(iv_data)
        
        # Initial guess or warm start
        x0 = self._get_initial_guess()
        
        # Bounds for parameters
        bounds = [
            (0.02, 0.08),   # theta
            (0.5, 5.0),     # kappa
            (0.1, 1.0),     # xi
            (-0.95, -0.05), # rho
            (0.01, 0.1)     # v0
        ]
        
        # Objective function
        def objective(params):
            return self._compute_objective(params, iv_data, weights, spot, r_curve, q_curve)
        
        # Optimize
        result = minimize(objective, x0, method='L-BFGS-B', bounds=bounds,
                         options={'maxiter': 100})
        
        if not result.success:
            # Try global optimization
            logger.warning("Local optimization failed, trying global optimization")
            result = differential_evolution(objective, bounds, maxiter=50, seed=42)
        
        # Extract parameters
        theta, kappa, xi, rho, v0 = result.x
        rmse = result.fun
        
        # Create model with calibrated parameters
        model = HestonModel(theta, kappa, xi, rho, v0)
        
        # Run QC checks
        qc_result = self._run_qc_checks(model, rmse, iv_data, spot, r_curve, q_curve)
        
        # Prepare result
        calibration_result = {
            'params': model.get_params(),
            'rmse': rmse,
            'qc_passed': qc_result['passed'],
            'qc_details': qc_result,
            'timestamp': datetime.now()
        }
        
        # Update if accepted
        if qc_result['passed']:
            self.last_params = model.get_params()
            self.last_rmse = rmse
            self.last_calibration_time = datetime.now()
            self.rejection_count = 0
            logger.info(f"Calibration accepted: RMSE={rmse:.4f}")
        else:
            self.rejection_count += 1
            self.rejection_reasons.append(qc_result['reason'])
            logger.warning(f"Calibration rejected: {qc_result['reason']}")
        
        return calibration_result
    
    def _prepare_iv_data(self, iv_surface: pd.DataFrame, spot: float) -> pd.DataFrame:
        """Prepare IV data for calibration"""
        data = iv_surface.copy()
        
        # Calculate moneyness and time to expiry
        data['moneyness'] = np.log(data['strike'] / spot)
        data['T'] = (data['expiry'] - datetime.now()).dt.days / 365.0
        
        # Filter out invalid data
        data = data[(data['T'] > 0) & (data['iv'] > 0.01) & (data['iv'] < 2.0)]
        
        return data
    
    def _calculate_weights(self, iv_data: pd.DataFrame) -> np.ndarray:
        """Calculate weights for calibration"""
        # Volume-based weights with liquid bias
        weights = iv_data['volume'].values
        weights = weights / weights.sum()
        
        # Apply liquid bias
        liquid_bias = self.calib_config.get('weights', {}).get('liquid_bias', 1.5)
        weights = weights ** liquid_bias
        weights = weights / weights.sum()
        
        return weights
    
    def _get_initial_guess(self) -> np.ndarray:
        """Get initial parameter guess"""
        if self.last_params:
            # Warm start from last calibration
            return np.array([
                self.last_params['theta'],
                self.last_params['kappa'],
                self.last_params['xi'],
                self.last_params['rho'],
                self.last_params['v0']
            ])
        else:
            # Default initial guess
            return np.array([0.04, 2.0, 0.3, -0.7, 0.04])
    
    def _compute_objective(self, params: np.ndarray, iv_data: pd.DataFrame,
                          weights: np.ndarray, spot: float,
                          r_curve: Dict, q_curve: Dict) -> float:
        """Compute calibration objective function"""
        theta, kappa, xi, rho, v0 = params
        
        # Check parameter bounds
        if not self._check_param_bounds(params):
            return 1e10
        
        # Create model
        model = HestonModel(theta, kappa, xi, rho, v0)
        
        # Compute model IVs
        rmse = 0
        count = 0
        
        for idx, row in iv_data.iterrows():
            K = row['strike']
            T = row['T']
            
            # Get rates
            r = r_curve.get(T, 0.05)
            q = q_curve.get(T, 0.02)
            
            try:
                # Price option
                model_price = model.price_option(spot, K, T, r, q, 'C')
                
                # Convert to IV
                model_iv = model.implied_volatility_from_price(
                    model_price, spot, K, T, r, q, 'C'
                )
                
                # Add to RMSE
                weight = weights[count] if count < len(weights) else 1.0
                rmse += weight * (model_iv - row['iv'])**2
                count += 1
                
            except Exception as e:
                logger.debug(f"Error pricing option K={K}, T={T}: {e}")
                return 1e10
        
        if count == 0:
            return 1e10
        
        rmse = np.sqrt(rmse / count)
        
        # Add regularization
        if self.last_params:
            alpha = self._compute_adaptive_alpha()
            reg_term = alpha * sum((params[i] - self.last_params.get(k, params[i]))**2 
                                  for i, k in enumerate(['theta', 'kappa', 'xi', 'rho', 'v0']))
            rmse += reg_term
        
        return rmse
    
    def _check_param_bounds(self, params: np.ndarray) -> bool:
        """Check if parameters are within bounds"""
        theta, kappa, xi, rho, v0 = params
        
        if not (0.02 <= theta <= 0.08):
            return False
        if not (0.5 <= kappa <= 5.0):
            return False
        if not (0.1 <= xi <= 1.0):
            return False
        if not (-0.95 <= rho <= -0.05):
            return False
        if not (0.01 <= v0 <= 0.1):
            return False
        
        return True
    
    def _compute_adaptive_alpha(self) -> float:
        """Compute adaptive regularization parameter"""
        if self.last_rmse < float('inf'):
            return self.alpha0 * (self.last_rmse**2 / self.resid_ref**2)
        return self.alpha0
    
    def _run_qc_checks(self, model: HestonModel, rmse: float, 
                       iv_data: pd.DataFrame, spot: float,
                       r_curve: Dict, q_curve: Dict) -> Dict:
        """Run quality control checks"""
        
        qc_result = {
            'passed': True,
            'checks': {},
            'reason': None
        }
        
        # Check 1: RMSE improvement
        if self.last_rmse < float('inf'):
            rmse_improvement_pct = 100 * (self.last_rmse - rmse) / self.last_rmse
            rmse_improvement_abs = self.last_rmse - rmse
            
            if rmse_improvement_pct < 2.0 and rmse_improvement_abs < 0.002:
                qc_result['checks']['rmse_improvement'] = 'Failed'
                qc_result['passed'] = False
                qc_result['reason'] = f"Insufficient RMSE improvement: {rmse_improvement_pct:.1f}%"
                return qc_result
        
        qc_result['checks']['rmse_improvement'] = 'Passed'
        
        # Check 2: Feller condition
        if 2 * model.kappa * model.theta < model.xi**2:
            qc_result['checks']['feller'] = 'Warning'
            # Don't fail on Feller alone if RMSE is good
        else:
            qc_result['checks']['feller'] = 'Passed'
        
        # Check 3: Static arbitrage
        arb_violations = self._check_static_arbitrage(model, iv_data, spot, r_curve, q_curve)
        if arb_violations > 0:
            qc_result['checks']['static_arbitrage'] = f'{arb_violations} violations'
            if arb_violations > 5:  # Allow some violations
                qc_result['passed'] = False
                qc_result['reason'] = f"Too many arbitrage violations: {arb_violations}"
                return qc_result
        else:
            qc_result['checks']['static_arbitrage'] = 'Passed'
        
        # Check 4: Local stability
        local_rmse_ok = self._check_local_stability(model, iv_data, spot, r_curve, q_curve)
        if not local_rmse_ok:
            qc_result['checks']['local_stability'] = 'Failed'
            qc_result['passed'] = False
            qc_result['reason'] = "Local RMSE spike detected"
            return qc_result
        
        qc_result['checks']['local_stability'] = 'Passed'
        
        return qc_result
    
    def _check_static_arbitrage(self, model: HestonModel, iv_data: pd.DataFrame,
                               spot: float, r_curve: Dict, q_curve: Dict) -> int:
        """Check for static arbitrage violations"""
        violations = 0
        
        # Group by expiry for butterfly checks
        for expiry, group in iv_data.groupby('T'):
            strikes = sorted(group['strike'].values)
            
            if len(strikes) < 3:
                continue
            
            r = r_curve.get(expiry, 0.05)
            q = q_curve.get(expiry, 0.02)
            
            # Check butterfly arbitrage
            for i in range(len(strikes) - 2):
                K1, K2, K3 = strikes[i], strikes[i+1], strikes[i+2]
                
                try:
                    C1 = model.price_option(spot, K1, expiry, r, q, 'C')
                    C2 = model.price_option(spot, K2, expiry, r, q, 'C')
                    C3 = model.price_option(spot, K3, expiry, r, q, 'C')
                    
                    # Butterfly spread value should be non-negative
                    butterfly = C1 - 2*C2 + C3
                    
                    if butterfly < -0.01:  # Small tolerance
                        violations += 1
                        
                except:
                    pass
        
        return violations
    
    def _check_local_stability(self, model: HestonModel, iv_data: pd.DataFrame,
                              spot: float, r_curve: Dict, q_curve: Dict) -> bool:
        """Check local RMSE stability"""
        
        # Define local neighborhoods
        moneyness_buckets = [(-0.09, -0.06), (-0.06, -0.03), (-0.03, 0.03), 
                           (0.03, 0.06), (0.06, 0.09)]
        dte_buckets = [(10, 20), (20, 35), (35, 50)]
        
        for m_min, m_max in moneyness_buckets:
            for dte_min, dte_max in dte_buckets:
                # Get local data
                local_data = iv_data[
                    (iv_data['moneyness'] >= m_min) & 
                    (iv_data['moneyness'] <= m_max) &
                    (iv_data['T'] * 365 >= dte_min) & 
                    (iv_data['T'] * 365 <= dte_max)
                ]
                
                if len(local_data) < 3:
                    continue
                
                # Compute local RMSE
                local_rmse = 0
                count = 0
                
                for _, row in local_data.iterrows():
                    try:
                        r = r_curve.get(row['T'], 0.05)
                        q = q_curve.get(row['T'], 0.02)
                        
                        model_price = model.price_option(spot, row['strike'], row['T'], r, q, 'C')
                        model_iv = model.implied_volatility_from_price(
                            model_price, spot, row['strike'], row['T'], r, q, 'C'
                        )
                        
                        local_rmse += (model_iv - row['iv'])**2
                        count += 1
                    except:
                        pass
                
                if count > 0:
                    local_rmse = np.sqrt(local_rmse / count)
                    
                    # Check if local RMSE spikes
                    if self.last_rmse < float('inf') and local_rmse > 1.25 * self.last_rmse:
                        logger.warning(f"Local RMSE spike in region m=[{m_min},{m_max}], dte=[{dte_min},{dte_max}]")
                        return False
        
        return True
    
    def get_surface(self) -> Optional[pd.DataFrame]:
        """Get calibrated IV surface"""
        if not self.last_params:
            return None
        
        # Generate surface grid
        model = HestonModel(**self.last_params)
        
        spot = 5000  # Default, should be passed in
        strikes = np.arange(4500, 5500, 25)
        expiries = [10, 15, 20, 30, 45] / 365.0
        
        surface = []
        for T in expiries:
            for K in strikes:
                try:
                    price = model.price_option(spot, K, T, 0.05, 0.02, 'C')
                    iv = model.implied_volatility_from_price(price, spot, K, T, 0.05, 0.02, 'C')
                    
                    surface.append({
                        'strike': K,
                        'expiry': T * 365,
                        'iv': iv,
                        'moneyness': np.log(K / spot)
                    })
                except:
                    pass
        
        return pd.DataFrame(surface)
