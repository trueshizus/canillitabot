#!/usr/bin/env python3
"""
Simple runner script for CanillitaBot - Reddit Argentina News Bot
"""

import sys
from pathlib import Path

# Add src directory to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from bot import main

if __name__ == "__main__":
    main()