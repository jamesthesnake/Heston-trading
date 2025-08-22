"""
Unified Data Feed Manager
Uses the new provider system for clean data management
"""
import asyncio
import logging
from datetime import datetime
from typing import Dict, Optional, Any, List, Callable

from .providers.provider_factory import DataProviderFactory, create_recommended_provider
from .providers.base_provider import DataProvider
from ..config.config_manager import get_config_manager

logger = logging.getLogger(__name__)

class UnifiedFeedManager:
    """
    Unified data feed manager using the new provider system
    Provides clean interface for all data operations
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the unified feed manager
        
        Args:
            config: Configuration dictionary or None to use global config
        """
        self.config = config
        self.provider: Optional[DataProvider] = None
        self.is_connected = False
        self.is_streaming = False
        
        # Data storage
        self.latest_snapshot: Optional[DataProvider.MarketDataSnapshot] = None
        self.data_callbacks: List[Callable] = []
        
        # Initialize provider from config
        self._initialize_provider()
        
        logger.info("Unified feed manager initialized")
    
    def _initialize_provider(self):
        """Initialize data provider from configuration"""
        try:
            if self.config:
                # Use provided config
                provider_config = self.config.get('data_provider', {})
                provider_type = provider_config.get('type', 'mock')
                self.provider = DataProviderFactory.create_provider(provider_type, provider_config)
            else:
                # Use global configuration manager
                config_manager = get_config_manager()
                provider_config = config_manager.get_data_provider_config()
                provider_type = provider_config.get('type', 'mock')
                self.provider = DataProviderFactory.create_provider(provider_type, provider_config)
            
            # Set up callbacks
            self.provider.set_data_callback(self._handle_data_update)
            self.provider.set_error_callback(self._handle_error)
            
            logger.info(f"Initialized {provider_type} data provider")
            
        except Exception as e:
            logger.error(f"Failed to initialize provider: {e}")
            # Fallback to mock provider
            logger.info("Falling back to mock provider")
            self.provider = create_recommended_provider("demo")
            self.provider.set_data_callback(self._handle_data_update)
            self.provider.set_error_callback(self._handle_error)
    
    async def connect(self) -> bool:
        """Connect to data source"""
        try:
            if not self.provider:
                logger.error("No data provider available")
                return False
            
            logger.info("Connecting to data source...")
            self.is_connected = await self.provider.connect()
            
            if self.is_connected:
                logger.info(f"Connected to {self.provider.provider_type} data provider")
                
                # Get initial snapshot
                await self._update_snapshot()
                
            return self.is_connected
            
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False
    
    async def disconnect(self) -> bool:
        """Disconnect from data source"""
        try:
            if self.provider and self.is_connected:
                await self.provider.disconnect()
            
            self.is_connected = False
            self.is_streaming = False
            logger.info("Disconnected from data source")
            return True
            
        except Exception as e:
            logger.error(f"Disconnect failed: {e}")
            return False
    
    async def start_streaming(self, symbols: Optional[List[str]] = None) -> bool:
        """Start real-time data streaming"""
        try:
            if not self.is_connected:
                logger.error("Not connected to data source")
                return False
            
            symbols = symbols or ['SPX', 'SPY', 'VIX']
            
            success = await self.provider.subscribe_real_time(symbols, self._handle_data_update)
            
            if success:
                self.is_streaming = True
                logger.info(f"Started streaming data for {symbols}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to start streaming: {e}")
            return False
    
    async def stop_streaming(self) -> bool:
        """Stop real-time data streaming"""
        try:
            if self.provider and self.is_streaming:
                await self.provider.unsubscribe_real_time(['SPX', 'SPY', 'VIX'])
            
            self.is_streaming = False
            logger.info("Stopped data streaming")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop streaming: {e}")
            return False
    
    async def get_underlying_data(self, symbols: Optional[List[str]] = None) -> Dict[str, Any]:
        """Get current underlying asset data"""
        try:
            if not self.provider or not self.is_connected:
                logger.error("No connection to data source")
                return {}
            
            symbols = symbols or ['SPX', 'SPY', 'VIX']
            return await self.provider.get_underlying_data(symbols)
            
        except Exception as e:
            logger.error(f"Error getting underlying data: {e}")
            return {}
    
    async def get_options_chain(self, underlying_symbol: str, 
                               strikes: Optional[List[float]] = None,
                               expirations: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Get options chain for underlying"""
        try:
            if not self.provider or not self.is_connected:
                logger.error("No connection to data source")
                return []
            
            return await self.provider.get_options_chain(underlying_symbol, strikes, expirations)
            
        except Exception as e:
            logger.error(f"Error getting options chain: {e}")
            return []
    
    async def get_market_snapshot(self) -> Optional[DataProvider.MarketDataSnapshot]:
        """Get complete market snapshot"""
        try:
            if not self.provider or not self.is_connected:
                logger.error("No connection to data source")
                return None
            
            snapshot = await self.provider.get_market_snapshot()
            self.latest_snapshot = snapshot
            return snapshot
            
        except Exception as e:
            logger.error(f"Error getting market snapshot: {e}")
            return None
    
    def get_latest_snapshot(self) -> Optional[DataProvider.MarketDataSnapshot]:
        """Get the latest cached snapshot"""
        return self.latest_snapshot
    
    def add_data_callback(self, callback: Callable[[DataProvider.MarketDataSnapshot], None]):
        """Add callback for data updates"""
        if callback not in self.data_callbacks:
            self.data_callbacks.append(callback)
    
    def remove_data_callback(self, callback: Callable):
        """Remove data callback"""
        if callback in self.data_callbacks:
            self.data_callbacks.remove(callback)
    
    def get_connection_status(self) -> Dict[str, Any]:
        """Get detailed connection status"""
        status = {
            'connected': self.is_connected,
            'streaming': self.is_streaming,
            'provider_type': self.provider.provider_type if self.provider else None,
            'last_update': self.latest_snapshot.timestamp if self.latest_snapshot else None
        }
        
        if self.provider:
            status.update({
                'provider_status': self.provider.get_connection_status().value,
                'provider_info': self.provider.get_provider_info()
            })
        
        return status
    
    def get_data_summary(self) -> Dict[str, Any]:
        """Get summary of current data"""
        if not self.latest_snapshot:
            return {
                'underlying_count': 0,
                'options_count': 0,
                'last_update': None
            }
        
        return {
            'underlying_count': len(self.latest_snapshot.underlying),
            'options_count': len(self.latest_snapshot.options),
            'last_update': self.latest_snapshot.timestamp,
            'underlying_symbols': list(self.latest_snapshot.underlying.keys()),
            'metadata': self.latest_snapshot.metadata
        }
    
    # Legacy compatibility methods (for backward compatibility)
    
    def connect_sync(self) -> bool:
        """Synchronous connect method for backward compatibility"""
        return asyncio.run(self.connect())
    
    def get_current_data(self) -> Dict[str, Any]:
        """Get current data in legacy format"""
        if not self.latest_snapshot:
            return {}
        
        return {
            'underlying': self.latest_snapshot.underlying,
            'options': self.latest_snapshot.options,
            'timestamp': self.latest_snapshot.timestamp,
            'metadata': self.latest_snapshot.metadata
        }
    
    # Private methods
    
    async def _update_snapshot(self):
        """Update the latest snapshot"""
        try:
            snapshot = await self.get_market_snapshot()
            if snapshot:
                self.latest_snapshot = snapshot
        except Exception as e:
            logger.error(f"Error updating snapshot: {e}")
    
    def _handle_data_update(self, snapshot: DataProvider.MarketDataSnapshot):
        """Handle incoming data updates"""
        try:
            self.latest_snapshot = snapshot
            
            # Notify all callbacks
            for callback in self.data_callbacks:
                try:
                    callback(snapshot)
                except Exception as e:
                    logger.error(f"Error in data callback: {e}")
                    
        except Exception as e:
            logger.error(f"Error handling data update: {e}")
    
    def _handle_error(self, error: Exception):
        """Handle provider errors"""
        logger.error(f"Provider error: {error}")
        
        # Could implement automatic reconnection logic here
        # For now, just log the error

# Factory function for backward compatibility
def create_feed_manager(config: Optional[Dict[str, Any]] = None) -> UnifiedFeedManager:
    """Create a feed manager instance"""
    return UnifiedFeedManager(config)