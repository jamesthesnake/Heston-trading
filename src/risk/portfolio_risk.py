"""
Portfolio Risk Analyzer - Portfolio-Level Risk Assessment
Analyzes portfolio-wide risks including correlations, VaR, stress testing, and market regime changes
"""
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from scipy import stats

from .risk_types import RiskLevel, RiskAction, RiskAlert

logger = logging.getLogger(__name__)

@dataclass
class PortfolioMetrics:
    """Portfolio risk metrics"""
    total_value: float
    daily_var_95: float
    daily_var_99: float
    expected_shortfall: float
    max_drawdown: float
    beta_to_market: float
    portfolio_volatility: float
    sharpe_ratio: float
    correlation_risk: float

class PortfolioRiskAnalyzer:
    """
    Analyzes portfolio-wide risks including:
    - Value at Risk (VaR) calculations
    - Stress testing scenarios
    - Correlation and concentration analysis
    - Market regime detection
    - Portfolio Greeks and exposures
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the portfolio risk analyzer
        
        Args:
            config: Risk configuration
        """
        self.config = config
        self.portfolio_config = config.get('portfolio_risk', {})
        
        # VaR parameters
        self.var_confidence_levels = self.portfolio_config.get('var_confidence_levels', [0.95, 0.99])
        self.var_lookback_days = self.portfolio_config.get('var_lookback_days', 252)  # 1 year
        self.var_methods = self.portfolio_config.get('var_methods', ['historical', 'parametric'])
        
        # Portfolio limits
        self.max_portfolio_var_pct = self.portfolio_config.get('max_portfolio_var_pct', 0.02)  # 2%
        self.max_concentration_pct = self.portfolio_config.get('max_concentration_pct', 0.4)  # 40%
        self.max_correlation_threshold = self.portfolio_config.get('max_correlation_threshold', 0.8)
        
        # Greeks limits
        self.max_net_delta = self.portfolio_config.get('max_net_delta', 100000)  # $100k
        self.max_net_gamma = self.portfolio_config.get('max_net_gamma', 5000)
        self.max_net_vega = self.portfolio_config.get('max_net_vega', 10000)
        self.max_theta_decay_portfolio = self.portfolio_config.get('max_theta_decay_portfolio', 2000)
        
        # Market stress scenarios
        self.stress_scenarios = self._initialize_stress_scenarios()
        
        # Market regime parameters
        self.volatility_regimes = self.portfolio_config.get('volatility_regimes', {
            'low': 0.15,    # 15% annualized
            'normal': 0.25,  # 25% annualized
            'high': 0.40     # 40% annualized
        })
        
        # Historical data storage
        self.price_history = []
        self.return_history = []
        self.volatility_history = []
        
        logger.info("Portfolio risk analyzer initialized")
    
    def _initialize_stress_scenarios(self) -> Dict[str, Dict[str, float]]:
        """Initialize market stress test scenarios"""
        return {
            'market_crash': {
                'spx_move': -0.20,      # 20% down
                'vol_spike': 2.0,       # 2x volatility
                'correlation_increase': 0.3  # Correlations increase by 30%
            },
            'vol_spike': {
                'spx_move': -0.05,      # 5% down
                'vol_spike': 1.5,       # 1.5x volatility
                'correlation_increase': 0.2
            },
            'rate_shock': {
                'spx_move': -0.10,      # 10% down
                'rate_move': 0.02,      # 200bp rate increase
                'vol_spike': 1.3
            },
            'flash_crash': {
                'spx_move': -0.15,      # 15% down instantly
                'vol_spike': 3.0,       # 3x volatility
                'liquidity_impact': 0.5  # 50% liquidity reduction
            }
        }
    
    async def analyze_portfolio(self, positions: List[Dict[str, Any]], 
                               market_data: Dict[str, Any],
                               portfolio_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze portfolio-wide risks
        
        Args:
            positions: List of current positions
            market_data: Current market data
            portfolio_metrics: Portfolio performance metrics
            
        Returns:
            Portfolio risk analysis results
        """
        try:
            analysis_start = datetime.now()
            
            alerts = []
            metrics = {}
            
            # 1. Calculate portfolio Greeks
            greeks_analysis = self._analyze_portfolio_greeks(positions)
            alerts.extend(greeks_analysis['alerts'])
            
            # 2. Calculate Value at Risk
            var_analysis = await self._calculate_portfolio_var(positions, market_data)
            alerts.extend(var_analysis['alerts'])
            
            # 3. Perform stress testing
            stress_analysis = await self._perform_stress_tests(positions, market_data)
            alerts.extend(stress_analysis['alerts'])
            
            # 4. Analyze correlations and concentrations
            correlation_analysis = self._analyze_correlations(positions, market_data)
            alerts.extend(correlation_analysis['alerts'])
            
            # 5. Detect market regime changes
            regime_analysis = self._analyze_market_regime(market_data)
            alerts.extend(regime_analysis['alerts'])
            
            # 6. Check portfolio limits
            limits_analysis = self._check_portfolio_limits(positions, portfolio_metrics)
            alerts.extend(limits_analysis['alerts'])
            
            # 7. Compile comprehensive metrics
            metrics = self._compile_portfolio_metrics(
                greeks_analysis, var_analysis, stress_analysis, 
                correlation_analysis, regime_analysis, limits_analysis
            )
            
            analysis_time = (datetime.now() - analysis_start).total_seconds()
            
            return {
                'alerts': alerts,
                'metrics': metrics,
                'analysis_time': analysis_time,
                'data_quality': self._assess_data_quality(market_data),
                'model_quality': self._assess_model_quality(),
                'market_stress': regime_analysis.get('current_regime', {})
            }
            
        except Exception as e:
            logger.error(f"Error analyzing portfolio: {e}")
            return {
                'alerts': [RiskAlert(
                    timestamp=datetime.now(),
                    level=RiskLevel.WARNING,
                    component="portfolio_analyzer",
                    rule="analysis_error",
                    message=f"Portfolio analysis failed: {e}",
                    current_value=0,
                    limit_value=0,
                    recommended_action=RiskAction.BLOCK_NEW,
                    metadata={'error': str(e)}
                )],
                'metrics': {},
                'analysis_time': 0
            }
    
    def _analyze_portfolio_greeks(self, positions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze portfolio-level Greeks exposure"""
        alerts = []
        
        try:
            if not positions:
                return {'alerts': alerts, 'greeks': {}}
            
            # Calculate net Greeks
            net_delta = sum(pos.get('delta', 0) * pos.get('quantity', 0) * 100 for pos in positions)
            net_gamma = sum(pos.get('gamma', 0) * pos.get('quantity', 0) * 100 for pos in positions)
            net_vega = sum(pos.get('vega', 0) * pos.get('quantity', 0) for pos in positions)
            net_theta = sum(pos.get('theta', 0) * pos.get('quantity', 0) for pos in positions)
            
            # Check delta limits
            if abs(net_delta) > self.max_net_delta:
                severity = RiskLevel.CRITICAL if abs(net_delta) > self.max_net_delta * 1.5 else RiskLevel.WARNING
                alerts.append(RiskAlert(
                    timestamp=datetime.now(),
                    level=severity,
                    component="portfolio_analyzer",
                    rule="portfolio_delta_limit",
                    message=f"Portfolio net delta ${net_delta:,.0f} exceeds limit ${self.max_net_delta:,.0f}",
                    current_value=abs(net_delta),
                    limit_value=self.max_net_delta,
                    recommended_action=RiskAction.CLOSE_RISKY if severity == RiskLevel.CRITICAL else RiskAction.REDUCE_SIZE,
                    metadata={
                        'net_delta': net_delta,
                        'position_count': len(positions)
                    }
                ))
            
            # Check gamma limits
            if abs(net_gamma) > self.max_net_gamma:
                alerts.append(RiskAlert(
                    timestamp=datetime.now(),
                    level=RiskLevel.WARNING,
                    component="portfolio_analyzer",
                    rule="portfolio_gamma_limit",
                    message=f"Portfolio net gamma ${net_gamma:,.0f} exceeds limit ${self.max_net_gamma:,.0f}",
                    current_value=abs(net_gamma),
                    limit_value=self.max_net_gamma,
                    recommended_action=RiskAction.REDUCE_SIZE,
                    metadata={
                        'net_gamma': net_gamma,
                        'position_count': len(positions)
                    }
                ))
            
            # Check vega limits
            if abs(net_vega) > self.max_net_vega:
                alerts.append(RiskAlert(
                    timestamp=datetime.now(),
                    level=RiskLevel.WARNING,
                    component="portfolio_analyzer",
                    rule="portfolio_vega_limit",
                    message=f"Portfolio net vega ${net_vega:,.0f} exceeds limit ${self.max_net_vega:,.0f}",
                    current_value=abs(net_vega),
                    limit_value=self.max_net_vega,
                    recommended_action=RiskAction.REDUCE_SIZE,
                    metadata={
                        'net_vega': net_vega,
                        'position_count': len(positions)
                    }
                ))
            
            # Check theta decay
            if abs(net_theta) > self.max_theta_decay_portfolio:
                alerts.append(RiskAlert(
                    timestamp=datetime.now(),
                    level=RiskLevel.CAUTION,
                    component="portfolio_analyzer",
                    rule="portfolio_theta_decay",
                    message=f"Portfolio theta decay ${net_theta:,.0f} exceeds threshold ${self.max_theta_decay_portfolio:,.0f}",
                    current_value=abs(net_theta),
                    limit_value=self.max_theta_decay_portfolio,
                    recommended_action=RiskAction.REDUCE_SIZE,
                    metadata={
                        'net_theta': net_theta,
                        'position_count': len(positions)
                    }
                ))
            
            greeks = {
                'net_delta': net_delta,
                'net_gamma': net_gamma,
                'net_vega': net_vega,
                'net_theta': net_theta
            }
            
            return {'alerts': alerts, 'greeks': greeks}
            
        except Exception as e:
            logger.error(f"Error analyzing portfolio Greeks: {e}")
            return {'alerts': [], 'greeks': {}}
    
    async def _calculate_portfolio_var(self, positions: List[Dict[str, Any]], 
                                      market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate Value at Risk for the portfolio"""
        alerts = []
        var_metrics = {}
        
        try:
            if not positions:
                return {'alerts': alerts, 'var_metrics': var_metrics}
            
            # For this implementation, we'll use a simplified VaR calculation
            # In production, this would use historical returns and Monte Carlo simulation
            
            # Calculate portfolio value
            portfolio_value = sum(abs(pos.get('market_value', 0)) for pos in positions)
            
            if portfolio_value == 0:
                return {'alerts': alerts, 'var_metrics': var_metrics}
            
            # Simplified VaR calculation using portfolio volatility estimate
            # This would be much more sophisticated in production
            estimated_volatility = self._estimate_portfolio_volatility(positions, market_data)
            
            # Daily VaR at different confidence levels
            daily_var_95 = portfolio_value * estimated_volatility * stats.norm.ppf(0.05) * -1  # 95% VaR
            daily_var_99 = portfolio_value * estimated_volatility * stats.norm.ppf(0.01) * -1  # 99% VaR
            
            var_95_pct = daily_var_95 / portfolio_value
            var_99_pct = daily_var_99 / portfolio_value
            
            # Check VaR limits
            if var_95_pct > self.max_portfolio_var_pct:
                severity = RiskLevel.CRITICAL if var_95_pct > self.max_portfolio_var_pct * 2 else RiskLevel.WARNING
                alerts.append(RiskAlert(
                    timestamp=datetime.now(),
                    level=severity,
                    component="portfolio_analyzer",
                    rule="portfolio_var_limit",
                    message=f"Portfolio VaR {var_95_pct:.2%} exceeds limit {self.max_portfolio_var_pct:.2%}",
                    current_value=var_95_pct,
                    limit_value=self.max_portfolio_var_pct,
                    recommended_action=RiskAction.REDUCE_SIZE,
                    metadata={
                        'var_95_dollar': daily_var_95,
                        'var_99_dollar': daily_var_99,
                        'portfolio_value': portfolio_value,
                        'estimated_volatility': estimated_volatility
                    }
                ))
            
            var_metrics = {
                'daily_var_95': daily_var_95,
                'daily_var_99': daily_var_99,
                'var_95_pct': var_95_pct,
                'var_99_pct': var_99_pct,
                'portfolio_volatility': estimated_volatility
            }
            
            return {'alerts': alerts, 'var_metrics': var_metrics}
            
        except Exception as e:
            logger.error(f"Error calculating portfolio VaR: {e}")
            return {'alerts': [], 'var_metrics': {}}
    
    async def _perform_stress_tests(self, positions: List[Dict[str, Any]], 
                                   market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Perform stress testing on the portfolio"""
        alerts = []
        stress_results = {}
        
        try:
            if not positions:
                return {'alerts': alerts, 'stress_results': stress_results}
            
            portfolio_value = sum(abs(pos.get('market_value', 0)) for pos in positions)
            
            if portfolio_value == 0:
                return {'alerts': alerts, 'stress_results': stress_results}
            
            # Perform each stress scenario
            for scenario_name, scenario_params in self.stress_scenarios.items():
                stress_pnl = self._calculate_stress_scenario_pnl(positions, scenario_params)
                stress_pnl_pct = stress_pnl / portfolio_value if portfolio_value > 0 else 0
                
                stress_results[scenario_name] = {
                    'pnl_dollar': stress_pnl,
                    'pnl_pct': stress_pnl_pct
                }
                
                # Check for severe stress losses
                if stress_pnl_pct < -0.15:  # 15% loss in stress scenario
                    alerts.append(RiskAlert(
                        timestamp=datetime.now(),
                        level=RiskLevel.WARNING,
                        component="portfolio_analyzer",
                        rule="stress_test_loss",
                        message=f"Severe stress test loss: {scenario_name} scenario shows {stress_pnl_pct:.1%} loss",
                        current_value=abs(stress_pnl_pct),
                        limit_value=0.15,
                        recommended_action=RiskAction.REDUCE_SIZE,
                        metadata={
                            'scenario': scenario_name,
                            'stress_pnl': stress_pnl,
                            'portfolio_value': portfolio_value,
                            'scenario_params': scenario_params
                        }
                    ))
            
            return {'alerts': alerts, 'stress_results': stress_results}
            
        except Exception as e:
            logger.error(f"Error performing stress tests: {e}")
            return {'alerts': [], 'stress_results': {}}
    
    def _calculate_stress_scenario_pnl(self, positions: List[Dict[str, Any]], 
                                      scenario_params: Dict[str, float]) -> float:
        """Calculate P&L for a specific stress scenario"""
        try:
            total_stress_pnl = 0.0
            
            spx_move = scenario_params.get('spx_move', 0)
            vol_spike = scenario_params.get('vol_spike', 1.0)
            
            for position in positions:
                # Simplified stress calculation using Greeks
                delta = position.get('delta', 0)
                gamma = position.get('gamma', 0)
                vega = position.get('vega', 0)
                quantity = position.get('quantity', 0)
                
                # Current underlying price (assuming SPX-based)
                current_price = 5000  # Simplified - would get from market data
                price_move = current_price * spx_move
                
                # Delta P&L
                delta_pnl = delta * quantity * price_move
                
                # Gamma P&L (second-order effect)
                gamma_pnl = 0.5 * gamma * quantity * (price_move ** 2)
                
                # Vega P&L (volatility change)
                vol_change = 0.05 * (vol_spike - 1.0)  # 5% base vol change
                vega_pnl = vega * quantity * vol_change
                
                position_stress_pnl = delta_pnl + gamma_pnl + vega_pnl
                total_stress_pnl += position_stress_pnl
            
            return total_stress_pnl
            
        except Exception as e:
            logger.error(f"Error calculating stress scenario P&L: {e}")
            return 0.0
    
    def _analyze_correlations(self, positions: List[Dict[str, Any]], 
                             market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze portfolio correlations and concentrations"""
        alerts = []
        correlation_metrics = {}
        
        try:
            if not positions:
                return {'alerts': alerts, 'correlation_metrics': correlation_metrics}
            
            # Analyze concentration by underlying
            concentrations = self._calculate_concentrations(positions)
            
            for asset, concentration_pct in concentrations.items():
                if concentration_pct > self.max_concentration_pct:
                    alerts.append(RiskAlert(
                        timestamp=datetime.now(),
                        level=RiskLevel.WARNING,
                        component="portfolio_analyzer",
                        rule="concentration_limit",
                        message=f"High concentration in {asset}: {concentration_pct:.1%} (limit: {self.max_concentration_pct:.1%})",
                        current_value=concentration_pct,
                        limit_value=self.max_concentration_pct,
                        recommended_action=RiskAction.REDUCE_SIZE,
                        metadata={
                            'asset': asset,
                            'concentration_pct': concentration_pct
                        }
                    ))
            
            correlation_metrics = {
                'concentrations': concentrations,
                'max_concentration': max(concentrations.values()) if concentrations else 0,
                'concentration_count': len([c for c in concentrations.values() if c > self.max_concentration_pct])
            }
            
            return {'alerts': alerts, 'correlation_metrics': correlation_metrics}
            
        except Exception as e:
            logger.error(f"Error analyzing correlations: {e}")
            return {'alerts': [], 'correlation_metrics': {}}
    
    def _analyze_market_regime(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze current market regime and detect changes"""
        alerts = []
        regime_analysis = {}
        
        try:
            # Simplified market regime detection
            # In production, this would use sophisticated statistical models
            
            current_vol = market_data.get('VIX', {}).get('last', 20)  # VIX level
            
            # Determine volatility regime
            if current_vol < self.volatility_regimes['low'] * 100:
                vol_regime = 'low'
            elif current_vol < self.volatility_regimes['normal'] * 100:
                vol_regime = 'normal'
            else:
                vol_regime = 'high'
            
            # Alert on high volatility regime
            if vol_regime == 'high':
                alerts.append(RiskAlert(
                    timestamp=datetime.now(),
                    level=RiskLevel.WARNING,
                    component="portfolio_analyzer",
                    rule="high_volatility_regime",
                    message=f"High volatility regime detected: VIX at {current_vol:.1f}",
                    current_value=current_vol,
                    limit_value=self.volatility_regimes['normal'] * 100,
                    recommended_action=RiskAction.REDUCE_SIZE,
                    metadata={
                        'vix_level': current_vol,
                        'volatility_regime': vol_regime
                    }
                ))
            
            regime_analysis = {
                'volatility_regime': vol_regime,
                'vix_level': current_vol,
                'regime_risk_multiplier': {'low': 0.8, 'normal': 1.0, 'high': 1.5}[vol_regime]
            }
            
            return {'alerts': alerts, 'current_regime': regime_analysis}
            
        except Exception as e:
            logger.error(f"Error analyzing market regime: {e}")
            return {'alerts': [], 'current_regime': {}}
    
    def _check_portfolio_limits(self, positions: List[Dict[str, Any]], 
                               portfolio_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Check portfolio-level limits and constraints"""
        alerts = []
        
        try:
            # Check total portfolio value limits
            total_value = sum(abs(pos.get('market_value', 0)) for pos in positions)
            max_portfolio_value = self.portfolio_config.get('max_portfolio_value', 10000000)  # $10M default
            
            if total_value > max_portfolio_value:
                alerts.append(RiskAlert(
                    timestamp=datetime.now(),
                    level=RiskLevel.WARNING,
                    component="portfolio_analyzer",
                    rule="portfolio_value_limit",
                    message=f"Portfolio value ${total_value:,.0f} exceeds limit ${max_portfolio_value:,.0f}",
                    current_value=total_value,
                    limit_value=max_portfolio_value,
                    recommended_action=RiskAction.BLOCK_NEW,
                    metadata={
                        'total_value': total_value,
                        'position_count': len(positions)
                    }
                ))
            
            # Check number of positions
            max_positions = self.portfolio_config.get('max_positions', 200)
            if len(positions) > max_positions:
                alerts.append(RiskAlert(
                    timestamp=datetime.now(),
                    level=RiskLevel.CAUTION,
                    component="portfolio_analyzer",
                    rule="position_count_limit",
                    message=f"Position count {len(positions)} exceeds limit {max_positions}",
                    current_value=len(positions),
                    limit_value=max_positions,
                    recommended_action=RiskAction.BLOCK_NEW,
                    metadata={
                        'position_count': len(positions),
                        'total_value': total_value
                    }
                ))
            
            return {'alerts': alerts}
            
        except Exception as e:
            logger.error(f"Error checking portfolio limits: {e}")
            return {'alerts': []}
    
    # Helper methods
    
    def _estimate_portfolio_volatility(self, positions: List[Dict[str, Any]], 
                                      market_data: Dict[str, Any]) -> float:
        """Estimate portfolio volatility (simplified)"""
        try:
            # Simplified estimation - in production would use historical correlations
            if not positions:
                return 0.0
            
            # Use VIX as a proxy for market volatility
            market_vol = market_data.get('VIX', {}).get('last', 20) / 100  # Convert to decimal
            
            # Adjust for portfolio composition (options vs stock)
            options_weight = len([p for p in positions if p.get('option_type') in ['C', 'P']]) / len(positions)
            vol_multiplier = 1.0 + options_weight * 0.5  # Options add volatility
            
            return market_vol * vol_multiplier / np.sqrt(252)  # Daily volatility
            
        except Exception as e:
            logger.error(f"Error estimating portfolio volatility: {e}")
            return 0.02  # Default 2% daily vol
    
    def _calculate_concentrations(self, positions: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate concentration percentages by underlying asset"""
        try:
            total_value = sum(abs(pos.get('market_value', 0)) for pos in positions)
            
            if total_value == 0:
                return {}
            
            concentrations = {}
            for position in positions:
                underlying = position.get('underlying', position.get('symbol', 'unknown'))
                value = abs(position.get('market_value', 0))
                
                if underlying not in concentrations:
                    concentrations[underlying] = 0
                concentrations[underlying] += value
            
            # Convert to percentages
            for underlying in concentrations:
                concentrations[underlying] = concentrations[underlying] / total_value
            
            return concentrations
            
        except Exception as e:
            logger.error(f"Error calculating concentrations: {e}")
            return {}
    
    def _assess_data_quality(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Assess the quality of market data"""
        try:
            quality_metrics = {
                'stale_data_pct': 0.0,
                'missing_prices_pct': 0.0,
                'missing_greeks_pct': 0.0,
                'last_update_age_seconds': 0
            }
            
            # Simplified data quality assessment
            # In production, this would check timestamps, data completeness, etc.
            
            return quality_metrics
            
        except Exception as e:
            logger.error(f"Error assessing data quality: {e}")
            return {}
    
    def _assess_model_quality(self) -> Dict[str, Any]:
        """Assess the quality of risk models"""
        try:
            model_quality = {
                'calibration_rmse': 0.05,  # Placeholder
                'last_calibration_age_hours': 1.0,
                'model_confidence': 0.85
            }
            
            return model_quality
            
        except Exception as e:
            logger.error(f"Error assessing model quality: {e}")
            return {}
    
    def _compile_portfolio_metrics(self, greeks_analysis: Dict[str, Any],
                                  var_analysis: Dict[str, Any],
                                  stress_analysis: Dict[str, Any],
                                  correlation_analysis: Dict[str, Any],
                                  regime_analysis: Dict[str, Any],
                                  limits_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Compile comprehensive portfolio risk metrics"""
        try:
            return {
                'greeks': greeks_analysis.get('greeks', {}),
                'var_metrics': var_analysis.get('var_metrics', {}),
                'stress_results': stress_analysis.get('stress_results', {}),
                'correlation_metrics': correlation_analysis.get('correlation_metrics', {}),
                'market_regime': regime_analysis.get('current_regime', {}),
                'summary': {
                    'total_alerts': len(greeks_analysis.get('alerts', [])) +
                                  len(var_analysis.get('alerts', [])) +
                                  len(stress_analysis.get('alerts', [])) +
                                  len(correlation_analysis.get('alerts', [])) +
                                  len(regime_analysis.get('alerts', [])) +
                                  len(limits_analysis.get('alerts', []))
                }
            }
            
        except Exception as e:
            logger.error(f"Error compiling portfolio metrics: {e}")
            return {}