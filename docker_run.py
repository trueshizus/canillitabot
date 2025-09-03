#!/usr/bin/env python3
"""
Simple bot runner for Docker container
"""

import sys
import os
from pathlib import Path

# Set working directory to project root
os.chdir('/app')

# Add paths for proper imports
sys.path.insert(0, '/app')
sys.path.insert(0, '/app/src')

# Now import and run
os.chdir('/app/src')  # Change to src for relative imports
exec(open('/app/run.py').read())
