"""
Centralized Configuration Management System
Handles loading, validation, and management of all system configurations
"""
import os
import yaml
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)

class ConfigFormat(Enum):
    YAML = "yaml"
    JSON = "json"

@dataclass
class DataProviderConfig:
    """Data provider configuration"""
    type: str = "mock"
    host: str = "127.0.0.1"
    port: int = 7497
    client_id: int = 1
    update_interval: float = 1.0
    volatility_factor: float = 1.0
    prefer_ib: bool = True
    fallback_to_mock: bool = True
    ib_timeout: int = 10
    ib_retry_interval: int = 300
    max_ib_attempts: int = 3

@dataclass
class StrategyConfig:
    """Core strategy configuration"""
    # Heston model parameters
    initial_params: Dict[str, float] = field(default_factory=lambda: {
        'theta': 0.04,
        'kappa': 2.0,
        'xi': 0.3,
        'rho': -0.7,
        'v0': 0.04
    })
    
    # Calibration settings
    calibration_frequency: int = 300  # seconds
    calibration_method: str = "least_squares"
    max_calibration_time: int = 30  # seconds
    
    # Trading parameters
    min_signal_confidence: float = 70.0
    position_size_method: str = "kelly"
    max_position_size: int = 10
    max_daily_risk: float = 5000.0

@dataclass
class MispricingDetectionConfig:
    """Mispricing detection configuration"""
    min_mispricing_pct: float = 5.0
    strong_mispricing_pct: float = 15.0
    min_signal_confidence: float = 70.0
    max_signals_per_cycle: int = 20
    min_option_volume: int = 10
    min_time_to_expiry: int = 7  # days

@dataclass
class RiskManagementConfig:
    """Risk management configuration"""
    max_portfolio_delta: float = 50000.0
    max_position_size: int = 100
    max_daily_loss: float = 10000.0
    stop_loss_pct: float = 0.5
    position_size_method: str = "kelly"
    risk_free_rate: float = 0.05

@dataclass
class DeltaHedgingConfig:
    """Delta hedging configuration"""
    delta_band: float = 0.05
    hedge_frequency: int = 60  # seconds
    hedge_instrument: str = "SPY"
    account_equity: float = 1000000.0
    hedge_ratio: float = 1.0

@dataclass
class DashboardConfig:
    """Dashboard configuration"""
    port: int = 8050
    host: str = "127.0.0.1"
    debug: bool = False
    auto_reload: bool = True
    update_interval: int = 2  # seconds

@dataclass
class LoggingConfig:
    """Logging configuration"""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_handler: bool = True
    log_directory: str = "logs"
    max_file_size: int = 10485760  # 10MB
    backup_count: int = 5

@dataclass
class SystemConfig:
    """Complete system configuration"""
    data_provider: DataProviderConfig = field(default_factory=DataProviderConfig)
    strategy: StrategyConfig = field(default_factory=StrategyConfig)
    mispricing_detection: MispricingDetectionConfig = field(default_factory=MispricingDetectionConfig)
    risk_management: RiskManagementConfig = field(default_factory=RiskManagementConfig)
    delta_hedging: DeltaHedgingConfig = field(default_factory=DeltaHedgingConfig)
    dashboard: DashboardConfig = field(default_factory=DashboardConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)

