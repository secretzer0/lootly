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
from typing import Dict, Any, Union, Optional
from fastmcp import Context

from api.oauth import OAuthManager, OAuthConfig
from api.rest_client import EbayRestClient, RestConfig
from api.errors import EbayApiError, extract_ebay_error_details
from data_types import success_response, error_response, ErrorCode
from models.browse import BrowseSearchInput, ItemDetailsInput
from lootly_server import mcp



# FILTER HELPER FUNCTIONS

def build_price_filter(min_price: Optional[float] = None, max_price: Optional[float] = None) -> str:
    """
    Build a price range filter string.
    
    Examples:
        build_price_filter(10, 50) -> "price:[10..50]"
        build_price_filter(min_price=10) -> "price:[10..]"
        build_price_filter(max_price=50) -> "price:[..50]"
    """
    if min_price is None and max_price is None:
        return ""
    
    min_str = str(min_price) if min_price is not None else ""
    max_str = str(max_price) if max_price is not None else ""
    return f"price:[{min_str}..{max_str}]"


def build_conditions_filter(*conditions: str) -> str:
    """
    Build a conditions filter string.
    
    Example:
        build_conditions_filter("NEW", "LIKE_NEW") -> "conditions:{NEW|LIKE_NEW}"
    """
    if not conditions:
        return ""
    return f"conditions:{{{('|'.join(conditions))}}}"


def build_sellers_filter(*sellers: str) -> str:
    """
    Build a sellers filter string.
    
    Example:
        build_sellers_filter("techstore", "gadgetshop") -> "sellers:{techstore|gadgetshop}"
    """
    if not sellers:
        return ""
    return f"sellers:{{{('|'.join(sellers))}}}"


def combine_filters(*filters: str) -> str:
    """
    Combine multiple filter strings with commas.
    
    Example:
        combine_filters("price:[10..50]", "conditions:{NEW}") -> "price:[10..50],conditions:{NEW}"
    """
    valid_filters = [f for f in filters if f]
    return ",".join(valid_filters)


# CONVERSION FUNCTIONS

