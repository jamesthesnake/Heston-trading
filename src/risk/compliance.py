"""
Compliance Monitor - Regulatory and Internal Compliance Monitoring
Monitors compliance with regulatory requirements and internal risk policies
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

from .risk_types import RiskLevel, RiskAction, RiskAlert

logger = logging.getLogger(__name__)

class ComplianceRuleType(Enum):
    """Types of compliance rules"""
    REGULATORY = "regulatory"
    INTERNAL = "internal"
    EXCHANGE = "exchange"
    PRUDENTIAL = "prudential"

@dataclass
class ComplianceRule:
    """Individual compliance rule definition"""
    rule_id: str
    rule_type: ComplianceRuleType
    name: str
    description: str
    limit_value: float
    warning_threshold: float
    critical_threshold: float
    enabled: bool = True

class ComplianceMonitor:
    """
    Monitors compliance with regulatory requirements and internal policies
    Including position limits, concentration limits, and trading restrictions
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the compliance monitor
        
        Args:
            config: Compliance configuration
        """
        self.config = config
        self.compliance_config = config.get('compliance', {})
        
        # Regulatory limits (examples - would be customized per jurisdiction)
        self.regulatory_limits = self.compliance_config.get('regulatory_limits', {})
        
        # Internal risk limits
        self.internal_limits = self.compliance_config.get('internal_limits', {})
        
        # Exchange-specific limits
        self.exchange_limits = self.compliance_config.get('exchange_limits', {})
        
        # Initialize compliance rules
        self.compliance_rules = self._initialize_compliance_rules()
        
        # Violation tracking
        self.violation_history: List[Dict[str, Any]] = []
        self.current_violations: List[RiskAlert] = []
        
        # Monitoring parameters
        self.violation_retention_days = self.compliance_config.get('violation_retention_days', 90)
        self.escalation_thresholds = self.compliance_config.get('escalation_thresholds', {
            'minor_violations_per_day': 5,
            'major_violations_per_day': 2,
            'critical_violations_per_day': 1
        })
        
        logger.info("Compliance monitor initialized")
    
    def _initialize_compliance_rules(self) -> List[ComplianceRule]:
        """Initialize all compliance rules"""
        rules = []
        
        # Regulatory rules (examples)
        rules.extend([
            ComplianceRule(
                rule_id="REG_POSITION_LIMIT",
                rule_type=ComplianceRuleType.REGULATORY,
                name="Position Limit",
                description="Maximum position size per security",
                limit_value=self.regulatory_limits.get('max_position_notional', 1000000),
                warning_threshold=0.8,
                critical_threshold=1.0
            ),
            ComplianceRule(
                rule_id="REG_CONCENTRATION_LIMIT",
                rule_type=ComplianceRuleType.REGULATORY,
                name="Concentration Limit",
                description="Maximum concentration in single issuer",
                limit_value=self.regulatory_limits.get('max_single_issuer_pct', 0.25),
                warning_threshold=0.8,
                critical_threshold=1.0
            ),
            ComplianceRule(
                rule_id="REG_LEVERAGE_LIMIT",
                rule_type=ComplianceRuleType.REGULATORY,
                name="Leverage Limit",
                description="Maximum portfolio leverage ratio",
                limit_value=self.regulatory_limits.get('max_leverage_ratio', 3.0),
                warning_threshold=0.85,
                critical_threshold=1.0
            )
        ])
        
        # Internal risk rules
        rules.extend([
            ComplianceRule(
                rule_id="INT_DAILY_LOSS_LIMIT",
                rule_type=ComplianceRuleType.INTERNAL,
                name="Daily Loss Limit",
                description="Maximum daily portfolio loss",
                limit_value=self.internal_limits.get('max_daily_loss', 50000),
                warning_threshold=0.8,
                critical_threshold=1.0
            ),
            ComplianceRule(
                rule_id="INT_VAR_LIMIT",
                rule_type=ComplianceRuleType.INTERNAL,
                name="Value at Risk Limit",
                description="Maximum portfolio VaR",
                limit_value=self.internal_limits.get('max_var_dollar', 100000),
                warning_threshold=0.8,
                critical_threshold=1.0
            ),
            ComplianceRule(
                rule_id="INT_DELTA_LIMIT",
                rule_type=ComplianceRuleType.INTERNAL,
                name="Delta Exposure Limit",
                description="Maximum net delta exposure",
                limit_value=self.internal_limits.get('max_net_delta', 100000),
                warning_threshold=0.8,
                critical_threshold=1.0
            )
        ])
        
        # Exchange rules
        rules.extend([
            ComplianceRule(
                rule_id="EXC_OPTION_POSITION_LIMIT",
                rule_type=ComplianceRuleType.EXCHANGE,
                name="Option Position Limit",
                description="Exchange option position limits",
                limit_value=self.exchange_limits.get('max_option_contracts', 25000),
                warning_threshold=0.9,
                critical_threshold=1.0
            )
        ])
        
        return rules
    
    async def check_compliance(self, positions: List[Dict[str, Any]], 
                              market_data: Dict[str, Any],
                              portfolio_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform comprehensive compliance check
        
        Args:
            positions: Current positions
            market_data: Current market data
            portfolio_metrics: Portfolio performance metrics
            
        Returns:
            Compliance check results
        """
        try:
            check_start = datetime.now()
            
            alerts = []
            compliance_metrics = {}
            
            # Check each compliance rule
            for rule in self.compliance_rules:
                if not rule.enabled:
                    continue
                
                rule_alerts = await self._check_compliance_rule(
                    rule, positions, market_data, portfolio_metrics
                )
                alerts.extend(rule_alerts)
            
            # Check for compliance patterns and escalations
            escalation_alerts = self._check_compliance_escalations()
            alerts.extend(escalation_alerts)
            
            # Update violation history
            self._update_violation_history(alerts)
            
            # Compile compliance metrics
            compliance_metrics = self._compile_compliance_metrics()
            
            check_time = (datetime.now() - check_start).total_seconds()
            
            return {
                'alerts': alerts,
                'metrics': compliance_metrics,
                'check_time': check_time,
                'rules_checked': len([r for r in self.compliance_rules if r.enabled]),
                'violations_today': self._count_violations_today()
            }
            
        except Exception as e:
            logger.error(f"Error checking compliance: {e}")
            return {
                'alerts': [RiskAlert(
                    timestamp=datetime.now(),
                    level=RiskLevel.WARNING,
                    component="compliance_monitor",
                    rule="compliance_check_error",
                    message=f"Compliance check failed: {e}",
                    current_value=0,
                    limit_value=0,
                    recommended_action=RiskAction.BLOCK_NEW,
                    metadata={'error': str(e)}
                )],
                'metrics': {},
                'check_time': 0
            }
    
    async def _check_compliance_rule(self, rule: ComplianceRule,
                                    positions: List[Dict[str, Any]], 
                                    market_data: Dict[str, Any],
                                    portfolio_metrics: Dict[str, Any]) -> List[RiskAlert]:
        """Check a specific compliance rule"""
        try:
            # Calculate current value for the rule
            current_value = self._calculate_rule_value(rule, positions, market_data, portfolio_metrics)
            
            if current_value is None:
                return []  # Skip if cannot calculate
            
            alerts = []
            
            # Check warning threshold
            warning_limit = rule.limit_value * rule.warning_threshold
            if abs(current_value) >= warning_limit:
                
                # Determine severity
                critical_limit = rule.limit_value * rule.critical_threshold
                if abs(current_value) >= critical_limit:
                    level = RiskLevel.CRITICAL
                    action = self._get_critical_action(rule)
                else:
                    level = RiskLevel.WARNING
                    action = self._get_warning_action(rule)
                
                alert = RiskAlert(
                    timestamp=datetime.now(),
                    level=level,
                    component="compliance_monitor",
                    rule=rule.rule_id,
                    message=f"{rule.name} violation: {abs(current_value):,.0f} exceeds {warning_limit:,.0f}",
                    current_value=abs(current_value),
                    limit_value=warning_limit,
                    recommended_action=action,
                    metadata={
                        'rule_type': rule.rule_type.value,
                        'rule_name': rule.name,
                        'description': rule.description,
                        'limit_value': rule.limit_value,
                        'warning_threshold': rule.warning_threshold,
                        'critical_threshold': rule.critical_threshold
                    }
                )
                
                alerts.append(alert)
            
            return alerts
            
        except Exception as e:
            logger.error(f"Error checking rule {rule.rule_id}: {e}")
            return []
    
    def _calculate_rule_value(self, rule: ComplianceRule,
                             positions: List[Dict[str, Any]], 
                             market_data: Dict[str, Any],
                             portfolio_metrics: Dict[str, Any]) -> Optional[float]:
        """Calculate current value for a compliance rule"""
        try:
            if rule.rule_id == "REG_POSITION_LIMIT":
                # Maximum single position notional value
                if not positions:
                    return 0.0
                return max(abs(pos.get('market_value', 0)) for pos in positions)
            
            elif rule.rule_id == "REG_CONCENTRATION_LIMIT":
                # Maximum concentration in single issuer
                total_value = sum(abs(pos.get('market_value', 0)) for pos in positions)
                if total_value == 0:
                    return 0.0
                
                concentrations = {}
                for pos in positions:
                    issuer = pos.get('underlying', pos.get('symbol', 'unknown'))
                    value = abs(pos.get('market_value', 0))
                    concentrations[issuer] = concentrations.get(issuer, 0) + value
                
                max_concentration = max(concentrations.values()) if concentrations else 0
                return max_concentration / total_value
            
            elif rule.rule_id == "REG_LEVERAGE_LIMIT":
                # Portfolio leverage ratio
                total_notional = sum(abs(pos.get('notional_value', pos.get('market_value', 0))) 
                                   for pos in positions)
                equity = portfolio_metrics.get('account_equity', 1000000)
                return total_notional / equity if equity > 0 else 0
            
            elif rule.rule_id == "INT_DAILY_LOSS_LIMIT":
                # Daily portfolio loss
                daily_pnl = portfolio_metrics.get('daily_pnl', 0)
                return abs(min(0, daily_pnl))  # Only count losses
            
            elif rule.rule_id == "INT_VAR_LIMIT":
                # Portfolio VaR
                return portfolio_metrics.get('daily_var_95', 0)
            
            elif rule.rule_id == "INT_DELTA_LIMIT":
                # Net delta exposure
                net_delta = sum(pos.get('delta', 0) * pos.get('quantity', 0) * 100 
                              for pos in positions)
                return abs(net_delta)
            
            elif rule.rule_id == "EXC_OPTION_POSITION_LIMIT":
                # Total option contracts
                option_contracts = sum(abs(pos.get('quantity', 0)) 
                                     for pos in positions 
                                     if pos.get('option_type') in ['C', 'P'])
                return option_contracts
            
            else:
                logger.warning(f"Unknown compliance rule: {rule.rule_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error calculating value for rule {rule.rule_id}: {e}")
            return None
    
    def _get_warning_action(self, rule: ComplianceRule) -> RiskAction:
        """Get recommended action for warning-level violations"""
        if rule.rule_type == ComplianceRuleType.REGULATORY:
            return RiskAction.BLOCK_NEW
        elif rule.rule_type == ComplianceRuleType.INTERNAL:
            return RiskAction.REDUCE_SIZE
        else:
            return RiskAction.REDUCE_SIZE
    
    def _get_critical_action(self, rule: ComplianceRule) -> RiskAction:
        """Get recommended action for critical-level violations"""
        if rule.rule_type == ComplianceRuleType.REGULATORY:
            return RiskAction.CLOSE_ALL
        elif rule.rule_type == ComplianceRuleType.INTERNAL:
            return RiskAction.CLOSE_RISKY
        else:
            return RiskAction.CLOSE_RISKY
    
    def _check_compliance_escalations(self) -> List[RiskAlert]:
        """Check for compliance escalation patterns"""
        alerts = []
        
        try:
            # Count violations today
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            today_violations = [v for v in self.violation_history 
                              if v['timestamp'] >= today_start]
            
            # Count by severity
            minor_count = len([v for v in today_violations if v['level'] == RiskLevel.CAUTION.value])
            major_count = len([v for v in today_violations if v['level'] == RiskLevel.WARNING.value])
            critical_count = len([v for v in today_violations if v['level'] == RiskLevel.CRITICAL.value])
            
            # Check escalation thresholds
            if critical_count >= self.escalation_thresholds['critical_violations_per_day']:
                alerts.append(RiskAlert(
                    timestamp=datetime.now(),
                    level=RiskLevel.EMERGENCY,
                    component="compliance_monitor",
                    rule="critical_violation_escalation",
                    message=f"Critical violation threshold exceeded: {critical_count} critical violations today",
                    current_value=critical_count,
                    limit_value=self.escalation_thresholds['critical_violations_per_day'],
                    recommended_action=RiskAction.EMERGENCY_STOP,
                    metadata={
                        'critical_violations': critical_count,
                        'major_violations': major_count,
                        'minor_violations': minor_count
                    }
                ))
            
            elif major_count >= self.escalation_thresholds['major_violations_per_day']:
                alerts.append(RiskAlert(
                    timestamp=datetime.now(),
                    level=RiskLevel.CRITICAL,
                    component="compliance_monitor",
                    rule="major_violation_escalation",
                    message=f"Major violation threshold exceeded: {major_count} major violations today",
                    current_value=major_count,
                    limit_value=self.escalation_thresholds['major_violations_per_day'],
                    recommended_action=RiskAction.CLOSE_RISKY,
                    metadata={
                        'major_violations': major_count,
                        'minor_violations': minor_count
                    }
                ))
            
            elif minor_count >= self.escalation_thresholds['minor_violations_per_day']:
                alerts.append(RiskAlert(
                    timestamp=datetime.now(),
                    level=RiskLevel.WARNING,
                    component="compliance_monitor",
                    rule="minor_violation_escalation",
                    message=f"Minor violation threshold exceeded: {minor_count} minor violations today",
                    current_value=minor_count,
                    limit_value=self.escalation_thresholds['minor_violations_per_day'],
                    recommended_action=RiskAction.BLOCK_NEW,
                    metadata={
                        'minor_violations': minor_count
                    }
                ))
            
            return alerts
            
        except Exception as e:
            logger.error(f"Error checking compliance escalations: {e}")
            return []
    
    def _update_violation_history(self, alerts: List[RiskAlert]):
        """Update violation history with new alerts"""
        try:
            for alert in alerts:
                violation_record = {
                    'timestamp': alert.timestamp,
                    'level': alert.level.value,
                    'rule': alert.rule,
                    'message': alert.message,
                    'current_value': alert.current_value,
                    'limit_value': alert.limit_value
                }
                self.violation_history.append(violation_record)
            
            # Clean old violations
            cutoff_date = datetime.now() - timedelta(days=self.violation_retention_days)
            self.violation_history = [v for v in self.violation_history 
                                    if v['timestamp'] > cutoff_date]
            
            # Update current violations
            self.current_violations = alerts
            
        except Exception as e:
            logger.error(f"Error updating violation history: {e}")
    
    def _count_violations_today(self) -> Dict[str, int]:
        """Count violations by severity for today"""
        try:
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            today_violations = [v for v in self.violation_history 
                              if v['timestamp'] >= today_start]
            
            counts = {
                'total': len(today_violations),
                'critical': len([v for v in today_violations if v['level'] == RiskLevel.CRITICAL.value]),
                'warning': len([v for v in today_violations if v['level'] == RiskLevel.WARNING.value]),
                'caution': len([v for v in today_violations if v['level'] == RiskLevel.CAUTION.value])
            }
            
            return counts
            
        except Exception as e:
            logger.error(f"Error counting violations: {e}")
            return {'total': 0, 'critical': 0, 'warning': 0, 'caution': 0}
    
    def _compile_compliance_metrics(self) -> Dict[str, Any]:
        """Compile comprehensive compliance metrics"""
        try:
            violations_today = self._count_violations_today()
            
            # Rule compliance status
            rule_status = {}
            for rule in self.compliance_rules:
                rule_status[rule.rule_id] = {
                    'name': rule.name,
                    'enabled': rule.enabled,
                    'type': rule.rule_type.value,
                    'limit_value': rule.limit_value
                }
            
            # Historical compliance
            total_violations = len(self.violation_history)
            avg_violations_per_day = total_violations / max(self.violation_retention_days, 1)
            
            return {
                'violations_today': violations_today,
                'total_rules': len(self.compliance_rules),
                'enabled_rules': len([r for r in self.compliance_rules if r.enabled]),
                'rule_status': rule_status,
                'historical_metrics': {
                    'total_violations': total_violations,
                    'avg_violations_per_day': avg_violations_per_day,
                    'retention_days': self.violation_retention_days
                },
                'escalation_thresholds': self.escalation_thresholds
            }
            
        except Exception as e:
            logger.error(f"Error compiling compliance metrics: {e}")
            return {}
    
    # Public API methods
    
    def get_compliance_status(self) -> Dict[str, Any]:
        """Get current compliance status"""
        try:
            violations_today = self._count_violations_today()
            
            # Determine overall compliance status
            if violations_today['critical'] > 0:
                status = 'CRITICAL'
            elif violations_today['warning'] > 0:
                status = 'WARNING'
            elif violations_today['caution'] > 0:
                status = 'CAUTION'
            else:
                status = 'COMPLIANT'
            
            return {
                'overall_status': status,
                'violations_today': violations_today,
                'current_violations': len(self.current_violations),
                'last_check': max([v['timestamp'] for v in self.violation_history]) if self.violation_history else None
            }
            
        except Exception as e:
            logger.error(f"Error getting compliance status: {e}")
            return {'overall_status': 'UNKNOWN', 'error': str(e)}
    
    def get_rule_details(self, rule_id: str) -> Optional[Dict[str, Any]]:
        """Get details for a specific compliance rule"""
        try:
            rule = next((r for r in self.compliance_rules if r.rule_id == rule_id), None)
            if not rule:
                return None
            
            # Get recent violations for this rule
            recent_violations = [v for v in self.violation_history 
                               if v['rule'] == rule_id and 
                               v['timestamp'] > datetime.now() - timedelta(days=30)]
            
            return {
                'rule_id': rule.rule_id,
                'name': rule.name,
                'description': rule.description,
                'type': rule.rule_type.value,
                'limit_value': rule.limit_value,
                'warning_threshold': rule.warning_threshold,
                'critical_threshold': rule.critical_threshold,
                'enabled': rule.enabled,
                'recent_violations': len(recent_violations),
                'last_violation': max([v['timestamp'] for v in recent_violations]) if recent_violations else None
            }
            
        except Exception as e:
            logger.error(f"Error getting rule details for {rule_id}: {e}")
            return None
    
    def is_trading_allowed(self, trade_type: str, trade_size: float = 0) -> Dict[str, Any]:
        """Check if a specific trade is allowed under current compliance rules"""
        try:
            violations_today = self._count_violations_today()
            
            # Block all trading if critical violations
            if violations_today['critical'] > 0:
                return {
                    'allowed': False,
                    'reason': 'Critical compliance violations present',
                    'violations': violations_today
                }
            
            # Restrict new positions if warning violations
            if violations_today['warning'] > 0 and trade_type == 'new_position':
                return {
                    'allowed': False,
                    'reason': 'New positions blocked due to compliance warnings',
                    'violations': violations_today
                }
            
            # Allow trading if compliant
            return {
                'allowed': True,
                'compliance_status': 'OK',
                'violations': violations_today
            }
            
        except Exception as e:
            logger.error(f"Error checking trading allowance: {e}")
            return {
                'allowed': False,
                'reason': f'Compliance check error: {e}',
                'error': str(e)
            }