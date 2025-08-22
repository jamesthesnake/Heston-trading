"""
SPX/XSP Options Mispricing Strategy - Main Orchestrator
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
import logging
from datetime import datetime, timedelta
import asyncio
from dataclasses import dataclass

from .heston_strategy import HestonModel
from .calibration import HestonCalibrator
from .signal_engine import SignalEngine
from .dividend_extractor import DividendExtractor
from .position_sizer import PositionSizer
from .delta_hedger import DeltaHedger
from .risk_manager import RiskManager, RiskLevel, RiskAction

logger = logging.getLogger(__name__)

@dataclass
class StrategyState:
    """Current strategy state"""
    is_running: bool = False
    last_calibration: Optional[datetime] = None
    current_model: Optional[HestonModel] = None
    positions: List[Dict] = None
    daily_pnl: float = 0.0
    risk_level: RiskLevel = RiskLevel.NORMAL
    
    def __post_init__(self):
        if self.positions is None:
            self.positions = []

class MispricingStrategy:
    """
    Main strategy orchestrator implementing the SPX/XSP options mispricing strategy
    """
    
    def __init__(self, config: dict):
        self.config = config
        self.strategy_config = config.get('strategy', {})
        
        # Initialize components
        self.calibrator = HestonCalibrator(config)
        self.signal_engine = SignalEngine(config)
        self.dividend_extractor = DividendExtractor(config)
        self.position_sizer = PositionSizer(config)
        self.delta_hedger = DeltaHedger(config)
        self.risk_manager = RiskManager(config)
        
        # Strategy parameters
        self.calibration_interval = self.strategy_config.get('calibration_interval_min', 10)
        self.signal_interval = self.strategy_config.get('signal_interval_sec', 5)
        self.max_slippage_bps = self.strategy_config.get('max_slippage_bps', 15)
        
        # Time filters
        self.market_open = self.strategy_config.get('market_open_hour', 9.5)  # 9:30 AM
        self.market_close = self.strategy_config.get('market_close_hour', 16.0)  # 4:00 PM
        self.tod_block_min = self.strategy_config.get('tod_block_min', 15)  # 15 minutes
        
        # State
        self.state = StrategyState()
        self.last_signal_time = None
        self.last_hedge_check = None
        
        # Performance tracking
        self.trade_history = []
        self.pnl_history = []
    
    async def start(self):
        """Start the real Heston trading strategy"""
        logger.info("MispricingStrategy started - implementing full Heston strategy")
        self.state.is_running = True
        
        # Import the new components
        from .heston_pricing_engine import HestonPricingEngine
        from .mispricing_detector import MispricingDetector
        from .trade_executor import TradeExecutor
        from .delta_hedger import DeltaHedger
        
        # Initialize strategy components
        try:
            self.pricing_engine = HestonPricingEngine(self.config)
            self.mispricing_detector = MispricingDetector(self.config)
            self.trade_executor = TradeExecutor(self.config)
            self.delta_hedger = DeltaHedger(self.config)
            
            logger.info("✓ All Heston strategy components initialized")
            
            # Strategy loop interval
            loop_interval = self.config.get('strategy_loop_interval', 5.0)  # 5 seconds
            
            while self.state.is_running:
                try:
                    await self._execute_strategy_cycle()
                    await asyncio.sleep(loop_interval)
                except Exception as e:
                    logger.error(f"Error in strategy cycle: {e}")
                    await asyncio.sleep(loop_interval * 2)  # Wait longer on error
                    
        except KeyboardInterrupt:
            logger.info("Strategy stopping...")
        except Exception as e:
            logger.error(f"Strategy initialization failed: {e}")
        finally:
            self.state.is_running = False
            logger.info("MispricingStrategy stopped")
    
    async def _execute_strategy_cycle(self):
        """Execute one complete Heston strategy cycle"""
        
        # This would normally get data from the feed manager
        # For now, we'll use the enhanced mock data
        from ..data.enhanced_mock_generator import enhanced_mock
        
        try:
            # 1. Get current market data
            underlying_data = enhanced_mock.generate_underlying_snapshot()
            options_data = enhanced_mock.generate_options_snapshot(underlying_data)
            
            if not options_data:
                logger.debug("No options data available for strategy cycle")
                return
            
            # 2. Calculate theoretical prices using calibrated Heston model
            theoretical_prices = self.pricing_engine.get_theoretical_prices(options_data, underlying_data)
            
            if not theoretical_prices:
                logger.debug("No theoretical prices calculated")
                return
            
            # 3. Detect mispricings
            mispricing_signals = self.mispricing_detector.detect_mispricings(
                options_data, theoretical_prices, underlying_data
            )
            
            if mispricing_signals:
                logger.info(f"Found {len(mispricing_signals)} mispricing signals")
                
                # Get signal summary
                signal_summary = self.mispricing_detector.get_signal_summary(mispricing_signals)
                logger.info(f"Signal summary: {signal_summary['strong_signals']} strong signals, "
                          f"avg mispricing: {signal_summary['avg_mispricing']:.1f}%")
            
            # 4. Execute trades based on signals
            if mispricing_signals:
                executed_trades = self.trade_executor.execute_signals(
                    mispricing_signals, options_data, underlying_data
                )
                
                if executed_trades:
                    logger.info(f"Executed {len(executed_trades)} new trades")
            
            # 5. Update existing positions
            updated_trades = self.trade_executor.update_positions(options_data)
            if updated_trades:
                logger.info(f"Updated {len(updated_trades)} positions")
            
            # 6. Perform delta hedging
            if self.trade_executor.active_trades:
                hedge_result = self.delta_hedger.rebalance_portfolio(
                    self.trade_executor.active_trades, options_data, underlying_data
                )
                
                if hedge_result.get('action') == 'hedge_executed':
                    logger.info(f"Delta hedge executed: {hedge_result.get('quantity')} "
                              f"{hedge_result.get('instrument')}")
            
            # 7. Update strategy state
            self._update_strategy_metrics()
            
        except Exception as e:
            logger.error(f"Strategy cycle error: {e}")
            raise
    
    def _update_strategy_metrics(self):
        """Update strategy performance metrics"""
        try:
            # Get portfolio summary
            portfolio_summary = self.trade_executor.get_portfolio_summary()
            
            # Update strategy state
            self.state.daily_pnl = portfolio_summary.get('daily_pnl', 0)
            
            # Update position count
            self.state.positions = list(self.trade_executor.active_trades.values())
            
            # Store latest metrics
            self.pnl_history.append({
                'timestamp': datetime.now(),
                'pnl': portfolio_summary.get('total_pnl', 0),
                'daily_pnl': portfolio_summary.get('daily_pnl', 0),
                'active_positions': portfolio_summary.get('active_positions', 0),
                'win_rate': portfolio_summary.get('win_rate', 0)
            })
            
            # Keep only recent history
            if len(self.pnl_history) > 1000:
                self.pnl_history = self.pnl_history[-500:]
                
        except Exception as e:
            logger.error(f"Error updating strategy metrics: {e}")
    
    def get_strategy_status(self) -> Dict:
        """Get current strategy status for dashboard"""
        try:
            portfolio_summary = getattr(self.trade_executor, 'get_portfolio_summary', lambda: {})()
            calibration_status = getattr(self.pricing_engine, 'get_calibration_status', lambda: {})()
            
            return {
                'is_running': self.state.is_running,
                'position_count': len(getattr(self.trade_executor, 'active_trades', {})),
                'risk_level': 'normal',  # Could be enhanced based on portfolio metrics
                'daily_pnl': portfolio_summary.get('daily_pnl', 0),
                'total_pnl': portfolio_summary.get('total_pnl', 0),
                'win_rate': portfolio_summary.get('win_rate', 0),
                'calibration_status': calibration_status.get('status', 'unknown'),
                'portfolio_delta': getattr(self.delta_hedger, 'portfolio_delta', 0),
                'hedge_position': getattr(self.delta_hedger, 'current_hedge_position', {})
            }
        except Exception as e:
            logger.error(f"Error getting strategy status: {e}")
            return {
                'is_running': self.state.is_running,
                'position_count': 0,
                'risk_level': 'error',
                'error': str(e)
            }
    
    def stop(self):
        """Stop the strategy"""
        self.state.is_running = False
        
    async def run_strategy_loop(self, market_data_feed):
        """
        Main strategy execution loop
        
        Args:
            market_data_feed: Async generator yielding market data snapshots
        """
        
        logger.info("Starting mispricing strategy")
        self.state.is_running = True
        
        try:
            async for market_snapshot in market_data_feed:
                await self._process_market_snapshot(market_snapshot)
                
        except Exception as e:
            logger.error(f"Strategy loop error: {e}")
            await self._emergency_shutdown()
        finally:
            self.state.is_running = False
            logger.info("Strategy stopped")
    
    async def _process_market_snapshot(self, snapshot: Dict):
        """Process a single market data snapshot"""
        
        timestamp = snapshot.get('timestamp', datetime.now())
        
        # Check if market is open
        if not self._is_market_open(timestamp):
            return
        
        # Check for end-of-day position flattening
        if self._should_flatten_positions(timestamp):
            await self._flatten_all_positions(snapshot)
            return
        
        # Update risk manager with current P&L
        current_pnl = self._calculate_current_pnl(snapshot)
        self.risk_manager.update_daily_pnl(current_pnl)
        
        # Risk check
        risk_assessment = self.risk_manager.check_risk_limits(
            self.state.positions, current_pnl, snapshot
        )
        
        self.state.risk_level = risk_assessment['risk_level']
        
        # Handle risk actions
        if risk_assessment['action'] == RiskAction.EMERGENCY_STOP:
            await self._emergency_shutdown()
            return
        elif risk_assessment['action'] == RiskAction.CLOSE_ALL:
            await self._close_all_positions(snapshot)
            return
        
        # Model calibration (every 10 minutes)
        if self._should_calibrate():
            await self._calibrate_model(snapshot)
        
        # Skip signal generation if no valid model
        if self.state.current_model is None:
            return
        
        # Generate trading signals (every 5 seconds)
        if self._should_generate_signals():
            await self._generate_and_process_signals(snapshot)
        
        # Delta hedging check
        if self._should_check_hedge():
            await self._check_delta_hedge(snapshot)
    
    async def _calibrate_model(self, snapshot: Dict):
        """Calibrate Heston model to current market"""
        
        logger.info("Starting model calibration")
        
        try:
            # Extract dividend yield
            options_data = snapshot.get('options', pd.DataFrame())
            spot = snapshot.get('underlying', {}).get('SPX', {}).get('last', 5000)
            
            dividend_yield = self.dividend_extractor.extract_dividend_yield(
                options_data, spot, snapshot.get('rates', {0.05: 0.05})
            )
            
            # Build yield curve
            q_curve = self.dividend_extractor.get_yield_curve([0.03, 0.08, 0.14])
            
            # Prepare IV surface
            iv_surface = self._prepare_iv_surface(options_data)
            
            # Calibrate model
            calibration_result = self.calibrator.calibrate(
                iv_surface, spot, 
                snapshot.get('rates', {0.05: 0.05}), 
                q_curve
            )
            
            # Update model if calibration passed QC
            if calibration_result['qc_passed']:
                self.state.current_model = HestonModel(**calibration_result['params'])
                self.state.last_calibration = datetime.now()
                logger.info(f"Model calibrated successfully: RMSE={calibration_result['rmse']:.4f}")
            else:
                logger.warning(f"Calibration rejected: {calibration_result['qc_details']['reason']}")
                
        except Exception as e:
            logger.error(f"Calibration error: {e}")
    
    async def _generate_and_process_signals(self, snapshot: Dict):
        """Generate and process trading signals"""
        
        try:
            # Get market IV data
            market_iv = self._extract_market_iv(snapshot)
            
            # Generate model surface
            model_surface = self._generate_model_surface(snapshot)
            
            # Generate signals
            signals = self.signal_engine.compute_signals(
                market_iv, model_surface, 
                snapshot.get('underlying', {}).get('SPX', {}).get('last', 5000)
            )
            
            # Process each signal
            for signal in signals:
                await self._process_signal(signal, snapshot)
                
            # Check exits for existing positions
            current_z = self.signal_engine._compute_z_scores(market_iv, model_surface)
            exits = self.signal_engine.check_exits(self.state.positions, current_z)
            
            for exit_signal in exits:
                await self._process_exit(exit_signal, snapshot)
                
            self.last_signal_time = datetime.now()
            
        except Exception as e:
            logger.error(f"Signal generation error: {e}")
    
    async def _process_signal(self, signal: Dict, snapshot: Dict):
        """Process a single trading signal"""
        
        # Check risk gates
        if self.state.risk_level != RiskLevel.NORMAL:
            logger.debug(f"Blocking signal due to risk level: {self.state.risk_level}")
            return
        
        # Get option market data
        option_data = self._get_option_data(signal, snapshot)
        if not option_data:
            return
        
        # Calculate position size
        vix = snapshot.get('underlying', {}).get('VIX', {}).get('last', 20)
        spot = snapshot.get('underlying', {}).get('SPX', {}).get('last', 5000)
        
        sizing_result = self.position_sizer.calculate_position_size(
            signal, option_data, spot, vix
        )
        
        if sizing_result['contracts'] == 0:
            logger.debug(f"Zero position size: {sizing_result['limiting_factor']}")
            return
        
        # Check portfolio limits
        portfolio_check = self.position_sizer.check_portfolio_limits(
            self.state.positions, sizing_result
        )
        
        if not all(portfolio_check.values()):
            logger.debug(f"Portfolio limits would be breached: {portfolio_check}")
            return
        
        # Risk manager final check
        risk_check = self.risk_manager.should_allow_new_position(sizing_result)
        if not risk_check['allowed']:
            logger.debug(f"Risk manager blocked position: {risk_check['reason']}")
            return
        
        # Generate and submit order
        await self._submit_option_order(signal, sizing_result, option_data)
    
    async def _submit_option_order(self, signal: Dict, sizing: Dict, option_data: Dict):
        """Submit option order"""
        
        # Create order
        order = {
            'symbol': signal['strike'],  # This would be properly formatted option symbol
            'side': signal['direction'],
            'quantity': sizing['contracts'],
            'order_type': 'LMT',
            'limit_price': sizing['mid_price'],
            'time_in_force': 'DAY',
            'strategy_id': 'mispricing',
            'signal_z': signal['z_score'],
            'timestamp': datetime.now()
        }
        
        logger.info(f"Submitting order: {order}")
        
        # Here you would integrate with your execution engine
        # For now, simulate immediate fill
        fill = {
            'order_id': f"order_{datetime.now().strftime('%H%M%S')}",
            'symbol': order['symbol'],
            'side': order['side'],
            'quantity': order['quantity'],
            'price': order['limit_price'],
            'timestamp': datetime.now()
        }
        
        # Update positions
        position = {
            'symbol': signal['strike'],
            'strike': signal['strike'],
            'expiry': signal['expiry'],
            'type': signal['type'],
            'side': signal['direction'],
            'quantity': sizing['contracts'],
            'entry_price': fill['price'],
            'entry_time': fill['timestamp'],
            'z_score': signal['z_score'],
            'vega_exposure': sizing['risk_metrics']['vega_exposure'],
            'gamma_exposure_1pct': sizing['risk_metrics']['gamma_exposure_1pct'],
            'delta_exposure': sizing['risk_metrics']['delta_exposure'],
            'notional': sizing['notional']
        }
        
        self.state.positions.append(position)
        self.trade_history.append(fill)
        
        logger.info(f"Position opened: {position}")
    
    async def _check_delta_hedge(self, snapshot: Dict):
        """Check and execute delta hedging if needed"""
        
        # Calculate portfolio delta
        portfolio_delta = sum(pos.get('delta_exposure', 0) for pos in self.state.positions)
        
        spot = snapshot.get('underlying', {}).get('SPX', {}).get('last', 5000)
        spy_data = snapshot.get('underlying', {}).get('SPY', {})
        es_data = snapshot.get('futures', {}).get('ES', {})
        
        # Check if hedging is needed
        hedge_triggers = self.delta_hedger.should_hedge(portfolio_delta, spot)
        
        if hedge_triggers['should_hedge']:
            # Select hedge instrument
            instrument = self.delta_hedger.select_hedge_instrument(spy_data, es_data)
            
            # Calculate hedge size
            spy_price = spy_data.get('last', 500)
            hedge_calc = self.delta_hedger.calculate_hedge_size(
                portfolio_delta, spot, spy_price, instrument
            )
            
            # Generate hedge order
            market_data = spy_data if instrument.value == 'SPY' else es_data
            hedge_order = self.delta_hedger.generate_hedge_order(hedge_calc, market_data)
            
            if hedge_order:
                logger.info(f"Submitting hedge order: {hedge_order}")
                # Here you would submit the hedge order
                
        self.last_hedge_check = datetime.now()
    
    def _should_calibrate(self) -> bool:
        """Check if model calibration is needed"""
        if self.state.last_calibration is None:
            return True
        
        time_since_calibration = datetime.now() - self.state.last_calibration
        return time_since_calibration.total_seconds() >= self.calibration_interval * 60
    
    def _should_generate_signals(self) -> bool:
        """Check if signal generation is needed"""
        if self.last_signal_time is None:
            return True
        
        time_since_signals = datetime.now() - self.last_signal_time
        return time_since_signals.total_seconds() >= self.signal_interval
    
    def _should_check_hedge(self) -> bool:
        """Check if delta hedge check is needed"""
        if self.last_hedge_check is None:
            return True
        
        time_since_hedge = datetime.now() - self.last_hedge_check
        return time_since_hedge.total_seconds() >= 30  # Check every 30 seconds
    
    def _is_market_open(self, timestamp: datetime) -> bool:
        """Check if market is open"""
        hour = timestamp.hour + timestamp.minute / 60.0
        
        # Check time of day blocks
        if hour < self.market_open + self.tod_block_min / 60.0:
            return False
        if hour > self.market_close - self.tod_block_min / 60.0:
            return False
            
        return self.market_open <= hour <= self.market_close
    
    def _should_flatten_positions(self, timestamp: datetime) -> bool:
        """Check if positions should be flattened (5 minutes before close)"""
        hour = timestamp.hour + timestamp.minute / 60.0
        return hour >= self.market_close - 5/60.0  # 5 minutes before close
    
    async def _flatten_all_positions(self, snapshot: Dict):
        """Flatten all positions before market close"""
        logger.info("Flattening all positions before market close")
        
        for position in self.state.positions:
            # Generate closing order (opposite side)
            close_side = 'SELL' if position['side'] == 'BUY' else 'BUY'
            
            # Submit closing order
            logger.info(f"Closing position: {position['symbol']}")
            
        # Clear positions
        self.state.positions = []
    
    async def _close_all_positions(self, snapshot: Dict):
        """Close all positions due to risk management"""
        logger.warning("Closing all positions due to risk management")
        await self._flatten_all_positions(snapshot)
    
    async def _emergency_shutdown(self):
        """Emergency shutdown procedure"""
        logger.critical("EMERGENCY SHUTDOWN INITIATED")
        self.state.is_running = False
        
        # Close all positions immediately
        for position in self.state.positions:
            logger.critical(f"Emergency close: {position['symbol']}")
        
        self.state.positions = []
    
    def _calculate_current_pnl(self, snapshot: Dict) -> float:
        """Calculate current daily P&L"""
        # This would calculate mark-to-market P&L for all positions
        # For now, return 0 as placeholder
        return 0.0
    
    def _prepare_iv_surface(self, options_data: pd.DataFrame) -> pd.DataFrame:
        """Prepare IV surface for calibration"""
        # Filter and clean options data for calibration
        return options_data
    
    def _extract_market_iv(self, snapshot: Dict) -> pd.DataFrame:
        """Extract market IV data from snapshot"""
        return snapshot.get('options', pd.DataFrame())
    
    def _generate_model_surface(self, snapshot: Dict) -> pd.DataFrame:
        """Generate model IV surface"""
        # Use current Heston model to generate theoretical IVs
        return pd.DataFrame()
    
    def _get_option_data(self, signal: Dict, snapshot: Dict) -> Optional[Dict]:
        """Get market data for specific option"""
        # Extract option market data from snapshot
        return {
            'bid': 10.0,
            'ask': 10.2,
            'volume': 1000,
            'delta': 0.5,
            'gamma': 0.01,
            'vega': 0.1
        }
    
    def get_strategy_status(self) -> Dict:
        """Get current strategy status"""
        return {
            'is_running': self.state.is_running,
            'risk_level': self.state.risk_level.value,
            'position_count': len(self.state.positions),
            'daily_pnl': self.state.daily_pnl,
            'last_calibration': self.state.last_calibration,
            'model_available': self.state.current_model is not None,
            'total_notional': sum(pos.get('notional', 0) for pos in self.state.positions)
        }
