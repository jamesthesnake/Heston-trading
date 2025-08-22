"""
Portfolio Manager - Position and Risk Management Module
Handles position tracking, P&L calculation, and delta hedging
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from .delta_hedger import DeltaHedger
from .trade_executor import TradeExecutor

logger = logging.getLogger(__name__)

@dataclass
class PositionSummary:
    """Summary of portfolio positions"""
    active_positions: int = 0
    total_pnl: float = 0.0
    daily_pnl: float = 0.0
    total_delta: float = 0.0
    total_gamma: float = 0.0
    total_theta: float = 0.0
    total_vega: float = 0.0
    win_rate: float = 0.0
    risk_utilization: float = 0.0

class PortfolioManager:
    """
    Portfolio manager responsible for position tracking, P&L calculation,
    risk management, and delta hedging coordination
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the portfolio manager
        
        Args:
            config: Portfolio configuration
        """
        self.config = config
        self.risk_config = config.get('risk_management', {})
        self.delta_config = config.get('delta_hedging', {})
        
        # Core components
        self.trade_executor = TradeExecutor(config)
        self.delta_hedger = DeltaHedger(config)
        
        # Portfolio state
        self.is_initialized = False
        self.positions_history = []
        self.pnl_history = []
        self.hedge_history = []
        
        # Risk management parameters
        self.max_portfolio_delta = self.risk_config.get('max_portfolio_delta', 50000.0)
        self.max_daily_loss = self.risk_config.get('max_daily_loss', 10000.0)
        self.max_position_size = self.risk_config.get('max_position_size', 100)
        
        # Delta hedging parameters
        self.delta_band = self.delta_config.get('delta_band', 0.05)
        self.hedge_frequency = self.delta_config.get('hedge_frequency', 60)  # seconds
        self.last_hedge_check = None
        
        # Performance tracking
        self.daily_stats = {
            'start_pnl': 0.0,
            'peak_pnl': 0.0,
            'trough_pnl': 0.0,
            'positions_opened': 0,
            'positions_closed': 0,
            'hedges_executed': 0,
            'start_time': datetime.now()
        }
        
        logger.info("Portfolio manager initialized")
    
    async def initialize(self) -> bool:
        """
        Initialize the portfolio manager
        
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            logger.info("Initializing portfolio manager...")
            
            # Initialize trade executor
            if not hasattr(self.trade_executor, 'active_trades'):
                logger.debug("Trade executor already initialized")
            
            # Initialize delta hedger
            if not hasattr(self.delta_hedger, 'portfolio_delta'):
                self.delta_hedger.portfolio_delta = 0.0
            
            # Reset daily stats
            self.daily_stats = {
                'start_pnl': 0.0,
                'peak_pnl': 0.0,
                'trough_pnl': 0.0,
                'positions_opened': 0,
                'positions_closed': 0,
                'hedges_executed': 0,
                'start_time': datetime.now()
            }
            
            self.is_initialized = True
            logger.info("✅ Portfolio manager initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Portfolio manager initialization failed: {e}")
            return False
    
    async def update_positions(self, executed_trades: List[Any], 
                              market_data: Dict[str, Any], 
                              theoretical_prices: Dict[str, float]) -> Dict[str, Any]:
        """
        Update portfolio positions with new trades and market data
        
        Args:
            executed_trades: List of newly executed trades
            market_data: Current market data
            theoretical_prices: Current theoretical option prices
            
        Returns:
            Dictionary with update results
        """
        if not self.is_initialized:
            return {'success': False, 'error': 'Portfolio manager not initialized'}
        
        try:
            update_start = datetime.now()
            
            # 1. Process new trades
            new_positions_count = len(executed_trades)
            if executed_trades:
                logger.info(f"📈 Adding {new_positions_count} new positions to portfolio")
                self.daily_stats['positions_opened'] += new_positions_count
            
            # 2. Update existing positions with current market data
            options_data = market_data.get('options', [])
            updated_positions = self.trade_executor.update_positions(options_data)
            
            if updated_positions:
                logger.debug(f"Updated {len(updated_positions)} existing positions")
            
            # 3. Calculate current portfolio summary
            portfolio_summary = self._calculate_portfolio_summary()
            
            # 4. Update P&L tracking
            self._update_pnl_tracking(portfolio_summary)
            
            # 5. Check for position closures
            closed_positions = self._check_position_closures()
            if closed_positions:
                logger.info(f"🔄 Closed {closed_positions} positions")
                self.daily_stats['positions_closed'] += closed_positions
            
            update_time = (datetime.now() - update_start).total_seconds()
            
            return {
                'success': True,
                'new_positions': new_positions_count,
                'updated_positions': len(updated_positions),
                'closed_positions': closed_positions,
                'portfolio_summary': portfolio_summary,
                'update_time': update_time
            }
            
        except Exception as e:
            logger.error(f"Error updating positions: {e}")
            return {'success': False, 'error': str(e)}
    
    async def manage_risk(self, underlying_data: Dict[str, Any], 
                         options_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Perform risk management including delta hedging
        
        Args:
            underlying_data: Current underlying market data
            options_data: Current options market data
            
        Returns:
            Dictionary with risk management results
        """
        try:
            risk_start = datetime.now()
            
            # 1. Check portfolio risk limits
            risk_check_result = self._check_risk_limits()
            
            if risk_check_result.get('violations'):
                logger.warning(f"⚠️ Risk violations detected: {risk_check_result['violations']}")
            
            # 2. Perform delta hedging if needed
            hedge_result = await self._perform_delta_hedging(underlying_data, options_data)
            
            # 3. Check for stop losses or position adjustments
            position_adjustments = self._check_position_adjustments()
            
            risk_time = (datetime.now() - risk_start).total_seconds()
            
            return {
                'success': True,
                'risk_check': risk_check_result,
                'hedge_result': hedge_result,
                'position_adjustments': position_adjustments,
                'risk_management_time': risk_time
            }
            
        except Exception as e:
            logger.error(f"Error in risk management: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _perform_delta_hedging(self, underlying_data: Dict[str, Any], 
                                    options_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Perform delta hedging if needed"""
        try:
            # Check if hedging is needed
            if not self._should_hedge():
                return {'action': 'no_hedge_needed', 'reason': 'Too soon since last hedge'}
            
            # Get active trades
            active_trades = self.trade_executor.get_active_trades()
            
            if not active_trades:
                return {'action': 'no_hedge_needed', 'reason': 'No active positions'}
            
            # Perform delta hedging
            hedge_result = self.delta_hedger.rebalance_portfolio(
                active_trades, options_data, underlying_data
            )
            
            self.last_hedge_check = datetime.now()
            
            if hedge_result.get('action') == 'hedge_executed':
                logger.info(f"⚖️ Delta hedge executed: {hedge_result.get('quantity')} "
                          f"{hedge_result.get('instrument')} @ ${hedge_result.get('price', 0):.2f}")
                self.daily_stats['hedges_executed'] += 1
                
                # Store hedge in history
                self.hedge_history.append({
                    'timestamp': datetime.now(),
                    'action': hedge_result.get('action'),
                    'quantity': hedge_result.get('quantity'),
                    'instrument': hedge_result.get('instrument'),
                    'price': hedge_result.get('price'),
                    'portfolio_delta_before': hedge_result.get('portfolio_delta_before'),
                    'portfolio_delta_after': hedge_result.get('portfolio_delta_after')
                })
            
            return hedge_result
            
        except Exception as e:
            logger.error(f"Error in delta hedging: {e}")
            return {'action': 'error', 'error': str(e)}
    
    def _calculate_portfolio_summary(self) -> PositionSummary:
        """Calculate current portfolio summary"""
        try:
            summary = PositionSummary()
            
            # Get portfolio summary from trade executor
            portfolio_data = self.trade_executor.get_portfolio_summary()
            
            summary.active_positions = portfolio_data.get('active_positions', 0)
            summary.total_pnl = portfolio_data.get('total_pnl', 0.0)
            summary.daily_pnl = portfolio_data.get('daily_pnl', 0.0)
            summary.win_rate = portfolio_data.get('win_rate', 0.0)
            summary.risk_utilization = portfolio_data.get('risk_utilization', 0.0)
            
            # Calculate Greeks if we have active positions
            if hasattr(self.delta_hedger, 'portfolio_delta'):
                summary.total_delta = self.delta_hedger.portfolio_delta
            
            # Additional Greeks would be calculated here from active trades
            # For now, using placeholder values
            summary.total_gamma = 0.0
            summary.total_theta = 0.0
            summary.total_vega = 0.0
            
            return summary
            
        except Exception as e:
            logger.error(f"Error calculating portfolio summary: {e}")
            return PositionSummary()
    
    def _update_pnl_tracking(self, portfolio_summary: PositionSummary):
        """Update P&L tracking and statistics"""
        try:
            current_pnl = portfolio_summary.total_pnl
            
            # Update daily stats
            if current_pnl > self.daily_stats['peak_pnl']:
                self.daily_stats['peak_pnl'] = current_pnl
            
            if current_pnl < self.daily_stats['trough_pnl']:
                self.daily_stats['trough_pnl'] = current_pnl
            
            # Store P&L history
            pnl_entry = {
                'timestamp': datetime.now(),
                'total_pnl': current_pnl,
                'daily_pnl': portfolio_summary.daily_pnl,
                'active_positions': portfolio_summary.active_positions,
                'portfolio_delta': portfolio_summary.total_delta
            }
            
            self.pnl_history.append(pnl_entry)
            
            # Keep only recent history
            if len(self.pnl_history) > 1000:
                self.pnl_history = self.pnl_history[-500:]
                
        except Exception as e:
            logger.error(f"Error updating P&L tracking: {e}")
    
    def _check_risk_limits(self) -> Dict[str, Any]:
        """Check portfolio against risk limits"""
        try:
            violations = []
            portfolio_summary = self._calculate_portfolio_summary()
            
            # Check portfolio delta limit
            abs_delta = abs(portfolio_summary.total_delta)
            if abs_delta > self.max_portfolio_delta:
                violations.append(f"Portfolio delta ${abs_delta:,.0f} exceeds limit ${self.max_portfolio_delta:,.0f}")
            
            # Check daily loss limit
            if portfolio_summary.daily_pnl < -self.max_daily_loss:
                violations.append(f"Daily loss ${portfolio_summary.daily_pnl:,.2f} exceeds limit ${self.max_daily_loss:,.2f}")
            
            # Check individual position sizes
            active_trades = self.trade_executor.get_active_trades()
            for trade_id, trade in active_trades.items():
                if abs(trade.quantity) > self.max_position_size:
                    violations.append(f"Position {trade_id} size {trade.quantity} exceeds limit {self.max_position_size}")
            
            return {
                'violations': violations,
                'risk_metrics': {
                    'portfolio_delta': portfolio_summary.total_delta,
                    'daily_pnl': portfolio_summary.daily_pnl,
                    'max_position_size': max([abs(t.quantity) for t in active_trades.values()]) if active_trades else 0
                }
            }
            
        except Exception as e:
            logger.error(f"Error checking risk limits: {e}")
            return {'violations': [f"Risk check error: {e}"]}
    
    def _check_position_closures(self) -> int:
        """Check for positions that should be closed"""
        try:
            # This would implement logic to check for position closures
            # based on stop losses, time decay, etc.
            # For now, return 0
            return 0
            
        except Exception as e:
            logger.error(f"Error checking position closures: {e}")
            return 0
    
    def _check_position_adjustments(self) -> Dict[str, Any]:
        """Check for positions that need adjustments"""
        try:
            # This would implement logic to check for position adjustments
            # based on risk parameters, market conditions, etc.
            return {'adjustments_needed': 0, 'adjustments': []}
            
        except Exception as e:
            logger.error(f"Error checking position adjustments: {e}")
            return {'adjustments_needed': 0, 'adjustments': [], 'error': str(e)}
    
    def _should_hedge(self) -> bool:
        """Check if delta hedging is needed"""
        if not self.last_hedge_check:
            return True
        
        time_since_hedge = datetime.now() - self.last_hedge_check
        return time_since_hedge.total_seconds() >= self.hedge_frequency
    
    # Public API methods
    
    def get_status(self) -> Dict[str, Any]:
        """Get current portfolio manager status"""
        try:
            portfolio_summary = self._calculate_portfolio_summary()
            
            return {
                'is_initialized': self.is_initialized,
                'active_positions': portfolio_summary.active_positions,
                'total_pnl': portfolio_summary.total_pnl,
                'daily_pnl': portfolio_summary.daily_pnl,
                'portfolio_delta': portfolio_summary.total_delta,
                'last_hedge_check': self.last_hedge_check,
                'daily_stats': self.daily_stats.copy()
            }
        except Exception as e:
            return {'error': str(e)}
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get portfolio performance summary"""
        try:
            portfolio_summary = self._calculate_portfolio_summary()
            
            # Calculate performance metrics
            runtime_hours = (datetime.now() - self.daily_stats['start_time']).total_seconds() / 3600
            
            return {
                'current_portfolio': {
                    'active_positions': portfolio_summary.active_positions,
                    'total_pnl': portfolio_summary.total_pnl,
                    'daily_pnl': portfolio_summary.daily_pnl,
                    'win_rate': portfolio_summary.win_rate,
                    'portfolio_delta': portfolio_summary.total_delta
                },
                'daily_performance': {
                    'peak_pnl': self.daily_stats['peak_pnl'],
                    'trough_pnl': self.daily_stats['trough_pnl'],
                    'positions_opened': self.daily_stats['positions_opened'],
                    'positions_closed': self.daily_stats['positions_closed'],
                    'hedges_executed': self.daily_stats['hedges_executed'],
                    'runtime_hours': runtime_hours
                },
                'risk_metrics': self._check_risk_limits()
            }
        except Exception as e:
            return {'error': str(e)}
    
    def get_positions_detail(self) -> Dict[str, Any]:
        """Get detailed position information"""
        try:
            active_trades = self.trade_executor.get_active_trades()
            
            positions_detail = []
            for trade_id, trade in active_trades.items():
                positions_detail.append({
                    'trade_id': trade_id,
                    'symbol': trade.symbol,
                    'strike': trade.strike,
                    'option_type': trade.option_type,
                    'quantity': trade.quantity,
                    'entry_price': trade.entry_price,
                    'current_price': getattr(trade, 'current_price', 0),
                    'pnl': getattr(trade, 'unrealized_pnl', 0),
                    'delta': getattr(trade, 'delta', 0)
                })
            
            return {
                'total_positions': len(positions_detail),
                'positions': positions_detail
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    async def shutdown(self):
        """Shutdown the portfolio manager"""
        try:
            logger.info("Shutting down portfolio manager...")
            
            # Final portfolio summary
            final_summary = self.get_performance_summary()
            logger.info(f"Final portfolio summary: {final_summary}")
            
            self.is_initialized = False
            
            logger.info("✅ Portfolio manager shutdown complete")
            
        except Exception as e:
            logger.error(f"Error shutting down portfolio manager: {e}")