"""
Order Management System
"""
import logging
from typing import Dict, List, Optional
from datetime import datetime
from enum import Enum
import uuid

logger = logging.getLogger(__name__)

class OrderStatus(Enum):
    PENDING = "PENDING"
    SUBMITTED = "SUBMITTED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"

class OrderType(Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"

class Order:
    """Order representation"""
    
    def __init__(self, symbol: str, quantity: int, order_type: OrderType = OrderType.LIMIT):
        self.id = str(uuid.uuid4())
        self.symbol = symbol
        self.quantity = quantity
        self.order_type = order_type
        self.status = OrderStatus.PENDING
        self.price = None
        self.filled_price = None
        self.timestamp = datetime.now()
        self.fill_time = None
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'symbol': self.symbol,
            'quantity': self.quantity,
            'type': self.order_type.value,
            'status': self.status.value,
            'price': self.price,
            'filled_price': self.filled_price,
            'timestamp': self.timestamp.isoformat()
        }

class OrderManager:
    """Manages order execution"""
    
    def __init__(self, config: dict):
        self.config = config
        self.orders = {}
        self.filled_orders = []
        self.use_mock = config.get('data', {}).get('use_mock', False)
        
        logger.info(f"OrderManager initialized (mock={self.use_mock})")
    
    def submit_order(self, order: Order) -> bool:
        """Submit an order"""
        logger.info(f"Submitting order: {order.symbol} qty={order.quantity}")
        
        if self.use_mock:
            # Mock execution
            order.status = OrderStatus.SUBMITTED
            self.orders[order.id] = order
            
            # Simulate immediate fill for mock
            self._mock_fill_order(order)
            return True
        else:
            # Real IB execution would go here
            order.status = OrderStatus.SUBMITTED
            self.orders[order.id] = order
            return True
    
    def _mock_fill_order(self, order: Order):
        """Mock order fill"""
        import random
        import time
        
        # Simulate some delay
        time.sleep(random.uniform(0.1, 0.5))
        
        # Mock fill
        order.status = OrderStatus.FILLED
        order.filled_price = order.price if order.price else 100.0
        order.fill_time = datetime.now()
        
        self.filled_orders.append(order)
        logger.info(f"Order filled: {order.id} at {order.filled_price}")
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order"""
        if order_id in self.orders:
            order = self.orders[order_id]
            if order.status in [OrderStatus.PENDING, OrderStatus.SUBMITTED]:
                order.status = OrderStatus.CANCELLED
                logger.info(f"Order cancelled: {order_id}")
                return True
        return False
    
    def get_open_orders(self) -> List[Order]:
        """Get all open orders"""
        return [o for o in self.orders.values() 
                if o.status in [OrderStatus.PENDING, OrderStatus.SUBMITTED]]
    
    def get_order_status(self, order_id: str) -> Optional[OrderStatus]:
        """Get order status"""
        if order_id in self.orders:
            return self.orders[order_id].status
        return None
