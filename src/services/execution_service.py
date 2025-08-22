"""
Execution Service
Unified interface for trade execution with order management and routing
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import uuid

from .base_service import BaseService, ServiceConfig

logger = logging.getLogger(__name__)

class OrderType(Enum):
    """Order types"""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"
    TRAILING_STOP = "trailing_stop"

class OrderSide(Enum):
    """Order side"""
    BUY = "buy"
    SELL = "sell"

class OrderStatus(Enum):
    """Order status"""
    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"

class TimeInForce(Enum):
    """Time in force"""
    DAY = "day"
    GTC = "gtc"  # Good Till Cancelled
    IOC = "ioc"  # Immediate or Cancel
    FOK = "fok"  # Fill or Kill

@dataclass
class OrderRequest:
    """Order request"""
    symbol: str
    side: OrderSide
    quantity: int
    order_type: OrderType
    price: Optional[float] = None
    stop_price: Optional[float] = None
    time_in_force: TimeInForce = TimeInForce.DAY
    
    # Order metadata
    strategy_id: Optional[str] = None
    parent_order_id: Optional[str] = None
    client_order_id: Optional[str] = None
    
    # Risk limits
    max_position_size: Optional[int] = None
    max_order_value: Optional[float] = None
    
    # Execution preferences
    allow_partial_fill: bool = True
    hidden_quantity: Optional[int] = None
    min_fill_size: Optional[int] = None
    
    def __post_init__(self):
        if self.client_order_id is None:
            self.client_order_id = str(uuid.uuid4())

@dataclass
class Order:
    """Order representation"""
    order_id: str
    client_order_id: str
    symbol: str
    side: OrderSide
    quantity: int
    order_type: OrderType
    status: OrderStatus
    
    # Prices
    price: Optional[float] = None
    stop_price: Optional[float] = None
    avg_fill_price: Optional[float] = 0.0
    
    # Execution details
    filled_quantity: int = 0
    remaining_quantity: int = 0
    time_in_force: TimeInForce = TimeInForce.DAY
    
    # Timestamps
    created_time: datetime = field(default_factory=datetime.now)
    submitted_time: Optional[datetime] = None
    last_update_time: datetime = field(default_factory=datetime.now)
    
    # Metadata
    strategy_id: Optional[str] = None
    parent_order_id: Optional[str] = None
    exchange: Optional[str] = None
    commission: float = 0.0
    
    # Fills
    fills: List[Dict[str, Any]] = field(default_factory=list)
    
    # Error information
    rejection_reason: Optional[str] = None
    error_message: Optional[str] = None
    
    def __post_init__(self):
        self.remaining_quantity = self.quantity - self.filled_quantity
    
    def is_active(self) -> bool:
        """Check if order is still active"""
        return self.status in [OrderStatus.PENDING, OrderStatus.SUBMITTED, OrderStatus.PARTIALLY_FILLED]
    
    def is_complete(self) -> bool:
        """Check if order is completely filled"""
        return self.status == OrderStatus.FILLED
    
    def add_fill(self, fill_quantity: int, fill_price: float, fill_time: datetime = None):
        """Add a fill to the order"""
        if fill_time is None:
            fill_time = datetime.now()
        
        # Create fill record
        fill = {
            'quantity': fill_quantity,
            'price': fill_price,
            'timestamp': fill_time,
            'fill_id': str(uuid.uuid4())
        }
        
        self.fills.append(fill)
        
        # Update order quantities
        self.filled_quantity += fill_quantity
        self.remaining_quantity = self.quantity - self.filled_quantity
        
        # Update average fill price
        if self.filled_quantity > 0:
            total_value = sum(f['quantity'] * f['price'] for f in self.fills)
            self.avg_fill_price = total_value / self.filled_quantity
        
        # Update status
        if self.remaining_quantity <= 0:
            self.status = OrderStatus.FILLED
        elif self.filled_quantity > 0:
            self.status = OrderStatus.PARTIALLY_FILLED
        
        self.last_update_time = fill_time

@dataclass
class ExecutionReport:
    """Execution report for order updates"""
    order_id: str
    client_order_id: str
    symbol: str
    status: OrderStatus
    
    # Execution details
    filled_quantity: int = 0
    avg_fill_price: float = 0.0
    last_fill_quantity: int = 0
    last_fill_price: float = 0.0
    
    # Timestamps
    timestamp: datetime = field(default_factory=datetime.now)
    
    # Additional info
    exchange: Optional[str] = None
    commission: float = 0.0
    error_message: Optional[str] = None

class ExecutionService(BaseService):
    """
    Execution Service providing unified trade execution
    with order management, routing, and monitoring
    """
    
    def __init__(self, config: ServiceConfig, strategy_config: Dict[str, Any]):
        super().__init__(config)
        
        self.strategy_config = strategy_config
        self.execution_config = strategy_config.get('execution', {})
        
        # Order management
        self.orders: Dict[str, Order] = {}  # order_id -> Order
        self.client_orders: Dict[str, Order] = {}  # client_order_id -> Order
        self.strategy_orders: Dict[str, List[str]] = {}  # strategy_id -> [order_ids]
        
        # Execution engines/brokers
        self.execution_engines: Dict[str, Any] = {}  # name -> engine
        self.default_engine: Optional[str] = None
        
        # Order routing
        self.routing_rules: List[Dict[str, Any]] = []
        self.execution_venues: List[str] = []
        
        # Risk controls
        self.position_limits: Dict[str, int] = {}  # symbol -> max_position
        self.daily_limits: Dict[str, float] = {}   # symbol -> max_daily_value
        self.daily_volumes: Dict[str, float] = {}  # symbol -> today's volume
        
        # Performance tracking
        self.execution_stats = {
            'total_orders': 0,
            'filled_orders': 0,
            'cancelled_orders': 0,
            'rejected_orders': 0,
            'avg_fill_time_ms': 0.0,
            'fill_rate': 0.0,
            'total_commission': 0.0,
            'total_volume': 0.0
        }
        
        # Event callbacks
        self.order_callbacks: List[Callable] = []
        self.fill_callbacks: List[Callable] = []
        self.rejection_callbacks: List[Callable] = []
        
        # Configuration
        self.enable_risk_checks = self.execution_config.get('enable_risk_checks', True)
        self.max_order_value = self.execution_config.get('max_order_value', 100000)
        self.max_daily_volume = self.execution_config.get('max_daily_volume', 1000000)
        self.commission_rate = self.execution_config.get('commission_rate', 0.001)
        
        # Order processing
        self.order_queue = asyncio.Queue()
        self.order_counter = 0
        
        logger.info("Execution Service initialized")
    
    async def _initialize(self) -> bool:
        """Initialize execution engines and connections"""
        try:
            # Initialize execution engines
            engines_config = self.execution_config.get('engines', {})
            
            for engine_name, engine_config in engines_config.items():
                try:
                    # In production, this would initialize actual broker connections
                    # For now, we'll create mock engines
                    engine = self._create_execution_engine(engine_name, engine_config)
                    if engine:
                        self.execution_engines[engine_name] = engine
                        logger.info(f"Execution engine {engine_name} initialized")
                        
                        # Set default engine
                        if not self.default_engine or engine_config.get('default', False):
                            self.default_engine = engine_name
                            
                except Exception as e:
                    logger.error(f"Failed to initialize execution engine {engine_name}: {e}")
            
            # Load routing rules
            self.routing_rules = self.execution_config.get('routing_rules', [])
            
            # Load position limits
            self.position_limits = self.execution_config.get('position_limits', {})
            self.daily_limits = self.execution_config.get('daily_limits', {})
            
            logger.info(f"Execution service initialized with {len(self.execution_engines)} engines")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize execution service: {e}")
            return False
    
    async def _start(self) -> bool:
        """Start execution service"""
        try:
            # Start order processing
            self.create_task(self._process_order_queue())
            
            # Start daily reset timer
            self.create_task(self._daily_reset_loop())
            
            # Start order monitoring
            self.create_task(self._monitor_orders())
            
            logger.info("Execution service started")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start execution service: {e}")
            return False
    
    async def _stop(self) -> bool:
        """Stop execution service"""
        try:
            # Cancel all active orders
            active_orders = [order for order in self.orders.values() if order.is_active()]
            if active_orders:
                logger.info(f"Cancelling {len(active_orders)} active orders")
                for order in active_orders:
                    await self.cancel_order(order.order_id)
            
            # Disconnect execution engines
            for engine_name, engine in self.execution_engines.items():
                try:
                    # In production, disconnect from broker
                    logger.info(f"Disconnecting execution engine {engine_name}")
                except Exception as e:
                    logger.warning(f"Error disconnecting engine {engine_name}: {e}")
            
            logger.info("Execution service stopped")
            return True
            
        except Exception as e:
            logger.error(f"Error stopping execution service: {e}")
            return False
    
    async def _health_check(self) -> Dict[str, Any]:
        """Perform health check"""
        active_orders = len([o for o in self.orders.values() if o.is_active()])
        
        health_data = {
            'execution_engines': {
                'total': len(self.execution_engines),
                'connected': len(self.execution_engines),  # Simplified
                'default_engine': self.default_engine
            },
            'orders': {
                'total': len(self.orders),
                'active': active_orders,
                'queue_depth': self.order_queue.qsize()
            },
            'performance': {
                'fill_rate': self.execution_stats['fill_rate'],
                'avg_fill_time_ms': self.execution_stats['avg_fill_time_ms'],
                'total_volume': self.execution_stats['total_volume']
            },
            'risk_controls': {
                'enabled': self.enable_risk_checks,
                'daily_volume_used': sum(self.daily_volumes.values()),
                'max_daily_volume': self.max_daily_volume
            }
        }
        
        return health_data
    
    async def submit_order(self, request: OrderRequest) -> str:
        """
        Submit a new order
        
        Args:
            request: Order request
            
        Returns:
            Order ID
        """
        try:
            # Generate order ID
            self.order_counter += 1
            order_id = f"ORDER_{self.order_counter}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Create order
            order = Order(
                order_id=order_id,
                client_order_id=request.client_order_id,
                symbol=request.symbol,
                side=request.side,
                quantity=request.quantity,
                order_type=request.order_type,
                status=OrderStatus.PENDING,
                price=request.price,
                stop_price=request.stop_price,
                time_in_force=request.time_in_force,
                strategy_id=request.strategy_id,
                parent_order_id=request.parent_order_id
            )
            
            # Risk checks
            if self.enable_risk_checks:
                risk_check_result = await self._perform_risk_checks(order, request)
                if not risk_check_result['allowed']:
                    order.status = OrderStatus.REJECTED
                    order.rejection_reason = risk_check_result['reason']
                    order.error_message = risk_check_result['message']
                    
                    # Store rejected order
                    self.orders[order_id] = order
                    self.client_orders[order.client_order_id] = order
                    
                    # Update stats
                    self.execution_stats['rejected_orders'] += 1
                    
                    # Call rejection callbacks
                    await self._call_rejection_callbacks(order)
                    
                    logger.warning(f"Order {order_id} rejected: {risk_check_result['reason']}")
                    return order_id
            
            # Store order
            self.orders[order_id] = order
            self.client_orders[order.client_order_id] = order
            
            # Track by strategy
            if order.strategy_id:
                if order.strategy_id not in self.strategy_orders:
                    self.strategy_orders[order.strategy_id] = []
                self.strategy_orders[order.strategy_id].append(order_id)
            
            # Route and submit order
            await self._route_and_submit_order(order)
            
            logger.info(f"Order {order_id} submitted: {request.side.value} {request.quantity} {request.symbol}")
            return order_id
            
        except Exception as e:
            logger.error(f"Error submitting order: {e}")
            raise
    
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an order"""
        try:
            order = self.orders.get(order_id)
            if not order:
                logger.warning(f"Order {order_id} not found")
                return False
            
            if not order.is_active():
                logger.warning(f"Order {order_id} is not active (status: {order.status.value})")
                return False
            
            # Update order status
            order.status = OrderStatus.CANCELLED
            order.last_update_time = datetime.now()
            
            # In production, would send cancel request to broker
            await self._send_cancel_to_engine(order)
            
            # Update stats
            self.execution_stats['cancelled_orders'] += 1
            
            # Call order callbacks
            await self._call_order_callbacks(order)
            
            logger.info(f"Order {order_id} cancelled")
            return True
            
        except Exception as e:
            logger.error(f"Error cancelling order {order_id}: {e}")
            return False
    
    async def modify_order(self, order_id: str, new_price: Optional[float] = None, 
                          new_quantity: Optional[int] = None) -> bool:
        """Modify an existing order"""
        try:
            order = self.orders.get(order_id)
            if not order:
                logger.warning(f"Order {order_id} not found")
                return False
            
            if not order.is_active():
                logger.warning(f"Order {order_id} is not active")
                return False
            
            # Update order details
            if new_price is not None:
                order.price = new_price
            
            if new_quantity is not None:
                if new_quantity < order.filled_quantity:
                    logger.warning(f"Cannot reduce quantity below filled amount")
                    return False
                order.quantity = new_quantity
                order.remaining_quantity = new_quantity - order.filled_quantity
            
            order.last_update_time = datetime.now()
            
            # In production, would send modify request to broker
            await self._send_modify_to_engine(order)
            
            logger.info(f"Order {order_id} modified")
            return True
            
        except Exception as e:
            logger.error(f"Error modifying order {order_id}: {e}")
            return False
    
    def get_order(self, order_id: str) -> Optional[Order]:
        """Get order by ID"""
        return self.orders.get(order_id)
    
    def get_order_by_client_id(self, client_order_id: str) -> Optional[Order]:
        """Get order by client ID"""
        return self.client_orders.get(client_order_id)
    
    def get_orders_by_strategy(self, strategy_id: str) -> List[Order]:
        """Get all orders for a strategy"""
        order_ids = self.strategy_orders.get(strategy_id, [])
        return [self.orders[oid] for oid in order_ids if oid in self.orders]
    
    def get_active_orders(self, symbol: Optional[str] = None) -> List[Order]:
        """Get all active orders, optionally filtered by symbol"""
        orders = [order for order in self.orders.values() if order.is_active()]
        if symbol:
            orders = [order for order in orders if order.symbol == symbol]
        return orders
    
    def get_filled_orders(self, symbol: Optional[str] = None, 
                         start_date: Optional[datetime] = None) -> List[Order]:
        """Get all filled orders"""
        orders = [order for order in self.orders.values() if order.is_complete()]
        if symbol:
            orders = [order for order in orders if order.symbol == symbol]
        if start_date:
            orders = [order for order in orders if order.last_update_time >= start_date]
        return orders
    
    def add_order_callback(self, callback: Callable):
        """Add callback for order events"""
        self.order_callbacks.append(callback)
    
    def add_fill_callback(self, callback: Callable):
        """Add callback for fill events"""
        self.fill_callbacks.append(callback)
    
    def add_rejection_callback(self, callback: Callable):
        """Add callback for rejection events"""
        self.rejection_callbacks.append(callback)
    
    # Internal methods
    
    def _create_execution_engine(self, name: str, config: Dict[str, Any]):
        """Create execution engine - mock implementation"""
        # In production, this would create actual broker connections
        return {
            'name': name,
            'config': config,
            'connected': True,
            'type': config.get('type', 'mock')
        }
    
    async def _perform_risk_checks(self, order: Order, request: OrderRequest) -> Dict[str, Any]:
        """Perform pre-trade risk checks"""
        try:
            # Position size check
            if request.max_position_size:
                current_position = await self._get_current_position(order.symbol)
                new_position = current_position + (order.quantity if order.side == OrderSide.BUY else -order.quantity)
                if abs(new_position) > request.max_position_size:
                    return {
                        'allowed': False,
                        'reason': 'position_limit_exceeded',
                        'message': f'Position limit exceeded: {abs(new_position)} > {request.max_position_size}'
                    }
            
            # Order value check
            if order.price:
                order_value = order.quantity * order.price
                if order_value > self.max_order_value:
                    return {
                        'allowed': False,
                        'reason': 'order_value_exceeded',
                        'message': f'Order value exceeded: {order_value} > {self.max_order_value}'
                    }
            
            # Daily volume check
            if request.max_order_value:
                order_value = order.quantity * (order.price or 100)  # Estimate for market orders
                current_daily = self.daily_volumes.get(order.symbol, 0)
                if current_daily + order_value > request.max_order_value:
                    return {
                        'allowed': False,
                        'reason': 'daily_volume_exceeded',
                        'message': f'Daily volume limit exceeded'
                    }
            
            # Global daily volume check
            total_daily = sum(self.daily_volumes.values())
            if order.price:
                order_value = order.quantity * order.price
                if total_daily + order_value > self.max_daily_volume:
                    return {
                        'allowed': False,
                        'reason': 'global_daily_limit_exceeded',
                        'message': f'Global daily volume limit exceeded'
                    }
            
            return {'allowed': True}
            
        except Exception as e:
            logger.error(f"Error in risk checks: {e}")
            return {
                'allowed': False,
                'reason': 'risk_check_error',
                'message': f'Risk check failed: {e}'
            }
    
    async def _get_current_position(self, symbol: str) -> int:
        """Get current position for symbol"""
        # Calculate net position from filled orders
        position = 0
        for order in self.orders.values():
            if order.symbol == symbol and order.is_complete():
                if order.side == OrderSide.BUY:
                    position += order.filled_quantity
                else:
                    position -= order.filled_quantity
        return position
    
    async def _route_and_submit_order(self, order: Order):
        """Route and submit order to appropriate execution engine"""
        try:
            # Determine execution venue
            venue = await self._determine_execution_venue(order)
            
            # Submit to execution engine
            engine = self.execution_engines.get(venue or self.default_engine)
            if not engine:
                raise Exception(f"No execution engine available for venue {venue}")
            
            # Update order status
            order.status = OrderStatus.SUBMITTED
            order.submitted_time = datetime.now()
            order.exchange = venue
            
            # In production, would submit to actual broker
            await self._simulate_order_execution(order)
            
            # Update stats
            self.execution_stats['total_orders'] += 1
            
            # Call order callbacks
            await self._call_order_callbacks(order)
            
        except Exception as e:
            logger.error(f"Error routing/submitting order {order.order_id}: {e}")
            order.status = OrderStatus.REJECTED
            order.error_message = str(e)
            await self._call_rejection_callbacks(order)
    
    async def _determine_execution_venue(self, order: Order) -> Optional[str]:
        """Determine best execution venue for order"""
        # Apply routing rules
        for rule in self.routing_rules:
            if self._matches_routing_rule(order, rule):
                return rule.get('venue')
        
        # Default venue
        return self.default_engine
    
    def _matches_routing_rule(self, order: Order, rule: Dict[str, Any]) -> bool:
        """Check if order matches routing rule"""
        # Symbol matching
        if 'symbols' in rule:
            if order.symbol not in rule['symbols']:
                return False
        
        # Order type matching
        if 'order_types' in rule:
            if order.order_type.value not in rule['order_types']:
                return False
        
        # Quantity matching
        if 'min_quantity' in rule:
            if order.quantity < rule['min_quantity']:
                return False
        
        if 'max_quantity' in rule:
            if order.quantity > rule['max_quantity']:
                return False
        
        return True
    
    async def _simulate_order_execution(self, order: Order):
        """Simulate order execution - for testing purposes"""
        try:
            # Simulate execution delay
            await asyncio.sleep(0.1)
            
            # For market orders, simulate immediate fill
            if order.order_type == OrderType.MARKET:
                # Simulate fill at market price (simplified)
                fill_price = order.price or 100.0  # Mock price
                fill_time = datetime.now()
                
                order.add_fill(order.quantity, fill_price, fill_time)
                order.commission = order.filled_quantity * fill_price * self.commission_rate
                
                # Update daily volume
                order_value = order.filled_quantity * fill_price
                if order.symbol not in self.daily_volumes:
                    self.daily_volumes[order.symbol] = 0
                self.daily_volumes[order.symbol] += order_value
                
                # Update stats
                self.execution_stats['filled_orders'] += 1
                self.execution_stats['total_commission'] += order.commission
                self.execution_stats['total_volume'] += order_value
                
                # Calculate fill rate
                if self.execution_stats['total_orders'] > 0:
                    self.execution_stats['fill_rate'] = (
                        self.execution_stats['filled_orders'] / self.execution_stats['total_orders']
                    )
                
                # Call fill callbacks
                await self._call_fill_callbacks(order)
                await self._call_order_callbacks(order)
                
                logger.info(f"Order {order.order_id} filled: {order.filled_quantity}@{fill_price}")
            
            # For limit orders, simulate partial logic (simplified)
            else:
                # In reality, would depend on market conditions
                # For now, just mark as submitted
                pass
                
        except Exception as e:
            logger.error(f"Error simulating execution for order {order.order_id}: {e}")
            order.status = OrderStatus.REJECTED
            order.error_message = str(e)
    
    async def _send_cancel_to_engine(self, order: Order):
        """Send cancel request to execution engine"""
        # In production, would send actual cancel request
        logger.info(f"Cancel request sent for order {order.order_id}")
    
    async def _send_modify_to_engine(self, order: Order):
        """Send modify request to execution engine"""
        # In production, would send actual modify request
        logger.info(f"Modify request sent for order {order.order_id}")
    
    async def _call_order_callbacks(self, order: Order):
        """Call order event callbacks"""
        for callback in self.order_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(order)
                else:
                    callback(order)
            except Exception as e:
                logger.error(f"Error in order callback: {e}")
    
    async def _call_fill_callbacks(self, order: Order):
        """Call fill event callbacks"""
        for callback in self.fill_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(order)
                else:
                    callback(order)
            except Exception as e:
                logger.error(f"Error in fill callback: {e}")
    
    async def _call_rejection_callbacks(self, order: Order):
        """Call rejection event callbacks"""
        for callback in self.rejection_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(order)
                else:
                    callback(order)
            except Exception as e:
                logger.error(f"Error in rejection callback: {e}")
    
    async def _process_order_queue(self):
        """Process queued orders"""
        try:
            while not self._shutdown_event.is_set():
                await asyncio.sleep(0.1)  # Process any queued orders
        except asyncio.CancelledError:
            logger.debug("Order queue processor cancelled")
        except Exception as e:
            logger.error(f"Error in order queue processor: {e}")
    
    async def _daily_reset_loop(self):
        """Reset daily counters at market open"""
        try:
            while not self._shutdown_event.is_set():
                try:
                    # Reset daily volumes (simplified - would use actual market hours)
                    now = datetime.now()
                    if now.hour == 0 and now.minute == 0:  # Midnight reset
                        self.daily_volumes.clear()
                        logger.info("Daily volume counters reset")
                    
                except Exception as e:
                    logger.error(f"Error in daily reset: {e}")
                
                # Wait for next check
                try:
                    await asyncio.wait_for(
                        self._shutdown_event.wait(),
                        timeout=60  # Check every minute
                    )
                    break
                except asyncio.TimeoutError:
                    continue
                    
        except asyncio.CancelledError:
            logger.debug("Daily reset loop cancelled")
        except Exception as e:
            logger.error(f"Error in daily reset loop: {e}")
    
    async def _monitor_orders(self):
        """Monitor order status and handle timeouts"""
        try:
            while not self._shutdown_event.is_set():
                try:
                    current_time = datetime.now()
                    
                    # Check for expired orders
                    for order in self.orders.values():
                        if order.is_active() and order.time_in_force == TimeInForce.DAY:
                            # Check if market is closed (simplified)
                            if current_time.hour >= 16:  # After 4 PM
                                order.status = OrderStatus.EXPIRED
                                order.last_update_time = current_time
                                await self._call_order_callbacks(order)
                    
                except Exception as e:
                    logger.error(f"Error monitoring orders: {e}")
                
                # Wait for next monitoring cycle
                try:
                    await asyncio.wait_for(
                        self._shutdown_event.wait(),
                        timeout=30  # Monitor every 30 seconds
                    )
                    break
                except asyncio.TimeoutError:
                    continue
                    
        except asyncio.CancelledError:
            logger.debug("Order monitor cancelled")
        except Exception as e:
            logger.error(f"Error in order monitor: {e}")
    
    def get_service_metrics(self) -> Dict[str, Any]:
        """Get detailed service metrics"""
        return {
            'execution_stats': self.execution_stats.copy(),
            'order_stats': {
                'total_orders': len(self.orders),
                'active_orders': len([o for o in self.orders.values() if o.is_active()]),
                'filled_orders': len([o for o in self.orders.values() if o.is_complete()]),
                'strategies_active': len(self.strategy_orders)
            },
            'risk_controls': {
                'enabled': self.enable_risk_checks,
                'position_limits': len(self.position_limits),
                'daily_volume_used': sum(self.daily_volumes.values()),
                'max_daily_volume': self.max_daily_volume
            },
            'execution_engines': {
                'total': len(self.execution_engines),
                'default': self.default_engine,
                'routing_rules': len(self.routing_rules)
            }
        }