"""
Strategy Orchestrator - Main Coordination Module
Coordinates all strategy components without handling implementation details
"""
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from .strategy_engine import StrategyEngine
from .portfolio_manager import PortfolioManager
from .lifecycle_manager import LifecycleManager
from ..config.config_manager import get_config_manager
from ..data.unified_feed_manager import UnifiedFeedManager

logger = logging.getLogger(__name__)

class StrategyOrchestrator:
    """
    Main strategy orchestrator that coordinates all components
    Keeps the big picture view without implementation details
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the strategy orchestrator
        
        Args:
            config: Configuration dictionary or None for default config
        """
        # Load configuration
        if config:
            self.config = config
        else:
            config_manager = get_config_manager()
            self.config = config_manager.get_strategy_config()
        
        # Initialize core managers
        self.strategy_engine = StrategyEngine(self.config)
        self.portfolio_manager = PortfolioManager(self.config)
        self.lifecycle_manager = LifecycleManager(self.config)
        
        # Data feed (can be injected or created)
        self.feed_manager: Optional[UnifiedFeedManager] = None
        self.external_feed = False
        
        # Orchestration state
        self.is_running = False
        self.cycle_count = 0
        self.last_cycle_time = None
        self.error_count = 0
        
        # Performance tracking
        self.cycle_metrics = []
        
        logger.info("Strategy orchestrator initialized")
    
    def set_data_feed(self, feed_manager: UnifiedFeedManager):
        """Set external data feed manager"""
        self.feed_manager = feed_manager
        self.external_feed = True
        logger.info("External data feed attached")
    
    async def start(self) -> bool:
        """
        Start the complete trading strategy
        
        Returns:
            True if started successfully, False otherwise
        """
        try:
            logger.info("🚀 Starting strategy orchestrator...")
            
            # Initialize data feed if not provided externally
            if not self.feed_manager:
                config_manager = get_config_manager()
                data_config = config_manager.get_data_provider_config()
                self.feed_manager = UnifiedFeedManager({'data_provider': data_config})
                logger.info("Created internal data feed manager")
            
            # Start lifecycle manager
            if not await self.lifecycle_manager.startup():
                logger.error("Failed to start lifecycle manager")
                return False
            
            # Connect to data source
            if not await self.feed_manager.connect():
                logger.error("Failed to connect to data source")
                await self.lifecycle_manager.shutdown()
                return False
            
            # Start data streaming
            if not await self.feed_manager.start_streaming():
                logger.error("Failed to start data streaming")
                await self.feed_manager.disconnect()
                await self.lifecycle_manager.shutdown()
                return False
            
            # Initialize strategy engine
            if not await self.strategy_engine.initialize():
                logger.error("Failed to initialize strategy engine")
                await self._cleanup()
                return False
            
            # Initialize portfolio manager
            if not await self.portfolio_manager.initialize():
                logger.error("Failed to initialize portfolio manager")
                await self._cleanup()
                return False
            
            # Set running state
            self.is_running = True
            self.cycle_count = 0
            self.error_count = 0
            
            logger.info("✅ Strategy orchestrator started successfully")
            
            # Start main orchestration loop
            await self._run_orchestration_loop()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to start strategy orchestrator: {e}")
            await self._cleanup()
            return False
    
    async def stop(self):
        """Stop the strategy orchestrator"""
        try:
            logger.info("🛑 Stopping strategy orchestrator...")
            
            self.is_running = False
            
            await self._cleanup()
            
            logger.info("✅ Strategy orchestrator stopped")
            
        except Exception as e:
            logger.error(f"Error stopping orchestrator: {e}")
    
    async def _run_orchestration_loop(self):
        """Main orchestration loop that coordinates all activities"""
        
        loop_interval = self.config.get('strategy', {}).get('loop_interval', 5.0)
        max_errors = self.config.get('strategy', {}).get('max_consecutive_errors', 10)
        
        logger.info(f"Starting orchestration loop (interval: {loop_interval}s)")
        
        while self.is_running:
            try:
                cycle_start = datetime.now()
                self.cycle_count += 1
                
                # Execute one complete strategy cycle
                cycle_result = await self._execute_cycle()
                
                # Record cycle metrics
                cycle_time = (datetime.now() - cycle_start).total_seconds()
                self._record_cycle_metrics(cycle_result, cycle_time)
                
                # Reset error count on successful cycle
                if cycle_result.get('success', False):
                    self.error_count = 0
                else:
                    self.error_count += 1
                
                # Stop if too many consecutive errors
                if self.error_count >= max_errors:
                    logger.error(f"Too many consecutive errors ({self.error_count}), stopping strategy")
                    break
                
                # Log periodic summary
                if self.cycle_count % 20 == 0:
                    await self._log_periodic_summary()
                
                # Wait for next cycle
                await asyncio.sleep(loop_interval)
                
            except KeyboardInterrupt:
                logger.info("Strategy stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in orchestration loop: {e}")
                self.error_count += 1
                
                if self.error_count >= max_errors:
                    logger.error("Too many errors, stopping strategy")
                    break
                
                # Wait longer on error
                await asyncio.sleep(loop_interval * 2)
    
    async def _execute_cycle(self) -> Dict[str, Any]:
        """
        Execute one complete strategy cycle
        
        Returns:
            Dictionary with cycle results and metrics
        """
        try:
            cycle_start = datetime.now()
            
            # 1. Get current market data
            snapshot = await self.feed_manager.get_market_snapshot()
            if not snapshot:
                return {'success': False, 'error': 'No market data'}
            
            # 2. Execute strategy logic
            strategy_result = await self.strategy_engine.execute_cycle(
                snapshot.underlying, snapshot.options
            )
            
            if not strategy_result.get('success', False):
                return {
                    'success': False, 
                    'error': f"Strategy execution failed: {strategy_result.get('error')}"
                }
            
            # 3. Update portfolio positions
            portfolio_result = await self.portfolio_manager.update_positions(
                strategy_result.get('executed_trades', []),
                strategy_result.get('market_data', {}),
                strategy_result.get('theoretical_prices', {})
            )
            
            # 4. Perform risk management and hedging
            risk_result = await self.portfolio_manager.manage_risk(
                snapshot.underlying, snapshot.options
            )
            
            # 5. Check system health
            health_status = await self.lifecycle_manager.check_health()
            
            cycle_time = (datetime.now() - cycle_start).total_seconds()
            
            return {
                'success': True,
                'cycle_count': self.cycle_count,
                'cycle_time': cycle_time,
                'strategy_result': strategy_result,
                'portfolio_result': portfolio_result,
                'risk_result': risk_result,
                'health_status': health_status,
                'market_data_quality': {
                    'underlying_count': len(snapshot.underlying),
                    'options_count': len(snapshot.options)
                }
            }
            
        except Exception as e:
            logger.error(f"Error in strategy cycle: {e}")
            return {'success': False, 'error': str(e)}
    
    def _record_cycle_metrics(self, cycle_result: Dict[str, Any], cycle_time: float):
        """Record metrics from cycle execution"""
        try:
            metrics = {
                'timestamp': datetime.now(),
                'cycle_count': self.cycle_count,
                'cycle_time': cycle_time,
                'success': cycle_result.get('success', False),
                'error_count': self.error_count
            }
            
            # Add detailed metrics if cycle was successful
            if cycle_result.get('success'):
                strategy_result = cycle_result.get('strategy_result', {})
                metrics.update({
                    'signals_found': strategy_result.get('signals_count', 0),
                    'trades_executed': strategy_result.get('trades_executed', 0),
                    'theoretical_prices_count': strategy_result.get('theoretical_prices_count', 0)
                })
            
            self.cycle_metrics.append(metrics)
            
            # Keep only recent metrics
            if len(self.cycle_metrics) > 1000:
                self.cycle_metrics = self.cycle_metrics[-500:]
                
        except Exception as e:
            logger.error(f"Error recording cycle metrics: {e}")
    
    async def _log_periodic_summary(self):
        """Log periodic summary of strategy performance"""
        try:
            # Get portfolio summary
            portfolio_summary = await self.portfolio_manager.get_performance_summary()
            
            # Get strategy summary
            strategy_summary = await self.strategy_engine.get_performance_summary()
            
            logger.info(f"📊 Cycle #{self.cycle_count} Summary:")
            logger.info(f"   Portfolio: {portfolio_summary.get('active_positions', 0)} positions, "
                       f"P&L: ${portfolio_summary.get('total_pnl', 0):,.2f}")
            logger.info(f"   Strategy: {strategy_summary.get('signals_today', 0)} signals, "
                       f"{strategy_summary.get('trades_today', 0)} trades executed")
            logger.info(f"   Health: {self.error_count} errors in last 20 cycles")
            
        except Exception as e:
            logger.error(f"Error logging periodic summary: {e}")
    
    async def _cleanup(self):
        """Cleanup all resources"""
        try:
            # Stop components in reverse order
            if hasattr(self, 'portfolio_manager'):
                await self.portfolio_manager.shutdown()
            
            if hasattr(self, 'strategy_engine'):
                await self.strategy_engine.shutdown()
            
            # Stop data streaming
            if self.feed_manager:
                await self.feed_manager.stop_streaming()
                
                # Only disconnect if we created the feed manager
                if not self.external_feed:
                    await self.feed_manager.disconnect()
            
            # Stop lifecycle manager last
            if hasattr(self, 'lifecycle_manager'):
                await self.lifecycle_manager.shutdown()
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    # Public API methods
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        try:
            return {
                'orchestrator': {
                    'is_running': self.is_running,
                    'cycle_count': self.cycle_count,
                    'error_count': self.error_count,
                    'last_cycle_time': self.last_cycle_time
                },
                'strategy_engine': self.strategy_engine.get_status(),
                'portfolio_manager': self.portfolio_manager.get_status(),
                'lifecycle_manager': self.lifecycle_manager.get_status(),
                'data_feed': self.feed_manager.get_connection_status() if self.feed_manager else None
            }
        except Exception as e:
            return {'error': str(e)}
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics across all components"""
        try:
            recent_metrics = self.cycle_metrics[-100:] if self.cycle_metrics else []
            
            success_rate = sum(1 for m in recent_metrics if m.get('success', False)) / len(recent_metrics) if recent_metrics else 0
            avg_cycle_time = sum(m.get('cycle_time', 0) for m in recent_metrics) / len(recent_metrics) if recent_metrics else 0
            
            return {
                'cycle_metrics': {
                    'total_cycles': self.cycle_count,
                    'success_rate': success_rate,
                    'avg_cycle_time': avg_cycle_time,
                    'current_error_count': self.error_count
                },
                'strategy_performance': self.strategy_engine.get_performance_summary(),
                'portfolio_performance': self.portfolio_manager.get_performance_summary()
            }
        except Exception as e:
            return {'error': str(e)}

# Convenience function for backward compatibility
async def create_and_start_strategy(config: Optional[Dict[str, Any]] = None) -> StrategyOrchestrator:
    """Create and start a strategy orchestrator"""
    orchestrator = StrategyOrchestrator(config)
    await orchestrator.start()
    return orchestrator