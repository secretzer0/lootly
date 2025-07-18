"""
eBay Browse API tools for searching and viewing items.

This module provides MCP tools for searching eBay items using the Browse API.
The Browse API provides access to eBay's item search functionality with advanced
filtering capabilities.

IMPLEMENTATION FOLLOWS: PYDANTIC-FIRST DEVELOPMENT METHODOLOGY
- All API fields included exactly as documented
- Strong typing with enums throughout
- Validation through Pydantic models only
- Zero manual validation code
"""
from typing import Optional, Dict, Any
from decimal import Decimal
from fastmcp import Context
from pydantic import BaseModel, Field, field_validator, ConfigDict

from api.oauth import OAuthManager, OAuthConfig
from api.rest_client import EbayRestClient, RestConfig
from api.errors import EbayApiError
from data_types import success_response, error_response, ErrorCode
from lootly_server import mcp


# PYDANTIC MODELS - API Documentation → Pydantic Models → MCP Tools


class BrowseSearchInput(BaseModel):
    """Complete input validation for Browse API search operations."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    # REQUIRED FIELDS
    query: str = Field(..., min_length=1, max_length=350, description="Search query")
    
    # OPTIONAL FIELDS
    category_ids: Optional[str] = Field(None, description="Comma-separated category IDs")
    price_min: Optional[Decimal] = Field(None, ge=0, description="Minimum price filter")
    price_max: Optional[Decimal] = Field(None, ge=0, description="Maximum price filter")
    conditions: Optional[str] = Field(None, description="Comma-separated condition IDs")
    sellers: Optional[str] = Field(None, description="Comma-separated seller usernames")
    sort: str = Field("relevance", description="Sort order")
    limit: int = Field(50, ge=1, le=200, description="Results per page")
    offset: int = Field(0, ge=0, description="Result offset for pagination")
    
    @field_validator('price_max')
    @classmethod
    def validate_price_range(cls, v, info):
        """Validate price range logic."""
        if v is not None and 'price_min' in info.data:
            price_min = info.data.get('price_min')
            if price_min is not None and v <= price_min:
                raise ValueError("price_max must be greater than price_min")
        return v
    
    @field_validator('sort')
    @classmethod
    def validate_sort_values(cls, v):
        """Validate sort parameter values."""
        valid_sorts = ["relevance", "price", "distance", "newlyListed"]
        if v not in valid_sorts:
            raise ValueError(f"sort must be one of: {', '.join(valid_sorts)}")
        return v


class ItemDetailsInput(BaseModel):
    """Input validation for item details requests."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    item_id: str = Field(..., min_length=1, description="eBay item ID")
    include_description: bool = Field(True, description="Include full item description")
    
    @field_validator('item_id')
    @classmethod
    def validate_item_id(cls, v):
        """Validate item ID format."""
        if not v or len(v.strip()) == 0:
            raise ValueError("item_id cannot be empty")
        return v


