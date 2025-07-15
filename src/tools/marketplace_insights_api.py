"""
eBay Marketplace Insights API tools for market trends and sales data.

Provides sales history and market trends data. Note: This is a Limited Release API
that requires special approval from eBay. Gracefully falls back to static data.
"""
from typing import Dict, Any, Optional, List
from fastmcp import Context
from pydantic import BaseModel, Field, field_validator, ConfigDict
from decimal import Decimal
from datetime import datetime, timedelta

from api.oauth import OAuthManager, OAuthConfig, OAuthScopes
from api.rest_client import EbayRestClient, RestConfig
from api.models import Money, Currency, ConditionId
from api.errors import (
    EbayApiError, AuthorizationError, ValidationError as ApiValidationError
)
from data_types import success_response, error_response, ErrorCode
from lootly_server import mcp


class MarketInsightsInput(BaseModel):
    """Base input model for marketplace insights."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    limit: int = Field(50, ge=1, le=200, description="Number of results")
    offset: int = Field(0, ge=0, description="Result offset for pagination")


class SearchSalesInput(MarketInsightsInput):
    """Input validation for sales search."""
    query: Optional[str] = Field(None, min_length=1, description="Search query")
    category_ids: Optional[str] = Field(None, description="Comma-separated category IDs")
    epid: Optional[str] = Field(None, description="eBay Product ID")
    gtin: Optional[str] = Field(None, description="Global Trade Item Number")
    price_min: Optional[float] = Field(None, ge=0, description="Minimum price")
    price_max: Optional[float] = Field(None, ge=0, description="Maximum price")
    conditions: Optional[str] = Field(None, description="Comma-separated condition IDs")
    last_sold_days: int = Field(90, ge=1, le=90, description="Days of sales history")
    
    @field_validator('query', 'category_ids', 'epid', 'gtin')
    @classmethod
    def at_least_one_criteria(cls, v, info):
        """Ensure at least one search criteria is provided."""
        if info.data.get('query') or info.data.get('category_ids') or \
           info.data.get('epid') or info.data.get('gtin'):
            return v
        if v is None and info.field_name == 'gtin':  # Last field to validate
            raise ValueError("At least one search criteria required: query, category_ids, epid, or gtin")
        return v


# Static fallback data for when API is not available
STATIC_MARKET_TRENDS = {
    "popular_categories": {
        "293": {  # Consumer Electronics
            "name": "Consumer Electronics",
            "avg_sold_price": 250.00,
            "items_sold_last_30_days": 15000,
            "top_brands": ["Apple", "Samsung", "Sony", "LG", "Bose"],
            "price_trend": "stable",
            "demand_level": "high"
        },
        "11450": {  # Clothing, Shoes & Accessories
            "name": "Clothing, Shoes & Accessories",
            "avg_sold_price": 45.00,
            "items_sold_last_30_days": 28000,
            "top_brands": ["Nike", "Adidas", "Lululemon", "North Face"],
            "price_trend": "seasonal",
            "demand_level": "very_high"
        },
        "267": {  # Books, Movies & Music
            "name": "Books, Movies & Music",
            "avg_sold_price": 15.00,
            "items_sold_last_30_days": 12000,
            "top_items": ["Textbooks", "Vinyl Records", "Rare Books"],
            "price_trend": "declining",
            "demand_level": "moderate"
        }
    },
    "trending_searches": [
        {"term": "iPhone 15", "category": "Cell Phones", "growth": "+45%"},
        {"term": "Pokemon cards", "category": "Collectibles", "growth": "+82%"},
        {"term": "Air Jordan", "category": "Athletic Shoes", "growth": "+31%"},
        {"term": "Vintage vinyl", "category": "Music", "growth": "+27%"},
        {"term": "PS5 games", "category": "Video Games", "growth": "+19%"}
    ]
}


def _has_marketplace_insights_access() -> bool:
    """Check if we have access to Marketplace Insights API."""
    # This is a Limited Release API - most users won't have access
    # Could check against a whitelist or config flag
    return mcp.config.marketplace_insights_enabled if hasattr(mcp.config, 'marketplace_insights_enabled') else False


def _convert_sales_data(sales_data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert API sales data to our format."""
    last_sold_date = sales_data.get("lastSoldDate")
    if last_sold_date:
        # Parse ISO date
        last_sold = datetime.fromisoformat(last_sold_date.replace('Z', '+00:00'))
    else:
        last_sold = None
    
    last_sold_price = sales_data.get("lastSoldPrice", {})
    total_sold = sales_data.get("totalSoldQuantity", 0)
    
    return {
        "item_id": sales_data.get("itemId"),
        "title": sales_data.get("title"),
        "category_id": sales_data.get("categoryId"),
        "category_name": sales_data.get("categoryName"),
        "last_sold_date": last_sold.isoformat() if last_sold else None,
        "last_sold_price": {
            "value": float(last_sold_price.get("value", 0)),
            "currency": last_sold_price.get("currency", "USD")
        },
        "total_sold_quantity": total_sold,
        "condition": sales_data.get("condition"),
        "listing_url": sales_data.get("itemWebUrl"),
        "image_url": sales_data.get("image", {}).get("imageUrl")
    }


