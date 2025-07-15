"""
eBay Taxonomy API tools for dynamic category management.

Provides access to eBay's category hierarchy, category suggestions, and item aspects.
This replaces static category data with live, up-to-date information from eBay.
"""
from typing import Dict, Any, Optional, List
from fastmcp import Context
from pydantic import BaseModel, Field, field_validator, ConfigDict
from datetime import datetime

from api.oauth import OAuthManager, OAuthConfig, OAuthScopes
from api.rest_client import EbayRestClient, RestConfig
from api.errors import EbayApiError, ValidationError as ApiValidationError
from data_types import success_response, error_response, ErrorCode
from lootly_server import mcp


class CategoryTreeInput(BaseModel):
    """Input validation for category tree operations."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    category_tree_id: str = Field(..., description="Category tree ID (e.g., '0' for US)")
    category_id: Optional[str] = Field(None, description="Specific category ID to retrieve")
    
    @field_validator('category_tree_id')
    @classmethod
    def validate_tree_id(cls, v):
        if not v or not v.strip():
            raise ValueError("Category tree ID cannot be empty")
        return v.strip()


class CategorySuggestionsInput(BaseModel):
    """Input validation for category suggestions."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    category_tree_id: str = Field(..., description="Category tree ID")
    query: str = Field(..., min_length=1, max_length=350, description="Search query")
    
    @field_validator('query')
    @classmethod
    def validate_query(cls, v):
        if not v or not v.strip():
            raise ValueError("Query cannot be empty")
        return v.strip()


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


# Static fallback data for when API is not available
STATIC_CATEGORY_DATA = {
    "default_tree_id": "0",  # US marketplace
    "major_categories": [
        {"category_id": "1", "category_name": "Collectibles", "level": 1, "leaf": False},
        {"category_id": "267", "category_name": "Books, Movies & Music", "level": 1, "leaf": False},
        {"category_id": "11450", "category_name": "Clothing, Shoes & Accessories", "level": 1, "leaf": False},
        {"category_id": "58058", "category_name": "Computers/Tablets & Networking", "level": 1, "leaf": False},
        {"category_id": "293", "category_name": "Consumer Electronics", "level": 1, "leaf": False},
        {"category_id": "11700", "category_name": "Home & Garden", "level": 1, "leaf": False},
        {"category_id": "281", "category_name": "Jewelry & Watches", "level": 1, "leaf": False},
        {"category_id": "888", "category_name": "Sporting Goods", "level": 1, "leaf": False},
        {"category_id": "220", "category_name": "Toys & Hobbies", "level": 1, "leaf": False},
        {"category_id": "131090", "category_name": "Video Games & Consoles", "level": 1, "leaf": False}
    ]
}


def _convert_category_node(node: Dict[str, Any]) -> Dict[str, Any]:
    """Convert API category node to our format."""
    return {
        "category_id": node.get("categoryId"),
        "category_name": node.get("categoryName"),
        "level": node.get("categoryTreeNodeLevel", 1),
        "leaf": node.get("leafCategory", False),
        "parent_id": node.get("parentCategoryId"),
        "child_count": len(node.get("childCategoryTreeNodes", [])),
        "has_children": len(node.get("childCategoryTreeNodes", [])) > 0
    }


