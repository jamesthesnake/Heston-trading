"""
Delta Hedging System with ES/SPY Selection Logic
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
import logging
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)

class HedgeInstrument(Enum):
    SPY = "SPY"
    ES = "ES"

class DeltaHedger:
    """
    Maintains delta neutrality using ES futures or SPY ETF
    """
    
    def __init__(self, config: dict):
        self.config = config
        self.hedge_config = config.get('delta_hedging', {})
        
        # Delta band parameters
        self.target_delta = self.hedge_config.get('target_delta', 0.0)
        self.delta_band = self.hedge_config.get('delta_band', 0.05)  # |Normalized Delta| ≤ 0.05
        self.new_fill_threshold = self.hedge_config.get('new_fill_threshold', 0.75)  # 0.75× band
        self.spot_move_threshold = self.hedge_config.get('spot_move_bps', 10)  # 10 basis points
        
        # Instrument selection
        self.spy_spread_threshold_bps = self.hedge_config.get('spy_spread_threshold_bps', 3)
        
        # ES contract specifications
        self.es_multiplier = 50  # $50 per point
        self.es_tick_size = 0.25  # 0.25 points
        self.es_tick_value = 12.50  # $12.50 per tick
        
        # Account parameters
        self.account_equity = self.hedge_config.get('account_equity', 1000000)  # $1M default
        
        # State tracking
        self.last_hedge_time = None
        self.last_spot_price = None
        self.current_hedge_position = {
            'instrument': None,
            'quantity': 0,
            'entry_price': 0,
            'timestamp': None
        }
        
        # Portfolio tracking
        self.portfolio_delta = 0.0
        self.hedging_history = []
        self.rebalance_count = 0
    
    def rebalance_portfolio(self, active_trades: Dict, options_data: List[Dict], 
                           underlying_data: Dict) -> Dict:
        """
        Real-time portfolio delta hedging
        
        Args:
            active_trades: Dictionary of active option trades
            options_data: Current options market data
            underlying_data: Current underlying prices
            
        Returns:
            Hedging result with actions taken
        """
        try:
            # Calculate current portfolio delta
            portfolio_delta = self._calculate_portfolio_delta(active_trades, options_data, underlying_data)
            self.portfolio_delta = portfolio_delta
            
            # Get current spot price
            spot_price = underlying_data.get('SPX', {}).get('last', 5000.0)
            
            # Check if hedging is needed
            hedge_decision = self.should_hedge(portfolio_delta, spot_price)
            
            if not hedge_decision['should_hedge']:
                return {
                    'action': 'no_hedge_needed',
                    'portfolio_delta': portfolio_delta,
                    'normalized_delta': abs(portfolio_delta) / self.account_equity,
                    'reason': 'Delta within acceptable band',
                    'current_hedge': self.current_hedge_position.copy()
                }
            
            # Execute hedge
            hedge_result = self._execute_hedge(portfolio_delta, underlying_data)
            
            # Update tracking
            self.last_hedge_time = datetime.now()
            self.last_spot_price = spot_price
            self.rebalance_count += 1
            
            # Record in history
            hedge_record = {
                'timestamp': datetime.now(),
                'portfolio_delta': portfolio_delta,
                'hedge_action': hedge_result.get('action'),
                'hedge_quantity': hedge_result.get('quantity', 0),
                'hedge_instrument': hedge_result.get('instrument'),
                'spot_price': spot_price,
                'reason': hedge_decision['reason']
            }
            self.hedging_history.append(hedge_record)
            
            # Keep only recent history
            if len(self.hedging_history) > 100:
                self.hedging_history = self.hedging_history[-50:]
            
            return hedge_result
            
        except Exception as e:
            logger.error(f"Error in portfolio rebalancing: {e}")
            return {
                'action': 'error',
                'error': str(e),
                'portfolio_delta': 0,
                'current_hedge': self.current_hedge_position.copy()
            }
    
    def _calculate_portfolio_delta(self, active_trades: Dict, options_data: List[Dict], 
                                 underlying_data: Dict) -> float:
        """Calculate total portfolio delta from active trades"""
        total_delta = 0.0
        spot_price = underlying_data.get('SPX', {}).get('last', 5000.0)
        
        for trade in active_trades.values():
            try:
                # Find current option data
                option_data = None
                for option in options_data:
                    if (option.get('symbol') == trade.symbol and
                        option.get('strike') == trade.strike and
                        option.get('expiry') == trade.expiry and
                        option.get('type') == trade.option_type):
                        option_data = option
                        break
                
                if not option_data:
                    continue
                
                # Get delta from market data or calculate
                delta = option_data.get('delta', 0)
                if delta == 0:
                    # Fallback delta calculation
                    delta = self._estimate_delta(trade, spot_price)
                
                # Calculate position delta (dollar delta)
                position_delta = delta * trade.quantity * 100 * spot_price  # 100 shares per contract
                
                # Adjust for trade direction
                if trade.direction.value == 'sell':
                    position_delta *= -1
                
                total_delta += position_delta
                
            except Exception as e:
                logger.debug(f"Error calculating delta for trade {trade.trade_id}: {e}")
                continue
        
        # Add current hedge position delta
        if self.current_hedge_position['quantity'] != 0:
            hedge_delta = self._calculate_hedge_delta(underlying_data)
            total_delta += hedge_delta
        
        return total_delta
    
    def _estimate_delta(self, trade, spot_price: float) -> float:
        """Estimate option delta when not available in market data"""
        try:
            from datetime import datetime
            import math
            from scipy.stats import norm
            
            # Basic Black-Scholes delta calculation
            strike = trade.strike
            expiry_date = datetime.strptime(trade.expiry, "%Y%m%d")
            days_to_expiry = (expiry_date - datetime.now()).days
            T = max(days_to_expiry / 365.0, 0.01)  # Minimum 1% of year
            
            r = 0.05  # Risk-free rate
            q = 0.02  # Dividend yield
            vol = 0.20  # Rough volatility estimate
            
            d1 = (math.log(spot_price / strike) + (r - q + 0.5 * vol**2) * T) / (vol * math.sqrt(T))
            
            if trade.option_type == 'C':
                delta = math.exp(-q * T) * norm.cdf(d1)
            else:  # Put
                delta = -math.exp(-q * T) * norm.cdf(-d1)
            
            return delta
            
        except Exception as e:
            logger.debug(f"Delta estimation failed: {e}")
            # Fallback estimates
            moneyness = spot_price / trade.strike
            if trade.option_type == 'C':
                if moneyness > 1.1:
                    return 0.8  # Deep ITM call
                elif moneyness > 0.9:
                    return 0.5  # ATM call
                else:
                    return 0.2  # OTM call
            else:  # Put
                if moneyness < 0.9:
                    return -0.8  # Deep ITM put
                elif moneyness < 1.1:
                    return -0.5  # ATM put
                else:
                    return -0.2  # OTM put
    
    def _execute_hedge(self, portfolio_delta: float, underlying_data: Dict) -> Dict:
        """Execute hedge to neutralize portfolio delta"""
        
        # Calculate target hedge size
        spot_price = underlying_data.get('SPX', {}).get('last', 5000.0)
        spy_price = underlying_data.get('SPY', {}).get('last', 500.0)
        
        # Determine which instrument to use
        instrument = self._select_hedge_instrument(underlying_data)
        
        if instrument == HedgeInstrument.SPY:
            # Calculate SPY shares needed
            # SPY delta = 1 (moves 1:1 with SPX approximately)
            target_hedge_delta = -portfolio_delta  # Opposite to neutralize
            spy_shares_needed = target_hedge_delta / spy_price
            
            # Round to nearest share
            spy_shares = round(spy_shares_needed)
            
            if spy_shares == 0:
                return {
                    'action': 'no_hedge_needed',
                    'reason': 'Calculated hedge size is zero',
                    'portfolio_delta': portfolio_delta,
                    'instrument': instrument.value
                }
            
            # Update position
            old_position = self.current_hedge_position.copy()
            self.current_hedge_position.update({
                'instrument': instrument.value,
                'quantity': spy_shares,
                'entry_price': spy_price,
                'timestamp': datetime.now()
            })
            
            return {
                'action': 'hedge_executed',
                'instrument': instrument.value,
                'quantity': spy_shares,
                'price': spy_price,
                'old_position': old_position,
                'new_position': self.current_hedge_position.copy(),
                'portfolio_delta': portfolio_delta,
                'target_delta_hedge': target_hedge_delta
            }
            
        else:  # ES futures
            # Calculate ES contracts needed
            es_point_value = self.es_multiplier
            target_hedge_delta = -portfolio_delta
            es_contracts_needed = target_hedge_delta / (spot_price * es_point_value)
            
            # Round to nearest contract
            es_contracts = round(es_contracts_needed)
            
            if es_contracts == 0:
                return {
                    'action': 'no_hedge_needed',
                    'reason': 'Calculated hedge size is zero',
                    'portfolio_delta': portfolio_delta,
                    'instrument': instrument.value
                }
            
            # Update position
            old_position = self.current_hedge_position.copy()
            self.current_hedge_position.update({
                'instrument': instrument.value,
                'quantity': es_contracts,
                'entry_price': spot_price,  # ES price approximately equals SPX
                'timestamp': datetime.now()
            })
            
            return {
                'action': 'hedge_executed',
                'instrument': instrument.value,
                'quantity': es_contracts,
                'price': spot_price,
                'old_position': old_position,
                'new_position': self.current_hedge_position.copy(),
                'portfolio_delta': portfolio_delta,
                'target_delta_hedge': target_hedge_delta
            }
    
    def _calculate_hedge_delta(self, underlying_data: Dict) -> float:
        """Calculate delta contribution from current hedge position"""
        if self.current_hedge_position['quantity'] == 0:
            return 0.0
        
        instrument = self.current_hedge_position['instrument']
        quantity = self.current_hedge_position['quantity']
        
        if instrument == 'SPY':
            spy_price = underlying_data.get('SPY', {}).get('last', 500.0)
            return quantity * spy_price  # SPY has delta ≈ 1
        elif instrument == 'ES':
            spot_price = underlying_data.get('SPX', {}).get('last', 5000.0)
            return quantity * spot_price * self.es_multiplier  # ES delta
        
        return 0.0
        
    def should_hedge(self, portfolio_delta: float, spot_price: float, 
                    new_fill_delta: Optional[float] = None) -> Dict[str, bool]:
        """
        Determine if hedging is required based on delta band and triggers
        
        Args:
            portfolio_delta: Current portfolio dollar delta
            spot_price: Current SPX spot price
            new_fill_delta: Delta from new fill (if any)
            
        Returns:
            Dict with hedge triggers and reasons
        """
        
        # Calculate normalized delta
        normalized_delta = abs(portfolio_delta) / self.account_equity
        
        triggers = {
            'delta_band_breach': False,
            'new_fill_trigger': False,
            'spot_move_trigger': False,
            'should_hedge': False,
            'reason': None
        }
        
        # Check delta band breach
        if normalized_delta > self.delta_band:
            triggers['delta_band_breach'] = True
            triggers['reason'] = f"Delta band breached: {normalized_delta:.4f} > {self.delta_band}"
        
        # Check new fill trigger
        if new_fill_delta is not None:
            new_normalized_delta = abs(new_fill_delta) / self.account_equity
            if new_normalized_delta > self.new_fill_threshold * self.delta_band:
                triggers['new_fill_trigger'] = True
                triggers['reason'] = f"New fill delta trigger: {new_normalized_delta:.4f}"
        
        # Check spot move trigger
        if self.last_spot_price is not None:
            spot_move_bps = abs(spot_price - self.last_spot_price) / self.last_spot_price * 10000
            if spot_move_bps > self.spot_move_threshold:
                triggers['spot_move_trigger'] = True
                triggers['reason'] = f"Spot moved {spot_move_bps:.1f} bps"
        
        # Overall hedge decision
        triggers['should_hedge'] = any([
            triggers['delta_band_breach'],
            triggers['new_fill_trigger'], 
            triggers['spot_move_trigger']
        ])
        
        return triggers
    
    def select_hedge_instrument(self, spy_data: Dict, es_data: Dict) -> HedgeInstrument:
        """
        Select optimal hedging instrument based on spread and liquidity
        
        Args:
            spy_data: SPY market data {bid, ask, last, volume}
            es_data: ES futures market data {bid, ask, last, volume}
            
        Returns:
            Selected hedge instrument
        """
        
        # Calculate SPY spread in basis points
        spy_bid = spy_data.get('bid', 0)
        spy_ask = spy_data.get('ask', 0)
        spy_mid = (spy_bid + spy_ask) / 2 if spy_bid > 0 and spy_ask > 0 else 0
        
        if spy_mid > 0:
            spy_spread_bps = (spy_ask - spy_bid) / spy_mid * 10000
        else:
            spy_spread_bps = float('inf')
        
        # Use ES if SPY spread is too wide
        if spy_spread_bps > self.spy_spread_threshold_bps:
            logger.info(f"Using ES: SPY spread {spy_spread_bps:.1f} bps > {self.spy_spread_threshold_bps} bps")
            return HedgeInstrument.ES
        else:
            logger.info(f"Using SPY: spread {spy_spread_bps:.1f} bps")
            return HedgeInstrument.SPY
    
    def calculate_hedge_size(self, portfolio_delta: float, spot_price: float, 
                           spy_price: float, instrument: HedgeInstrument) -> Dict:
        """
        Calculate hedge size to neutralize portfolio delta
        
        Args:
            portfolio_delta: Current portfolio dollar delta
            spot_price: Current SPX spot price  
            spy_price: Current SPY price
            instrument: Selected hedge instrument
            
        Returns:
            Hedge calculation results
        """
        
        if instrument == HedgeInstrument.ES:
            # ES contracts = round(-Portfolio_Delta × Multiplier / 50)
            # Assuming multiplier is 100 (standard for index options)
            multiplier = 100
            es_contracts = round(-portfolio_delta * multiplier / self.es_multiplier)
            
            return {
                'instrument': 'ES',
                'quantity': es_contracts,
                'dollar_hedge': es_contracts * self.es_multiplier,
                'hedge_ratio': es_contracts * self.es_multiplier / (portfolio_delta * multiplier) if portfolio_delta != 0 else 0
            }
            
        else:  # SPY
            # SPY shares = round(-Portfolio_Delta × Multiplier × SPX_Level / SPY_Price)
            multiplier = 100
            spy_shares = round(-portfolio_delta * multiplier * spot_price / spy_price)
            
            return {
                'instrument': 'SPY',
                'quantity': spy_shares,
                'dollar_hedge': spy_shares * spy_price,
                'hedge_ratio': (spy_shares * spy_price) / (portfolio_delta * multiplier * spot_price) if portfolio_delta != 0 else 0
            }
    
    def generate_hedge_order(self, hedge_calc: Dict, market_data: Dict) -> Dict:
        """
        Generate hedge order with appropriate pricing
        
        Args:
            hedge_calc: Hedge calculation from calculate_hedge_size
            market_data: Current market data for hedge instrument
            
        Returns:
            Hedge order specification
        """
        
        instrument = hedge_calc['instrument']
        quantity = hedge_calc['quantity']
        
        if quantity == 0:
            return None
        
        # Determine order side
        side = 'BUY' if quantity > 0 else 'SELL'
        abs_quantity = abs(quantity)
        
        # Set order price (use midpoint for limit orders)
        bid = market_data.get('bid', 0)
        ask = market_data.get('ask', 0)
        
        if bid > 0 and ask > 0:
            mid_price = (bid + ask) / 2
            
            # For ES, round to tick size
            if instrument == 'ES':
                mid_price = round(mid_price / self.es_tick_size) * self.es_tick_size
        else:
            mid_price = market_data.get('last', 0)
        
        order = {
            'instrument': instrument,
            'side': side,
            'quantity': abs_quantity,
            'order_type': 'LMT',
            'limit_price': mid_price,
            'time_in_force': 'DAY',
            'hedge_reason': 'delta_neutrality',
            'timestamp': datetime.now()
        }
        
        return order
    
    def update_hedge_position(self, fill: Dict):
        """
        Update current hedge position after fill
        
        Args:
            fill: Fill data {instrument, side, quantity, price, timestamp}
        """
        
        instrument = fill['instrument']
        side = fill['side']
        quantity = fill['quantity']
        price = fill['price']
        
        # Convert to signed quantity
        signed_quantity = quantity if side == 'BUY' else -quantity
        
        # Update position
        if self.current_hedge_position['instrument'] == instrument:
            # Add to existing position
            old_qty = self.current_hedge_position['quantity']
            new_qty = old_qty + signed_quantity
            
            # Update average price if position increases
            if (old_qty >= 0 and signed_quantity > 0) or (old_qty <= 0 and signed_quantity < 0):
                old_notional = old_qty * self.current_hedge_position['entry_price']
                new_notional = signed_quantity * price
                total_notional = old_notional + new_notional
                
                if new_qty != 0:
                    avg_price = total_notional / new_qty
                else:
                    avg_price = 0
                    
                self.current_hedge_position['entry_price'] = avg_price
            
            self.current_hedge_position['quantity'] = new_qty
            
        else:
            # New instrument, replace position
            self.current_hedge_position = {
                'instrument': instrument,
                'quantity': signed_quantity,
                'entry_price': price,
                'timestamp': fill['timestamp']
            }
        
        # Clean up zero positions
        if self.current_hedge_position['quantity'] == 0:
            self.current_hedge_position = {
                'instrument': None,
                'quantity': 0,
                'entry_price': 0,
                'timestamp': None
            }
        
        logger.info(f"Updated hedge position: {self.current_hedge_position}")
    
    def get_hedge_pnl(self, current_prices: Dict[str, float]) -> float:
        """
        Calculate current P&L on hedge position
        
        Args:
            current_prices: Current prices {SPY: price, ES: price}
            
        Returns:
            Hedge P&L in dollars
        """
        
        if self.current_hedge_position['quantity'] == 0:
            return 0.0
        
        instrument = self.current_hedge_position['instrument']
        quantity = self.current_hedge_position['quantity']
        entry_price = self.current_hedge_position['entry_price']
        
        current_price = current_prices.get(instrument, entry_price)
        
        if instrument == 'ES':
            # ES P&L = contracts × (current_price - entry_price) × multiplier
            pnl = quantity * (current_price - entry_price) * self.es_multiplier
        else:  # SPY
            # SPY P&L = shares × (current_price - entry_price)
            pnl = quantity * (current_price - entry_price)
        
        return pnl
    
    def get_hedge_delta(self, spot_price: float, spy_price: float) -> float:
        """
        Calculate delta contribution from current hedge position
        
        Args:
            spot_price: Current SPX spot price
            spy_price: Current SPY price
            
        Returns:
            Hedge delta in dollars
        """
        
        if self.current_hedge_position['quantity'] == 0:
            return 0.0
        
        instrument = self.current_hedge_position['instrument']
        quantity = self.current_hedge_position['quantity']
        
        if instrument == 'ES':
            # ES delta ≈ contracts × multiplier (assuming ES tracks SPX 1:1)
            hedge_delta = quantity * self.es_multiplier
        else:  # SPY
            # SPY delta = shares × (SPY_price / SPX_price) × SPX_price = shares × SPY_price
            hedge_delta = quantity * spy_price
        
        return hedge_delta
    
    def check_hedge_health(self, portfolio_delta: float, spot_price: float, 
                          spy_price: float) -> Dict:
        """
        Check health of current hedge position
        
        Args:
            portfolio_delta: Current portfolio delta
            spot_price: Current SPX spot price
            spy_price: Current SPY price
            
        Returns:
            Hedge health metrics
        """
        
        hedge_delta = self.get_hedge_delta(spot_price, spy_price)
        net_delta = portfolio_delta + hedge_delta
        normalized_net_delta = abs(net_delta) / self.account_equity
        
        return {
            'portfolio_delta': portfolio_delta,
            'hedge_delta': hedge_delta,
            'net_delta': net_delta,
            'normalized_net_delta': normalized_net_delta,
            'within_band': normalized_net_delta <= self.delta_band,
            'hedge_position': self.current_hedge_position.copy(),
            'timestamp': datetime.now()
        }
    
    def get_statistics(self) -> Dict:
        """Get hedging statistics"""
        
        return {
            'current_position': self.current_hedge_position.copy(),
            'delta_band': self.delta_band,
            'target_delta': self.target_delta,
            'last_hedge_time': self.last_hedge_time,
            'account_equity': self.account_equity
        }