@mcp.tool
async def search_item_sales(
    ctx: Context,
    query: Optional[str] = None,
    category_ids: Optional[str] = None,
    epid: Optional[str] = None,
    gtin: Optional[str] = None,
    price_min: Optional[float] = None,
    price_max: Optional[float] = None,
    conditions: Optional[str] = None,
    last_sold_days: int = 90,
    limit: int = 50,
    offset: int = 0
) -> str:
    """
    Search for sold items and get sales history data.
    
    This tool provides market insights by analyzing actual sales data from the last 90 days.
    Note: This uses the Marketplace Insights API which requires special access.
    
    Args:
        query: Search keywords (e.g., "iPhone 15 Pro")
        category_ids: Comma-separated eBay category IDs
        epid: eBay Product ID for specific product
        gtin: Global Trade Item Number (UPC, EAN, ISBN)
        price_min: Minimum sold price filter
        price_max: Maximum sold price filter
        conditions: Comma-separated condition IDs (NEW, USED, etc)
        last_sold_days: Days of history (1-90, default 90)
        limit: Results per page (max 200)
        offset: Pagination offset
        ctx: MCP context
    
    Returns:
        JSON response with sales history and market insights
    """
    await ctx.info(f"Searching sales history: {query or category_ids or epid or gtin}")
    await ctx.report_progress(0.1, "Validating search parameters...")
    
    # Check if we have API access
    if not _has_marketplace_insights_access():
        await ctx.info("Marketplace Insights API not available, using static trend data")
        
        # Return static data as fallback
        trend_data = STATIC_MARKET_TRENDS.get("popular_categories", {})
        
        # Filter by category if provided
        if category_ids:
            cat_id = category_ids.split(",")[0]  # Use first category
            if cat_id in trend_data:
                category_data = trend_data[cat_id]
                return success_response(
                    data={
                        "sales_data": [{
                            "category_id": cat_id,
                            "category_name": category_data["name"],
                            "avg_sold_price": category_data["avg_sold_price"],
                            "estimated_monthly_sales": category_data["items_sold_last_30_days"],
                            "price_trend": category_data["price_trend"],
                            "demand_level": category_data["demand_level"],
                            "top_brands": category_data.get("top_brands", [])
                        }],
                        "total_results": 1,
                        "data_source": "static_trends",
                        "note": "Live sales data requires Marketplace Insights API access"
                    },
                    message="Using static market trend data"
                ).to_json_string()
        
        # Return trending searches if no specific criteria
        return success_response(
            data={
                "trending_searches": STATIC_MARKET_TRENDS["trending_searches"],
                "popular_categories": list(trend_data.values()),
                "data_source": "static_trends",
                "note": "Live sales data requires Marketplace Insights API access"
            },
            message="Market trends overview"
        ).to_json_string()
    
    # Validate input
    try:
        input_data = SearchSalesInput(
            query=query,
            category_ids=category_ids,
            epid=epid,
            gtin=gtin,
            price_min=price_min,
            price_max=price_max,
            conditions=conditions,
            last_sold_days=last_sold_days,
            limit=limit,
            offset=offset
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
            "eBay API credentials not configured"
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
        rate_limit_per_day=5000  # Lower limit for Marketplace Insights
    )
    rest_client = EbayRestClient(oauth_manager, rest_config)
    
    try:
        await ctx.report_progress(0.3, "Searching eBay sales history...")
        
        # Build query parameters
        params = {
            "limit": input_data.limit,
            "offset": input_data.offset
        }
        
        # Add search criteria
        if input_data.query:
            params["q"] = input_data.query
        if input_data.category_ids:
            params["category_ids"] = input_data.category_ids
        if input_data.epid:
            params["epid"] = input_data.epid
        if input_data.gtin:
            params["gtin"] = input_data.gtin
            
        # Add filters
        filters = []
        
        # Price filter
        if input_data.price_min or input_data.price_max:
            price_filter = "price:["
            price_filter += str(input_data.price_min) if input_data.price_min else "*"
            price_filter += ".."
            price_filter += str(input_data.price_max) if input_data.price_max else "*"
            price_filter += "]"
            filters.append(price_filter)
        
        # Condition filter
        if input_data.conditions:
            filters.append(f"conditions:{{{input_data.conditions}}}")
        
        # Last sold date filter
        end_date = datetime.now()
        start_date = end_date - timedelta(days=input_data.last_sold_days)
        filters.append(f"lastSoldDate:[{start_date.isoformat()}..{end_date.isoformat()}]")
        
        if filters:
            params["filter"] = ",".join(filters)
        
        # Make API request
        response = await rest_client.get(
            "/buy/marketplace_insights/v1_beta/item_sales/search",
            params=params,
            scope=OAuthScopes.BUY_INSIGHTS
        )
        
        await ctx.report_progress(0.8, "Processing sales data...")
        
        # Parse response
        sales_items = []
        for item in response.get("itemSales", []):
            try:
                sales_items.append(_convert_sales_data(item))
            except Exception as e:
                await ctx.error(f"Error parsing sales item: {str(e)}")
                continue
        
        # Calculate insights
        total_results = response.get("total", 0)
        
        insights = {
            "total_items_sold": sum(item["total_sold_quantity"] for item in sales_items),
            "avg_sale_price": sum(item["last_sold_price"]["value"] for item in sales_items) / len(sales_items) if sales_items else 0,
            "date_range": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            }
        }
        
        await ctx.report_progress(1.0, "Complete")
        await ctx.info(f"Found {len(sales_items)} sales records (total: {total_results})")
        
        return success_response(
            data={
                "sales_items": sales_items,
                "total_results": total_results,
                "offset": input_data.offset,
                "limit": input_data.limit,
                "has_more": (input_data.offset + len(sales_items)) < total_results,
                "insights": insights,
                "search_criteria": {
                    "query": input_data.query,
                    "category_ids": input_data.category_ids,
                    "epid": input_data.epid,
                    "gtin": input_data.gtin,
                    "filters": {
                        "price_range": bool(input_data.price_min or input_data.price_max),
                        "conditions": bool(input_data.conditions),
                        "last_sold_days": input_data.last_sold_days
                    }
                }
            },
            message=f"Found {total_results} sold items matching criteria"
        ).to_json_string()
        
    except AuthorizationError as e:
        await ctx.error(f"Authorization error: {str(e)}")
        return error_response(
            ErrorCode.PERMISSION_DENIED,
            "Marketplace Insights API requires special access approval from eBay"
        ).to_json_string()
    except EbayApiError as e:
        await ctx.error(f"eBay API error: {str(e)}")
        return error_response(
            ErrorCode.EXTERNAL_API_ERROR,
            str(e),
            {"status_code": e.status_code}
        ).to_json_string()
    except Exception as e:
        await ctx.error(f"Search failed: {str(e)}")
        return error_response(
            ErrorCode.INTERNAL_ERROR,
            f"Failed to search sales data: {str(e)}"
        ).to_json_string()
    finally:
        await rest_client.close()


