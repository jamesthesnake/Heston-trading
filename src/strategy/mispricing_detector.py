"""
Mispricing Detection Engine
Identifies trading opportunities by comparing Heston theoretical prices with market prices
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class SignalStrength(Enum):
    WEAK = "weak"
    MEDIUM = "medium"
    STRONG = "strong"
    VERY_STRONG = "very_strong"

class TradeDirection(Enum):
    BUY = "buy"
    SELL = "sell"

@dataclass
class MispricingSignal:
    """Individual mispricing trading signal"""
    option_key: str
    symbol: str
    strike: float
    expiry: str
    option_type: str
    direction: TradeDirection
    strength: SignalStrength
    market_price: float
    theoretical_price: float
    mispricing_pct: float
    confidence: float
    volume: int
    bid_ask_spread: float
    time_to_expiry: float
    moneyness: float
    timestamp: datetime
    
class MispricingDetector:
    """
    Detects option mispricings by comparing market vs theoretical prices
    """
    
    def __init__(self, config: dict):
        self.config = config
        self.detection_config = config.get('mispricing_detection', {})
        
        # Mispricing thresholds
        self.min_mispricing_pct = self.detection_config.get('min_mispricing_pct', 5.0)  # 5%
        self.strong_mispricing_pct = self.detection_config.get('strong_mispricing_pct', 15.0)  # 15%
        self.very_strong_mispricing_pct = self.detection_config.get('very_strong_mispricing_pct', 25.0)  # 25%
        
        # Quality filters
        self.min_volume = self.detection_config.get('min_volume', 10)
        self.max_bid_ask_spread_pct = self.detection_config.get('max_bid_ask_spread_pct', 10.0)  # 10%
        self.min_price = self.detection_config.get('min_option_price', 0.50)  # $0.50
        self.max_price = self.detection_config.get('max_option_price', 100.0)  # $100
        
        # Moneyness filters
        self.min_moneyness = self.detection_config.get('min_moneyness', 0.85)
        self.max_moneyness = self.detection_config.get('max_moneyness', 1.15)
        
        # Time to expiry filters (in days)
        self.min_dte = self.detection_config.get('min_days_to_expiry', 7)
        self.max_dte = self.detection_config.get('max_days_to_expiry', 45)
        
        # Historical tracking
        self.signal_history = []
        self.max_history_size = 1000
        
        logger.info("MispricingDetector initialized")
    
    def detect_mispricings(self, options_data: List[Dict], theoretical_prices: Dict[str, float], 
                          underlying_data: Dict) -> List[MispricingSignal]:
        """
        Detect option mispricings by comparing market vs theoretical prices
        
        Args:
            options_data: List of option market data
            theoretical_prices: Dictionary of theoretical prices from Heston model
            underlying_data: Current underlying prices
            
        Returns:
            List of mispricing signals sorted by strength
        """
        signals = []
        spot = underlying_data.get('SPX', {}).get('last', 5000.0)
        
        for option in options_data:
            try:
                signal = self._analyze_option_mispricing(option, theoretical_prices, spot)
                if signal:
                    signals.append(signal)
            except Exception as e:
                logger.debug(f"Error analyzing option {option.get('strike')}: {e}")
                continue
        
        # Sort by mispricing magnitude
        signals.sort(key=lambda x: abs(x.mispricing_pct), reverse=True)
        
        # Store in history
        self._update_signal_history(signals)
        
        logger.info(f"Detected {len(signals)} mispricing signals")
        return signals
    
    def _analyze_option_mispricing(self, option: Dict, theoretical_prices: Dict[str, float], 
                                 spot: float) -> Optional[MispricingSignal]:
        """Analyze individual option for mispricing"""
        
        # Get option details
        symbol = option.get('symbol', '')
        if symbol != 'SPX':
            return None
            
        strike = option.get('strike', 0)
        expiry = option.get('expiry', '')
        option_type = option.get('type', '')
        
        if not all([strike, expiry, option_type]):
            return None
        
        # Get market data
        bid = option.get('bid', 0)
        ask = option.get('ask', 0)
        volume = option.get('volume', 0)
        
        if bid <= 0 or ask <= 0 or ask <= bid:
            return None
        
        market_price = (bid + ask) / 2  # Use mid price
        bid_ask_spread = ask - bid
        bid_ask_spread_pct = (bid_ask_spread / market_price) * 100 if market_price > 0 else 100
        
        # Apply quality filters
        if not self._passes_quality_filters(option, market_price, volume, bid_ask_spread_pct, spot):
            return None
        
        # Get theoretical price
        option_key = self._get_option_key(option)
        theoretical_price = theoretical_prices.get(option_key)
        
        if theoretical_price is None or theoretical_price <= 0:
            return None
        
        # Calculate mispricing
        mispricing_pct = ((market_price - theoretical_price) / theoretical_price) * 100
        
        # Check if mispricing is significant enough
        if abs(mispricing_pct) < self.min_mispricing_pct:
            return None
        
        # Determine trade direction
        if market_price > theoretical_price:
            direction = TradeDirection.SELL  # Market overpriced - sell
        else:
            direction = TradeDirection.BUY   # Market underpriced - buy
        
        # Determine signal strength
        strength = self._get_signal_strength(abs(mispricing_pct))
        
        # Calculate confidence based on various factors
        confidence = self._calculate_confidence(option, market_price, theoretical_price, 
                                              volume, bid_ask_spread_pct)
        
        # Calculate additional metrics
        time_to_expiry = self._calculate_time_to_expiry(expiry)
        moneyness = strike / spot
        
        return MispricingSignal(
            option_key=option_key,
            symbol=symbol,
            strike=strike,
            expiry=expiry,
            option_type=option_type,
            direction=direction,
            strength=strength,
            market_price=market_price,
            theoretical_price=theoretical_price,
            mispricing_pct=mispricing_pct,
            confidence=confidence,
            volume=volume,
            bid_ask_spread=bid_ask_spread,
            time_to_expiry=time_to_expiry,
            moneyness=moneyness,
            timestamp=datetime.now()
        )
    
    def _passes_quality_filters(self, option: Dict, market_price: float, volume: int, 
                               bid_ask_spread_pct: float, spot: float) -> bool:
        """Check if option passes quality filters"""
        
        # Volume filter
        if volume < self.min_volume:
            return False
        
        # Price range filter
        if market_price < self.min_price or market_price > self.max_price:
            return False
        
        # Bid-ask spread filter
        if bid_ask_spread_pct > self.max_bid_ask_spread_pct:
            return False
        
        # Moneyness filter
        strike = option.get('strike', 0)
        if strike <= 0:
            return False
            
        moneyness = strike / spot
        if moneyness < self.min_moneyness or moneyness > self.max_moneyness:
            return False
        
        # Time to expiry filter
        expiry = option.get('expiry', '')
        if not expiry:
            return False
            
        try:
            expiry_date = datetime.strptime(expiry, "%Y%m%d")
            days_to_expiry = (expiry_date - datetime.now()).days
            
            if days_to_expiry < self.min_dte or days_to_expiry > self.max_dte:
                return False
        except:
            return False
        
        return True
    
    def _get_signal_strength(self, mispricing_pct: float) -> SignalStrength:
        """Determine signal strength based on mispricing percentage"""
        if mispricing_pct >= self.very_strong_mispricing_pct:
            return SignalStrength.VERY_STRONG
        elif mispricing_pct >= self.strong_mispricing_pct:
            return SignalStrength.STRONG
        elif mispricing_pct >= self.min_mispricing_pct * 2:  # 2x minimum threshold
            return SignalStrength.MEDIUM
        else:
            return SignalStrength.WEAK
    
    def _calculate_confidence(self, option: Dict, market_price: float, theoretical_price: float,
                            volume: int, bid_ask_spread_pct: float) -> float:
        """Calculate confidence score for the signal (0-100)"""
        confidence = 50.0  # Base confidence
        
        # Volume factor (higher volume = higher confidence)
        if volume >= 100:
            confidence += 15
        elif volume >= 50:
            confidence += 10
        elif volume >= 20:
            confidence += 5
        
        # Bid-ask spread factor (tighter spreads = higher confidence)
        if bid_ask_spread_pct <= 2.0:
            confidence += 15
        elif bid_ask_spread_pct <= 5.0:
            confidence += 10
        elif bid_ask_spread_pct <= 8.0:
            confidence += 5
        
        # Price level factor (avoid very cheap options)
        if market_price >= 2.0:
            confidence += 10
        elif market_price >= 1.0:
            confidence += 5
        
        # Mispricing magnitude (larger mispricings get higher confidence)
        mispricing_pct = abs((market_price - theoretical_price) / theoretical_price) * 100
        if mispricing_pct >= 20:
            confidence += 15
        elif mispricing_pct >= 15:
            confidence += 10
        elif mispricing_pct >= 10:
            confidence += 5
        
        return min(100.0, max(0.0, confidence))
    
    def _calculate_time_to_expiry(self, expiry_str: str) -> float:
        """Calculate time to expiry in years"""
        try:
            expiry_date = datetime.strptime(expiry_str, "%Y%m%d")
            days_to_expiry = (expiry_date - datetime.now()).days
            return days_to_expiry / 365.0
        except:
            return 0.0
    
    def _get_option_key(self, option: Dict) -> str:
        """Generate unique key for option"""
        symbol = option.get('symbol', '')
        strike = option.get('strike', 0)
        expiry = option.get('expiry', '')
        option_type = option.get('type', '')
        return f"{symbol}_{strike}_{expiry}_{option_type}"
    
    def _update_signal_history(self, signals: List[MispricingSignal]):
        """Update signal history for tracking"""
        self.signal_history.extend(signals)
        
        # Keep only recent signals
        if len(self.signal_history) > self.max_history_size:
            self.signal_history = self.signal_history[-self.max_history_size:]
    
    def get_signal_summary(self, signals: List[MispricingSignal]) -> Dict:
        """Get summary statistics of current signals"""
        if not signals:
            return {
                'total_signals': 0,
                'buy_signals': 0,
                'sell_signals': 0,
                'avg_mispricing': 0,
                'max_mispricing': 0,
                'strong_signals': 0
            }
        
        buy_signals = sum(1 for s in signals if s.direction == TradeDirection.BUY)
        sell_signals = sum(1 for s in signals if s.direction == TradeDirection.SELL)
        
        mispricings = [abs(s.mispricing_pct) for s in signals]
        avg_mispricing = np.mean(mispricings)
        max_mispricing = np.max(mispricings)
        
        strong_signals = sum(1 for s in signals if s.strength in [SignalStrength.STRONG, SignalStrength.VERY_STRONG])
        
        return {
            'total_signals': len(signals),
            'buy_signals': buy_signals,
            'sell_signals': sell_signals,
            'avg_mispricing': avg_mispricing,
            'max_mispricing': max_mispricing,
            'strong_signals': strong_signals,
            'signal_breakdown': {
                'very_strong': sum(1 for s in signals if s.strength == SignalStrength.VERY_STRONG),
                'strong': sum(1 for s in signals if s.strength == SignalStrength.STRONG),
                'medium': sum(1 for s in signals if s.strength == SignalStrength.MEDIUM),
                'weak': sum(1 for s in signals if s.strength == SignalStrength.WEAK)
            }
        }
    
    def get_top_signals(self, signals: List[MispricingSignal], count: int = 10) -> List[MispricingSignal]:
        """Get top signals by mispricing magnitude and confidence"""
        # Sort by combined score (mispricing * confidence)
        scored_signals = [(s, abs(s.mispricing_pct) * s.confidence / 100) for s in signals]
        scored_signals.sort(key=lambda x: x[1], reverse=True)
        
        return [s[0] for s in scored_signals[:count]]