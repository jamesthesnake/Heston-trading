"""
Risk Management System
"""
import logging
from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class RiskMetrics:
    """Risk metrics container"""
    delta: float = 0.0
    gamma: float = 0.0
    vega: float = 0.0
    theta: float = 0.0
    total_exposure: float = 0.0
    var_95: float = 0.0
    max_drawdown: float = 0.0

class RiskManager:
    """Manages portfolio risk"""
    
    def __init__(self, config: dict):
        self.config = config
        self.risk_limits = config.get('risk', {})
        self.current_metrics = RiskMetrics()
        self.daily_pnl = 0.0
        self.starting_capital = 1000000
        
        logger.info("RiskManager initialized")
    
    def check_trade_risk(self, trade: dict) -> bool:
        """Check if trade passes risk limits"""
        # Check position size limit
        max_size = self.risk_limits.get('position_size_limit', 20000)
        if trade.get('notional', 0) > max_size:
            logger.warning(f"Trade rejected: Size {trade['notional']} exceeds limit {max_size}")
            return False
        
        # Check daily loss limit
        daily_limit = self.risk_limits.get('daily_hard_stop_pct', 1.0)
        if self.daily_pnl < -(daily_limit / 100) * self.starting_capital:
            logger.warning(f"Trade rejected: Daily loss limit reached")
            return False
        
        return True
    
    def update_metrics(self, positions: List[dict]):
        """Update risk metrics from positions"""
        total_delta = sum(p.get('delta', 0) * p.get('quantity', 0) for p in positions)
        total_gamma = sum(p.get('gamma', 0) * p.get('quantity', 0) for p in positions)
        total_vega = sum(p.get('vega', 0) * p.get('quantity', 0) for p in positions)
        total_theta = sum(p.get('theta', 0) * p.get('quantity', 0) for p in positions)
        
        self.current_metrics.delta = total_delta
        self.current_metrics.gamma = total_gamma
        self.current_metrics.vega = total_vega
        self.current_metrics.theta = total_theta
        
        logger.debug(f"Risk metrics updated: Δ={total_delta:.2f}, Γ={total_gamma:.2f}")
    
    def check_portfolio_limits(self) -> bool:
        """Check if portfolio is within risk limits"""
        # Check delta limit
        max_delta = self.risk_limits.get('max_delta_exposure', 0.05)
        if abs(self.current_metrics.delta) > max_delta * self.starting_capital:
            logger.warning(f"Delta limit breached: {self.current_metrics.delta}")
            return False
        
        # Check vega limit
        max_vega = self.risk_limits.get('max_vega_exposure', 2500)
        if abs(self.current_metrics.vega) > max_vega:
            logger.warning(f"Vega limit breached: {self.current_metrics.vega}")
            return False
        
        return True
    
    def get_risk_report(self) -> dict:
        """Generate risk report"""
        return {
            'timestamp': datetime.now().isoformat(),
            'metrics': {
                'delta': self.current_metrics.delta,
                'gamma': self.current_metrics.gamma,
                'vega': self.current_metrics.vega,
                'theta': self.current_metrics.theta
            },
            'pnl': {
                'daily': self.daily_pnl,
                'daily_pct': (self.daily_pnl / self.starting_capital) * 100
            },
            'limits': {
                'delta_used': abs(self.current_metrics.delta) / (self.risk_limits.get('max_delta_exposure', 0.05) * self.starting_capital),
                'vega_used': abs(self.current_metrics.vega) / self.risk_limits.get('max_vega_exposure', 2500)
            }
        }
