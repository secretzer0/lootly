"""
eBay Catalog API tools for product metadata and catalog management.

Provides access to eBay's product catalog with detailed product information,
search capabilities, and product matching for enhanced listings.
"""
from typing import Dict, Any, Optional, List
from fastmcp import Context
from pydantic import BaseModel, Field, field_validator, ConfigDict
from datetime import datetime
import json

from api.oauth import OAuthManager, OAuthConfig, OAuthScopes
from api.rest_client import EbayRestClient, RestConfig
from api.errors import EbayApiError, ValidationError as ApiValidationError
from data_types import success_response, error_response, ErrorCode
from lootly_server import mcp


class CatalogSearchInput(BaseModel):
    """Input validation for catalog search."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    query: Optional[str] = Field(None, min_length=1, description="Search query")
    gtin: Optional[str] = Field(None, description="Global Trade Item Number")
    brand: Optional[str] = Field(None, min_length=1, description="Brand name")
    mpn: Optional[str] = Field(None, min_length=1, description="Manufacturer Part Number")
    category_ids: Optional[str] = Field(None, description="Comma-separated category IDs")
    limit: int = Field(50, ge=1, le=200, description="Results per page")
    offset: int = Field(0, ge=0, description="Result offset")
    
    @field_validator('category_ids')
    @classmethod
    def at_least_one_criteria(cls, v, info):
        """Ensure at least one search criteria is provided."""
        # Check if any search criteria has a value
        has_query = bool(info.data.get('query'))
        has_gtin = bool(info.data.get('gtin'))
        has_brand = bool(info.data.get('brand'))
        has_mpn = bool(info.data.get('mpn'))
        has_category_ids = bool(v)
        
        if not any([has_query, has_gtin, has_brand, has_mpn, has_category_ids]):
            raise ValueError("At least one search criteria required: query, gtin, brand, mpn, or category_ids")
        return v


class ProductDetailsInput(BaseModel):
    """Input validation for product details."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    epid: str = Field(..., min_length=1, description="eBay Product ID")
    
    @field_validator('epid')
    @classmethod
    def validate_epid(cls, v):
        if not v or not v.strip():
            raise ValueError("eBay Product ID cannot be empty")
        return v.strip()


# Static fallback data for when API is not available
STATIC_PRODUCT_DATA = {
    "popular_products": [
        {
            "epid": "12345678901",
            "title": "Apple iPhone 15 Pro",
            "brand": "Apple",
            "mpn": "A2848",
            "gtin": "194253434894",
            "category_id": "9355",
            "category_name": "Cell Phones & Smartphones",
            "image_url": "https://example.com/iphone15pro.jpg",
            "description": "Latest iPhone with advanced camera system",
            "aspects": {
                "Brand": "Apple",
                "Model": "iPhone 15 Pro",
                "Storage Capacity": "128GB",
                "Color": "Natural Titanium",
                "Network": "Unlocked"
            }
        },
        {
            "epid": "12345678902",
            "title": "Samsung Galaxy S24 Ultra",
            "brand": "Samsung",
            "mpn": "SM-S928U",
            "gtin": "887276742441",
            "category_id": "9355",
            "category_name": "Cell Phones & Smartphones",
            "image_url": "https://example.com/galaxys24ultra.jpg",
            "description": "Premium Android smartphone with S Pen",
            "aspects": {
                "Brand": "Samsung",
                "Model": "Galaxy S24 Ultra",
                "Storage Capacity": "256GB",
                "Color": "Titanium Black",
                "Network": "Unlocked"
            }
        }
    ]
}


def _convert_catalog_product(product: Dict[str, Any]) -> Dict[str, Any]:
    """Convert API product data to our format."""
    # Extract images
    images = []
    for img in product.get("image", {}).get("imageUrls", []):
        images.append(img)
    
    # Extract product identifiers
    product_ids = product.get("productIdentifiers", [])
    gtin = None
    mpn = None
    brand = product.get("brand")
    
    for identifier in product_ids:
        if identifier.get("type") == "GTIN":
            gtin = identifier.get("value")
        elif identifier.get("type") == "MPN":
            mpn = identifier.get("value")
    
    # Extract aspects
    aspects = {}
    for aspect in product.get("aspects", []):
        name = aspect.get("name")
        values = aspect.get("values", [])
        if name and values:
            aspects[name] = values[0] if len(values) == 1 else values
    
    return {
        "epid": product.get("epid"),
        "title": product.get("title"),
        "brand": brand,
        "mpn": mpn,
        "gtin": gtin,
        "description": product.get("description"),
        "category_id": product.get("categoryId"),
        "category_name": product.get("categoryName"),
        "images": images,
        "primary_image": images[0] if images else None,
        "aspects": aspects,
        "product_web_url": product.get("productWebUrl"),
        "marketplace_ids": product.get("marketplaceIds", [])
    }


