"""
eBay Marketing API tools for merchandising and promotional content.

Provides access to eBay's merchandising products, deals, and promotional
content using the modern REST Marketing API.
"""
from typing import Dict, Any, Optional, List
from fastmcp import Context
from pydantic import BaseModel, Field, field_validator
from decimal import Decimal
from datetime import datetime

from api.oauth import OAuthManager, OAuthConfig, OAuthScopes
from api.rest_client import EbayRestClient, RestConfig
from api.models import Money, Currency, MarketplaceId
from api.errors import EbayApiError, AuthorizationError
from data_types import success_response, error_response, ErrorCode
from lootly_server import mcp


class MarketingProductsInput(BaseModel):
    """Input validation for marketing products."""
    category_id: Optional[str] = Field(None, description="eBay category ID to filter by")
    marketplace_id: str = Field("EBAY_US", description="eBay marketplace ID")
    max_results: int = Field(20, ge=1, le=100, description="Maximum number of products to return")
    aspect_filter: Optional[str] = Field(None, description="Product aspect filter (e.g., 'Brand:Apple')")
    
    @field_validator('category_id')
    @classmethod
    def validate_category_id(cls, v):
        if v is not None and (not v or not v.strip()):
            raise ValueError("Category ID cannot be empty if provided")
        return v.strip() if v else None
    
    @field_validator('marketplace_id')
    @classmethod
    def validate_marketplace_id(cls, v):
        valid_marketplaces = [marketplace.value for marketplace in MarketplaceId]
        if v not in valid_marketplaces:
            raise ValueError(f"Invalid marketplace ID. Must be one of: {valid_marketplaces}")
        return v


