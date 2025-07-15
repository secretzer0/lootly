"""eBay Finding API tools for searching items."""
from typing import Dict, Any, Optional, List
from fastmcp import Context
from data_types import success_response, error_response, ErrorCode, validate_tool_input
from logging_config import log_performance
from pydantic import BaseModel, Field
from api.ebay_client import EbayApiClient
from lootly_server import mcp


class SearchItemsInput(BaseModel):
    """Input model for search_items tool."""
    keywords: str = Field(..., min_length=1, description="Search keywords")
    category_id: Optional[str] = Field(None, description="eBay category ID to filter by")
    min_price: Optional[float] = Field(None, description="Minimum price in USD")
    max_price: Optional[float] = Field(None, description="Maximum price in USD")
    condition: Optional[str] = Field(None, description="Item condition: New, Used, Refurbished")
    sort_order: Optional[str] = Field(
        "BestMatch",
        description="Sort order: BestMatch, PricePlusShippingLowest, PricePlusShippingHighest, CurrentPriceHighest, EndTimeSoonest"
    )
    page_number: int = Field(1, description="Page number for pagination")
    page_size: int = Field(50, description="Number of items per page (max 100)")


@mcp.tool
async def search_items(
    keywords: str,
    category_id: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    condition: Optional[str] = None,
    sort_order: str = "BestMatch",
    page_number: int = 1,
    page_size: int = 50,
    *,
    ctx: Context
) -> str:
    """
    Search for items on eBay using keywords and filters.
    
    This tool searches the eBay marketplace for items matching your criteria.
    You can filter by category, price range, condition, and sort the results.
    
    Args:
        keywords: Search terms (e.g., "vintage camera", "iPhone 15")
        category_id: eBay category ID to filter results
        min_price: Minimum price filter in USD
        max_price: Maximum price filter in USD
        condition: Item condition filter (New, Used, Refurbished)
        sort_order: How to sort results
        page_number: Page number for pagination (starts at 1)
        page_size: Number of items per page (max 100)
        ctx: MCP context for logging
    
    Returns:
        JSON response with search results including items, pagination info, and search metadata
    """
    # Get server instance from global mcp
    from lootly_server import mcp
    
    await ctx.info(f"Searching eBay for: {keywords}")
    await ctx.report_progress(0.1, "Validating search parameters...")
    
    try:
        # Check if credentials are available
        if not mcp.config.app_id:
            return success_response(
                data={
                    "items": [],
                    "pagination": {
                        "page": page_number,
                        "page_size": 0,
                        "total_items": 0,
                        "total_pages": 0,
                        "has_next": False
                    },
                    "search_params": {
                        "keywords": keywords,
                        "filters_applied": {}
                    },
                    "note": "eBay API credentials not configured. To search eBay items, please set EBAY_APP_ID environment variable."
                },
                message="eBay API credentials not available - see note for setup instructions"
            ).to_json_string()
        
        # Create client after credential check
        client = EbayApiClient(mcp.config, mcp.logger)
        
        # Validate input
        input_data = validate_tool_input(SearchItemsInput, {
            "keywords": keywords,
            "category_id": category_id,
            "min_price": min_price,
            "max_price": max_price,
            "condition": condition,
            "sort_order": sort_order,
            "page_number": page_number,
            "page_size": page_size
        })
        
        # Validate pagination
        client.validate_pagination(input_data.page_number)
        
        # Build API parameters
        params = {
            "keywords": input_data.keywords,
            "paginationInput": {
                "entriesPerPage": min(input_data.page_size, 100),
                "pageNumber": input_data.page_number
            },
            "sortOrder": input_data.sort_order
        }
        
        # Add optional filters
        if input_data.category_id:
            params["categoryId"] = input_data.category_id
        
        if input_data.min_price or input_data.max_price:
            params["itemFilter"] = []
            if input_data.min_price:
                params["itemFilter"].append({
                    "name": "MinPrice",
                    "value": str(input_data.min_price)
                })
            if input_data.max_price:
                params["itemFilter"].append({
                    "name": "MaxPrice",
                    "value": str(input_data.max_price)
                })
        
        if input_data.condition:
            if "itemFilter" not in params:
                params["itemFilter"] = []
            params["itemFilter"].append({
                "name": "Condition",
                "value": input_data.condition
            })
        
        await ctx.report_progress(0.3, "Searching eBay marketplace...")
        
        # Execute search
        response = await client.execute_with_retry(
            "finding",
            "findItemsAdvanced",
            params
        )
        
        await ctx.report_progress(0.8, "Processing search results...")
        
        # Extract results
        search_result = response.get("searchResult", [{}])[0]
        items = search_result.get("item", [])
        
        # Format items for response
        formatted_items = []
        for item in items:
            formatted_item = {
                "item_id": item.get("itemId", [None])[0],
                "title": item.get("title", [None])[0],
                "price": {
                    "value": float(item.get("sellingStatus", [{}])[0].get("currentPrice", [{}])[0].get("value", 0)),
                    "currency": item.get("sellingStatus", [{}])[0].get("currentPrice", [{}])[0].get("_currencyId", "USD")
                },
                "condition": item.get("condition", [{}])[0].get("conditionDisplayName", [None])[0],
                "listing_type": item.get("listingInfo", [{}])[0].get("listingType", [None])[0],
                "location": item.get("location", [None])[0],
                "shipping": {
                    "cost": float(item.get("shippingInfo", [{}])[0].get("shippingServiceCost", [{}])[0].get("value", 0)),
                    "type": item.get("shippingInfo", [{}])[0].get("shippingType", [None])[0]
                },
                "url": item.get("viewItemURL", [None])[0],
                "image_url": item.get("galleryURL", [None])[0],
                "end_time": item.get("listingInfo", [{}])[0].get("endTime", [None])[0]
            }
            formatted_items.append(formatted_item)
        
        # Get pagination info
        pagination_output = response.get("paginationOutput", [{}])[0]
        total_entries = int(pagination_output.get("totalEntries", [0])[0])
        total_pages = int(pagination_output.get("totalPages", [0])[0])
        
        await ctx.report_progress(1.0, "Search complete")
        await ctx.info(f"Found {len(formatted_items)} items (page {input_data.page_number}/{total_pages})")
        
        return success_response(
            data={
                "items": formatted_items,
                "pagination": {
                    "page": input_data.page_number,
                    "page_size": len(formatted_items),
                    "total_items": total_entries,
                    "total_pages": total_pages,
                    "has_next": input_data.page_number < total_pages
                },
                "search_params": {
                    "keywords": input_data.keywords,
                    "filters_applied": {
                        "category": bool(input_data.category_id),
                        "price_range": bool(input_data.min_price or input_data.max_price),
                        "condition": bool(input_data.condition)
                    }
                }
            },
            message=f"Successfully found {total_entries} items matching '{keywords}'"
        ).to_json_string()
        
    except ValueError as e:
        await ctx.error(f"Invalid search parameters: {str(e)}")
        return error_response(
            ErrorCode.VALIDATION_ERROR,
            str(e)
        ).to_json_string()
    except Exception as e:
        await ctx.error(f"Search failed: {str(e)}")
        mcp.logger.tool_failed("search_items", str(e), 0)
        return error_response(
            ErrorCode.INTERNAL_ERROR,
            f"Failed to search items: {str(e)}"
        ).to_json_string()