def _build_search_params(input_data: BrowseSearchInput) -> Dict[str, Any]:
    """Convert Pydantic model to Browse API search parameters."""
    params = {
        "q": input_data.q,
        "limit": input_data.limit,
        "offset": input_data.offset,
        "sort": input_data.sort.value if hasattr(input_data.sort, 'value') else input_data.sort
    }
    
    # Add category_ids if provided
    if input_data.category_ids:
        params["category_ids"] = input_data.category_ids
    
    # Pass filter string directly if provided
    if input_data.filter:
        params["filter"] = input_data.filter
    
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
    Search for items on eBay using advanced filtering and sorting capabilities.

    This tool provides access to eBay's Browse API search endpoint with support for:
    - Keyword searching with AND/OR logic
    - Category filtering
    - Advanced filter combinations
    - Multiple sort options
    - Pagination support

    Parameters:
        search_input: Search configuration as a JSON object with these fields:
        
        q (required, string): Search keywords - max 300 characters
            - AND search: "iphone ipad" (items containing both)
            - OR search: "(iphone, ipad)" (items containing either)
            - Phrase search: "\"apple iphone\"" (exact phrase)
            
        category_ids (optional, string): Single eBay category ID to filter results
            - Example: "9355" for Cell Phones & Smartphones
            - Must be numeric, only one category allowed
            
        filter (optional, string): Advanced filtering with specific syntax
            Available filters:
            
            price - Filter by price range
                Syntax: price:[min..max], price:[min..], price:[..max]
                Examples:
                    price:[10..50] - Items $10 to $50
                    price:[10..] - Items $10 and above
                    price:[..50] - Items up to $50
                    
            sellers - Filter by specific seller usernames
                Syntax: sellers:{username1|username2|...}
                Example: sellers:{techstore|gadgetshop}
                
            buyingOptions - Filter by listing type
                Syntax: buyingOptions:{FIXED_PRICE|AUCTION|BEST_OFFER|CLASSIFIED_AD}
                Example: buyingOptions:{FIXED_PRICE|BEST_OFFER}
                
            conditions - Filter by item condition
                Syntax: conditions:{NEW|LIKE_NEW|VERY_GOOD|GOOD|ACCEPTABLE|FOR_PARTS_OR_NOT_WORKING}
                Values can also include refurbished conditions:
                    CERTIFIED_REFURBISHED, EXCELLENT_REFURBISHED, VERY_GOOD_REFURBISHED,
                    GOOD_REFURBISHED, SELLER_REFURBISHED
                Example: conditions:{NEW|LIKE_NEW|CERTIFIED_REFURBISHED}
                
            deliveryCountry - Filter by delivery location
                Syntax: deliveryCountry:XX (2-letter ISO country code)
                Example: deliveryCountry:US
                
            pickupCountry/pickupPostalCode - Local pickup filters
                Example: pickupCountry:US,pickupPostalCode:95125
                
            charityOnly - Show only charity listings
                Syntax: charityOnly:true
                
            bidCount - Filter by minimum number of bids (auctions only)
                Syntax: bidCount:{X}
                Example: bidCount:{5} - Items with 5+ bids
                
            Multiple filters: Separate with commas
                Example: filter=price:[10..100],conditions:{NEW},sellers:{techstore}
                
        sort (optional, string): Sort order for results
            Options:
                - BestMatch: eBay's relevance algorithm (default)
                - price: Lowest total price first (item + shipping)
                - -price: Highest total price first
                - newlyListed: Most recently listed first
                - endingSoonest: Auctions ending soonest first
                - distance: Closest items first (requires pickup filters)
            
        limit (optional, integer): Number of results (1-200, default: 50)
        offset (optional, integer): Number of results to skip for pagination (default: 0)

    Returns:
        JSON response containing:
        {
            "success": true,
            "data": {
                "items": [
                    {
                        "itemId": "v1|123456789|0",  // RESTful item identifier
                        "title": "Item title",
                        "price": {"value": "99.99", "currency": "USD"},
                        "condition": "NEW",
                        "seller": {"username": "seller123", "feedbackScore": 100},
                        "itemLocation": {"city": "San Jose", "stateOrProvince": "CA"},
                        "shippingOptions": [...],
                        "itemWebUrl": "https://www.ebay.com/itm/...",
                        "image": {"imageUrl": "..."},
                        "categories": [{"categoryId": "9355", "categoryName": "..."}],
                        "freeShipping": true
                    }
                ],
                "total": 1500,  // Total matching items
                "limit": 50,
                "offset": 0,
                "refinements": {...}  // Available refinement options
            }
        }

    Examples:
        # Search for iPhones under $500
        {
            "q": "iphone",
            "filter": "price:[..500],conditions:{NEW|CERTIFIED_REFURBISHED}",
            "sort": "price",
            "limit": 100
        }
        
        # Search in specific category with seller filter
        {
            "q": "laptop",
            "category_ids": "175672",
            "filter": "sellers:{bestbuy|dell},buyingOptions:{FIXED_PRICE}",
            "sort": "newlyListed"
        }
        
        # Local pickup search sorted by distance
        {
            "q": "furniture",
            "filter": "pickupCountry:US,pickupPostalCode:95125,price:[50..500]",
            "sort": "distance"
        }
        
        # Find auctions with bids ending soon
        {
            "q": "vintage camera",
            "filter": "buyingOptions:{AUCTION},bidCount:{1}",
            "sort": "endingSoonest"
        }

    Notes:
        - Maximum 10,000 items returnable per search
        - Use pagination (offset) to retrieve additional results
        - Filter syntax is case-sensitive for enum values
        - The itemId returned can be used with get_item_details for full information
        - Price sorting includes shipping cost in the calculation
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
        sandbox=mcp.config.sandbox_mode,
        redirect_uri=mcp.config.redirect_uri
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
    Retrieve comprehensive details for a specific eBay item.

    This tool supports both modern RESTful item IDs and legacy item IDs from older
    eBay APIs. The tool automatically detects which type of ID is provided and
    calls the appropriate endpoint.

    Parameters:
        details_input: Item details configuration as a JSON object with:
        
        item_id (required, string): The item identifier - accepts two formats:
        
            1. RESTful Item ID (recommended):
               - Format: v1|{listing_id}|{transaction_id}
               - Examples:
                 * Single SKU: "v1|272662989093|0"
                 * Multi-SKU: "v1|162862654321|422363059871"
               - These IDs are returned by search_items and other Browse API methods
               
            2. Legacy Item ID:
               - Format: Numeric string (10-19 digits)
               - Example: "272662989093"
               - These IDs come from older eBay APIs (Shopping, Finding, Trading)
               - Useful for transitioning from legacy systems

    Returns:
        JSON response containing:
        {
            "success": true,
            "data": {
                "itemId": "v1|272662989093|0",  // Always returns RESTful format
                "title": "Item title",
                "subtitle": "Brief item description",
                "description": "Full HTML description...",
                "price": {"value": "99.99", "currency": "USD"},
                "condition": "NEW",
                "conditionDescription": "Brand new in box",
                "seller": {
                    "username": "seller123",
                    "feedbackScore": 1000,
                    "feedbackPercentage": "99.5"
                },
                "itemLocation": {
                    "city": "San Jose",
                    "stateOrProvince": "CA",
                    "country": "US",
                    "postalCode": "95***"
                },
                "shippingOptions": [
                    {
                        "shippingServiceCode": "USPS Priority Mail",
                        "shippingCost": {"value": "0.00", "currency": "USD"},
                        "estimatedDeliveryDate": "2024-01-15"
                    }
                ],
                "images": {"imageUrl": "..."},          // Primary image
                "additionalImages": [...],              // All other images
                "categories": [
                    {"categoryId": "9355", "categoryName": "Cell Phones & Smartphones"}
                ],
                "brand": "Apple",
                "mpn": "A2342",                        // Manufacturer Part Number
                "gtin": "194252138472",                // Global Trade Item Number
                "returnTerms": {
                    "returnsAccepted": true,
                    "returnPeriod": {"unit": "DAY", "value": 30}
                },
                "estimatedAvailabilities": [{
                    "estimatedAvailableQuantity": 10,
                    "estimatedSoldQuantity": 25
                }],
                "quantity_available": 10,               // Extracted from estimatedAvailabilities
                "localPickup": false,
                "freeShipping": true,
                "itemWebUrl": "https://www.ebay.com/itm/..."
            }
        }

    Examples:
        # Using RESTful item ID from search results
        {
            "item_id": "v1|272662989093|0"
        }
        
        # Using legacy item ID from older systems  
        {
            "item_id": "272662989093"
        }
        
        # Multi-SKU item with specific variation
        {
            "item_id": "v1|162862654321|422363059871"
        }

    Notes:
        - Always prefer RESTful IDs when available (returned by search_items)
        - Legacy IDs are automatically converted to the appropriate API call
        - If using a legacy ID, the response will include the RESTful ID for future use
        - Some fields may be empty depending on what the seller has provided
        - The description field contains full HTML that may need sanitization
        - quantity_available is extracted from estimatedAvailabilities when present
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
    
    await ctx.info(f"Getting details for item: {details_input.item_id}")
    await ctx.report_progress(0.1, "Validating item request...")
    
    # Pydantic validation already handled - no manual validation needed!
    
    # Detect ID format
    is_legacy_id = details_input.item_id.isdigit()
    if is_legacy_id:
        await ctx.info("Detected legacy item ID format")
    
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
        sandbox=mcp.config.sandbox_mode,
        redirect_uri=mcp.config.redirect_uri
    )
    oauth_manager = OAuthManager(oauth_config)
    
    rest_config = RestConfig(
        sandbox=mcp.config.sandbox_mode,
        rate_limit_per_day=mcp.config.rate_limit_per_day
    )
    rest_client = EbayRestClient(oauth_manager, rest_config)
    
    try:
        await ctx.report_progress(0.3, "Fetching item details from eBay...")
        
        # Different endpoints for legacy vs RESTful IDs
        if is_legacy_id:
            # Use legacy endpoint
            params = {
                "legacy_item_id": details_input.item_id,
                "fieldgroups": "PRODUCT,ADDITIONAL_SELLER_DETAILS"
            }
            response = await rest_client.get(
                "/buy/browse/v1/item/get_item_by_legacy_id",
                params=params
            )
        else:
            # Use standard RESTful endpoint
            params = {"fieldgroups": "PRODUCT,ADDITIONAL_SELLER_DETAILS"}
            response = await rest_client.get(
                f"/buy/browse/v1/item/{details_input.item_id}",
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
                f"Item {details_input.item_id} not found",
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