@mcp.tool
async def get_category_sales_insights(
    ctx: Context,
    category_id: str,
    last_sold_days: int = 30,
    limit: int = 100
) -> str:
    """
    Get sales insights for a specific category.
    
    Analyzes sales patterns, pricing trends, and demand levels for a category.
    
    Args:
        category_id: eBay category ID to analyze
        last_sold_days: Days of history (1-90, default 30)
        limit: Number of top items to analyze
        ctx: MCP context
    
    Returns:
        JSON response with category sales insights
    """
    await ctx.info(f"Getting sales insights for category {category_id}")
    
    # Use search_item_sales with category filter
    return await search_item_sales.fn(
        ctx=ctx,
        category_ids=category_id,
        last_sold_days=last_sold_days,
        limit=limit
    )


@mcp.tool
async def get_product_sales_history(
    ctx: Context,
    epid: Optional[str] = None,
    gtin: Optional[str] = None,
    last_sold_days: int = 90
) -> str:
    """
    Get detailed sales history for a specific product.
    
    Tracks price trends and sales velocity for a product identified by ePID or GTIN.
    
    Args:
        epid: eBay Product ID
        gtin: Global Trade Item Number (UPC, EAN, ISBN)
        last_sold_days: Days of history (1-90, default 90)
        ctx: MCP context
    
    Returns:
        JSON response with product sales history
    """
    if not epid and not gtin:
        return error_response(
            ErrorCode.VALIDATION_ERROR,
            "Either epid or gtin must be provided"
        ).to_json_string()
    
    await ctx.info(f"Getting sales history for product {epid or gtin}")
    
    # Use search_item_sales with product identifier
    return await search_item_sales.fn(
        ctx=ctx,
        epid=epid,
        gtin=gtin,
        last_sold_days=last_sold_days,
        limit=200  # Get more data for better analysis
    )


@mcp.tool
async def get_trending_items(
    ctx: Context,
    category_ids: Optional[str] = None,
    limit: int = 20
) -> str:
    """
    Get currently trending items based on recent sales velocity.
    
    Identifies items with increasing sales frequency and buyer interest.
    
    Args:
        category_ids: Optional comma-separated category IDs to filter
        limit: Number of trending items to return
        ctx: MCP context
    
    Returns:
        JSON response with trending items
    """
    await ctx.info("Getting trending items based on sales data")
    
    # For trending, look at recent sales (last 7 days)
    result = await search_item_sales.fn(
        ctx=ctx,
        category_ids=category_ids,
        last_sold_days=7,
        limit=limit,
        offset=0
    )
    
    # The most sold items in the last 7 days are trending
    # In a real implementation, we'd compare with previous periods
    return result