def _convert_product_summary(summary: Dict[str, Any]) -> Dict[str, Any]:
    """Convert API product summary to our format."""
    # Extract basic info
    epid = summary.get("epid")
    title = summary.get("title")
    
    # Extract images
    image_data = summary.get("image", {})
    image_url = image_data.get("imageUrl") if image_data else None
    
    # Extract product identifiers
    product_ids = summary.get("productIdentifiers", [])
    gtin = None
    brand = summary.get("brand")
    
    for identifier in product_ids:
        if identifier.get("type") == "GTIN":
            gtin = identifier.get("value")
    
    return {
        "epid": epid,
        "title": title,
        "brand": brand,
        "gtin": gtin,
        "image_url": image_url,
        "category_id": summary.get("categoryId"),
        "category_name": summary.get("categoryName"),
        "marketplace_ids": summary.get("marketplaceIds", [])
    }


@mcp.tool
async def search_catalog_products(
    ctx: Context,
    query: Optional[str] = None,
    gtin: Optional[str] = None,
    brand: Optional[str] = None,
    mpn: Optional[str] = None,
    category_ids: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
) -> str:
    """
    Search eBay's product catalog for products.
    
    Search for products in eBay's catalog using various criteria like keywords,
    GTIN, brand, or manufacturer part number. Returns product summaries.
    
    Args:
        query: Search keywords (e.g., "iPhone 15", "Samsung Galaxy")
        gtin: Global Trade Item Number (UPC, EAN, ISBN)
        brand: Brand name filter
        mpn: Manufacturer Part Number
        category_ids: Comma-separated category IDs to filter
        limit: Number of results per page (max 200)
        offset: Pagination offset
        ctx: MCP context
    
    Returns:
        JSON response with product search results
    """
    await ctx.info(f"Searching catalog for: {query or gtin or brand or mpn}")
    await ctx.report_progress(0.1, "Validating search parameters...")
    
    # Check credentials
    if not mcp.config.app_id or not mcp.config.cert_id:
        await ctx.info("Using static product data - set credentials for live catalog")
        
        # Return static popular products
        products = STATIC_PRODUCT_DATA["popular_products"]
        
        # Simple filtering for demo
        if query:
            query_lower = query.lower()
            products = [p for p in products if query_lower in p["title"].lower()]
        elif brand:
            brand_lower = brand.lower()
            products = [p for p in products if brand_lower in p["brand"].lower()]
        elif category_ids:
            cat_id = category_ids.split(",")[0]
            products = [p for p in products if p["category_id"] == cat_id]
        
        return success_response(
            data={
                "products": products,
                "total_results": len(products),
                "offset": offset,
                "limit": limit,
                "data_source": "static_catalog",
                "note": "Live catalog data requires eBay API credentials"
            },
            message=f"Found {len(products)} products (static data)"
        ).to_json_string()
    
    # Validate input
    try:
        input_data = CatalogSearchInput(
            query=query,
            gtin=gtin,
            brand=brand,
            mpn=mpn,
            category_ids=category_ids,
            limit=limit,
            offset=offset
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
        await ctx.report_progress(0.3, "Searching product catalog...")
        
        # Build query parameters
        params = {
            "limit": input_data.limit,
            "offset": input_data.offset
        }
        
        # Add search criteria
        if input_data.query:
            params["q"] = input_data.query
        if input_data.gtin:
            params["gtin"] = input_data.gtin
        if input_data.brand:
            params["brand"] = input_data.brand
        if input_data.mpn:
            params["mpn"] = input_data.mpn
        if input_data.category_ids:
            params["category_ids"] = input_data.category_ids
        
        # Make API request
        response = await rest_client.get(
            "/commerce/catalog/v1/product_summary/search",
            params=params,
            scope=OAuthScopes.COMMERCE_CATALOG
        )
        
        await ctx.report_progress(0.8, "Processing product results...")
        
        # Parse response
        products = []
        for product_summary in response.get("productSummaries", []):
            try:
                product = _convert_product_summary(product_summary)
                products.append(product)
            except Exception as e:
                await ctx.error(f"Error parsing product: {str(e)}")
                continue
        
        total_results = response.get("total", 0)
        
        await ctx.report_progress(1.0, "Complete")
        await ctx.info(f"Found {len(products)} products (total: {total_results})")
        
        return success_response(
            data={
                "products": products,
                "total_results": total_results,
                "offset": input_data.offset,
                "limit": input_data.limit,
                "has_more": (input_data.offset + len(products)) < total_results,
                "search_criteria": {
                    "query": input_data.query,
                    "gtin": input_data.gtin,
                    "brand": input_data.brand,
                    "mpn": input_data.mpn,
                    "category_ids": input_data.category_ids
                },
                "data_source": "live_api"
            },
            message=f"Found {total_results} products in catalog"
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
            f"Failed to search catalog: {str(e)}"
        ).to_json_string()
    finally:
        await rest_client.close()


@mcp.tool
async def get_product_details(
    ctx: Context,
    epid: str
) -> str:
    """
    Get detailed information about a specific catalog product.
    
    Retrieves comprehensive product information including description,
    images, specifications, and marketplace availability.
    
    Args:
        epid: eBay Product ID
        ctx: MCP context
    
    Returns:
        JSON response with detailed product information
    """
    await ctx.info(f"Getting product details for ePID: {epid}")
    await ctx.report_progress(0.1, "Validating product ID...")
    
    # Check credentials
    if not mcp.config.app_id or not mcp.config.cert_id:
        # Return static product if it matches
        for product in STATIC_PRODUCT_DATA["popular_products"]:
            if product["epid"] == epid:
                return success_response(
                    data=product,
                    message="Product details (static data)"
                ).to_json_string()
        
        return error_response(
            ErrorCode.RESOURCE_NOT_FOUND,
            f"Product {epid} not found in static catalog"
        ).to_json_string()
    
    # Validate input
    try:
        input_data = ProductDetailsInput(epid=epid)
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
        await ctx.report_progress(0.3, "Fetching product details...")
        
        # Make API request
        response = await rest_client.get(
            f"/commerce/catalog/v1/product/{input_data.epid}",
            scope=OAuthScopes.COMMERCE_CATALOG
        )
        
        await ctx.report_progress(0.8, "Processing product data...")
        
        # Convert to our format
        product = _convert_catalog_product(response)
        
        await ctx.report_progress(1.0, "Complete")
        await ctx.info(f"Retrieved details for: {product['title']}")
        
        return success_response(
            data=product,
            message="Product details retrieved successfully"
        ).to_json_string()
        
    except EbayApiError as e:
        if e.status_code == 404:
            return error_response(
                ErrorCode.RESOURCE_NOT_FOUND,
                f"Product {epid} not found in catalog"
            ).to_json_string()
        await ctx.error(f"eBay API error: {str(e)}")
        return error_response(
            ErrorCode.EXTERNAL_API_ERROR,
            str(e),
            {"status_code": e.status_code, "epid": epid}
        ).to_json_string()
    except Exception as e:
        await ctx.error(f"Failed to get product details: {str(e)}")
        return error_response(
            ErrorCode.INTERNAL_ERROR,
            f"Failed to get product details: {str(e)}"
        ).to_json_string()
    finally:
        await rest_client.close()


@mcp.tool
async def find_products_by_image(
    ctx: Context,
    image_url: str,
    limit: int = 20
) -> str:
    """
    Find products using image recognition.
    
    Uses eBay's image recognition to find similar products based on an image.
    Useful for identifying products from photos.
    
    Args:
        image_url: URL of the image to search with
        limit: Number of results to return (max 50)
        ctx: MCP context
    
    Returns:
        JSON response with matching products
    """
    await ctx.info(f"Searching by image: {image_url}")
    
    # Check credentials
    if not mcp.config.app_id or not mcp.config.cert_id:
        return success_response(
            data={
                "products": [],
                "image_url": image_url,
                "data_source": "static_fallback",
                "note": "Image search requires eBay API credentials"
            },
            message="Image search not available without credentials"
        ).to_json_string()
    
    # Validate URL
    if not image_url.startswith(('http://', 'https://')):
        return error_response(
            ErrorCode.VALIDATION_ERROR,
            "Image URL must start with http:// or https://"
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
        await ctx.report_progress(0.3, "Analyzing image...")
        
        # Make API request
        response = await rest_client.get(
            "/commerce/catalog/v1/product_summary/search",
            params={
                "image": image_url,
                "limit": min(limit, 50)
            },
            scope=OAuthScopes.COMMERCE_CATALOG
        )
        
        await ctx.report_progress(0.8, "Processing results...")
        
        # Parse response
        products = []
        for product_summary in response.get("productSummaries", []):
            try:
                product = _convert_product_summary(product_summary)
                products.append(product)
            except Exception as e:
                await ctx.error(f"Error parsing product: {str(e)}")
                continue
        
        await ctx.report_progress(1.0, "Complete")
        await ctx.info(f"Found {len(products)} products from image")
        
        return success_response(
            data={
                "products": products,
                "image_url": image_url,
                "total_results": len(products),
                "data_source": "live_api"
            },
            message=f"Found {len(products)} products matching image"
        ).to_json_string()
        
    except EbayApiError as e:
        await ctx.error(f"eBay API error: {str(e)}")
        return error_response(
            ErrorCode.EXTERNAL_API_ERROR,
            str(e),
            {"status_code": e.status_code, "image_url": image_url}
        ).to_json_string()
    except Exception as e:
        await ctx.error(f"Image search failed: {str(e)}")
        return error_response(
            ErrorCode.INTERNAL_ERROR,
            f"Failed to search by image: {str(e)}"
        ).to_json_string()
    finally:
        await rest_client.close()


@mcp.tool
async def get_product_aspects(
    ctx: Context,
    epid: str
) -> str:
    """
    Get item aspects for a specific catalog product.
    
    Returns the standard aspects/attributes associated with a product,
    useful for creating accurate listings.
    
    Args:
        epid: eBay Product ID
        ctx: MCP context
    
    Returns:
        JSON response with product aspects
    """
    await ctx.info(f"Getting aspects for product: {epid}")
    
    # For now, delegate to get_product_details and extract aspects
    result = await get_product_details.fn(ctx=ctx, epid=epid)
    
    try:
        result_data = json.loads(result)
        if result_data["status"] == "success":
            product = result_data["data"]
            aspects = product.get("aspects", {})
            
            return success_response(
                data={
                    "epid": epid,
                    "aspects": aspects,
                    "total_aspects": len(aspects)
                },
                message=f"Found {len(aspects)} aspects for product"
            ).to_json_string()
        else:
            # Return the error as-is
            return result
            
    except Exception as e:
        await ctx.error(f"Failed to extract aspects: {str(e)}")
        return error_response(
            ErrorCode.INTERNAL_ERROR,
            f"Failed to get product aspects: {str(e)}"
        ).to_json_string()


@mcp.tool
async def get_product_reviews_summary(
    ctx: Context,
    epid: str
) -> str:
    """
    Get review summary for a catalog product.
    
    Returns aggregated review data including ratings and review counts.
    
    Args:
        epid: eBay Product ID
        ctx: MCP context
    
    Returns:
        JSON response with review summary
    """
    await ctx.info(f"Getting review summary for product: {epid}")
    
    # Check credentials
    if not mcp.config.app_id or not mcp.config.cert_id:
        return success_response(
            data={
                "epid": epid,
                "reviews": {
                    "average_rating": 0,
                    "total_reviews": 0,
                    "rating_distribution": {}
                },
                "data_source": "static_fallback",
                "note": "Review data requires eBay API credentials"
            },
            message="Review data not available without credentials"
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
        # Make API request
        response = await rest_client.get(
            f"/commerce/catalog/v1/product/{epid}/get_product_reviews",
            scope=OAuthScopes.COMMERCE_CATALOG
        )
        
        # Parse review data
        reviews = response.get("reviews", {})
        rating_distribution = response.get("ratingDistribution", {})
        
        await ctx.info(f"Retrieved review summary")
        
        return success_response(
            data={
                "epid": epid,
                "reviews": {
                    "average_rating": reviews.get("averageRating", 0),
                    "total_reviews": reviews.get("totalReviews", 0),
                    "rating_distribution": rating_distribution
                },
                "data_source": "live_api"
            },
            message="Review summary retrieved successfully"
        ).to_json_string()
        
    except EbayApiError as e:
        if e.status_code == 404:
            return error_response(
                ErrorCode.RESOURCE_NOT_FOUND,
                f"No reviews found for product {epid}"
            ).to_json_string()
        await ctx.error(f"eBay API error: {str(e)}")
        return error_response(
            ErrorCode.EXTERNAL_API_ERROR,
            str(e),
            {"status_code": e.status_code, "epid": epid}
        ).to_json_string()
    except Exception as e:
        await ctx.error(f"Failed to get reviews: {str(e)}")
        return error_response(
            ErrorCode.INTERNAL_ERROR,
            f"Failed to get product reviews: {str(e)}"
        ).to_json_string()
    finally:
        await rest_client.close()