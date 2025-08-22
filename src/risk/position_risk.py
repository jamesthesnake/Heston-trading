"""
Position Risk Analyzer - Individual Position Risk Assessment
Analyzes risk at the individual position level including Greeks, concentrations, and stop losses
"""
import logging
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from .risk_types import RiskLevel, RiskAction, RiskAlert

logger = logging.getLogger(__name__)

@dataclass
class PositionRisk:
    """Individual position risk metrics"""
    position_id: str
    symbol: str
    risk_score: float  # 0.0 to 1.0
    delta_risk: float
    gamma_risk: float
    theta_decay: float
    vega_risk: float
    liquidity_risk: float
    concentration_risk: float
    time_decay_risk: float

class PositionRiskAnalyzer:
    """
    Analyzes risk at the individual position level
    Focuses on position-specific risks like Greeks exposure, concentration, and stop losses
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the position risk analyzer
        
        Args:
            config: Risk configuration
        """
        self.config = config
        self.position_config = config.get('position_risk', {})
        
        # Position risk thresholds
        self.max_position_delta = self.position_config.get('max_position_delta', 10000)
        self.max_position_gamma = self.position_config.get('max_position_gamma', 500)
        self.max_position_vega = self.position_config.get('max_position_vega', 1000)
        self.max_theta_decay_daily = self.position_config.get('max_theta_decay_daily', 500)
        
        # Concentration limits
        self.max_single_position_pct = self.position_config.get('max_single_position_pct', 0.1)  # 10%
        self.max_expiry_concentration = self.position_config.get('max_expiry_concentration', 0.3)  # 30%
        self.max_strike_concentration = self.position_config.get('max_strike_concentration', 0.25)  # 25%
        
        # Stop loss parameters
        self.position_stop_loss_pct = self.position_config.get('position_stop_loss_pct', 0.5)  # 50%
        self.trailing_stop_enabled = self.position_config.get('trailing_stop_enabled', True)
        self.trailing_stop_distance = self.position_config.get('trailing_stop_distance', 0.3)  # 30%
        
        # Time decay thresholds
        self.low_dte_threshold = self.position_config.get('low_dte_threshold', 7)  # days
        self.critical_dte_threshold = self.position_config.get('critical_dte_threshold', 3)  # days
        
        # Liquidity parameters
        self.min_daily_volume = self.position_config.get('min_daily_volume', 50)
        self.min_open_interest = self.position_config.get('min_open_interest', 100)
        
        logger.info("Position risk analyzer initialized")
    
    async def analyze_positions(self, positions: List[Dict[str, Any]], 
                               market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze risk for all positions
        
        Args:
            positions: List of current positions
            market_data: Current market data
            
        Returns:
            Position risk analysis results
        """
        try:
            analysis_start = datetime.now()
            
            alerts = []
            position_risks = []
            metrics = {}
            
            # Analyze each position individually
            for position in positions:
                position_analysis = await self._analyze_single_position(position, market_data)
                position_risks.append(position_analysis['risk'])
                alerts.extend(position_analysis['alerts'])
            
            # Portfolio-level position analysis
            portfolio_analysis = self._analyze_position_portfolio(positions, position_risks)
            alerts.extend(portfolio_analysis['alerts'])
            
            # Compile metrics
            metrics = self._compile_position_metrics(position_risks, portfolio_analysis)
            
            analysis_time = (datetime.now() - analysis_start).total_seconds()
            
            return {
                'alerts': alerts,
                'position_risks': position_risks,
                'metrics': metrics,
                'analysis_time': analysis_time
            }
            
        except Exception as e:
            logger.error(f"Error analyzing positions: {e}")
            return {
                'alerts': [RiskAlert(
                    timestamp=datetime.now(),
                    level=RiskLevel.WARNING,
                    component="position_analyzer",
                    rule="analysis_error",
                    message=f"Position analysis failed: {e}",
                    current_value=0,
                    limit_value=0,
                    recommended_action=RiskAction.BLOCK_NEW,
                    metadata={'error': str(e)}
                )],
                'position_risks': [],
                'metrics': {},
                'analysis_time': 0
            }
    
    async def _analyze_single_position(self, position: Dict[str, Any], 
                                      market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze risk for a single position"""
        try:
            position_id = position.get('position_id', 'unknown')
            symbol = position.get('symbol', 'unknown')
            
            alerts = []
            
            # 1. Greeks risk analysis
            greeks_alerts = self._analyze_greeks_risk(position)
            alerts.extend(greeks_alerts)
            
            # 2. Stop loss analysis
            stop_loss_alerts = self._analyze_stop_losses(position)
            alerts.extend(stop_loss_alerts)
            
            # 3. Time decay analysis
            time_decay_alerts = self._analyze_time_decay(position)
            alerts.extend(time_decay_alerts)
            
            # 4. Liquidity analysis
            liquidity_alerts = self._analyze_position_liquidity(position, market_data)
            alerts.extend(liquidity_alerts)
            
            # 5. Calculate overall position risk score
            risk_score = self._calculate_position_risk_score(position, alerts)
            
            # 6. Create position risk object
            position_risk = PositionRisk(
                position_id=position_id,
                symbol=symbol,
                risk_score=risk_score,
                delta_risk=self._calculate_delta_risk(position),
                gamma_risk=self._calculate_gamma_risk(position),
                theta_decay=position.get('theta', 0) * position.get('quantity', 0),
                vega_risk=self._calculate_vega_risk(position),
                liquidity_risk=self._calculate_liquidity_risk(position, market_data),
                concentration_risk=0.0,  # Calculated at portfolio level
                time_decay_risk=self._calculate_time_decay_risk(position)
            )
            
            return {
                'risk': position_risk,
                'alerts': alerts
            }
            
        except Exception as e:
            logger.error(f"Error analyzing position {position.get('position_id', 'unknown')}: {e}")
            return {
                'risk': PositionRisk(
                    position_id=position.get('position_id', 'unknown'),
                    symbol=position.get('symbol', 'unknown'),
                    risk_score=1.0,  # Maximum risk on error
                    delta_risk=0, gamma_risk=0, theta_decay=0, vega_risk=0,
                    liquidity_risk=1.0, concentration_risk=0, time_decay_risk=0
                ),
                'alerts': [RiskAlert(
                    timestamp=datetime.now(),
                    level=RiskLevel.WARNING,
                    component="position_analyzer",
                    rule="position_analysis_error",
                    message=f"Position {position.get('position_id')} analysis failed: {e}",
                    current_value=0,
                    limit_value=0,
                    recommended_action=RiskAction.CLOSE_RISKY,
                    metadata={'position_id': position.get('position_id'), 'error': str(e)}
                )]
            }
    
    def _analyze_greeks_risk(self, position: Dict[str, Any]) -> List[RiskAlert]:
        """Analyze Greeks-based risk for a position"""
        alerts = []
        
        try:
            quantity = position.get('quantity', 0)
            delta = position.get('delta', 0)
            gamma = position.get('gamma', 0)
            vega = position.get('vega', 0)
            theta = position.get('theta', 0)
            
            # Delta risk
            position_delta = abs(delta * quantity * 100)  # Per $1 move
            if position_delta > self.max_position_delta:
                alerts.append(RiskAlert(
                    timestamp=datetime.now(),
                    level=RiskLevel.WARNING if position_delta < self.max_position_delta * 1.5 else RiskLevel.CRITICAL,
                    component="position_analyzer",
                    rule="position_delta_limit",
                    message=f"Position delta exposure ${position_delta:,.0f} exceeds limit ${self.max_position_delta:,.0f}",
                    current_value=position_delta,
                    limit_value=self.max_position_delta,
                    recommended_action=RiskAction.REDUCE_SIZE,
                    metadata={
                        'position_id': position.get('position_id'),
                        'symbol': position.get('symbol'),
                        'delta_per_contract': delta,
                        'quantity': quantity
                    }
                ))
            
            # Gamma risk
            position_gamma = abs(gamma * quantity * 100)  # Per $1 move
            if position_gamma > self.max_position_gamma:
                alerts.append(RiskAlert(
                    timestamp=datetime.now(),
                    level=RiskLevel.WARNING,
                    component="position_analyzer",
                    rule="position_gamma_limit",
                    message=f"Position gamma exposure ${position_gamma:,.0f} exceeds limit ${self.max_position_gamma:,.0f}",
                    current_value=position_gamma,
                    limit_value=self.max_position_gamma,
                    recommended_action=RiskAction.REDUCE_SIZE,
                    metadata={
                        'position_id': position.get('position_id'),
                        'symbol': position.get('symbol'),
                        'gamma_per_contract': gamma,
                        'quantity': quantity
                    }
                ))
            
            # Vega risk
            position_vega = abs(vega * quantity)  # Per 1% vol move
            if position_vega > self.max_position_vega:
                alerts.append(RiskAlert(
                    timestamp=datetime.now(),
                    level=RiskLevel.WARNING,
                    component="position_analyzer",
                    rule="position_vega_limit",
                    message=f"Position vega exposure ${position_vega:,.0f} exceeds limit ${self.max_position_vega:,.0f}",
                    current_value=position_vega,
                    limit_value=self.max_position_vega,
                    recommended_action=RiskAction.REDUCE_SIZE,
                    metadata={
                        'position_id': position.get('position_id'),
                        'symbol': position.get('symbol'),
                        'vega_per_contract': vega,
                        'quantity': quantity
                    }
                ))
            
            # Theta decay
            daily_theta_decay = abs(theta * quantity)
            if daily_theta_decay > self.max_theta_decay_daily:
                alerts.append(RiskAlert(
                    timestamp=datetime.now(),
                    level=RiskLevel.CAUTION,
                    component="position_analyzer",
                    rule="position_theta_decay",
                    message=f"Daily theta decay ${daily_theta_decay:,.0f} exceeds threshold ${self.max_theta_decay_daily:,.0f}",
                    current_value=daily_theta_decay,
                    limit_value=self.max_theta_decay_daily,
                    recommended_action=RiskAction.REDUCE_SIZE,
                    metadata={
                        'position_id': position.get('position_id'),
                        'symbol': position.get('symbol'),
                        'theta_per_contract': theta,
                        'quantity': quantity
                    }
                ))
                
        except Exception as e:
            logger.error(f"Error analyzing Greeks risk: {e}")
            
        return alerts
    
    def _analyze_stop_losses(self, position: Dict[str, Any]) -> List[RiskAlert]:
        """Analyze stop loss conditions for a position"""
        alerts = []
        
        try:
            entry_price = position.get('entry_price', 0)
            current_price = position.get('current_price', entry_price)
            unrealized_pnl = position.get('unrealized_pnl', 0)
            position_value = abs(entry_price * position.get('quantity', 0) * 100)  # Notional value
            
            if position_value == 0:
                return alerts
            
            # Calculate P&L percentage
            pnl_percentage = unrealized_pnl / position_value if position_value > 0 else 0
            
            # Check stop loss threshold
            if pnl_percentage < -self.position_stop_loss_pct:
                severity = RiskLevel.CRITICAL if pnl_percentage < -self.position_stop_loss_pct * 1.5 else RiskLevel.WARNING
                
                alerts.append(RiskAlert(
                    timestamp=datetime.now(),
                    level=severity,
                    component="position_analyzer",
                    rule="position_stop_loss",
                    message=f"Position stop loss triggered: {pnl_percentage:.1%} loss exceeds {self.position_stop_loss_pct:.1%} threshold",
                    current_value=abs(pnl_percentage),
                    limit_value=self.position_stop_loss_pct,
                    recommended_action=RiskAction.CLOSE_RISKY,
                    metadata={
                        'position_id': position.get('position_id'),
                        'symbol': position.get('symbol'),
                        'entry_price': entry_price,
                        'current_price': current_price,
                        'unrealized_pnl': unrealized_pnl,
                        'position_value': position_value
                    }
                ))
                
        except Exception as e:
            logger.error(f"Error analyzing stop losses: {e}")
            
        return alerts
    
    def _analyze_time_decay(self, position: Dict[str, Any]) -> List[RiskAlert]:
        """Analyze time decay risk for a position"""
        alerts = []
        
        try:
            dte = position.get('days_to_expiry', 365)  # Default to far expiry
            option_type = position.get('option_type', 'unknown')
            
            # Check for low DTE positions
            if dte <= self.critical_dte_threshold and option_type in ['C', 'P']:
                alerts.append(RiskAlert(
                    timestamp=datetime.now(),
                    level=RiskLevel.CRITICAL,
                    component="position_analyzer",
                    rule="critical_time_decay",
                    message=f"Critical time decay risk: {dte} days to expiry (threshold: {self.critical_dte_threshold})",
                    current_value=dte,
                    limit_value=self.critical_dte_threshold,
                    recommended_action=RiskAction.CLOSE_RISKY,
                    metadata={
                        'position_id': position.get('position_id'),
                        'symbol': position.get('symbol'),
                        'option_type': option_type,
                        'expiry_date': position.get('expiry_date')
                    }
                ))
            elif dte <= self.low_dte_threshold and option_type in ['C', 'P']:
                alerts.append(RiskAlert(
                    timestamp=datetime.now(),
                    level=RiskLevel.WARNING,
                    component="position_analyzer",
                    rule="high_time_decay",
                    message=f"High time decay risk: {dte} days to expiry (threshold: {self.low_dte_threshold})",
                    current_value=dte,
                    limit_value=self.low_dte_threshold,
                    recommended_action=RiskAction.REDUCE_SIZE,
                    metadata={
                        'position_id': position.get('position_id'),
                        'symbol': position.get('symbol'),
                        'option_type': option_type,
                        'expiry_date': position.get('expiry_date')
                    }
                ))
                
        except Exception as e:
            logger.error(f"Error analyzing time decay: {e}")
            
        return alerts
    
    def _analyze_position_liquidity(self, position: Dict[str, Any], 
                                   market_data: Dict[str, Any]) -> List[RiskAlert]:
        """Analyze liquidity risk for a position"""
        alerts = []
        
        try:
            symbol = position.get('symbol', '')
            daily_volume = position.get('volume', 0)
            open_interest = position.get('open_interest', 0)
            bid_ask_spread = position.get('bid_ask_spread', 0)
            
            # Check minimum volume
            if daily_volume < self.min_daily_volume:
                alerts.append(RiskAlert(
                    timestamp=datetime.now(),
                    level=RiskLevel.WARNING,
                    component="position_analyzer",
                    rule="low_liquidity_volume",
                    message=f"Low liquidity: daily volume {daily_volume} below threshold {self.min_daily_volume}",
                    current_value=daily_volume,
                    limit_value=self.min_daily_volume,
                    recommended_action=RiskAction.REDUCE_SIZE,
                    metadata={
                        'position_id': position.get('position_id'),
                        'symbol': symbol,
                        'volume': daily_volume,
                        'open_interest': open_interest
                    }
                ))
            
            # Check minimum open interest
            if open_interest < self.min_open_interest:
                alerts.append(RiskAlert(
                    timestamp=datetime.now(),
                    level=RiskLevel.WARNING,
                    component="position_analyzer",
                    rule="low_liquidity_oi",
                    message=f"Low liquidity: open interest {open_interest} below threshold {self.min_open_interest}",
                    current_value=open_interest,
                    limit_value=self.min_open_interest,
                    recommended_action=RiskAction.REDUCE_SIZE,
                    metadata={
                        'position_id': position.get('position_id'),
                        'symbol': symbol,
                        'volume': daily_volume,
                        'open_interest': open_interest
                    }
                ))
                
        except Exception as e:
            logger.error(f"Error analyzing position liquidity: {e}")
            
        return alerts
    
    def _analyze_position_portfolio(self, positions: List[Dict[str, Any]], 
                                   position_risks: List[PositionRisk]) -> Dict[str, Any]:
        """Analyze portfolio-level position risks"""
        alerts = []
        
        try:
            if not positions:
                return {'alerts': alerts}
            
            # Calculate total portfolio value
            total_value = sum(abs(pos.get('market_value', 0)) for pos in positions)
            
            if total_value == 0:
                return {'alerts': alerts}
            
            # Check concentration by symbol
            symbol_concentrations = {}
            for position in positions:
                symbol = position.get('symbol', 'unknown')
                value = abs(position.get('market_value', 0))
                symbol_concentrations[symbol] = symbol_concentrations.get(symbol, 0) + value
            
            for symbol, value in symbol_concentrations.items():
                concentration_pct = value / total_value
                if concentration_pct > self.max_single_position_pct:
                    alerts.append(RiskAlert(
                        timestamp=datetime.now(),
                        level=RiskLevel.WARNING,
                        component="position_analyzer",
                        rule="symbol_concentration",
                        message=f"Symbol concentration risk: {symbol} represents {concentration_pct:.1%} of portfolio (limit: {self.max_single_position_pct:.1%})",
                        current_value=concentration_pct,
                        limit_value=self.max_single_position_pct,
                        recommended_action=RiskAction.REDUCE_SIZE,
                        metadata={
                            'symbol': symbol,
                            'concentration_value': value,
                            'total_portfolio_value': total_value
                        }
                    ))
            
            # Update concentration risk in position risks
            for i, position_risk in enumerate(position_risks):
                symbol_value = symbol_concentrations.get(position_risk.symbol, 0)
                position_risk.concentration_risk = symbol_value / total_value
                
        except Exception as e:
            logger.error(f"Error analyzing position portfolio: {e}")
            
        return {'alerts': alerts}
    
    # Risk calculation methods
    
    def _calculate_position_risk_score(self, position: Dict[str, Any], 
                                      alerts: List[RiskAlert]) -> float:
        """Calculate overall risk score for a position (0.0 to 1.0)"""
        try:
            # Base risk score
            risk_score = 0.0
            
            # Add risk based on alerts
            for alert in alerts:
                if alert.level == RiskLevel.EMERGENCY:
                    risk_score += 0.5
                elif alert.level == RiskLevel.CRITICAL:
                    risk_score += 0.3
                elif alert.level == RiskLevel.WARNING:
                    risk_score += 0.2
                elif alert.level == RiskLevel.CAUTION:
                    risk_score += 0.1
            
            # Add risk based on position characteristics
            dte = position.get('days_to_expiry', 365)
            if dte <= 7:
                risk_score += 0.2
            elif dte <= 14:
                risk_score += 0.1
            
            # Normalize to 0.0-1.0 range
            return min(1.0, risk_score)
            
        except Exception as e:
            logger.error(f"Error calculating position risk score: {e}")
            return 0.5  # Default medium risk
    
    def _calculate_delta_risk(self, position: Dict[str, Any]) -> float:
        """Calculate delta risk for a position"""
        try:
            delta = position.get('delta', 0)
            quantity = position.get('quantity', 0)
            return abs(delta * quantity * 100)  # Dollar delta per $1 move
        except:
            return 0.0
    
    def _calculate_gamma_risk(self, position: Dict[str, Any]) -> float:
        """Calculate gamma risk for a position"""
        try:
            gamma = position.get('gamma', 0)
            quantity = position.get('quantity', 0)
            return abs(gamma * quantity * 100)  # Dollar gamma per $1 move
        except:
            return 0.0
    
    def _calculate_vega_risk(self, position: Dict[str, Any]) -> float:
        """Calculate vega risk for a position"""
        try:
            vega = position.get('vega', 0)
            quantity = position.get('quantity', 0)
            return abs(vega * quantity)  # Dollar vega per 1% vol move
        except:
            return 0.0
    
    def _calculate_liquidity_risk(self, position: Dict[str, Any], 
                                 market_data: Dict[str, Any]) -> float:
        """Calculate liquidity risk score (0.0 to 1.0)"""
        try:
            volume = position.get('volume', 0)
            open_interest = position.get('open_interest', 0)
            
            # Liquidity score based on volume and open interest
            volume_score = min(1.0, volume / max(self.min_daily_volume, 1))
            oi_score = min(1.0, open_interest / max(self.min_open_interest, 1))
            
            # Combined liquidity score (higher is better, so invert for risk)
            liquidity_score = (volume_score + oi_score) / 2
            return 1.0 - liquidity_score
            
        except:
            return 0.5  # Default medium liquidity risk
    
    def _calculate_time_decay_risk(self, position: Dict[str, Any]) -> float:
        """Calculate time decay risk score (0.0 to 1.0)"""
        try:
            dte = position.get('days_to_expiry', 365)
            option_type = position.get('option_type', '')
            
            if option_type not in ['C', 'P']:
                return 0.0  # No time decay for non-options
            
            # Time decay risk increases exponentially as expiry approaches
            if dte <= 3:
                return 1.0
            elif dte <= 7:
                return 0.8
            elif dte <= 14:
                return 0.6
            elif dte <= 30:
                return 0.4
            elif dte <= 60:
                return 0.2
            else:
                return 0.1
                
        except:
            return 0.0
    
    def _compile_position_metrics(self, position_risks: List[PositionRisk],
                                 portfolio_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Compile comprehensive position risk metrics"""
        try:
            if not position_risks:
                return {}
            
            # Aggregate metrics
            total_positions = len(position_risks)
            avg_risk_score = sum(p.risk_score for p in position_risks) / total_positions
            total_delta_risk = sum(p.delta_risk for p in position_risks)
            total_gamma_risk = sum(p.gamma_risk for p in position_risks)
            total_vega_risk = sum(p.vega_risk for p in position_risks)
            total_theta_decay = sum(p.theta_decay for p in position_risks)
            
            # Risk distribution
            high_risk_positions = len([p for p in position_risks if p.risk_score > 0.7])
            medium_risk_positions = len([p for p in position_risks if 0.3 < p.risk_score <= 0.7])
            low_risk_positions = len([p for p in position_risks if p.risk_score <= 0.3])
            
            return {
                'total_positions': total_positions,
                'average_risk_score': avg_risk_score,
                'risk_distribution': {
                    'high_risk': high_risk_positions,
                    'medium_risk': medium_risk_positions,
                    'low_risk': low_risk_positions
                },
                'aggregate_greeks': {
                    'total_delta_risk': total_delta_risk,
                    'total_gamma_risk': total_gamma_risk,
                    'total_vega_risk': total_vega_risk,
                    'total_theta_decay': total_theta_decay
                },
                'liquidity_metrics': {
                    'avg_liquidity_risk': sum(p.liquidity_risk for p in position_risks) / total_positions,
                    'high_liquidity_risk_count': len([p for p in position_risks if p.liquidity_risk > 0.7])
                },
                'time_decay_metrics': {
                    'avg_time_decay_risk': sum(p.time_decay_risk for p in position_risks) / total_positions,
                    'high_time_decay_count': len([p for p in position_risks if p.time_decay_risk > 0.7])
                }
            }
            
        except Exception as e:
            logger.error(f"Error compiling position metrics: {e}")
            return {}