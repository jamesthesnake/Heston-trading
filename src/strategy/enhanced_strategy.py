"""
Enhanced Mispricing Strategy with Configuration Management
Uses the new unified configuration and data provider systems
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from ..config.config_manager import get_config_manager, SystemConfig
from ..data.unified_feed_manager import UnifiedFeedManager
from .heston_pricing_engine import HestonPricingEngine
from .mispricing_detector import MispricingDetector
from .trade_executor import TradeExecutor
from .delta_hedger import DeltaHedger

logger = logging.getLogger(__name__)

@dataclass
class StrategyState:
    """Enhanced strategy state tracking"""
    is_running: bool = False
    start_time: Optional[datetime] = None
    last_calibration: Optional[datetime] = None
    last_signal_check: Optional[datetime] = None
    last_hedge_check: Optional[datetime] = None
    cycle_count: int = 0
    error_count: int = 0
    
class EnhancedMispricingStrategy:
    """
    Enhanced mispricing strategy with unified configuration and data management
    """
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize enhanced strategy
        
        Args:
            config_file: Path to configuration file (optional)
        """
        # Load configuration
        self.config_manager = get_config_manager()
        if config_file:
            self.config_manager.load_config(config_file)
        
        self.config = self.config_manager.get_config()
        
        # Validate configuration
        config_errors = self.config_manager.validate_config()
        if config_errors:
            logger.error(f"Configuration validation failed: {config_errors}")
            raise ValueError(f"Invalid configuration: {config_errors}")
        
        # Initialize data feed manager
        data_config = self.config_manager.get_data_provider_config()
        self.feed_manager = UnifiedFeedManager({'data_provider': data_config})
        
        # Initialize strategy components
        strategy_config = self.config_manager.get_strategy_config()
        self.pricing_engine = HestonPricingEngine(strategy_config)
        self.mispricing_detector = MispricingDetector(strategy_config)
        self.trade_executor = TradeExecutor(strategy_config)
        self.delta_hedger = DeltaHedger(strategy_config)
        
        # Strategy state
        self.state = StrategyState()
        
        # Configuration-driven parameters
        self.loop_interval = 5.0  # seconds
        self.calibration_frequency = self.config.strategy.calibration_frequency
        self.hedge_frequency = self.config.delta_hedging.hedge_frequency
        
        logger.info("Enhanced mispricing strategy initialized")
    
    async def start(self) -> bool:
        """Start the enhanced strategy"""
        try:
            logger.info("Starting enhanced mispricing strategy...")
            
            # Connect to data source
            if not await self.feed_manager.connect():
                logger.error("Failed to connect to data source")
                return False
            
            # Start data streaming
            if not await self.feed_manager.start_streaming():
                logger.error("Failed to start data streaming")
                return False
            
            # Initialize strategy state
            self.state.is_running = True
            self.state.start_time = datetime.now()
            self.state.cycle_count = 0
            self.state.error_count = 0
            
            logger.info("✅ Enhanced strategy started successfully")
            
            # Main strategy loop
            while self.state.is_running:
                try:
                    await self._execute_strategy_cycle()
                    await asyncio.sleep(self.loop_interval)
                    
                except KeyboardInterrupt:
                    logger.info("Strategy stopped by user")
                    break
                except Exception as e:
                    logger.error(f"Error in strategy cycle: {e}")
                    self.state.error_count += 1
                    
                    # Stop strategy if too many errors
                    if self.state.error_count > 10:
                        logger.error("Too many errors - stopping strategy")
                        break
                    
                    await asyncio.sleep(self.loop_interval)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to start strategy: {e}")
            return False
        finally:
            await self.stop()
    
    async def stop(self):
        """Stop the strategy"""
        try:
            logger.info("Stopping enhanced strategy...")
            
            self.state.is_running = False
            
            # Stop data streaming
            await self.feed_manager.stop_streaming()
            
            # Disconnect from data source
            await self.feed_manager.disconnect()
            
            # Log final statistics
            if self.state.start_time:
                runtime = datetime.now() - self.state.start_time
                logger.info(f"Strategy ran for {runtime}, {self.state.cycle_count} cycles completed")
            
            logger.info("✅ Enhanced strategy stopped")
            
        except Exception as e:
            logger.error(f"Error stopping strategy: {e}")
    
    async def _execute_strategy_cycle(self):
        """Execute one complete strategy cycle"""
        try:
            cycle_start = datetime.now()
            self.state.cycle_count += 1
            
            logger.debug(f"Starting strategy cycle #{self.state.cycle_count}")
            
            # 1. Get current market data
            snapshot = await self.feed_manager.get_market_snapshot()
            if not snapshot:
                logger.warning("No market data available")
                return
            
            underlying_data = snapshot.underlying
            options_data = snapshot.options
            
            if not underlying_data or not options_data:
                logger.warning("Incomplete market data")
                return
            
            # 2. Calibrate Heston model if needed
            if self._should_calibrate():
                logger.info("Calibrating Heston model...")
                try:
                    self.pricing_engine.calibrate_model(options_data, underlying_data)
                    self.state.last_calibration = datetime.now()
                    logger.info("✅ Heston model calibrated successfully")
                except Exception as e:
                    logger.error(f"Model calibration failed: {e}")
            
            # 3. Calculate theoretical prices
            theoretical_prices = self.pricing_engine.get_theoretical_prices(
                options_data, underlying_data
            )
            
            if not theoretical_prices:
                logger.warning("No theoretical prices calculated")
                return
            
            # 4. Detect mispricing opportunities
            mispricing_signals = self.mispricing_detector.detect_mispricings(
                options_data, theoretical_prices, underlying_data
            )
            
            # 5. Execute trades based on signals
            if mispricing_signals:
                logger.info(f"Found {len(mispricing_signals)} mispricing signals")
                
                executed_trades = self.trade_executor.execute_signals(
                    mispricing_signals, options_data, underlying_data
                )
                
                if executed_trades:
                    logger.info(f"✅ Executed {len(executed_trades)} trades")
            
            # 6. Update existing positions
            updated_positions = self.trade_executor.update_positions(options_data)
            
            # 7. Perform delta hedging if needed
            if self._should_hedge():
                logger.debug("Checking delta hedging...")
                try:
                    active_trades = self.trade_executor.get_active_trades()
                    if active_trades:
                        hedge_result = self.delta_hedger.rebalance_portfolio(
                            active_trades, options_data, underlying_data
                        )
                        
                        if hedge_result.get('action') == 'hedge_executed':
                            logger.info(f"✅ Delta hedge executed: {hedge_result}")
                    
                    self.state.last_hedge_check = datetime.now()
                    
                except Exception as e:
                    logger.error(f"Delta hedging failed: {e}")
            
            # 8. Log cycle summary
            cycle_time = (datetime.now() - cycle_start).total_seconds()
            
            if self.state.cycle_count % 20 == 0:  # Every 20 cycles
                summary = self._get_cycle_summary(
                    len(underlying_data), len(options_data), 
                    len(mispricing_signals), cycle_time
                )
                logger.info(f"Cycle #{self.state.cycle_count} summary: {summary}")
            
            self.state.last_signal_check = datetime.now()
            
        except Exception as e:
            logger.error(f"Error in strategy cycle: {e}")
            raise
    
    def _should_calibrate(self) -> bool:
        """Check if model calibration is needed"""
        if not self.state.last_calibration:
            return True
        
        time_since_calibration = datetime.now() - self.state.last_calibration
        return time_since_calibration.total_seconds() >= self.calibration_frequency
    
    def _should_hedge(self) -> bool:
        """Check if delta hedging is needed"""
        if not self.state.last_hedge_check:
            return True
        
        time_since_hedge = datetime.now() - self.state.last_hedge_check
        return time_since_hedge.total_seconds() >= self.hedge_frequency
    
    def _get_cycle_summary(self, underlying_count: int, options_count: int, 
                          signals_count: int, cycle_time: float) -> str:
        """Get cycle summary string"""
        return (f"Underlying: {underlying_count}, Options: {options_count}, "
                f"Signals: {signals_count}, Time: {cycle_time:.2f}s")
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get strategy performance summary"""
        try:
            portfolio_summary = self.trade_executor.get_portfolio_summary()
            
            runtime = None
            if self.state.start_time:
                runtime = (datetime.now() - self.state.start_time).total_seconds()
            
            return {
                'is_running': self.state.is_running,
                'runtime_seconds': runtime,
                'cycle_count': self.state.cycle_count,
                'error_count': self.state.error_count,
                'last_calibration': self.state.last_calibration,
                'last_signal_check': self.state.last_signal_check,
                'last_hedge_check': self.state.last_hedge_check,
                'portfolio_summary': portfolio_summary,
                'config_type': type(self.config).__name__
            }
            
        except Exception as e:
            logger.error(f"Error getting performance summary: {e}")
            return {'error': str(e)}
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        try:
            feed_status = self.feed_manager.get_connection_status()
            data_summary = self.feed_manager.get_data_summary()
            performance = self.get_performance_summary()
            
            return {
                'strategy': performance,
                'data_feed': feed_status,
                'data_summary': data_summary,
                'configuration': {
                    'provider_type': self.config.data_provider.type,
                    'calibration_frequency': self.calibration_frequency,
                    'hedge_frequency': self.hedge_frequency,
                    'loop_interval': self.loop_interval
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting system status: {e}")
            return {'error': str(e)}
    
    def update_configuration(self, section: str, updates: Dict[str, Any]):
        """Update configuration dynamically"""
        try:
            self.config_manager.update_config(section, updates)
            self.config = self.config_manager.get_config()
            
            # Update strategy parameters
            if section == 'strategy':
                self.calibration_frequency = self.config.strategy.calibration_frequency
            elif section == 'delta_hedging':
                self.hedge_frequency = self.config.delta_hedging.hedge_frequency
            
            logger.info(f"Configuration updated: {section}")
            
        except Exception as e:
            logger.error(f"Error updating configuration: {e}")
            raise
    
    # Legacy compatibility methods
    
    @property
    def is_running(self) -> bool:
        """Legacy property for backward compatibility"""
        return self.state.is_running