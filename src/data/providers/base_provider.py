"""
Abstract Base Data Provider Interface
Defines the contract for all market data providers
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

class DataProvider(ABC):
    """Abstract base class for all market data providers"""
    
    class ConnectionStatus(Enum):
        DISCONNECTED = "disconnected"
        CONNECTING = "connecting"
        CONNECTED = "connected"
        ERROR = "error"
        RECONNECTING = "reconnecting"
    
    @dataclass
    class MarketDataSnapshot:
        """Standardized market data snapshot"""
        timestamp: datetime
        underlying: Dict[str, Any]  # {'SPX': {'last': 5000, 'bid': 4999.5, ...}, ...}
        options: List[Dict[str, Any]]  # [{'symbol': 'SPX', 'strike': 5000, ...}, ...]
        metadata: Dict[str, Any]  # Provider-specific metadata
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the data provider with configuration"""
        self.config = config
        self.connection_status = self.ConnectionStatus.DISCONNECTED
        self.error_callback: Optional[Callable] = None
        self.data_callback: Optional[Callable] = None
        self._last_snapshot: Optional[self.MarketDataSnapshot] = None
    
    @abstractmethod
    async def connect(self) -> bool:
        """
        Establish connection to data source
        Returns: True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def disconnect(self) -> bool:
        """
        Close connection to data source
        Returns: True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def is_connected(self) -> bool:
        """
        Check if currently connected to data source
        Returns: True if connected, False otherwise
        """
        pass
    
    @abstractmethod
    async def get_underlying_data(self, symbols: List[str]) -> Dict[str, Any]:
        """
        Get current underlying asset data
        Args:
            symbols: List of underlying symbols (e.g., ['SPX', 'SPY'])
        Returns:
            Dictionary with symbol as key and market data as value
        """
        pass
    
    @abstractmethod
    async def get_options_chain(self, underlying_symbol: str, 
                               strikes: Optional[List[float]] = None,
                               expirations: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Get options chain for underlying symbol
        Args:
            underlying_symbol: Symbol of underlying asset
            strikes: Optional list of specific strikes
            expirations: Optional list of specific expiration dates
        Returns:
            List of option contracts with market data
        """
        pass
    
    @abstractmethod
    async def get_market_snapshot(self) -> MarketDataSnapshot:
        """
        Get complete market data snapshot
        Returns:
            MarketDataSnapshot with current market state
        """
        pass
    
    @abstractmethod
    async def subscribe_real_time(self, symbols: List[str], 
                                 callback: Callable[[MarketDataSnapshot], None]) -> bool:
        """
        Subscribe to real-time market data updates
        Args:
            symbols: List of symbols to subscribe to
            callback: Function to call when new data arrives
        Returns:
            True if subscription successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def unsubscribe_real_time(self, symbols: List[str]) -> bool:
        """
        Unsubscribe from real-time market data
        Args:
            symbols: List of symbols to unsubscribe from
        Returns:
            True if unsubscription successful, False otherwise
        """
        pass
    
    # Common utility methods (implemented in base class)
    
    def set_error_callback(self, callback: Callable[[Exception], None]):
        """Set callback for error handling"""
        self.error_callback = callback
    
    def set_data_callback(self, callback: Callable[[MarketDataSnapshot], None]):
        """Set callback for data updates"""
        self.data_callback = callback
    
    def get_connection_status(self) -> ConnectionStatus:
        """Get current connection status"""
        return self.connection_status
    
    def get_last_snapshot(self) -> Optional[MarketDataSnapshot]:
        """Get the last received market data snapshot"""
        return self._last_snapshot
    
    def _update_connection_status(self, status: ConnectionStatus):
        """Update connection status (internal use)"""
        self.connection_status = status
    
    def _handle_error(self, error: Exception):
        """Handle errors and call error callback if set"""
        if self.error_callback:
            self.error_callback(error)
    
    def _handle_data_update(self, snapshot: MarketDataSnapshot):
        """Handle new data and call data callback if set"""
        self._last_snapshot = snapshot
        if self.data_callback:
            self.data_callback(snapshot)
    
    # Validation methods
    
    def _validate_config(self) -> bool:
        """Validate provider configuration"""
        required_fields = self._get_required_config_fields()
        for field in required_fields:
            if field not in self.config:
                raise ValueError(f"Missing required config field: {field}")
        return True
    
    @abstractmethod
    def _get_required_config_fields(self) -> List[str]:
        """Get list of required configuration fields for this provider"""
        pass
    
    def get_provider_info(self) -> Dict[str, Any]:
        """Get information about this data provider"""
        return {
            'provider_type': self.__class__.__name__,
            'connection_status': self.connection_status.value,
            'config_fields': list(self.config.keys()),
            'last_update': self._last_snapshot.timestamp if self._last_snapshot else None
        }