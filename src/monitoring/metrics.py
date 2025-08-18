"""
Prometheus metrics server
"""
import logging
from prometheus_client import Counter, Gauge, start_http_server

logger = logging.getLogger(__name__)

class MetricsServer:
    """Prometheus metrics server"""
    
    def __init__(self, port=9090):
        self.port = port
        
        # Define metrics
        self.trades_total = Counter('heston_trades_total', 'Total number of trades')
        self.positions_open = Gauge('heston_positions_open', 'Number of open positions')
        self.pnl_total = Gauge('heston_pnl_total', 'Total P&L')
        
        logger.info(f"Metrics server initialized on port {port}")
    
    def start(self):
        """Start the metrics server"""
        try:
            start_http_server(self.port)
            logger.info(f"Metrics server started at http://localhost:{self.port}/metrics")
        except Exception as e:
            logger.error(f"Failed to start metrics server: {e}")
    
    def update_positions(self, count: int):
        """Update positions gauge"""
        self.positions_open.set(count)
    
    def increment_trades(self):
        """Increment trades counter"""
        self.trades_total.inc()
    
    def update_pnl(self, pnl: float):
        """Update P&L gauge"""
        self.pnl_total.set(pnl)
