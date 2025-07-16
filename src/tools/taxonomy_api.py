"""
eBay Taxonomy API tools for intelligent category management.

Provides progressive category navigation, smart caching, and LLM-friendly 
category search. Implements eBay's recommended caching strategy with 
version-based invalidation.
"""
from typing import Optional
from fastmcp import Context
from pydantic import BaseModel, Field, field_validator, ConfigDict
from datetime import datetime, timezone

from api.oauth import OAuthManager, OAuthConfig, OAuthScopes
from api.rest_client import EbayRestClient, RestConfig
from api.errors import EbayApiError
from api.category_cache import get_category_tree_json, find_category_subtree
from data_types import success_response, error_response, ErrorCode
from lootly_server import mcp




class ItemAspectsInput(BaseModel):
    """Input validation for item aspects."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    category_tree_id: str = Field(..., description="Category tree ID")
    category_id: str = Field(..., description="Category ID")
    
    @field_validator('category_id')
    @classmethod
    def validate_category_id(cls, v):
        if not v or not v.strip():
            raise ValueError("Category ID cannot be empty")
        return v.strip()


@mcp.tool
async def get_default_category_tree_id(
    ctx: Context,
    marketplace_id: str = "EBAY_US"
) -> str:
    """
    Get the default category tree ID for a marketplace.
    
    Each eBay marketplace has its own category tree. This tool gets the
    default category tree ID for the specified marketplace.
    
    Args:
        marketplace_id: eBay marketplace ID (e.g., "EBAY_US", "EBAY_GB")
        ctx: MCP context
    
    Returns:
        JSON response with the default category tree ID
    """
    await ctx.info(f"Getting default category tree ID for {marketplace_id}")
    
    # Check credentials
    if not mcp.config.app_id or not mcp.config.cert_id:
        return success_response(
            data={
                "category_tree_id": "0",
                "marketplace_id": marketplace_id,
                "data_source": "static_default",
                "note": "Using default US category tree ID. Set credentials for live data."
            },
            message="Using default category tree ID"
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
            params={"marketplace_id": marketplace_id},
            scope=OAuthScopes.COMMERCE_TAXONOMY
        )
        
        category_tree_id = response.get("categoryTreeId")
        
        await ctx.info(f"Default category tree ID: {category_tree_id}")
        
        return success_response(
            data={
                "category_tree_id": category_tree_id,
                "marketplace_id": marketplace_id,
                "data_source": "live_api"
            },
            message=f"Default category tree ID for {marketplace_id}"
        ).to_json_string()
        
    except EbayApiError as e:
        await ctx.error(f"eBay API error: {str(e)}")
        return error_response(
            ErrorCode.EXTERNAL_API_ERROR,
            str(e),
            {"status_code": e.status_code, "marketplace_id": marketplace_id}
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
    category_tree_id: str = "0",
    category_id: Optional[str] = None
) -> str:
    """
    Get eBay category tree as raw JSON for LLM analysis.
    
    Returns complete category hierarchy (17,000+ categories) or subtree starting from 
    a specific parent category. LLMs can process this JSON directly to find the best 
    category match or understand the hierarchy structure.
    
    Usage for LLMs:
    - Call with no category_id for FULL category tree (all 17k+ categories)
    - Call with category_id="58058" for just Computer/Electronics subtree  
    - Process the raw JSON to find best category matches
    - Use the hierarchy to understand parent/child relationships
    
    Args:
        category_tree_id: Category tree ID (default "0" for US marketplace)
        category_id: Optional parent category ID to get subtree (omit for full tree)
        ctx: MCP context
    
    Returns:
        Raw JSON with complete category data for LLM processing
    """
    await ctx.info(f"Getting category tree {category_tree_id}" + 
                  (f" starting from {category_id}" if category_id else ""))
    
    # Check credentials
    if not mcp.config.app_id or not mcp.config.cert_id:
        return error_response(
            ErrorCode.CONFIGURATION_ERROR,
            "eBay API credentials required for category tree access"
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
                marketplace_id="EBAY_US"
            )
            
            if category_id:
                # Find subtree for specific category
                subtree_json = find_category_subtree(category_tree_json, category_id)
                if not subtree_json:
                    return error_response(
                        ErrorCode.NOT_FOUND_ERROR,
                        f"Category {category_id} not found in tree"
                    ).to_json_string()
                
                await ctx.info(f"Retrieved subtree for category {category_id}")
                
                return success_response(
                    data=subtree_json,  # Raw JSON subtree
                    message=f"Category subtree for {category_id}"
                ).to_json_string()
            else:
                # Return full tree as raw JSON
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
async def get_item_aspects_for_category(
    ctx: Context,
    category_id: str,
    category_tree_id: str = "0"
) -> str:
    """
    Get item aspects (attributes) for a specific category.
    
    Returns the required and optional attributes for listing items in a category.
    Essential for creating proper listings with the correct specifications.
    
    Args:
        category_id: eBay category ID
        category_tree_id: Category tree ID (default "0" for US)
        ctx: MCP context
    
    Returns:
        JSON response with item aspects and constraints
    """
    await ctx.info(f"Getting item aspects for category {category_id}")
    await ctx.report_progress(0.1, "Validating parameters...")
    
    # Check credentials
    if not mcp.config.app_id or not mcp.config.cert_id:
        return success_response(
            data={
                "category_id": category_id,
                "category_tree_id": category_tree_id,
                "aspects": [],
                "data_source": "static_fallback",
                "note": "Item aspects require eBay API credentials. Common aspects include Brand, Model, Condition, Color, Size."
            },
            message="Item aspects not available without API credentials"
        ).to_json_string()
    
    # Validate input
    try:
        input_data = ItemAspectsInput(
            category_tree_id=category_tree_id,
            category_id=category_id
        )
    except Exception as e:
        await ctx.error(f"Validation error: {str(e)}")
        return error_response(
            ErrorCode.VALIDATION_ERROR,
            str(e)
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
        await ctx.report_progress(0.3, "Fetching item aspects...")
        
        # Make API request
        response = await rest_client.get(
            f"/commerce/taxonomy/v1/category_tree/{input_data.category_tree_id}/get_item_aspects_for_category",
            params={"category_id": input_data.category_id},
            scope=OAuthScopes.COMMERCE_TAXONOMY
        )
        
        await ctx.report_progress(0.8, "Processing aspects...")
        
        # Parse aspects
        aspects = []
        for aspect in response.get("aspects", []):
            aspect_data = {
                "localizedAspectName": aspect.get("localizedAspectName"),
                "aspectConstraint": aspect.get("aspectConstraint"),
                "aspectDataType": aspect.get("aspectDataType"),
                "aspectEnabledForVariations": aspect.get("aspectEnabledForVariations", False),
                "aspectRequired": aspect.get("aspectRequired", False),
                "aspectUsage": aspect.get("aspectUsage"),
                "expectedRequiredByDate": aspect.get("expectedRequiredByDate"),
                "itemToAspectCardinality": aspect.get("itemToAspectCardinality"),
                "relevanceIndicator": aspect.get("relevanceIndicator")
            }
            
            # Add aspect values if available
            if "aspectValues" in aspect:
                aspect_data["aspectValues"] = aspect["aspectValues"]
            
            aspects.append(aspect_data)
        
        await ctx.report_progress(1.0, "Complete")
        await ctx.info(f"Found {len(aspects)} item aspects")
        
        return success_response(
            data={
                "category_id": input_data.category_id,
                "category_tree_id": input_data.category_tree_id,
                "aspects": aspects,
                "total_aspects": len(aspects),
                "data_source": "live_api",
                "fetched_at": datetime.now(timezone.utc).isoformat()
            },
            message=f"Found {len(aspects)} item aspects for category {category_id}"
        ).to_json_string()
        
    except EbayApiError as e:
        await ctx.error(f"eBay API error: {str(e)}")
        return error_response(
            ErrorCode.EXTERNAL_API_ERROR,
            str(e),
            {"status_code": e.status_code, "category_id": category_id}
        ).to_json_string()
    except Exception as e:
        await ctx.error(f"Failed to get item aspects: {str(e)}")
        return error_response(
            ErrorCode.INTERNAL_ERROR,
            f"Failed to get item aspects: {str(e)}"
        ).to_json_string()
    finally:
        await rest_client.close()


@mcp.tool
async def get_compatibility_properties(
    ctx: Context,
    category_id: str,
    category_tree_id: str = "0"
) -> str:
    """
    Get compatibility properties for automotive and related categories.
    
    Returns vehicle compatibility information for parts and accessories.
    
    Args:
        category_id: eBay category ID
        category_tree_id: Category tree ID (default "0" for US)
        ctx: MCP context
    
    Returns:
        JSON response with compatibility properties
    """
    await ctx.info(f"Getting compatibility properties for category {category_id}")
    
    # Check credentials
    if not mcp.config.app_id or not mcp.config.cert_id:
        return success_response(
            data={
                "category_id": category_id,
                "category_tree_id": category_tree_id,
                "compatibility_properties": [],
                "data_source": "static_fallback",
                "note": "Compatibility properties require eBay API credentials"
            },
            message="Compatibility properties not available without API credentials"
        ).to_json_string()
    
    # Validate input
    try:
        input_data = ItemAspectsInput(
            category_tree_id=category_tree_id,
            category_id=category_id
        )
    except Exception as e:
        await ctx.error(f"Validation error: {str(e)}")
        return error_response(
            ErrorCode.VALIDATION_ERROR,
            str(e)
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
        # Make API request
        response = await rest_client.get(
            f"/commerce/taxonomy/v1/category_tree/{input_data.category_tree_id}/get_compatibility_properties",
            params={"category_id": input_data.category_id},
            scope=OAuthScopes.COMMERCE_TAXONOMY
        )
        
        # Parse compatibility properties
        compatibility_properties = response.get("compatibilityProperties", [])
        
        await ctx.info(f"Found {len(compatibility_properties)} compatibility properties")
        
        return success_response(
            data={
                "category_id": input_data.category_id,
                "category_tree_id": input_data.category_tree_id,
                "compatibility_properties": compatibility_properties,
                "total_properties": len(compatibility_properties),
                "data_source": "live_api",
                "fetched_at": datetime.now(timezone.utc).isoformat()
            },
            message=f"Found {len(compatibility_properties)} compatibility properties"
        ).to_json_string()
        
    except EbayApiError as e:
        await ctx.error(f"eBay API error: {str(e)}")
        return error_response(
            ErrorCode.EXTERNAL_API_ERROR,
            str(e),
            {"status_code": e.status_code, "category_id": category_id}
        ).to_json_string()
    except Exception as e:
        await ctx.error(f"Failed to get compatibility properties: {str(e)}")
        return error_response(
            ErrorCode.INTERNAL_ERROR,
            f"Failed to get compatibility properties: {str(e)}"
        ).to_json_string()
    finally:
        await rest_client.close()