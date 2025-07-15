"""
eBay Browse API tools for searching and viewing items.

Replaces the legacy Finding API with modern REST API implementation.
"""
from typing import Dict, Any, Optional, List
from fastmcp import Context
from pydantic import BaseModel, Field, field_validator, ValidationError as PydanticValidationError
from decimal import Decimal
from datetime import datetime

from api.oauth import OAuthManager, OAuthConfig, OAuthScopes
from api.rest_client import EbayRestClient, RestConfig
from api.models import (
    SearchRequest, Item, SearchResult, Category, Seller,
    Money, Currency, ConditionId, ListingStatus, Location,
    ShippingOption, Image
)
from api.errors import (
    EbayApiError, ValidationError, NotFoundError
)
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
    price_min: Optional[float] = None,
    price_max: Optional[float] = None,
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
        price_min: Minimum price filter
        price_max: Maximum price filter
        conditions: Comma-separated condition IDs (NEW, USED, etc)
        sellers: Comma-separated seller usernames
        sort: Sort order (relevance, price, distance, newlyListed)
        limit: Number of results per page (max 200)
        offset: Result offset for pagination
        ctx: MCP context
    
    Returns:
        JSON response with search results and pagination info
    """
    await ctx.info(f"Searching eBay for: {query}")
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
            price_min=Decimal(str(price_min)) if price_min else None,
            price_max=Decimal(str(price_max)) if price_max else None,
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
        await ctx.report_progress(0.3, "Searching eBay marketplace...")
        
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
        
        await ctx.report_progress(0.8, "Processing search results...")
        
        # Parse response into models
        items = []
        for item_summary in response.get("itemSummaries", []):
            try:
                # Convert to our Item model
                item = _convert_browse_item(item_summary)
                items.append(item.dict())
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
        
        await ctx.report_progress(1.0, "Search complete")
        await ctx.info(f"Found {len(items)} items (showing {input_data.offset+1}-{input_data.offset+len(items)} of {total})")
        
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
            message=f"Found {total} items matching '{query}'"
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
        # Build field groups
        fieldgroups = ["PRODUCT", "COMPACT"]
        if include_description:
            fieldgroups.append("ADDITIONAL_SELLER_DETAILS")
        
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
            data=item.dict(),
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
    offset: int = 0
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
        ctx: MCP context
    
    Returns:
        JSON response with items from the category
    """
    await ctx.info(f"Browsing category: {category_id}")
    
    # Use search_items with category filter
    return await search_items.fn(
        ctx=ctx,
        query="*",  # Wildcard to get all items
        category_ids=category_id,
        sort=sort,
        limit=limit,
        offset=offset
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
        listing_start_date=item_data.get("itemCreationDate") or datetime.now().isoformat(),
        primary_category=primary_category
    )


def _convert_browse_item_detail(item_data: Dict[str, Any]) -> Item:
    """Convert Browse API detailed item to our Item model."""
    # Start with basic conversion
    item = _convert_browse_item(item_data)
    
    # Add additional details
    item.description = item_data.get("description")
    item.quantity_available = item_data.get("estimatedAvailabilities", [{}])[0].get("availabilityThreshold")
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