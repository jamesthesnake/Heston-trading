"""
Interactive Brokers data provider for SPX/XSP options
"""
import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from collections import defaultdict

from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.order import Order
from ibapi.ticktype import TickTypeEnum

logger = logging.getLogger(__name__)

@dataclass
class OptionData:
    """Option market data structure"""
    symbol: str
    strike: float
    expiry: str
    option_type: str  # 'C' or 'P'
    
    # NBBO data
    bid: float = 0.0
    ask: float = 0.0
    bid_size: int = 0
    ask_size: int = 0
    midpoint: float = 0.0
    
    # Greeks and IV
    delta: float = 0.0
    gamma: float = 0.0
    theta: float = 0.0
    vega: float = 0.0
    implied_vol: float = 0.0
    
    # Trade data
    last_price: float = 0.0
    last_size: int = 0
    volume: int = 0
    open_interest: int = 0
    
    # Timestamps
    nbbo_timestamp: datetime = None
    last_trade_timestamp: datetime = None
    
    def update_nbbo(self, bid: float, ask: float, bid_size: int, ask_size: int):
        """Update NBBO data"""
        self.bid = bid
        self.ask = ask
        self.bid_size = bid_size
        self.ask_size = ask_size
        self.midpoint = (bid + ask) / 2 if bid > 0 and ask > 0 else 0.0
        self.nbbo_timestamp = datetime.now()

@dataclass
class UnderlyingData:
    """Underlying asset data"""
    symbol: str
    bid: float = 0.0
    ask: float = 0.0
    last: float = 0.0
    timestamp: datetime = None

class IBWrapper(EWrapper):
    """Interactive Brokers API wrapper"""
    
    def __init__(self, provider):
        self.provider = provider
        self.next_req_id = 1000
        
    def nextValidId(self, orderId: int):
        """Receive next valid order ID"""
        self.next_req_id = orderId
        logger.info(f"Connected to IB. Next valid ID: {orderId}")
        self.provider.is_connected = True
        
    def error(self, reqId: int, errorCode: int, errorString: str):
        """Handle errors"""
        if errorCode in [2104, 2106, 2158]:  # Market data warnings
            logger.debug(f"IB Warning {errorCode}: {errorString}")
        else:
            logger.error(f"IB Error {errorCode}: {errorString}")
            
    def tickPrice(self, reqId: int, tickType: int, price: float, attrib):
        """Handle tick price updates"""
        self.provider.handle_tick_price(reqId, tickType, price)
        
    def tickSize(self, reqId: int, tickType: int, size: int):
        """Handle tick size updates"""
        self.provider.handle_tick_size(reqId, tickType, size)
        
    def tickOptionComputation(self, reqId: int, tickType: int, tickAttrib: int,
                             impliedVol: float, delta: float, optPrice: float,
                             pvDividend: float, gamma: float, vega: float,
                             theta: float, undPrice: float):
        """Handle option Greeks and IV"""
        self.provider.handle_option_computation(reqId, impliedVol, delta, gamma, vega, theta)

