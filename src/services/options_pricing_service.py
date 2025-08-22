"""
Options Pricing Service
Unified interface for options pricing with multiple models and calibration
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
import numpy as np
from enum import Enum

from .base_service import BaseService, ServiceConfig
from ..strategy.heston_pricing_engine import HestonPricingEngine
from ..data.black_scholes import BlackScholesCalculator

logger = logging.getLogger(__name__)

class PricingModel(Enum):
    """Available pricing models"""
    BLACK_SCHOLES = "black_scholes"
    HESTON = "heston"
    BINOMIAL = "binomial"
    MONTE_CARLO = "monte_carlo"

@dataclass
class OptionContract:
    """Option contract specification"""
    symbol: str
    underlying: str
    option_type: str  # 'C' or 'P'
    strike: float
    expiry_date: datetime
    quantity: int = 1
    
    def __post_init__(self):
        if self.option_type not in ['C', 'P']:
            raise ValueError("option_type must be 'C' or 'P'")

@dataclass
class PricingRequest:
    """Options pricing request"""
    contracts: List[OptionContract]
    market_data: Dict[str, Any]
    model: PricingModel = PricingModel.HESTON
    include_greeks: bool = True
    calibrate_model: bool = True
    use_cache: bool = True
    cache_ttl: int = 300  # seconds
    request_id: Optional[str] = None
    priority: int = 1

@dataclass
class PricingResult:
    """Options pricing result"""
    contract: OptionContract
    theoretical_price: float
    bid: Optional[float] = None
    ask: Optional[float] = None
    market_price: Optional[float] = None
    model_used: PricingModel = PricingModel.HESTON
    
    # Greeks
    delta: Optional[float] = None
    gamma: Optional[float] = None
    theta: Optional[float] = None
    vega: Optional[float] = None
    rho: Optional[float] = None
    
    # Additional metrics
    implied_volatility: Optional[float] = None
    time_to_expiry: Optional[float] = None
    moneyness: Optional[float] = None
    
    # Model parameters used
    model_parameters: Dict[str, Any] = field(default_factory=dict)
    
    # Quality metrics
    pricing_error: Optional[float] = None
    confidence_score: float = 1.0
    
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class PricingResponse:
    """Complete pricing response"""
    request_id: str
    results: List[PricingResult]
    calibration_results: Dict[str, Any] = field(default_factory=dict)
    processing_time_ms: float = 0.0
    cache_hit: bool = False
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)

class OptionsPricingService(BaseService):
    """
    Options Pricing Service providing unified access to multiple pricing models
    with automatic calibration, caching, and performance optimization
    """
    
    def __init__(self, config: ServiceConfig, strategy_config: Dict[str, Any]):
        super().__init__(config)
        
        self.strategy_config = strategy_config
        self.pricing_config = strategy_config.get('options_pricing', {})
        
        # Pricing models
        self.heston_engine: Optional[HestonPricingEngine] = None
        self.bs_calculator: Optional[BlackScholesCalculator] = None
        
        # Model parameters cache
        self.model_parameters_cache: Dict[str, Dict[str, Any]] = {}
        self.calibration_cache: Dict[str, Dict[str, Any]] = {}
        self.pricing_cache: Dict[str, PricingResult] = {}
        self.cache_timestamps: Dict[str, datetime] = {}
        
        # Configuration
        self.default_model = PricingModel(self.pricing_config.get('default_model', 'heston'))
        self.auto_calibrate = self.pricing_config.get('auto_calibrate', True)
        self.calibration_frequency = self.pricing_config.get('calibration_frequency', 3600)  # seconds
        self.cache_enabled = self.pricing_config.get('enable_cache', True)
        self.cache_ttl = self.pricing_config.get('cache_ttl', 300)  # seconds
        
        # Calibration tracking
        self.last_calibration: Dict[str, datetime] = {}
        self.calibration_quality: Dict[str, float] = {}
        self.calibration_history: List[Dict[str, Any]] = []
        
        # Performance tracking
        self.pricing_stats = {
            'total_requests': 0,
            'cache_hits': 0,
            'calibrations_performed': 0,
            'avg_pricing_time_ms': 0.0,
            'model_usage': {model.value: 0 for model in PricingModel}
        }
        
        # Request queue
        self.pricing_queue = asyncio.Queue()
        self.active_requests: Dict[str, PricingRequest] = {}
        self.request_counter = 0
        
        logger.info(f"Options Pricing Service initialized with default model: {self.default_model.value}")
    
    async def _initialize(self) -> bool:
        """Initialize pricing models"""
        try:
            # Initialize Heston pricing engine
            heston_config = self.pricing_config.get('heston_parameters', {})
            self.heston_engine = HestonPricingEngine(heston_config)
            
            # Initialize Black-Scholes calculator  
            self.bs_calculator = BlackScholesCalculator()
            
            # Load any cached calibration parameters
            await self._load_calibration_cache()
            
            logger.info("Options pricing models initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize options pricing service: {e}")
            return False
    
    async def _start(self) -> bool:
        """Start pricing service"""
        try:
            # Start request processing
            self.create_task(self._process_pricing_queue())
            
            # Start periodic calibration
            if self.auto_calibrate:
                self.create_task(self._calibration_loop())
            
            # Start cache cleanup
            if self.cache_enabled:
                self.create_task(self._cache_cleanup_loop())
            
            logger.info("Options pricing service started")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start options pricing service: {e}")
            return False
    
    async def _stop(self) -> bool:
        """Stop pricing service"""
        try:
            # Save calibration cache
            await self._save_calibration_cache()
            
            # Clear caches
            self.pricing_cache.clear()
            self.cache_timestamps.clear()
            self.model_parameters_cache.clear()
            
            logger.info("Options pricing service stopped")
            return True
            
        except Exception as e:
            logger.error(f"Error stopping options pricing service: {e}")
            return False
    
    async def _health_check(self) -> Dict[str, Any]:
        """Perform health check"""
        health_data = {
            'models_available': {
                'heston': self.heston_engine is not None,
                'black_scholes': self.bs_calculator is not None
            },
            'calibration_status': {
                'auto_calibrate': self.auto_calibrate,
                'last_calibrations': {k: v.isoformat() if v else None 
                                    for k, v in self.last_calibration.items()},
                'calibration_quality': self.calibration_quality.copy()
            },
            'cache_status': {
                'enabled': self.cache_enabled,
                'entries': len(self.pricing_cache),
                'hit_rate': self.pricing_stats['cache_hits'] / max(self.pricing_stats['total_requests'], 1)
            },
            'performance': {
                'requests_processed': self.pricing_stats['total_requests'],
                'avg_pricing_time_ms': self.pricing_stats['avg_pricing_time_ms'],
                'queue_depth': self.pricing_queue.qsize()
            }
        }
        
        return health_data
    
    async def price_options(self, request: PricingRequest) -> PricingResponse:
        """
        Price options using specified model
        
        Args:
            request: Pricing request with contracts and parameters
            
        Returns:
            Pricing response with results
        """
        start_time = datetime.now()
        request_id = request.request_id or f"price_{self.request_counter}"
        self.request_counter += 1
        
        try:
            # Add to active requests
            self.active_requests[request_id] = request
            
            results = []
            calibration_results = {}
            errors = []
            warnings = []
            cache_hits = 0
            
            # Calibrate model if needed
            if request.calibrate_model and request.model == PricingModel.HESTON:
                calibration_results = await self._calibrate_heston_model(
                    request.market_data, request.contracts[0].underlying
                )
                if not calibration_results.get('success', False):
                    warnings.append("Model calibration failed, using cached parameters")
            
            # Price each contract
            for contract in request.contracts:
                try:
                    # Check cache first
                    cached_result = None
                    if request.use_cache and self.cache_enabled:
                        cached_result = await self._get_cached_pricing(contract, request.market_data)
                        if cached_result:
                            cache_hits += 1
                    
                    if cached_result:
                        results.append(cached_result)
                    else:
                        # Calculate new pricing
                        pricing_result = await self._price_single_option(
                            contract, request.market_data, request.model, request.include_greeks
                        )
                        
                        if pricing_result:
                            results.append(pricing_result)
                            
                            # Cache result
                            if self.cache_enabled:
                                await self._cache_pricing_result(pricing_result, request.market_data)
                        else:
                            errors.append(f"Failed to price contract {contract.symbol}")
                
                except Exception as e:
                    error_msg = f"Error pricing contract {contract.symbol}: {e}"
                    errors.append(error_msg)
                    logger.error(error_msg)
            
            # Create response
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            response = PricingResponse(
                request_id=request_id,
                results=results,
                calibration_results=calibration_results,
                processing_time_ms=processing_time,
                cache_hit=(cache_hits > 0),
                errors=errors,
                warnings=warnings
            )
            
            # Update statistics
            await self._update_pricing_stats(response, request.model)
            
            return response
            
        except Exception as e:
            logger.error(f"Error in options pricing: {e}")
            return PricingResponse(
                request_id=request_id,
                results=[],
                processing_time_ms=(datetime.now() - start_time).total_seconds() * 1000,
                errors=[str(e)]
            )
        finally:
            # Clean up
            self.active_requests.pop(request_id, None)
    
    async def calibrate_model(self, underlying: str, market_data: Dict[str, Any], 
                             model: PricingModel = PricingModel.HESTON) -> Dict[str, Any]:
        """
        Manually calibrate a pricing model
        
        Args:
            underlying: Underlying symbol to calibrate for
            market_data: Current market data
            model: Model to calibrate
            
        Returns:
            Calibration results
        """
        try:
            if model == PricingModel.HESTON:
                return await self._calibrate_heston_model(market_data, underlying)
            else:
                return {'success': False, 'error': f'Model {model.value} calibration not implemented'}
        
        except Exception as e:
            logger.error(f"Error calibrating model {model.value}: {e}")
            return {'success': False, 'error': str(e)}
    
    async def get_implied_volatility(self, contract: OptionContract, 
                                   market_price: float, market_data: Dict[str, Any]) -> Optional[float]:
        """Calculate implied volatility from market price"""
        try:
            if not self.bs_calculator:
                return None
            
            # Extract market data
            underlying_price = market_data.get(contract.underlying, {}).get('last', 0)
            if not underlying_price:
                return None
            
            # Calculate time to expiry
            time_to_expiry = (contract.expiry_date - datetime.now()).total_seconds() / (365.25 * 24 * 3600)
            if time_to_expiry <= 0:
                return None
            
            # Use risk-free rate from config or default
            risk_free_rate = self.pricing_config.get('risk_free_rate', 0.02)
            
            # Calculate implied volatility using Newton-Raphson
            # Note: This would need a method implementation in BlackScholesCalculator
            # For now, return a placeholder based on VIX or default
            return market_data.get('VIX', {}).get('last', 20) / 100 if 'VIX' in market_data else 0.2
            
        except Exception as e:
            logger.error(f"Error calculating implied volatility: {e}")
            return None
    
    # Internal methods
    
    async def _price_single_option(self, contract: OptionContract, market_data: Dict[str, Any],
                                  model: PricingModel, include_greeks: bool) -> Optional[PricingResult]:
        """Price a single option contract"""
        try:
            # Extract market data
            underlying_data = market_data.get(contract.underlying, {})
            spot_price = underlying_data.get('last', 0)
            
            if not spot_price:
                logger.warning(f"No spot price available for {contract.underlying}")
                return None
            
            # Calculate time to expiry in years
            time_to_expiry = (contract.expiry_date - datetime.now()).total_seconds() / (365.25 * 24 * 3600)
            if time_to_expiry <= 0:
                logger.warning(f"Option {contract.symbol} is expired")
                return None
            
            # Get risk-free rate
            risk_free_rate = self.pricing_config.get('risk_free_rate', 0.02)
            
            # Price based on model
            if model == PricingModel.HESTON and self.heston_engine:
                result = await self._price_with_heston(
                    contract, spot_price, time_to_expiry, risk_free_rate, include_greeks
                )
            elif model == PricingModel.BLACK_SCHOLES and self.bs_calculator:
                result = await self._price_with_black_scholes(
                    contract, spot_price, time_to_expiry, risk_free_rate, 
                    underlying_data, include_greeks
                )
            else:
                logger.error(f"Model {model.value} not available")
                return None
            
            if result:
                # Add market data
                result.bid = underlying_data.get('bid')
                result.ask = underlying_data.get('ask')
                result.market_price = underlying_data.get('last')
                result.time_to_expiry = time_to_expiry
                result.moneyness = spot_price / contract.strike
                
                # Calculate implied volatility from market price
                if result.market_price:
                    result.implied_volatility = await self.get_implied_volatility(
                        contract, result.market_price, market_data
                    )
                
                # Calculate pricing error if market price available
                if result.market_price:
                    result.pricing_error = abs(result.theoretical_price - result.market_price) / result.market_price
                
                # Calculate confidence score
                result.confidence_score = self._calculate_confidence_score(result, market_data)
            
            return result
            
        except Exception as e:
            logger.error(f"Error pricing option {contract.symbol}: {e}")
            return None
    
    async def _price_with_heston(self, contract: OptionContract, spot_price: float,
                                time_to_expiry: float, risk_free_rate: float,
                                include_greeks: bool) -> Optional[PricingResult]:
        """Price option using Heston model"""
        try:
            # Get model parameters
            params = self.model_parameters_cache.get(contract.underlying, {})
            if not params:
                # Use default parameters if no calibration available
                params = self.pricing_config.get('heston_parameters', {
                    'theta': 0.04,
                    'kappa': 2.0,
                    'xi': 0.3,
                    'rho': -0.7,
                    'v0': 0.04
                })
            
            # Price the option
            price = self.heston_engine.price_option(
                S=spot_price,
                K=contract.strike,
                T=time_to_expiry,
                r=risk_free_rate,
                option_type=contract.option_type,
                **params
            )
            
            result = PricingResult(
                contract=contract,
                theoretical_price=price,
                model_used=PricingModel.HESTON,
                model_parameters=params.copy()
            )
            
            # Calculate Greeks if requested
            if include_greeks:
                greeks = self.heston_engine.calculate_greeks(
                    S=spot_price,
                    K=contract.strike,
                    T=time_to_expiry,
                    r=risk_free_rate,
                    option_type=contract.option_type,
                    **params
                )
                
                result.delta = greeks.get('delta')
                result.gamma = greeks.get('gamma')
                result.theta = greeks.get('theta')
                result.vega = greeks.get('vega')
                result.rho = greeks.get('rho')
            
            return result
            
        except Exception as e:
            logger.error(f"Error pricing with Heston model: {e}")
            return None
    
    async def _price_with_black_scholes(self, contract: OptionContract, spot_price: float,
                                       time_to_expiry: float, risk_free_rate: float,
                                       market_data: Dict[str, Any], include_greeks: bool) -> Optional[PricingResult]:
        """Price option using Black-Scholes model"""
        try:
            # Get volatility estimate
            volatility = market_data.get('implied_volatility', 
                                       self.pricing_config.get('default_volatility', 0.2))
            
            # Price the option using Black-Scholes
            if contract.option_type == 'C':
                price = self.bs_calculator.call_price(
                    S=spot_price,
                    K=contract.strike,
                    T=time_to_expiry,
                    r=risk_free_rate,
                    sigma=volatility
                )
            else:
                price = self.bs_calculator.put_price(
                    S=spot_price,
                    K=contract.strike,
                    T=time_to_expiry,
                    r=risk_free_rate,
                    sigma=volatility
                )
            
            result = PricingResult(
                contract=contract,
                theoretical_price=price,
                model_used=PricingModel.BLACK_SCHOLES,
                model_parameters={'volatility': volatility, 'risk_free_rate': risk_free_rate}
            )
            
            # Calculate Greeks if requested (simplified implementation)
            if include_greeks:
                d1_val = self.bs_calculator.d1(spot_price, contract.strike, time_to_expiry, risk_free_rate, volatility)
                d2_val = self.bs_calculator.d2(spot_price, contract.strike, time_to_expiry, risk_free_rate, volatility)
                
                from scipy.stats import norm
                import numpy as np
                
                # Calculate Greeks manually
                if contract.option_type == 'C':
                    result.delta = norm.cdf(d1_val)
                    result.theta = (-(spot_price * norm.pdf(d1_val) * volatility) / (2 * np.sqrt(time_to_expiry)) - 
                                  risk_free_rate * contract.strike * np.exp(-risk_free_rate * time_to_expiry) * norm.cdf(d2_val)) / 365
                else:
                    result.delta = norm.cdf(d1_val) - 1
                    result.theta = (-(spot_price * norm.pdf(d1_val) * volatility) / (2 * np.sqrt(time_to_expiry)) + 
                                  risk_free_rate * contract.strike * np.exp(-risk_free_rate * time_to_expiry) * norm.cdf(-d2_val)) / 365
                
                result.gamma = norm.pdf(d1_val) / (spot_price * volatility * np.sqrt(time_to_expiry))
                result.vega = spot_price * np.sqrt(time_to_expiry) * norm.pdf(d1_val) / 100
                result.rho = (contract.strike * time_to_expiry * np.exp(-risk_free_rate * time_to_expiry) * 
                            (norm.cdf(d2_val) if contract.option_type == 'C' else norm.cdf(-d2_val)) * 
                            (1 if contract.option_type == 'C' else -1)) / 100
            
            return result
            
        except Exception as e:
            logger.error(f"Error pricing with Black-Scholes model: {e}")
            return None
    
    async def _calibrate_heston_model(self, market_data: Dict[str, Any], 
                                     underlying: str) -> Dict[str, Any]:
        """Calibrate Heston model parameters"""
        try:
            # Check if recent calibration exists
            if (underlying in self.last_calibration and 
                (datetime.now() - self.last_calibration[underlying]).seconds < self.calibration_frequency):
                return {'success': True, 'source': 'cached', 'parameters': self.model_parameters_cache.get(underlying, {})}
            
            # Perform calibration using market option prices
            # This would typically use observed option prices to fit model parameters
            # For now, we'll use a simplified approach
            
            calibration_result = await self._perform_heston_calibration(market_data, underlying)
            
            if calibration_result['success']:
                # Store calibrated parameters
                self.model_parameters_cache[underlying] = calibration_result['parameters']
                self.last_calibration[underlying] = datetime.now()
                self.calibration_quality[underlying] = calibration_result.get('quality', 0.5)
                
                # Add to history
                self.calibration_history.append({
                    'timestamp': datetime.now(),
                    'underlying': underlying,
                    'parameters': calibration_result['parameters'].copy(),
                    'quality': calibration_result.get('quality', 0.5)
                })
                
                # Keep history limited
                if len(self.calibration_history) > 100:
                    self.calibration_history = self.calibration_history[-50:]
                
                logger.info(f"Heston model calibrated for {underlying}")
            
            return calibration_result
            
        except Exception as e:
            logger.error(f"Error calibrating Heston model for {underlying}: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _perform_heston_calibration(self, market_data: Dict[str, Any], 
                                         underlying: str) -> Dict[str, Any]:
        """Perform actual Heston calibration"""
        try:
            # This is a simplified calibration
            # In production, this would use market option prices and optimization
            
            # Get current market conditions
            spot_price = market_data.get(underlying, {}).get('last', 100)
            
            # Use VIX or implied volatility as starting point
            implied_vol = market_data.get('VIX', {}).get('last', 20) / 100 if 'VIX' in market_data else 0.2
            
            # Simple calibration based on market conditions
            # These would normally be optimized against market prices
            parameters = {
                'theta': max(0.01, min(0.1, implied_vol * 0.8)),  # Long-term variance
                'kappa': 2.0,  # Mean reversion speed
                'xi': 0.3,     # Volatility of volatility
                'rho': -0.7,   # Correlation
                'v0': max(0.01, min(0.1, implied_vol))  # Initial variance
            }
            
            # Calculate quality score based on market conditions
            quality = 0.8 if implied_vol > 0 else 0.5
            
            return {
                'success': True,
                'parameters': parameters,
                'quality': quality,
                'method': 'simplified',
                'market_conditions': {
                    'spot_price': spot_price,
                    'implied_vol': implied_vol
                }
            }
            
        except Exception as e:
            logger.error(f"Error in Heston calibration: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _get_cached_pricing(self, contract: OptionContract, 
                                 market_data: Dict[str, Any]) -> Optional[PricingResult]:
        """Get cached pricing result if available and fresh"""
        try:
            cache_key = f"{contract.symbol}_{contract.strike}_{contract.expiry_date.strftime('%Y%m%d')}"
            
            if cache_key in self.pricing_cache and cache_key in self.cache_timestamps:
                cache_age = (datetime.now() - self.cache_timestamps[cache_key]).total_seconds()
                
                if cache_age <= self.cache_ttl:
                    cached_result = self.pricing_cache[cache_key]
                    logger.debug(f"Cache hit for {cache_key}")
                    return cached_result
            
            return None
            
        except Exception as e:
            logger.error(f"Error checking pricing cache: {e}")
            return None
    
    async def _cache_pricing_result(self, result: PricingResult, market_data: Dict[str, Any]):
        """Cache pricing result"""
        try:
            cache_key = f"{result.contract.symbol}_{result.contract.strike}_{result.contract.expiry_date.strftime('%Y%m%d')}"
            
            self.pricing_cache[cache_key] = result
            self.cache_timestamps[cache_key] = datetime.now()
            
        except Exception as e:
            logger.error(f"Error caching pricing result: {e}")
    
    def _calculate_confidence_score(self, result: PricingResult, market_data: Dict[str, Any]) -> float:
        """Calculate confidence score for pricing result"""
        try:
            confidence = 1.0
            
            # Reduce confidence for far OTM options
            if result.moneyness:
                if result.moneyness < 0.8 or result.moneyness > 1.2:
                    confidence -= 0.1
                if result.moneyness < 0.5 or result.moneyness > 2.0:
                    confidence -= 0.2
            
            # Reduce confidence for short-term options
            if result.time_to_expiry and result.time_to_expiry < 0.02:  # < 1 week
                confidence -= 0.15
            
            # Reduce confidence based on pricing error
            if result.pricing_error:
                if result.pricing_error > 0.1:  # > 10% error
                    confidence -= 0.2
                elif result.pricing_error > 0.05:  # > 5% error
                    confidence -= 0.1
            
            # Reduce confidence for old calibration
            if result.contract.underlying in self.last_calibration:
                calibration_age = (datetime.now() - self.last_calibration[result.contract.underlying]).seconds
                if calibration_age > self.calibration_frequency * 2:
                    confidence -= 0.1
            
            return max(0.0, min(1.0, confidence))
            
        except Exception as e:
            logger.error(f"Error calculating confidence score: {e}")
            return 0.5
    
    async def _process_pricing_queue(self):
        """Process queued pricing requests"""
        try:
            while not self._shutdown_event.is_set():
                await asyncio.sleep(0.1)  # Process any queued requests
        except asyncio.CancelledError:
            logger.debug("Pricing queue processor cancelled")
        except Exception as e:
            logger.error(f"Error in pricing queue processor: {e}")
    
    async def _calibration_loop(self):
        """Periodic calibration loop"""
        try:
            while not self._shutdown_event.is_set():
                try:
                    # Placeholder for periodic recalibration
                    # Would typically trigger based on market conditions or time
                    pass
                except Exception as e:
                    logger.error(f"Error in calibration loop: {e}")
                
                # Wait for next calibration cycle
                try:
                    await asyncio.wait_for(
                        self._shutdown_event.wait(),
                        timeout=self.calibration_frequency
                    )
                    break
                except asyncio.TimeoutError:
                    continue
                    
        except asyncio.CancelledError:
            logger.debug("Calibration loop cancelled")
        except Exception as e:
            logger.error(f"Error in calibration loop: {e}")
    
    async def _cache_cleanup_loop(self):
        """Clean up expired cache entries"""
        try:
            while not self._shutdown_event.is_set():
                try:
                    current_time = datetime.now()
                    expired_keys = []
                    
                    for key, timestamp in self.cache_timestamps.items():
                        if (current_time - timestamp).total_seconds() > self.cache_ttl:
                            expired_keys.append(key)
                    
                    for key in expired_keys:
                        self.pricing_cache.pop(key, None)
                        self.cache_timestamps.pop(key, None)
                    
                    if expired_keys:
                        logger.debug(f"Cleaned up {len(expired_keys)} expired pricing cache entries")
                    
                except Exception as e:
                    logger.error(f"Error in pricing cache cleanup: {e}")
                
                # Wait for next cleanup cycle
                try:
                    await asyncio.wait_for(
                        self._shutdown_event.wait(),
                        timeout=300  # Clean every 5 minutes
                    )
                    break
                except asyncio.TimeoutError:
                    continue
                    
        except asyncio.CancelledError:
            logger.debug("Cache cleanup loop cancelled")
        except Exception as e:
            logger.error(f"Error in cache cleanup loop: {e}")
    
    async def _update_pricing_stats(self, response: PricingResponse, model: PricingModel):
        """Update pricing statistics"""
        try:
            self.pricing_stats['total_requests'] += 1
            
            if response.cache_hit:
                self.pricing_stats['cache_hits'] += 1
            
            self.pricing_stats['model_usage'][model.value] += 1
            
            # Update average processing time
            total_time = (self.pricing_stats['avg_pricing_time_ms'] * 
                         (self.pricing_stats['total_requests'] - 1) + 
                         response.processing_time_ms)
            self.pricing_stats['avg_pricing_time_ms'] = total_time / self.pricing_stats['total_requests']
            
        except Exception as e:
            logger.error(f"Error updating pricing stats: {e}")
    
    async def _load_calibration_cache(self):
        """Load cached calibration parameters"""
        # Placeholder for loading persisted calibration data
        pass
    
    async def _save_calibration_cache(self):
        """Save calibration parameters to cache"""
        # Placeholder for persisting calibration data
        pass
    
    def get_service_metrics(self) -> Dict[str, Any]:
        """Get detailed service metrics"""
        return {
            'pricing_stats': self.pricing_stats.copy(),
            'calibration_stats': {
                'auto_calibrate': self.auto_calibrate,
                'underlyings_calibrated': len(self.model_parameters_cache),
                'avg_calibration_quality': sum(self.calibration_quality.values()) / max(len(self.calibration_quality), 1),
                'recent_calibrations': len([c for c in self.calibration_history if (datetime.now() - c['timestamp']).seconds < 3600])
            },
            'cache_stats': {
                'enabled': self.cache_enabled,
                'entries': len(self.pricing_cache),
                'hit_rate': self.pricing_stats['cache_hits'] / max(self.pricing_stats['total_requests'], 1),
                'ttl_seconds': self.cache_ttl
            },
            'model_stats': {
                'default_model': self.default_model.value,
                'available_models': [model.value for model in PricingModel],
                'usage_distribution': self.pricing_stats['model_usage']
            }
        }