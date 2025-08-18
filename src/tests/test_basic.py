"""Basic tests to ensure system works"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_imports():
    """Test that all modules can be imported"""
    from src.strategy import HestonStrategy
    from src.data import DataFeedManager
    from src.monitoring import Dashboard, MetricsServer
    from src.risk import RiskManager
    from src.execution import OrderManager, ExecutionEngine
    from src.utils import DataValidator
    
    assert HestonStrategy is not None
    assert DataFeedManager is not None
    assert Dashboard is not None
    assert RiskManager is not None
    assert OrderManager is not None
    
def test_config_loading():
    """Test configuration loading"""
    import yaml
    from pathlib import Path
    
    config_path = Path("config/config.yaml")
    assert config_path.exists()
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    assert 'strategy' in config
    assert 'risk' in config
    assert 'execution' in config

def test_mock_data_feed():
    """Test mock data feed"""
    from src.data import DataFeedManager
    
    config = {'data': {'use_mock': True}}
    feed = DataFeedManager(config)
    
    assert feed.connect()
    snapshot = feed.get_snapshot()
    
    assert snapshot is not None
    assert 'SPX' in snapshot
    assert 'options' in snapshot
    
def test_risk_manager():
    """Test risk manager"""
    from src.risk import RiskManager
    
    config = {
        'risk': {
            'max_delta_exposure': 0.05,
            'max_vega_exposure': 2500
        }
    }
    
    rm = RiskManager(config)
    
    # Test trade risk check
    trade = {'notional': 10000}
    assert rm.check_trade_risk(trade) == True
    
    # Test with excessive size
    trade = {'notional': 50000}
    assert rm.check_trade_risk(trade) == False

if __name__ == "__main__":
    test_imports()
    print("✓ All imports successful")
    
    test_config_loading()
    print("✓ Config loading successful")
    
    test_mock_data_feed()
    print("✓ Mock data feed successful")
    
    test_risk_manager()
    print("✓ Risk manager successful")
    
    print("\nAll tests passed!")
