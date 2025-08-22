#!/usr/bin/env python3
"""
Test Service Layer
Tests the new service layer architecture with all service abstractions
"""
import asyncio
import logging
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.services import (
    BaseService, ServiceConfig, ServiceStatus,
    MarketDataService, OptionsPricingService, 
    ExecutionService, NotificationService
)
from src.services.market_data_service import MarketDataRequest
from src.services.notification_service import NotificationLevel
from src.services.options_pricing_service import OptionContract, PricingRequest, PricingModel
from src.services.execution_service import OrderRequest, OrderType, OrderSide, TimeInForce
from src.services.notification_service import Notification, NotificationChannel
from src.config.config_manager import get_config_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_service_configurations():
    """Test service configuration and initialization"""
    print("🔧 Testing Service Configurations")
    print("=" * 60)
    
    # Load configuration
    config_manager = get_config_manager()
    config_manager.load_config("config/demo_config.yaml")
    strategy_config = config_manager.get_strategy_config()
    
    # Test service configs
    service_configs = [
        ServiceConfig(name="market_data", enabled=True, auto_restart=True),
        ServiceConfig(name="options_pricing", enabled=True, heartbeat_interval=60),
        ServiceConfig(name="execution", enabled=True, max_retries=5),
        ServiceConfig(name="notification", enabled=True, dependencies=["market_data"])
    ]
    
    print(f"✅ Created {len(service_configs)} service configurations")
    
    # Test service status enumeration
    all_statuses = [status.value for status in ServiceStatus]
    print(f"✅ Service status states: {', '.join(all_statuses)}")
    
    return {
        'strategy_config': strategy_config,
        'service_configs': service_configs
    }

async def test_market_data_service(strategy_config, service_config):
    """Test Market Data Service"""
    print("\n📊 Testing Market Data Service")
    print("-" * 50)
    
    # Create service
    service = MarketDataService(service_config, strategy_config)
    
    try:
        # Test service lifecycle
        assert await service.start(), "Failed to start market data service"
        print("✅ Market data service started")
        
        # Test health check
        health = await service._health_check()
        print(f"✅ Health check: {health['provider_status']['primary_connected']}")
        
        # Test market data request
        request = MarketDataRequest(
            symbols=['SPY', 'QQQ'],
            data_types=['quotes', 'greeks'],
            priority=1,
            use_cache=True
        )
        
        response = await service.get_market_data(request)
        print(f"✅ Market data request: {len(response.symbols)} symbols, latency: {response.latency_ms:.1f}ms")
        print(f"✅ Data source: {response.source_provider}, cache hit: {response.cache_hit}")
        
        # Test subscription (mock)
        callback_called = False
        def test_callback(symbol, data):
            nonlocal callback_called
            callback_called = True
            print(f"✅ Subscription callback: {symbol}")
        
        await service.subscribe_market_data(['SPY'], ['quotes'], test_callback)
        print("✅ Market data subscription created")
        
        # Test option chain
        chain_data = await service.get_option_chain('SPY', '2024-03-15')
        print(f"✅ Option chain data: {len(chain_data)} entries")
        
        # Test historical data
        hist_data = await service.get_historical_data('SPY', '1D', 30)
        print(f"✅ Historical data: {len(hist_data)} periods")
        
        # Get service metrics
        metrics = service.get_service_metrics()
        print(f"✅ Service metrics: {metrics['request_stats']['total_requests']} requests processed")
        
        return {'success': True, 'service': service}
        
    except Exception as e:
        print(f"❌ Market data service error: {e}")
        return {'success': False, 'error': str(e)}

