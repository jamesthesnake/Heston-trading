"""
Risk Management System - Legacy Interface
This module provides backward compatibility while delegating to the comprehensive strategy risk manager
"""
import logging
from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass

# Import the comprehensive risk manager
from ..strategy.risk_manager import RiskManager as ComprehensiveRiskManager, RiskLevel

logger = logging.getLogger(__name__)

@dataclass
class RiskMetrics:
    """Risk metrics container - legacy interface"""
    delta: float = 0.0
    gamma: float = 0.0
    vega: float = 0.0
    theta: float = 0.0
    total_exposure: float = 0.0
    var_95: float = 0.0
    max_drawdown: float = 0.0

class RiskManager:
    """
    Legacy risk manager interface that delegates to comprehensive strategy risk manager
    Maintains backward compatibility while providing enhanced functionality
    """
    
    def __init__(self, config: dict):
        self.config = config
        
        # Initialize comprehensive risk manager
        self.comprehensive_rm = ComprehensiveRiskManager(config)
        
        # Legacy interface compatibility
        self.risk_limits = config.get('risk', {})
        self.current_metrics = RiskMetrics()
        self.daily_pnl = 0.0
        self.starting_capital = config.get('risk_management', {}).get('starting_equity', 1000000)
        
        logger.info("Legacy RiskManager initialized with comprehensive backend")
    
    def check_trade_risk(self, trade: dict) -> bool:
        """Check if trade passes risk limits - enhanced with comprehensive checks"""
        
        # Convert trade to position format for comprehensive check
        position = {
            'notional': trade.get('notional', 0),
            'vega_exposure': trade.get('vega', 0) * trade.get('quantity', 0) * 100,
            'gamma_exposure_1pct': trade.get('gamma', 0) * trade.get('quantity', 0) * 100,
            'delta_exposure': trade.get('delta', 0) * trade.get('quantity', 0) * 100
        }
        
        # Use comprehensive risk manager
        risk_check = self.comprehensive_rm.should_allow_new_position(position)
        
        if not risk_check['allowed']:
            logger.warning(f"Trade rejected by comprehensive risk manager: {risk_check['reason']}")
            return False
        
        # Legacy checks for backward compatibility
        max_size = self.risk_limits.get('position_size_limit', 20000)
        if trade.get('notional', 0) > max_size:
            logger.warning(f"Trade rejected: Size {trade['notional']} exceeds limit {max_size}")
            return False
        
        return True
    
    def update_metrics(self, positions: List[dict]):
        """Update risk metrics from positions"""
        
        # Update comprehensive risk manager
        self.comprehensive_rm.positions = positions
        
        # Update legacy metrics for backward compatibility
        total_delta = sum(p.get('delta', 0) * p.get('quantity', 0) for p in positions)
        total_gamma = sum(p.get('gamma', 0) * p.get('quantity', 0) for p in positions)
        total_vega = sum(p.get('vega', 0) * p.get('quantity', 0) for p in positions)
        total_theta = sum(p.get('theta', 0) * p.get('quantity', 0) for p in positions)
        
        self.current_metrics.delta = total_delta
        self.current_metrics.gamma = total_gamma
        self.current_metrics.vega = total_vega
        self.current_metrics.theta = total_theta
        
        # Update daily P&L
        self.comprehensive_rm.update_daily_pnl(self.daily_pnl)
        
        logger.debug(f"Risk metrics updated: Δ={total_delta:.2f}, Γ={total_gamma:.2f}")
    
    def check_portfolio_limits(self) -> bool:
        """Check if portfolio is within risk limits - enhanced"""
        
        # Use comprehensive risk manager
        risk_assessment = self.comprehensive_rm.check_risk_limits(
            self.comprehensive_rm.positions, 
            self.daily_pnl, 
            {'timestamp': datetime.now()}
        )
        
        # Return False if any breaches detected
        if risk_assessment['breaches']:
            logger.warning(f"Portfolio limits breached: {len(risk_assessment['breaches'])} violations")
            return False
        
        return True
    
    def get_risk_report(self) -> dict:
        """Generate enhanced risk report"""
        
        # Get comprehensive risk summary
        comprehensive_summary = self.comprehensive_rm.get_risk_summary()
        
        # Legacy format with enhanced data
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
            },
            # Enhanced comprehensive data
            'comprehensive': {
                'risk_level': comprehensive_summary['risk_level'],
                'breach_count': comprehensive_summary['breach_count_today'],
                'soft_stop_threshold': comprehensive_summary['soft_stop_threshold'],
                'hard_stop_threshold': comprehensive_summary['hard_stop_threshold'],
                'position_count': comprehensive_summary['position_count']
            }
        }
    
    # Additional methods for enhanced functionality
    def get_comprehensive_manager(self) -> ComprehensiveRiskManager:
        """Get access to comprehensive risk manager for advanced features"""
        return self.comprehensive_rm
    
    def is_emergency_stop(self) -> bool:
        """Check if emergency stop is active"""
        return self.comprehensive_rm.current_risk_level == RiskLevel.EMERGENCY
    
    def is_hard_stop(self) -> bool:
        """Check if hard stop is active"""
        return self.comprehensive_rm.current_risk_level == RiskLevel.HARD_STOP
