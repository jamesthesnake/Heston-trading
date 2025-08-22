#!/usr/bin/env python3
"""
Heston Trading System Setup Script
Helps new users verify their installation and get started quickly
"""
import sys
import subprocess
import importlib.util
from pathlib import Path

def check_python_version():
    """Check if Python version is supported"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Python 3.8+ required. Current version:", f"{version.major}.{version.minor}.{version.micro}")
        return False
    print(f"✅ Python version: {version.major}.{version.minor}.{version.micro}")
    return True

def check_dependencies():
    """Check if core dependencies are installed"""
    core_deps = [
        'numpy', 'pandas', 'scipy', 'yaml', 'asyncio'
    ]
    
    missing_deps = []
    for dep in core_deps:
        try:
            if dep == 'yaml':
                import yaml
            elif dep == 'asyncio':
                import asyncio
            else:
                importlib.import_module(dep)
            print(f"✅ {dep} installed")
        except ImportError:
            print(f"❌ {dep} missing")
            missing_deps.append(dep)
    
    return missing_deps

def check_config_files():
    """Check if configuration files exist"""
    config_dir = Path("config")
    if not config_dir.exists():
        print("❌ Config directory not found")
        return False
    
    required_configs = ["demo_config.yaml", "live_config.yaml"]
    missing_configs = []
    
    for config in required_configs:
        config_path = config_dir / config
        if config_path.exists():
            print(f"✅ {config} found")
        else:
            print(f"❌ {config} missing")
            missing_configs.append(config)
    
    return len(missing_configs) == 0

def run_basic_tests():
    """Run basic system tests"""
    print("\n🧪 Running basic system tests...")
    
    try:
        # Test configuration loading
        print("Testing configuration system...")
        result = subprocess.run([
            sys.executable, "-c", 
            "from src.config.config_manager import get_config_manager; "
            "cm = get_config_manager(); "
            "cm.load_config('config/demo_config.yaml'); "
            "print('✅ Configuration system working')"
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print("✅ Configuration system test passed")
        else:
            print("❌ Configuration system test failed:")
            print(result.stderr)
            return False
    
    except Exception as e:
        print(f"❌ Configuration test error: {e}")
        return False
    
    try:
        # Test risk system
        print("Testing risk management system...")
        result = subprocess.run([
            sys.executable, "-c",
            "from src.risk.risk_engine import RiskEngine; "
            "from src.risk.risk_types import RiskLevel; "
            "print('✅ Risk system imports working')"
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print("✅ Risk system test passed")
        else:
            print("❌ Risk system test failed:")
            print(result.stderr)
            return False
    
    except Exception as e:
        print(f"❌ Risk system test error: {e}")
        return False
    
    return True

def install_dependencies():
    """Install missing dependencies"""
    print("\n📦 Installing dependencies...")
    
    try:
        result = subprocess.run([
            sys.executable, "-m", "pip", "install", "-r", "requirements.txt"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Dependencies installed successfully")
            return True
        else:
            print("❌ Failed to install dependencies:")
            print(result.stderr)
            return False
    
    except Exception as e:
        print(f"❌ Error installing dependencies: {e}")
        return False

def main():
    """Main setup function"""
    print("🛡️ HESTON TRADING SYSTEM SETUP")
    print("=" * 50)
    
    # Check Python version
    if not check_python_version():
        print("\n❌ Setup failed: Unsupported Python version")
        return False
    
    # Check dependencies
    print("\n📋 Checking dependencies...")
    missing_deps = check_dependencies()
    
    if missing_deps:
        print(f"\n⚠️ Missing dependencies: {', '.join(missing_deps)}")
        install = input("Install missing dependencies? (y/n): ").lower().strip()
        
        if install == 'y':
            if not install_dependencies():
                print("\n❌ Setup failed: Could not install dependencies")
                return False
            
            # Re-check dependencies
            missing_deps = check_dependencies()
            if missing_deps:
                print(f"\n❌ Still missing dependencies: {', '.join(missing_deps)}")
                return False
        else:
            print("\n❌ Setup aborted: Dependencies required")
            return False
    
    # Check configuration files
    print("\n⚙️ Checking configuration files...")
    if not check_config_files():
        print("\n❌ Setup failed: Configuration files missing")
        print("Please ensure config/demo_config.yaml and config/live_config.yaml exist")
        return False
    
    # Run basic tests
    if not run_basic_tests():
        print("\n❌ Setup failed: Basic tests failed")
        return False
    
    # Success message
    print("\n🎉 SETUP COMPLETE!")
    print("=" * 50)
    print("✅ All checks passed")
    print("\n🚀 Next steps:")
    print("1. Run the risk management test:")
    print("   python test_enhanced_risk.py")
    print("\n2. Run the service layer test:")
    print("   python test_service_layer.py")
    print("\n3. Check the README.md for detailed usage instructions")
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️ Setup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error during setup: {e}")
        sys.exit(1)