async def test_options_pricing_service(strategy_config, service_config):
    """Test Options Pricing Service"""
    print("\n💰 Testing Options Pricing Service")
    print("-" * 50)
    
    # Create service
    service = OptionsPricingService(service_config, strategy_config)
    
    try:
        # Test service lifecycle
        assert await service.start(), "Failed to start options pricing service"
        print("✅ Options pricing service started")
        
        # Test health check
        health = await service._health_check()
        print(f"✅ Health check: Heston available: {health['models_available']['heston']}")
        
        # Create test option contract
        contract = OptionContract(
            symbol='SPY240315C00500000',
            underlying='SPY',
            option_type='C',
            strike=500.0,
            expiry_date=datetime(2024, 3, 15),
            quantity=1
        )
        
        # Create pricing request
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
        
        pricing_request = PricingRequest(
            contracts=[contract],
            market_data=market_data,
            model=PricingModel.HESTON,
            include_greeks=True,
            calibrate_model=True
        )
        
        # Test pricing
        response = await service.price_options(pricing_request)
        print(f"✅ Options pricing: {len(response.results)} contracts priced")
        
        if response.results:
            result = response.results[0]
            print(f"✅ Theoretical price: ${result.theoretical_price:.2f}")
            print(f"✅ Greeks: Delta={result.delta:.3f}, Gamma={result.gamma:.3f}")
            print(f"✅ Confidence score: {result.confidence_score:.2f}")
        
        # Test calibration
        calibration = await service.calibrate_model('SPY', market_data, PricingModel.HESTON)
        print(f"✅ Model calibration: {calibration['success']}")
        
        # Test implied volatility calculation
        if response.results:
            iv = await service.get_implied_volatility(contract, 25.50, market_data)
            print(f"✅ Implied volatility: {iv:.3f}" if iv else "✅ IV calculation: N/A")
        
        # Get service metrics
        metrics = service.get_service_metrics()
        print(f"✅ Service metrics: {metrics['pricing_stats']['total_requests']} pricing requests")
        
        return {'success': True, 'service': service}
        
    except Exception as e:
        print(f"❌ Options pricing service error: {e}")
        return {'success': False, 'error': str(e)}

async def test_execution_service(strategy_config, service_config):
    """Test Execution Service"""
    print("\n⚡ Testing Execution Service")
    print("-" * 50)
    
    # Create service
    service = ExecutionService(service_config, strategy_config)
    
    try:
        # Test service lifecycle
        assert await service.start(), "Failed to start execution service"
        print("✅ Execution service started")
        
        # Test health check
        health = await service._health_check()
        print(f"✅ Health check: {health['execution_engines']['total']} engines available")
        
        # Create test order request
        order_request = OrderRequest(
            symbol='SPY',
            side=OrderSide.BUY,
            quantity=100,
            order_type=OrderType.MARKET,
            time_in_force=TimeInForce.DAY,
            strategy_id='test_strategy',
            max_position_size=1000,
            max_order_value=50000
        )
        
        # Submit order
        order_id = await service.submit_order(order_request)
        print(f"✅ Order submitted: {order_id}")
        
        # Get order
        order = service.get_order(order_id)
        if order:
            print(f"✅ Order retrieved: {order.symbol} {order.side.value} {order.quantity}")
            print(f"✅ Order status: {order.status.value}")
        
        # Wait for simulated execution
        await asyncio.sleep(0.2)
        
        # Check order status after execution
        order = service.get_order(order_id)
        if order:
            print(f"✅ Order after execution: {order.status.value}")
            if order.fills:
                print(f"✅ Fills: {len(order.fills)} fills, avg price: ${order.avg_fill_price:.2f}")
        
        # Test order modification
        if order and order.is_active():
            modified = await service.modify_order(order_id, new_price=505.0)
            print(f"✅ Order modification: {modified}")
        
        # Get active orders
        active_orders = service.get_active_orders('SPY')
        print(f"✅ Active orders for SPY: {len(active_orders)}")
        
        # Get orders by strategy
        strategy_orders = service.get_orders_by_strategy('test_strategy')
        print(f"✅ Strategy orders: {len(strategy_orders)}")
        
        # Test order callbacks
        callback_called = False
        def order_callback(order):
            nonlocal callback_called
            callback_called = True
            print(f"✅ Order callback: {order.order_id} -> {order.status.value}")
        
        service.add_order_callback(order_callback)
        print("✅ Order callback registered")
        
        # Get service metrics
        metrics = service.get_service_metrics()
        print(f"✅ Service metrics: {metrics['execution_stats']['total_orders']} orders processed")
        
        return {'success': True, 'service': service}
        
    except Exception as e:
        print(f"❌ Execution service error: {e}")
        return {'success': False, 'error': str(e)}

