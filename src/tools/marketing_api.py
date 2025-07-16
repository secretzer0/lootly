"""
eBay Marketing API tool for merchandised products.

Provides access to eBay's Buy Marketing API to retrieve best-selling
and merchandised products for specific categories.
"""
from typing import Dict, Any, Optional, List
from fastmcp import Context
from pydantic import BaseModel, Field, field_validator, ConfigDict
import json

from api.oauth import OAuthManager, OAuthConfig, OAuthScopes
from api.rest_client import EbayRestClient, RestConfig
from api.errors import EbayApiError, ValidationError as ApiValidationError
from data_types import success_response, error_response, ErrorCode
from lootly_server import mcp


class MerchandisedProductsInput(BaseModel):
    """Input validation for merchandised products request."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    category_id: str = Field(..., description="eBay category ID (required)")
    metric_name: str = Field(default="BEST_SELLING", description="Metric type (currently only BEST_SELLING)")
    limit: int = Field(default=20, ge=1, le=100, description="Maximum products to return")
    aspect_filter: Optional[str] = Field(None, description="Product aspect filter (e.g., 'Brand:Apple')")
    
    @field_validator('category_id')
    @classmethod
    def validate_category_id(cls, v):
        if not v or not v.strip():
            raise ValueError("Category ID is required")
        # Basic validation - must be numeric
        if not v.isdigit():
            raise ValueError("Category ID must be numeric")
        return v.strip()
    
    @field_validator('metric_name')
    @classmethod
    def validate_metric_name(cls, v):
        # Currently only BEST_SELLING is supported
        if v != "BEST_SELLING":
            raise ValueError("Only BEST_SELLING metric is currently supported")
        return v


def _convert_merchandised_product(product: Dict[str, Any]) -> Dict[str, Any]:
    """Convert API product response to our format."""
    # Extract price details
    market_price = product.get("marketPriceDetails", [])
    price_info = {}
    if market_price:
        # Get the first price detail
        price_detail = market_price[0]
        if price_detail.get("estimatedStartPrice"):
            price_info["min_price"] = float(price_detail["estimatedStartPrice"].get("value", 0))
            price_info["currency"] = price_detail["estimatedStartPrice"].get("currency", "USD")
        if price_detail.get("estimatedEndPrice"):
            price_info["max_price"] = float(price_detail["estimatedEndPrice"].get("value", 0))
    
    # Extract image
    image_url = None
    if product.get("image"):
        image_url = product["image"].get("imageUrl")
    
    return {
        "epid": product.get("epid"),
        "title": product.get("title"),
        "image_url": image_url,
        "average_rating": product.get("averageRating", 0),
        "rating_count": product.get("ratingCount", 0),
        "review_count": product.get("reviewCount", 0),
        "price_info": price_info,
        "web_url": f"https://www.ebay.com/p/{product.get('epid')}" if product.get('epid') else None
    }




@mcp.tool
async def get_merchandised_products(
    ctx: Context,
    category_id: str,
    limit: int = 20,
    aspect_filter: Optional[str] = None
) -> str:
    """
    Get best-selling merchandised products for a specific category.
    
    Retrieves top-selling products from eBay's Buy Marketing API for the
    specified category. Currently only supports the BEST_SELLING metric.
    
    Args:
        category_id: eBay category ID (required, use 9355 for sandbox testing)
        limit: Maximum number of products to return (1-100, default: 20)
        aspect_filter: Filter by product aspects (e.g., 'Brand:Apple')
        ctx: MCP context
    
    Returns:
        JSON response with merchandised products
    
    Example:
        Get top smartphones:
        - category_id: "9355" (Cell Phones & Smartphones)
        - limit: 10
        
        Get top Apple products in category:
        - category_id: "9355"
        - aspect_filter: "Brand:Apple"
    """
    await ctx.info(f"Getting merchandised products for category: {category_id}")
    await ctx.report_progress(0.1, "Validating input...")
    
    # Validate input
    try:
        input_data = MerchandisedProductsInput(
            category_id=category_id,
            metric_name="BEST_SELLING",  # Currently the only supported metric
            limit=limit,
            aspect_filter=aspect_filter
        )
    except Exception as e:
        await ctx.error(f"Invalid input: {str(e)}")
        return error_response(
            ErrorCode.VALIDATION_ERROR,
            f"Invalid input: {str(e)}"
        ).to_json_string()
    
    # Check credentials
    if not mcp.config.app_id:
        await ctx.error("No eBay credentials configured")
        return error_response(
            ErrorCode.CONFIGURATION_ERROR,
            "eBay App ID not configured. Please set EBAY_APP_ID environment variable."
        ).to_json_string()
    
    # Initialize OAuth manager
    oauth_config = OAuthConfig(
        client_id=mcp.config.app_id,
        client_secret=mcp.config.cert_id or "",
        sandbox=mcp.config.sandbox_mode
    )
    oauth_manager = OAuthManager(oauth_config)
    
    # Initialize REST client
    rest_config = RestConfig(
        sandbox=mcp.config.sandbox_mode,
        timeout=mcp.config.timeout,
        max_retries=mcp.config.max_retries,
        rate_limit_per_day=mcp.config.rate_limit_per_day
    )
    rest_client = EbayRestClient(oauth_manager, rest_config)
    
    try:
        await ctx.report_progress(0.3, "Calling eBay Marketing API...")
        
        # Build query parameters
        params = {
            "category_id": input_data.category_id,
            "metric_name": input_data.metric_name,
            "limit": input_data.limit
        }
        
        if input_data.aspect_filter:
            params["aspect_filter"] = input_data.aspect_filter
        
        # Make API request
        response = await rest_client.get(
            "/buy/marketing/v1_beta/merchandised_product",
            params=params,
            scope=OAuthScopes.BUY_MARKETING
        )
        
        await ctx.report_progress(0.8, "Processing response...")
        
        # Extract products
        products = response.get("merchandisedProducts", [])
        
        # Convert products to our format
        converted_products = [_convert_merchandised_product(product) for product in products]
        
        await ctx.report_progress(1.0, "Complete")
        await ctx.info(f"Retrieved {len(converted_products)} merchandised products")
        
        return success_response(
            data={
                "merchandised_products": converted_products,
                "total": len(converted_products),
                "category_id": input_data.category_id,
                "metric_name": input_data.metric_name,
                "limit": input_data.limit,
                "aspect_filter": input_data.aspect_filter
            },
            message=f"Retrieved {len(converted_products)} merchandised products"
        ).to_json_string()
        
    except EbayApiError as e:
        await ctx.error(f"eBay API error: {str(e)}")
        
        # Handle specific errors
        if e.status_code == 404:
            return error_response(
                ErrorCode.RESOURCE_NOT_FOUND,
                f"Category {input_data.category_id} not found or has no merchandised products"
            ).to_json_string()
        elif e.status_code == 400:
            # Check for sandbox testing note
            error_msg = str(e)
            if "category ID 9355" in error_msg and mcp.config.sandbox_mode:
                return error_response(
                    ErrorCode.VALIDATION_ERROR,
                    "In sandbox mode, you must use category ID 9355 for testing"
                ).to_json_string()
            return error_response(
                ErrorCode.VALIDATION_ERROR,
                f"Invalid request: {error_msg}"
            ).to_json_string()
        else:
            return error_response(
                ErrorCode.EXTERNAL_API_ERROR,
                f"eBay API error: {str(e)}"
            ).to_json_string()
            
    except Exception as e:
        await ctx.error(f"Unexpected error: {str(e)}")
        return error_response(
            ErrorCode.INTERNAL_ERROR,
            f"Failed to get merchandised products: {str(e)}"
        ).to_json_string()
        
    finally:
        # Clean up
        if 'rest_client' in locals():
            await rest_client.close()