class CategoryBrowseInput(BaseModel):
    """Input validation for category browsing."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    category_id: str = Field(..., min_length=1, description="eBay category ID")
    sort: str = Field("relevance", description="Sort order")
    limit: int = Field(50, ge=1, le=200, description="Results per page")
    offset: int = Field(0, ge=0, description="Result offset")
    price_min: Optional[Decimal] = Field(None, ge=0, description="Minimum price filter")
    price_max: Optional[Decimal] = Field(None, ge=0, description="Maximum price filter")
    
    @field_validator('price_max')
    @classmethod
    def validate_price_range(cls, v, info):
        """Validate price range logic."""
        if v is not None and 'price_min' in info.data:
            price_min = info.data.get('price_min')
            if price_min is not None and v <= price_min:
                raise ValueError("price_max must be greater than price_min")
        return v


# CONVERSION FUNCTIONS

def _build_search_params(input_data: BrowseSearchInput) -> Dict[str, Any]:
    """Convert Pydantic model to Browse API search parameters."""
    params = {
        "q": input_data.query,
        "limit": input_data.limit,
        "offset": input_data.offset,
        "sort": input_data.sort
    }
    
    # Build filter string
    filters = []
    
    if input_data.category_ids:
        filters.append(f"categoryIds:{{{input_data.category_ids}}}")
    
    if input_data.price_min is not None or input_data.price_max is not None:
        price_filter = "price:["
        price_filter += str(input_data.price_min) if input_data.price_min is not None else "*"
        price_filter += ".."
        price_filter += str(input_data.price_max) if input_data.price_max is not None else "*"
        price_filter += "]"
        filters.append(price_filter)
    
    if input_data.conditions:
        filters.append(f"conditions:{{{input_data.conditions}}}")
    
    if input_data.sellers:
        filters.append(f"sellers:{{{input_data.sellers}}}")
    
    if filters:
        params["filter"] = ",".join(filters)
    
    return params


def _format_search_response(response: Dict[str, Any]) -> Dict[str, Any]:
    """Format Browse API search response for consistent output."""
    items = []
    
    for item_summary in response.get("itemSummaries", []):
        formatted_item = {
            "item_id": item_summary.get("itemId"),
            "title": item_summary.get("title"),
            "price": item_summary.get("price", {}),
            "condition": item_summary.get("condition"),
            "seller": item_summary.get("seller", {}),
            "item_location": item_summary.get("itemLocation", {}),
            "shipping_options": item_summary.get("shippingOptions", []),
            "item_web_url": item_summary.get("itemWebUrl"),
            "image": item_summary.get("image", {}),
            "categories": item_summary.get("categories", [])
        }
        
        # Add computed fields
        formatted_item["free_shipping"] = any(
            opt.get("shippingCost", {}).get("value") == "0.0"
            for opt in formatted_item["shipping_options"]
        )
        
        items.append(formatted_item)
    
    return {
        "items": items,
        "total": response.get("total", 0),
        "limit": response.get("limit", 0),
        "offset": response.get("offset", 0),
        "refinements": response.get("refinements"),
        "warnings": response.get("warnings", [])
    }


def _format_item_details_response(item_data: Dict[str, Any]) -> Dict[str, Any]:
    """Format Browse API item details response."""
    formatted = {
        "item_id": item_data.get("itemId"),
        "title": item_data.get("title"),
        "subtitle": item_data.get("shortDescription"),
        "description": item_data.get("description"),
        "price": item_data.get("price", {}),
        "condition": item_data.get("condition"),
        "condition_description": item_data.get("conditionDescription"),
        "seller": item_data.get("seller", {}),
        "item_location": item_data.get("itemLocation", {}),
        "shipping_options": item_data.get("shippingOptions", []),
        "item_web_url": item_data.get("itemWebUrl"),
        "images": item_data.get("image", {}),
        "additional_images": item_data.get("additionalImages", []),
        "categories": item_data.get("categories", []),
        "brand": item_data.get("brand"),
        "mpn": item_data.get("mpn"),
        "gtin": item_data.get("gtin"),
        "estimated_availabilities": item_data.get("estimatedAvailabilities", []),
        "return_terms": item_data.get("returnTerms", {}),
        "product": item_data.get("product", {}),
        "local_pickup": item_data.get("localPickup", False),
        "available_coupons": item_data.get("availableCoupons", False),
        "addon_services": item_data.get("addonServices", [])
    }
    
    # Add computed fields
    formatted["free_shipping"] = any(
        opt.get("shippingCost", {}).get("value") == "0.0"
        for opt in formatted["shipping_options"]
    )
    
    # Get quantity if available
    est_avail = formatted["estimated_availabilities"]
    if est_avail:
        formatted["quantity_available"] = est_avail[0].get("estimatedAvailableQuantity")
    
    return formatted


# MCP TOOLS - Using Pydantic Models


@mcp.tool
async def search_items(
    ctx: Context,
    search_input: BrowseSearchInput
) -> str:
    """
    Search for items on eBay using the Browse API.
    
    This tool provides access to eBay's Browse API with advanced filtering
    and sorting capabilities for item search.
    
    Args:
        search_input: Complete search configuration with query and filters
        ctx: MCP context
    
    Returns:
        JSON response with search results and pagination info
    """
    await ctx.info(f"Searching eBay for: {search_input.query}")
    await ctx.report_progress(0.1, "Validating search parameters...")
    
    # Pydantic validation already handled - no manual validation needed!
    
    # Check credentials
    if not mcp.config.app_id or not mcp.config.cert_id:
        return error_response(
            ErrorCode.CONFIGURATION_ERROR,
            "eBay App ID and Cert ID must be configured"
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
        await ctx.report_progress(0.3, "Searching eBay marketplace...")
        
        # Convert Pydantic model to API parameters
        params = _build_search_params(search_input)
        
        # Make API request - Browse API uses client credentials with api_scope
        response = await rest_client.get(
            "/buy/browse/v1/item_summary/search",
            params=params
        )
        
        await ctx.report_progress(0.8, "Processing search results...")
        
        # Format response
        formatted_response = _format_search_response(response)
        
        await ctx.report_progress(1.0, "Complete")
        await ctx.info(f"Found {formatted_response['total']} items, returning {len(formatted_response['items'])}")
        
        return success_response(
            data=formatted_response,
            message=f"Successfully searched for '{search_input.query}'"
        ).to_json_string()
        
    except EbayApiError as e:
        # Log comprehensive error details
        await ctx.error(f"eBay API error: {e.get_comprehensive_message()}")
        
        # Return full error details in response
        return error_response(
            ErrorCode.EXTERNAL_API_ERROR,
            e.get_comprehensive_message(),
            e.get_full_error_details()
        ).to_json_string()
    except Exception as e:
        await ctx.error(f"Failed to search items: {str(e)}")
        return error_response(
            ErrorCode.INTERNAL_ERROR,
            f"Failed to search items: {str(e)}"
        ).to_json_string()
    finally:
        await rest_client.close()


@mcp.tool
async def get_item_details(
    ctx: Context,
    details_input: ItemDetailsInput
) -> str:
    """
    Get detailed information about a specific eBay item.
    
    Retrieves comprehensive details including description, images, shipping,
    seller information, and current status.
    
    Args:
        details_input: Item details request configuration
        ctx: MCP context
    
    Returns:
        JSON response with complete item details
    """
    await ctx.info(f"Getting details for item: {details_input.item_id}")
    await ctx.report_progress(0.1, "Validating item request...")
    
    # Pydantic validation already handled - no manual validation needed!
    
    # Check credentials
    if not mcp.config.app_id or not mcp.config.cert_id:
        return error_response(
            ErrorCode.CONFIGURATION_ERROR,
            "eBay App ID and Cert ID must be configured"
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
        await ctx.report_progress(0.3, "Fetching item details from eBay...")
        
        # Build field groups based on description requirement
        params = {}
        if details_input.include_description:
            params["fieldgroups"] = "PRODUCT,ADDITIONAL_SELLER_DETAILS"
        else:
            params["fieldgroups"] = "COMPACT"
        
        # Make API request - Browse API uses client credentials with api_scope
        response = await rest_client.get(
            f"/buy/browse/v1/item/{details_input.item_id}",
            params=params
        )
        
        await ctx.report_progress(0.8, "Processing item details...")
        
        # Format response
        formatted_response = _format_item_details_response(response)
        
        await ctx.report_progress(1.0, "Complete")
        await ctx.info(f"Retrieved details for: {formatted_response.get('title', 'Unknown')}")
        
        return success_response(
            data=formatted_response,
            message="Successfully retrieved item details"
        ).to_json_string()
        
    except EbayApiError as e:
        # Log comprehensive error details
        await ctx.error(f"eBay API error: {e.get_comprehensive_message()}")
        
        # Handle 404 specially for not found
        if e.status_code == 404:
            return error_response(
                ErrorCode.RESOURCE_NOT_FOUND,
                f"Item {details_input.item_id} not found",
                e.get_full_error_details()
            ).to_json_string()
        
        # Return full error details in response
        return error_response(
            ErrorCode.EXTERNAL_API_ERROR,
            e.get_comprehensive_message(),
            e.get_full_error_details()
        ).to_json_string()
    except Exception as e:
        await ctx.error(f"Failed to get item details: {str(e)}")
        return error_response(
            ErrorCode.INTERNAL_ERROR,
            f"Failed to get item details: {str(e)}"
        ).to_json_string()
    finally:
        await rest_client.close()


@mcp.tool
async def get_items_by_category(
    ctx: Context,
    category_input: CategoryBrowseInput
) -> str:
    """
    Browse items within a specific eBay category.
    
    Retrieves items from a category without requiring search keywords.
    Useful for browsing category listings.
    
    Args:
        category_input: Category browsing configuration
        ctx: MCP context
    
    Returns:
        JSON response with items from the category
    """
    await ctx.info(f"Browsing category: {category_input.category_id}")
    await ctx.report_progress(0.1, "Validating category request...")
    
    # Pydantic validation already handled - no manual validation needed!
    
    # Check credentials
    if not mcp.config.app_id or not mcp.config.cert_id:
        return error_response(
            ErrorCode.CONFIGURATION_ERROR,
            "eBay App ID and Cert ID must be configured"
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
        await ctx.report_progress(0.3, "Browsing category...")
        
        # Use search with category filter and minimal query
        search_input = BrowseSearchInput(
            query=" ",  # Minimal query for category browsing
            category_ids=category_input.category_id,
            sort=category_input.sort,
            limit=category_input.limit,
            offset=category_input.offset,
            price_min=category_input.price_min,
            price_max=category_input.price_max
        )
        
        # Convert to API parameters
        params = _build_search_params(search_input)
        
        # Make API request - Browse API uses client credentials with api_scope
        response = await rest_client.get(
            "/buy/browse/v1/item_summary/search",
            params=params
        )
        
        await ctx.report_progress(0.8, "Processing category results...")
        
        # Format response
        formatted_response = _format_search_response(response)
        
        await ctx.report_progress(1.0, "Complete")
        await ctx.info(f"Found {formatted_response['total']} items in category")
        
        return success_response(
            data=formatted_response,
            message=f"Successfully browsed category {category_input.category_id}"
        ).to_json_string()
        
    except EbayApiError as e:
        # Log comprehensive error details
        await ctx.error(f"eBay API error: {e.get_comprehensive_message()}")
        
        # Return full error details in response
        return error_response(
            ErrorCode.EXTERNAL_API_ERROR,
            e.get_comprehensive_message(),
            e.get_full_error_details()
        ).to_json_string()
    except Exception as e:
        await ctx.error(f"Failed to browse category: {str(e)}")
        return error_response(
            ErrorCode.INTERNAL_ERROR,
            f"Failed to browse category: {str(e)}"
        ).to_json_string()
    finally:
        await rest_client.close()