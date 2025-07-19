"""
Unified Pydantic Models for eBay MCP Server

This module consolidates all pydantic models and enums used across the eBay MCP server,
providing a single source of truth for data validation and type safety.

Organization:
- enums.py: All eBay API enumerations with validation
- common.py: Shared models used across multiple APIs (Amount, CategoryType, etc.)
- browse.py: Browse API input models
- marketplace.py: Marketplace insights and trending models
- policies.py: Policy management models (fulfillment, return, payment)
- account.py: Account and privileges models
- inventory.py: Inventory management models
"""

# Import all models and enums for easy access
from .enums import *
from .common import *

# Import specific domain models as they're created
try:
    from .browse import *
except ImportError:
    pass

try:
    from .marketplace import *
except ImportError:
    pass

try:
    from .policies import *
except ImportError:
    pass

try:
    from .account import *
except ImportError:
    pass

try:
    from .inventory import *
except ImportError:
    pass

__all__ = [
    # Re-export everything from submodules
    # This will be populated as we add the modules
]