"""
Trade Data AI Analyzer - Main Entry Point
PyQt6 desktop application for material-specific trade data classification
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui.main_window import main

if __name__ == "__main__":
    main()
