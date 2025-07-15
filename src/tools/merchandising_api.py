"""eBay Merchandising API tools for discovering popular and trending items.

The Merchandising API helps surface good deals, trending items, and popular products
to enhance shopping experiences.
"""
from typing import Optional, List, Dict, Any
from fastmcp import Context
from pydantic import BaseModel, Field, field_validator
from api.ebay_client import EbayApiClient
from data_types import (
    success_response, 
    error_response, 
    ErrorCode,
    validate_tool_input
)
from logging_config import log_performance
from lootly_server import mcp


class GetMostWatchedItemsInput(BaseModel):
    """Input validation for get_most_watched_items."""
    category_id: Optional[str] = Field(None, description="eBay category ID to filter by")
    max_results: int = Field(20, ge=1, le=100, description="Maximum number of items to return")


class GetRelatedCategoryItemsInput(BaseModel):
    """Input validation for get_related_category_items."""
    category_id: str = Field(..., description="eBay category ID")
    max_results: int = Field(20, ge=1, le=100, description="Maximum number of items to return")


class GetSimilarItemsInput(BaseModel):
    """Input validation for get_similar_items."""
    item_id: str = Field(..., description="eBay item ID to find similar items for")
    max_results: int = Field(20, ge=1, le=100, description="Maximum number of items to return")
    
    @field_validator('item_id')
    def validate_item_id(cls, v):
        if not v or not v.strip():
            raise ValueError("Item ID cannot be empty")
        return v.strip()


class GetTopSellingProductsInput(BaseModel):
    """Input validation for get_top_selling_products."""
    category_id: Optional[str] = Field(None, description="eBay category ID to filter by")
    max_results: int = Field(20, ge=1, le=100, description="Maximum number of products to return")


def _parse_merchandising_item(item_data: Dict[str, Any]) -> Dict[str, Any]:
    """Parse a merchandising API item into standardized format."""
    # Extract basic item info
    item_id = item_data.get("itemId", [""])[0]
    title = item_data.get("title", [""])[0]
    
    # Extract price info
    current_price_data = item_data.get("currentPrice", [{}])[0]
    current_price = float(current_price_data.get("value", 0))
    currency = current_price_data.get("_currencyId", "USD")
    
    # Extract seller info
    seller_info = item_data.get("sellerInfo", [{}])[0]
    seller_name = seller_info.get("sellerUserName", ["Unknown"])[0]
    feedback_score = int(seller_info.get("feedbackScore", [0])[0])
    positive_feedback = float(seller_info.get("positiveFeedbackPercent", [100.0])[0])
    
    # Extract shipping info
    shipping_info = item_data.get("shippingInfo", [{}])[0]
    shipping_type = shipping_info.get("shippingType", [""])[0]
    ship_to_locations = shipping_info.get("shipToLocations", ["Worldwide"])[0]
    
    # Extract listing info
    listing_info = item_data.get("listingInfo", [{}])[0]
    listing_type = listing_info.get("listingType", [""])[0]
    end_time = listing_info.get("endTime", [""])[0]
    
    # Extract condition
    condition = item_data.get("condition", [{}])[0]
    condition_name = condition.get("conditionDisplayName", [""])[0]
    
    # Extract other metrics
    watch_count = int(item_data.get("watchCount", [0])[0]) if "watchCount" in item_data else None
    view_item_url = item_data.get("viewItemURL", [""])[0]
    gallery_url = item_data.get("galleryURL", [""])[0]
    category_name = item_data.get("primaryCategory", [{}])[0].get("categoryName", [""])[0]
    
    return {
        "item_id": item_id,
        "title": title,
        "price": {
            "value": current_price,
            "currency": currency
        },
        "seller": {
            "username": seller_name,
            "feedback_score": feedback_score,
            "positive_feedback_percent": positive_feedback
        },
        "shipping": {
            "type": shipping_type,
            "ships_to": ship_to_locations
        },
        "listing": {
            "type": listing_type,
            "end_time": end_time
        },
        "condition": condition_name,
        "watch_count": watch_count,
        "url": view_item_url,
        "image_url": gallery_url,
        "category": category_name
    }


