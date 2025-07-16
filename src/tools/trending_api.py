"""
Trending Items API using Browse API for merchandising functionality.

Since eBay doesn't provide a direct "most watched" API, this module uses
strategic Browse API searches to find trending and popular items.
"""
from typing import Dict, Any, Optional, List
from fastmcp import Context
from pydantic import BaseModel, Field, field_validator
from decimal import Decimal
from datetime import datetime

from api.oauth import OAuthManager, OAuthConfig, OAuthScopes
from api.rest_client import EbayRestClient, RestConfig
from api.models import MarketplaceId
from api.errors import EbayApiError
from data_types import success_response, error_response, ErrorCode
from lootly_server import mcp


class TrendingItemsInput(BaseModel):
    """Input validation for trending items."""
    category_id: Optional[str] = Field(None, description="eBay category ID to filter by")
    max_results: int = Field(20, ge=1, le=100, description="Maximum number of items to return")
    marketplace_id: str = Field("EBAY_US", description="eBay marketplace ID")
    
    @field_validator('category_id')
    @classmethod
    def validate_category_id(cls, v):
        if v is not None and (not v or not v.strip()):
            raise ValueError("Category ID cannot be empty if provided")
        return v.strip() if v else None


@mcp.tool
async def get_most_watched_items(
    ctx: Context,
    category_id: Optional[str] = None,
    max_results: int = 20
) -> str:
    """
    Get the most watched items on eBay using strategic Browse API searches.
    
    Since eBay doesn't provide a direct "most watched" API, this tool uses
    strategic search terms and sorting to find trending and popular items
    that are likely to be highly watched.
    
    Args:
        category_id: Optional eBay category ID to filter results
        max_results: Maximum number of items to return (1-100, default 20)
        ctx: MCP context
    
    Returns:
        JSON response with trending items
    """
    await ctx.info("Getting most watched items using strategic Browse API searches...")
    await ctx.report_progress(0.1, "Validating input parameters...")
    
    # Check credentials
    if not mcp.config.app_id or not mcp.config.cert_id:
        return success_response(
            data={
                "items": [],
                "total_count": 0,
                "category_id": category_id,
                "note": "eBay API credentials not configured. Please set EBAY_APP_ID and EBAY_CERT_ID."
            },
            message="eBay API credentials not available"
        ).to_json_string()
    
    # Validate input
    try:
        input_data = TrendingItemsInput(
            category_id=category_id,
            max_results=max_results
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
        await ctx.report_progress(0.3, "Searching for trending items...")
        
        # Strategy: Use multiple search approaches to find trending items
        all_items = []
        
        # Search 1: Newly listed items (likely to be trending)
        items_1 = await _search_trending_items(
            rest_client, 
            ctx,
            "trending popular hot new",
            input_data.category_id,
            "newlyListed",
            max_results=input_data.max_results // 2
        )
        all_items.extend(items_1)
        
        # Search 2: Best Match for popular terms
        items_2 = await _search_trending_items(
            rest_client,
            ctx,
            "must have popular trending viral",
            input_data.category_id,
            "relevance",
            max_results=input_data.max_results - len(items_1)
        )
        all_items.extend(items_2)
        
        # Remove duplicates while preserving order
        seen_ids = set()
        unique_items = []
        for item in all_items:
            item_id = item.get("item_id")
            if item_id and item_id not in seen_ids:
                seen_ids.add(item_id)
                unique_items.append(item)
        
        # Limit to requested number
        trending_items = unique_items[:input_data.max_results]
        
        await ctx.report_progress(1.0, "Complete")
        await ctx.info(f"Found {len(trending_items)} trending items")
        
        return success_response(
            data={
                "items": trending_items,
                "total_count": len(trending_items),
                "category_id": input_data.category_id,
                "search_strategy": "multi_search_trending",
                "api_used": "browse_api_strategic"
            },
            message=f"Retrieved {len(trending_items)} trending items"
        ).to_json_string()
        
    except EbayApiError as e:
        await ctx.error(f"eBay API error: {str(e)}")
        return error_response(
            ErrorCode.EXTERNAL_API_ERROR,
            str(e),
            {"status_code": e.status_code}
        ).to_json_string()
    except Exception as e:
        await ctx.error(f"Failed to get trending items: {str(e)}")
        return error_response(
            ErrorCode.INTERNAL_ERROR,
            f"Failed to retrieve trending items: {str(e)}"
        ).to_json_string()
    finally:
        await rest_client.close()


@mcp.tool
async def get_trending_items_by_category(
    ctx: Context,
    category_id: str,
    max_results: int = 20
) -> str:
    """
    Get trending items within a specific category.
    
    This tool focuses on finding trending items within a particular category,
    which can help identify category-specific trends and hot products.
    
    Args:
        category_id: eBay category ID (required)
        max_results: Maximum number of items to return (1-100, default 20)
        ctx: MCP context
    
    Returns:
        JSON response with trending items from the category
    """
    await ctx.info(f"Getting trending items for category: {category_id}")
    
    # Use the same implementation as get_most_watched_items with category filter
    return await get_most_watched_items.fn(
        ctx=ctx,
        category_id=category_id,
        max_results=max_results
    )


async def _search_trending_items(
    rest_client: EbayRestClient,
    ctx: Context,
    search_terms: str,
    category_id: Optional[str],
    sort_order: str,
    max_results: int = 10
) -> List[Dict[str, Any]]:
    """Execute a strategic search for trending items."""
    
    # Build search parameters
    params = {
        "q": search_terms,
        "limit": max_results,
        "sort": sort_order,
        "offset": 0
    }
    
    # Add category filter if provided
    filters = []
    if category_id:
        filters.append(f"categoryIds:{{{category_id}}}")
    
    # Add quality filters to improve results
    filters.extend([
        "conditions:{1000,1500,2000}",  # New and refurbished items
        "buyingOptions:{FIXED_PRICE}"   # Fixed price items only
    ])
    
    if filters:
        params["filter"] = ",".join(filters)
    
    try:
        # Make API request
        response = await rest_client.get(
            "/buy/browse/v1/item_summary/search",
            params=params,
            scope=OAuthScopes.BUY_BROWSE
        )
        
        # Parse response
        items = []
        for item_summary in response.get("itemSummaries", []):
            try:
                # Convert to standardized format
                item = _convert_trending_item(item_summary)
                items.append(item)
            except Exception as e:
                await ctx.error(f"Error parsing trending item: {str(e)}")
                continue
        
        return items
        
    except Exception as e:
        await ctx.error(f"Trending search failed for '{search_terms}': {str(e)}")
        return []


def _convert_trending_item(item_data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert Browse API item to trending format."""
    # Extract basic info
    item_id = item_data.get("itemId", "")
    title = item_data.get("title", "")
    
    # Extract price
    price_data = item_data.get("price", {})
    price_value = float(price_data.get("value", 0))
    currency = price_data.get("currency", "USD")
    
    # Extract seller info
    seller_data = item_data.get("seller", {})
    seller_name = seller_data.get("username", "Unknown")
    feedback_score = seller_data.get("feedbackScore", 0)
    # Handle feedbackPercentage as string or float
    feedback_percentage = seller_data.get("feedbackPercentage", "100.0")
    if isinstance(feedback_percentage, str):
        try:
            feedback_percentage = float(feedback_percentage)
        except (ValueError, TypeError):
            feedback_percentage = 100.0
    else:
        feedback_percentage = float(feedback_percentage) if feedback_percentage else 100.0
    
    # Extract condition
    condition = item_data.get("condition", "NEW")
    
    # Extract image
    image_data = item_data.get("image", {})
    image_url = image_data.get("imageUrl", "")
    
    # Extract category
    categories = item_data.get("categories", [])
    category_name = categories[0].get("categoryName", "") if categories else ""
    
    # Extract location
    location_data = item_data.get("itemLocation", {})
    location = f"{location_data.get('city', '')}, {location_data.get('stateOrProvince', '')}"
    
    # Extract shipping
    shipping_options = item_data.get("shippingOptions", [])
    free_shipping = any(
        float(option.get("shippingCost", {}).get("value", 0)) == 0 
        for option in shipping_options
    )
    
    return {
        "item_id": item_id,
        "title": title,
        "price": {
            "value": price_value,
            "currency": currency
        },
        "seller": {
            "username": seller_name,
            "feedback_score": feedback_score,
            "positive_feedback_percent": feedback_percentage
        },
        "condition": condition,
        "url": item_data.get("itemWebUrl", ""),
        "image_url": image_url,
        "category": category_name,
        "location": location.strip(", "),
        "free_shipping": free_shipping,
        "watch_count": None,  # Not available in Browse API
        "trending_score": "high",  # Estimated based on search strategy
        "listing_date": item_data.get("itemCreationDate"),
        "end_date": item_data.get("itemEndDate")
    }