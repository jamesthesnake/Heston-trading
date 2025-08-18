"""
Data validation utilities
"""
import logging
from typing import Dict, List, Tuple, Optional

logger = logging.getLogger(__name__)

class DataValidator:
    """Validates market data"""
    
    @staticmethod
    def validate_quote(quote: dict) -> Tuple[bool, Optional[str]]:
        """Validate a market quote"""
        
        # Check required fields
        required = ['bid', 'ask', 'last']
        for field in required:
            if field not in quote:
                return False, f"Missing field: {field}"
        
        # Check bid/ask relationship
        if quote['bid'] > quote['ask']:
            return False, "Bid > Ask"
        
        # Check for negative prices
        if quote['bid'] < 0 or quote['ask'] < 0:
            return False, "Negative prices"
        
        # Check spread
        if quote['ask'] > 0:
            spread_pct = (quote['ask'] - quote['bid']) / quote['ask'] * 100
            if spread_pct > 50:  # More than 50% spread
                return False, f"Excessive spread: {spread_pct:.1f}%"
        
        return True, None
    
    @staticmethod
    def validate_option(option: dict) -> Tuple[bool, Optional[str]]:
        """Validate option data"""
        
        # Check required fields
        required = ['strike', 'type', 'bid', 'ask', 'iv']
        for field in required:
            if field not in option:
                return False, f"Missing field: {field}"
        
        # Check IV bounds
        if not 0.01 < option['iv'] < 3.0:
            return False, f"Invalid IV: {option['iv']}"
        
        # Check option type
        if option['type'] not in ['C', 'P']:
            return False, f"Invalid option type: {option['type']}"
        
        return True, None
    
    @staticmethod
    def validate_position(position: dict) -> Tuple[bool, Optional[str]]:
        """Validate position data"""
        
        required = ['symbol', 'quantity', 'entry_price']
        for field in required:
            if field not in position:
                return False, f"Missing field: {field}"
        
        if position['quantity'] == 0:
            return False, "Zero quantity"
        
        if position['entry_price'] <= 0:
            return False, "Invalid entry price"
        
        return True, None