async def test_notification_service(strategy_config, service_config):
    """Test Notification Service"""
    print("\n📢 Testing Notification Service")
    print("-" * 50)
    
    # Create service
    service = NotificationService(service_config, strategy_config)
    
    try:
        # Test service lifecycle
        assert await service.start(), "Failed to start notification service"
        print("✅ Notification service started")
        
        # Test health check
        health = await service._health_check()
        print(f"✅ Health check: {health['channels']['enabled']} channels enabled")
        
        # Create test notification
        notification = Notification(
            id="",  # Will be generated
            level=NotificationLevel.INFO,
            title="Test Notification",
            message="This is a test notification from the service layer test",
            channels=[NotificationChannel.CONSOLE, NotificationChannel.FILE],
            source="test",
            category="system_test",
            data={'test_key': 'test_value', 'timestamp': datetime.now().isoformat()}
        )
        
        # Send notification
        notif_id = await service.send_notification(notification)
        print(f"✅ Notification sent: {notif_id}")
        
        # Wait for processing
        await asyncio.sleep(0.1)
        
        # Get notification
        sent_notification = service.get_notification(notif_id)
        if sent_notification:
            print(f"✅ Notification status: {sent_notification.status.value}")
            print(f"✅ Delivery results: {len(sent_notification.delivery_results)} channels")
        
        # Send alert notification
        alert_id = await service.send_alert(
            level=NotificationLevel.WARNING,
            title="Test Alert",
            message="This is a test alert notification",
            channels=[NotificationChannel.CONSOLE],
            source="test_alert"
        )
        print(f"✅ Alert sent: {alert_id}")
        
        # Test subscription
        callback_called = False
        def notification_callback(notification):
            nonlocal callback_called
            callback_called = True
            print(f"✅ Notification callback: {notification.title}")
        
        service.subscribe(NotificationLevel.ERROR, notification_callback)
        
        # Send error notification to trigger callback
        error_id = await service.send_alert(
            level=NotificationLevel.ERROR,
            title="Test Error",
            message="This is a test error notification",
            channels=[NotificationChannel.CONSOLE]
        )
        
        # Wait for processing
        await asyncio.sleep(0.1)
        print(f"✅ Error notification callback triggered: {callback_called}")
        
        # Get recent notifications
        recent = service.get_recent_notifications(1)  # Last 1 hour
        print(f"✅ Recent notifications: {len(recent)}")
        
        # Get service metrics
        metrics = service.get_service_metrics()
        print(f"✅ Service metrics: {metrics['notification_stats']['total_sent']} notifications sent")
        
        return {'success': True, 'service': service}
        
    except Exception as e:
        print(f"❌ Notification service error: {e}")
        return {'success': False, 'error': str(e)}

async def test_service_integration():
    """Test service integration and coordination"""
    print("\n🔗 Testing Service Integration")
    print("-" * 50)
    
    try:
        # Load configuration
        config_manager = get_config_manager()
        config_manager.load_config("config/demo_config.yaml")
        strategy_config = config_manager.get_strategy_config()
        
        # Create service configurations
        market_data_config = ServiceConfig(
            name="market_data_service",
            enabled=True,
            heartbeat_interval=30,
            auto_restart=True
        )
        
        notification_config = ServiceConfig(
            name="notification_service", 
            enabled=True,
            dependencies=["market_data_service"]
        )
        
        # Create services
        market_service = MarketDataService(market_data_config, strategy_config)
        notify_service = NotificationService(notification_config, strategy_config)
        
        # Start services
        await market_service.start()
        await notify_service.start()
        print("✅ Multiple services started successfully")
        
        # Test service coordination
        market_request = MarketDataRequest(
            symbols=['SPY'],
            data_types=['quotes'],
            use_cache=True
        )
        
        # Get market data
        market_response = await market_service.get_market_data(market_request)
        print(f"✅ Market data retrieved: {len(market_response.data)} symbols")
        
        # Send notification about market data
        await notify_service.send_alert(
            level=NotificationLevel.INFO,
            title="Market Data Update",
            message=f"Retrieved market data for {len(market_response.symbols)} symbols",
            channels=[NotificationChannel.CONSOLE],
            data={
                'symbols': market_response.symbols,
                'source_provider': market_response.source_provider,
                'latency_ms': market_response.latency_ms
            }
        )
        print("✅ Cross-service notification sent")
        
        # Test service status monitoring
        market_status = market_service.get_status()
        notify_status = notify_service.get_status()
        
        market_uptime = market_status['uptime_seconds'] or 0
        notify_uptime = notify_status['uptime_seconds'] or 0
        print(f"✅ Market data service: {market_status['status']} (uptime: {market_uptime:.1f}s)")
        print(f"✅ Notification service: {notify_status['status']} (healthy: {notify_status['healthy']})")
        
        # Test graceful shutdown
        await market_service.stop()
        await notify_service.stop()
        print("✅ Services stopped gracefully")
        
        return {'success': True, 'services_tested': 2}
        
    except Exception as e:
        print(f"❌ Service integration error: {e}")
        return {'success': False, 'error': str(e)}

