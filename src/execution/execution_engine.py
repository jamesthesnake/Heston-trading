"""
Execution Engine for trade execution
"""
import logging
from typing import Dict, Optional
from .order_manager import OrderManager, Order, OrderType

logger = logging.getLogger(__name__)

class ExecutionEngine:
    """Handles trade execution logic"""
    
    def __init__(self, config: dict):
        self.config = config
        self.order_manager = OrderManager(config)
        self.execution_config = config.get('execution', {})
        
        logger.info("ExecutionEngine initialized")
    
    def execute_trade(self, signal: dict) -> Optional[str]:
        """Execute a trade based on signal"""
        logger.info(f"Executing trade for signal: {signal}")
        
        # Create order from signal
        order = self._create_order_from_signal(signal)
        
        if order:
            # Set price for limit orders
            if order.order_type == OrderType.LIMIT:
                order.price = signal.get('target_price', 100.0)
            
            # Submit order
            if self.order_manager.submit_order(order):
                return order.id
        
        return None
    
    def _create_order_from_signal(self, signal: dict) -> Optional[Order]:
        """Create order from trading signal"""
        symbol = signal.get('symbol')
        quantity = signal.get('quantity', 0)
        
        if not symbol or quantity == 0:
            logger.warning("Invalid signal: missing symbol or quantity")
            return None
        
        # Determine order type
        order_type_str = self.execution_config.get('order_type', 'limit').upper()
        order_type = OrderType.LIMIT if order_type_str == 'LIMIT' else OrderType.MARKET
        
        order = Order(symbol, quantity, order_type)
        return order
    
    def close_position(self, position: dict) -> Optional[str]:
        """Close an existing position"""
        # Create opposite order to close
        signal = {
            'symbol': position['symbol'],
            'quantity': -position['quantity'],  # Opposite direction
            'target_price': position.get('current_price', 100.0)
        }
        
        return self.execute_trade(signal)
    
    def cancel_all_orders(self):
        """Cancel all open orders"""
        open_orders = self.order_manager.get_open_orders()
        for order in open_orders:
            self.order_manager.cancel_order(order.id)
        
        logger.info(f"Cancelled {len(open_orders)} orders")
