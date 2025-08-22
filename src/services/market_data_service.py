"""
Market Data Service
Unified interface for market data access with caching and failover support
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, asdict
from collections import defaultdict

from .base_service import BaseService, ServiceConfig, ServiceStatus
from ..data.providers.base_provider import DataProvider
from ..data.providers.provider_factory import DataProviderFactory

logger = logging.getLogger(__name__)

@dataclass
class MarketDataRequest:
    """Market data request"""
    symbols: List[str]
    data_types: List[str]  # ['quotes', 'greeks', 'chains', 'historicals']
    priority: int = 1  # Higher = more priority
    timeout: float = 5.0
    use_cache: bool = True
    max_age_seconds: int = 30

@dataclass 
class MarketDataResponse:
    """Market data response"""
    request_id: str
    symbols: List[str]
    data: Dict[str, Any]
    timestamp: datetime
    source_provider: str
    cache_hit: bool = False
    latency_ms: float = 0.0
    errors: List[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []

class MarketDataService(BaseService):
    """
    Market Data Service providing unified access to market data
    with caching, failover, and performance optimization
    """
    
    def __init__(self, config: ServiceConfig, strategy_config: Dict[str, Any]):
        super().__init__(config)
        
        self.strategy_config = strategy_config
        self.market_config = strategy_config.get('market_data', {})
        
        # Provider management
        self.primary_provider: Optional[DataProvider] = None
        self.fallback_providers: List[DataProvider] = []
        self.provider_factory = DataProviderFactory()
        
        # Caching
        self.cache_enabled = self.market_config.get('enable_cache', True)
        self.cache_duration = self.market_config.get('cache_duration', 30)  # seconds
        self.data_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_timestamps: Dict[str, datetime] = {}
        
        # Request management
        self.request_queue = asyncio.Queue()
        self.active_requests: Dict[str, MarketDataRequest] = {}
        self.request_counter = 0
        
        # Performance tracking
        self.request_stats = {
            'total_requests': 0,
            'cache_hits': 0,
            'provider_failures': 0,
            'avg_latency_ms': 0.0,
            'requests_per_second': 0.0
        }
        self.request_history = []
        
        # Subscription management
        self.active_subscriptions: Dict[str, Set[str]] = defaultdict(set)  # symbol -> data_types
        self.subscription_callbacks: Dict[str, List] = defaultdict(list)  # symbol -> callbacks
        
        # Configuration
        self.max_concurrent_requests = self.market_config.get('max_concurrent_requests', 10)
        self.request_timeout = self.market_config.get('request_timeout', 5.0)
        self.failover_threshold = self.market_config.get('failover_threshold', 3)
        self.provider_failure_counts: Dict[str, int] = defaultdict(int)
        
        logger.info(f"Market Data Service initialized with cache={self.cache_enabled}")
    
    async def _initialize(self) -> bool:
        """Initialize market data providers"""
        try:
            # Initialize primary provider
            primary_config = self.market_config.get('primary_provider', {})
            self.primary_provider = self.provider_factory.create_provider(
                primary_config.get('type', 'mock'),
                primary_config
            )
            
            if not await self.primary_provider.connect():
                logger.error("Failed to connect primary market data provider")
                return False
            
            # Initialize fallback providers
            fallback_configs = self.market_config.get('fallback_providers', [])
            for fb_config in fallback_configs:
                try:
                    provider = self.provider_factory.create_provider(
                        fb_config.get('type', 'mock'),
                        fb_config
                    )
                    if await provider.connect():
                        self.fallback_providers.append(provider)
                        logger.info(f"Fallback provider {fb_config.get('type')} connected")
                except Exception as e:
                    logger.warning(f"Failed to initialize fallback provider: {e}")
            
            logger.info(f"Market data service initialized with {len(self.fallback_providers)} fallback providers")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize market data service: {e}")
            return False
    
    async def _start(self) -> bool:
        """Start market data processing"""
        try:
            # Start request processing task
            self.create_task(self._process_request_queue())
            
            # Start cache cleanup task
            if self.cache_enabled:
                self.create_task(self._cache_cleanup_loop())
            
            # Start performance monitoring
            self.create_task(self._performance_monitor_loop())
            
            logger.info("Market data service started")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start market data service: {e}")
            return False
    
    async def _stop(self) -> bool:
        """Stop market data service"""
        try:
            # Disconnect providers
            if self.primary_provider:
                await self.primary_provider.disconnect()
            
            for provider in self.fallback_providers:
                try:
                    await provider.disconnect()
                except Exception as e:
                    logger.warning(f"Error disconnecting fallback provider: {e}")
            
            # Clear caches
            self.data_cache.clear()
            self.cache_timestamps.clear()
            self.active_subscriptions.clear()
            
            logger.info("Market data service stopped")
            return True
            
        except Exception as e:
            logger.error(f"Error stopping market data service: {e}")
            return False
    
    async def _health_check(self) -> Dict[str, Any]:
        """Perform health check"""
        health_data = {
            'provider_status': {
                'primary_connected': self.primary_provider and self.primary_provider.is_connected(),
                'fallback_count': len([p for p in self.fallback_providers if p.is_connected()]),
                'total_fallbacks': len(self.fallback_providers)
            },
            'cache_status': {
                'enabled': self.cache_enabled,
                'entry_count': len(self.data_cache),
                'hit_rate': self.request_stats['cache_hits'] / max(self.request_stats['total_requests'], 1)
            },
            'performance': {
                'requests_per_second': self.request_stats['requests_per_second'],
                'avg_latency_ms': self.request_stats['avg_latency_ms'],
                'queue_depth': self.request_queue.qsize(),
                'active_requests': len(self.active_requests)
            }
        }
        
        return health_data
    
    async def get_market_data(self, request: MarketDataRequest) -> MarketDataResponse:
        """
        Get market data with caching and failover
        
        Args:
            request: Market data request
            
        Returns:
            Market data response
        """
        start_time = datetime.now()
        request_id = f"req_{self.request_counter}"
        self.request_counter += 1
        
        try:
            # Check cache first
            if request.use_cache and self.cache_enabled:
                cached_response = await self._get_cached_data(request, request_id)
                if cached_response:
                    return cached_response
            
            # Add to active requests
            self.active_requests[request_id] = request
            
            # Try primary provider
            response = await self._fetch_from_provider(
                self.primary_provider, request, request_id
            )
            
            if not response:
                # Try fallback providers
                for provider in self.fallback_providers:
                    if provider.is_connected():
                        response = await self._fetch_from_provider(
                            provider, request, request_id
                        )
                        if response:
                            break
            
            if not response:
                # All providers failed
                response = MarketDataResponse(
                    request_id=request_id,
                    symbols=request.symbols,
                    data={},
                    timestamp=datetime.now(),
                    source_provider="none",
                    errors=["All market data providers failed"]
                )
            
            # Update cache if successful
            if response and not response.errors and self.cache_enabled:
                await self._cache_response(response)
            
            # Calculate latency
            response.latency_ms = (datetime.now() - start_time).total_seconds() * 1000
            
            # Update stats
            await self._update_request_stats(response)
            
            return response
            
        except Exception as e:
            logger.error(f"Error getting market data: {e}")
            return MarketDataResponse(
                request_id=request_id,
                symbols=request.symbols,
                data={},
                timestamp=datetime.now(),
                source_provider="error",
                errors=[str(e)]
            )
        finally:
            # Clean up
            self.active_requests.pop(request_id, None)
    
    async def subscribe_market_data(self, symbols: List[str], data_types: List[str], callback):
        """
        Subscribe to real-time market data updates
        
        Args:
            symbols: List of symbols to subscribe to
            data_types: List of data types to subscribe to
            callback: Callback function for updates
        """
        try:
            for symbol in symbols:
                # Add to subscriptions
                self.active_subscriptions[symbol].update(data_types)
                self.subscription_callbacks[symbol].append(callback)
                
                # Subscribe with provider
                if self.primary_provider and hasattr(self.primary_provider, 'subscribe'):
                    await self.primary_provider.subscribe(symbol, data_types, self._handle_subscription_update)
            
            logger.info(f"Subscribed to {len(symbols)} symbols: {data_types}")
            
        except Exception as e:
            logger.error(f"Error subscribing to market data: {e}")
    
    async def unsubscribe_market_data(self, symbols: List[str], callback=None):
        """Unsubscribe from market data updates"""
        try:
            for symbol in symbols:
                if callback:
                    # Remove specific callback
                    if symbol in self.subscription_callbacks:
                        self.subscription_callbacks[symbol] = [
                            cb for cb in self.subscription_callbacks[symbol] if cb != callback
                        ]
                else:
                    # Remove all callbacks
                    self.subscription_callbacks[symbol].clear()
                
                # If no more callbacks, unsubscribe from provider
                if not self.subscription_callbacks[symbol]:
                    if self.primary_provider and hasattr(self.primary_provider, 'unsubscribe'):
                        await self.primary_provider.unsubscribe(symbol)
                    self.active_subscriptions.pop(symbol, None)
            
            logger.info(f"Unsubscribed from {len(symbols)} symbols")
            
        except Exception as e:
            logger.error(f"Error unsubscribing from market data: {e}")
    
    async def get_option_chain(self, underlying: str, expiry_date: str = None) -> Dict[str, Any]:
        """Get option chain data"""
        request = MarketDataRequest(
            symbols=[underlying],
            data_types=['option_chain'],
            timeout=10.0
        )
        
        # Add expiry filter if provided
        if expiry_date:
            request.filters = {'expiry_date': expiry_date}
        
        response = await self.get_market_data(request)
        return response.data.get(underlying, {})
    
    async def get_historical_data(self, symbol: str, timeframe: str = '1D', 
                                 periods: int = 30) -> List[Dict[str, Any]]:
        """Get historical market data"""
        request = MarketDataRequest(
            symbols=[symbol],
            data_types=['historical'],
            timeout=15.0,
            use_cache=True,
            max_age_seconds=300  # 5 minutes for historical data
        )
        request.filters = {'timeframe': timeframe, 'periods': periods}
        
        response = await self.get_market_data(request)
        return response.data.get(symbol, {}).get('historical', [])
    
    # Internal methods
    
    async def _get_cached_data(self, request: MarketDataRequest, request_id: str) -> Optional[MarketDataResponse]:
        """Check cache for data"""
        try:
            cache_key = f"{'-'.join(sorted(request.symbols))}:{'-'.join(sorted(request.data_types))}"
            
            if cache_key in self.data_cache and cache_key in self.cache_timestamps:
                cache_age = (datetime.now() - self.cache_timestamps[cache_key]).total_seconds()
                
                if cache_age <= request.max_age_seconds:
                    # Cache hit
                    cached_data = self.data_cache[cache_key]
                    
                    response = MarketDataResponse(
                        request_id=request_id,
                        symbols=request.symbols,
                        data=cached_data['data'],
                        timestamp=cached_data['timestamp'],
                        source_provider=cached_data['source_provider'],
                        cache_hit=True
                    )
                    
                    logger.debug(f"Cache hit for {cache_key}")
                    return response
            
            return None
            
        except Exception as e:
            logger.error(f"Error checking cache: {e}")
            return None
    
    async def _cache_response(self, response: MarketDataResponse):
        """Cache successful response"""
        try:
            cache_key = f"{'-'.join(sorted(response.symbols))}"
            
            self.data_cache[cache_key] = {
                'data': response.data,
                'timestamp': response.timestamp,
                'source_provider': response.source_provider
            }
            self.cache_timestamps[cache_key] = datetime.now()
            
        except Exception as e:
            logger.error(f"Error caching response: {e}")
    
    async def _fetch_from_provider(self, provider: DataProvider, request: MarketDataRequest, 
                                  request_id: str) -> Optional[MarketDataResponse]:
        """Fetch data from a specific provider"""
        try:
            if not provider or not provider.is_connected():
                return None
            
            data = {}
            errors = []
            
            for symbol in request.symbols:
                symbol_data = {}
                
                # Get different data types
                for data_type in request.data_types:
                    try:
                        if data_type == 'quotes':
                            quotes = await provider.get_quotes([symbol])
                            symbol_data['quotes'] = quotes.get(symbol, {})
                        elif data_type == 'greeks':
                            greeks = await provider.get_greeks([symbol])
                            symbol_data['greeks'] = greeks.get(symbol, {})
                        elif data_type == 'option_chain':
                            chain = await provider.get_option_chain(symbol)
                            symbol_data['option_chain'] = chain
                        elif data_type == 'historical':
                            # Historical data parameters from request filters
                            hist_data = await provider.get_historical_data(symbol)
                            symbol_data['historical'] = hist_data
                    except Exception as e:
                        error_msg = f"Failed to get {data_type} for {symbol}: {e}"
                        errors.append(error_msg)
                        logger.warning(error_msg)
                
                if symbol_data:
                    data[symbol] = symbol_data
            
            if data:
                response = MarketDataResponse(
                    request_id=request_id,
                    symbols=request.symbols,
                    data=data,
                    timestamp=datetime.now(),
                    source_provider=provider.__class__.__name__,
                    errors=errors
                )
                
                # Reset failure count on success
                provider_name = provider.__class__.__name__
                self.provider_failure_counts[provider_name] = 0
                
                return response
            
            return None
            
        except Exception as e:
            # Track provider failures
            provider_name = provider.__class__.__name__ if provider else "unknown"
            self.provider_failure_counts[provider_name] += 1
            logger.error(f"Provider {provider_name} failed: {e}")
            return None
    
    async def _handle_subscription_update(self, symbol: str, data: Dict[str, Any]):
        """Handle subscription data updates"""
        try:
            # Call all registered callbacks for this symbol
            for callback in self.subscription_callbacks.get(symbol, []):
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(symbol, data)
                    else:
                        callback(symbol, data)
                except Exception as e:
                    logger.error(f"Error in subscription callback for {symbol}: {e}")
        
        except Exception as e:
            logger.error(f"Error handling subscription update for {symbol}: {e}")
    
    async def _process_request_queue(self):
        """Process queued market data requests"""
        try:
            while not self._shutdown_event.is_set():
                # Process any queued requests
                await asyncio.sleep(0.1)  # Small delay to prevent busy loop
                
        except asyncio.CancelledError:
            logger.debug("Request queue processor cancelled")
        except Exception as e:
            logger.error(f"Error in request queue processor: {e}")
    
    async def _cache_cleanup_loop(self):
        """Clean up expired cache entries"""
        try:
            while not self._shutdown_event.is_set():
                try:
                    current_time = datetime.now()
                    expired_keys = []
                    
                    for key, timestamp in self.cache_timestamps.items():
                        if (current_time - timestamp).total_seconds() > self.cache_duration:
                            expired_keys.append(key)
                    
                    for key in expired_keys:
                        self.data_cache.pop(key, None)
                        self.cache_timestamps.pop(key, None)
                    
                    if expired_keys:
                        logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
                    
                except Exception as e:
                    logger.error(f"Error in cache cleanup: {e}")
                
                # Wait for next cleanup cycle
                try:
                    await asyncio.wait_for(
                        self._shutdown_event.wait(),
                        timeout=60  # Clean every minute
                    )
                    break
                except asyncio.TimeoutError:
                    continue
                    
        except asyncio.CancelledError:
            logger.debug("Cache cleanup loop cancelled")
        except Exception as e:
            logger.error(f"Error in cache cleanup loop: {e}")
    
    async def _performance_monitor_loop(self):
        """Monitor service performance"""
        try:
            while not self._shutdown_event.is_set():
                try:
                    # Calculate requests per second
                    if len(self.request_history) >= 2:
                        time_diff = (self.request_history[-1]['timestamp'] - 
                                   self.request_history[0]['timestamp']).total_seconds()
                        if time_diff > 0:
                            self.request_stats['requests_per_second'] = len(self.request_history) / time_diff
                    
                    # Calculate average latency
                    if self.request_history:
                        avg_latency = sum(r['latency_ms'] for r in self.request_history) / len(self.request_history)
                        self.request_stats['avg_latency_ms'] = avg_latency
                    
                    # Keep only recent history (last 100 requests)
                    if len(self.request_history) > 100:
                        self.request_history = self.request_history[-50:]
                    
                except Exception as e:
                    logger.error(f"Error in performance monitoring: {e}")
                
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
            logger.debug("Performance monitor loop cancelled")
        except Exception as e:
            logger.error(f"Error in performance monitor loop: {e}")
    
    async def _update_request_stats(self, response: MarketDataResponse):
        """Update request statistics"""
        try:
            self.request_stats['total_requests'] += 1
            
            if response.cache_hit:
                self.request_stats['cache_hits'] += 1
            
            if response.errors:
                self.request_stats['provider_failures'] += 1
            
            # Add to request history
            self.request_history.append({
                'timestamp': datetime.now(),
                'latency_ms': response.latency_ms,
                'cache_hit': response.cache_hit,
                'errors': len(response.errors)
            })
            
        except Exception as e:
            logger.error(f"Error updating request stats: {e}")
    
    def get_service_metrics(self) -> Dict[str, Any]:
        """Get detailed service metrics"""
        return {
            'request_stats': self.request_stats.copy(),
            'provider_stats': {
                'primary_connected': self.primary_provider and self.primary_provider.is_connected(),
                'fallback_providers': len(self.fallback_providers),
                'failure_counts': dict(self.provider_failure_counts)
            },
            'cache_stats': {
                'enabled': self.cache_enabled,
                'entries': len(self.data_cache),
                'hit_rate': self.request_stats['cache_hits'] / max(self.request_stats['total_requests'], 1)
            },
            'subscription_stats': {
                'active_symbols': len(self.active_subscriptions),
                'total_subscriptions': sum(len(data_types) for data_types in self.active_subscriptions.values())
            }
        }