class ConfigManager:
    """Centralized configuration manager"""
    
    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file
        self.config: SystemConfig = SystemConfig()
        self._config_dir = Path(__file__).parent
        self._project_root = self._config_dir.parent.parent
        
        # Load configuration if file provided
        if config_file:
            self.load_config(config_file)
    
    def load_config(self, config_file: str, format_type: Optional[ConfigFormat] = None) -> SystemConfig:
        """
        Load configuration from file
        
        Args:
            config_file: Path to configuration file
            format_type: Configuration format (auto-detected if None)
            
        Returns:
            Loaded SystemConfig
        """
        try:
            config_path = Path(config_file)
            
            # Make path absolute if relative
            if not config_path.is_absolute():
                config_path = self._project_root / config_path
            
            if not config_path.exists():
                logger.warning(f"Config file not found: {config_path}")
                logger.info("Using default configuration")
                return self.config
            
            # Auto-detect format if not specified
            if format_type is None:
                if config_path.suffix.lower() in ['.yaml', '.yml']:
                    format_type = ConfigFormat.YAML
                elif config_path.suffix.lower() == '.json':
                    format_type = ConfigFormat.JSON
                else:
                    raise ValueError(f"Unsupported config file format: {config_path.suffix}")
            
            # Load configuration data
            with open(config_path, 'r') as f:
                if format_type == ConfigFormat.YAML:
                    config_data = yaml.safe_load(f)
                else:  # JSON
                    config_data = json.load(f)
            
            # Update configuration
            self._update_config_from_dict(config_data)
            
            logger.info(f"Configuration loaded from {config_path}")
            return self.config
            
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            logger.info("Using default configuration")
            return self.config
    
    def save_config(self, config_file: str, format_type: ConfigFormat = ConfigFormat.YAML):
        """
        Save current configuration to file
        
        Args:
            config_file: Path to save configuration
            format_type: Format to save in
        """
        try:
            config_path = Path(config_file)
            
            # Make path absolute if relative
            if not config_path.is_absolute():
                config_path = self._project_root / config_path
            
            # Create directory if it doesn't exist
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Convert config to dictionary
            config_dict = self._config_to_dict()
            
            # Save configuration
            with open(config_path, 'w') as f:
                if format_type == ConfigFormat.YAML:
                    yaml.dump(config_dict, f, default_flow_style=False, indent=2)
                else:  # JSON
                    json.dump(config_dict, f, indent=2)
            
            logger.info(f"Configuration saved to {config_path}")
            
        except Exception as e:
            logger.error(f"Error saving configuration: {e}")
            raise
    
    def get_config(self) -> SystemConfig:
        """Get current system configuration"""
        return self.config
    
    def get_data_provider_config(self) -> Dict[str, Any]:
        """Get data provider configuration as dictionary"""
        return self._dataclass_to_dict(self.config.data_provider)
    
    def get_strategy_config(self) -> Dict[str, Any]:
        """Get strategy configuration as dictionary"""
        return {
            'strategy': self._dataclass_to_dict(self.config.strategy),
            'mispricing_detection': self._dataclass_to_dict(self.config.mispricing_detection),
            'risk_management': self._dataclass_to_dict(self.config.risk_management),
            'delta_hedging': self._dataclass_to_dict(self.config.delta_hedging)
        }
    
    def get_dashboard_config(self) -> Dict[str, Any]:
        """Get dashboard configuration as dictionary"""
        return self._dataclass_to_dict(self.config.dashboard)
    
    def update_config(self, section: str, updates: Dict[str, Any]):
        """
        Update a specific configuration section
        
        Args:
            section: Configuration section name
            updates: Dictionary of updates to apply
        """
        try:
            if section == 'data_provider':
                self._update_dataclass(self.config.data_provider, updates)
            elif section == 'strategy':
                self._update_dataclass(self.config.strategy, updates)
            elif section == 'mispricing_detection':
                self._update_dataclass(self.config.mispricing_detection, updates)
            elif section == 'risk_management':
                self._update_dataclass(self.config.risk_management, updates)
            elif section == 'delta_hedging':
                self._update_dataclass(self.config.delta_hedging, updates)
            elif section == 'dashboard':
                self._update_dataclass(self.config.dashboard, updates)
            elif section == 'logging':
                self._update_dataclass(self.config.logging, updates)
            else:
                raise ValueError(f"Unknown configuration section: {section}")
            
            logger.info(f"Updated {section} configuration")
            
        except Exception as e:
            logger.error(f"Error updating configuration section {section}: {e}")
            raise
    
    def validate_config(self) -> List[str]:
        """
        Validate current configuration
        
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        try:
            # Validate data provider config
            dp_config = self.config.data_provider
            if dp_config.type not in ['mock', 'interactive_brokers', 'hybrid']:
                errors.append(f"Invalid data provider type: {dp_config.type}")
            
            if dp_config.port < 1 or dp_config.port > 65535:
                errors.append(f"Invalid port number: {dp_config.port}")
            
            # Validate strategy config
            strategy_config = self.config.strategy
            for param, value in strategy_config.initial_params.items():
                if not isinstance(value, (int, float)):
                    errors.append(f"Invalid Heston parameter {param}: must be numeric")
            
            # Validate mispricing detection config
            mp_config = self.config.mispricing_detection
            if mp_config.min_mispricing_pct < 0 or mp_config.min_mispricing_pct > 100:
                errors.append("min_mispricing_pct must be between 0 and 100")
            
            # Validate risk management config
            rm_config = self.config.risk_management
            if rm_config.max_daily_loss < 0:
                errors.append("max_daily_loss must be positive")
            
            # Validate dashboard config
            dashboard_config = self.config.dashboard
            if dashboard_config.port < 1 or dashboard_config.port > 65535:
                errors.append(f"Invalid dashboard port: {dashboard_config.port}")
            
        except Exception as e:
            errors.append(f"Configuration validation error: {e}")
        
        return errors
    
    def create_example_configs(self):
        """Create example configuration files"""
        examples_dir = self._project_root / "config" / "examples"
        examples_dir.mkdir(parents=True, exist_ok=True)
        
        # Demo configuration
        demo_config = SystemConfig()
        demo_config.data_provider.type = "mock"
        demo_config.data_provider.volatility_factor = 1.5
        demo_config.dashboard.debug = True
        
        self.config = demo_config
        self.save_config(examples_dir / "demo_config.yaml")
        
        # Live trading configuration
        live_config = SystemConfig()
        live_config.data_provider.type = "hybrid"
        live_config.data_provider.prefer_ib = True
        live_config.strategy.max_daily_risk = 2000.0
        live_config.dashboard.debug = False
        
        self.config = live_config
        self.save_config(examples_dir / "live_config.yaml")
        
        # Reset to default
        self.config = SystemConfig()
        
        logger.info(f"Example configurations created in {examples_dir}")
    
    # Helper methods
    
    def _update_config_from_dict(self, config_data: Dict[str, Any]):
        """Update configuration from dictionary"""
        for section, values in config_data.items():
            if hasattr(self.config, section):
                section_config = getattr(self.config, section)
                self._update_dataclass(section_config, values)
    
    def _update_dataclass(self, dataclass_instance, updates: Dict[str, Any]):
        """Update dataclass instance with dictionary values"""
        for key, value in updates.items():
            if hasattr(dataclass_instance, key):
                setattr(dataclass_instance, key, value)
    
    def _dataclass_to_dict(self, dataclass_instance) -> Dict[str, Any]:
        """Convert dataclass to dictionary"""
        result = {}
        for field_name in dataclass_instance.__dataclass_fields__:
            value = getattr(dataclass_instance, field_name)
            if isinstance(value, dict):
                result[field_name] = value.copy()
            else:
                result[field_name] = value
        return result
    
    def _config_to_dict(self) -> Dict[str, Any]:
        """Convert entire configuration to dictionary"""
        return {
            'data_provider': self._dataclass_to_dict(self.config.data_provider),
            'strategy': self._dataclass_to_dict(self.config.strategy),
            'mispricing_detection': self._dataclass_to_dict(self.config.mispricing_detection),
            'risk_management': self._dataclass_to_dict(self.config.risk_management),
            'delta_hedging': self._dataclass_to_dict(self.config.delta_hedging),
            'dashboard': self._dataclass_to_dict(self.config.dashboard),
            'logging': self._dataclass_to_dict(self.config.logging)
        }

# Global configuration manager instance
_global_config_manager: Optional[ConfigManager] = None

def get_config_manager() -> ConfigManager:
    """Get global configuration manager instance"""
    global _global_config_manager
    if _global_config_manager is None:
        _global_config_manager = ConfigManager()
    return _global_config_manager

def load_config(config_file: str) -> SystemConfig:
    """Load configuration from file using global manager"""
    manager = get_config_manager()
    return manager.load_config(config_file)

def get_config() -> SystemConfig:
    """Get current system configuration"""
    manager = get_config_manager()
    return manager.get_config()