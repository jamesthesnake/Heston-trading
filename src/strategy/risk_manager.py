"""
Comprehensive Risk Management with Stop Losses and Position Limits
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
import logging
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)

class RiskLevel(Enum):
    NORMAL = "normal"
    SOFT_STOP = "soft_stop"
    HARD_STOP = "hard_stop"
    EMERGENCY = "emergency"

class RiskAction(Enum):
    ALLOW = "allow"
    BLOCK_ENTRIES = "block_entries"
    CLOSE_ALL = "close_all"
    EMERGENCY_STOP = "emergency_stop"

class RiskManager:
    """
    Comprehensive risk management with multiple layers of protection
    """
    
    def __init__(self, config: dict):
        self.config = config
        self.risk_config = config.get('risk_management', {})
        
        # Account parameters
        self.starting_equity = self.risk_config.get('starting_equity', 1000000)
        self.current_equity = self.starting_equity
        
        # Daily stop losses
        self.soft_stop_pct = self.risk_config.get('soft_stop_pct', 0.005)  # -0.5%
        self.hard_stop_pct = self.risk_config.get('hard_stop_pct', 0.010)  # -1.0%
        
        # Position limits
        self.max_portfolio_vega = self.risk_config.get('max_portfolio_vega', 2500)
        self.max_portfolio_gamma = self.risk_config.get('max_portfolio_gamma', 2000)
        self.max_normalized_delta = self.risk_config.get('max_normalized_delta', 0.05)
        
        # Concentration limits
        self.max_expiry_notional = self.risk_config.get('max_expiry_notional', 250000)
        self.concentration_limits = self._initialize_concentration_limits()
        
        # State tracking
        self.current_risk_level = RiskLevel.NORMAL
        self.daily_pnl = 0.0
        self.positions = []
        self.risk_breaches = []
        self.last_risk_check = None
        
        # Emergency conditions
        self.data_staleness_threshold = self.risk_config.get('data_staleness_sec', 1.5)
        self.model_rmse_multiplier = self.risk_config.get('model_rmse_multiplier', 1.5)
        
    def _initialize_concentration_limits(self) -> Dict:
        """Initialize concentration limits by DTE and moneyness buckets"""
        return {
            ('10-20', 'ITM'): 50000,   # $50k max notional
            ('10-20', 'ATM'): 100000,  # $100k max notional
            ('10-20', 'OTM'): 75000,   # $75k max notional
            ('20-35', 'ITM'): 75000,
            ('20-35', 'ATM'): 150000,
            ('20-35', 'OTM'): 100000,
            ('35-50', 'ITM'): 100000,
            ('35-50', 'ATM'): 200000,
            ('35-50', 'OTM'): 125000
        }
    
    def check_risk_limits(self, positions: List[Dict], current_pnl: float, 
                         market_data: Dict) -> Dict:
        """
        Comprehensive risk limit check
        
        Args:
            positions: Current positions with risk metrics
            current_pnl: Current daily P&L
            market_data: Current market data for staleness check
            
        Returns:
            Risk assessment with actions required
        """
        
        self.positions = positions
        self.daily_pnl = current_pnl
        self.current_equity = self.starting_equity + current_pnl
        
        risk_assessment = {
            'risk_level': RiskLevel.NORMAL,
            'action': RiskAction.ALLOW,
            'breaches': [],
            'warnings': [],
            'metrics': {},
            'timestamp': datetime.now()
        }
        
        # Check daily stop losses
        stop_check = self._check_daily_stops(current_pnl)
        if stop_check['breach']:
            risk_assessment['breaches'].append(stop_check)
            risk_assessment['risk_level'] = stop_check['level']
            risk_assessment['action'] = stop_check['action']
        
        # Check position limits
        position_check = self._check_position_limits(positions)
        if position_check['breach']:
            risk_assessment['breaches'].extend(position_check['breaches'])
            if risk_assessment['risk_level'] == RiskLevel.NORMAL:
                risk_assessment['risk_level'] = RiskLevel.SOFT_STOP
                risk_assessment['action'] = RiskAction.BLOCK_ENTRIES
        
        # Check concentration limits
        concentration_check = self._check_concentration_limits(positions)
        if concentration_check['breach']:
            risk_assessment['warnings'].extend(concentration_check['warnings'])
        
        # Check emergency conditions
        emergency_check = self._check_emergency_conditions(market_data)
        if emergency_check['breach']:
            risk_assessment['breaches'].extend(emergency_check['breaches'])
            risk_assessment['risk_level'] = RiskLevel.EMERGENCY
            risk_assessment['action'] = RiskAction.EMERGENCY_STOP
        
        # Update state
        self.current_risk_level = risk_assessment['risk_level']
        self.last_risk_check = datetime.now()
        
        # Store breaches
        if risk_assessment['breaches']:
            self.risk_breaches.extend(risk_assessment['breaches'])
        
        # Calculate risk metrics
        risk_assessment['metrics'] = self._calculate_risk_metrics(positions)
        
        return risk_assessment
    
    def _check_daily_stops(self, current_pnl: float) -> Dict:
        """Check daily stop loss levels"""
        
        pnl_pct = current_pnl / self.starting_equity
        
        if pnl_pct <= -self.hard_stop_pct:
            return {
                'breach': True,
                'level': RiskLevel.HARD_STOP,
                'action': RiskAction.CLOSE_ALL,
                'type': 'hard_stop',
                'message': f"Hard stop triggered: {pnl_pct:.2%} <= -{self.hard_stop_pct:.2%}",
                'pnl': current_pnl,
                'pnl_pct': pnl_pct
            }
        elif pnl_pct <= -self.soft_stop_pct:
            return {
                'breach': True,
                'level': RiskLevel.SOFT_STOP,
                'action': RiskAction.BLOCK_ENTRIES,
                'type': 'soft_stop',
                'message': f"Soft stop triggered: {pnl_pct:.2%} <= -{self.soft_stop_pct:.2%}",
                'pnl': current_pnl,
                'pnl_pct': pnl_pct
            }
        else:
            return {
                'breach': False,
                'level': RiskLevel.NORMAL,
                'action': RiskAction.ALLOW,
                'pnl': current_pnl,
                'pnl_pct': pnl_pct
            }
    
    def _check_position_limits(self, positions: List[Dict]) -> Dict:
        """Check portfolio position limits"""
        
        breaches = []
        
        # Calculate portfolio Greeks
        total_vega = sum(pos.get('vega_exposure', 0) for pos in positions)
        total_gamma = sum(pos.get('gamma_exposure_1pct', 0) for pos in positions)
        total_delta = sum(pos.get('delta_exposure', 0) for pos in positions)
        
        normalized_delta = abs(total_delta) / self.current_equity
        
        # Check limits
        if abs(total_vega) > self.max_portfolio_vega:
            breaches.append({
                'type': 'vega_limit',
                'message': f"Portfolio vega limit breached: ${abs(total_vega):,.0f} > ${self.max_portfolio_vega:,.0f}",
                'current': abs(total_vega),
                'limit': self.max_portfolio_vega
            })
        
        if abs(total_gamma) > self.max_portfolio_gamma:
            breaches.append({
                'type': 'gamma_limit',
                'message': f"Portfolio gamma limit breached: ${abs(total_gamma):,.0f} > ${self.max_portfolio_gamma:,.0f}",
                'current': abs(total_gamma),
                'limit': self.max_portfolio_gamma
            })
        
        if normalized_delta > self.max_normalized_delta:
            breaches.append({
                'type': 'delta_limit',
                'message': f"Normalized delta limit breached: {normalized_delta:.4f} > {self.max_normalized_delta:.4f}",
                'current': normalized_delta,
                'limit': self.max_normalized_delta
            })
        
        return {
            'breach': len(breaches) > 0,
            'breaches': breaches,
            'metrics': {
                'total_vega': total_vega,
                'total_gamma': total_gamma,
                'total_delta': total_delta,
                'normalized_delta': normalized_delta
            }
        }
    
    def _check_concentration_limits(self, positions: List[Dict]) -> Dict:
        """Check concentration limits by expiry and buckets"""
        
        warnings = []
        
        # Group by expiry
        expiry_exposure = {}
        bucket_exposure = {}
        
        for pos in positions:
            expiry = pos.get('expiry')
            dte = pos.get('dte', 0)
            moneyness = pos.get('moneyness', 0)
            notional = pos.get('notional', 0)
            
            # Expiry concentration
            if expiry:
                expiry_exposure[expiry] = expiry_exposure.get(expiry, 0) + notional
            
            # Bucket concentration
            dte_bucket = self._get_dte_bucket(dte)
            moneyness_bucket = self._get_moneyness_bucket(moneyness)
            bucket_key = (dte_bucket, moneyness_bucket)
            
            if bucket_key in self.concentration_limits:
                bucket_exposure[bucket_key] = bucket_exposure.get(bucket_key, 0) + notional
        
        # Check expiry limits
        for expiry, exposure in expiry_exposure.items():
            if exposure > self.max_expiry_notional:
                warnings.append({
                    'type': 'expiry_concentration',
                    'message': f"Expiry concentration warning: {expiry} has ${exposure:,.0f} > ${self.max_expiry_notional:,.0f}",
                    'expiry': expiry,
                    'exposure': exposure,
                    'limit': self.max_expiry_notional
                })
        
        # Check bucket limits
        for bucket_key, exposure in bucket_exposure.items():
            limit = self.concentration_limits[bucket_key]
            if exposure > limit:
                warnings.append({
                    'type': 'bucket_concentration',
                    'message': f"Bucket concentration warning: {bucket_key} has ${exposure:,.0f} > ${limit:,.0f}",
                    'bucket': bucket_key,
                    'exposure': exposure,
                    'limit': limit
                })
        
        return {
            'breach': False,  # Concentration limits are warnings, not hard stops
            'warnings': warnings,
            'expiry_exposure': expiry_exposure,
            'bucket_exposure': bucket_exposure
        }
    
    def _check_emergency_conditions(self, market_data: Dict) -> Dict:
        """Check for emergency stop conditions"""
        
        breaches = []
        
        # Check data staleness
        if 'timestamp' in market_data:
            data_age = (datetime.now() - market_data['timestamp']).total_seconds()
            if data_age > self.data_staleness_threshold:
                breaches.append({
                    'type': 'data_staleness',
                    'message': f"Data staleness: {data_age:.1f}s > {self.data_staleness_threshold}s",
                    'data_age': data_age,
                    'threshold': self.data_staleness_threshold
                })
        
        # Check model health
        if 'model_rmse' in market_data and 'baseline_rmse' in market_data:
            current_rmse = market_data['model_rmse']
            baseline_rmse = market_data['baseline_rmse']
            rmse_ratio = current_rmse / baseline_rmse if baseline_rmse > 0 else float('inf')
            
            if rmse_ratio > self.model_rmse_multiplier:
                breaches.append({
                    'type': 'model_health',
                    'message': f"Model RMSE degraded: {rmse_ratio:.2f}x > {self.model_rmse_multiplier}x baseline",
                    'current_rmse': current_rmse,
                    'baseline_rmse': baseline_rmse,
                    'ratio': rmse_ratio
                })
        
        return {
            'breach': len(breaches) > 0,
            'breaches': breaches
        }
    
    def _get_dte_bucket(self, dte: int) -> str:
        """Get DTE bucket for concentration limits"""
        if dte <= 20:
            return '10-20'
        elif dte <= 35:
            return '20-35'
        else:
            return '35-50'
    
    def _get_moneyness_bucket(self, moneyness: float) -> str:
        """Get moneyness bucket for concentration limits"""
        if moneyness < -0.02:
            return 'ITM'  # In-the-money (for calls, strike < spot)
        elif moneyness > 0.02:
            return 'OTM'  # Out-of-the-money
        else:
            return 'ATM'  # At-the-money
    
    def _calculate_risk_metrics(self, positions: List[Dict]) -> Dict:
        """Calculate comprehensive risk metrics"""
        
        if not positions:
            return {
                'position_count': 0,
                'total_notional': 0,
                'total_vega': 0,
                'total_gamma': 0,
                'total_delta': 0,
                'normalized_delta': 0,
                'max_single_position': 0,
                'avg_position_size': 0
            }
        
        notionals = [pos.get('notional', 0) for pos in positions]
        vegas = [pos.get('vega_exposure', 0) for pos in positions]
        gammas = [pos.get('gamma_exposure_1pct', 0) for pos in positions]
        deltas = [pos.get('delta_exposure', 0) for pos in positions]
        
        return {
            'position_count': len(positions),
            'total_notional': sum(notionals),
            'total_vega': sum(vegas),
            'total_gamma': sum(gammas),
            'total_delta': sum(deltas),
            'normalized_delta': abs(sum(deltas)) / self.current_equity,
            'max_single_position': max(notionals) if notionals else 0,
            'avg_position_size': np.mean(notionals) if notionals else 0,
            'vega_utilization': abs(sum(vegas)) / self.max_portfolio_vega,
            'gamma_utilization': abs(sum(gammas)) / self.max_portfolio_gamma
        }
    
    def should_allow_new_position(self, new_position: Dict) -> Dict:
        """
        Check if new position should be allowed
        
        Args:
            new_position: Proposed new position with risk metrics
            
        Returns:
            Decision with reasoning
        """
        
        # Check current risk level
        if self.current_risk_level == RiskLevel.HARD_STOP:
            return {
                'allowed': False,
                'reason': 'Hard stop active - no new positions allowed'
            }
        
        if self.current_risk_level == RiskLevel.SOFT_STOP:
            return {
                'allowed': False,
                'reason': 'Soft stop active - blocking new entries'
            }
        
        if self.current_risk_level == RiskLevel.EMERGENCY:
            return {
                'allowed': False,
                'reason': 'Emergency stop active'
            }
        
        # Check if new position would breach limits
        test_positions = self.positions + [new_position]
        position_check = self._check_position_limits(test_positions)
        
        if position_check['breach']:
            return {
                'allowed': False,
                'reason': f"Would breach position limits: {position_check['breaches'][0]['message']}"
            }
        
        return {
            'allowed': True,
            'reason': 'Position within risk limits'
        }
    
    def get_exit_signals(self, positions: List[Dict]) -> List[Dict]:
        """
        Generate exit signals based on risk conditions
        
        Args:
            positions: Current positions
            
        Returns:
            List of positions that should be closed
        """
        
        exits = []
        
        # Hard stop - close all positions
        if self.current_risk_level == RiskLevel.HARD_STOP:
            for pos in positions:
                exits.append({
                    'position': pos,
                    'reason': 'hard_stop',
                    'urgency': 'immediate'
                })
        
        # Emergency stop - close all positions immediately
        elif self.current_risk_level == RiskLevel.EMERGENCY:
            for pos in positions:
                exits.append({
                    'position': pos,
                    'reason': 'emergency_stop',
                    'urgency': 'emergency'
                })
        
        return exits
    
    def update_daily_pnl(self, pnl: float):
        """Update current daily P&L"""
        self.daily_pnl = pnl
        self.current_equity = self.starting_equity + pnl
    
    def reset_daily_limits(self):
        """Reset daily limits at start of new trading day"""
        self.daily_pnl = 0.0
        self.current_equity = self.starting_equity
        self.current_risk_level = RiskLevel.NORMAL
        self.risk_breaches = []
        logger.info("Daily risk limits reset")
    
    def get_risk_summary(self) -> Dict:
        """Get comprehensive risk summary"""
        
        return {
            'risk_level': self.current_risk_level.value,
            'daily_pnl': self.daily_pnl,
            'daily_pnl_pct': self.daily_pnl / self.starting_equity,
            'current_equity': self.current_equity,
            'soft_stop_threshold': -self.soft_stop_pct * self.starting_equity,
            'hard_stop_threshold': -self.hard_stop_pct * self.starting_equity,
            'position_count': len(self.positions),
            'breach_count_today': len(self.risk_breaches),
            'last_risk_check': self.last_risk_check
        }
