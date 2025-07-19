"""
eBay Taxonomy API tools for intelligent category management.

Provides progressive category navigation, smart caching, and LLM-friendly 
category search. Implements eBay's recommended caching strategy with 
version-based invalidation.

IMPLEMENTATION FOLLOWS: PYDANTIC-FIRST DEVELOPMENT METHODOLOGY
- All API fields included exactly as documented
- Strong typing with enums throughout
- Validation through Pydantic models only
- Zero manual validation code
- Efficient caching preserved for performance

API Documentation: https://developer.ebay.com/api-docs/commerce/taxonomy/resources/methods
OAuth Scope Required: https://api.ebay.com/oauth/api_scope/commerce.taxonomy (basic scope)
"""
from fastmcp import Context

from api.oauth import OAuthManager, OAuthConfig
from api.rest_client import EbayRestClient, RestConfig
from api.errors import EbayApiError
from api.category_cache import get_category_tree_json, find_category_subtree
from models.enums import MarketplaceIdEnum
from models.browse import (
    GetDefaultCategoryTreeIdInput, GetCategoryTreeInput, GetCategorySubtreeInput,
    GetCategorySuggestionsInput, GetExpiredCategoriesInput
)
from data_types import success_response, error_response, ErrorCode
from lootly_server import mcp


# PYDANTIC MODELS - API Documentation → Pydantic Models → MCP Tools


@mcp.tool
async def get_default_category_tree_id(
    ctx: Context,
    input_data: GetDefaultCategoryTreeIdInput
) -> str:
    """
    Get the default category tree ID for a marketplace.
    
    Each eBay marketplace has its own category tree. This tool gets the
    default category tree ID for the specified marketplace. Call this first
    to get the tree ID needed for get_category_tree.
    
    Args:
        input_data: Input containing marketplace ID
        ctx: MCP context
    
    Returns:
        JSON response with the default category tree ID
    """
    await ctx.info(f"Getting default category tree ID for {input_data.marketplaceId}")
    
    # Input already validated by Pydantic
    
    # Check credentials
    if not mcp.config.app_id or not mcp.config.cert_id:
        return error_response(
            ErrorCode.CONFIGURATION_ERROR,
            "eBay API credentials required for category tree access. Get credentials from https://developer.ebay.com/my/keys"
        ).to_json_string()
    
    # Initialize API clients
    oauth_config = OAuthConfig(
        client_id=mcp.config.app_id,
        client_secret=mcp.config.cert_id,
        sandbox=mcp.config.sandbox_mode
    )
    oauth_manager = OAuthManager(oauth_config)
    
    rest_config = RestConfig(
        sandbox=mcp.config.sandbox_mode,
        rate_limit_per_day=mcp.config.rate_limit_per_day
    )
    rest_client = EbayRestClient(oauth_manager, rest_config)
    
    try:
        # Get default category tree ID
        response = await rest_client.get(
            "/commerce/taxonomy/v1/get_default_category_tree_id",
            params={"marketplace_id": input_data.marketplaceId}
        )
        response_body = response["body"]
        
        category_tree_id = response_body.get("categoryTreeId")
        
        await ctx.info(f"Default category tree ID: {category_tree_id}")
        
        return success_response(
            data={
                "categoryTreeId": category_tree_id,
                "marketplaceId": input_data.marketplaceId,
                "dataSource": "live_api"
            },
            message=f"Default category tree ID for {input_data.marketplaceId}"
        ).to_json_string()
        
    except EbayApiError as e:
        await ctx.error(f"eBay API error: {e.get_comprehensive_message()}")
        error_details = e.get_full_error_details()
        error_details["marketplaceId"] = input_data.marketplaceId
        
        return error_response(
            ErrorCode.EXTERNAL_API_ERROR,
            e.get_comprehensive_message(),
            error_details
        ).to_json_string()
    except Exception as e:
        await ctx.error(f"Failed to get category tree ID: {str(e)}")
        return error_response(
            ErrorCode.INTERNAL_ERROR,
            f"Failed to get category tree ID: {str(e)}"
        ).to_json_string()
    finally:
        await rest_client.close()


