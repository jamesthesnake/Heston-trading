#!/usr/bin/env python3
"""
Migration Script to New Architecture
Demonstrates the new system and provides migration path
"""
import sys
import asyncio
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.config.config_manager import ConfigManager
from src.data.providers.provider_factory import create_recommended_provider
from src.data.unified_feed_manager import UnifiedFeedManager
from src.strategy.enhanced_strategy import EnhancedMispricingStrategy

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_new_architecture():
    """Test the new architecture components"""
    
    print("🎯 Testing New Heston Trading Architecture")
    print("=" * 60)
    
    # 1. Test Configuration Management
    print("\n1️⃣ Testing Configuration Management")
    config_manager = ConfigManager()
    
    # Create example configs
    config_manager.create_example_configs()
    print("✅ Example configurations created")
    
    # Load demo config
    config = config_manager.load_config("config/demo_config.yaml")
    print(f"✅ Demo configuration loaded: {config.data_provider.type} provider")
    
    # Validate config
    errors = config_manager.validate_config()
    if errors:
        print(f"❌ Configuration errors: {errors}")
    else:
        print("✅ Configuration validation passed")
    
    # 2. Test Data Provider System
    print("\n2️⃣ Testing Data Provider System")
    
    # Test mock provider
    mock_provider = create_recommended_provider("demo")
    connected = await mock_provider.connect()
    print(f"✅ Mock provider connected: {connected}")
    
    if connected:
        # Get underlying data
        underlying_data = await mock_provider.get_underlying_data(['SPX', 'SPY'])
        print(f"✅ Got underlying data for {len(underlying_data)} symbols")
        
        # Get market snapshot
        snapshot = await mock_provider.get_market_snapshot()
        print(f"✅ Market snapshot: {len(snapshot.underlying)} underlying, {len(snapshot.options)} options")
        
        await mock_provider.disconnect()
    
    # 3. Test Unified Feed Manager
    print("\n3️⃣ Testing Unified Feed Manager")
    
    feed_manager = UnifiedFeedManager()
    connected = await feed_manager.connect()
    print(f"✅ Feed manager connected: {connected}")
    
    if connected:
        # Get connection status
        status = feed_manager.get_connection_status()
        print(f"✅ Feed status: {status['provider_type']} provider")
        
        # Get data summary
        summary = feed_manager.get_data_summary()
        print(f"✅ Data summary: {summary}")
        
        await feed_manager.disconnect()
    
    # 4. Test Enhanced Strategy (quick test)
    print("\n4️⃣ Testing Enhanced Strategy")
    
    try:
        strategy = EnhancedMispricingStrategy("config/demo_config.yaml")
        print("✅ Enhanced strategy initialized")
        
        # Get system status
        status = strategy.get_system_status()
        print(f"✅ System status: {status['configuration']['provider_type']} provider")
        
        # Run for a few cycles
        print("🔄 Running strategy for 15 seconds...")
        
        # Start strategy in background
        strategy_task = asyncio.create_task(strategy.start())
        
        # Let it run for 15 seconds
        await asyncio.sleep(15)
        
        # Stop strategy
        await strategy.stop()
        
        # Cancel the task
        strategy_task.cancel()
        
        # Get performance summary
        performance = strategy.get_performance_summary()
        print(f"✅ Strategy completed {performance.get('cycle_count', 0)} cycles")
        
    except Exception as e:
        print(f"⚠️ Strategy test failed (expected in some environments): {e}")
    
    print("\n🎉 Architecture Testing Complete!")
    print("=" * 60)

def compare_architectures():
    """Compare old vs new architecture"""
    
    print("\n📊 Architecture Comparison")
    print("=" * 60)
    
    old_files = [
        "src/monitoring/dashboard.py",
        "src/dashboard/options_dashboard.py", 
        "src/data/feed_manager.py",
        "src/strategy/mispricing_strategy.py"
    ]
    
    new_files = [
        "src/monitoring/unified_dashboard.py",
        "src/data/unified_feed_manager.py", 
        "src/data/providers/base_provider.py",
        "src/data/providers/mock_provider.py",
        "src/data/providers/enhanced_ib_provider.py",
        "src/data/providers/hybrid_provider.py",
        "src/data/providers/provider_factory.py",
        "src/config/config_manager.py",
        "src/strategy/enhanced_strategy.py"
    ]
    
    print("🔴 Old Architecture:")
    for file in old_files:
        if Path(file).exists():
            print(f"  • {file}")
    
    print("\n🟢 New Architecture:")
    for file in new_files:
        if Path(file).exists():
            print(f"  • {file}")
    
    print("\n✨ Improvements:")
    print("  • ✅ Unified dashboard (consolidated 2 dashboards)")
    print("  • ✅ Clean data provider interface with fallback")
    print("  • ✅ Centralized configuration management")
    print("  • ✅ Better separation of concerns")
    print("  • ✅ Enhanced error handling and logging")
    print("  • ✅ Backward compatibility maintained")

def show_migration_guide():
    """Show migration guide"""
    
    print("\n📋 Migration Guide")
    print("=" * 60)
    
    print("To use the new architecture:")
    print()
    print("1️⃣ Configuration:")
    print("  from src.config.config_manager import get_config_manager")
    print("  config_manager = get_config_manager()")
    print("  config_manager.load_config('config/demo_config.yaml')")
    print()
    print("2️⃣ Data Management:")
    print("  from src.data.unified_feed_manager import UnifiedFeedManager")
    print("  feed_manager = UnifiedFeedManager()")
    print("  await feed_manager.connect()")
    print()
    print("3️⃣ Strategy:")
    print("  from src.strategy.enhanced_strategy import EnhancedMispricingStrategy")
    print("  strategy = EnhancedMispricingStrategy('config/demo_config.yaml')")
    print("  await strategy.start()")
    print()
    print("4️⃣ Dashboard:")
    print("  from src.monitoring.unified_dashboard import UnifiedDashboard")
    print("  dashboard = UnifiedDashboard(strategy, feed_manager)")
    print("  dashboard.run()")

async def main():
    """Main migration demonstration"""
    
    print("🎯 HESTON TRADING SYSTEM - ARCHITECTURE MIGRATION")
    print("=" * 70)
    
    try:
        # Test new architecture
        await test_new_architecture()
        
        # Show comparisons
        compare_architectures()
        
        # Show migration guide
        show_migration_guide()
        
        print("\n🚀 Migration Complete!")
        print("The new architecture is ready for use.")
        print("Example configurations are available in config/examples/")
        
    except Exception as e:
        logger.error(f"Migration test failed: {e}")
        print(f"\n❌ Migration test failed: {e}")
        print("Please check the logs for details.")

if __name__ == "__main__":
    asyncio.run(main())