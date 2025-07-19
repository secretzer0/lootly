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
from typing import Dict, Any, Union
from fastmcp import Context

from api.oauth import OAuthManager, OAuthConfig
from api.rest_client import EbayRestClient, RestConfig
from api.errors import EbayApiError, extract_ebay_error_details
from data_types import success_response, error_response, ErrorCode
from models.browse import BrowseSearchInput, ItemDetailsInput, CategoryBrowseInput
from lootly_server import mcp



# CONVERSION FUNCTIONS

def _build_search_params(input_data: BrowseSearchInput) -> Dict[str, Any]:
    """Convert Pydantic model to Browse API search parameters."""
    params = {
        "q": input_data.q,
        "limit": input_data.limit,
        "offset": input_data.offset,
        "sort": input_data.sort
    }
    
    # Build filter string
    filters = []
    
    if input_data.categoryIds:
        filters.append(f"categoryIds:{{{input_data.categoryIds}}}")
    
    if input_data.priceMin is not None or input_data.priceMax is not None:
        price_filter = "price:["
        price_filter += str(input_data.priceMin) if input_data.priceMin is not None else "*"
        price_filter += ".."
        price_filter += str(input_data.priceMax) if input_data.priceMax is not None else "*"
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
            "itemId": item_summary.get("itemId"),
            "title": item_summary.get("title"),
            "price": item_summary.get("price", {}),
            "condition": item_summary.get("condition"),
            "seller": item_summary.get("seller", {}),
            "itemLocation": item_summary.get("itemLocation", {}),
            "shippingOptions": item_summary.get("shippingOptions", []),
            "itemWebUrl": item_summary.get("itemWebUrl"),
            "image": item_summary.get("image", {}),
            "categories": item_summary.get("categories", [])
        }
        
        # Add computed fields
        formatted_item["freeShipping"] = any(
            opt.get("shippingCost", {}).get("value") == "0.0"
            for opt in formatted_item["shippingOptions"]
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
        "itemId": item_data.get("itemId"),
        "title": item_data.get("title"),
        "subtitle": item_data.get("shortDescription"),
        "description": item_data.get("description"),
        "price": item_data.get("price", {}),
        "condition": item_data.get("condition"),
        "conditionDescription": item_data.get("conditionDescription"),
        "seller": item_data.get("seller", {}),
        "itemLocation": item_data.get("itemLocation", {}),
        "shippingOptions": item_data.get("shippingOptions", []),
        "itemWebUrl": item_data.get("itemWebUrl"),
        "images": item_data.get("image", {}),
        "additionalImages": item_data.get("additionalImages", []),
        "categories": item_data.get("categories", []),
        "brand": item_data.get("brand"),
        "mpn": item_data.get("mpn"),
        "gtin": item_data.get("gtin"),
        "estimatedAvailabilities": item_data.get("estimatedAvailabilities", []),
        "returnTerms": item_data.get("returnTerms", {}),
        "product": item_data.get("product", {}),
        "localPickup": item_data.get("localPickup", False),
        "availableCoupons": item_data.get("availableCoupons", False),
        "addonServices": item_data.get("addonServices", [])
    }
    
    # Add computed fields
    formatted["freeShipping"] = any(
        opt.get("shippingCost", {}).get("value") == "0.0"
        for opt in formatted["shippingOptions"]
    )
    
    # Get quantity if available
    est_avail = formatted["estimatedAvailabilities"]
    if est_avail:
        formatted["quantity_available"] = est_avail[0].get("estimatedAvailableQuantity")
    
    return formatted


# MCP TOOLS - Using Pydantic Models