@mcp.tool
async def get_category_tree(
    ctx: Context,
    category_tree_id: str = "0"
) -> str:
    """
    Get the complete eBay category tree as raw JSON for LLM analysis.
    
    Returns complete category hierarchy (17,000+ categories). LLMs can process 
    this JSON directly to find the best category match or understand the hierarchy 
    structure. Uses efficient caching with 24-hour TTL.
    
    To use this tool:
    1. First call get_default_category_tree_id with your marketplace
    2. Then call this tool with the category_tree_id from step 1
    
    Usage for LLMs:
    - Process the raw JSON to find best category matches
    - Use the hierarchy to understand parent/child relationships
    - All 17k+ categories included for comprehensive search
    
    Args:
        category_tree_id: Category tree ID from get_default_category_tree_id
        ctx: MCP context
    
    Returns:
        Raw JSON with complete category data for LLM processing
    """
    await ctx.info(f"Getting full category tree {category_tree_id}")
    
    # Validate input
    try:
        input_data = GetCategoryTreeInput(categoryTreeId=category_tree_id)
    except Exception as e:
        await ctx.error(f"Validation error: {str(e)}")
        return error_response(
            ErrorCode.VALIDATION_ERROR,
            str(e)
        ).to_json_string()
    
    # Check credentials
    if not mcp.config.app_id or not mcp.config.cert_id:
        return error_response(
            ErrorCode.CONFIGURATION_ERROR,
            "eBay API credentials required for category tree access. Get credentials from https://developer.ebay.com/my/keys"
        ).to_json_string()
    
    try:
        # Initialize API clients
        oauth_config = OAuthConfig(
            client_id=mcp.config.app_id,
            client_secret=mcp.config.cert_id,
            sandbox=mcp.config.sandbox_mode
        )
        oauth_manager = OAuthManager(oauth_config)
        
        rest_config = RestConfig(
            sandbox=mcp.config.sandbox_mode,
            rate_limit_per_day=mcp.config.rate_limit_per_day
        )
        rest_client = EbayRestClient(oauth_manager, rest_config)
        
        try:
            # Get raw category tree JSON from cache or API
            category_tree_json = await get_category_tree_json(
                oauth_manager, 
                rest_client, 
                category_tree_id=input_data.categoryTreeId
            )
            
            await ctx.info(f"Retrieved full category tree with {len(str(category_tree_json))} characters")
            
            return success_response(
                data=category_tree_json,  # Complete raw JSON
                message="Complete eBay category tree for LLM processing"
            ).to_json_string()
        
        finally:
            await rest_client.close()
        
    except Exception as e:
        await ctx.error(f"Failed to get category tree: {str(e)}")
        return error_response(
            ErrorCode.INTERNAL_ERROR,
            f"Failed to get category tree: {str(e)}"
        ).to_json_string()


