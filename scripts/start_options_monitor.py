#!/usr/bin/env python3
"""
Startup script for SPX/XSP Options Real-Time Monitor
"""
import sys
import os
from pathlib import Path

# Add src to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from apps.options_monitor_app import main

if __name__ == "__main__":
    # Change to project root directory
    os.chdir(project_root)
    
    # Run the application
    sys.exit(main())
