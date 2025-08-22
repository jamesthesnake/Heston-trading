"""
Data Feed Manager for market data
"""
import logging
from datetime import datetime
from typing import Dict, Optional
import random
import asyncio
from .enhanced_mock_generator import enhanced_mock

logger = logging.getLogger(__name__)

class DataFeedManager:
    """Manages market data feeds"""
    
    def __init__(self, config: dict):
        self.config = config
        self.is_connected = False
        self.use_mock = config.get('data', {}).get('use_mock', False)
        self.current_data = {}
        
        logger.info(f"DataFeedManager initialized (mock={self.use_mock})")
    
    def connect(self) -> bool:
        """Connect to data source"""
        if self.use_mock:
            logger.info("Using mock data source")
            self.is_connected = True
            self._generate_mock_data()
        else:
            logger.info("Connecting to Interactive Brokers...")
            # IB connection would go here
            self.is_connected = True
        
        return self.is_connected
    
    def _generate_mock_data(self):
        """Generate enhanced realistic mock market data"""
        # Generate underlying data
        underlying_data = enhanced_mock.generate_underlying_snapshot()
        
        # Generate options data
        options_data = enhanced_mock.generate_options_snapshot(underlying_data)
        
        # Generate trading signals
        signals = enhanced_mock.generate_trading_signals(underlying_data, options_data)
        
        # Generate positions
        positions = enhanced_mock.generate_positions()
        
        self.current_data = {
            'underlying': underlying_data,
            'options': options_data,
            'signals': signals,
            'positions': positions,
            'market_state': {
                'session': self._get_market_session(),
                'sentiment': enhanced_mock.market_sentiment,
                'volatility_regime': enhanced_mock.volatility_regime,
                'timestamp': datetime.now()
            }
        }
    
    def _get_market_session(self) -> str:
        """Determine current market session"""
        current_hour = datetime.now().hour
        
        if 9 <= current_hour < 16:
            return "open"
        elif 16 <= current_hour < 20:
            return "after_hours"
        else:
            return "closed"
    
    def get_snapshot(self) -> Optional[Dict]:
        """Get current market snapshot"""
        if self.use_mock:
            self._generate_mock_data()
        return self.current_data
    
    async def stream_data(self, update_interval: float = 1.0):
        """Stream live data updates"""
        while self.is_connected:
            if self.use_mock:
                self._generate_mock_data()
                yield self.current_data
            await asyncio.sleep(update_interval)
    
    def disconnect(self):
        """Disconnect from data source"""
        self.is_connected = False
        logger.info("DataFeedManager disconnected")