@mcp.tool
async def get_search_keywords(
    partial_keyword: str,
    *,
    ctx: Context
) -> str:
    """
    Get keyword suggestions based on partial input.
    
    This tool provides autocomplete suggestions for eBay search keywords,
    helping users find the right search terms.
    
    Args:
        partial_keyword: Partial keyword to get suggestions for
        ctx: MCP context for logging
    
    Returns:
        JSON response with keyword suggestions
    """
    from lootly_server import mcp
    
    await ctx.info(f"Getting keyword suggestions for: {partial_keyword}")
    
    # Check if credentials are available
    if not mcp.config.app_id:
        return success_response(
            data={
                "input": partial_keyword,
                "suggestions": [],
                "note": "eBay API credentials not configured. To get keyword suggestions, please set EBAY_APP_ID environment variable."
            },
            message="eBay API credentials not available - see note for setup instructions"
        ).to_json_string()
    
    # Create client after credential check
    client = EbayApiClient(mcp.config, mcp.logger)
    
    try:
        # Validate input
        if not partial_keyword or len(partial_keyword) < 2:
            return error_response(
                ErrorCode.VALIDATION_ERROR,
                "Keyword must be at least 2 characters long"
            ).to_json_string()
        
        # Execute API call
        params = {"keywords": partial_keyword}
        response = await client.execute_with_retry(
            "finding",
            "getSearchKeywordsRecommendation",
            params
        )
        
        # Extract suggestions
        keywords = response.get("keywords", [])
        suggestions = [kw.get("keyword", [None])[0] for kw in keywords if kw.get("keyword")]
        
        await ctx.info(f"Found {len(suggestions)} keyword suggestions")
        
        return success_response(
            data={
                "input": partial_keyword,
                "suggestions": suggestions
            },
            message=f"Found {len(suggestions)} keyword suggestions"
        ).to_json_string()
        
    except Exception as e:
        await ctx.error(f"Failed to get suggestions: {str(e)}")
        return error_response(
            ErrorCode.INTERNAL_ERROR,
            f"Failed to get keyword suggestions: {str(e)}"
        ).to_json_string()