class IBProvider(EClient):
    """Interactive Brokers data provider"""
    
    def __init__(self, config: dict, callback: Optional[Callable] = None):
        wrapper = IBWrapper(self)
        EClient.__init__(self, wrapper)
        
        self.config = config
        self.callback = callback
        self.is_connected = False
        
        # Data storage
        self.option_data: Dict[int, OptionData] = {}
        self.underlying_data: Dict[str, UnderlyingData] = {}
        self.req_id_to_contract: Dict[int, Contract] = {}
        
        # Request ID management
        self.next_req_id = 1000
        
        # Threading
        self.api_thread = None
        self.running = False
        
    def connect_ib(self, host: str = "127.0.0.1", port: int = 7497, client_id: int = 1):
        """Connect to Interactive Brokers"""
        try:
            self.connect(host, port, client_id)
            
            # Start API thread
            self.api_thread = threading.Thread(target=self.run, daemon=True)
            self.api_thread.start()
            
            # Wait for connection
            timeout = 10
            start_time = time.time()
            while not self.is_connected and (time.time() - start_time) < timeout:
                time.sleep(0.1)
                
            if not self.is_connected:
                raise ConnectionError("Failed to connect to IB within timeout")
                
            logger.info("Successfully connected to Interactive Brokers")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to IB: {e}")
            return False
            
    def disconnect_ib(self):
        """Disconnect from Interactive Brokers"""
        self.running = False
        self.disconnect()
        if self.api_thread:
            self.api_thread.join(timeout=5)
        logger.info("Disconnected from Interactive Brokers")
        
    def create_option_contract(self, symbol: str, strike: float, expiry: str, option_type: str) -> Contract:
        """Create option contract"""
        contract = Contract()
        contract.symbol = symbol
        contract.secType = "OPT"
        contract.exchange = "SMART"
        contract.currency = "USD"
        contract.strike = strike
        contract.lastTradeDateOrContractMonth = expiry
        contract.right = option_type
        return contract
        
    def create_stock_contract(self, symbol: str) -> Contract:
        """Create stock contract"""
        contract = Contract()
        contract.symbol = symbol
        contract.secType = "STK"
        contract.exchange = "SMART"
        contract.currency = "USD"
        return contract
        
    def create_index_contract(self, symbol: str) -> Contract:
        """Create index contract"""
        contract = Contract()
        contract.symbol = symbol
        contract.secType = "IND"
        contract.exchange = "CBOE"
        contract.currency = "USD"
        return contract
        
    def create_future_contract(self, symbol: str, expiry: str) -> Contract:
        """Create futures contract"""
        contract = Contract()
        contract.symbol = symbol
        contract.secType = "FUT"
        contract.exchange = "CME"
        contract.currency = "USD"
        contract.lastTradeDateOrContractMonth = expiry
        return contract
        
    def subscribe_option_data(self, symbol: str, strike: float, expiry: str, option_type: str):
        """Subscribe to option market data"""
        contract = self.create_option_contract(symbol, strike, expiry, option_type)
        req_id = self.next_req_id
        self.next_req_id += 1
        
        # Store contract mapping
        self.req_id_to_contract[req_id] = contract
        
        # Initialize option data
        option_data = OptionData(
            symbol=symbol,
            strike=strike,
            expiry=expiry,
            option_type=option_type
        )
        self.option_data[req_id] = option_data
        
        # Request market data
        self.reqMktData(req_id, contract, "", False, False, [])
        
        # Request option computations (Greeks)
        self.reqMktData(req_id, contract, "100,101,104,105,106", False, False, [])
        
        logger.debug(f"Subscribed to {symbol} {strike} {expiry} {option_type}")
        
    def subscribe_underlying_data(self, symbol: str):
        """Subscribe to underlying asset data"""
        if symbol == "SPX":
            contract = self.create_index_contract("SPX")
        elif symbol == "VIX":
            contract = self.create_index_contract("VIX")
        elif symbol.startswith("ES"):
            # ES futures - need to determine front month
            expiry = self._get_front_month_expiry()
            contract = self.create_future_contract("ES", expiry)
        else:
            contract = self.create_stock_contract(symbol)
            
        req_id = self.next_req_id
        self.next_req_id += 1
        
        # Store contract mapping
        self.req_id_to_contract[req_id] = contract
        
        # Initialize underlying data
        self.underlying_data[symbol] = UnderlyingData(symbol=symbol)
        
        # Request market data
        self.reqMktData(req_id, contract, "", False, False, [])
        
        logger.debug(f"Subscribed to underlying {symbol}")
        
    def _get_front_month_expiry(self) -> str:
        """Get front month expiry for ES futures"""
        now = datetime.now()
        # ES expires quarterly (Mar, Jun, Sep, Dec)
        quarters = [3, 6, 9, 12]
        
        for month in quarters:
            if month >= now.month:
                return f"{now.year}{month:02d}"
        
        # Next year's March
        return f"{now.year + 1}03"
        
    def handle_tick_price(self, req_id: int, tick_type: int, price: float):
        """Handle price tick updates"""
        if req_id in self.option_data:
            option = self.option_data[req_id]
            
            if tick_type == TickTypeEnum.BID:
                option.bid = price
            elif tick_type == TickTypeEnum.ASK:
                option.ask = price
            elif tick_type == TickTypeEnum.LAST:
                option.last_price = price
                option.last_trade_timestamp = datetime.now()
                
            # Update midpoint
            if option.bid > 0 and option.ask > 0:
                option.midpoint = (option.bid + option.ask) / 2
                option.nbbo_timestamp = datetime.now()
                
        elif req_id in self.req_id_to_contract:
            # Handle underlying data
            contract = self.req_id_to_contract[req_id]
            symbol = contract.symbol
            
            if symbol in self.underlying_data:
                underlying = self.underlying_data[symbol]
                
                if tick_type == TickTypeEnum.BID:
                    underlying.bid = price
                elif tick_type == TickTypeEnum.ASK:
                    underlying.ask = price
                elif tick_type == TickTypeEnum.LAST:
                    underlying.last = price
                    
                underlying.timestamp = datetime.now()
                
    def handle_tick_size(self, req_id: int, tick_type: int, size: int):
        """Handle size tick updates"""
        if req_id in self.option_data:
            option = self.option_data[req_id]
            
            if tick_type == TickTypeEnum.BID_SIZE:
                option.bid_size = size
            elif tick_type == TickTypeEnum.ASK_SIZE:
                option.ask_size = size
            elif tick_type == TickTypeEnum.LAST_SIZE:
                option.last_size = size
            elif tick_type == TickTypeEnum.VOLUME:
                option.volume = size
                
    def handle_option_computation(self, req_id: int, implied_vol: float, delta: float,
                                 gamma: float, vega: float, theta: float):
        """Handle option Greeks and IV"""
        if req_id in self.option_data:
            option = self.option_data[req_id]
            
            if implied_vol > 0:
                option.implied_vol = implied_vol
            if abs(delta) < 1:
                option.delta = delta
            if gamma > 0:
                option.gamma = gamma
            if vega > 0:
                option.vega = vega
            if theta != 0:
                option.theta = theta
                
    def get_option_snapshot(self) -> List[OptionData]:
        """Get current options snapshot"""
        return list(self.option_data.values())
        
    def get_underlying_snapshot(self) -> Dict[str, UnderlyingData]:
        """Get current underlying data snapshot"""
        return self.underlying_data.copy()
