"""
Helper utilities
"""
import json
import pickle
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import numpy as np

def save_json(data: dict, filepath: str):
    """Save data to JSON file"""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2, default=str)

def load_json(filepath: str) -> dict:
    """Load data from JSON file"""
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            return json.load(f)
    return {}

def save_pickle(data: Any, filepath: str):
    """Save data to pickle file"""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'wb') as f:
        pickle.dump(data, f)

def load_pickle(filepath: str) -> Any:
    """Load data from pickle file"""
    if os.path.exists(filepath):
        with open(filepath, 'rb') as f:
            return pickle.load(f)
    return None

def calculate_returns(prices: List[float]) -> List[float]:
    """Calculate returns from price series"""
    if len(prices) < 2:
        return []
    
    prices_array = np.array(prices)
    returns = np.diff(prices_array) / prices_array[:-1]
    return returns.tolist()

def calculate_sharpe_ratio(returns: List[float], risk_free_rate: float = 0.02) -> float:
    """Calculate Sharpe ratio"""
    if not returns:
        return 0.0
    
    returns_array = np.array(returns)
    excess_returns = returns_array - risk_free_rate / 252  # Daily risk-free rate
    
    if len(excess_returns) < 2:
        return 0.0
    
    return np.sqrt(252) * np.mean(excess_returns) / np.std(excess_returns)

def get_market_hours() -> Tuple[datetime, datetime]:
    """Get today's market hours"""
    now = datetime.now()
    market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = now.replace(hour=16, minute=0, second=0, microsecond=0)
    return market_open, market_close

def is_market_open() -> bool:
    """Check if market is currently open"""
    now = datetime.now()
    
    # Check if weekend
    if now.weekday() >= 5:  # Saturday = 5, Sunday = 6
        return False
    
    # Check market hours (9:30 AM - 4:00 PM ET)
    market_open, market_close = get_market_hours()
    return market_open <= now <= market_close

def format_number(value: float, decimals: int = 2) -> str:
    """Format number for display"""
    if abs(value) >= 1e6:
        return f"{value/1e6:.{decimals}f}M"
    elif abs(value) >= 1e3:
        return f"{value/1e3:.{decimals}f}K"
    else:
        return f"{value:.{decimals}f}"

def calculate_option_metrics(spot: float, strike: float, dte: int) -> dict:
    """Calculate basic option metrics"""
    moneyness = np.log(strike / spot)
    time_to_expiry = dte / 365.0
    
    return {
        'moneyness': moneyness,
        'time_to_expiry': time_to_expiry,
        'is_itm_call': spot > strike,
        'is_itm_put': spot < strike,
        'intrinsic_call': max(0, spot - strike),
        'intrinsic_put': max(0, strike - spot)
    }
