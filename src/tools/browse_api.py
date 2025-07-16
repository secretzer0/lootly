"""
eBay Browse API tools for searching and viewing items.

Replaces the legacy Finding API with modern REST API implementation.
"""
from typing import Dict, Any, Optional, List
from fastmcp import Context
from pydantic import BaseModel, Field, field_validator, ValidationError as PydanticValidationError
from decimal import Decimal
from datetime import datetime, timezone

from api.oauth import OAuthManager, OAuthConfig, OAuthScopes
from api.rest_client import EbayRestClient, RestConfig
from api.models import (
    Item, SearchResult, Category, Seller,
    Money, Currency, ConditionId, ListingStatus, Location,
    ShippingOption, Image
)
from api.errors import EbayApiError
from data_types import success_response, error_response, ErrorCode
from lootly_server import mcp


class BrowseSearchInput(BaseModel):
    """Input model for browse search."""
    query: str = Field(..., min_length=1, description="Search query")
    category_ids: Optional[str] = Field(None, description="Comma-separated category IDs")
    price_min: Optional[Decimal] = Field(None, ge=0, description="Minimum price")
    price_max: Optional[Decimal] = Field(None, ge=0, description="Maximum price")
    conditions: Optional[str] = Field(None, description="Comma-separated condition IDs (NEW, USED, etc)")
    sellers: Optional[str] = Field(None, description="Comma-separated seller usernames")
    sort: Optional[str] = Field("relevance", description="Sort order: relevance, price, distance, newlyListed")
    limit: int = Field(50, ge=1, le=200, description="Results per page")
    offset: int = Field(0, ge=0, description="Result offset")
    
    @field_validator('price_max')
    @classmethod
    def validate_price_range(cls, v, info):
        if 'price_min' in info.data and v is not None and info.data.get('price_min') is not None:
            if v <= info.data['price_min']:
                raise ValueError("price_max must be greater than price_min")
        return v


@mcp.tool
async def search_items(
    ctx: Context,
    query: str,
    category_ids: Optional[str] = None,
    price_min: Optional[str] = None,
    price_max: Optional[str] = None,
    conditions: Optional[str] = None,
    sellers: Optional[str] = None,
    sort: str = "relevance",
    limit: int = 50,
    offset: int = 0
) -> str:
    """
    Search for items on eBay using the Browse API.
    
    This modern search tool provides access to eBay's Browse API with advanced
    filtering and sorting capabilities.
    
    Args:
        query: Search terms (e.g., "vintage camera", "iPhone 15")
        category_ids: Comma-separated eBay category IDs
        price_min: Minimum price filter (e.g., "100", "50.00")
        price_max: Maximum price filter (e.g., "600", "999.99")
        conditions: Comma-separated condition IDs (NEW, USED, etc)
        sellers: Comma-separated seller usernames
        sort: Sort order (relevance, price, distance, newlyListed)
        limit: Number of results per page (max 200)
        offset: Result offset for pagination
        ctx: MCP context
    
    Returns:
        JSON response with search results and pagination info
        
    Note:
        This tool returns structured data for processing. Please provide the user with a 
        helpful summary of the results (e.g., "Found 5 items, here are the best matches:")
        rather than showing them the raw JSON data.
    """
    await ctx.info(f"🔍 Searching eBay for: {query}")
    await ctx.report_progress(0.1, "Validating search parameters...")
    
    # Check credentials
    if not mcp.config.app_id or not mcp.config.cert_id:
        return success_response(
            data={
                "items": [],
                "total": 0,
                "limit": limit,
                "offset": offset,
                "note": "eBay API credentials not configured. Please set EBAY_APP_ID and EBAY_CERT_ID."
            },
            message="eBay API credentials not available"
        ).to_json_string()
    
    # Validate input
    try:
        input_data = BrowseSearchInput(
            query=query,
            category_ids=category_ids,
            price_min=Decimal(price_min) if price_min else None,
            price_max=Decimal(price_max) if price_max else None,
            conditions=conditions,
            sellers=sellers,
            sort=sort,
            limit=limit,
            offset=offset
        )
    except PydanticValidationError as e:
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
        await ctx.report_progress(0.3, "🌐 Searching eBay marketplace...")
        
        # Build query parameters
        params = {
            "q": input_data.query,
            "limit": input_data.limit,
            "offset": input_data.offset,
            "sort": input_data.sort
        }
        
        # Add filters
        filters = []
        
        if input_data.category_ids:
            filters.append(f"categoryIds:{{{input_data.category_ids}}}")
            
        if input_data.price_min or input_data.price_max:
            price_filter = "price:["
            price_filter += str(input_data.price_min) if input_data.price_min else "*"
            price_filter += ".."
            price_filter += str(input_data.price_max) if input_data.price_max else "*"
            price_filter += "]"
            filters.append(price_filter)
            
        if input_data.conditions:
            filters.append(f"conditions:{{{input_data.conditions}}}")
            
        if input_data.sellers:
            filters.append(f"sellers:{{{input_data.sellers}}}")
            
        if filters:
            params["filter"] = ",".join(filters)
        
        # Make API request
        response = await rest_client.get(
            "/buy/browse/v1/item_summary/search",
            params=params,
            scope=OAuthScopes.BUY_BROWSE
        )
        
        await ctx.report_progress(0.8, "📦 Processing search results...")
        
        # Parse response into models
        items = []
        for item_summary in response.get("itemSummaries", []):
            try:
                # Convert to our Item model
                item = _convert_browse_item(item_summary)
                items.append(item.model_dump())
            except Exception as e:
                await ctx.error(f"Error parsing item: {str(e)}")
                import traceback
                await ctx.error(f"Traceback: {traceback.format_exc()}")
                continue
        
        # Build result
        total = response.get("total", 0)
        result = SearchResult(
            total=total,
            offset=input_data.offset,
            limit=input_data.limit,
            items=[],  # We'll return dicts, not models
            refinements=response.get("refinements")
        )
        
        await ctx.report_progress(1.0, "✅ Search complete")
        await ctx.info(f"📊 Found {len(items)} items (showing {input_data.offset+1}-{input_data.offset+len(items)} of {total})")
        
        return success_response(
            data={
                "items": items,
                "total": total,
                "offset": input_data.offset,
                "limit": input_data.limit,
                "has_more": result.has_more,
                "search_params": {
                    "query": input_data.query,
                    "filters": {
                        "categories": bool(input_data.category_ids),
                        "price_range": bool(input_data.price_min or input_data.price_max),
                        "conditions": bool(input_data.conditions),
                        "sellers": bool(input_data.sellers)
                    }
                }
            },
            message=f"Successfully found {total} items matching '{input_data.query}'. Use this data to provide a helpful summary to the user."
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
            f"Failed to search items: {str(e)}"
        ).to_json_string()
    finally:
        await rest_client.close()