@mcp.tool
async def get_category_subtree(
    ctx: Context,
    category_tree_id: str,
    category_id: str
) -> str:
    """
    Get a specific category subtree for efficient navigation.
    
    Returns the subtree starting from a specific category ID. This is more 
    efficient than fetching the entire tree when you only need a specific 
    branch. Uses the same caching mechanism as the full tree.
    
    To use this tool:
    1. First call get_default_category_tree_id with your marketplace
    2. Then call this tool with the category_tree_id from step 1
    
    Args:
        category_tree_id: Category tree ID from get_default_category_tree_id
        category_id: Parent category ID to get subtree from
        ctx: MCP context
    
    Returns:
        Raw JSON subtree for the specified category
    """
    await ctx.info(f"Getting category subtree for {category_id} in tree {category_tree_id}")
    
    # Validate input
    try:
        input_data = GetCategorySubtreeInput(
            categoryTreeId=category_tree_id,
            categoryId=category_id
        )
    except Exception as e:
        await ctx.error(f"Validation error: {str(e)}")
        return error_response(
            ErrorCode.VALIDATION_ERROR,
            str(e)
        ).to_json_string()
    
    # Check credentials
    if not mcp.config.app_id or not mcp.config.cert_id:
        return error_response(
            ErrorCode.CONFIGURATION_ERROR,
            "eBay API credentials required for category tree access. Get credentials from https://developer.ebay.com/my/keys"
        ).to_json_string()
    
    try:
        # Initialize API clients
        oauth_config = OAuthConfig(
            client_id=mcp.config.app_id,
            client_secret=mcp.config.cert_id,
            sandbox=mcp.config.sandbox_mode
        )
        oauth_manager = OAuthManager(oauth_config)
        
        rest_config = RestConfig(
            sandbox=mcp.config.sandbox_mode,
            rate_limit_per_day=mcp.config.rate_limit_per_day
        )
        rest_client = EbayRestClient(oauth_manager, rest_config)
        
        try:
            # First get the full tree from cache
            category_tree_json = await get_category_tree_json(
                oauth_manager, 
                rest_client, 
                category_tree_id=input_data.categoryTreeId
            )
            
            # Find subtree for specific category
            subtree_json = find_category_subtree(category_tree_json, input_data.categoryId)
            if not subtree_json:
                return error_response(
                    ErrorCode.NOT_FOUND_ERROR,
                    f"Category {input_data.categoryId} not found in tree"
                ).to_json_string()
            
            await ctx.info(f"Retrieved subtree for category {input_data.categoryId}")
            
            return success_response(
                data=subtree_json,  # Raw JSON subtree
                message=f"Category subtree for {input_data.categoryId}"
            ).to_json_string()
        
        finally:
            await rest_client.close()
        
    except Exception as e:
        await ctx.error(f"Failed to get category subtree: {str(e)}")
        return error_response(
            ErrorCode.INTERNAL_ERROR,
            f"Failed to get category subtree: {str(e)}"
        ).to_json_string()


@mcp.tool
async def get_category_suggestions(
    ctx: Context,
    category_tree_id: str,
    q: str
) -> str:
    """
    Get category suggestions based on a search query.
    
    Returns suggested categories that match the search query. This helps sellers 
    find the most appropriate category for their items by searching with keywords.
    
    To use this tool:
    1. First call get_default_category_tree_id with your marketplace
    2. Then call this tool with the category_tree_id from step 1
    
    Args:
        category_tree_id: Category tree ID from get_default_category_tree_id
        q: Query string for category search
        ctx: MCP context
    
    Returns:
        JSON response with suggested categories
    """
    await ctx.info(f"Getting category suggestions for query: {q}")
    
    # Validate input
    try:
        input_data = GetCategorySuggestionsInput(
            categoryTreeId=category_tree_id,
            q=q
        )
    except Exception as e:
        await ctx.error(f"Validation error: {str(e)}")
        return error_response(
            ErrorCode.VALIDATION_ERROR,
            str(e)
        ).to_json_string()
    
    # Check credentials
    if not mcp.config.app_id or not mcp.config.cert_id:
        return error_response(
            ErrorCode.CONFIGURATION_ERROR,
            "eBay API credentials required for category tree access. Get credentials from https://developer.ebay.com/my/keys"
        ).to_json_string()
    
    # Initialize API clients
    oauth_config = OAuthConfig(
        client_id=mcp.config.app_id,
        client_secret=mcp.config.cert_id,
        sandbox=mcp.config.sandbox_mode
    )
    oauth_manager = OAuthManager(oauth_config)
    
    rest_config = RestConfig(
        sandbox=mcp.config.sandbox_mode,
        rate_limit_per_day=mcp.config.rate_limit_per_day
    )
    rest_client = EbayRestClient(oauth_manager, rest_config)
    
    try:
        # Get category suggestions
        response = await rest_client.get(
            f"/commerce/taxonomy/v1/category_tree/{input_data.categoryTreeId}/get_category_suggestions",
            params={"q": input_data.q}
        )
        response_body = response["body"]
        
        await ctx.info(f"Found {len(response_body.get('categorySuggestions', []))} category suggestions")
        
        return success_response(
            data=response_body,  # Raw API response
            message=f"Category suggestions for '{input_data.q}'"
        ).to_json_string()
        
    except EbayApiError as e:
        await ctx.error(f"eBay API error: {e.get_comprehensive_message()}")
        error_details = e.get_full_error_details()
        error_details["query"] = input_data.q
        
        return error_response(
            ErrorCode.EXTERNAL_API_ERROR,
            e.get_comprehensive_message(),
            error_details
        ).to_json_string()
    except Exception as e:
        await ctx.error(f"Failed to get category suggestions: {str(e)}")
        return error_response(
            ErrorCode.INTERNAL_ERROR,
            f"Failed to get category suggestions: {str(e)}"
        ).to_json_string()
    finally:
        await rest_client.close()


