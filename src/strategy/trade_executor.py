"""
Automated Trade Execution Engine
Executes trades based on mispricing signals with risk management
"""
import numpy as np
from typing import Dict, List, Optional, Tuple
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
from .mispricing_detector import MispricingSignal, SignalStrength, TradeDirection

logger = logging.getLogger(__name__)

class OrderStatus(Enum):
    PENDING = "pending"
    FILLED = "filled"
    REJECTED = "rejected"
    CANCELLED = "cancelled"

class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"

@dataclass
class Trade:
    """Individual trade execution"""
    trade_id: str
    option_key: str
    symbol: str
    strike: float
    expiry: str
    option_type: str
    direction: TradeDirection
    quantity: int
    entry_price: float
    target_price: Optional[float]
    stop_loss: Optional[float]
    status: OrderStatus
    signal_strength: SignalStrength
    confidence: float
    timestamp: datetime
    fill_timestamp: Optional[datetime] = None
    exit_timestamp: Optional[datetime] = None
    exit_price: Optional[float] = None
    pnl: float = 0.0
    max_pnl: float = 0.0
    min_pnl: float = 0.0

class TradeExecutor:
    """
    Automated trade execution with position sizing and risk management
    """
    
    def __init__(self, config: dict):
        self.config = config
        self.execution_config = config.get('trade_execution', {})
        
        # Position sizing
        self.max_position_size = self.execution_config.get('max_position_size', 10)
        self.base_position_size = self.execution_config.get('base_position_size', 1)
        self.size_scaling_factor = self.execution_config.get('size_scaling_factor', 2.0)
        
        # Risk management
        self.max_risk_per_trade = self.execution_config.get('max_risk_per_trade', 1000.0)  # $1000
        self.max_daily_risk = self.execution_config.get('max_daily_risk', 5000.0)  # $5000
        self.max_portfolio_delta = self.execution_config.get('max_portfolio_delta', 0.1)
        self.max_portfolio_vega = self.execution_config.get('max_portfolio_vega', 1000.0)
        
        # Execution parameters
        self.min_signal_confidence = self.execution_config.get('min_signal_confidence', 70.0)
        self.min_signal_strength = self.execution_config.get('min_signal_strength', 'medium')
        self.slippage_allowance = self.execution_config.get('slippage_allowance', 0.02)  # 2%
        
        # Stop loss and take profit
        self.stop_loss_pct = self.execution_config.get('stop_loss_pct', 50.0)  # 50% loss
        self.take_profit_pct = self.execution_config.get('take_profit_pct', 100.0)  # 100% gain
        
        # Active trades and history
        self.active_trades: Dict[str, Trade] = {}
        self.trade_history: List[Trade] = []
        self.daily_pnl = 0.0
        self.daily_risk_used = 0.0
        
        # Trade ID counter
        self.trade_counter = 0
        
        logger.info("TradeExecutor initialized")
    
    def execute_signals(self, signals: List[MispricingSignal], options_data: List[Dict], 
                       underlying_data: Dict) -> List[Trade]:
        """
        Execute trades based on mispricing signals
        
        Args:
            signals: List of mispricing signals
            options_data: Current options market data
            underlying_data: Current underlying prices
            
        Returns:
            List of executed trades
        """
        executed_trades = []
        
        # Filter signals for execution
        executable_signals = self._filter_signals_for_execution(signals)
        
        # Check portfolio risk before executing any trades
        if not self._check_portfolio_risk():
            logger.warning("Portfolio risk limits reached - no new trades")
            return executed_trades
        
        for signal in executable_signals:
            try:
                trade = self._execute_signal(signal, options_data, underlying_data)
                if trade:
                    executed_trades.append(trade)
                    self.active_trades[trade.trade_id] = trade
                    logger.info(f"Executed trade: {trade.trade_id} - {trade.symbol} {trade.strike}{trade.option_type}")
                    
            except Exception as e:
                logger.error(f"Failed to execute signal for {signal.option_key}: {e}")
                continue
        
        logger.info(f"Executed {len(executed_trades)} trades from {len(signals)} signals")
        return executed_trades
    
    def _filter_signals_for_execution(self, signals: List[MispricingSignal]) -> List[MispricingSignal]:
        """Filter signals that meet execution criteria"""
        executable = []
        
        for signal in signals:
            # Check signal quality
            if signal.confidence < self.min_signal_confidence:
                continue
            
            # Check signal strength
            strength_map = {
                'weak': 1, 'medium': 2, 'strong': 3, 'very_strong': 4
            }
            min_strength_level = strength_map.get(self.min_signal_strength, 2)
            signal_strength_level = strength_map.get(signal.strength.value, 0)
            
            if signal_strength_level < min_strength_level:
                continue
            
            # Check if we already have a position in this option
            if signal.option_key in [t.option_key for t in self.active_trades.values()]:
                continue
            
            # Check daily risk limit
            estimated_risk = self._estimate_trade_risk(signal)
            if self.daily_risk_used + estimated_risk > self.max_daily_risk:
                continue
            
            executable.append(signal)
        
        # Sort by signal strength and confidence
        executable.sort(key=lambda s: (
            strength_map.get(s.strength.value, 0),
            s.confidence,
            abs(s.mispricing_pct)
        ), reverse=True)
        
        # Limit number of simultaneous trades
        max_simultaneous_trades = self.execution_config.get('max_simultaneous_trades', 20)
        current_trades = len(self.active_trades)
        available_slots = max_simultaneous_trades - current_trades
        
        return executable[:available_slots]
    
    def _execute_signal(self, signal: MispricingSignal, options_data: List[Dict], 
                       underlying_data: Dict) -> Optional[Trade]:
        """Execute individual signal"""
        
        # Find current market data for this option
        option_data = None
        for option in options_data:
            if (option.get('symbol') == signal.symbol and 
                option.get('strike') == signal.strike and
                option.get('expiry') == signal.expiry and
                option.get('type') == signal.option_type):
                option_data = option
                break
        
        if not option_data:
            logger.warning(f"No market data found for {signal.option_key}")
            return None
        
        # Calculate position size
        position_size = self._calculate_position_size(signal)
        
        # Determine entry price and risk
        entry_price, risk_amount = self._determine_entry_price_and_risk(signal, option_data)
        
        if entry_price <= 0:
            logger.warning(f"Invalid entry price for {signal.option_key}")
            return None
        
        # Check individual trade risk
        if risk_amount > self.max_risk_per_trade:
            logger.warning(f"Trade risk too high: ${risk_amount:.0f} > ${self.max_risk_per_trade:.0f}")
            return None
        
        # Calculate stop loss and take profit
        stop_loss, target_price = self._calculate_exit_levels(entry_price, signal.direction)
        
        # Create trade
        trade_id = self._generate_trade_id()
        trade = Trade(
            trade_id=trade_id,
            option_key=signal.option_key,
            symbol=signal.symbol,
            strike=signal.strike,
            expiry=signal.expiry,
            option_type=signal.option_type,
            direction=signal.direction,
            quantity=position_size,
            entry_price=entry_price,
            target_price=target_price,
            stop_loss=stop_loss,
            status=OrderStatus.FILLED,  # Assume immediate fill in simulation
            signal_strength=signal.strength,
            confidence=signal.confidence,
            timestamp=datetime.now(),
            fill_timestamp=datetime.now()
        )
        
        # Update risk tracking
        self.daily_risk_used += risk_amount
        
        logger.info(f"Created trade: {trade_id} - {signal.direction.value.upper()} "
                   f"{position_size} {signal.symbol} {signal.strike}{signal.option_type} @ ${entry_price:.2f}")
        
        return trade
    
    def _calculate_position_size(self, signal: MispricingSignal) -> int:
        """Calculate position size based on signal strength and confidence"""
        
        # Base size
        size = self.base_position_size
        
        # Scale by signal strength
        strength_multipliers = {
            SignalStrength.WEAK: 1.0,
            SignalStrength.MEDIUM: 1.5,
            SignalStrength.STRONG: 2.0,
            SignalStrength.VERY_STRONG: 3.0
        }
        size *= strength_multipliers.get(signal.strength, 1.0)
        
        # Scale by confidence
        confidence_multiplier = signal.confidence / 100.0
        size *= confidence_multiplier
        
        # Scale by mispricing magnitude
        mispricing_multiplier = min(2.0, abs(signal.mispricing_pct) / 10.0)  # Cap at 2x
        size *= mispricing_multiplier
        
        # Apply maximum limit
        size = min(size, self.max_position_size)
        
        return max(1, int(size))
    
    def _determine_entry_price_and_risk(self, signal: MispricingSignal, 
                                       option_data: Dict) -> Tuple[float, float]:
        """Determine entry price and risk amount"""
        
        bid = option_data.get('bid', 0)
        ask = option_data.get('ask', 0)
        
        if bid <= 0 or ask <= 0:
            return 0.0, 0.0
        
        # Determine entry price based on direction
        if signal.direction == TradeDirection.BUY:
            # Buying - use ask price with slippage allowance
            entry_price = ask * (1 + self.slippage_allowance)
        else:
            # Selling - use bid price with slippage allowance
            entry_price = bid * (1 - self.slippage_allowance)
        
        # Calculate position size
        position_size = self._calculate_position_size(signal)
        
        # Calculate risk (maximum loss)
        if signal.direction == TradeDirection.BUY:
            # Risk is full premium paid
            risk_amount = entry_price * position_size * 100  # 100 shares per contract
        else:
            # Risk for short positions is harder to calculate - use conservative estimate
            # Assume maximum 5x the premium received
            risk_amount = entry_price * position_size * 100 * 5
        
        return entry_price, risk_amount
    
    def _calculate_exit_levels(self, entry_price: float, direction: TradeDirection) -> Tuple[float, float]:
        """Calculate stop loss and take profit levels"""
        
        if direction == TradeDirection.BUY:
            # Long position
            stop_loss = entry_price * (1 - self.stop_loss_pct / 100)
            target_price = entry_price * (1 + self.take_profit_pct / 100)
        else:
            # Short position
            stop_loss = entry_price * (1 + self.stop_loss_pct / 100)
            target_price = entry_price * (1 - self.take_profit_pct / 100)
        
        return stop_loss, target_price
    
    def _estimate_trade_risk(self, signal: MispricingSignal) -> float:
        """Estimate risk for a potential trade"""
        position_size = self._calculate_position_size(signal)
        
        if signal.direction == TradeDirection.BUY:
            # Risk is premium paid
            risk = signal.market_price * position_size * 100
        else:
            # Conservative risk estimate for short positions
            risk = signal.market_price * position_size * 100 * 3
        
        return risk
    
    def _check_portfolio_risk(self) -> bool:
        """Check if portfolio risk limits allow new trades"""
        
        # Check daily risk limit
        if self.daily_risk_used >= self.max_daily_risk:
            return False
        
        # Additional risk checks would go here (delta, vega, etc.)
        
        return True
    
    def _generate_trade_id(self) -> str:
        """Generate unique trade ID"""
        self.trade_counter += 1
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"T_{timestamp}_{self.trade_counter:04d}"
    
    def update_positions(self, options_data: List[Dict]) -> List[Trade]:
        """Update active positions with current market data"""
        updated_trades = []
        
        for trade_id, trade in list(self.active_trades.items()):
            try:
                # Find current market data
                current_option_data = None
                for option in options_data:
                    if (option.get('symbol') == trade.symbol and
                        option.get('strike') == trade.strike and
                        option.get('expiry') == trade.expiry and
                        option.get('type') == trade.option_type):
                        current_option_data = option
                        break
                
                if not current_option_data:
                    continue
                
                # Update P&L
                current_price = (current_option_data.get('bid', 0) + current_option_data.get('ask', 0)) / 2
                if current_price > 0:
                    self._update_trade_pnl(trade, current_price)
                
                # Check exit conditions
                if self._should_exit_trade(trade, current_price):
                    exited_trade = self._exit_trade(trade, current_price)
                    if exited_trade:
                        updated_trades.append(exited_trade)
                        del self.active_trades[trade_id]
                        self.trade_history.append(exited_trade)
                
            except Exception as e:
                logger.error(f"Error updating trade {trade_id}: {e}")
        
        return updated_trades
    
    def _update_trade_pnl(self, trade: Trade, current_price: float):
        """Update trade P&L"""
        if trade.direction == TradeDirection.BUY:
            pnl = (current_price - trade.entry_price) * trade.quantity * 100
        else:
            pnl = (trade.entry_price - current_price) * trade.quantity * 100
        
        trade.pnl = pnl
        trade.max_pnl = max(trade.max_pnl, pnl)
        trade.min_pnl = min(trade.min_pnl, pnl)
    
    def _should_exit_trade(self, trade: Trade, current_price: float) -> bool:
        """Check if trade should be exited"""
        
        # Check stop loss
        if trade.stop_loss:
            if trade.direction == TradeDirection.BUY and current_price <= trade.stop_loss:
                return True
            elif trade.direction == TradeDirection.SELL and current_price >= trade.stop_loss:
                return True
        
        # Check take profit
        if trade.target_price:
            if trade.direction == TradeDirection.BUY and current_price >= trade.target_price:
                return True
            elif trade.direction == TradeDirection.SELL and current_price <= trade.target_price:
                return True
        
        # Check time-based exit (close to expiry)
        try:
            expiry_date = datetime.strptime(trade.expiry, "%Y%m%d")
            days_to_expiry = (expiry_date - datetime.now()).days
            
            if days_to_expiry <= 2:  # Close positions 2 days before expiry
                return True
                
        except:
            pass
        
        return False
    
    def _exit_trade(self, trade: Trade, exit_price: float) -> Trade:
        """Exit a trade"""
        trade.exit_price = exit_price
        trade.exit_timestamp = datetime.now()
        trade.status = OrderStatus.FILLED
        
        # Final P&L calculation
        self._update_trade_pnl(trade, exit_price)
        
        # Update daily P&L
        self.daily_pnl += trade.pnl
        
        logger.info(f"Exited trade {trade.trade_id}: P&L ${trade.pnl:.2f}")
        
        return trade
    
    def get_portfolio_summary(self) -> Dict:
        """Get portfolio summary statistics"""
        total_pnl = sum(trade.pnl for trade in self.active_trades.values())
        total_pnl += sum(trade.pnl for trade in self.trade_history[-50:])  # Last 50 closed trades
        
        active_positions = len(self.active_trades)
        total_trades = len(self.trade_history) + active_positions
        
        if self.trade_history:
            winning_trades = sum(1 for t in self.trade_history if t.pnl > 0)
            win_rate = winning_trades / len(self.trade_history) * 100 if self.trade_history else 0
        else:
            win_rate = 0
        
        return {
            'total_pnl': total_pnl,
            'daily_pnl': self.daily_pnl,
            'active_positions': active_positions,
            'total_trades': total_trades,
            'win_rate': win_rate,
            'daily_risk_used': self.daily_risk_used,
            'max_daily_risk': self.max_daily_risk,
            'risk_utilization': (self.daily_risk_used / self.max_daily_risk) * 100
        }