@mcp.tool
async def get_item_details(
    ctx: Context,
    item_id: str,
    include_description: bool = True
) -> str:
    """
    Get detailed information about a specific eBay item.
    
    Retrieves comprehensive details including description, images, shipping,
    seller information, and current status.
    
    Args:
        item_id: eBay item ID (e.g., "v1|123456789|0")
        include_description: Whether to include full description
        ctx: MCP context
    
    Returns:
        JSON response with complete item details
    """
    await ctx.info(f"Getting details for item: {item_id}")
    
    # Check credentials
    if not mcp.config.app_id or not mcp.config.cert_id:
        return success_response(
            data={
                "item_id": item_id,
                "error": "eBay API credentials not configured"
            },
            message="Please set EBAY_APP_ID and EBAY_CERT_ID"
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
        # Build field groups - COMPACT cannot be combined with others
        if include_description:
            fieldgroups = ["PRODUCT", "ADDITIONAL_SELLER_DETAILS"]
        else:
            fieldgroups = ["COMPACT"]
        
        # Make API request
        response = await rest_client.get(
            f"/buy/browse/v1/item/{item_id}",
            params={"fieldgroups": ",".join(fieldgroups)},
            scope=OAuthScopes.BUY_BROWSE
        )
        
        # Convert to our Item model
        item = _convert_browse_item_detail(response)
        
        await ctx.info(f"Retrieved details for: {item.title}")
        
        return success_response(
            data=item.model_dump(),
            message=f"Successfully retrieved item details"
        ).to_json_string()
        
    except EbayApiError as e:
        if e.status_code == 404:
            return error_response(
                ErrorCode.RESOURCE_NOT_FOUND,
                f"Item {item_id} not found"
            ).to_json_string()
        await ctx.error(f"eBay API error: {str(e)}")
        return error_response(
            ErrorCode.EXTERNAL_API_ERROR,
            str(e),
            {"status_code": e.status_code}
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
    category_id: str,
    sort: str = "relevance",
    limit: int = 50,
    offset: int = 0,
    price_min: Optional[float] = None,
    price_max: Optional[float] = None
) -> str:
    """
    Browse items within a specific eBay category.
    
    Retrieves items from a category without requiring search keywords.
    Useful for browsing category listings.
    
    Args:
        category_id: eBay category ID
        sort: Sort order (relevance, price, distance, newlyListed)
        limit: Results per page (max 200)
        offset: Result offset for pagination
        price_min: Optional minimum price filter to narrow results
        price_max: Optional maximum price filter to narrow results
        ctx: MCP context
    
    Returns:
        JSON response with items from the category
    """
    await ctx.info(f"Browsing category: {category_id}")
    
    # For very broad categories, we need to be more specific to avoid "response too large" errors
    # Using just "*" can return too many results
    
    # Strategy: Never use "*" for category browsing - it's always too broad
    # Instead, use a space which matches items but is more restrictive
    # This returns relevant items without overwhelming the API
    query = " "
    
    # Use search_items with category filter
    return await search_items.fn(
        ctx=ctx,
        query=query,
        category_ids=category_id,
        sort=sort,
        limit=limit,
        offset=offset,
        price_min=price_min,
        price_max=price_max
    )


def _condition_string_to_id(condition_str: str) -> ConditionId:
    """Convert condition string to ConditionId enum."""
    condition_map = {
        "NEW": ConditionId.NEW,
        "NEW_OTHER": ConditionId.NEW_OTHER,
        "NEW_WITH_DEFECTS": ConditionId.NEW_WITH_DEFECTS,
        "CERTIFIED_REFURBISHED": ConditionId.CERTIFIED_REFURBISHED,
        "EXCELLENT_REFURBISHED": ConditionId.EXCELLENT_REFURBISHED,
        "VERY_GOOD_REFURBISHED": ConditionId.VERY_GOOD_REFURBISHED,
        "GOOD_REFURBISHED": ConditionId.GOOD_REFURBISHED,
        "USED_EXCELLENT": ConditionId.USED_EXCELLENT,
        "USED_VERY_GOOD": ConditionId.USED_VERY_GOOD,
        "USED_GOOD": ConditionId.USED_GOOD,
        "USED_ACCEPTABLE": ConditionId.USED_ACCEPTABLE,
        "USED": ConditionId.USED_GOOD,  # Default USED mapping
        "FOR_PARTS": ConditionId.FOR_PARTS,
    }
    return condition_map.get(condition_str, ConditionId.NEW)


def _convert_browse_item(item_data: Dict[str, Any]) -> Item:
    """Convert Browse API item summary to our Item model."""
    # Extract price
    price_data = item_data.get("price", {})
    price = Money(
        value=Decimal(price_data.get("value", "0")),
        currency=Currency(price_data.get("currency", "USD"))
    )
    
    # Extract seller
    seller_data = item_data.get("seller", {})
    seller = Seller(
        username=seller_data.get("username", "Unknown"),
        feedback_percentage=seller_data.get("feedbackPercentage"),
        feedback_score=seller_data.get("feedbackScore")
    )
    
    # Extract location
    location_data = item_data.get("itemLocation", {})
    location = Location(
        country=location_data.get("country", "US"),
        city=location_data.get("city"),
        state_or_province=location_data.get("stateOrProvince"),
        postal_code=location_data.get("postalCode")
    )
    
    # Extract primary category
    categories = item_data.get("categories", [])
    if categories:
        primary_category = Category(
            category_id=categories[0]["categoryId"],
            category_name=categories[0]["categoryName"]
        )
    else:
        primary_category = Category(
            category_id="0",
            category_name="Unknown"
        )
    
    # Extract images
    image_data = item_data.get("image", {})
    images = []
    if image_data.get("imageUrl"):
        images.append(Image(
            url=image_data["imageUrl"],
            height=image_data.get("height"),
            width=image_data.get("width")
        ))
    
    # Extract shipping
    shipping_options = []
    shipping_data = item_data.get("shippingOptions", [])
    for opt in shipping_data:
        shipping_cost = opt.get("shippingCost")
        if shipping_cost:
            cost = Money(
                value=Decimal(shipping_cost.get("value", "0")),
                currency=Currency(shipping_cost.get("currency", "USD"))
            )
        else:
            cost = None
            
        shipping_options.append(ShippingOption(
            service_type=opt.get("shippingServiceCode", "Standard"),
            shipping_cost=cost,
            estimated_delivery_date=opt.get("maxEstimatedDeliveryDate"),
            expedited=opt.get("expeditedShipping", False),
            global_shipping=opt.get("type") == "INTERNATIONAL"
        ))
    
    # Build Item model
    return Item(
        item_id=item_data["itemId"],
        title=item_data["title"],
        subtitle=item_data.get("shortDescription"),
        price=price,
        condition_id=_condition_string_to_id(item_data.get("condition", "NEW")),
        images=images,
        primary_image=images[0] if images else None,
        seller=seller,
        item_location=location,
        shipping_options=shipping_options,
        free_shipping=any(opt.shipping_cost and opt.shipping_cost.value == 0 for opt in shipping_options),
        listing_status=ListingStatus.ACTIVE,  # Browse API only returns active items
        item_url=item_data.get("itemWebUrl", ""),
        listing_start_date=item_data.get("itemCreationDate") or datetime.now(timezone.utc).isoformat(),
        primary_category=primary_category
    )


def _convert_browse_item_detail(item_data: Dict[str, Any]) -> Item:
    """Convert Browse API detailed item to our Item model."""
    # Item details API has different structure than search results
    # Extract categories from categoryPath if categories array missing
    categories = item_data.get("categories", [])
    if not categories and item_data.get("categoryIdPath") and item_data.get("categoryPath"):
        # Parse from paths
        cat_ids = item_data["categoryIdPath"].split("|")
        cat_names = item_data["categoryPath"].split("|")
        categories = [{"categoryId": cat_id, "categoryName": cat_name} 
                     for cat_id, cat_name in zip(cat_ids, cat_names)]
        item_data["categories"] = categories
    
    # Ensure we have itemWebUrl if missing
    if not item_data.get("itemWebUrl") and item_data.get("itemId"):
        item_id = item_data["itemId"]
        item_data["itemWebUrl"] = f"https://www.ebay.com/itm/{item_id}"
    
    # Start with basic conversion
    item = _convert_browse_item(item_data)
    
    # Add additional details
    item.description = item_data.get("description")
    
    # Get availability from estimatedAvailabilities
    est_avail = item_data.get("estimatedAvailabilities", [{}])
    if est_avail:
        item.quantity_available = est_avail[0].get("estimatedAvailableQuantity")
    
    item.brand = item_data.get("brand")
    item.mpn = item_data.get("mpn")
    
    # Add all images
    all_images = []
    for img in item_data.get("additionalImages", []):
        all_images.append(Image(
            url=img.get("imageUrl"),
            height=img.get("height"),
            width=img.get("width")
        ))
    if all_images:
        item.images.extend(all_images)
    
    return item


@mcp.tool
async def analyze_seller_performance(
    ctx: Context,
    seller_username: str,
    category_id: Optional[str] = None,
    max_items: int = 50
) -> str:
    """
    Analyze a seller's performance and strategies.
    
    Retrieves and analyzes a seller's listings to understand their strategies,
    pricing patterns, and success indicators for market research.
    
    Args:
        seller_username: eBay seller username
        category_id: Optional category filter
        max_items: Maximum items to analyze (default: 50)
        ctx: MCP context
    
    Returns:
        JSON response with seller performance analysis
    """
    await ctx.info(f"Analyzing seller performance for: {seller_username}")
    await ctx.report_progress(0.1, "Fetching seller listings...")
    
    # Check credentials
    if not mcp.config.app_id or not mcp.config.cert_id:
        return success_response(
            data={
                "seller_username": seller_username,
                "analysis": {
                    "total_listings": 25,
                    "average_price": 49.99,
                    "pricing_strategy": "competitive",
                    "success_indicators": {
                        "feedback_score": 98.5,
                        "estimated_listing_count": 100,
                        "listing_quality": "high"
                    }
                },
                "data_source": "static_analysis",
                "note": "Live seller analysis requires eBay API credentials"
            },
            message="Seller analysis (static data)"
        ).to_json_string()
    
    try:
        # Build search query to find seller's items
        search_result = await search_items.fn(
            ctx=ctx,
            query="*",  # Any item
            sellers=seller_username,
            category_ids=category_id,
            limit=max_items,
            sort="relevance"
        )
        
        # Parse search results
        import json
        search_data = json.loads(search_result)
        
        if search_data["status"] != "success":
            return error_response(
                ErrorCode.EXTERNAL_API_ERROR,
                f"Failed to fetch seller listings: {search_data.get('error_message', 'Unknown error')}"
            ).to_json_string()
        
        items = search_data["data"]["items"]
        
        await ctx.report_progress(0.6, f"Analyzing {len(items)} listings...")
        
        # Analyze seller performance
        analysis = _analyze_seller_data(items, seller_username)
        
        await ctx.report_progress(1.0, "Analysis complete")
        await ctx.info(f"Analyzed {len(items)} listings from {seller_username}")
        
        return success_response(
            data={
                "seller_username": seller_username,
                "category_filter": category_id,
                "items_analyzed": len(items),
                "analysis": analysis,
                "sample_listings": items[:5],  # Include sample for reference
                "analysis_date": datetime.now(timezone.utc).isoformat(),
                "data_source": "browse_api_analysis"
            },
            message=f"Seller performance analysis complete for {seller_username}"
        ).to_json_string()
        
    except Exception as e:
        await ctx.error(f"Failed to analyze seller performance: {str(e)}")
        return error_response(
            ErrorCode.INTERNAL_ERROR,
            f"Failed to analyze seller performance: {str(e)}"
        ).to_json_string()


@mcp.tool
async def find_successful_sellers(
    ctx: Context,
    query: str,
    category_id: Optional[str] = None,
    min_feedback_score: int = 98,
    max_sellers: int = 10
) -> str:
    """
    Find successful sellers in a product category or search term.
    
    Identifies top-performing sellers based on feedback scores, listing quality,
    and other success indicators for competitive analysis.
    
    Args:
        query: Search query or product type
        category_id: Optional category filter
        min_feedback_score: Minimum seller feedback score (default: 98)
        max_sellers: Maximum sellers to analyze (default: 10)
        ctx: MCP context
    
    Returns:
        JSON response with successful seller analysis
    """
    await ctx.info(f"Finding successful sellers for: {query}")
    await ctx.report_progress(0.1, "Searching for listings...")
    
    # Check credentials
    if not mcp.config.app_id or not mcp.config.cert_id:
        return success_response(
            data={
                "query": query,
                "successful_sellers": [
                    {
                        "username": "top_seller_123",
                        "feedback_score": 99.2,
                        "estimated_listings": 150,
                        "success_indicators": ["high_feedback", "competitive_pricing", "fast_shipping"]
                    }
                ],
                "data_source": "static_analysis",
                "note": "Live seller analysis requires eBay API credentials"
            },
            message="Successful sellers analysis (static data)"
        ).to_json_string()
    
    try:
        # Search for items to find sellers
        search_result = await search_items.fn(
            ctx=ctx,
            query=query,
            category_ids=category_id,
            limit=100,  # Get more items to find diverse sellers
            sort="relevance"
        )
        
        # Parse search results
        import json
        search_data = json.loads(search_result)
        
        if search_data["status"] != "success":
            return error_response(
                ErrorCode.EXTERNAL_API_ERROR,
                f"Failed to search items: {search_data.get('error_message', 'Unknown error')}"
            ).to_json_string()
        
        items = search_data["data"]["items"]
        
        await ctx.report_progress(0.6, f"Analyzing {len(items)} listings for successful sellers...")
        
        # Analyze sellers from the items
        successful_sellers = _identify_successful_sellers(items, min_feedback_score, max_sellers)
        
        await ctx.report_progress(1.0, "Analysis complete")
        await ctx.info(f"Identified {len(successful_sellers)} successful sellers")
        
        return success_response(
            data={
                "query": query,
                "category_filter": category_id,
                "items_analyzed": len(items),
                "successful_sellers": successful_sellers,
                "analysis_criteria": {
                    "min_feedback_score": min_feedback_score,
                    "max_sellers": max_sellers
                },
                "analysis_date": datetime.now(timezone.utc).isoformat(),
                "data_source": "browse_api_analysis"
            },
            message=f"Found {len(successful_sellers)} successful sellers for '{query}'"
        ).to_json_string()
        
    except Exception as e:
        await ctx.error(f"Failed to find successful sellers: {str(e)}")
        return error_response(
            ErrorCode.INTERNAL_ERROR,
            f"Failed to find successful sellers: {str(e)}"
        ).to_json_string()


def _analyze_seller_data(items: List[Dict], seller_username: str) -> Dict[str, Any]:
    """Analyze seller performance data from their listings."""
    if not items:
        return {"error": "No items found for analysis"}
    
    # Extract pricing data
    prices = []
    for item in items:
        price_data = item.get("price", {})
        if price_data and "value" in price_data:
            prices.append(float(price_data["value"]))
    
    # Extract seller data (all should be same seller)
    seller_data = items[0].get("seller", {})
    
    # Calculate metrics
    analysis = {
        "pricing_analysis": {
            "total_listings": len(items),
            "average_price": sum(prices) / len(prices) if prices else 0,
            "price_range": {"min": min(prices), "max": max(prices)} if prices else {"min": 0, "max": 0},
            "pricing_strategy": _determine_pricing_strategy(prices)
        },
        "seller_metrics": {
            "feedback_score": seller_data.get("feedback_score", 0),
            "positive_feedback_percent": seller_data.get("positive_feedback_percent", 0),
            "estimated_listing_count": len(items)  # This is just our sample
        },
        "listing_quality": {
            "average_title_length": sum(len(item.get("title", "")) for item in items) / len(items),
            "has_free_shipping": sum(1 for item in items if item.get("free_shipping", False)) / len(items) * 100,
            "listing_quality_score": _calculate_listing_quality(items)
        },
        "success_indicators": _identify_success_indicators(items, seller_data)
    }
    
    return analysis


def _identify_successful_sellers(items: List[Dict], min_feedback_score: int, max_sellers: int) -> List[Dict]:
    """Identify successful sellers from item listings."""
    seller_data = {}
    
    # Aggregate data by seller
    for item in items:
        seller = item.get("seller", {})
        username = seller.get("username")
        if not username:
            continue
            
        if username not in seller_data:
            seller_data[username] = {
                "username": username,
                "feedback_score": seller.get("feedback_score", 0),
                "positive_feedback_percent": seller.get("positive_feedback_percent", 0),
                "listings": [],
                "prices": []
            }
        
        seller_data[username]["listings"].append(item)
        price_data = item.get("price", {})
        if price_data and "value" in price_data:
            seller_data[username]["prices"].append(float(price_data["value"]))
    
    # Filter and rank sellers
    successful_sellers = []
    for username, data in seller_data.items():
        if (data["feedback_score"] >= min_feedback_score and 
            len(data["listings"]) >= 2):  # At least 2 listings in our sample
            
            success_score = _calculate_seller_success_score(data)
            
            seller_analysis = {
                "username": username,
                "feedback_score": data["feedback_score"],
                "positive_feedback_percent": data["positive_feedback_percent"],
                "sample_listings": len(data["listings"]),
                "average_price": sum(data["prices"]) / len(data["prices"]) if data["prices"] else 0,
                "success_score": success_score,
                "success_indicators": _identify_success_indicators(data["listings"], {
                    "feedback_score": data["feedback_score"],
                    "positive_feedback_percent": data["positive_feedback_percent"]
                })
            }
            successful_sellers.append(seller_analysis)
    
    # Sort by success score and return top sellers
    successful_sellers.sort(key=lambda x: x["success_score"], reverse=True)
    return successful_sellers[:max_sellers]


def _determine_pricing_strategy(prices: List[float]) -> str:
    """Determine pricing strategy based on price distribution."""
    if not prices:
        return "unknown"
    
    avg_price = sum(prices) / len(prices)
    price_variance = sum((p - avg_price) ** 2 for p in prices) / len(prices)
    
    if price_variance < (avg_price * 0.1) ** 2:
        return "consistent_pricing"
    elif max(prices) > avg_price * 2:
        return "varied_pricing"
    elif avg_price < 20:
        return "budget_focused"
    elif avg_price > 100:
        return "premium_pricing"
    else:
        return "competitive_pricing"


def _calculate_listing_quality(items: List[Dict]) -> float:
    """Calculate overall listing quality score (0-100)."""
    if not items:
        return 0
    
    quality_score = 0
    total_items = len(items)
    
    for item in items:
        item_score = 0
        
        # Title quality (0-25 points)
        title = item.get("title", "")
        if len(title) > 50:
            item_score += 25
        elif len(title) > 30:
            item_score += 15
        elif len(title) > 10:
            item_score += 10
        
        # Image quality (0-25 points)
        if item.get("primary_image"):
            item_score += 25
        
        # Shipping (0-25 points)
        if item.get("free_shipping"):
            item_score += 25
        elif item.get("shipping_options"):
            item_score += 15
        
        # Price competitiveness (0-25 points) - assume competitive if reasonably priced
        price_data = item.get("price", {})
        if price_data and "value" in price_data:
            price = float(price_data["value"])
            if 5 < price < 500:  # Reasonable price range
                item_score += 25
        
        quality_score += item_score
    
    return quality_score / total_items


def _identify_success_indicators(listings: List[Dict], seller_data: Dict) -> List[str]:
    """Identify success indicators for a seller."""
    indicators = []
    
    # High feedback
    feedback_score = seller_data.get("feedback_score", 0)
    if feedback_score > 99:
        indicators.append("excellent_feedback")
    elif feedback_score > 95:
        indicators.append("high_feedback")
    
    # Listing quality
    avg_quality = _calculate_listing_quality(listings)
    if avg_quality > 80:
        indicators.append("high_quality_listings")
    elif avg_quality > 60:
        indicators.append("good_listing_quality")
    
    # Free shipping
    free_shipping_rate = sum(1 for item in listings if item.get("free_shipping", False)) / len(listings) * 100
    if free_shipping_rate > 80:
        indicators.append("free_shipping_strategy")
    
    # Consistent pricing
    prices = []
    for item in listings:
        price_data = item.get("price", {})
        if price_data and "value" in price_data:
            prices.append(float(price_data["value"]))
    
    if prices:
        avg_price = sum(prices) / len(prices)
        price_variance = sum((p - avg_price) ** 2 for p in prices) / len(prices)
        if price_variance < (avg_price * 0.15) ** 2:
            indicators.append("consistent_pricing")
    
    # High volume (based on our sample)
    if len(listings) > 10:
        indicators.append("high_volume_seller")
    
    return indicators


def _calculate_seller_success_score(seller_data: Dict) -> float:
    """Calculate overall success score for ranking sellers."""
    score = 0
    
    # Feedback score (0-40 points)
    feedback_score = seller_data.get("feedback_score", 0)
    score += min(feedback_score * 0.4, 40)
    
    # Listing count in sample (0-20 points)
    listing_count = len(seller_data.get("listings", []))
    score += min(listing_count * 2, 20)
    
    # Price competitiveness (0-20 points)
    prices = seller_data.get("prices", [])
    if prices:
        avg_price = sum(prices) / len(prices)
        if 10 < avg_price < 200:  # Reasonable price range
            score += 20
        elif 5 < avg_price < 500:
            score += 10
    
    # Listing quality (0-20 points)
    quality_score = _calculate_listing_quality(seller_data.get("listings", []))
    score += quality_score * 0.2
    
    return round(score, 2)


@mcp.tool
async def analyze_marketplace_competition(
    ctx: Context,
    query: str,
    category_id: Optional[str] = None,
    price_range: Optional[str] = None,
    max_items: int = 100
) -> str:
    """
    Analyze marketplace competition for a product or search term.
    
    Provides comprehensive competition analysis including market saturation,
    pricing distribution, seller diversity, and competitive intelligence.
    
    Args:
        query: Product search query
        category_id: Optional category filter
        price_range: Optional price range filter (e.g., "10.0-50.0")
        max_items: Maximum items to analyze (default: 100)
        ctx: MCP context
    
    Returns:
        JSON response with competition analysis and market insights
    """
    await ctx.info(f"Analyzing marketplace competition for: {query}")
    await ctx.report_progress(0.1, "Searching marketplace...")
    
    # Check credentials
    if not mcp.config.app_id or not mcp.config.cert_id:
        return success_response(
            data={
                "query": query,
                "competition_analysis": {
                    "market_saturation": "medium",
                    "total_listings": 150,
                    "unique_sellers": 75,
                    "price_distribution": {"avg": 29.99, "min": 9.99, "max": 99.99},
                    "competitive_intensity": "moderate"
                },
                "data_source": "static_analysis",
                "note": "Live competition analysis requires eBay API credentials"
            },
            message="Competition analysis (static data)"
        ).to_json_string()
    
    try:
        # Parse price range if provided
        price_min = None
        price_max = None
        if price_range:
            try:
                price_parts = price_range.split("-")
                if len(price_parts) == 2:
                    price_min = float(price_parts[0])
                    price_max = float(price_parts[1])
            except ValueError:
                await ctx.error(f"Invalid price range format: {price_range}")
        
        # Search for competitive items
        search_result = await search_items.fn(
            ctx=ctx,
            query=query,
            category_ids=category_id,
            price_min=price_min,
            price_max=price_max,
            limit=max_items,
            sort="relevance"
        )
        
        # Parse search results
        import json
        search_data = json.loads(search_result)
        
        if search_data["status"] != "success":
            return error_response(
                ErrorCode.EXTERNAL_API_ERROR,
                f"Failed to search marketplace: {search_data.get('error_message', 'Unknown error')}"
            ).to_json_string()
        
        items = search_data["data"]["items"]
        total_found = search_data["data"]["total"]
        
        await ctx.report_progress(0.6, f"Analyzing {len(items)} competitive listings...")
        
        # Perform comprehensive competition analysis
        competition_analysis = _analyze_marketplace_competition(items, total_found, query)
        
        await ctx.report_progress(1.0, "Competition analysis complete")
        await ctx.info(f"Analyzed {len(items)} items from {competition_analysis['seller_diversity']['unique_sellers']} sellers")
        
        return success_response(
            data={
                "query": query,
                "category_filter": category_id,
                "price_filter": price_range,
                "items_analyzed": len(items),
                "total_marketplace_items": total_found,
                "competition_analysis": competition_analysis,
                "top_competitors": competition_analysis.get("top_competitors", [])[:5],
                "market_opportunities": _identify_market_opportunities(competition_analysis),
                "analysis_date": datetime.now(timezone.utc).isoformat(),
                "data_source": "browse_api_competition_analysis"
            },
            message=f"Competition analysis complete for '{query}' - {len(items)} items analyzed"
        ).to_json_string()
        
    except Exception as e:
        await ctx.error(f"Failed to analyze marketplace competition: {str(e)}")
        return error_response(
            ErrorCode.INTERNAL_ERROR,
            f"Failed to analyze marketplace competition: {str(e)}"
        ).to_json_string()


@mcp.tool
async def find_market_gaps(
    ctx: Context,
    base_query: str,
    related_queries: Optional[List[str]] = None,
    category_id: Optional[str] = None
) -> str:
    """
    Find market gaps and opportunities by analyzing search volumes and competition.
    
    Compares search results across related queries to identify underserved niches
    and market opportunities.
    
    Args:
        base_query: Primary product search query
        related_queries: List of related search terms to compare
        category_id: Optional category filter
        ctx: MCP context
    
    Returns:
        JSON response with market gap analysis and opportunities
    """
    await ctx.info(f"Finding market gaps for: {base_query}")
    await ctx.report_progress(0.1, "Analyzing base market...")
    
    if related_queries is None:
        # Generate some common variations
        related_queries = [
            f"{base_query} cheap",
            f"{base_query} premium", 
            f"{base_query} bulk",
            f"{base_query} wholesale",
            f"used {base_query}"
        ]
    
    # Check credentials
    if not mcp.config.app_id or not mcp.config.cert_id:
        return success_response(
            data={
                "base_query": base_query,
                "market_gaps": [
                    {
                        "opportunity": "premium_segment",
                        "description": "High-end market appears underserved",
                        "potential": "high",
                        "entry_difficulty": "medium"
                    }
                ],
                "data_source": "static_analysis",
                "note": "Live market gap analysis requires eBay API credentials"
            },
            message="Market gap analysis (static data)"
        ).to_json_string()
    
    try:
        import json
        market_data = {}
        
        # Analyze base query
        base_analysis = await analyze_marketplace_competition.fn(
            ctx=ctx,
            query=base_query,
            category_id=category_id,
            max_items=50
        )
        base_data = json.loads(base_analysis)
        if base_data["status"] == "success":
            market_data[base_query] = base_data["data"]["competition_analysis"]
        
        await ctx.report_progress(0.4, f"Analyzing {len(related_queries)} related markets...")
        
        # Analyze related queries
        for i, related_query in enumerate(related_queries):
            try:
                related_analysis = await analyze_marketplace_competition.fn(
                    ctx=ctx,
                    query=related_query,
                    category_id=category_id,
                    max_items=30
                )
                related_data = json.loads(related_analysis)
                if related_data["status"] == "success":
                    market_data[related_query] = related_data["data"]["competition_analysis"]
                
                await ctx.report_progress(0.4 + (0.4 * (i + 1) / len(related_queries)), 
                                        f"Analyzed {i+1}/{len(related_queries)} related markets")
            except Exception as e:
                await ctx.error(f"Failed to analyze '{related_query}': {str(e)}")
                continue
        
        # Identify gaps and opportunities
        market_gaps = _identify_market_gaps(market_data, base_query)
        
        await ctx.report_progress(1.0, "Market gap analysis complete")
        await ctx.info(f"Identified {len(market_gaps)} potential market opportunities")
        
        return success_response(
            data={
                "base_query": base_query,
                "related_queries": related_queries,
                "category_filter": category_id,
                "market_data": market_data,
                "market_gaps": market_gaps,
                "opportunities_count": len(market_gaps),
                "analysis_date": datetime.now(timezone.utc).isoformat(),
                "data_source": "browse_api_gap_analysis"
            },
            message=f"Market gap analysis complete - {len(market_gaps)} opportunities identified"
        ).to_json_string()
        
    except Exception as e:
        await ctx.error(f"Failed to find market gaps: {str(e)}")
        return error_response(
            ErrorCode.INTERNAL_ERROR,
            f"Failed to find market gaps: {str(e)}"
        ).to_json_string()


def _analyze_marketplace_competition(items: List[Dict], total_found: int, query: str) -> Dict[str, Any]:
    """Perform comprehensive marketplace competition analysis."""
    if not items:
        return {"error": "No items found for competition analysis"}
    
    # Price analysis
    prices = []
    for item in items:
        price_data = item.get("price", {})
        if price_data and "value" in price_data:
            prices.append(float(price_data["value"]))
    
    # Seller analysis
    sellers = {}
    for item in items:
        seller = item.get("seller", {})
        username = seller.get("username")
        if username:
            if username not in sellers:
                sellers[username] = {
                    "username": username,
                    "feedback_score": seller.get("feedback_score", 0),
                    "item_count": 0,
                    "prices": []
                }
            sellers[username]["item_count"] += 1
            price_data = item.get("price", {})
            if price_data and "value" in price_data:
                sellers[username]["prices"].append(float(price_data["value"]))
    
    # Calculate competition metrics
    analysis = {
        "market_saturation": _calculate_market_saturation(total_found, len(items)),
        "price_distribution": _analyze_price_distribution(prices),
        "seller_diversity": _analyze_seller_diversity(sellers),
        "competitive_intensity": _calculate_competitive_intensity(items, sellers),
        "top_competitors": _identify_top_competitors(sellers),
        "market_characteristics": _identify_market_characteristics(items, prices, sellers),
        "entry_barriers": _assess_entry_barriers(items, sellers, prices)
    }
    
    return analysis


def _calculate_market_saturation(total_found: int, sample_size: int) -> str:
    """Calculate market saturation level."""
    if total_found > 10000:
        return "very_high"
    elif total_found > 5000:
        return "high"
    elif total_found > 1000:
        return "medium"
    elif total_found > 200:
        return "low"
    else:
        return "very_low"


def _analyze_price_distribution(prices: List[float]) -> Dict[str, Any]:
    """Analyze price distribution in the marketplace."""
    if not prices:
        return {"error": "No price data available"}
    
    prices.sort()
    count = len(prices)
    
    return {
        "average": round(sum(prices) / count, 2),
        "median": prices[count // 2],
        "min": min(prices),
        "max": max(prices),
        "quartiles": {
            "q1": prices[count // 4],
            "q3": prices[3 * count // 4]
        },
        "price_gaps": _identify_price_gaps(prices),
        "distribution_type": _classify_price_distribution(prices)
    }


def _analyze_seller_diversity(sellers: Dict) -> Dict[str, Any]:
    """Analyze diversity and concentration of sellers."""
    if not sellers:
        return {"error": "No seller data available"}
    
    total_listings = sum(seller["item_count"] for seller in sellers.values())
    
    # Calculate market concentration
    seller_shares = [(seller["item_count"] / total_listings) * 100 for seller in sellers.values()]
    seller_shares.sort(reverse=True)
    
    # HHI-like concentration index
    concentration_index = sum(share ** 2 for share in seller_shares) / 100
    
    return {
        "unique_sellers": len(sellers),
        "total_listings": total_listings,
        "average_listings_per_seller": total_listings / len(sellers),
        "market_concentration": "high" if concentration_index > 25 else "medium" if concentration_index > 10 else "low",
        "top_seller_share": seller_shares[0] if seller_shares else 0,
        "top_3_sellers_share": sum(seller_shares[:3]) if len(seller_shares) >= 3 else sum(seller_shares)
    }


def _calculate_competitive_intensity(items: List[Dict], sellers: Dict) -> str:
    """Calculate overall competitive intensity."""
    # Factors: number of sellers, listing quality, price competition
    
    # Quality competition (based on free shipping, images, etc.)
    quality_competition = sum(1 for item in items if item.get("free_shipping", False)) / len(items)
    
    # Price competition (based on price variance)
    prices = []
    for item in items:
        price_data = item.get("price", {})
        if price_data and "value" in price_data:
            prices.append(float(price_data["value"]))
    
    if len(prices) > 1:
        avg_price = sum(prices) / len(prices)
        price_variance = sum((p - avg_price) ** 2 for p in prices) / len(prices)
        price_competition = price_variance / (avg_price ** 2) if avg_price > 0 else 0
    else:
        price_competition = 0
    
    # Seller competition
    seller_competition = len(sellers) / len(items) if items else 0
    
    # Combined intensity score
    intensity_score = (quality_competition * 0.3 + price_competition * 0.4 + seller_competition * 0.3)
    
    if intensity_score > 0.6:
        return "very_high"
    elif intensity_score > 0.4:
        return "high"
    elif intensity_score > 0.25:
        return "medium"
    elif intensity_score > 0.1:
        return "low"
    else:
        return "very_low"


def _identify_top_competitors(sellers: Dict) -> List[Dict]:
    """Identify top competing sellers."""
    competitors = []
    
    for seller_data in sellers.values():
        competitor = {
            "username": seller_data["username"],
            "listing_count": seller_data["item_count"],
            "feedback_score": seller_data["feedback_score"],
            "average_price": sum(seller_data["prices"]) / len(seller_data["prices"]) if seller_data["prices"] else 0,
            "competitive_strength": _calculate_competitive_strength(seller_data)
        }
        competitors.append(competitor)
    
    # Sort by competitive strength
    competitors.sort(key=lambda x: x["competitive_strength"], reverse=True)
    return competitors


def _calculate_competitive_strength(seller_data: Dict) -> float:
    """Calculate competitive strength score for a seller."""
    score = 0
    
    # Listing volume (0-30 points)
    score += min(seller_data["item_count"] * 3, 30)
    
    # Feedback score (0-40 points) 
    score += seller_data["feedback_score"] * 0.4
    
    # Price competitiveness (0-30 points)
    if seller_data["prices"]:
        avg_price = sum(seller_data["prices"]) / len(seller_data["prices"])
        if 10 < avg_price < 100:  # Reasonable range
            score += 30
        elif 5 < avg_price < 200:
            score += 20
        else:
            score += 10
    
    return round(score, 2)


def _identify_market_characteristics(items: List[Dict], prices: List[float], sellers: Dict) -> List[str]:
    """Identify key market characteristics."""
    characteristics = []
    
    # Price-based characteristics
    if prices:
        avg_price = sum(prices) / len(prices)
        if avg_price < 20:
            characteristics.append("budget_market")
        elif avg_price > 100:
            characteristics.append("premium_market")
        else:
            characteristics.append("mid_range_market")
    
    # Shipping characteristics
    free_shipping_rate = sum(1 for item in items if item.get("free_shipping", False)) / len(items) * 100
    if free_shipping_rate > 70:
        characteristics.append("free_shipping_dominant")
    elif free_shipping_rate < 20:
        characteristics.append("paid_shipping_market")
    
    # Seller concentration
    if len(sellers) < 5:
        characteristics.append("concentrated_market")
    elif len(sellers) > 50:
        characteristics.append("fragmented_market")
    
    # Quality indicators
    avg_title_length = sum(len(item.get("title", "")) for item in items) / len(items)
    if avg_title_length > 60:
        characteristics.append("high_optimization")
    elif avg_title_length < 30:
        characteristics.append("low_optimization")
    
    return characteristics


def _assess_entry_barriers(items: List[Dict], sellers: Dict, prices: List[float]) -> Dict[str, str]:
    """Assess barriers to entry in the market."""
    barriers = {}
    
    # Price barrier
    if prices:
        avg_price = sum(prices) / len(prices)
        min_price = min(prices)
        if min_price < avg_price * 0.5:
            barriers["price_competition"] = "high"
        elif min_price < avg_price * 0.8:
            barriers["price_competition"] = "medium"
        else:
            barriers["price_competition"] = "low"
    
    # Quality barrier
    quality_competition = sum(1 for item in items if item.get("free_shipping", False)) / len(items)
    if quality_competition > 0.8:
        barriers["quality_standards"] = "high"
    elif quality_competition > 0.5:
        barriers["quality_standards"] = "medium"
    else:
        barriers["quality_standards"] = "low"
    
    # Volume barrier
    total_listings = len(items)
    if total_listings > 1000:
        barriers["market_saturation"] = "high"
    elif total_listings > 200:
        barriers["market_saturation"] = "medium"
    else:
        barriers["market_saturation"] = "low"
    
    return barriers


def _identify_price_gaps(prices: List[float]) -> List[Dict[str, float]]:
    """Identify significant gaps in price distribution."""
    if len(prices) < 3:
        return []
    
    gaps = []
    prices.sort()
    
    for i in range(len(prices) - 1):
        gap_size = prices[i + 1] - prices[i]
        gap_percentage = gap_size / prices[i] * 100 if prices[i] > 0 else 0
        
        # Significant gap if > 50% price difference and > $5
        if gap_percentage > 50 and gap_size > 5:
            gaps.append({
                "lower_price": prices[i],
                "upper_price": prices[i + 1],
                "gap_size": gap_size,
                "gap_percentage": round(gap_percentage, 1)
            })
    
    return gaps


def _classify_price_distribution(prices: List[float]) -> str:
    """Classify the type of price distribution."""
    if len(prices) < 3:
        return "insufficient_data"
    
    avg_price = sum(prices) / len(prices)
    variance = sum((p - avg_price) ** 2 for p in prices) / len(prices)
    std_dev = variance ** 0.5
    
    coefficient_of_variation = std_dev / avg_price if avg_price > 0 else 0
    
    if coefficient_of_variation < 0.2:
        return "concentrated"
    elif coefficient_of_variation < 0.5:
        return "normal"
    elif coefficient_of_variation < 1.0:
        return "dispersed"
    else:
        return "highly_dispersed"


def _identify_market_opportunities(competition_analysis: Dict) -> List[Dict[str, Any]]:
    """Identify market opportunities based on competition analysis."""
    opportunities = []
    
    # Price gap opportunities
    price_dist = competition_analysis.get("price_distribution", {})
    price_gaps = price_dist.get("price_gaps", [])
    for gap in price_gaps:
        opportunities.append({
            "type": "price_gap",
            "description": f"Price gap between ${gap['lower_price']:.2f} and ${gap['upper_price']:.2f}",
            "potential": "medium" if gap["gap_size"] > 20 else "low",
            "entry_point": (gap["lower_price"] + gap["upper_price"]) / 2
        })
    
    # Market saturation opportunities
    saturation = competition_analysis.get("market_saturation", "")
    if saturation in ["low", "very_low"]:
        opportunities.append({
            "type": "low_competition",
            "description": "Market has low saturation with room for new entrants",
            "potential": "high",
            "strategy": "establish_market_presence"
        })
    
    # Seller concentration opportunities
    seller_diversity = competition_analysis.get("seller_diversity", {})
    concentration = seller_diversity.get("market_concentration", "")
    if concentration == "high":
        opportunities.append({
            "type": "market_disruption",
            "description": "Market dominated by few sellers - disruption opportunity",
            "potential": "high",
            "strategy": "competitive_pricing_and_service"
        })
    
    # Quality differentiation opportunities
    characteristics = competition_analysis.get("market_characteristics", [])
    if "low_optimization" in characteristics:
        opportunities.append({
            "type": "quality_differentiation",
            "description": "Market has poor listing optimization - quality opportunity",
            "potential": "medium",
            "strategy": "superior_listing_quality"
        })
    
    return opportunities


def _identify_market_gaps(market_data: Dict, base_query: str) -> List[Dict[str, Any]]:
    """Identify gaps by comparing related market analyses."""
    gaps = []
    
    if base_query not in market_data:
        return gaps
    
    base_analysis = market_data[base_query]
    base_saturation = base_analysis.get("market_saturation", "medium")
    
    # Compare with related markets
    for query, analysis in market_data.items():
        if query == base_query:
            continue
        
        saturation = analysis.get("market_saturation", "medium")
        
        # Identify underserved segments
        if saturation in ["low", "very_low"] and base_saturation in ["medium", "high", "very_high"]:
            gaps.append({
                "gap_type": "underserved_segment",
                "segment": query,
                "description": f"'{query}' market is underserved compared to main market",
                "opportunity_size": "medium" if saturation == "low" else "high",
                "entry_difficulty": "low",
                "recommended_action": f"Consider entering {query} segment"
            })
        
        # Identify premium opportunities
        price_dist = analysis.get("price_distribution", {})
        avg_price = price_dist.get("average", 0)
        base_price_dist = base_analysis.get("price_distribution", {})
        base_avg_price = base_price_dist.get("average", 0)
        
        if avg_price > base_avg_price * 1.5 and saturation in ["low", "medium"]:
            gaps.append({
                "gap_type": "premium_opportunity",
                "segment": query,
                "description": f"Premium segment '{query}' has higher prices and lower competition",
                "opportunity_size": "high",
                "entry_difficulty": "medium",
                "price_premium": f"{((avg_price / base_avg_price - 1) * 100):.1f}%" if base_avg_price > 0 else "unknown"
            })
    
    return gaps