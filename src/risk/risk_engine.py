"""
Risk Engine - Core Risk Management Coordinator
Orchestrates all risk management components and provides unified risk assessment
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from .risk_types import RiskLevel, RiskAction, RiskAlert
from .position_risk import PositionRiskAnalyzer
from .portfolio_risk import PortfolioRiskAnalyzer
from .compliance import ComplianceMonitor

logger = logging.getLogger(__name__)

@dataclass
class RiskAssessment:
    """Comprehensive risk assessment result"""
    timestamp: datetime
    overall_level: RiskLevel
    recommended_action: RiskAction
    alerts: List[RiskAlert]
    metrics: Dict[str, Any]
    position_count: int
    portfolio_value: float
    confidence_score: float

class RiskEngine:
    """
    Core risk engine that coordinates all risk management components
    and provides unified risk assessment and action recommendations
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the risk engine
        
        Args:
            config: Risk management configuration
        """
        self.config = config
        self.risk_config = config.get('risk_management', {})
        
        # Initialize risk analyzers
        self.position_analyzer = PositionRiskAnalyzer(config)
        self.portfolio_analyzer = PortfolioRiskAnalyzer(config)
        self.compliance_monitor = ComplianceMonitor(config)
        
        # Risk engine parameters
        self.assessment_frequency = self.risk_config.get('assessment_frequency', 30)  # seconds
        self.alert_retention_hours = self.risk_config.get('alert_retention_hours', 24)
        self.confidence_threshold = self.risk_config.get('confidence_threshold', 0.7)
        
        # State tracking
        self.current_assessment: Optional[RiskAssessment] = None
        self.last_assessment_time: Optional[datetime] = None
        self.alert_history: List[RiskAlert] = []
        self.assessment_history: List[RiskAssessment] = []
        
        # Risk level escalation tracking
        self.risk_level_history: List[Dict[str, Any]] = []
        self.consecutive_warnings = 0
        self.last_emergency_time: Optional[datetime] = None
        
        logger.info("Risk engine initialized")
    
    async def assess_risk(self, positions: List[Dict[str, Any]], 
                         market_data: Dict[str, Any],
                         portfolio_metrics: Dict[str, Any]) -> RiskAssessment:
        """
        Perform comprehensive risk assessment
        
        Args:
            positions: Current trading positions
            market_data: Current market data
            portfolio_metrics: Portfolio performance metrics
            
        Returns:
            Comprehensive risk assessment
        """
        try:
            assessment_start = datetime.now()
            
            # 1. Analyze position-level risks
            position_risks = await self.position_analyzer.analyze_positions(
                positions, market_data
            )
            
            # 2. Analyze portfolio-level risks
            portfolio_risks = await self.portfolio_analyzer.analyze_portfolio(
                positions, market_data, portfolio_metrics
            )
            
            # 3. Check compliance violations
            compliance_risks = await self.compliance_monitor.check_compliance(
                positions, market_data, portfolio_metrics
            )
            
            # 4. Consolidate all risk alerts
            all_alerts = (position_risks.get('alerts', []) + 
                         portfolio_risks.get('alerts', []) + 
                         compliance_risks.get('alerts', []))
            
            # 5. Determine overall risk level
            overall_level = self._determine_overall_risk_level(all_alerts)
            
            # 6. Recommend actions
            recommended_action = self._determine_recommended_action(overall_level, all_alerts)
            
            # 7. Calculate confidence score
            confidence_score = self._calculate_confidence_score(
                position_risks, portfolio_risks, compliance_risks
            )
            
            # 8. Compile comprehensive metrics
            comprehensive_metrics = self._compile_comprehensive_metrics(
                position_risks, portfolio_risks, compliance_risks
            )
            
            # 9. Create assessment
            assessment = RiskAssessment(
                timestamp=assessment_start,
                overall_level=overall_level,
                recommended_action=recommended_action,
                alerts=all_alerts,
                metrics=comprehensive_metrics,
                position_count=len(positions),
                portfolio_value=portfolio_metrics.get('total_value', 0),
                confidence_score=confidence_score
            )
            
            # 10. Update state and history
            self._update_assessment_state(assessment)
            
            logger.info(f"Risk assessment completed: {overall_level.value} level, "
                       f"{len(all_alerts)} alerts, {recommended_action.value} action")
            
            return assessment
            
        except Exception as e:
            logger.error(f"Error in risk assessment: {e}")
            
            # Return emergency assessment on error
            return RiskAssessment(
                timestamp=datetime.now(),
                overall_level=RiskLevel.EMERGENCY,
                recommended_action=RiskAction.EMERGENCY_STOP,
                alerts=[RiskAlert(
                    timestamp=datetime.now(),
                    level=RiskLevel.EMERGENCY,
                    component="risk_engine",
                    rule="assessment_failure",
                    message=f"Risk assessment failed: {e}",
                    current_value=0,
                    limit_value=0,
                    recommended_action=RiskAction.EMERGENCY_STOP,
                    metadata={'error': str(e)}
                )],
                metrics={},
                position_count=len(positions),
                portfolio_value=0,
                confidence_score=0.0
            )
    
    def _determine_overall_risk_level(self, alerts: List[RiskAlert]) -> RiskLevel:
        """Determine overall risk level from all alerts"""
        if not alerts:
            return RiskLevel.HEALTHY
        
        # Count alerts by severity
        emergency_count = sum(1 for a in alerts if a.level == RiskLevel.EMERGENCY)
        critical_count = sum(1 for a in alerts if a.level == RiskLevel.CRITICAL)
        warning_count = sum(1 for a in alerts if a.level == RiskLevel.WARNING)
        caution_count = sum(1 for a in alerts if a.level == RiskLevel.CAUTION)
        
        # Escalation logic
        if emergency_count > 0:
            return RiskLevel.EMERGENCY
        elif critical_count >= 2 or (critical_count >= 1 and warning_count >= 3):
            return RiskLevel.CRITICAL
        elif critical_count >= 1 or warning_count >= 3:
            return RiskLevel.WARNING
        elif warning_count >= 1 or caution_count >= 3:
            return RiskLevel.CAUTION
        else:
            return RiskLevel.HEALTHY
    
    def _determine_recommended_action(self, risk_level: RiskLevel, 
                                    alerts: List[RiskAlert]) -> RiskAction:
        """Determine recommended action based on risk level and alerts"""
        
        # Emergency conditions
        if risk_level == RiskLevel.EMERGENCY:
            return RiskAction.EMERGENCY_STOP
        
        # Critical conditions
        if risk_level == RiskLevel.CRITICAL:
            # Check for specific critical conditions
            stop_loss_alerts = [a for a in alerts if 'stop_loss' in a.rule.lower()]
            if stop_loss_alerts:
                return RiskAction.CLOSE_ALL
            else:
                return RiskAction.CLOSE_RISKY
        
        # Warning conditions
        if risk_level == RiskLevel.WARNING:
            # Check for position limit violations
            position_alerts = [a for a in alerts if 'position' in a.rule.lower()]
            if position_alerts:
                return RiskAction.REDUCE_SIZE
            else:
                return RiskAction.BLOCK_NEW
        
        # Caution conditions
        if risk_level == RiskLevel.CAUTION:
            return RiskAction.REDUCE_SIZE
        
        # Healthy state
        return RiskAction.ALLOW_ALL
    
    def _calculate_confidence_score(self, position_risks: Dict[str, Any],
                                   portfolio_risks: Dict[str, Any],
                                   compliance_risks: Dict[str, Any]) -> float:
        """Calculate confidence score for the risk assessment"""
        try:
            # Base confidence starts at 1.0
            confidence = 1.0
            
            # Reduce confidence based on data quality issues
            data_quality = portfolio_risks.get('data_quality', {})
            if data_quality.get('stale_data_pct', 0) > 0.1:  # >10% stale data
                confidence -= 0.2
            
            if data_quality.get('missing_greeks_pct', 0) > 0.05:  # >5% missing Greeks
                confidence -= 0.1
            
            # Reduce confidence based on model uncertainty
            model_quality = portfolio_risks.get('model_quality', {})
            if model_quality.get('calibration_rmse', 0) > 0.1:  # High calibration error
                confidence -= 0.15
            
            # Reduce confidence based on market conditions
            market_stress = portfolio_risks.get('market_stress', {})
            if market_stress.get('volatility_regime', 'normal') == 'high':
                confidence -= 0.1
            
            return max(0.0, min(1.0, confidence))
            
        except Exception as e:
            logger.error(f"Error calculating confidence score: {e}")
            return 0.5  # Default to medium confidence on error
    
    def _compile_comprehensive_metrics(self, position_risks: Dict[str, Any],
                                     portfolio_risks: Dict[str, Any],
                                     compliance_risks: Dict[str, Any]) -> Dict[str, Any]:
        """Compile comprehensive risk metrics from all analyzers"""
        try:
            return {
                'position_metrics': position_risks.get('metrics', {}),
                'portfolio_metrics': portfolio_risks.get('metrics', {}),
                'compliance_metrics': compliance_risks.get('metrics', {}),
                'assessment_metadata': {
                    'analysis_time_ms': (datetime.now() - self.last_assessment_time).total_seconds() * 1000 if self.last_assessment_time else 0,
                    'analyzer_versions': {
                        'position_analyzer': getattr(self.position_analyzer, 'version', '1.0'),
                        'portfolio_analyzer': getattr(self.portfolio_analyzer, 'version', '1.0'),
                        'compliance_monitor': getattr(self.compliance_monitor, 'version', '1.0')
                    }
                }
            }
        except Exception as e:
            logger.error(f"Error compiling metrics: {e}")
            return {}
    
    def _update_assessment_state(self, assessment: RiskAssessment):
        """Update internal state with new assessment"""
        try:
            # Update current assessment
            self.current_assessment = assessment
            self.last_assessment_time = assessment.timestamp
            
            # Add to history
            self.assessment_history.append(assessment)
            
            # Keep only recent assessments
            if len(self.assessment_history) > 1000:
                self.assessment_history = self.assessment_history[-500:]
            
            # Add alerts to alert history
            self.alert_history.extend(assessment.alerts)
            
            # Clean old alerts
            cutoff_time = datetime.now() - timedelta(hours=self.alert_retention_hours)
            self.alert_history = [a for a in self.alert_history if a.timestamp > cutoff_time]
            
            # Track risk level changes
            self.risk_level_history.append({
                'timestamp': assessment.timestamp,
                'level': assessment.overall_level,
                'alert_count': len(assessment.alerts)
            })
            
            # Track consecutive warnings
            if assessment.overall_level in [RiskLevel.WARNING, RiskLevel.CRITICAL]:
                self.consecutive_warnings += 1
            else:
                self.consecutive_warnings = 0
            
            # Track emergency events
            if assessment.overall_level == RiskLevel.EMERGENCY:
                self.last_emergency_time = assessment.timestamp
                
        except Exception as e:
            logger.error(f"Error updating assessment state: {e}")
    
    # Public API methods
    
    def get_current_risk_level(self) -> RiskLevel:
        """Get current risk level"""
        if self.current_assessment:
            return self.current_assessment.overall_level
        return RiskLevel.HEALTHY
    
    def get_recent_alerts(self, hours: int = 1) -> List[RiskAlert]:
        """Get alerts from the last N hours"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return [a for a in self.alert_history if a.timestamp > cutoff_time]
    
    def get_risk_summary(self) -> Dict[str, Any]:
        """Get comprehensive risk summary"""
        try:
            current_level = self.get_current_risk_level()
            recent_alerts = self.get_recent_alerts(24)  # Last 24 hours
            
            # Alert summary
            alert_counts = {}
            for alert in recent_alerts:
                level = alert.level.value
                alert_counts[level] = alert_counts.get(level, 0) + 1
            
            return {
                'current_risk_level': current_level.value,
                'consecutive_warnings': self.consecutive_warnings,
                'last_emergency': self.last_emergency_time,
                'recent_alerts': {
                    'total': len(recent_alerts),
                    'by_level': alert_counts
                },
                'assessment_stats': {
                    'total_assessments': len(self.assessment_history),
                    'last_assessment': self.last_assessment_time,
                    'confidence_score': self.current_assessment.confidence_score if self.current_assessment else 0.0
                }
            }
        except Exception as e:
            logger.error(f"Error getting risk summary: {e}")
            return {'error': str(e)}
    
    def is_action_allowed(self, action_type: str, position_size: int = 0) -> Dict[str, Any]:
        """Check if a specific action is allowed under current risk conditions"""
        try:
            current_level = self.get_current_risk_level()
            current_action = self.current_assessment.recommended_action if self.current_assessment else RiskAction.ALLOW_ALL
            
            # Define action restrictions by risk level
            restrictions = {
                RiskLevel.HEALTHY: [],
                RiskLevel.CAUTION: ['large_positions'],  # Positions > normal size
                RiskLevel.WARNING: ['new_positions', 'large_positions'],
                RiskLevel.CRITICAL: ['new_positions', 'large_positions', 'size_increases'],
                RiskLevel.EMERGENCY: ['all_trading']
            }
            
            blocked_actions = restrictions.get(current_level, [])
            
            # Check specific action
            action_allowed = action_type not in blocked_actions
            
            # Additional checks for position sizing
            if action_type == 'new_position' and position_size > 0:
                max_size = self._get_max_allowed_position_size()
                if position_size > max_size:
                    action_allowed = False
                    blocked_actions.append(f'position_size_exceeds_{max_size}')
            
            return {
                'allowed': action_allowed,
                'risk_level': current_level.value,
                'recommended_action': current_action.value,
                'blocked_actions': blocked_actions,
                'max_position_size': self._get_max_allowed_position_size()
            }
            
        except Exception as e:
            logger.error(f"Error checking action allowance: {e}")
            return {
                'allowed': False,
                'error': str(e),
                'risk_level': 'unknown'
            }
    
    def _get_max_allowed_position_size(self) -> int:
        """Get maximum allowed position size based on current risk level"""
        current_level = self.get_current_risk_level()
        
        base_size = self.risk_config.get('max_position_size', 100)
        
        size_multipliers = {
            RiskLevel.HEALTHY: 1.0,
            RiskLevel.CAUTION: 0.75,
            RiskLevel.WARNING: 0.5,
            RiskLevel.CRITICAL: 0.25,
            RiskLevel.EMERGENCY: 0.0
        }
        
        multiplier = size_multipliers.get(current_level, 0.5)
        return int(base_size * multiplier)