@mcp.tool
async def search_items(
    ctx: Context,
    search_input: Union[BrowseSearchInput, str, Dict[str, Any]]
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
    # Handle JSON string or dict input for MCP compatibility
    if isinstance(search_input, (str, dict)):
        from utils.input_converter import parse_json_string_parameter, preprocess_llm_json, COMMON_FIELD_SPECS
        await ctx.info("Preprocessing input for MCP compatibility...")
        
        # Parse JSON string if needed
        if isinstance(search_input, str):
            parsed_data = parse_json_string_parameter(search_input, 'search_input')
        else:
            parsed_data = search_input
        
        # Apply field preprocessing
        field_specs = {
            'conditions': COMMON_FIELD_SPECS['conditions'],
            'category_ids': COMMON_FIELD_SPECS['category_ids'],
            'sellers': COMMON_FIELD_SPECS['sellers']
        }
        processed_data = preprocess_llm_json(parsed_data, field_specs)
        
        # Create validated pydantic model
        search_input = BrowseSearchInput(**processed_data)
    
    await ctx.info(f"Searching eBay for: {search_input.q}")
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
        response_body = response["body"]
        
        await ctx.report_progress(0.8, "Processing search results...")
        
        # Format response
        formatted_response = _format_search_response(response_body)
        
        await ctx.report_progress(1.0, "Complete")
        await ctx.info(f"Found {formatted_response['total']} items, returning {len(formatted_response['items'])}")
        
        return success_response(
            data=formatted_response,
            message=f"Successfully searched for '{search_input.q}'"
        ).to_json_string()
        
    except EbayApiError as e:
        # Log comprehensive error details
        await ctx.error(f"eBay API error: {e.get_comprehensive_message()}")
        
        # Return full error details in response
        return error_response(
            ErrorCode.EXTERNAL_API_ERROR,
            e.get_comprehensive_message(),
            extract_ebay_error_details(e)
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
    details_input: Union[ItemDetailsInput, str, Dict[str, Any]]
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
    # Handle JSON string or dict input for MCP compatibility
    if isinstance(details_input, (str, dict)):
        from utils.input_converter import parse_json_string_parameter
        await ctx.info("Preprocessing input for MCP compatibility...")
        
        # Parse JSON string if needed
        if isinstance(details_input, str):
            parsed_data = parse_json_string_parameter(details_input, 'details_input')
        else:
            parsed_data = details_input
        
        # Create validated pydantic model
        details_input = ItemDetailsInput(**parsed_data)
    
    await ctx.info(f"Getting details for item: {details_input.itemId}")
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
        if details_input.includeDescription:
            params["fieldgroups"] = "PRODUCT,ADDITIONAL_SELLER_DETAILS"
        else:
            params["fieldgroups"] = "COMPACT"
        
        # Make API request - Browse API uses client credentials with api_scope
        response = await rest_client.get(
            f"/buy/browse/v1/item/{details_input.itemId}",
            params=params
        )
        response_body = response["body"]
        
        await ctx.report_progress(0.8, "Processing item details...")
        
        # Format response
        formatted_response = _format_item_details_response(response_body)
        
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
                f"Item {details_input.itemId} not found",
                extract_ebay_error_details(e)
            ).to_json_string()
        
        # Return full error details in response
        return error_response(
            ErrorCode.EXTERNAL_API_ERROR,
            e.get_comprehensive_message(),
            extract_ebay_error_details(e)
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
    category_input: Union[CategoryBrowseInput, str, Dict[str, Any]]
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
    # Handle JSON string or dict input for MCP compatibility
    if isinstance(category_input, (str, dict)):
        from utils.input_converter import parse_json_string_parameter
        await ctx.info("Preprocessing input for MCP compatibility...")
        
        # Parse JSON string if needed
        if isinstance(category_input, str):
            parsed_data = parse_json_string_parameter(category_input, 'category_input')
        else:
            parsed_data = category_input
        
        # Create validated pydantic model
        category_input = CategoryBrowseInput(**parsed_data)
    
    await ctx.info(f"Browsing category: {category_input.categoryId}")
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
        # For category browsing, we need a more specific query to avoid "too large" errors
        search_input = BrowseSearchInput(
            q="item",  # Generic query for category browsing
            categoryIds=category_input.categoryId,
            sort=category_input.sort,
            limit=category_input.limit,
            offset=category_input.offset,
            priceMin=category_input.priceMin,
            priceMax=category_input.priceMax
        )
        
        # Convert to API parameters
        params = _build_search_params(search_input)
        
        # Make API request - Browse API uses client credentials with api_scope
        response = await rest_client.get(
            "/buy/browse/v1/item_summary/search",
            params=params
        )
        response_body = response["body"]
        
        await ctx.report_progress(0.8, "Processing category results...")
        
        # Format response
        formatted_response = _format_search_response(response_body)
        
        await ctx.report_progress(1.0, "Complete")
        await ctx.info(f"Found {formatted_response['total']} items in category")
        
        return success_response(
            data=formatted_response,
            message=f"Successfully browsed category {category_input.categoryId}"
        ).to_json_string()
        
    except EbayApiError as e:
        # Log comprehensive error details
        await ctx.error(f"eBay API error: {e.get_comprehensive_message()}")
        
        # Return full error details in response
        return error_response(
            ErrorCode.EXTERNAL_API_ERROR,
            e.get_comprehensive_message(),
            extract_ebay_error_details(e)
        ).to_json_string()
    except Exception as e:
        await ctx.error(f"Failed to browse category: {str(e)}")
        return error_response(
            ErrorCode.INTERNAL_ERROR,
            f"Failed to browse category: {str(e)}"
        ).to_json_string()
    finally:
        await rest_client.close()