def _convert_category_subtree(subtree: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Convert API category subtree to flat list."""
    categories = []
    
    def process_node(node: Dict[str, Any], parent_id: Optional[str] = None):
        # Convert current node
        category = _convert_category_node(node)
        if parent_id:
            category["parent_id"] = parent_id
        categories.append(category)
        
        # Process children
        for child in node.get("childCategoryTreeNodes", []):
            process_node(child, node.get("categoryId"))
    
    process_node(subtree)
    return categories


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
    Get the complete category tree or a specific category subtree.
    
    Retrieves the hierarchical category structure from eBay's Taxonomy API.
    Can get the entire tree or a specific subtree starting from a category.
    
    Args:
        category_tree_id: Category tree ID (default "0" for US)
        category_id: Optional category ID to get subtree (omit for full tree)
        ctx: MCP context
    
    Returns:
        JSON response with category tree structure
    """
    await ctx.info(f"Getting category tree {category_tree_id}" + 
                  (f" starting from {category_id}" if category_id else ""))
    await ctx.report_progress(0.1, "Validating parameters...")
    
    # Check credentials
    if not mcp.config.app_id or not mcp.config.cert_id:
        await ctx.info("Using static category data - set credentials for live data")
        return success_response(
            data={
                "category_tree_id": category_tree_id,
                "categories": STATIC_CATEGORY_DATA["major_categories"],
                "total_categories": len(STATIC_CATEGORY_DATA["major_categories"]),
                "data_source": "static_fallback",
                "note": "Live category data requires eBay API credentials"
            },
            message="Using static category data"
        ).to_json_string()
    
    # Validate input
    try:
        input_data = CategoryTreeInput(
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
        await ctx.report_progress(0.3, "Fetching category tree from eBay...")
        
        # Build endpoint
        if input_data.category_id:
            endpoint = f"/commerce/taxonomy/v1/category_tree/{input_data.category_tree_id}/get_category_subtree"
            params = {"category_id": input_data.category_id}
        else:
            endpoint = f"/commerce/taxonomy/v1/category_tree/{input_data.category_tree_id}"
            params = {}
        
        # Make API request
        response = await rest_client.get(
            endpoint,
            params=params,
            scope=OAuthScopes.COMMERCE_TAXONOMY
        )
        
        await ctx.report_progress(0.8, "Processing category data...")
        
        # Parse response
        if input_data.category_id:
            # Subtree response
            categories = _convert_category_subtree(response)
        else:
            # Full tree response
            root_node = response.get("rootCategoryNode", {})
            categories = _convert_category_subtree(root_node)
        
        # Build metadata
        metadata = {
            "category_tree_id": input_data.category_tree_id,
            "category_tree_version": response.get("categoryTreeVersion"),
            "applicable_marketplace_ids": response.get("applicableMarketplaceIds", []),
            "total_categories": len(categories),
            "data_source": "live_api",
            "fetched_at": datetime.now().isoformat()
        }
        
        await ctx.report_progress(1.0, "Complete")
        await ctx.info(f"Retrieved {len(categories)} categories")
        
        return success_response(
            data={
                "categories": categories,
                "metadata": metadata,
                "query": {
                    "category_tree_id": input_data.category_tree_id,
                    "category_id": input_data.category_id,
                    "subtree_only": bool(input_data.category_id)
                }
            },
            message=f"Retrieved {len(categories)} categories from tree {input_data.category_tree_id}"
        ).to_json_string()
        
    except EbayApiError as e:
        await ctx.error(f"eBay API error: {str(e)}")
        return error_response(
            ErrorCode.EXTERNAL_API_ERROR,
            str(e),
            {"status_code": e.status_code, "category_tree_id": category_tree_id}
        ).to_json_string()
    except Exception as e:
        await ctx.error(f"Failed to get category tree: {str(e)}")
        return error_response(
            ErrorCode.INTERNAL_ERROR,
            f"Failed to get category tree: {str(e)}"
        ).to_json_string()
    finally:
        await rest_client.close()


@mcp.tool
async def get_category_suggestions(
    ctx: Context,
    query: str,
    category_tree_id: str = "0"
) -> str:
    """
    Get category suggestions for a search query.
    
    Suggests the most appropriate categories for listing an item based on
    keywords or product description.
    
    Args:
        query: Search query or item description
        category_tree_id: Category tree ID (default "0" for US)
        ctx: MCP context
    
    Returns:
        JSON response with suggested categories
    """
    await ctx.info(f"Getting category suggestions for: {query}")
    await ctx.report_progress(0.1, "Validating query...")
    
    # Check credentials
    if not mcp.config.app_id or not mcp.config.cert_id:
        # Return basic suggestions based on common patterns
        suggestions = []
        query_lower = query.lower()
        
        # Simple keyword matching for fallback
        if any(word in query_lower for word in ['iphone', 'android', 'phone', 'smartphone']):
            suggestions.append({
                "category_id": "9355",
                "category_name": "Cell Phones & Smartphones",
                "relevancy": 95,
                "path": "Electronics > Cell Phones & Accessories > Cell Phones & Smartphones"
            })
        elif any(word in query_lower for word in ['laptop', 'computer', 'desktop', 'pc']):
            suggestions.append({
                "category_id": "177",
                "category_name": "Computers & Tablets",
                "relevancy": 90,
                "path": "Computers/Tablets & Networking > Laptops & Netbooks"
            })
        elif any(word in query_lower for word in ['book', 'novel', 'textbook']):
            suggestions.append({
                "category_id": "267",
                "category_name": "Books",
                "relevancy": 85,
                "path": "Books, Movies & Music > Books"
            })
        else:
            # Generic suggestions
            suggestions.append({
                "category_id": "1",
                "category_name": "Collectibles",
                "relevancy": 50,
                "path": "Collectibles"
            })
        
        return success_response(
            data={
                "suggestions": suggestions,
                "query": query,
                "category_tree_id": category_tree_id,
                "data_source": "static_pattern_matching",
                "note": "Set eBay API credentials for AI-powered category suggestions"
            },
            message=f"Found {len(suggestions)} category suggestions (static)"
        ).to_json_string()
    
    # Validate input
    try:
        input_data = CategorySuggestionsInput(
            category_tree_id=category_tree_id,
            query=query
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
        await ctx.report_progress(0.3, "Getting AI category suggestions...")
        
        # Make API request
        response = await rest_client.get(
            f"/commerce/taxonomy/v1/category_tree/{input_data.category_tree_id}/get_category_suggestions",
            params={"q": input_data.query},
            scope=OAuthScopes.COMMERCE_TAXONOMY
        )
        
        await ctx.report_progress(0.8, "Processing suggestions...")
        
        # Parse suggestions
        suggestions = []
        for suggestion in response.get("categorySuggestions", []):
            category = suggestion.get("category", {})
            suggestions.append({
                "category_id": category.get("categoryId"),
                "category_name": category.get("categoryName"),
                "category_tree_node_level": category.get("categoryTreeNodeLevel"),
                "category_tree_node_ancestors": category.get("categoryTreeNodeAncestors", []),
                "relevancy": suggestion.get("relevancy", "0")
            })
        
        await ctx.report_progress(1.0, "Complete")
        await ctx.info(f"Found {len(suggestions)} category suggestions")
        
        return success_response(
            data={
                "suggestions": suggestions,
                "query": input_data.query,
                "category_tree_id": input_data.category_tree_id,
                "data_source": "live_api",
                "fetched_at": datetime.now().isoformat()
            },
            message=f"Found {len(suggestions)} category suggestions"
        ).to_json_string()
        
    except EbayApiError as e:
        await ctx.error(f"eBay API error: {str(e)}")
        return error_response(
            ErrorCode.EXTERNAL_API_ERROR,
            str(e),
            {"status_code": e.status_code, "query": query}
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
                "fetched_at": datetime.now().isoformat()
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
                "fetched_at": datetime.now().isoformat()
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