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
from pydantic import BaseModel, Field, field_validator, ConfigDict

from api.oauth import OAuthManager, OAuthConfig
from api.rest_client import EbayRestClient, RestConfig
from api.errors import EbayApiError
from api.category_cache import get_category_tree_json, find_category_subtree
from models.enums import MarketplaceIdEnum
from data_types import success_response, error_response, ErrorCode
from lootly_server import mcp


# PYDANTIC MODELS - API Documentation → Pydantic Models → MCP Tools


class GetDefaultCategoryTreeIdInput(BaseModel):
    """Input validation for getting default category tree ID."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    marketplace_id: MarketplaceIdEnum = Field(
        default=MarketplaceIdEnum.EBAY_US,
        description="eBay marketplace ID"
    )


class GetCategoryTreeInput(BaseModel):
    """Input validation for getting category tree."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    category_tree_id: str = Field(
        default="0",
        description="Category tree ID (default '0' for US marketplace)"
    )


class GetCategorySubtreeInput(BaseModel):
    """Input validation for getting category subtree."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    category_tree_id: str = Field(..., description="Category tree ID")
    category_id: str = Field(..., description="Parent category ID to get subtree from")
    
    @field_validator('category_id')
    @classmethod
    def validate_category_id(cls, v):
        if not v or not v.strip():
            raise ValueError("Category ID cannot be empty")
        return v.strip()


class GetCategorySuggestionsInput(BaseModel):
    """Input validation for getting category suggestions."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    category_tree_id: str = Field(..., description="Category tree ID")
    q: str = Field(..., description="Query string for category search", min_length=1)
    
    @field_validator('q')
    @classmethod
    def validate_query(cls, v):
        if not v or not v.strip():
            raise ValueError("Query string cannot be empty")
        return v.strip()


class GetExpiredCategoriesInput(BaseModel):
    """Input validation for getting expired categories."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    category_tree_id: str = Field(..., description="Category tree ID")
    marketplace_id: MarketplaceIdEnum = Field(
        default=MarketplaceIdEnum.EBAY_US,
        description="eBay marketplace ID"
    )


# MCP TOOLS - Pydantic Models → MCP Tools → API Integration


@mcp.tool
async def get_default_category_tree_id(
    ctx: Context,
    marketplace_id: MarketplaceIdEnum = MarketplaceIdEnum.EBAY_US
) -> str:
    """
    Get the default category tree ID for a marketplace.
    
    Each eBay marketplace has its own category tree. This tool gets the
    default category tree ID for the specified marketplace. Call this first
    to get the tree ID needed for get_category_tree.
    
    Args:
        marketplace_id: eBay marketplace ID (e.g., EBAY_US, EBAY_GB)
        ctx: MCP context
    
    Returns:
        JSON response with the default category tree ID
    """
    await ctx.info(f"Getting default category tree ID for {marketplace_id.value}")
    
    # Validate input
    try:
        input_data = GetDefaultCategoryTreeIdInput(marketplace_id=marketplace_id)
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
        # Get default category tree ID
        response = await rest_client.get(
            "/commerce/taxonomy/v1/get_default_category_tree_id",
            params={"marketplace_id": input_data.marketplace_id.value}
        )
        response_body = response["body"]
        
        category_tree_id = response_body.get("categoryTreeId")
        
        await ctx.info(f"Default category tree ID: {category_tree_id}")
        
        return success_response(
            data={
                "category_tree_id": category_tree_id,
                "marketplace_id": input_data.marketplace_id.value,
                "data_source": "live_api"
            },
            message=f"Default category tree ID for {input_data.marketplace_id.value}"
        ).to_json_string()
        
    except EbayApiError as e:
        await ctx.error(f"eBay API error: {e.get_comprehensive_message()}")
        error_details = e.get_full_error_details()
        error_details["marketplace_id"] = input_data.marketplace_id.value
        
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
        input_data = GetCategoryTreeInput(category_tree_id=category_tree_id)
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
                category_tree_id=input_data.category_tree_id
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
            category_tree_id=category_tree_id,
            category_id=category_id
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
                category_tree_id=input_data.category_tree_id
            )
            
            # Find subtree for specific category
            subtree_json = find_category_subtree(category_tree_json, input_data.category_id)
            if not subtree_json:
                return error_response(
                    ErrorCode.NOT_FOUND_ERROR,
                    f"Category {input_data.category_id} not found in tree"
                ).to_json_string()
            
            await ctx.info(f"Retrieved subtree for category {input_data.category_id}")
            
            return success_response(
                data=subtree_json,  # Raw JSON subtree
                message=f"Category subtree for {input_data.category_id}"
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
            category_tree_id=category_tree_id,
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
            f"/commerce/taxonomy/v1/category_tree/{input_data.category_tree_id}/get_category_suggestions",
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
    category_tree_id: str,
    marketplace_id: MarketplaceIdEnum = MarketplaceIdEnum.EBAY_US
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
        category_tree_id: Category tree ID from get_default_category_tree_id
        marketplace_id: eBay marketplace ID
        ctx: MCP context
    
    Returns:
        JSON response with expired categories
    """
    await ctx.info(f"Getting expired categories for tree {category_tree_id} in {marketplace_id.value}")
    
    # Validate input
    try:
        input_data = GetExpiredCategoriesInput(
            category_tree_id=category_tree_id,
            marketplace_id=marketplace_id
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
        # Get expired categories
        response = await rest_client.get(
            f"/commerce/taxonomy/v1/category_tree/{input_data.category_tree_id}/get_expired_categories",
            params={"marketplace_id": input_data.marketplace_id.value}
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
        error_details["marketplace_id"] = input_data.marketplace_id.value
        
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