@mcp.tool
async def get_most_watched_items(
    category_id: Optional[str] = None,
    max_results: int = 20,
    *,
    ctx: Context
) -> str:
    """Get the most watched items on eBay.
    
    Retrieves trending items based on watch count, optionally filtered by category.
    This helps identify what buyers are most interested in.
    
    Args:
        category_id: Optional eBay category ID to filter results
        max_results: Maximum number of items to return (1-100, default 20)
        ctx: MCP context for client communication
        
    Returns:
        JSON string with most watched items or error
    """
    await ctx.info("Getting most watched items...")
    
    try:
        # Validate input
        input_data = validate_tool_input(
            GetMostWatchedItemsInput,
            {"category_id": category_id, "max_results": max_results}
        )
        
        # Initialize API client
        api_client = EbayApiClient(ctx.server.config, ctx.server.logger)
        
        # Build API parameters
        params = {
            "maxResults": str(input_data.max_results)
        }
        
        if input_data.category_id:
            params["categoryId"] = input_data.category_id
            await ctx.info(f"Filtering by category: {input_data.category_id}")
        
        # Call Merchandising API
        await ctx.report_progress(0.3, "Calling eBay Merchandising API...")
        
        response = await api_client.execute_with_retry(
            "merchandising",
            "getMostWatchedItems",
            params
        )
        
        await ctx.report_progress(0.7, "Processing response...")
        
        # Parse response
        items_data = response.get("itemRecommendations", {}).get("item", [])
        if not isinstance(items_data, list):
            items_data = [items_data]
        
        # Process items
        items = []
        for item_data in items_data:
            try:
                items.append(_parse_merchandising_item(item_data))
            except Exception as e:
                await ctx.warning(f"Failed to parse item: {str(e)}")
                continue
        
        await ctx.report_progress(1.0, "Complete")
        await ctx.info(f"Found {len(items)} most watched items")
        
        return success_response(
            data={
                "items": items,
                "total_count": len(items),
                "category_id": input_data.category_id
            },
            message=f"Retrieved {len(items)} most watched items"
        ).to_json_string()
        
    except ValueError as e:
        await ctx.error(f"Validation error: {str(e)}")
        return error_response(ErrorCode.VALIDATION_ERROR, str(e)).to_json_string()
    except Exception as e:
        await ctx.error(f"Failed to get most watched items: {str(e)}")
        ctx.server.logger.tool_failed("get_most_watched_items", str(e), 0)
        return error_response(
            ErrorCode.INTERNAL_ERROR,
            f"Failed to retrieve most watched items: {str(e)}"
        ).to_json_string()


