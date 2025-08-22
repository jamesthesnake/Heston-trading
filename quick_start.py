#!/usr/bin/env python3
"""
Heston Trading System Quick Start
Demonstrates key system functionality for new users
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def demo_configuration():
    """Demonstrate configuration management"""
    print("🔧 Configuration Management Demo")
    print("-" * 40)
    
    try:
        from src.config.config_manager import get_config_manager
        
        # Load demo configuration
        config_manager = get_config_manager()
        config_manager.load_config("config/demo_config.yaml")
        
        # Get strategy configuration
        strategy_config = config_manager.get_strategy_config()
        
        print("✅ Configuration loaded successfully")
        print(f"✅ Risk management enabled: {strategy_config.get('risk_management', {}).get('enabled', False)}")
        print(f"✅ Market data provider: {strategy_config.get('market_data', {}).get('primary_provider', {}).get('type', 'unknown')}")
        
        return strategy_config
        
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        return None

async def demo_market_data():
    """Demonstrate market data service"""
    print("\n📊 Market Data Service Demo")
    print("-" * 40)
    
    try:
        from src.services import MarketDataService, ServiceConfig
        from src.services.market_data_service import MarketDataRequest
        from src.config.config_manager import get_config_manager
        
        # Load configuration
        config_manager = get_config_manager()
        config_manager.load_config("config/demo_config.yaml")
        strategy_config = config_manager.get_strategy_config()
        
        # Create service
        service_config = ServiceConfig(name="market_data_demo", enabled=True, heartbeat_interval=10)
        market_service = MarketDataService(service_config, strategy_config)
        
        # Start service
        await market_service.start()
        print("✅ Market Data Service started")
        
        # Request market data
        request = MarketDataRequest(
            symbols=['SPY', 'QQQ', 'IWM'],
            data_types=['quotes', 'greeks'],
            use_cache=True
        )
        
        response = await market_service.get_market_data(request)
        
        print(f"✅ Retrieved data for {len(response.symbols)} symbols")
        print(f"✅ Source: {response.source_provider}")
        print(f"✅ Latency: {response.latency_ms:.1f}ms")
        print(f"✅ Cache hit: {response.cache_hit}")
        
        # Get service metrics
        metrics = market_service.get_service_metrics()
        print(f"✅ Total requests processed: {metrics['request_stats']['total_requests']}")
        
        # Stop service
        await market_service.stop()
        print("✅ Market Data Service stopped")
        
        return True
        
    except Exception as e:
        print(f"❌ Market data error: {e}")
        return False

async def demo_options_pricing():
    """Demonstrate options pricing service"""
    print("\n💰 Options Pricing Service Demo")
    print("-" * 40)
    
    try:
        from src.services import OptionsPricingService, ServiceConfig
        from src.services.options_pricing_service import OptionContract, PricingRequest, PricingModel
        from src.config.config_manager import get_config_manager
        from datetime import datetime, timedelta
        
        # Load configuration
        config_manager = get_config_manager()
        config_manager.load_config("config/demo_config.yaml")
        strategy_config = config_manager.get_strategy_config()
        
        # Create service
        service_config = ServiceConfig(name="pricing_demo", enabled=True)
        pricing_service = OptionsPricingService(service_config, strategy_config)
        
        # Start service
        await pricing_service.start()
        print("✅ Options Pricing Service started")
        
        # Create sample option contract
        expiry_date = datetime.now() + timedelta(days=30)  # 30 days from now
        contract = OptionContract(
            symbol=f'SPY{expiry_date.strftime("%y%m%d")}C00500000',
            underlying='SPY',
            option_type='C',
            strike=500.0,
            expiry_date=expiry_date,
            quantity=1
        )
        
        # Market data
        market_data = {
            'SPY': {
                'last': 505.0,
                'bid': 504.8,
                'ask': 505.2,
                'volume': 1000000,
                'implied_volatility': 0.18
            },
            'VIX': {'last': 16.5}
        }
        
        # Create pricing request
        request = PricingRequest(
            contracts=[contract],
            market_data=market_data,
            model=PricingModel.HESTON,
            include_greeks=True,
            calibrate_model=True
        )
        
        # Price the option
        response = await pricing_service.price_options(request)
        
        if response.results:
            result = response.results[0]
            print(f"✅ Contract: {contract.option_type} {contract.strike} strike")
            print(f"✅ Theoretical price: ${result.theoretical_price:.2f}")
            if result.delta is not None:
                print(f"✅ Delta: {result.delta:.3f}")
            if result.gamma is not None:
                print(f"✅ Gamma: {result.gamma:.3f}")
            print(f"✅ Model used: {result.model_used.value}")
            print(f"✅ Confidence score: {result.confidence_score:.2f}")
        else:
            print("⚠️ No pricing results returned")
        
        # Get service metrics
        metrics = pricing_service.get_service_metrics()
        print(f"✅ Pricing requests processed: {metrics['pricing_stats']['total_requests']}")
        
        # Stop service
        await pricing_service.stop()
        print("✅ Options Pricing Service stopped")
        
        return True
        
    except Exception as e:
        print(f"❌ Options pricing error: {e}")
        return False

async def demo_risk_management():
    """Demonstrate risk management system"""
    print("\n🛡️ Risk Management System Demo")
    print("-" * 40)
    
    try:
        from src.risk.risk_engine import RiskEngine
        from src.risk.risk_types import RiskLevel, RiskAction
        from src.config.config_manager import get_config_manager
        
        # Load configuration
        config_manager = get_config_manager()
        config_manager.load_config("config/demo_config.yaml")
        strategy_config = config_manager.get_strategy_config()
        
        # Create risk engine
        risk_engine = RiskEngine(strategy_config)
        print("✅ Risk Engine initialized")
        
        # Sample portfolio positions
        positions = [
            {
                'position_id': 'POS001',
                'symbol': 'SPY',
                'underlying': 'SPY',
                'option_type': 'C',
                'strike': 500,
                'quantity': 10,
                'market_value': 25000,
                'unrealized_pnl': 1500,
                'delta': 0.6,
                'gamma': 0.02,
                'theta': -15,
                'vega': 45,
                'days_to_expiry': 30
            },
            {
                'position_id': 'POS002',
                'symbol': 'QQQ',
                'underlying': 'QQQ',
                'option_type': 'P',
                'strike': 380,
                'quantity': -5,
                'market_value': -12000,
                'unrealized_pnl': 800,
                'delta': -0.3,
                'gamma': 0.01,
                'theta': -8,
                'vega': 25,
                'days_to_expiry': 15
            }
        ]
        
        # Market data
        market_data = {
            'SPY': {'last': 505, 'volume': 5000000},
            'QQQ': {'last': 382, 'volume': 3000000},
            'VIX': {'last': 16.5}
        }
        
        # Portfolio metrics
        portfolio_metrics = {
            'total_value': 75000,
            'daily_pnl': 2300,
            'account_equity': 1000000,
            'daily_var_95': 8000
        }
        
        # Assess risk
        assessment = await risk_engine.assess_risk(positions, market_data, portfolio_metrics)
        
        print(f"✅ Risk assessment completed")
        print(f"✅ Overall risk level: {assessment.overall_level.value.upper()}")
        print(f"✅ Recommended action: {assessment.recommended_action.value}")
        print(f"✅ Number of alerts: {len(assessment.alerts)}")
        print(f"✅ Confidence score: {assessment.confidence_score:.2f}")
        print(f"✅ Positions analyzed: {assessment.position_count}")
        print(f"✅ Portfolio value: ${assessment.portfolio_value:,.2f}")
        
        # Show sample alerts
        if assessment.alerts:
            print("\n📋 Sample Risk Alerts:")
            for i, alert in enumerate(assessment.alerts[:3]):  # Show first 3 alerts
                print(f"   {i+1}. {alert.level.value.upper()}: {alert.message}")
        
        # Get risk summary
        summary = risk_engine.get_risk_summary()
        print(f"✅ Risk summary available with {summary['assessment_stats']['total_assessments']} assessments")
        
        return True
        
    except Exception as e:
        print(f"❌ Risk management error: {e}")
        return False

async def demo_notifications():
    """Demonstrate notification system"""
    print("\n📢 Notification System Demo")
    print("-" * 40)
    
    try:
        from src.services import NotificationService, ServiceConfig
        from src.services.notification_service import Notification, NotificationLevel, NotificationChannel
        from src.config.config_manager import get_config_manager
        
        # Load configuration
        config_manager = get_config_manager()
        config_manager.load_config("config/demo_config.yaml")
        strategy_config = config_manager.get_strategy_config()
        
        # Create service
        service_config = ServiceConfig(name="notification_demo", enabled=True)
        notification_service = NotificationService(service_config, strategy_config)
        
        # Start service
        await notification_service.start()
        print("✅ Notification Service started")
        
        # Send sample notifications
        notifications = [
            ("System Started", "Demo system has been started successfully", NotificationLevel.INFO),
            ("Risk Alert", "Portfolio risk level elevated to WARNING", NotificationLevel.WARNING),
            ("Trading Update", "New position opened: SPY Call 500", NotificationLevel.INFO)
        ]
        
        notification_ids = []
        for title, message, level in notifications:
            notification_id = await notification_service.send_alert(
                level=level,
                title=title,
                message=message,
                channels=[NotificationChannel.CONSOLE],
                source="demo"
            )
            notification_ids.append(notification_id)
        
        print(f"✅ Sent {len(notification_ids)} notifications")
        
        # Wait for processing
        await asyncio.sleep(0.2)
        
        # Get metrics
        metrics = notification_service.get_service_metrics()
        print(f"✅ Notifications processed: {metrics['notification_stats']['total_sent']}")
        
        # Get recent notifications
        recent = notification_service.get_recent_notifications(1)  # Last 1 hour
        print(f"✅ Recent notifications: {len(recent)}")
        
        # Stop service
        await notification_service.stop()
        print("✅ Notification Service stopped")
        
        return True
        
    except Exception as e:
        print(f"❌ Notification error: {e}")
        return False

async def main():
    """Main demo function"""
    print("🚀 HESTON TRADING SYSTEM - QUICK START DEMO")
    print("=" * 60)
    print("This demo showcases the key components of the system")
    print()
    
    demos = [
        ("Configuration Management", demo_configuration),
        ("Market Data Service", demo_market_data),
        ("Options Pricing Service", demo_options_pricing),
        ("Risk Management System", demo_risk_management),
        ("Notification System", demo_notifications)
    ]
    
    results = []
    
    for name, demo_func in demos:
        try:
            if asyncio.iscoroutinefunction(demo_func):
                result = await demo_func()
            else:
                result = demo_func()
            results.append((name, result))
        except Exception as e:
            print(f"❌ {name} failed: {e}")
            results.append((name, False))
    
    # Summary
    print("\n🎉 QUICK START DEMO COMPLETE!")
    print("=" * 60)
    
    successful = sum(1 for _, success in results if success)
    total = len(results)
    
    print(f"✅ Results: {successful}/{total} components working")
    
    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {status}: {name}")
    
    if successful == total:
        print("\n🎯 All systems operational!")
        print("🚀 Ready for trading operations")
        print("\n📚 Next Steps:")
        print("  • Review README.md for detailed documentation")
        print("  • Run 'python test_enhanced_risk.py' for comprehensive risk testing")
        print("  • Run 'python test_service_layer.py' for full service testing")
        print("  • Customize configuration files for your trading needs")
    else:
        print(f"\n⚠️ {total - successful} components need attention")
        print("Please check error messages above and ensure all dependencies are installed")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️ Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()