"""
Position Sizing Engine with VIX-based Risk Scaling
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class PositionSizer:
    """
    Calculates position sizes based on multiple risk constraints and VIX regime
    """
    
    def __init__(self, config: dict):
        self.config = config
        self.sizing_config = config.get('position_sizing', {})
        
        # Base limits per trade
        self.vega_limit = self.sizing_config.get('vega_limit', 300)  # $300 per 1 vol point
        self.gamma_limit = self.sizing_config.get('gamma_limit', 250)  # $250 for 1% spot move
        self.dollar_limit = self.sizing_config.get('dollar_limit', 20000)  # $20k notional
        
        # Liquidity constraints
        self.max_size_pct = self.sizing_config.get('max_size_pct', 0.15)  # 15% of displayed size
        self.max_volume_pct = self.sizing_config.get('max_volume_pct', 0.05)  # 5% of avg daily volume
        
        # VIX-based multipliers
        self.vix_thresholds = self.sizing_config.get('vix_thresholds', {
            'low': 15,      # VIX < 15: 100% size
            'medium': 25,   # VIX 15-25: 75% size  
            'high': 35      # VIX 25-35: 50% size, VIX > 35: 0% size
        })
        
        self.vix_multipliers = self.sizing_config.get('vix_multipliers', {
            'low': 1.0,
            'medium': 0.75,
            'high': 0.50,
            'extreme': 0.0
        })
        
    def calculate_position_size(self, signal: Dict, option_data: Dict, 
                               spot: float, vix: float) -> Dict:
        """
        Calculate optimal position size based on multiple constraints
        
        Args:
            signal: Trading signal with z-score and direction
            option_data: Option market data (bid, ask, volume, Greeks)
            spot: Current spot price
            vix: Current VIX level
            
        Returns:
            Position sizing result with contracts and risk metrics
        """
        
        # Extract option parameters
        bid = option_data.get('bid', 0)
        ask = option_data.get('ask', 0)
        volume = option_data.get('volume', 0)
        avg_volume = option_data.get('avg_volume', volume)  # Use current if avg not available
        
        # Greeks
        delta = option_data.get('delta', 0)
        gamma = option_data.get('gamma', 0)
        vega = option_data.get('vega', 0)
        
        if bid <= 0 or ask <= 0:
            return self._create_zero_size_result("Invalid bid/ask")
        
        mid_price = (bid + ask) / 2
        
        # Calculate size constraints
        constraints = self._calculate_constraints(
            mid_price, delta, gamma, vega, spot, volume, avg_volume
        )
        
        # Apply VIX-based scaling
        vix_multiplier = self._get_vix_multiplier(vix)
        
        if vix_multiplier == 0:
            return self._create_zero_size_result(f"VIX too high: {vix:.1f}")
        
        # Take minimum of all constraints
        base_size = min(constraints.values())
        scaled_size = int(base_size * vix_multiplier)
        
        # Ensure minimum size of 1 contract
        final_size = max(1, scaled_size) if scaled_size > 0 else 0
        
        # Calculate risk metrics for final size
        risk_metrics = self._calculate_risk_metrics(
            final_size, mid_price, delta, gamma, vega, spot
        )
        
        return {
            'contracts': final_size,
            'vix_multiplier': vix_multiplier,
            'constraints': constraints,
            'limiting_factor': min(constraints, key=constraints.get),
            'risk_metrics': risk_metrics,
            'mid_price': mid_price,
            'notional': final_size * mid_price * 100,
            'timestamp': datetime.now()
        }
    
    def _calculate_constraints(self, mid_price: float, delta: float, gamma: float, 
                              vega: float, spot: float, volume: int, 
                              avg_volume: int) -> Dict[str, int]:
        """Calculate position size constraints"""
        
        constraints = {}
        
        # Vega constraint: $300 per 1 vol point move
        if abs(vega) > 0:
            vega_contracts = int(self.vega_limit / (abs(vega) * 100))  # vega is per share, multiply by 100
            constraints['vega'] = max(1, vega_contracts)
        else:
            constraints['vega'] = 1000  # Large number if no vega risk
        
        # Gamma constraint: $250 for 1% spot move  
        if abs(gamma) > 0:
            # Gamma P&L for 1% move = 0.5 * gamma * (0.01 * spot)^2 * spot * contracts * 100
            gamma_pnl_per_contract = 0.5 * abs(gamma) * (0.01 * spot)**2 * spot * 100
            if gamma_pnl_per_contract > 0:
                gamma_contracts = int(self.gamma_limit / gamma_pnl_per_contract)
                constraints['gamma'] = max(1, gamma_contracts)
            else:
                constraints['gamma'] = 1000
        else:
            constraints['gamma'] = 1000
        
        # Dollar constraint: $20k notional
        dollar_contracts = int(self.dollar_limit / (mid_price * 100))
        constraints['dollar'] = max(1, dollar_contracts)
        
        # Liquidity constraints
        if volume > 0:
            # 15% of displayed size (assuming bid/ask size equals volume for simplicity)
            liquidity_contracts = int(volume * self.max_size_pct)
            constraints['liquidity'] = max(1, liquidity_contracts)
        else:
            constraints['liquidity'] = 1
        
        if avg_volume > 0:
            # 5% of average daily volume
            volume_contracts = int(avg_volume * self.max_volume_pct)
            constraints['avg_volume'] = max(1, volume_contracts)
        else:
            constraints['avg_volume'] = 1
        
        return constraints
    
    def _get_vix_multiplier(self, vix: float) -> float:
        """Get VIX-based position size multiplier"""
        
        if vix < self.vix_thresholds['low']:
            return self.vix_multipliers['low']  # 100%
        elif vix < self.vix_thresholds['medium']:
            return self.vix_multipliers['medium']  # 75%
        elif vix < self.vix_thresholds['high']:
            return self.vix_multipliers['high']  # 50%
        else:
            return self.vix_multipliers['extreme']  # 0%
    
    def _calculate_risk_metrics(self, contracts: int, mid_price: float, 
                               delta: float, gamma: float, vega: float, 
                               spot: float) -> Dict[str, float]:
        """Calculate risk metrics for position size"""
        
        if contracts == 0:
            return {
                'notional': 0,
                'delta_exposure': 0,
                'vega_exposure': 0,
                'gamma_exposure_1pct': 0
            }
        
        # Notional exposure
        notional = contracts * mid_price * 100
        
        # Delta exposure (dollar delta)
        delta_exposure = contracts * delta * spot * 100
        
        # Vega exposure (P&L for 1 vol point move)
        vega_exposure = contracts * vega * 100
        
        # Gamma exposure (P&L for 1% spot move)
        gamma_exposure_1pct = 0.5 * contracts * gamma * (0.01 * spot)**2 * spot * 100
        
        return {
            'notional': notional,
            'delta_exposure': delta_exposure,
            'vega_exposure': vega_exposure,
            'gamma_exposure_1pct': gamma_exposure_1pct
        }
    
    def _create_zero_size_result(self, reason: str) -> Dict:
        """Create zero position size result"""
        return {
            'contracts': 0,
            'vix_multiplier': 0,
            'constraints': {},
            'limiting_factor': reason,
            'risk_metrics': {
                'notional': 0,
                'delta_exposure': 0,
                'vega_exposure': 0,
                'gamma_exposure_1pct': 0
            },
            'mid_price': 0,
            'notional': 0,
            'timestamp': datetime.now()
        }
    
    def check_portfolio_limits(self, current_positions: List[Dict], 
                              new_position: Dict) -> Dict[str, bool]:
        """
        Check if adding new position would violate portfolio limits
        
        Args:
            current_positions: List of current positions with risk metrics
            new_position: New position to add
            
        Returns:
            Dict of limit checks {limit_name: passed}
        """
        
        # Portfolio limits
        max_portfolio_vega = self.sizing_config.get('max_portfolio_vega', 2500)
        max_portfolio_gamma = self.sizing_config.get('max_portfolio_gamma', 2000)
        max_normalized_delta = self.sizing_config.get('max_normalized_delta', 0.05)
        
        # Calculate current portfolio metrics
        current_vega = sum(pos.get('vega_exposure', 0) for pos in current_positions)
        current_gamma = sum(pos.get('gamma_exposure_1pct', 0) for pos in current_positions)
        current_delta = sum(pos.get('delta_exposure', 0) for pos in current_positions)
        
        # Calculate new totals
        new_vega = current_vega + new_position['risk_metrics']['vega_exposure']
        new_gamma = current_gamma + new_position['risk_metrics']['gamma_exposure_1pct']
        new_delta = current_delta + new_position['risk_metrics']['delta_exposure']
        
        # Normalize delta (assuming account equity for normalization)
        account_equity = self.sizing_config.get('account_equity', 1000000)  # $1M default
        normalized_delta = abs(new_delta) / account_equity
        
        checks = {
            'vega_limit': abs(new_vega) <= max_portfolio_vega,
            'gamma_limit': abs(new_gamma) <= max_portfolio_gamma,
            'delta_limit': normalized_delta <= max_normalized_delta
        }
        
        return checks
    
    def get_concentration_limits(self) -> Dict[str, Dict]:
        """Get concentration limits by expiry and moneyness buckets"""
        
        return {
            'per_expiry': {
                'max_notional': self.sizing_config.get('max_expiry_notional', 250000)
            },
            'per_bucket': {
                # DTE × Moneyness buckets with specific limits
                'buckets': {
                    ('10-20', 'ITM'): {'max_notional': 50000},
                    ('10-20', 'ATM'): {'max_notional': 100000},
                    ('10-20', 'OTM'): {'max_notional': 75000},
                    ('20-35', 'ITM'): {'max_notional': 75000},
                    ('20-35', 'ATM'): {'max_notional': 150000},
                    ('20-35', 'OTM'): {'max_notional': 100000},
                    ('35-50', 'ITM'): {'max_notional': 100000},
                    ('35-50', 'ATM'): {'max_notional': 200000},
                    ('35-50', 'OTM'): {'max_notional': 125000}
                }
            }
        }
    
    def get_sizing_statistics(self, recent_positions: List[Dict]) -> Dict:
        """Get position sizing statistics"""
        
        if not recent_positions:
            return {}
        
        sizes = [pos['contracts'] for pos in recent_positions]
        notionals = [pos['notional'] for pos in recent_positions]
        vix_multipliers = [pos.get('vix_multiplier', 1.0) for pos in recent_positions]
        
        return {
            'avg_size': np.mean(sizes),
            'median_size': np.median(sizes),
            'max_size': np.max(sizes),
            'avg_notional': np.mean(notionals),
            'avg_vix_multiplier': np.mean(vix_multipliers),
            'zero_size_pct': len([s for s in sizes if s == 0]) / len(sizes) * 100
        }