@mcp.tool
async def get_related_category_items(
    category_id: str,
    max_results: int = 20,
    *,
    ctx: Context
) -> str:
    """Get items from categories related to the specified category.
    
    Helps users discover items in related categories they might not have considered.
    
    Args:
        category_id: eBay category ID to find related categories for
        max_results: Maximum number of items to return (1-100, default 20)
        ctx: MCP context for client communication
        
    Returns:
        JSON string with items from related categories or error
    """
    await ctx.info(f"Getting items from categories related to: {category_id}")
    
    try:
        # Validate input
        input_data = validate_tool_input(
            GetRelatedCategoryItemsInput,
            {"category_id": category_id, "max_results": max_results}
        )
        
        # Initialize API client
        api_client = EbayApiClient(ctx.server.config, ctx.server.logger)
        
        # Build API parameters
        params = {
            "categoryId": input_data.category_id,
            "maxResults": str(input_data.max_results)
        }
        
        # Call Merchandising API
        await ctx.report_progress(0.3, "Finding related categories...")
        
        response = await api_client.execute_with_retry(
            "merchandising",
            "getRelatedCategoryItems",
            params
        )
        
        await ctx.report_progress(0.7, "Processing items...")
        
        # Parse response
        items_data = response.get("itemRecommendations", {}).get("item", [])
        if not isinstance(items_data, list):
            items_data = [items_data]
        
        # Process items
        items = []
        categories_found = set()
        
        for item_data in items_data:
            try:
                parsed_item = _parse_merchandising_item(item_data)
                items.append(parsed_item)
                if parsed_item["category"]:
                    categories_found.add(parsed_item["category"])
            except Exception as e:
                await ctx.warning(f"Failed to parse item: {str(e)}")
                continue
        
        await ctx.report_progress(1.0, "Complete")
        await ctx.info(f"Found {len(items)} items from {len(categories_found)} related categories")
        
        return success_response(
            data={
                "items": items,
                "total_count": len(items),
                "source_category_id": input_data.category_id,
                "related_categories": list(categories_found)
            },
            message=f"Retrieved {len(items)} items from related categories"
        ).to_json_string()
        
    except ValueError as e:
        await ctx.error(f"Validation error: {str(e)}")
        return error_response(ErrorCode.VALIDATION_ERROR, str(e)).to_json_string()
    except Exception as e:
        await ctx.error(f"Failed to get related category items: {str(e)}")
        ctx.server.logger.tool_failed("get_related_category_items", str(e), 0)
        return error_response(
            ErrorCode.INTERNAL_ERROR,
            f"Failed to retrieve related category items: {str(e)}"
        ).to_json_string()


@mcp.tool
async def get_similar_items(
    item_id: str,
    max_results: int = 20,
    *,
    ctx: Context
) -> str:
    """Find items similar to a specified item.
    
    Uses eBay's recommendation engine to find items similar to the one provided.
    Useful for "you might also like" features.
    
    Args:
        item_id: eBay item ID to find similar items for
        max_results: Maximum number of items to return (1-100, default 20)
        ctx: MCP context for client communication
        
    Returns:
        JSON string with similar items or error
    """
    await ctx.info(f"Finding items similar to: {item_id}")
    
    try:
        # Validate input
        input_data = validate_tool_input(
            GetSimilarItemsInput,
            {"item_id": item_id, "max_results": max_results}
        )
        
        # Initialize API client
        api_client = EbayApiClient(ctx.server.config, ctx.server.logger)
        
        # Build API parameters
        params = {
            "itemId": input_data.item_id,
            "maxResults": str(input_data.max_results)
        }
        
        # Call Merchandising API
        await ctx.report_progress(0.3, "Searching for similar items...")
        
        response = await api_client.execute_with_retry(
            "merchandising",
            "getSimilarItems",
            params
        )
        
        await ctx.report_progress(0.7, "Processing similar items...")
        
        # Parse response
        items_data = response.get("itemRecommendations", {}).get("item", [])
        if not isinstance(items_data, list):
            items_data = [items_data]
        
        # Process items
        items = []
        for item_data in items_data:
            try:
                items.append(_parse_merchandising_item(item_data))
            except Exception as e:
                await ctx.warning(f"Failed to parse item: {str(e)}")
                continue
        
        await ctx.report_progress(1.0, "Complete")
        await ctx.info(f"Found {len(items)} similar items")
        
        return success_response(
            data={
                "items": items,
                "total_count": len(items),
                "source_item_id": input_data.item_id
            },
            message=f"Found {len(items)} similar items"
        ).to_json_string()
        
    except ValueError as e:
        await ctx.error(f"Validation error: {str(e)}")
        return error_response(ErrorCode.VALIDATION_ERROR, str(e)).to_json_string()
    except Exception as e:
        await ctx.error(f"Failed to get similar items: {str(e)}")
        ctx.server.logger.tool_failed("get_similar_items", str(e), 0)
        return error_response(
            ErrorCode.INTERNAL_ERROR,
            f"Failed to find similar items: {str(e)}"
        ).to_json_string()