@mcp.tool
async def get_expired_categories(
    ctx: Context,
    categoryTreeId: str
) -> str:
    """
    Get a list of expired categories for a marketplace.
    
    Returns categories that have been deprecated or are no longer valid for 
    new listings. This helps identify categories that need to be updated in 
    existing systems.
    
    To use this tool:
    1. First call get_default_category_tree_id with your marketplace
    2. Then call this tool with the category_tree_id from step 1
    
    Args:
        categoryTreeId: Category tree ID from get_default_category_tree_id (usually "0" for most marketplaces)
        ctx: MCP context
    
    Returns:
        JSON response with expired categories containing fromCategoryId and toCategoryId mappings
    """
    await ctx.info(f"Getting expired categories for tree {categoryTreeId}")
    
    # Validate input
    try:
        input_data = GetExpiredCategoriesInput(categoryTreeId=categoryTreeId)
    except Exception as e:
        await ctx.error(f"Validation error: {str(e)}")
        return error_response(
            ErrorCode.VALIDATION_ERROR,
            str(e)
        ).to_json_string()
    
    # Check credentials
    if not mcp.config.app_id or not mcp.config.cert_id:
        return error_response(
            ErrorCode.CONFIGURATION_ERROR,
            "eBay API credentials required for category tree access. Get credentials from https://developer.ebay.com/my/keys"
        ).to_json_string()
    
    # Initialize API clients
    oauth_config = OAuthConfig(
        client_id=mcp.config.app_id,
        client_secret=mcp.config.cert_id,
        sandbox=mcp.config.sandbox_mode
    )
    oauth_manager = OAuthManager(oauth_config)
    
    rest_config = RestConfig(
        sandbox=mcp.config.sandbox_mode,
        rate_limit_per_day=mcp.config.rate_limit_per_day
    )
    rest_client = EbayRestClient(oauth_manager, rest_config)
    
    try:
        # Get expired categories
        response = await rest_client.get(
            f"/commerce/taxonomy/v1/category_tree/{input_data.categoryTreeId}/get_expired_categories"
        )
        response_body = response["body"]
        
        expired_count = len(response_body.get("expiredCategories", []))
        await ctx.info(f"Found {expired_count} expired categories")
        
        return success_response(
            data=response_body,  # Raw API response
            message=f"Found {expired_count} expired categories"
        ).to_json_string()
        
    except EbayApiError as e:
        await ctx.error(f"eBay API error: {e.get_comprehensive_message()}")
        error_details = e.get_full_error_details()
        error_details["categoryTreeId"] = input_data.categoryTreeId
        
        return error_response(
            ErrorCode.EXTERNAL_API_ERROR,
            e.get_comprehensive_message(),
            error_details
        ).to_json_string()
    except Exception as e:
        await ctx.error(f"Failed to get expired categories: {str(e)}")
        return error_response(
            ErrorCode.INTERNAL_ERROR,
            f"Failed to get expired categories: {str(e)}"
        ).to_json_string()
    finally:
        await rest_client.close()