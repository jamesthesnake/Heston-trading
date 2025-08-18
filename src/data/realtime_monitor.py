"""
Real-time options monitor with 5-second snapshots
"""
import logging
import threading
import time
from datetime import datetime
from typing import Dict, List, Optional, Callable
import json

from data.providers.ib_provider import IBProvider, OptionData, UnderlyingData
from data.options_screener import OptionsScreener, ScreeningCriteria, ScreenedOption
from data.black_scholes import BlackScholesCalculator

logger = logging.getLogger(__name__)

class RealTimeOptionsMonitor:
    """Real-time options monitoring system"""
    
    def __init__(self, config: dict, callback: Optional[Callable] = None):
        self.config = config
        self.callback = callback
        
        # Initialize components
        self.ib_provider = IBProvider(config, self._on_data_update)
        self.screener = OptionsScreener(ScreeningCriteria())
        self.bs_calculator = BlackScholesCalculator()
        
        # Data storage
        self.current_snapshot = {}
        self.last_snapshot_time = None
        
        # Threading
        self.monitor_thread = None
        self.running = False
        self.snapshot_interval = 5.0  # 5 seconds
        
        # Risk-free rate (can be updated from config)
        self.risk_free_rate = config.get('risk_free_rate', 0.05)
        
        # Underlying symbols to monitor
        self.underlying_symbols = ['SPX', 'SPY', 'VIX', 'ES']
        
        logger.info("RealTimeOptionsMonitor initialized")
        
    def start(self) -> bool:
        """Start the real-time monitoring system"""
        try:
            # Connect to IB (skip if using mock data)
            use_mock = self.config.get('data', {}).get('use_mock', False)
            if not use_mock:
                if not self.ib_provider.connect_ib():
                    logger.error("Failed to connect to Interactive Brokers")
                    return False
            else:
                logger.info("Using mock data - skipping IB connection")
                
            # Subscribe to underlying data
            for symbol in self.underlying_symbols:
                self.ib_provider.subscribe_underlying_data(symbol)
                
            # Wait for initial underlying data
            time.sleep(2)
            
            # Get underlying prices and subscribe to options
            underlying_prices = self._get_underlying_prices()
            if underlying_prices:
                self._subscribe_to_options(underlying_prices)
                
            # Start monitoring thread
            self.running = True
            self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.monitor_thread.start()
            
            logger.info("Real-time options monitor started")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start monitor: {e}")
            return False
            
    def stop(self):
        """Stop the monitoring system"""
        self.running = False
        
        if self.monitor_thread:
            self.monitor_thread.join(timeout=10)
            
        if self.ib_provider:
            self.ib_provider.disconnect_ib()
            
        logger.info("Real-time options monitor stopped")
        
    def _monitor_loop(self):
        """Main monitoring loop - 5-second snapshots"""
        while self.running:
            try:
                start_time = time.time()
                
                # Generate snapshot
                snapshot = self._generate_snapshot()
                
                if snapshot:
                    self.current_snapshot = snapshot
                    self.last_snapshot_time = datetime.now()
                    
                    # Call callback if provided
                    if self.callback:
                        self.callback(snapshot)
                        
                    logger.debug(f"Generated snapshot with {len(snapshot.get('screened_options', []))} options")
                
                # Sleep for remainder of interval
                elapsed = time.time() - start_time
                sleep_time = max(0, self.snapshot_interval - elapsed)
                time.sleep(sleep_time)
                
            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")
                time.sleep(1)
                
    def _generate_snapshot(self) -> Dict:
        """Generate current market snapshot"""
        try:
            # Get current data from IB
            options_data = self.ib_provider.get_option_snapshot()
            underlying_data = self.ib_provider.get_underlying_snapshot()
            
            # Extract underlying prices
            underlying_prices = {}
            for symbol, data in underlying_data.items():
                if data.last > 0:
                    underlying_prices[symbol] = data.last
                elif data.bid > 0 and data.ask > 0:
                    underlying_prices[symbol] = (data.bid + data.ask) / 2
                    
            # Enhance options data with calculated Greeks
            enhanced_options = self._enhance_options_data(options_data, underlying_prices)
            
            # Screen options
            screened_options = self.screener.screen_options(enhanced_options, underlying_prices)
            
            # Create snapshot
            snapshot = {
                'timestamp': datetime.now().isoformat(),
                'underlying_data': self._format_underlying_data(underlying_data),
                'screened_options': self._format_screened_options(screened_options),
                'summary_stats': self.screener.get_summary_stats(screened_options),
                'market_overview': self._generate_market_overview(underlying_data, screened_options)
            }
            
            return snapshot
            
        except Exception as e:
            logger.error(f"Error generating snapshot: {e}")
            return {}
            
    def _enhance_options_data(self, options_data: List[OptionData], 
                             underlying_prices: Dict[str, float]) -> List[OptionData]:
        """Enhance options data with calculated Greeks if missing"""
        enhanced = []
        
        for option in options_data:
            try:
                # Get underlying price
                underlying_price = underlying_prices.get(option.symbol)
                if not underlying_price:
                    continue
                    
                # Calculate time to expiry
                T = self.bs_calculator.time_to_expiry(option.expiry)
                if T <= 0:
                    continue
                    
                # If we have market price but missing Greeks, calculate them
                if option.midpoint > 0 and (option.delta == 0 or option.implied_vol == 0):
                    
                    # Calculate implied volatility if missing
                    if option.implied_vol == 0:
                        option.implied_vol = self.bs_calculator.implied_volatility(
                            option.midpoint, underlying_price, option.strike, T,
                            self.risk_free_rate, option.option_type
                        )
                    
                    # Calculate Greeks if missing
                    if option.implied_vol > 0:
                        greeks = self.bs_calculator.calculate_all_greeks(
                            underlying_price, option.strike, T, self.risk_free_rate,
                            option.implied_vol, option.option_type
                        )
                        
                        if option.delta == 0:
                            option.delta = greeks['delta']
                        if option.gamma == 0:
                            option.gamma = greeks['gamma']
                        if option.theta == 0:
                            option.theta = greeks['theta']
                        if option.vega == 0:
                            option.vega = greeks['vega']
                            
                enhanced.append(option)
                
            except Exception as e:
                logger.warning(f"Error enhancing option data: {e}")
                continue
                
        return enhanced
        
    def _get_underlying_prices(self) -> Dict[str, float]:
        """Get current underlying prices"""
        underlying_data = self.ib_provider.get_underlying_snapshot()
        prices = {}
        
        for symbol, data in underlying_data.items():
            if data.last > 0:
                prices[symbol] = data.last
            elif data.bid > 0 and data.ask > 0:
                prices[symbol] = (data.bid + data.ask) / 2
                
        return prices
        
    def _subscribe_to_options(self, underlying_prices: Dict[str, float]):
        """Subscribe to relevant options based on screening criteria"""
        # Generate option requests
        requests = self.screener.generate_option_chain_requests(underlying_prices)
        
        # Limit to reasonable number of contracts
        max_contracts = self.config.get('max_option_contracts', 500)
        if len(requests) > max_contracts:
            logger.warning(f"Limiting option subscriptions to {max_contracts} contracts")
            requests = requests[:max_contracts]
            
        # Subscribe to options
        for symbol, strike, expiry, option_type in requests:
            self.ib_provider.subscribe_option_data(symbol, strike, expiry, option_type)
            
        logger.info(f"Subscribed to {len(requests)} option contracts")
        
    def _format_underlying_data(self, underlying_data: Dict[str, UnderlyingData]) -> Dict:
        """Format underlying data for output"""
        formatted = {}
        
        for symbol, data in underlying_data.items():
            formatted[symbol] = {
                'bid': data.bid,
                'ask': data.ask,
                'last': data.last,
                'midpoint': (data.bid + data.ask) / 2 if data.bid > 0 and data.ask > 0 else data.last,
                'timestamp': data.timestamp.isoformat() if data.timestamp else None
            }
            
        return formatted
        
    def _format_screened_options(self, screened_options: List[ScreenedOption]) -> List[Dict]:
        """Format screened options for output"""
        formatted = []
        
        for screened in screened_options:
            option = screened.option_data
            
            formatted_option = {
                # Contract details
                'symbol': option.symbol,
                'strike': option.strike,
                'expiry': option.expiry,
                'option_type': option.option_type,
                'dte': screened.dte,
                
                # NBBO data
                'bid': option.bid,
                'ask': option.ask,
                'bid_size': option.bid_size,
                'ask_size': option.ask_size,
                'midpoint': option.midpoint,
                'nbbo_timestamp': option.nbbo_timestamp.isoformat() if option.nbbo_timestamp else None,
                
                # Trade data
                'last_price': option.last_price,
                'last_size': option.last_size,
                'volume': option.volume,
                'open_interest': option.open_interest,
                'last_trade_timestamp': option.last_trade_timestamp.isoformat() if option.last_trade_timestamp else None,
                
                # Greeks and IV
                'implied_vol': option.implied_vol,
                'delta': option.delta,
                'gamma': option.gamma,
                'theta': option.theta,
                'vega': option.vega,
                
                # Screening metrics
                'moneyness': screened.moneyness,
                'spread_width_pct': screened.spread_width_pct,
                'distance_from_atm_pct': screened.distance_from_atm_pct,
                'notional_value': screened.notional_value,
                'daily_theta_decay': screened.daily_theta_decay
            }
            
            formatted.append(formatted_option)
            
        return formatted
        
    def _generate_market_overview(self, underlying_data: Dict[str, UnderlyingData], 
                                 screened_options: List[ScreenedOption]) -> Dict:
        """Generate market overview"""
        overview = {
            'total_screened_options': len(screened_options),
            'underlying_levels': {},
            'volatility_metrics': {},
            'top_volume_options': []
        }
        
        # Underlying levels
        for symbol, data in underlying_data.items():
            if data.last > 0:
                overview['underlying_levels'][symbol] = data.last
                
        # Volatility metrics
        if screened_options:
            ivs = [opt.option_data.implied_vol for opt in screened_options if opt.option_data.implied_vol > 0]
            if ivs:
                overview['volatility_metrics'] = {
                    'avg_iv': sum(ivs) / len(ivs),
                    'min_iv': min(ivs),
                    'max_iv': max(ivs)
                }
                
        # Top volume options
        top_volume = sorted(screened_options, key=lambda x: x.option_data.volume, reverse=True)[:10]
        overview['top_volume_options'] = [
            {
                'symbol': opt.option_data.symbol,
                'strike': opt.option_data.strike,
                'expiry': opt.option_data.expiry,
                'type': opt.option_data.option_type,
                'volume': opt.option_data.volume,
                'midpoint': opt.option_data.midpoint
            }
            for opt in top_volume
        ]
        
        return overview
        
    def get_current_snapshot(self) -> Optional[Dict]:
        """Get the most recent snapshot"""
        return self.current_snapshot.copy() if self.current_snapshot else None
        
    def update_screening_criteria(self, **kwargs):
        """Update screening criteria"""
        self.screener.update_criteria(**kwargs)
        
        # Re-subscribe to options if needed
        underlying_prices = self._get_underlying_prices()
        if underlying_prices:
            self._subscribe_to_options(underlying_prices)
            
    def export_snapshot_to_json(self, filename: Optional[str] = None) -> str:
        """Export current snapshot to JSON file"""
        if not self.current_snapshot:
            raise ValueError("No snapshot available")
            
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"options_snapshot_{timestamp}.json"
            
        with open(filename, 'w') as f:
            json.dump(self.current_snapshot, f, indent=2, default=str)
            
        return filename
        
    def _on_data_update(self, data):
        """Callback for data updates from IB provider"""
        # This could be used for real-time alerts or immediate processing
        pass