@mcp.tool
async def get_top_selling_products(
    category_id: Optional[str] = None,
    max_results: int = 20,
    *,
    ctx: Context
) -> str:
    """Get top selling products on eBay.
    
    Retrieves best-selling products based on sales data, optionally filtered by category.
    Useful for identifying popular products and market trends.
    
    Args:
        category_id: Optional eBay category ID to filter results
        max_results: Maximum number of products to return (1-100, default 20)
        ctx: MCP context for client communication
        
    Returns:
        JSON string with top selling products or error
    """
    await ctx.info("Getting top selling products...")
    
    try:
        # Validate input
        input_data = validate_tool_input(
            GetTopSellingProductsInput,
            {"category_id": category_id, "max_results": max_results}
        )
        
        # Initialize API client
        api_client = EbayApiClient(ctx.server.config, ctx.server.logger)
        
        # Build API parameters
        params = {
            "maxResults": str(input_data.max_results)
        }
        
        if input_data.category_id:
            params["categoryId"] = input_data.category_id
            await ctx.info(f"Filtering by category: {input_data.category_id}")
        
        # Call Merchandising API
        await ctx.report_progress(0.3, "Fetching top selling products...")
        
        response = await api_client.execute_with_retry(
            "merchandising",
            "getTopSellingProducts",
            params
        )
        
        await ctx.report_progress(0.7, "Processing product data...")
        
        # Parse response
        products_data = response.get("productRecommendations", {}).get("product", [])
        if not isinstance(products_data, list):
            products_data = [products_data]
        
        # Process products
        products = []
        for product_data in products_data:
            try:
                product_id = product_data.get("productId", [{}])[0].get("value", "")
                title = product_data.get("title", [""])[0]
                
                # Extract catalog info
                catalog_info = product_data.get("catalogInfo", [{}])[0]
                product_url = catalog_info.get("productURL", [""])[0]
                
                # Extract price range
                price_range_data = product_data.get("priceRangeMin", [{}])[0]
                min_price = float(price_range_data.get("value", 0)) if price_range_data else None
                
                price_range_max_data = product_data.get("priceRangeMax", [{}])[0]
                max_price = float(price_range_max_data.get("value", 0)) if price_range_max_data else None
                
                currency = price_range_data.get("_currencyId", "USD") if price_range_data else "USD"
                
                # Extract other info
                image_url = product_data.get("imageURL", [""])[0]
                review_count = int(product_data.get("reviewCount", [0])[0]) if "reviewCount" in product_data else 0
                rating = float(product_data.get("rating", [0])[0]) if "rating" in product_data else None
                
                products.append({
                    "product_id": product_id,
                    "title": title,
                    "price_range": {
                        "min": min_price,
                        "max": max_price,
                        "currency": currency
                    },
                    "url": product_url,
                    "image_url": image_url,
                    "review_count": review_count,
                    "rating": rating
                })
            except Exception as e:
                await ctx.warning(f"Failed to parse product: {str(e)}")
                continue
        
        await ctx.report_progress(1.0, "Complete")
        await ctx.info(f"Found {len(products)} top selling products")
        
        return success_response(
            data={
                "products": products,
                "total_count": len(products),
                "category_id": input_data.category_id
            },
            message=f"Retrieved {len(products)} top selling products"
        ).to_json_string()
        
    except ValueError as e:
        await ctx.error(f"Validation error: {str(e)}")
        return error_response(ErrorCode.VALIDATION_ERROR, str(e)).to_json_string()
    except Exception as e:
        await ctx.error(f"Failed to get top selling products: {str(e)}")
        ctx.server.logger.tool_failed("get_top_selling_products", str(e), 0)
        return error_response(
            ErrorCode.INTERNAL_ERROR,
            f"Failed to retrieve top selling products: {str(e)}"
        ).to_json_string()