@mcp.tool
async def find_items_by_category(
    category_id: str,
    sort_order: str = "BestMatch",
    page_number: int = 1,
    page_size: int = 50,
    *,
    ctx: Context
) -> str:
    """
    Browse items within a specific eBay category.
    
    This tool retrieves items from a specific category without requiring search keywords.
    Useful for browsing category listings.
    
    Args:
        category_id: eBay category ID
        sort_order: How to sort results
        page_number: Page number for pagination
        page_size: Number of items per page
        ctx: MCP context for logging
    
    Returns:
        JSON response with items from the category
    """
    from lootly_server import mcp
    
    await ctx.info(f"Browsing category: {category_id}")
    
    # Check if credentials are available
    if not mcp.config.app_id:
        return success_response(
            data={
                "items": [],
                "category_id": category_id,
                "total_items": 0,
                "note": "eBay API credentials not configured. To browse categories, please set EBAY_APP_ID environment variable."
            },
            message="eBay API credentials not available - see note for setup instructions"
        ).to_json_string()
    
    # Create client after credential check
    client = EbayApiClient(mcp.config, mcp.logger)
    
    try:
        # Validate pagination
        client.validate_pagination(page_number)
        
        # Build API parameters
        params = {
            "categoryId": category_id,
            "paginationInput": {
                "entriesPerPage": min(page_size, 100),
                "pageNumber": page_number
            },
            "sortOrder": sort_order
        }
        
        # Execute search
        response = await client.execute_with_retry(
            "finding",
            "findItemsByCategory",
            params
        )
        
        # Extract and format results (similar to search_items)
        search_result = response.get("searchResult", [{}])[0]
        items = search_result.get("item", [])
        
        formatted_items = []
        for item in items:
            formatted_item = {
                "item_id": item.get("itemId", [None])[0],
                "title": item.get("title", [None])[0],
                "price": {
                    "value": float(item.get("sellingStatus", [{}])[0].get("currentPrice", [{}])[0].get("value", 0)),
                    "currency": item.get("sellingStatus", [{}])[0].get("currentPrice", [{}])[0].get("_currencyId", "USD")
                },
                "condition": item.get("condition", [{}])[0].get("conditionDisplayName", [None])[0],
                "url": item.get("viewItemURL", [None])[0],
                "image_url": item.get("galleryURL", [None])[0]
            }
            formatted_items.append(formatted_item)
        
        pagination_output = response.get("paginationOutput", [{}])[0]
        total_entries = int(pagination_output.get("totalEntries", [0])[0])
        
        await ctx.info(f"Found {len(formatted_items)} items in category")
        
        return success_response(
            data={
                "items": formatted_items,
                "category_id": category_id,
                "total_items": total_entries
            },
            message=f"Successfully retrieved {len(formatted_items)} items from category"
        ).to_json_string()
        
    except Exception as e:
        await ctx.error(f"Category browse failed: {str(e)}")
        return error_response(
            ErrorCode.INTERNAL_ERROR,
            f"Failed to browse category: {str(e)}"
        ).to_json_string()


class AdvancedSearchInput(BaseModel):
    """Input model for advanced search."""
    keywords: Optional[str] = Field(None, description="Search keywords")
    category_id: Optional[str] = Field(None, description="Category ID")
    seller_id: Optional[str] = Field(None, description="Seller username")
    min_feedback_score: Optional[int] = Field(None, description="Minimum seller feedback score")
    listing_type: Optional[str] = Field(None, description="Listing type: Auction, BuyItNow, All")
    free_shipping_only: bool = Field(False, description="Only show items with free shipping")
    returns_accepted_only: bool = Field(False, description="Only show items that accept returns")
    authorized_seller_only: bool = Field(False, description="Only show authorized sellers")
    min_quantity: Optional[int] = Field(None, description="Minimum available quantity")
    exclude_keywords: Optional[str] = Field(None, description="Keywords to exclude from results")


