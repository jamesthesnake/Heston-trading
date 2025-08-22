"""
Enhanced Interactive Brokers Data Provider
Implements the DataProvider interface for IB integration
"""
import asyncio
import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
from collections import defaultdict

# Handle optional IB API dependency
try:
    from ibapi.client import EClient
    from ibapi.wrapper import EWrapper
    from ibapi.contract import Contract
    from ibapi.ticktype import TickTypeEnum
    IB_AVAILABLE = True
except ImportError:
    # Create dummy classes if IB API not available
    class EClient:
        pass
    class EWrapper:
        pass
    class Contract:
        pass
    class TickTypeEnum:
        @staticmethod
        def to_str(tick_type):
            return f"TICK_{tick_type}"
    IB_AVAILABLE = False

from .base_provider import DataProvider

logger = logging.getLogger(__name__)

class IBDataProvider(DataProvider, EWrapper, EClient):
    """Enhanced Interactive Brokers data provider implementing the DataProvider interface"""
    
    def __init__(self, config: Dict[str, Any]):
        DataProvider.__init__(self, config)
        if IB_AVAILABLE:
            EClient.__init__(self, self)
        else:
            logger.warning("IB API not available - IB provider will not function")
        
        self.provider_type = "interactive_brokers"
        self.host = config.get('host', '127.0.0.1')
        self.port = config.get('port', 7497)
        self.client_id = config.get('client_id', 1)
        
        # Connection management
        self.connection_thread: Optional[threading.Thread] = None
        self.is_running = False
        self._connected = False
        
        # Data storage
        self.market_data: Dict[int, Dict] = {}
        self.contracts: Dict[int, Contract] = {}
        self.next_req_id = 1000
        
        # Real-time subscription management
        self.subscribed_symbols: List[str] = []
        self.subscription_req_ids: Dict[str, int] = {}
        
        logger.info("Enhanced IB data provider initialized")
    
    def _get_required_config_fields(self) -> List[str]:
        """IB provider has optional config fields"""
        return []
    
    async def connect(self) -> bool:
        """Connect to Interactive Brokers"""
        if not IB_AVAILABLE:
            logger.error("Cannot connect - IB API not available")
            self._update_connection_status(self.ConnectionStatus.ERROR)
            return False
            
        try:
            self._update_connection_status(self.ConnectionStatus.CONNECTING)
            
            # Start connection in separate thread
            self.connection_thread = threading.Thread(target=self._connect_thread)
            self.connection_thread.daemon = True
            self.connection_thread.start()
            
            # Wait for connection with timeout
            timeout = 15
            start_time = time.time()
            while time.time() - start_time < timeout:
                if self._connected:
                    self._update_connection_status(self.ConnectionStatus.CONNECTED)
                    logger.info(f"Connected to IB at {self.host}:{self.port}")
                    return True
                await asyncio.sleep(0.1)
            
            self._update_connection_status(self.ConnectionStatus.ERROR)
            logger.error("Failed to connect to IB within timeout")
            return False
            
        except Exception as e:
            self._update_connection_status(self.ConnectionStatus.ERROR)
            self._handle_error(e)
            return False
    
    def _connect_thread(self):
        """Connect to IB in separate thread"""
        try:
            super().connect(self.host, self.port, self.client_id)
            self.is_running = True
            self.run()
        except Exception as e:
            logger.error(f"IB connection thread error: {e}")
            self._handle_error(e)
    
    async def disconnect(self) -> bool:
        """Disconnect from Interactive Brokers"""
        try:
            self.is_running = False
            super().disconnect()
            
            if self.connection_thread and self.connection_thread.is_alive():
                self.connection_thread.join(timeout=5)
                
            self._update_connection_status(self.ConnectionStatus.DISCONNECTED)
            self._connected = False
            logger.info("Disconnected from IB")
            return True
        except Exception as e:
            self._handle_error(e)
            return False
    
    async def is_connected(self) -> bool:
        """Check if connected to IB"""
        return self._connected and self.isConnected()
    
    async def get_underlying_data(self, symbols: List[str]) -> Dict[str, Any]:
        """Get underlying asset data from IB"""
        data = {}
        
        for symbol in symbols:
            try:
                contract = self._create_underlying_contract(symbol)
                req_id = self._get_next_req_id()
                
                # Clear previous data
                if req_id in self.market_data:
                    del self.market_data[req_id]
                
                # Request market data
                self.reqMktData(req_id, contract, "", False, False, [])
                # Wait for data with timeout
                timeout = 5
                start_time = time.time()
                while time.time() - start_time < timeout:
                    if req_id in self.market_data and 'LAST' in self.market_data[req_id]:
                        break
                    await asyncio.sleep(0.1)
                
                # Cancel market data request
                self.cancelMktData(req_id)
                
                if req_id in self.market_data:
                    raw_data = self.market_data[req_id]
                    data[symbol] = self._format_underlying_data(symbol, raw_data)
                else:
                    logger.warning(f"No data received for {symbol}")
                
            except Exception as e:
                logger.error(f"Error getting underlying data for {symbol}: {e}")
        
        return data
    
    async def get_options_chain(self, underlying_symbol: str, 
                               strikes: Optional[List[float]] = None,
                               expirations: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Get options chain from IB"""
        options = []
        
        try:
            # For now, return empty list as full options chain implementation
            # requires handling contractDetails callback which is complex
            logger.info(f"Options chain request for {underlying_symbol} - implementation pending")
            
            # In a full implementation, this would:
            # 1. Create option contract template
            # 2. Use reqContractDetails to get all available contracts
            # 3. Subscribe to market data for each contract
            # 4. Format the results
            
        except Exception as e:
            logger.error(f"Error getting options chain for {underlying_symbol}: {e}")
        
        return options
    
    async def get_market_snapshot(self) -> DataProvider.MarketDataSnapshot:
        """Get complete market snapshot from IB"""
        underlying_symbols = ['SPX', 'SPY', 'VIX']
        
        underlying_data = await self.get_underlying_data(underlying_symbols)
        options_data = []  # Would get from options chain in full implementation
        
        return self.MarketDataSnapshot(
            timestamp=datetime.now(),
            underlying=underlying_data,
            options=options_data,
            metadata={
                'provider': 'interactive_brokers',
                'connection_status': self.connection_status.value,
                'client_id': self.client_id,
                'host': self.host,
                'port': self.port
            }
        )
    
    async def subscribe_real_time(self, symbols: List[str], 
                                 callback: Callable[[DataProvider.MarketDataSnapshot], None]) -> bool:
        """Subscribe to real-time data from IB"""
        try:
            self.data_callback = callback
            
            for symbol in symbols:
                if symbol not in self.subscribed_symbols:
                    contract = self._create_underlying_contract(symbol)
                    req_id = self._get_next_req_id()
                    
                    self.contracts[req_id] = contract
                    self.subscription_req_ids[symbol] = req_id
                    
                    # Subscribe to market data
                    self.reqMktData(req_id, contract, "", False, False, [])
                    self.subscribed_symbols.append(symbol)
            
            logger.info(f"Subscribed to real-time IB data for {symbols}")
            return True
            
        except Exception as e:
            self._handle_error(e)
            return False
    
    async def unsubscribe_real_time(self, symbols: List[str]) -> bool:
        """Unsubscribe from real-time IB data"""
        try:
            for symbol in symbols:
                if symbol in self.subscription_req_ids:
                    req_id = self.subscription_req_ids[symbol]
                    self.cancelMktData(req_id)
                    
                    # Clean up
                    if req_id in self.contracts:
                        del self.contracts[req_id]
                    if req_id in self.market_data:
                        del self.market_data[req_id]
                    del self.subscription_req_ids[symbol]
                    
                    if symbol in self.subscribed_symbols:
                        self.subscribed_symbols.remove(symbol)
            
            logger.info(f"Unsubscribed from real-time IB data for {symbols}")
            return True
            
        except Exception as e:
            self._handle_error(e)
            return False
    
    # IB Wrapper methods (callbacks)
    
    def nextValidId(self, orderId: int):
        """Receive next valid order ID"""
        self.next_req_id = orderId
        self._connected = True
        logger.info(f"IB connected. Next valid ID: {orderId}")
    
    def tickPrice(self, reqId: int, tickType: int, price: float, attrib):
        """Handle price tick data"""
        if reqId not in self.market_data:
            self.market_data[reqId] = {}
        
        tick_name = TickTypeEnum.to_str(tickType)
        self.market_data[reqId][tick_name] = price
        self.market_data[reqId]['timestamp'] = datetime.now()
        
        # If this is a subscribed symbol, trigger callback
        if self.data_callback and reqId in self.contracts:
            self._trigger_data_callback(reqId)
    
    def tickSize(self, reqId: int, tickType: int, size: int):
        """Handle size tick data"""
        if reqId not in self.market_data:
            self.market_data[reqId] = {}
        
        tick_name = TickTypeEnum.to_str(tickType)
        self.market_data[reqId][tick_name + '_size'] = size
    
    def tickOptionComputation(self, reqId: int, tickType: int, tickAttrib: int,
                             impliedVol: float, delta: float, optPrice: float,
                             pvDividend: float, gamma: float, vega: float,
                             theta: float, undPrice: float):
        """Handle option Greeks and IV"""
        if reqId not in self.market_data:
            self.market_data[reqId] = {}
        
        greeks = {
            'implied_vol': impliedVol if impliedVol != -1 else 0,
            'delta': delta if delta != -1 else 0,
            'gamma': gamma if gamma != -1 else 0,
            'vega': vega if vega != -1 else 0,
            'theta': theta if theta != -1 else 0,
            'theoretical_price': optPrice if optPrice != -1 else 0
        }
        
        self.market_data[reqId].update(greeks)
    
    def error(self, reqId: int, errorCode: int, errorString: str, advancedOrderRejectJson=""):
        """Handle IB errors"""
        if errorCode in [2104, 2106, 2158, 10167]:  # Market data warnings/info
            logger.debug(f"IB Info {errorCode}: {errorString}")
        elif errorCode in [502, 504, 1100, 1102]:  # Connection errors
            logger.error(f"IB Connection Error {errorCode}: {errorString}")
            self._update_connection_status(self.ConnectionStatus.ERROR)
            self._connected = False
        else:
            logger.error(f"IB Error {errorCode}: {errorString}")
            error = Exception(f"IB Error {errorCode}: {errorString}")
            self._handle_error(error)
    
    def connectionClosed(self):
        """Handle connection closed"""
        logger.warning("IB connection closed")
        self._connected = False
        self._update_connection_status(self.ConnectionStatus.DISCONNECTED)
    
    # Helper methods
    
    def _get_next_req_id(self) -> int:
        """Get next request ID"""
        req_id = self.next_req_id
        self.next_req_id += 1
        return req_id
    
    def _create_underlying_contract(self, symbol: str) -> Contract:
        """Create contract for underlying asset"""
        contract = Contract()
        contract.symbol = symbol
        contract.currency = "USD"
        
        if symbol in ['SPX', 'VIX']:
            contract.secType = "IND"
            contract.exchange = "CBOE"
        else:  # SPY, etc.
            contract.secType = "STK"
            contract.exchange = "SMART"
        
        return contract
    
    def _format_underlying_data(self, symbol: str, raw_data: Dict) -> Dict[str, Any]:
        """Format raw IB data to standard format"""
        last_price = raw_data.get('LAST', 0)
        bid_price = raw_data.get('BID', 0)
        ask_price = raw_data.get('ASK', 0)
        
        # Calculate change (would need previous close for accurate calculation)
        change = 0
        change_pct = 0
        
        return {
            'symbol': symbol,
            'last': last_price,
            'bid': bid_price,
            'ask': ask_price,
            'change': change,
            'change_pct': change_pct,
            'volume': raw_data.get('VOLUME', 0),
            'open': raw_data.get('OPEN', last_price),
            'high': raw_data.get('HIGH', last_price),
            'low': raw_data.get('LOW', last_price),
            'timestamp': raw_data.get('timestamp', datetime.now())
        }
    
    def _trigger_data_callback(self, req_id: int):
        """Trigger data callback for real-time updates"""
        try:
            # Find symbol for this req_id
            symbol = None
            for sym, rid in self.subscription_req_ids.items():
                if rid == req_id:
                    symbol = sym
                    break
            
            if symbol and self.data_callback:
                # Create snapshot with current data
                underlying_data = {symbol: self._format_underlying_data(symbol, self.market_data[req_id])}
                
                snapshot = self.MarketDataSnapshot(
                    timestamp=datetime.now(),
                    underlying=underlying_data,
                    options=[],  # Real-time options data would go here
                    metadata={
                        'provider': 'interactive_brokers',
                        'update_type': 'real_time',
                        'symbol': symbol
                    }
                )
                
                self._handle_data_update(snapshot)
                
        except Exception as e:
            logger.error(f"Error triggering data callback: {e}")