"""
Data Provider Factory
Creates and manages data provider instances based on configuration
"""
import logging
from typing import Dict, Any, Optional, Type
from enum import Enum

from .base_provider import DataProvider
from .mock_provider import MockDataProvider
from .enhanced_ib_provider import IBDataProvider
from .hybrid_provider import HybridDataProvider

logger = logging.getLogger(__name__)

class ProviderType(Enum):
    MOCK = "mock"
    INTERACTIVE_BROKERS = "interactive_brokers"
    HYBRID = "hybrid"

class DataProviderFactory:
    """Factory for creating data provider instances"""
    
    _providers: Dict[str, Type[DataProvider]] = {
        ProviderType.MOCK.value: MockDataProvider,
        ProviderType.INTERACTIVE_BROKERS.value: IBDataProvider,
        ProviderType.HYBRID.value: HybridDataProvider
    }
    
    @classmethod
    def create_provider(cls, provider_type: str, config: Dict[str, Any]) -> DataProvider:
        """
        Create a data provider instance
        
        Args:
            provider_type: Type of provider to create ('mock', 'interactive_brokers', 'hybrid')
            config: Configuration dictionary for the provider
            
        Returns:
            DataProvider instance
            
        Raises:
            ValueError: If provider_type is not supported
        """
        if provider_type not in cls._providers:
            available_types = list(cls._providers.keys())
            raise ValueError(f"Unsupported provider type: {provider_type}. "
                           f"Available types: {available_types}")
        
        provider_class = cls._providers[provider_type]
        
        try:
            logger.info(f"Creating {provider_type} data provider")
            provider = provider_class(config)
            logger.info(f"Successfully created {provider_type} provider")
            return provider
            
        except Exception as e:
            logger.error(f"Failed to create {provider_type} provider: {e}")
            raise
    
    @classmethod
    def create_from_config(cls, config: Dict[str, Any]) -> DataProvider:
        """
        Create a data provider from configuration
        
        Args:
            config: Configuration dictionary with 'type' field and provider-specific config
            
        Returns:
            DataProvider instance
        """
        provider_type = config.get('type', 'mock')
        provider_config = config.get('config', {})
        
        return cls.create_provider(provider_type, provider_config)
    
    @classmethod
    def get_available_providers(cls) -> list[str]:
        """Get list of available provider types"""
        return list(cls._providers.keys())
    
    @classmethod
    def register_provider(cls, provider_type: str, provider_class: Type[DataProvider]):
        """
        Register a new provider type
        
        Args:
            provider_type: String identifier for the provider
            provider_class: Class that implements DataProvider interface
        """
        if not issubclass(provider_class, DataProvider):
            raise ValueError(f"Provider class must inherit from DataProvider")
        
        cls._providers[provider_type] = provider_class
        logger.info(f"Registered new provider type: {provider_type}")

def create_recommended_provider(mode: str = "demo") -> DataProvider:
    """
    Create a recommended provider based on usage mode
    
    Args:
        mode: Usage mode ('demo', 'live', 'hybrid')
        
    Returns:
        DataProvider instance with recommended configuration
    """
    if mode == "demo":
        config = {
            'update_interval': 1.0,
            'volatility_factor': 1.5,  # More dynamic for demo
        }
        return DataProviderFactory.create_provider('mock', config)
    
    elif mode == "live":
        config = {
            'host': '127.0.0.1',
            'port': 7497,
            'client_id': 1
        }
        return DataProviderFactory.create_provider('interactive_brokers', config)
    
    elif mode == "hybrid":
        config = {
            'prefer_ib': True,
            'fallback_to_mock': True,
            'ib_timeout': 10,
            'ib_config': {
                'host': '127.0.0.1',
                'port': 7497,
                'client_id': 1
            },
            'mock_config': {
                'update_interval': 2.0,
                'volatility_factor': 1.0
            }
        }
        return DataProviderFactory.create_provider('hybrid', config)
    
    else:
        raise ValueError(f"Unknown mode: {mode}. Use 'demo', 'live', or 'hybrid'")

# Example configurations for different use cases
EXAMPLE_CONFIGS = {
    'demo_basic': {
        'type': 'mock',
        'config': {
            'update_interval': 1.0,
            'volatility_factor': 1.0
        }
    },
    
    'demo_volatile': {
        'type': 'mock',
        'config': {
            'update_interval': 0.5,
            'volatility_factor': 2.0
        }
    },
    
    'ib_paper': {
        'type': 'interactive_brokers',
        'config': {
            'host': '127.0.0.1',
            'port': 7497,  # Paper trading port
            'client_id': 1
        }
    },
    
    'ib_live': {
        'type': 'interactive_brokers',
        'config': {
            'host': '127.0.0.1',
            'port': 7496,  # Live trading port
            'client_id': 1
        }
    },
    
    'hybrid_robust': {
        'type': 'hybrid',
        'config': {
            'prefer_ib': True,
            'fallback_to_mock': True,
            'ib_timeout': 15,
            'ib_retry_interval': 300,
            'max_ib_attempts': 5,
            'ib_config': {
                'host': '127.0.0.1',
                'port': 7497,
                'client_id': 1
            },
            'mock_config': {
                'update_interval': 2.0,
                'volatility_factor': 1.2
            }
        }
    }
}