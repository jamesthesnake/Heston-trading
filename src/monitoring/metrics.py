"""
Enhanced Prometheus metrics server with comprehensive strategy integration
"""
import logging
from prometheus_client import Counter, Gauge, Histogram, start_http_server

# Import comprehensive monitoring system
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from strategy.monitoring_system import MonitoringSystem

logger = logging.getLogger(__name__)

class MetricsServer:
    """Enhanced Prometheus metrics server with comprehensive strategy metrics"""
    
    def __init__(self, monitoring_system=None, port=9090):
        self.port = port
        self.monitoring_system = monitoring_system
        
        # Define comprehensive metrics
        self._setup_metrics()
        
        logger.info(f"Enhanced Metrics server initialized on port {port}")
    
    def _setup_metrics(self):
        """Setup comprehensive Prometheus metrics"""
        
        # Trading metrics
        self.trades_total = Counter('heston_trades_total', 'Total number of trades', ['side', 'outcome'])
        self.positions_open = Gauge('heston_positions_open', 'Number of open positions')
        self.pnl_total = Gauge('heston_pnl_total', 'Total P&L')
        self.daily_pnl = Gauge('heston_daily_pnl', 'Daily P&L')
        
        # Performance metrics
        self.sharpe_ratio = Gauge('heston_sharpe_ratio', 'Sharpe ratio')
        self.hit_rate = Gauge('heston_hit_rate', 'Hit rate percentage')
        self.max_drawdown = Gauge('heston_max_drawdown', 'Maximum drawdown')
        self.current_drawdown = Gauge('heston_current_drawdown', 'Current drawdown')
        
        # Risk metrics
        self.portfolio_delta = Gauge('heston_portfolio_delta', 'Portfolio delta exposure')
        self.portfolio_gamma = Gauge('heston_portfolio_gamma', 'Portfolio gamma exposure')
        self.portfolio_vega = Gauge('heston_portfolio_vega', 'Portfolio vega exposure')
        self.portfolio_theta = Gauge('heston_portfolio_theta', 'Portfolio theta exposure')
        self.risk_level = Gauge('heston_risk_level', 'Current risk level (0=normal, 1=soft_stop, 2=hard_stop, 3=emergency)')
        
        # Model metrics
        self.calibration_rmse = Gauge('heston_calibration_rmse', 'Heston model calibration RMSE')
        self.calibration_age = Gauge('heston_calibration_age_seconds', 'Age of current calibration in seconds')
        self.signal_count = Gauge('heston_active_signals', 'Number of active trading signals')
        
        # System metrics
        self.alerts_total = Counter('heston_alerts_total', 'Total alerts generated', ['level', 'type'])
        self.data_staleness = Gauge('heston_data_staleness_seconds', 'Market data staleness in seconds')
        self.execution_latency = Histogram('heston_execution_latency_seconds', 'Order execution latency')
        
        # Market metrics
        self.vix_level = Gauge('heston_vix_level', 'VIX level')
        self.spx_price = Gauge('heston_spx_price', 'SPX price')
        self.implied_vol_surface_quality = Gauge('heston_iv_surface_quality', 'IV surface data quality score')
    
    def start(self):
        """Start the enhanced metrics server"""
        try:
            start_http_server(self.port)
            logger.info(f"Enhanced Metrics server started at http://localhost:{self.port}/metrics")
        except Exception as e:
            logger.error(f"Failed to start metrics server: {e}")
    
    def update_from_monitoring_system(self):
        """Update all metrics from comprehensive monitoring system"""
        if not self.monitoring_system:
            return
        
        try:
            # Get comprehensive data
            dashboard_data = self.monitoring_system.get_dashboard_data()
            
            # Update performance metrics
            perf = dashboard_data['performance']
            self.pnl_total.set(perf['total_pnl'])
            self.daily_pnl.set(perf['daily_pnl'])
            self.sharpe_ratio.set(perf['sharpe_ratio'])
            self.hit_rate.set(perf['hit_rate'] * 100)  # Convert to percentage
            self.max_drawdown.set(perf['max_drawdown'])
            self.current_drawdown.set(perf['current_drawdown'])
            
            # Update risk metrics
            risk = dashboard_data['risk']
            self.portfolio_delta.set(risk['portfolio_delta'])
            self.portfolio_gamma.set(risk['portfolio_gamma'])
            self.portfolio_vega.set(risk['portfolio_vega'])
            self.portfolio_theta.set(risk['portfolio_theta'])
            
            # Map risk level to numeric
            risk_level_map = {'normal': 0, 'soft_stop': 1, 'hard_stop': 2, 'emergency': 3}
            self.risk_level.set(risk_level_map.get(risk['risk_level'], 0))
            
            # Update system metrics
            system = dashboard_data['system']
            self.positions_open.set(system['position_count'])
            self.data_staleness.set(system.get('data_staleness_seconds', 0))
            
            # Update model metrics if available
            if 'model' in dashboard_data:
                model = dashboard_data['model']
                self.calibration_rmse.set(model.get('calibration_rmse', 0))
                self.calibration_age.set(model.get('calibration_age_seconds', 0))
                self.signal_count.set(model.get('active_signals', 0))
            
            # Update market metrics if available
            if 'market' in dashboard_data:
                market = dashboard_data['market']
                self.vix_level.set(market.get('vix', 0))
                self.spx_price.set(market.get('spx_price', 0))
                self.implied_vol_surface_quality.set(market.get('iv_quality', 0))
                
        except Exception as e:
            logger.error(f"Error updating metrics from monitoring system: {e}")
    
    # Legacy methods for backward compatibility
    def update_positions(self, count: int):
        """Update positions gauge - legacy method"""
        self.positions_open.set(count)
    
    def increment_trades(self, side='unknown', outcome='unknown'):
        """Increment trades counter - enhanced legacy method"""
        self.trades_total.labels(side=side, outcome=outcome).inc()
    
    def update_pnl(self, pnl: float):
        """Update P&L gauge - legacy method"""
        self.pnl_total.set(pnl)
    
    # New enhanced methods
    def record_execution_latency(self, latency_seconds: float):
        """Record order execution latency"""
        self.execution_latency.observe(latency_seconds)
    
    def increment_alert(self, level: str, alert_type: str):
        """Increment alert counter"""
        self.alerts_total.labels(level=level, type=alert_type).inc()
    
    def set_monitoring_system(self, monitoring_system: MonitoringSystem):
        """Set the monitoring system for enhanced metrics"""
        self.monitoring_system = monitoring_system
        logger.info("Monitoring system connected to metrics server")
