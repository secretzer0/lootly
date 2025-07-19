"""
eBay Marketing API tool for merchandised products.

Provides access to eBay's Buy Marketing API to retrieve best-selling
and merchandised products for specific categories.
"""
from typing import Optional, Dict, Any
from fastmcp import Context

from api.oauth import OAuthManager, OAuthConfig
from api.rest_client import EbayRestClient, RestConfig
from api.errors import EbayApiError
from models.browse import MerchandisedProductsInput
from data_types import success_response, error_response, ErrorCode
from lootly_server import mcp


# HELPER FUNCTIONS

def _convert_merchandised_product(product_data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert eBay merchandised product response for consistent output."""
    formatted = {
        "epid": product_data.get("epid"),
        "title": product_data.get("title"),
        "imageUrl": product_data.get("imageUrl"),
        "averageSellingPrice": product_data.get("averageSellingPrice"),
        "marketPriceDetails": product_data.get("marketPriceDetails", {}),
        "ratingHistogram": product_data.get("ratingHistogram", {}),
        "ratingCount": product_data.get("ratingCount"),
        "reviewCount": product_data.get("reviewCount")
    }
    
    # Clean up None values except for imageUrl (keep for test compatibility)
    return {k: v for k, v in formatted.items() if v is not None or k == "imageUrl"}


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
        
    Note:
        This tool returns product data for analysis. Please provide the user with a 
        helpful summary of the top products and their key details rather than raw JSON.
    
    Example:
        Get top smartphones:
        - category_id: "9355" (Cell Phones & Smartphones)
        - limit: 10
        
        Get top Apple products in category:
        - category_id: "9355"
        - aspect_filter: "Brand:Apple"
    """
    await ctx.info(f"🛒 Getting merchandised products for category: {category_id}")
    await ctx.report_progress(0.1, "✅ Validating input...")
    
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
        await ctx.report_progress(0.3, "🌐 Calling eBay Marketing API...")
        
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
            params=params
        )
        response_body = response["body"]
        
        await ctx.report_progress(0.8, "📦 Processing response...")
        
        # Extract products
        products = response_body.get("merchandisedProducts", [])
        
        # Convert products to our format
        converted_products = [_convert_merchandised_product(product) for product in products]
        
        await ctx.report_progress(1.0, "✅ Complete")
        await ctx.info(f"🏆 Retrieved {len(converted_products)} merchandised products")
        
        return success_response(
            data={
                "merchandised_products": converted_products,
                "total": len(converted_products),
                "category_id": input_data.category_id,
                "metric_name": input_data.metric_name,
                "limit": input_data.limit,
                "aspect_filter": input_data.aspect_filter
            },
            message=f"Retrieved {len(converted_products)} merchandised products. Please provide a helpful summary of the top products and their key details."
        ).to_json_string()
        
    except EbayApiError as e:
        # Log comprehensive error details
        await ctx.error(f"eBay API error: {e.get_comprehensive_message()}")
        
        # Handle specific errors
        if e.status_code == 404:
            return error_response(
                ErrorCode.RESOURCE_NOT_FOUND,
                f"Category {input_data.category_id} not found or has no merchandised products",
                e.get_full_error_details()
            ).to_json_string()
        elif e.status_code == 400:
            # Check for sandbox testing note
            error_msg = e.get_comprehensive_message()
            if "category ID 9355" in error_msg and mcp.config.sandbox_mode:
                return error_response(
                    ErrorCode.VALIDATION_ERROR,
                    "In sandbox mode, you must use category ID 9355 for testing",
                    e.get_full_error_details()
                ).to_json_string()
            return error_response(
                ErrorCode.VALIDATION_ERROR,
                f"Invalid request: {error_msg}",
                e.get_full_error_details()
            ).to_json_string()
        else:
            # Return full error details in response
            return error_response(
                ErrorCode.EXTERNAL_API_ERROR,
                e.get_comprehensive_message(),
                e.get_full_error_details()
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