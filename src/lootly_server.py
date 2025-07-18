"""Lootly MCP Server implementation."""
from dotenv import load_dotenv
from fastmcp import FastMCP
from config import EbayConfig
from logging_config import setup_mcp_logging
from __version__ import __version__
from api.cache import init_cache_manager

# Load environment variables
load_dotenv()

# Load configuration
config = EbayConfig.from_env()

# Check credential status and provide helpful feedback
credential_status = config.check_credential_status()
if not credential_status["ready_for_basic_apis"]:
    print("\n⚠️  WARNING: eBay credentials not found!")
    print("Basic API functionality will be limited.")
    print("\nTo set up credentials:")
    print("1. Copy .env.template to .env")
    print("2. Get credentials from https://developer.ebay.com/my/keys")
    print("3. Add your App ID, Dev ID, and Cert ID to .env")
    print("\nStarting with limited functionality...\n")
else:
    print("\n✅ eBay credentials loaded successfully")
    for message in credential_status["messages"]:
        print(f"   {message}")
    print()

# Note: Full credential validation is handled per-tool to allow graceful degradation

# Setup logging
logger = setup_mcp_logging(config)

# Initialize cache manager
cache_manager = init_cache_manager(config.redis_url)

# Create global MCP instance
mcp = FastMCP(
    "Lootly - eBay Integration Server", 
    version=__version__
)

# Store config, logger, and cache manager for tool access
mcp.config = config
mcp.logger = logger
mcp.cache_manager = cache_manager


def create_lootly_server():
    """Create and configure the Lootly MCP server."""
    # Import all modules to register their decorated functions
    # This is done inside the function to avoid circular imports
    
    # Tools
    import tools.browse_api  # New Browse API (replaces Finding API)
    import tools.taxonomy_api  # New Taxonomy API (dynamic categories)
    import tools.account_api  # New Account API (business policies)
    import tools.oauth_consent  # OAuth consent management
    import tools.marketing_api  # New Marketing API for merchandising
    import tools.marketplace_insights_api  # Marketplace Insights API for sales data
    import tools.trending_api  # Trending items using Browse API
    import tools.return_policy_api  # Return Policy API for managing return policies
    import tools.payment_policy_api  # Payment Policy API for managing payment policies
    import tools.fulfillment_policy_api  # Fulfillment Policy API for managing shipping policies
    import tools.inventory_item_api  # Inventory Item API for managing product inventory
    
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
