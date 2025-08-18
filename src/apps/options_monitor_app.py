"""
Main application runner for SPX/XSP options real-time monitor
"""
import sys
import os
import logging
import yaml
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from dashboard.options_dashboard import OptionsDashboard

def setup_logging(log_level: str = "INFO"):
    """Setup logging configuration"""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('logs/options_monitor.log')
        ]
    )

def load_config(config_path: str = None) -> dict:
    """Load configuration from YAML file"""
    if not config_path:
        # Default to dev config
        config_path = "config/config.dev.yaml"
    
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Add options-specific configuration
        config.update({
            'risk_free_rate': 0.05,  # 5% risk-free rate
            'max_option_contracts': 500,  # Limit IB subscriptions
            'screening_criteria': {
                'min_dte': 10,
                'max_dte': 50,
                'strike_range_pct': 0.09,  # ±9%
                'max_spread_width_pct': 0.10,  # ≤10%
                'min_mid_price': 0.20,  # ≥$0.20
                'min_volume': 1000,  # ≥1,000
                'min_open_interest': 500,  # ≥500
                'symbols': ['SPX', 'XSP']
            }
        })
        
        return config
        
    except Exception as e:
        print(f"Error loading config: {e}")
        return {}

def main():
    """Main application entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='SPX/XSP Options Real-Time Monitor')
    parser.add_argument('--config', '-c', help='Configuration file path')
    parser.add_argument('--host', default='127.0.0.1', help='Dashboard host')
    parser.add_argument('--port', type=int, default=8050, help='Dashboard port')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--log-level', default='INFO', help='Logging level')
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)
    
    # Load configuration
    config = load_config(args.config)
    if not config:
        logger.error("Failed to load configuration")
        return 1
    
    try:
        # Create and run dashboard
        dashboard = OptionsDashboard(config)
        
        logger.info("Starting SPX/XSP Options Real-Time Monitor")
        logger.info(f"Dashboard will be available at http://{args.host}:{args.port}")
        logger.info("Press Ctrl+C to stop")
        
        dashboard.run(host=args.host, port=args.port, debug=args.debug)
        
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        if 'dashboard' in locals():
            dashboard.stop()
        return 0
        
    except Exception as e:
        logger.error(f"Application error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
