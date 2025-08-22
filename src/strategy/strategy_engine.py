"""
Strategy Engine - Core Trading Logic Module
Handles Heston model calibration, mispricing detection, and signal generation
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

from .heston_pricing_engine import HestonPricingEngine
from .mispricing_detector import MispricingDetector
from .trade_executor import TradeExecutor

logger = logging.getLogger(__name__)

class StrategyEngine:
    """
    Core strategy engine that implements the Heston mispricing logic
    Focused on trading strategy implementation without orchestration concerns
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the strategy engine
        
        Args:
            config: Strategy configuration
        """
        self.config = config
        self.strategy_config = config.get('strategy', {})
        self.mispricing_config = config.get('mispricing_detection', {})
        
        # Core strategy components
        self.pricing_engine = HestonPricingEngine(config)
        self.mispricing_detector = MispricingDetector(config)
        self.trade_executor = TradeExecutor(config)
        
        # Strategy parameters
        self.calibration_frequency = self.strategy_config.get('calibration_frequency', 300)  # 5 minutes
        self.min_signal_confidence = self.mispricing_config.get('min_signal_confidence', 70.0)
        self.max_signals_per_cycle = self.mispricing_config.get('max_signals_per_cycle', 20)
        
        # Strategy state
        self.is_initialized = False
        self.last_calibration = None
        self.calibration_count = 0
        self.signal_history = []
        self.execution_history = []
        
        # Performance tracking
        self.cycle_performance = []
        self.daily_stats = {
            'signals_generated': 0,
            'trades_executed': 0,
            'calibrations_performed': 0,
            'start_time': datetime.now()
        }
        
        logger.info("Strategy engine initialized")
    
    async def initialize(self) -> bool:
        """
        Initialize the strategy engine
        
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            logger.info("Initializing strategy engine...")
            
            # Initialize all components
            initialization_tasks = [
                self._initialize_pricing_engine(),
                self._initialize_mispricing_detector(),
                self._initialize_trade_executor()
            ]
            
            results = await asyncio.gather(*initialization_tasks, return_exceptions=True)
            
            # Check if all initializations succeeded
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Component {i} initialization failed: {result}")
                    return False
                elif not result:
                    logger.error(f"Component {i} initialization returned False")
                    return False
            
            self.is_initialized = True
            self.daily_stats['start_time'] = datetime.now()
            
            logger.info("✅ Strategy engine initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Strategy engine initialization failed: {e}")
            return False
    
    async def execute_cycle(self, underlying_data: Dict[str, Any], 
                           options_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Execute one complete strategy cycle
        
        Args:
            underlying_data: Current underlying market data
            options_data: Current options market data
            
        Returns:
            Dictionary with cycle results
        """
        if not self.is_initialized:
            return {'success': False, 'error': 'Strategy engine not initialized'}
        
        try:
            cycle_start = datetime.now()
            
            # 1. Calibrate Heston model if needed
            calibration_performed = await self._handle_calibration(options_data, underlying_data)
            
            # 2. Calculate theoretical prices
            theoretical_prices = await self._calculate_theoretical_prices(options_data, underlying_data)
            
            if not theoretical_prices:
                return {
                    'success': False, 
                    'error': 'No theoretical prices calculated'
                }
            
            # 3. Detect mispricing opportunities
            mispricing_signals = await self._detect_mispricings(
                options_data, theoretical_prices, underlying_data
            )
            
            # 4. Execute trades based on signals
            executed_trades = await self._execute_trades(
                mispricing_signals, options_data, underlying_data
            )
            
            # 5. Update performance tracking
            cycle_time = (datetime.now() - cycle_start).total_seconds()
            self._update_performance_tracking(
                len(mispricing_signals), len(executed_trades), 
                calibration_performed, cycle_time
            )
            
            return {
                'success': True,
                'signals_count': len(mispricing_signals),
                'trades_executed': len(executed_trades),
                'theoretical_prices_count': len(theoretical_prices),
                'calibration_performed': calibration_performed,
                'cycle_time': cycle_time,
                'executed_trades': executed_trades,
                'market_data': {
                    'underlying': underlying_data,
                    'options': options_data
                },
                'theoretical_prices': theoretical_prices,
                'mispricing_signals': mispricing_signals
            }
            
        except Exception as e:
            logger.error(f"Error in strategy cycle execution: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _handle_calibration(self, options_data: List[Dict[str, Any]], 
                                 underlying_data: Dict[str, Any]) -> bool:
        """Handle Heston model calibration if needed"""
        try:
            if self._should_calibrate():
                logger.info("🔬 Calibrating Heston model...")
                
                success = await self._perform_calibration(options_data, underlying_data)
                
                if success:
                    self.last_calibration = datetime.now()
                    self.calibration_count += 1
                    self.daily_stats['calibrations_performed'] += 1
                    logger.info("✅ Heston model calibrated successfully")
                    return True
                else:
                    logger.warning("⚠️ Heston calibration failed, using previous parameters")
                    return False
            
            return False
            
        except Exception as e:
            logger.error(f"Error in calibration handling: {e}")
            return False
    
    async def _perform_calibration(self, options_data: List[Dict[str, Any]], 
                                  underlying_data: Dict[str, Any]) -> bool:
        """Perform the actual Heston model calibration"""
        try:
            # Use the pricing engine's calibration method
            calibration_result = self.pricing_engine.calibrate_to_current_market(
                options_data, underlying_data
            )
            
            return calibration_result.get('success', False)
            
        except Exception as e:
            logger.error(f"Calibration execution failed: {e}")
            return False
    
    async def _calculate_theoretical_prices(self, options_data: List[Dict[str, Any]], 
                                           underlying_data: Dict[str, Any]) -> Dict[str, float]:
        """Calculate theoretical option prices using calibrated Heston model"""
        try:
            theoretical_prices = self.pricing_engine.get_theoretical_prices(
                options_data, underlying_data
            )
            
            if theoretical_prices:
                logger.debug(f"Calculated {len(theoretical_prices)} theoretical prices")
            else:
                logger.warning("No theoretical prices calculated")
            
            return theoretical_prices
            
        except Exception as e:
            logger.error(f"Error calculating theoretical prices: {e}")
            return {}
    
    async def _detect_mispricings(self, options_data: List[Dict[str, Any]], 
                                 theoretical_prices: Dict[str, float], 
                                 underlying_data: Dict[str, Any]) -> List[Any]:
        """Detect mispricing opportunities"""
        try:
            mispricing_signals = self.mispricing_detector.detect_mispricings(
                options_data, theoretical_prices, underlying_data
            )
            
            # Filter signals by confidence and limit count
            filtered_signals = self._filter_signals(mispricing_signals)
            
            if filtered_signals:
                logger.info(f"🎯 Found {len(filtered_signals)} high-quality mispricing signals")
                
                # Get signal summary for logging
                signal_summary = self.mispricing_detector.get_signal_summary(filtered_signals)
                logger.info(f"Signal summary: {signal_summary.get('strong_signals', 0)} strong, "
                          f"avg mispricing: {signal_summary.get('avg_mispricing', 0):.1f}%")
            
            # Store in history
            self.signal_history.append({
                'timestamp': datetime.now(),
                'total_signals': len(mispricing_signals),
                'filtered_signals': len(filtered_signals)
            })
            
            self.daily_stats['signals_generated'] += len(filtered_signals)
            
            return filtered_signals
            
        except Exception as e:
            logger.error(f"Error detecting mispricings: {e}")
            return []
    
    async def _execute_trades(self, mispricing_signals: List[Any], 
                             options_data: List[Dict[str, Any]], 
                             underlying_data: Dict[str, Any]) -> List[Any]:
        """Execute trades based on mispricing signals"""
        try:
            if not mispricing_signals:
                return []
            
            executed_trades = self.trade_executor.execute_signals(
                mispricing_signals, options_data, underlying_data
            )
            
            if executed_trades:
                logger.info(f"✅ Executed {len(executed_trades)} trades")
                
                # Log trade details
                for trade in executed_trades:
                    direction = "🟢 BOUGHT" if trade.direction.value == "buy" else "🔴 SOLD"
                    logger.info(f"   {direction} {trade.quantity} {trade.symbol} "
                              f"{trade.strike:.0f}{trade.option_type} @ ${trade.entry_price:.2f}")
            
            # Store in execution history
            self.execution_history.append({
                'timestamp': datetime.now(),
                'signals_processed': len(mispricing_signals),
                'trades_executed': len(executed_trades)
            })
            
            self.daily_stats['trades_executed'] += len(executed_trades)
            
            return executed_trades
            
        except Exception as e:
            logger.error(f"Error executing trades: {e}")
            return []
    
    def _should_calibrate(self) -> bool:
        """Check if Heston model calibration is needed"""
        if not self.last_calibration:
            return True
        
        time_since_calibration = datetime.now() - self.last_calibration
        return time_since_calibration.total_seconds() >= self.calibration_frequency
    
    def _filter_signals(self, signals: List[Any]) -> List[Any]:
        """Filter signals by confidence and other criteria"""
        try:
            filtered = []
            
            for signal in signals:
                # Check confidence threshold
                if signal.confidence < self.min_signal_confidence:
                    continue
                
                # Check if we haven't hit the max signals limit
                if len(filtered) >= self.max_signals_per_cycle:
                    break
                
                filtered.append(signal)
            
            # Sort by confidence (highest first)
            filtered.sort(key=lambda s: s.confidence, reverse=True)
            
            return filtered
            
        except Exception as e:
            logger.error(f"Error filtering signals: {e}")
            return signals  # Return unfiltered on error
    
    def _update_performance_tracking(self, signals_count: int, trades_count: int, 
                                   calibration_performed: bool, cycle_time: float):
        """Update performance tracking metrics"""
        try:
            performance_entry = {
                'timestamp': datetime.now(),
                'signals_count': signals_count,
                'trades_count': trades_count,
                'calibration_performed': calibration_performed,
                'cycle_time': cycle_time
            }
            
            self.cycle_performance.append(performance_entry)
            
            # Keep only recent performance data
            if len(self.cycle_performance) > 1000:
                self.cycle_performance = self.cycle_performance[-500:]
                
        except Exception as e:
            logger.error(f"Error updating performance tracking: {e}")
    
    # Component initialization methods
    
    async def _initialize_pricing_engine(self) -> bool:
        """Initialize the Heston pricing engine"""
        try:
            # Pricing engine initialization is typically synchronous
            logger.debug("Pricing engine ready")
            return True
        except Exception as e:
            logger.error(f"Pricing engine initialization failed: {e}")
            return False
    
    async def _initialize_mispricing_detector(self) -> bool:
        """Initialize the mispricing detector"""
        try:
            # Mispricing detector initialization
            logger.debug("Mispricing detector ready")
            return True
        except Exception as e:
            logger.error(f"Mispricing detector initialization failed: {e}")
            return False
    
    async def _initialize_trade_executor(self) -> bool:
        """Initialize the trade executor"""
        try:
            # Trade executor initialization
            logger.debug("Trade executor ready")
            return True
        except Exception as e:
            logger.error(f"Trade executor initialization failed: {e}")
            return False
    
    # Public API methods
    
    def get_status(self) -> Dict[str, Any]:
        """Get current strategy engine status"""
        try:
            return {
                'is_initialized': self.is_initialized,
                'last_calibration': self.last_calibration,
                'calibration_count': self.calibration_count,
                'daily_signals': self.daily_stats['signals_generated'],
                'daily_trades': self.daily_stats['trades_executed'],
                'daily_calibrations': self.daily_stats['calibrations_performed'],
                'runtime_hours': (datetime.now() - self.daily_stats['start_time']).total_seconds() / 3600
            }
        except Exception as e:
            return {'error': str(e)}
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get strategy engine performance summary"""
        try:
            recent_performance = self.cycle_performance[-100:] if self.cycle_performance else []
            
            if recent_performance:
                avg_cycle_time = sum(p['cycle_time'] for p in recent_performance) / len(recent_performance)
                total_signals = sum(p['signals_count'] for p in recent_performance)
                total_trades = sum(p['trades_count'] for p in recent_performance)
                signal_to_trade_ratio = total_trades / total_signals if total_signals > 0 else 0
            else:
                avg_cycle_time = 0
                total_signals = 0
                total_trades = 0
                signal_to_trade_ratio = 0
            
            return {
                'daily_stats': self.daily_stats.copy(),
                'recent_performance': {
                    'avg_cycle_time': avg_cycle_time,
                    'total_signals': total_signals,
                    'total_trades': total_trades,
                    'signal_to_trade_ratio': signal_to_trade_ratio
                },
                'calibration_status': {
                    'last_calibration': self.last_calibration,
                    'calibration_count': self.calibration_count,
                    'next_calibration_due': self._should_calibrate()
                }
            }
        except Exception as e:
            return {'error': str(e)}
    
    async def shutdown(self):
        """Shutdown the strategy engine"""
        try:
            logger.info("Shutting down strategy engine...")
            
            # Strategy engine cleanup would go here
            # For now, just mark as not initialized
            self.is_initialized = False
            
            logger.info("✅ Strategy engine shutdown complete")
            
        except Exception as e:
            logger.error(f"Error shutting down strategy engine: {e}")

# For backward compatibility and testing
import asyncio