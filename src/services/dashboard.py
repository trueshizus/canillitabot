"""
Compatibility wrapper for CanillitaBot Dashboard.
The dashboard has been moved to src/dashboard/ for better organization.
This file provides backward compatibility.
"""

import warnings
from ..dashboard.app import CanillitaDashboard, main

# Show deprecation warning
warnings.warn(
    "Importing from src.services.dashboard is deprecated. "
    "Please import from src.dashboard.app instead.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export for compatibility
__all__ = ['CanillitaDashboard', 'main']