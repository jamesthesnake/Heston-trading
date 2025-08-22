#!/usr/bin/env python3
"""
Main entry point for Heston Trading System
"""
import sys
import os
import click
import logging
import asyncio
from pathlib import Path
import yaml

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def load_config(config_path: str, env: str) -> dict:
    """Load configuration files"""
    config = {}
    
    # Load main config
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Load environment-specific config
    env_config_path = f"config/config.{env}.yaml"
    if os.path.exists(env_config_path):
        with open(env_config_path, 'r') as f:
            env_config = yaml.safe_load(f)
            # Merge configs (env config overrides main)
            config.update(env_config)
    
    return config

@click.command()
@click.option('--env', default='development', help='Environment: development/paper/live')
@click.option('--config', default='config/config.yaml', help='Config file path')
@click.option('--dashboard/--no-dashboard', default=True, help='Enable dashboard')
@click.option('--mock/--no-mock', default=False, help='Use mock data')
def main(env, config, dashboard, mock):
    """Start Heston Trading System"""
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    print("="*60)
    print("       HESTON TRADING SYSTEM")
    print("="*60)
    print(f"Environment: {env}")
    print(f"Config: {config}")
    print(f"Dashboard: {'Enabled' if dashboard else 'Disabled'}")
    print(f"Mock Data: {'Yes' if mock else 'No'}")
    print("="*60)
    
    try:
        # Load configuration
        config_data = load_config(config, env)
        
        # Override mock setting if specified
        if mock or env == 'development':
            if 'data' not in config_data:
                config_data['data'] = {}
            config_data['data']['use_mock'] = True
        
        # Import here to catch any import errors
        from src.strategy import MispricingStrategy
        from src.data import DataFeedManager
        from src.monitoring import Dashboard, MetricsServer
        
        # Initialize components
        logger.info("Initializing components...")
        
        # Initialize data feed
        feed_manager = DataFeedManager(config_data)
        if feed_manager.connect():
            logger.info("✓ Data feed connected")
        else:
            logger.error("Failed to connect data feed")
            return 1
        
        # Initialize strategy
        strategy = MispricingStrategy(config_data)
        logger.info("✓ Strategy initialized")
        
        # Start metrics server
        metrics = MetricsServer(port=config_data.get('monitoring', {}).get('prometheus_port', 9090))
        metrics.start()
        logger.info("✓ Metrics server started")
        
        # Start dashboard if enabled
        if dashboard:
            dash = Dashboard(strategy, feed_manager, 
                           port=config_data.get('monitoring', {}).get('dashboard_port', 8050))
            dash.start()
            logger.info("✓ Dashboard started at http://localhost:8050")
        
        logger.info("✓ System ready")
        logger.info("System running. Press Ctrl+C to stop.")
        print("\n" + "="*60)
        print("Dashboard: http://localhost:8050")
        print("Metrics:   http://localhost:9090/metrics")
        print("Press Ctrl+C to stop")
        print("="*60 + "\n")
        
        # Create and run event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def run_system():
            """Run the complete system"""
            # Start strategy
            strategy_task = asyncio.create_task(strategy.start())
            
            # Keep system running
            try:
                await strategy_task
            except KeyboardInterrupt:
                pass
        
        # Run the system
        loop.run_until_complete(run_system())
        
    except KeyboardInterrupt:
        logger.info("\nShutting down...")
        if 'strategy' in locals():
            strategy.stop()
        if 'feed_manager' in locals():
            feed_manager.disconnect()
        logger.info("Shutdown complete")
        
    except ImportError as e:
        logger.error(f"Import error: {e}")
        logger.error("Please ensure all dependencies are installed: pip install -r requirements.txt")
        return 1
        
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