@mcp.tool
async def get_top_selling_products(
    ctx: Context,
    category_id: Optional[str] = None,
    marketplace_id: str = "EBAY_US",
    max_results: int = 20,
    aspect_filter: Optional[str] = None
) -> str:
    """
    Get top selling products on eBay using the Marketing API.
    
    This tool uses eBay's Marketing API to retrieve best-selling products
    based on actual sales data and demand factors. Returns curated product
    collections that help motivate customers to buy.
    
    Args:
        category_id: Optional eBay category ID to filter results
        marketplace_id: eBay marketplace (EBAY_US, EBAY_GB, etc.)
        max_results: Maximum number of products to return (1-100, default 20)
        aspect_filter: Optional product aspect filter (e.g., 'Brand:Apple')
        ctx: MCP context
    
    Returns:
        JSON response with top selling products
    """
    await ctx.info("Getting top selling products using Marketing API...")
    await ctx.report_progress(0.1, "Validating input parameters...")
    
    # Check credentials
    if not mcp.config.app_id or not mcp.config.cert_id:
        return success_response(
            data={
                "products": [],
                "total_count": 0,
                "category_id": category_id,
                "marketplace_id": marketplace_id,
                "note": "eBay API credentials not configured. Please set EBAY_APP_ID and EBAY_CERT_ID."
            },
            message="eBay API credentials not available"
        ).to_json_string()
    
    # Validate input
    try:
        input_data = MarketingProductsInput(
            category_id=category_id,
            marketplace_id=marketplace_id,
            max_results=max_results,
            aspect_filter=aspect_filter
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
        await ctx.report_progress(0.3, "Fetching top selling products from Marketing API...")
        
        # Build query parameters for Marketing API
        params = {
            "metric": "BEST_SELLING",
            "marketplace_id": input_data.marketplace_id,
            "limit": input_data.max_results
        }
        
        # Add category filter if provided
        if input_data.category_id:
            params["category_id"] = input_data.category_id
            await ctx.info(f"Filtering by category: {input_data.category_id}")
        
        # Add aspect filter if provided
        if input_data.aspect_filter:
            params["aspect_filter"] = input_data.aspect_filter
            await ctx.info(f"Filtering by aspect: {input_data.aspect_filter}")
        
        # Make API request to Marketing API
        response = await rest_client.get(
            "/buy/marketing/v1_beta/merchandised_product",
            params=params,
            scope=OAuthScopes.BUY_MARKETING
        )
        
        await ctx.report_progress(0.7, "Processing merchandised products...")
        
        # Parse response
        products = []
        merchandised_products = response.get("merchandisedProducts", [])
        
        for product_data in merchandised_products:
            try:
                # Convert to standardized format
                product = _convert_marketing_product(product_data)
                products.append(product)
            except Exception as e:
                await ctx.error(f"Error parsing product: {str(e)}")
                continue
        
        await ctx.report_progress(1.0, "Complete")
        await ctx.info(f"Found {len(products)} top selling products")
        
        return success_response(
            data={
                "products": products,
                "total_count": len(products),
                "category_id": input_data.category_id,
                "marketplace_id": input_data.marketplace_id,
                "metric": "BEST_SELLING",
                "api_used": "marketing_api"
            },
            message=f"Retrieved {len(products)} top selling products"
        ).to_json_string()
        
    except EbayApiError as e:
        await ctx.error(f"Marketing API error: {str(e)}")
        
        # If Marketing API fails, try fallback to Browse API
        if e.status_code == 403 or e.status_code == 401:
            await ctx.info("Marketing API access denied, falling back to Browse API...")
            return await _fallback_to_browse_api(ctx, input_data)
        
        return error_response(
            ErrorCode.EXTERNAL_API_ERROR,
            str(e),
            {"status_code": e.status_code}
        ).to_json_string()
    except Exception as e:
        await ctx.error(f"Failed to get top selling products: {str(e)}")
        return error_response(
            ErrorCode.INTERNAL_ERROR,
            f"Failed to retrieve top selling products: {str(e)}"
        ).to_json_string()
    finally:
        await rest_client.close()


@mcp.tool
async def get_merchandised_products(
    ctx: Context,
    category_id: str,
    marketplace_id: str = "EBAY_US",
    max_results: int = 20
) -> str:
    """
    Get merchandised products for a specific category.
    
    This tool retrieves curated product collections including "also viewed"
    and "also bought" products to help with cross-selling and upselling.
    
    Args:
        category_id: eBay category ID (required)
        marketplace_id: eBay marketplace (EBAY_US, EBAY_GB, etc.)
        max_results: Maximum number of products to return (1-100, default 20)
        ctx: MCP context
    
    Returns:
        JSON response with merchandised products
    """
    await ctx.info(f"Getting merchandised products for category: {category_id}")
    
    # Use the same implementation as get_top_selling_products
    return await get_top_selling_products.fn(
        ctx=ctx,
        category_id=category_id,
        marketplace_id=marketplace_id,
        max_results=max_results
    )


async def _fallback_to_browse_api(ctx: Context, input_data: MarketingProductsInput) -> str:
    """Fallback to Browse API when Marketing API is not available."""
    await ctx.info("Using Browse API as fallback for top selling products...")
    
    # Import Browse API tools
    from tools.browse_api import search_items
    
    # Build search query for popular items
    search_query = "best seller popular top rated"
    if input_data.aspect_filter and "Brand:" in input_data.aspect_filter:
        brand = input_data.aspect_filter.split("Brand:")[1].split(",")[0].strip()
        search_query = f"{brand} {search_query}"
    
    # Use Browse API search
    try:
        result = await search_items.fn(
            ctx=ctx,
            query=search_query,
            category_ids=input_data.category_id,
            sort="relevance",
            limit=input_data.max_results
        )
        
        # Parse the result and reformat for consistency
        import json
        result_data = json.loads(result)
        
        if result_data.get("status") == "success":
            items = result_data.get("data", {}).get("items", [])
            
            # Convert items to product format
            products = []
            for item in items:
                product = {
                    "product_id": item.get("item_id", ""),
                    "title": item.get("title", ""),
                    "price_range": {
                        "min": item.get("price", {}).get("value", 0),
                        "max": item.get("price", {}).get("value", 0),
                        "currency": item.get("price", {}).get("currency", "USD")
                    },
                    "url": item.get("item_url", ""),
                    "image_url": item.get("primary_image", {}).get("url", ""),
                    "review_count": 0,  # Not available in Browse API
                    "rating": None,  # Not available in Browse API
                    "sales_rank": "estimated",  # Estimated based on search results
                    "fallback_used": True
                }
                products.append(product)
            
            return success_response(
                data={
                    "products": products,
                    "total_count": len(products),
                    "category_id": input_data.category_id,
                    "marketplace_id": input_data.marketplace_id,
                    "metric": "BEST_SELLING_ESTIMATED",
                    "api_used": "browse_api_fallback"
                },
                message=f"Retrieved {len(products)} top selling products (Browse API fallback)"
            ).to_json_string()
        
        return result
        
    except Exception as e:
        await ctx.error(f"Browse API fallback failed: {str(e)}")
        return error_response(
            ErrorCode.INTERNAL_ERROR,
            f"Both Marketing API and Browse API fallback failed: {str(e)}"
        ).to_json_string()


def _convert_marketing_product(product_data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert Marketing API product to standardized format."""
    # Extract basic product info
    product_id = product_data.get("productId", "")
    title = product_data.get("title", "")
    
    # Extract price range
    price_range = product_data.get("priceRange", {})
    min_price = price_range.get("minPrice", {})
    max_price = price_range.get("maxPrice", {})
    
    # Safely convert price values
    try:
        min_value = float(min_price.get("value", 0)) if min_price else 0
        # Handle negative prices
        min_value = max(0, min_value)
    except (ValueError, TypeError):
        min_value = 0
    
    try:
        max_value = float(max_price.get("value", 0)) if max_price else min_value
        # Handle negative prices
        max_value = max(0, max_value)
    except (ValueError, TypeError):
        max_value = min_value
    
    currency = min_price.get("currency", "USD") if min_price else "USD"
    
    # Extract review info
    review_count = product_data.get("reviewCount", 0)
    rating = product_data.get("averageRating", 0)
    
    # Extract image
    image_url = product_data.get("imageUrl", "")
    
    # Extract URL
    product_url = product_data.get("productUrl", "")
    
    return {
        "product_id": product_id,
        "title": title,
        "price_range": {
            "min": min_value,
            "max": max_value,
            "currency": currency
        },
        "url": product_url,
        "image_url": image_url,
        "review_count": review_count,
        "rating": rating,
        "sales_rank": "best_selling",
        "fallback_used": False
    }