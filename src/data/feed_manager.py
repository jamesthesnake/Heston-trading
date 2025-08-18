"""
Data Feed Manager for market data
"""
import logging
from datetime import datetime
from typing import Dict, Optional
import random

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
        """Generate mock market data"""
        self.current_data = {
            'SPX': {
                'bid': 4999.50,
                'ask': 5000.50,
                'last': 5000.00,
                'timestamp': datetime.now()
            },
            'VIX': {
                'last': 15.5 + random.random(),
                'timestamp': datetime.now()
            },
            'options': []
        }
        
        # Generate mock options
        for strike in range(4900, 5100, 25):
            for option_type in ['C', 'P']:
                self.current_data['options'].append({
                    'strike': strike,
                    'type': option_type,
                    'bid': 20 + random.random() * 5,
                    'ask': 21 + random.random() * 5,
                    'iv': 0.15 + random.random() * 0.05,
                    'volume': random.randint(100, 5000)
                })
    
    def get_snapshot(self) -> Optional[Dict]:
        """Get current market snapshot"""
        if self.use_mock:
            self._generate_mock_data()
        return self.current_data
    
    def disconnect(self):
        """Disconnect from data source"""
        self.is_connected = False
        logger.info("DataFeedManager disconnected")