@mcp.tool
async def find_items_advanced(
    keywords: Optional[str] = None,
    category_id: Optional[str] = None,
    seller_id: Optional[str] = None,
    min_feedback_score: Optional[int] = None,
    listing_type: Optional[str] = None,
    free_shipping_only: bool = False,
    returns_accepted_only: bool = False,
    authorized_seller_only: bool = False,
    min_quantity: Optional[int] = None,
    exclude_keywords: Optional[str] = None,
    page_number: int = 1,
    *,
    ctx: Context
) -> str:
    """
    Perform advanced search with multiple filter criteria.
    
    This tool provides access to eBay's advanced search capabilities with
    extensive filtering options.
    
    Args:
        keywords: Search keywords (optional if category_id provided)
        category_id: Category to search within
        seller_id: Specific seller to search
        min_feedback_score: Minimum seller feedback score
        listing_type: Type of listing (Auction, BuyItNow, All)
        free_shipping_only: Filter for free shipping
        returns_accepted_only: Filter for returns accepted
        authorized_seller_only: Filter for authorized sellers
        min_quantity: Minimum available quantity
        exclude_keywords: Keywords to exclude
        page_number: Page number for results
        ctx: MCP context for logging
    
    Returns:
        JSON response with filtered search results
    """
    from lootly_server import mcp
    
    await ctx.info("Performing advanced search with filters")
    
    # Check if credentials are available
    if not mcp.config.app_id:
        return success_response(
            data={
                "items": [],
                "filters_applied": 0,
                "total_results": 0,
                "note": "eBay API credentials not configured. To perform advanced searches, please set EBAY_APP_ID environment variable."
            },
            message="eBay API credentials not available - see note for setup instructions"
        ).to_json_string()
    
    # Create client after credential check
    client = EbayApiClient(mcp.config, mcp.logger)
    
    try:
        # Validate input
        input_data = validate_tool_input(AdvancedSearchInput, {
            "keywords": keywords,
            "category_id": category_id,
            "seller_id": seller_id,
            "min_feedback_score": min_feedback_score,
            "listing_type": listing_type,
            "free_shipping_only": free_shipping_only,
            "returns_accepted_only": returns_accepted_only,
            "authorized_seller_only": authorized_seller_only,
            "min_quantity": min_quantity,
            "exclude_keywords": exclude_keywords
        })
        
        # Ensure we have either keywords or category
        if not input_data.keywords and not input_data.category_id:
            return error_response(
                ErrorCode.VALIDATION_ERROR,
                "Either keywords or category_id must be provided"
            ).to_json_string()
        
        # Build parameters
        params = {
            "paginationInput": {
                "entriesPerPage": 50,
                "pageNumber": page_number
            }
        }
        
        if input_data.keywords:
            params["keywords"] = input_data.keywords
        if input_data.category_id:
            params["categoryId"] = input_data.category_id
        
        # Build item filters
        item_filters = []
        
        if input_data.seller_id:
            item_filters.append({"name": "Seller", "value": input_data.seller_id})
        if input_data.min_feedback_score:
            item_filters.append({"name": "MinFeedbackScore", "value": str(input_data.min_feedback_score)})
        if input_data.listing_type and input_data.listing_type != "All":
            item_filters.append({"name": "ListingType", "value": input_data.listing_type})
        if input_data.free_shipping_only:
            item_filters.append({"name": "FreeShippingOnly", "value": "true"})
        if input_data.returns_accepted_only:
            item_filters.append({"name": "ReturnsAcceptedOnly", "value": "true"})
        if input_data.authorized_seller_only:
            item_filters.append({"name": "AuthorizedSellerOnly", "value": "true"})
        if input_data.min_quantity:
            item_filters.append({"name": "MinQuantity", "value": str(input_data.min_quantity)})
        if input_data.exclude_keywords:
            item_filters.append({"name": "ExcludeKeywords", "value": input_data.exclude_keywords})
        
        if item_filters:
            params["itemFilter"] = item_filters
        
        # Execute search
        response = await client.execute_with_retry(
            "finding",
            "findItemsAdvanced",
            params
        )
        
        # Format results
        search_result = response.get("searchResult", [{}])[0]
        items = search_result.get("item", [])
        
        formatted_items = []
        for item in items:
            formatted_item = {
                "item_id": item.get("itemId", [None])[0],
                "title": item.get("title", [None])[0],
                "seller": {
                    "username": item.get("sellerInfo", [{}])[0].get("sellerUserName", [None])[0],
                    "feedback_score": int(item.get("sellerInfo", [{}])[0].get("feedbackScore", [0])[0]),
                    "positive_feedback_percent": float(item.get("sellerInfo", [{}])[0].get("positiveFeedbackPercent", [0])[0])
                },
                "price": {
                    "value": float(item.get("sellingStatus", [{}])[0].get("currentPrice", [{}])[0].get("value", 0)),
                    "currency": item.get("sellingStatus", [{}])[0].get("currentPrice", [{}])[0].get("_currencyId", "USD")
                },
                "listing_type": item.get("listingInfo", [{}])[0].get("listingType", [None])[0],
                "url": item.get("viewItemURL", [None])[0]
            }
            formatted_items.append(formatted_item)
        
        filters_applied = len(item_filters)
        await ctx.info(f"Found {len(formatted_items)} items with {filters_applied} filters applied")
        
        return success_response(
            data={
                "items": formatted_items,
                "filters_applied": filters_applied,
                "total_results": int(response.get("paginationOutput", [{}])[0].get("totalEntries", [0])[0])
            },
            message=f"Advanced search completed with {filters_applied} filters"
        ).to_json_string()
        
    except Exception as e:
        await ctx.error(f"Advanced search failed: {str(e)}")
        return error_response(
            ErrorCode.INTERNAL_ERROR,
            f"Failed to perform advanced search: {str(e)}"
        ).to_json_string()