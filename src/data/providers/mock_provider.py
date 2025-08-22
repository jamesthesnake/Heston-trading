"""
Enhanced Mock Data Provider
Provides realistic market data simulation for testing and demo purposes
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
import random
import numpy as np
from .base_provider import DataProvider

logger = logging.getLogger(__name__)

class MockDataProvider(DataProvider):
    """Enhanced mock data provider with realistic market simulation"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.provider_type = "mock"
        self.simulation_task: Optional[asyncio.Task] = None
        self.update_interval = config.get('update_interval', 1.0)  # seconds
        self.volatility_factor = config.get('volatility_factor', 1.0)
        
        # Market state
        self.underlying_prices = {
            'SPX': 5000.0,
            'SPY': 500.0,
            'VIX': 15.0
        }
        
        # Options universe
        self.options_universe = []
        self._initialize_options_universe()
        
        logger.info("Mock data provider initialized")
    
    def _get_required_config_fields(self) -> List[str]:
        """No required fields for mock provider"""
        return []
    
    async def connect(self) -> bool:
        """Connect to mock data source (always successful)"""
        try:
            self._update_connection_status(self.ConnectionStatus.CONNECTING)
            await asyncio.sleep(0.1)  # Simulate connection time
            self._update_connection_status(self.ConnectionStatus.CONNECTED)
            logger.info("Mock data provider connected")
            return True
        except Exception as e:
            self._update_connection_status(self.ConnectionStatus.ERROR)
            self._handle_error(e)
            return False
    
    async def disconnect(self) -> bool:
        """Disconnect from mock data source"""
        try:
            if self.simulation_task:
                self.simulation_task.cancel()
                self.simulation_task = None
            
            self._update_connection_status(self.ConnectionStatus.DISCONNECTED)
            logger.info("Mock data provider disconnected")
            return True
        except Exception as e:
            self._handle_error(e)
            return False
    
    async def is_connected(self) -> bool:
        """Check if connected"""
        return self.connection_status == self.ConnectionStatus.CONNECTED
    
    async def get_underlying_data(self, symbols: List[str]) -> Dict[str, Any]:
        """Get current underlying asset data"""
        self._update_underlying_prices()
        
        data = {}
        for symbol in symbols:
            if symbol in self.underlying_prices:
                price = self.underlying_prices[symbol]
                change = random.uniform(-0.02, 0.02) * self.volatility_factor
                
                data[symbol] = {
                    'symbol': symbol,
                    'last': price,
                    'bid': price - 0.01,
                    'ask': price + 0.01,
                    'change': price * change,
                    'change_pct': change * 100,
                    'volume': random.randint(1000000, 5000000),
                    'open': price * (1 + random.uniform(-0.01, 0.01)),
                    'high': price * (1 + random.uniform(0, 0.02)),
                    'low': price * (1 + random.uniform(-0.02, 0)),
                    'timestamp': datetime.now()
                }
        
        return data
    
    async def get_options_chain(self, underlying_symbol: str, 
                               strikes: Optional[List[float]] = None,
                               expirations: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Get options chain for underlying symbol"""
        if underlying_symbol not in self.underlying_prices:
            return []
        
        underlying_price = self.underlying_prices[underlying_symbol]
        options = []
        
        # Generate options around current price
        strike_range = strikes or self._generate_strike_range(underlying_price)
        exp_dates = expirations or self._generate_expiration_dates()
        
        for strike in strike_range:
            for exp_date in exp_dates:
                for option_type in ['C', 'P']:
                    option = self._generate_option_data(
                        underlying_symbol, strike, exp_date, option_type, underlying_price
                    )
                    options.append(option)
        
        return options
    
    async def get_market_snapshot(self) -> DataProvider.MarketDataSnapshot:
        """Get complete market data snapshot"""
        underlying_symbols = ['SPX', 'SPY', 'VIX']
        
        # Get underlying data
        underlying_data = await self.get_underlying_data(underlying_symbols)
        
        # Get options data
        options_data = []
        for symbol in ['SPX', 'SPY']:
            chain = await self.get_options_chain(symbol)
            options_data.extend(chain)
        
        snapshot = self.MarketDataSnapshot(
            timestamp=datetime.now(),
            underlying=underlying_data,
            options=options_data,
            metadata={
                'provider': 'mock',
                'total_options': len(options_data),
                'volatility_factor': self.volatility_factor
            }
        )
        
        return snapshot
    
    async def subscribe_real_time(self, symbols: List[str], 
                                 callback: Callable[[DataProvider.MarketDataSnapshot], None]) -> bool:
        """Subscribe to real-time mock data updates"""
        try:
            self.data_callback = callback
            
            # Start simulation task if not already running
            if not self.simulation_task:
                self.simulation_task = asyncio.create_task(self._simulation_loop())
            
            logger.info(f"Subscribed to real-time mock data for {symbols}")
            return True
        except Exception as e:
            self._handle_error(e)
            return False
    
    async def unsubscribe_real_time(self, symbols: List[str]) -> bool:
        """Unsubscribe from real-time mock data"""
        try:
            if self.simulation_task:
                self.simulation_task.cancel()
                self.simulation_task = None
            
            self.data_callback = None
            logger.info(f"Unsubscribed from real-time mock data for {symbols}")
            return True
        except Exception as e:
            self._handle_error(e)
            return False
    
    async def _simulation_loop(self):
        """Main simulation loop for real-time data"""
        try:
            while True:
                if self.connection_status == self.ConnectionStatus.CONNECTED:
                    snapshot = await self.get_market_snapshot()
                    self._handle_data_update(snapshot)
                
                await asyncio.sleep(self.update_interval)
                
        except asyncio.CancelledError:
            logger.info("Mock data simulation loop cancelled")
        except Exception as e:
            logger.error(f"Error in simulation loop: {e}")
            self._handle_error(e)
    
    def _initialize_options_universe(self):
        """Initialize the options universe for simulation"""
        # This would typically be loaded from a configuration file
        self.options_universe = []
        logger.info("Options universe initialized")
    
    def _update_underlying_prices(self):
        """Update underlying prices with realistic movement"""
        for symbol in self.underlying_prices:
            current_price = self.underlying_prices[symbol]
            
            # Random walk with mean reversion
            drift = 0.0001  # Small upward drift
            volatility = {
                'SPX': 0.0001,
                'SPY': 0.0001,
                'VIX': 0.001
            }.get(symbol, 0.0001) * self.volatility_factor
            
            change = drift + random.normalvariate(0, volatility)
            new_price = current_price * (1 + change)
            
            # Apply bounds to keep prices realistic
            if symbol == 'SPX':
                new_price = max(4000, min(6000, new_price))
            elif symbol == 'SPY':
                new_price = max(400, min(600, new_price))
            elif symbol == 'VIX':
                new_price = max(10, min(50, new_price))
            
            self.underlying_prices[symbol] = new_price
    
    def _generate_strike_range(self, underlying_price: float) -> List[float]:
        """Generate realistic strike range around underlying price"""
        # Generate strikes in 25-point increments for SPX-style, 5-point for SPY
        increment = 25 if underlying_price > 1000 else 5
        
        strikes = []
        for i in range(-10, 11):  # 20 strikes total
            strike = round((underlying_price + i * increment) / increment) * increment
            strikes.append(strike)
        
        return sorted(strikes)
    
    def _generate_expiration_dates(self) -> List[str]:
        """Generate realistic expiration dates"""
        base_date = datetime.now().date()
        expirations = []
        
        # Weekly expirations for next 8 weeks
        for i in range(1, 9):
            # Find next Friday
            days_ahead = (4 - base_date.weekday()) % 7
            if days_ahead == 0:
                days_ahead = 7
            next_friday = base_date + timedelta(days=days_ahead + (i-1)*7)
            expirations.append(next_friday.strftime('%Y-%m-%d'))
        
        return expirations
    
    def _generate_option_data(self, underlying_symbol: str, strike: float, 
                             expiration: str, option_type: str, underlying_price: float) -> Dict[str, Any]:
        """Generate realistic option market data"""
        # Calculate time to expiration
        exp_date = datetime.strptime(expiration, '%Y-%m-%d').date()
        dte = (exp_date - datetime.now().date()).days
        
        # Simple Black-Scholes approximation for mock data
        time_to_exp = max(dte / 365.0, 0.001)
        moneyness = underlying_price / strike if option_type == 'C' else strike / underlying_price
        
        # Realistic implied volatility
        base_iv = 0.15 + 0.1 * abs(1 - moneyness)  # Smile effect
        if dte < 7:
            base_iv += 0.05  # Higher IV for weekly options
        
        implied_vol = base_iv + random.uniform(-0.02, 0.02)
        implied_vol = max(0.05, min(1.0, implied_vol))
        
        # Approximate option price
        intrinsic = max(0, underlying_price - strike if option_type == 'C' else strike - underlying_price)
        time_value = implied_vol * underlying_price * np.sqrt(time_to_exp) * 0.4
        theoretical_price = intrinsic + time_value
        
        # Add bid/ask spread
        spread = max(0.05, theoretical_price * 0.02)
        bid = max(0.01, theoretical_price - spread/2)
        ask = theoretical_price + spread/2
        last = bid + random.uniform(0, spread)
        
        # Greeks (simplified)
        delta = 0.5 + (underlying_price - strike) / (2 * underlying_price) if option_type == 'C' else -0.5 + (strike - underlying_price) / (2 * underlying_price)
        delta = max(-1, min(1, delta))
        
        gamma = 0.01 * np.exp(-0.5 * ((underlying_price - strike) / (0.1 * underlying_price))**2)
        theta = -theoretical_price * 0.1 / 365
        vega = underlying_price * np.sqrt(time_to_exp) * 0.01
        
        return {
            'symbol': underlying_symbol,
            'strike': strike,
            'expiration': expiration,
            'type': option_type,
            'option_type': option_type,  # Duplicate for compatibility
            'dte': dte,
            'bid': round(bid, 2),
            'ask': round(ask, 2),
            'last': round(last, 2),
            'volume': random.randint(0, 1000),
            'open_interest': random.randint(100, 5000),
            'implied_vol': round(implied_vol, 4),
            'delta': round(delta, 4),
            'gamma': round(gamma, 4),
            'theta': round(theta, 4),
            'vega': round(vega, 4),
            'theoretical_price': round(theoretical_price, 2),
            'timestamp': datetime.now()
        }