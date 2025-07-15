"""Lootly MCP Server implementation."""
from dotenv import load_dotenv
from fastmcp import FastMCP
from config import EbayConfig
from logging_config import setup_mcp_logging
from __version__ import __version__

# Load environment variables
load_dotenv()

# Load configuration
config = EbayConfig.from_env()
config.validate_credentials()

# Setup logging
logger = setup_mcp_logging(config)

# Create global MCP instance
mcp = FastMCP(
    "Lootly - eBay Integration Server", 
    version=__version__
)

# Store config and logger for tool access
mcp.config = config
mcp.logger = logger


def create_lootly_server():
    """Create and configure the Lootly MCP server."""
    # Import all modules to register their decorated functions
    # This is done inside the function to avoid circular imports
    
    # Tools
    import tools.finding_api
    import tools.trading_api
    import tools.shopping_api
    import tools.merchandising_api
    
    # Resources
    import resources.categories
    import resources.shipping
    import resources.policies
    import resources.trends
    
    # Prompts
    import prompts.search_assistant
    import prompts.listing_optimizer
    import prompts.deal_finder
    import prompts.market_researcher
    
    # Everything is already configured above
    # and registered via decorators in the imported modules
    return mcp


def main():
    """Entry point for lootly-server command."""
    # This is just an alias to the main function in main.py
    from main import main as main_func
    main_func()