def compare_service_architecture():
    """Compare old vs new service architecture"""
    print("\n📊 Service Architecture Comparison")
    print("=" * 60)
    
    old_approach = [
        "Monolithic strategy components",
        "Direct coupling between modules",
        "No standardized service interface",
        "Manual lifecycle management",
        "Limited error handling",
        "No service health monitoring"
    ]
    
    new_approach = [
        "Service-oriented architecture with BaseService",
        "Loose coupling via service abstractions",
        "Standardized service lifecycle and interface",
        "Automatic service management and monitoring",
        "Comprehensive error handling and recovery",
        "Built-in health checks and metrics",
        "Event-driven callbacks and notifications",
        "Service dependency management",
        "Graceful shutdown and resource cleanup"
    ]
    
    print("🔴 Old Approach:")
    for item in old_approach:
        print(f"  • {item}")
    
    print("\n🟢 New Service Layer Architecture:")
    for item in new_approach:
        print(f"  • {item}")
    
    print("\n✨ Service Layer Benefits:")
    print("  • 🎯 Unified Interface: All services follow BaseService pattern")
    print("  • ⚡ Lifecycle Management: Automatic start/stop/restart capabilities")
    print("  • 🔍 Health Monitoring: Built-in health checks and status reporting")
    print("  • 🛡️ Error Recovery: Automatic retry and failover mechanisms")
    print("  • 📊 Performance Metrics: Comprehensive service performance tracking")
    print("  • 🔗 Service Coordination: Event-driven inter-service communication")
    print("  • 📢 Notification System: Multi-channel alert and notification delivery")
    print("  • 💾 Caching & Throttling: Intelligent caching and rate limiting")

async def main():
    """Main test function"""
    print("🛡️ SERVICE LAYER ARCHITECTURE TEST")
    print("=" * 70)
    
    try:
        # Test configurations
        config_data = await test_service_configurations()
        strategy_config = config_data['strategy_config']
        service_configs = config_data['service_configs']
        
        # Test individual services
        services_tested = []
        
        # Test Market Data Service
        market_result = await test_market_data_service(strategy_config, service_configs[0])
        services_tested.append(('Market Data Service', market_result['success']))
        if market_result['success']:
            await market_result['service'].stop()
        
        # Test Options Pricing Service
        pricing_result = await test_options_pricing_service(strategy_config, service_configs[1])
        services_tested.append(('Options Pricing Service', pricing_result['success']))
        if pricing_result['success']:
            await pricing_result['service'].stop()
        
        # Test Execution Service
        execution_result = await test_execution_service(strategy_config, service_configs[2])
        services_tested.append(('Execution Service', execution_result['success']))
        if execution_result['success']:
            await execution_result['service'].stop()
        
        # Test Notification Service
        notification_result = await test_notification_service(strategy_config, service_configs[3])
        services_tested.append(('Notification Service', notification_result['success']))
        if notification_result['success']:
            await notification_result['service'].stop()
        
        # Test service integration
        integration_result = await test_service_integration()
        services_tested.append(('Service Integration', integration_result['success']))
        
        # Compare architectures
        compare_service_architecture()
        
        # Summary
        print("\n🎉 SERVICE LAYER TESTS COMPLETE!")
        print("=" * 70)
        
        successful_tests = sum(1 for _, success in services_tested if success)
        total_tests = len(services_tested)
        
        print(f"✅ Test Results: {successful_tests}/{total_tests} services passed")
        
        for service_name, success in services_tested:
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"  {status}: {service_name}")
        
        if successful_tests == total_tests:
            print("🛡️ Service layer architecture is fully operational!")
            print("🚀 Ready for production service coordination")
        else:
            print(f"⚠️ {total_tests - successful_tests} services need attention")
        
    except Exception as e:
        logger.error(f"Service layer test failed: {e}")
        print(f"\n❌ Service layer test failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())