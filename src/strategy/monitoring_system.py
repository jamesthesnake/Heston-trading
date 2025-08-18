"""
Comprehensive Monitoring and Alerting System
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Callable
import logging
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass
from collections import deque
import json

logger = logging.getLogger(__name__)

class AlertLevel(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class MetricType(Enum):
    PERFORMANCE = "performance"
    RISK = "risk"
    EXECUTION = "execution"
    MODEL = "model"
    SYSTEM = "system"

@dataclass
class Alert:
    """Alert message"""
    level: AlertLevel
    metric_type: MetricType
    message: str
    value: float
    threshold: float
    timestamp: datetime
    acknowledged: bool = False

@dataclass
class PerformanceMetrics:
    """Performance tracking metrics"""
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    hit_rate: float = 0.0
    profit_factor: float = 0.0
    total_pnl: float = 0.0
    win_rate: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    total_trades: int = 0

class MonitoringSystem:
    """
    Comprehensive monitoring and alerting for the trading strategy
    """
    
    def __init__(self, config: dict):
        self.config = config
        self.monitoring_config = config.get('monitoring', {})
        
        # Performance targets
        self.target_sharpe = self.monitoring_config.get('target_sharpe', 1.0)
        self.max_drawdown_pct = self.monitoring_config.get('max_drawdown_pct', 0.04)
        self.target_hit_rate = self.monitoring_config.get('target_hit_rate', 0.50)
        
        # Alert configuration
        self.alert_config = self.monitoring_config.get('alerts', {})
        
        # Data storage
        self.pnl_history = deque(maxlen=10000)
        self.trade_history = deque(maxlen=5000)
        self.alerts = deque(maxlen=1000)
        self.metrics_history = deque(maxlen=1000)
        
        # Performance tracking
        self.daily_pnl = 0.0
        self.peak_equity = 0.0
        self.current_drawdown = 0.0
        self.starting_equity = config.get('risk_management', {}).get('starting_equity', 1000000)
        
        # Alert handlers
        self.alert_handlers: List[Callable] = []
        
        # System health tracking
        self.last_data_update = None
        self.calibration_rejections = 0
        self.order_rejections = 0
        self.connection_issues = 0
        
    def add_alert_handler(self, handler: Callable[[Alert], None]):
        """Add alert handler (e.g., email, Slack, SMS)"""
        self.alert_handlers.append(handler)
    
    def update_pnl(self, pnl: float, timestamp: datetime = None):
        """Update P&L and calculate performance metrics"""
        
        if timestamp is None:
            timestamp = datetime.now()
        
        self.daily_pnl = pnl
        current_equity = self.starting_equity + pnl
        
        # Update peak equity and drawdown
        if current_equity > self.peak_equity:
            self.peak_equity = current_equity
            self.current_drawdown = 0.0
        else:
            self.current_drawdown = (self.peak_equity - current_equity) / self.peak_equity
        
        # Store P&L history
        self.pnl_history.append({
            'timestamp': timestamp,
            'pnl': pnl,
            'equity': current_equity,
            'drawdown': self.current_drawdown
        })
        
        # Check performance alerts
        self._check_performance_alerts()
    
    def add_trade(self, trade: Dict):
        """Add completed trade for performance tracking"""
        
        self.trade_history.append({
            'timestamp': trade.get('timestamp', datetime.now()),
            'symbol': trade.get('symbol'),
            'side': trade.get('side'),
            'quantity': trade.get('quantity'),
            'entry_price': trade.get('entry_price'),
            'exit_price': trade.get('exit_price'),
            'pnl': trade.get('pnl', 0),
            'duration_min': trade.get('duration_min', 0),
            'z_score': trade.get('z_score', 0)
        })
        
        # Update performance metrics
        self._update_performance_metrics()
    
    def _update_performance_metrics(self) -> PerformanceMetrics:
        """Calculate current performance metrics"""
        
        if len(self.trade_history) == 0:
            return PerformanceMetrics()
        
        trades = list(self.trade_history)
        pnls = [t['pnl'] for t in trades]
        
        # Basic metrics
        total_pnl = sum(pnls)
        total_trades = len(trades)
        winning_trades = [p for p in pnls if p > 0]
        losing_trades = [p for p in pnls if p < 0]
        
        win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0
        hit_rate = win_rate  # Same as win rate for this strategy
        
        avg_win = np.mean(winning_trades) if winning_trades else 0
        avg_loss = np.mean(losing_trades) if losing_trades else 0
        
        # Profit factor
        gross_profit = sum(winning_trades) if winning_trades else 0
        gross_loss = abs(sum(losing_trades)) if losing_trades else 0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        # Sharpe ratio (annualized)
        if len(pnls) > 1:
            daily_returns = np.array(pnls) / self.starting_equity
            sharpe_ratio = np.mean(daily_returns) / np.std(daily_returns) * np.sqrt(252) if np.std(daily_returns) > 0 else 0
        else:
            sharpe_ratio = 0
        
        metrics = PerformanceMetrics(
            sharpe_ratio=sharpe_ratio,
            max_drawdown=self.current_drawdown,
            hit_rate=hit_rate,
            profit_factor=profit_factor,
            total_pnl=total_pnl,
            win_rate=win_rate,
            avg_win=avg_win,
            avg_loss=avg_loss,
            total_trades=total_trades
        )
        
        # Store metrics history
        self.metrics_history.append({
            'timestamp': datetime.now(),
            'metrics': metrics
        })
        
        return metrics
    
    def _check_performance_alerts(self):
        """Check for performance-related alerts"""
        
        metrics = self._update_performance_metrics()
        
        # Sharpe ratio alert
        if metrics.total_trades >= 20 and metrics.sharpe_ratio < self.target_sharpe:
            self._create_alert(
                AlertLevel.MEDIUM,
                MetricType.PERFORMANCE,
                f"Sharpe ratio below target: {metrics.sharpe_ratio:.2f} < {self.target_sharpe}",
                metrics.sharpe_ratio,
                self.target_sharpe
            )
        
        # Drawdown alert
        if self.current_drawdown > self.max_drawdown_pct:
            self._create_alert(
                AlertLevel.HIGH,
                MetricType.RISK,
                f"Maximum drawdown exceeded: {self.current_drawdown:.2%} > {self.max_drawdown_pct:.2%}",
                self.current_drawdown,
                self.max_drawdown_pct
            )
        
        # Hit rate alert
        if metrics.total_trades >= 20 and (metrics.hit_rate < 0.45 or metrics.hit_rate > 0.55):
            level = AlertLevel.MEDIUM if 0.40 <= metrics.hit_rate <= 0.60 else AlertLevel.HIGH
            self._create_alert(
                level,
                MetricType.PERFORMANCE,
                f"Hit rate outside target range: {metrics.hit_rate:.1%} (target: 45-55%)",
                metrics.hit_rate,
                self.target_hit_rate
            )
    
    def check_system_health(self, system_data: Dict):
        """Check system health metrics"""
        
        current_time = datetime.now()
        
        # Data staleness check
        if 'last_data_update' in system_data:
            data_age = (current_time - system_data['last_data_update']).total_seconds()
            if data_age > 1.5:  # 1.5 seconds threshold
                self._create_alert(
                    AlertLevel.CRITICAL,
                    MetricType.SYSTEM,
                    f"Data staleness detected: {data_age:.1f}s old",
                    data_age,
                    1.5
                )
        
        # Model health check
        if 'model_rmse' in system_data and 'baseline_rmse' in system_data:
            rmse_ratio = system_data['model_rmse'] / system_data['baseline_rmse']
            if rmse_ratio > 1.5:
                self._create_alert(
                    AlertLevel.CRITICAL,
                    MetricType.MODEL,
                    f"Model RMSE degraded: {rmse_ratio:.2f}x baseline",
                    rmse_ratio,
                    1.5
                )
        
        # Calibration rejection rate
        if 'calibration_rejections' in system_data:
            rejection_rate = system_data['calibration_rejections'] / max(system_data.get('calibration_attempts', 1), 1)
            if rejection_rate > 0.10:  # 10% threshold
                self._create_alert(
                    AlertLevel.MEDIUM,
                    MetricType.MODEL,
                    f"High calibration rejection rate: {rejection_rate:.1%}",
                    rejection_rate,
                    0.10
                )
        
        # Order rejection monitoring
        if 'order_rejections' in system_data:
            recent_rejections = system_data['order_rejections']
            if recent_rejections > 5:  # More than 5 rejections recently
                self._create_alert(
                    AlertLevel.HIGH,
                    MetricType.EXECUTION,
                    f"High order rejection count: {recent_rejections}",
                    recent_rejections,
                    5
                )
    
    def check_execution_quality(self, execution_data: Dict):
        """Monitor execution quality metrics"""
        
        # Slippage monitoring
        if 'avg_slippage_bps' in execution_data:
            avg_slippage = execution_data['avg_slippage_bps']
            if avg_slippage > 15:  # 15 bps threshold
                self._create_alert(
                    AlertLevel.MEDIUM,
                    MetricType.EXECUTION,
                    f"High average slippage: {avg_slippage:.1f} bps",
                    avg_slippage,
                    15
                )
        
        # Fill rate monitoring
        if 'fill_rate' in execution_data:
            fill_rate = execution_data['fill_rate']
            if fill_rate < 0.85:  # 85% threshold
                self._create_alert(
                    AlertLevel.MEDIUM,
                    MetricType.EXECUTION,
                    f"Low fill rate: {fill_rate:.1%}",
                    fill_rate,
                    0.85
                )
    
    def _create_alert(self, level: AlertLevel, metric_type: MetricType, 
                     message: str, value: float, threshold: float):
        """Create and process new alert"""
        
        alert = Alert(
            level=level,
            metric_type=metric_type,
            message=message,
            value=value,
            threshold=threshold,
            timestamp=datetime.now()
        )
        
        self.alerts.append(alert)
        
        # Log alert
        log_level = {
            AlertLevel.CRITICAL: logging.CRITICAL,
            AlertLevel.HIGH: logging.ERROR,
            AlertLevel.MEDIUM: logging.WARNING,
            AlertLevel.LOW: logging.INFO
        }[level]
        
        logger.log(log_level, f"ALERT [{level.value.upper()}]: {message}")
        
        # Notify handlers
        for handler in self.alert_handlers:
            try:
                handler(alert)
            except Exception as e:
                logger.error(f"Alert handler failed: {e}")
    
    def get_dashboard_data(self) -> Dict:
        """Get comprehensive dashboard data"""
        
        current_metrics = self._update_performance_metrics()
        recent_alerts = [a for a in self.alerts if not a.acknowledged][-10:]  # Last 10 unacknowledged
        
        # Recent P&L (last 24 hours)
        recent_pnl = []
        cutoff_time = datetime.now() - timedelta(hours=24)
        for pnl_data in self.pnl_history:
            if pnl_data['timestamp'] >= cutoff_time:
                recent_pnl.append(pnl_data)
        
        return {
            'performance': {
                'daily_pnl': self.daily_pnl,
                'daily_pnl_pct': self.daily_pnl / self.starting_equity,
                'sharpe_ratio': current_metrics.sharpe_ratio,
                'max_drawdown': current_metrics.max_drawdown,
                'current_drawdown': self.current_drawdown,
                'hit_rate': current_metrics.hit_rate,
                'profit_factor': current_metrics.profit_factor,
                'total_trades': current_metrics.total_trades,
                'win_rate': current_metrics.win_rate
            },
            'alerts': {
                'critical_count': len([a for a in recent_alerts if a.level == AlertLevel.CRITICAL]),
                'high_count': len([a for a in recent_alerts if a.level == AlertLevel.HIGH]),
                'recent_alerts': [
                    {
                        'level': a.level.value,
                        'type': a.metric_type.value,
                        'message': a.message,
                        'timestamp': a.timestamp.isoformat()
                    }
                    for a in recent_alerts
                ]
            },
            'system': {
                'last_update': datetime.now().isoformat(),
                'data_points': len(self.pnl_history),
                'trade_count': len(self.trade_history),
                'alert_count': len(self.alerts)
            },
            'charts': {
                'pnl_curve': [
                    {
                        'timestamp': p['timestamp'].isoformat(),
                        'pnl': p['pnl'],
                        'equity': p['equity'],
                        'drawdown': p['drawdown']
                    }
                    for p in recent_pnl
                ]
            }
        }
    
    def get_performance_report(self, days_back: int = 30) -> Dict:
        """Generate detailed performance report"""
        
        cutoff_time = datetime.now() - timedelta(days=days_back)
        
        # Filter recent trades
        recent_trades = [
            t for t in self.trade_history 
            if t['timestamp'] >= cutoff_time
        ]
        
        if not recent_trades:
            return {'error': 'No trades in specified period'}
        
        # Calculate metrics
        pnls = [t['pnl'] for t in recent_trades]
        durations = [t['duration_min'] for t in recent_trades]
        z_scores = [abs(t['z_score']) for t in recent_trades if t['z_score'] != 0]
        
        winning_trades = [p for p in pnls if p > 0]
        losing_trades = [p for p in pnls if p < 0]
        
        report = {
            'period': f"{days_back} days",
            'trade_count': len(recent_trades),
            'total_pnl': sum(pnls),
            'avg_pnl_per_trade': np.mean(pnls),
            'win_rate': len(winning_trades) / len(recent_trades),
            'avg_winner': np.mean(winning_trades) if winning_trades else 0,
            'avg_loser': np.mean(losing_trades) if losing_trades else 0,
            'largest_winner': max(pnls) if pnls else 0,
            'largest_loser': min(pnls) if pnls else 0,
            'avg_duration_min': np.mean(durations) if durations else 0,
            'avg_entry_z_score': np.mean(z_scores) if z_scores else 0,
            'profit_factor': sum(winning_trades) / abs(sum(losing_trades)) if losing_trades else float('inf')
        }
        
        return report
    
    def acknowledge_alert(self, alert_timestamp: datetime):
        """Acknowledge an alert"""
        for alert in self.alerts:
            if alert.timestamp == alert_timestamp:
                alert.acknowledged = True
                logger.info(f"Alert acknowledged: {alert.message}")
                break
    
    def get_alert_summary(self) -> Dict:
        """Get summary of alert status"""
        
        recent_alerts = [a for a in self.alerts if a.timestamp >= datetime.now() - timedelta(hours=24)]
        unacknowledged = [a for a in recent_alerts if not a.acknowledged]
        
        return {
            'total_alerts_24h': len(recent_alerts),
            'unacknowledged': len(unacknowledged),
            'critical': len([a for a in unacknowledged if a.level == AlertLevel.CRITICAL]),
            'high': len([a for a in unacknowledged if a.level == AlertLevel.HIGH]),
            'medium': len([a for a in unacknowledged if a.level == AlertLevel.MEDIUM]),
            'low': len([a for a in unacknowledged if a.level == AlertLevel.LOW])
        }
    
    def export_metrics(self, filepath: str):
        """Export metrics to JSON file"""
        
        export_data = {
            'performance_metrics': self._update_performance_metrics().__dict__,
            'dashboard_data': self.get_dashboard_data(),
            'performance_report': self.get_performance_report(),
            'alert_summary': self.get_alert_summary(),
            'export_timestamp': datetime.now().isoformat()
        }
        
        with open(filepath, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)
        
        logger.info(f"Metrics exported to {filepath}")

# Example alert handlers
def email_alert_handler(alert: Alert):
    """Example email alert handler"""
    if alert.level in [AlertLevel.CRITICAL, AlertLevel.HIGH]:
        # Here you would integrate with email service
        logger.info(f"EMAIL ALERT: {alert.message}")

def slack_alert_handler(alert: Alert):
    """Example Slack alert handler"""
    if alert.level == AlertLevel.CRITICAL:
        # Here you would integrate with Slack API
        logger.info(f"SLACK ALERT: {alert.message}")

def sms_alert_handler(alert: Alert):
    """Example SMS alert handler"""
    if alert.level == AlertLevel.CRITICAL:
        # Here you would integrate with SMS service
        logger.info(f"SMS ALERT: {alert.message}")
