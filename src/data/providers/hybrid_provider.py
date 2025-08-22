"""
Hybrid Data Provider
Combines Interactive Brokers and Mock data with intelligent fallback
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime

from .base_provider import DataProvider
from .enhanced_ib_provider import IBDataProvider
from .mock_provider import MockDataProvider

logger = logging.getLogger(__name__)

class HybridDataProvider(DataProvider):
    """
    Hybrid provider that attempts to use IB data and falls back to mock data
    Provides seamless switching and data validation
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.provider_type = "hybrid"
        
        # Configuration
        self.prefer_ib = config.get('prefer_ib', True)
        self.ib_timeout = config.get('ib_timeout', 10)
        self.fallback_to_mock = config.get('fallback_to_mock', True)
        self.ib_retry_interval = config.get('ib_retry_interval', 300)  # 5 minutes
        
        # Initialize providers
        self.ib_provider = IBDataProvider(config.get('ib_config', {}))
        self.mock_provider = MockDataProvider(config.get('mock_config', {}))
        
        # State management
        self.active_provider: Optional[DataProvider] = None
        self.ib_available = False
        self.last_ib_check = None
        self.connection_attempts = 0
        self.max_connection_attempts = config.get('max_ib_attempts', 3)
        
        logger.info("Hybrid data provider initialized")
    
    def _get_required_config_fields(self) -> List[str]:
        """No required fields for hybrid provider"""
        return []
    
    async def connect(self) -> bool:
        """Connect to data sources with intelligent fallback"""
        try:
            self._update_connection_status(self.ConnectionStatus.CONNECTING)
            
            # Always ensure mock provider is available
            mock_connected = await self.mock_provider.connect()
            if not mock_connected:
                logger.error("Failed to connect mock provider")
                self._update_connection_status(self.ConnectionStatus.ERROR)
                return False
            
            # Try IB connection if preferred
            if self.prefer_ib:
                ib_connected = await self._try_ib_connection()
                if ib_connected:
                    self.active_provider = self.ib_provider
                    self.ib_available = True
                    logger.info("Connected to IB - using live data")
                else:
                    if self.fallback_to_mock:
                        self.active_provider = self.mock_provider
                        logger.info("IB unavailable - using mock data")
                    else:
                        self._update_connection_status(self.ConnectionStatus.ERROR)
                        return False
            else:
                # Use mock provider by default
                self.active_provider = self.mock_provider
                logger.info("Using mock data provider")
            
            self._update_connection_status(self.ConnectionStatus.CONNECTED)
            return True
            
        except Exception as e:
            self._update_connection_status(self.ConnectionStatus.ERROR)
            self._handle_error(e)
            return False
    
    async def disconnect(self) -> bool:
        """Disconnect from all data sources"""
        try:
            ib_result = await self.ib_provider.disconnect()
            mock_result = await self.mock_provider.disconnect()
            
            self.active_provider = None
            self.ib_available = False
            self._update_connection_status(self.ConnectionStatus.DISCONNECTED)
            
            logger.info("Disconnected from all data providers")
            return ib_result and mock_result
            
        except Exception as e:
            self._handle_error(e)
            return False
    
    async def is_connected(self) -> bool:
        """Check if any provider is connected"""
        if self.active_provider:
            return await self.active_provider.is_connected()
        return False
    
    async def get_underlying_data(self, symbols: List[str]) -> Dict[str, Any]:
        """Get underlying data with fallback logic"""
        try:
            # Check if IB should be retried
            await self._check_ib_reconnection()
            
            if self.active_provider:
                data = await self.active_provider.get_underlying_data(symbols)
                
                # Validate data quality
                if self._validate_data_quality(data, symbols):
                    return data
                else:
                    logger.warning("Data quality check failed, attempting fallback")
                    return await self._fallback_get_underlying_data(symbols)
            else:
                logger.error("No active provider available")
                return {}
                
        except Exception as e:
            logger.error(f"Error getting underlying data: {e}")
            return await self._fallback_get_underlying_data(symbols)
    
    async def get_options_chain(self, underlying_symbol: str, 
                               strikes: Optional[List[float]] = None,
                               expirations: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Get options chain with fallback logic"""
        try:
            await self._check_ib_reconnection()
            
            if self.active_provider:
                options = await self.active_provider.get_options_chain(
                    underlying_symbol, strikes, expirations
                )
                
                # For now, mock provider has better options simulation
                # In production, IB would provide real options data
                if isinstance(self.active_provider, IBDataProvider) and not options:
                    logger.info("IB options chain empty, using mock data")
                    return await self.mock_provider.get_options_chain(
                        underlying_symbol, strikes, expirations
                    )
                
                return options
            else:
                return []
                
        except Exception as e:
            logger.error(f"Error getting options chain: {e}")
            return await self.mock_provider.get_options_chain(
                underlying_symbol, strikes, expirations
            )
    
    async def get_market_snapshot(self) -> DataProvider.MarketDataSnapshot:
        """Get market snapshot with hybrid data"""
        try:
            await self._check_ib_reconnection()
            
            if self.active_provider:
                snapshot = await self.active_provider.get_market_snapshot()
                
                # Enhance IB data with mock options if needed
                if isinstance(self.active_provider, IBDataProvider) and not snapshot.options:
                    logger.debug("Enhancing IB data with mock options")
                    mock_snapshot = await self.mock_provider.get_market_snapshot()
                    
                    # Combine IB underlying with mock options
                    enhanced_snapshot = self.MarketDataSnapshot(
                        timestamp=snapshot.timestamp,
                        underlying=snapshot.underlying,
                        options=mock_snapshot.options,
                        metadata={
                            **snapshot.metadata,
                            'enhanced_with_mock_options': True,
                            'primary_provider': 'interactive_brokers',
                            'options_provider': 'mock'
                        }
                    )
                    return enhanced_snapshot
                
                return snapshot
            else:
                # Fallback to mock
                return await self.mock_provider.get_market_snapshot()
                
        except Exception as e:
            logger.error(f"Error getting market snapshot: {e}")
            return await self.mock_provider.get_market_snapshot()
    
    async def subscribe_real_time(self, symbols: List[str], 
                                 callback: Callable[[DataProvider.MarketDataSnapshot], None]) -> bool:
        """Subscribe to real-time data"""
        try:
            # Store callback for potential provider switching
            self.data_callback = callback
            
            if self.active_provider:
                result = await self.active_provider.subscribe_real_time(symbols, callback)
                
                if result:
                    logger.info(f"Subscribed to real-time data via {self.active_provider.provider_type}")
                    return True
                else:
                    # Try fallback
                    return await self._fallback_subscribe_real_time(symbols, callback)
            else:
                return False
                
        except Exception as e:
            logger.error(f"Error subscribing to real-time data: {e}")
            return await self._fallback_subscribe_real_time(symbols, callback)
    
    async def unsubscribe_real_time(self, symbols: List[str]) -> bool:
        """Unsubscribe from real-time data"""
        try:
            results = []
            
            # Unsubscribe from all providers
            if await self.ib_provider.is_connected():
                results.append(await self.ib_provider.unsubscribe_real_time(symbols))
            
            if await self.mock_provider.is_connected():
                results.append(await self.mock_provider.unsubscribe_real_time(symbols))
            
            self.data_callback = None
            return any(results)
            
        except Exception as e:
            logger.error(f"Error unsubscribing from real-time data: {e}")
            return False
    
    # Helper methods
    
    async def _try_ib_connection(self) -> bool:
        """Attempt to connect to IB with retry logic"""
        if self.connection_attempts >= self.max_connection_attempts:
            logger.warning(f"Max IB connection attempts ({self.max_connection_attempts}) reached")
            return False
        
        try:
            self.connection_attempts += 1
            logger.info(f"Attempting IB connection (attempt {self.connection_attempts})")
            
            result = await asyncio.wait_for(
                self.ib_provider.connect(),
                timeout=self.ib_timeout
            )
            
            if result:
                self.connection_attempts = 0  # Reset on success
                self.last_ib_check = datetime.now()
                return True
            else:
                logger.warning("IB connection failed")
                return False
                
        except asyncio.TimeoutError:
            logger.warning(f"IB connection timeout after {self.ib_timeout} seconds")
            return False
        except Exception as e:
            logger.error(f"IB connection error: {e}")
            return False
    
    async def _check_ib_reconnection(self):
        """Check if IB should be retried"""
        if (not self.ib_available and 
            self.prefer_ib and 
            isinstance(self.active_provider, MockDataProvider)):
            
            now = datetime.now()
            if (self.last_ib_check is None or 
                (now - self.last_ib_check).total_seconds() > self.ib_retry_interval):
                
                logger.info("Attempting IB reconnection")
                if await self._try_ib_connection():
                    logger.info("IB reconnected successfully - switching providers")
                    
                    # Unsubscribe from mock
                    if self.data_callback:
                        await self.mock_provider.unsubscribe_real_time(self.subscribed_symbols)
                    
                    # Switch to IB
                    self.active_provider = self.ib_provider
                    self.ib_available = True
                    
                    # Resubscribe if needed
                    if self.data_callback and hasattr(self, 'subscribed_symbols'):
                        await self.ib_provider.subscribe_real_time(
                            self.subscribed_symbols, self.data_callback
                        )
                else:
                    self.last_ib_check = now
    
    def _validate_data_quality(self, data: Dict[str, Any], expected_symbols: List[str]) -> bool:
        """Validate data quality and completeness"""
        if not data:
            return False
        
        # Check if we have data for all requested symbols
        for symbol in expected_symbols:
            if symbol not in data:
                logger.warning(f"Missing data for symbol: {symbol}")
                return False
            
            symbol_data = data[symbol]
            
            # Check for valid price data
            if symbol_data.get('last', 0) <= 0:
                logger.warning(f"Invalid price data for {symbol}: {symbol_data.get('last')}")
                return False
        
        return True
    
    async def _fallback_get_underlying_data(self, symbols: List[str]) -> Dict[str, Any]:
        """Fallback method for getting underlying data"""
        if self.fallback_to_mock:
            logger.info("Using mock provider fallback for underlying data")
            return await self.mock_provider.get_underlying_data(symbols)
        return {}
    
    async def _fallback_subscribe_real_time(self, symbols: List[str], 
                                           callback: Callable) -> bool:
        """Fallback method for real-time subscription"""
        if self.fallback_to_mock:
            logger.info("Using mock provider fallback for real-time data")
            return await self.mock_provider.subscribe_real_time(symbols, callback)
        return False
    
    def get_provider_status(self) -> Dict[str, Any]:
        """Get detailed status of all providers"""
        return {
            'active_provider': self.active_provider.provider_type if self.active_provider else None,
            'ib_available': self.ib_available,
            'ib_connected': asyncio.run(self.ib_provider.is_connected()),
            'mock_connected': asyncio.run(self.mock_provider.is_connected()),
            'connection_attempts': self.connection_attempts,
            'last_ib_check': self.last_ib_check,
            'prefer_ib': self.prefer_ib,
            'fallback_to_mock': self.fallback_to_mock
        }