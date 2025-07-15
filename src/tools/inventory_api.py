"""
eBay Inventory API tools for modern listing management.

Provides access to eBay's Inventory API for creating and managing
inventory items, offers, and listings using the new REST architecture.
"""
from typing import Dict, Any, Optional, List, Union
from fastmcp import Context
from pydantic import BaseModel, Field, field_validator, ConfigDict
from datetime import datetime
import json

from api.oauth import OAuthManager, OAuthConfig, OAuthScopes
from api.rest_client import EbayRestClient, RestConfig
from api.errors import EbayApiError, ValidationError as ApiValidationError
from api.cache import CacheTTL
from data_types import success_response, error_response, ErrorCode
from lootly_server import mcp
from tools.oauth_consent import get_user_access_token


async def _check_user_consent(ctx: Context) -> Optional[str]:
    """Check if user has valid consent and return access token."""
    if not mcp.config.app_id:
        return None
    
    user_token = await get_user_access_token(mcp.config.app_id)
    if not user_token:
        await ctx.info("⚠️  User consent required for Inventory API. Use check_user_consent_status and initiate_user_consent tools.")
        return None
    
    return user_token


class InventoryItemInput(BaseModel):
    """Input validation for inventory item creation."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    sku: str = Field(..., min_length=1, max_length=50, description="Seller-defined SKU")
    title: str = Field(..., min_length=1, max_length=80, description="Item title")
    description: str = Field(..., min_length=1, description="Item description")
    category_id: str = Field(..., description="eBay category ID")
    brand: Optional[str] = Field(None, description="Brand name")
    mpn: Optional[str] = Field(None, description="Manufacturer Part Number")
    upc: Optional[str] = Field(None, description="Universal Product Code")
    price: float = Field(..., gt=0, description="Item price")
    currency: str = Field(default="USD", description="Currency code")
    quantity: int = Field(..., ge=0, description="Available quantity")
    condition: str = Field(default="NEW", description="Item condition")
    
    @field_validator('sku')
    @classmethod
    def validate_sku(cls, v):
        # SKU must be alphanumeric with hyphens/underscores
        if not v.replace('-', '').replace('_', '').isalnum():
            raise ValueError("SKU must contain only alphanumeric characters, hyphens, and underscores")
        return v
    
    @field_validator('condition')
    @classmethod
    def validate_condition(cls, v):
        valid_conditions = ["NEW", "LIKE_NEW", "USED_EXCELLENT", "USED_VERY_GOOD", "USED_GOOD", "USED_ACCEPTABLE", "FOR_PARTS_OR_NOT_WORKING"]
        if v not in valid_conditions:
            raise ValueError(f"Condition must be one of: {', '.join(valid_conditions)}")
        return v


class OfferInput(BaseModel):
    """Input validation for offer creation."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    sku: str = Field(..., min_length=1, description="Inventory item SKU")
    marketplace_id: str = Field(default="EBAY_US", description="Marketplace ID")
    format: str = Field(default="FIXED_PRICE", description="Listing format")
    duration: str = Field(default="GTC", description="Listing duration")
    category_id: str = Field(..., description="eBay category ID")
    listing_policies: Optional[Dict[str, str]] = Field(None, description="Business policy IDs")
    
    @field_validator('format')
    @classmethod
    def validate_format(cls, v):
        valid_formats = ["FIXED_PRICE", "AUCTION"]
        if v not in valid_formats:
            raise ValueError(f"Format must be one of: {', '.join(valid_formats)}")
        return v


class InventorySearchInput(BaseModel):
    """Input validation for inventory search."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    sku: Optional[str] = Field(None, description="Search by SKU")
    title: Optional[str] = Field(None, description="Search by title")
    limit: int = Field(25, ge=1, le=200, description="Results per page")
    offset: int = Field(0, ge=0, description="Result offset")


def _convert_inventory_item(item: Dict[str, Any]) -> Dict[str, Any]:
    """Convert API inventory item to our format."""
    # Extract availability info
    availability = item.get("availability", {})
    
    # Extract product details
    product = item.get("product", {})
    
    # Extract pricing
    pricing = item.get("pricing", {})
    
    return {
        "sku": item.get("sku"),
        "title": product.get("title"),
        "description": product.get("description"),
        "brand": product.get("brand"),
        "mpn": product.get("mpn"),
        "upc": product.get("upc"),
        "condition": item.get("condition"),
        "condition_description": item.get("conditionDescription"),
        "category_id": product.get("categoryId"),
        "price": pricing.get("price", {}).get("value"),
        "currency": pricing.get("price", {}).get("currency"),
        "quantity": availability.get("shipToLocationAvailability", {}).get("quantity", 0),
        "images": product.get("imageUrls", []),
        "aspects": product.get("aspects", {}),
        "created_date": item.get("createdDate"),
        "last_modified_date": item.get("lastModifiedDate"),
        "status": item.get("status", "ACTIVE")
    }


def _convert_offer(offer: Dict[str, Any]) -> Dict[str, Any]:
    """Convert API offer to our format."""
    # Extract listing details
    listing = offer.get("listing", {})
    
    return {
        "offer_id": offer.get("offerId"),
        "sku": offer.get("sku"),
        "marketplace_id": offer.get("marketplaceId"),
        "format": offer.get("format"),
        "duration": listing.get("duration"),
        "category_id": offer.get("categoryId"),
        "listing_id": listing.get("listingId"),
        "listing_status": listing.get("listingStatus"),
        "quantity_sold": offer.get("quantitySold", 0),
        "available_quantity": offer.get("availableQuantity", 0),
        "price": offer.get("pricingSummary", {}).get("price", {}).get("value"),
        "currency": offer.get("pricingSummary", {}).get("price", {}).get("currency"),
        "created_date": offer.get("createdDate"),
        "last_modified_date": offer.get("lastModifiedDate"),
        "status": offer.get("status", "PUBLISHED")
    }


# Static fallback data for inventory items
STATIC_INVENTORY_ITEMS = [
    {
        "sku": "SAMPLE-001",
        "title": "Sample Product for Testing",
        "description": "This is a sample product for testing purposes",
        "brand": "Generic",
        "mpn": "SAMPLE001",
        "upc": "123456789012",
        "condition": "NEW",
        "category_id": "166",
        "price": 29.99,
        "currency": "USD",
        "quantity": 10,
        "images": ["https://example.com/sample.jpg"],
        "aspects": {"Color": "Blue", "Size": "Medium"},
        "status": "ACTIVE"
    }
]


@mcp.tool
async def create_inventory_item(
    ctx: Context,
    sku: str,
    title: str,
    description: str,
    category_id: str,
    price: float,
    quantity: int,
    brand: Optional[str] = None,
    mpn: Optional[str] = None,
    upc: Optional[str] = None,
    currency: str = "USD",
    condition: str = "NEW"
) -> str:
    """
    Create or update an inventory item.
    
    Creates a new inventory item that can be used to create offers/listings.
    This is the foundation for modern eBay listing management.
    
    Args:
        sku: Seller-defined SKU (must be unique)
        title: Item title (max 80 characters)
        description: Item description
        category_id: eBay category ID
        price: Item price
        quantity: Available quantity
        brand: Brand name (optional)
        mpn: Manufacturer Part Number (optional)
        upc: Universal Product Code (optional)
        currency: Currency code (default: USD)
        condition: Item condition (default: NEW)
        ctx: MCP context
    
    Returns:
        JSON response with inventory item details
    """
    await ctx.info(f"Creating inventory item: {sku}")
    await ctx.report_progress(0.1, "Validating inventory item data...")
    
    # Check credentials
    if not mcp.config.app_id or not mcp.config.cert_id:
        await ctx.info("Using static inventory data - set credentials for live inventory")
        
        # Return static inventory item
        static_item = {
            "sku": sku,
            "title": title,
            "description": description,
            "brand": brand,
            "mpn": mpn,
            "upc": upc,
            "condition": condition,
            "category_id": category_id,
            "price": price,
            "currency": currency,
            "quantity": quantity,
            "images": [],
            "aspects": {},
            "status": "ACTIVE",
            "created_date": datetime.utcnow().isoformat() + "Z"
        }
        
        return success_response(
            data={
                "inventory_item": static_item,
                "data_source": "static_fallback",
                "note": "Live inventory management requires eBay API credentials"
            },
            message=f"Inventory item {sku} created (static data)"
        ).to_json_string()
    
    # Check user consent
    user_token = await _check_user_consent(ctx)
    if not user_token:
        return error_response(
            ErrorCode.AUTHENTICATION_ERROR,
            "User consent required for Inventory API. Use initiate_user_consent to authorize access.",
            {"required_scopes": OAuthScopes.USER_CONSENT_SCOPES.split()}
        ).to_json_string()
    
    # Validate input
    try:
        input_data = InventoryItemInput(
            sku=sku,
            title=title,
            description=description,
            category_id=category_id,
            brand=brand,
            mpn=mpn,
            upc=upc,
            price=price,
            currency=currency,
            quantity=quantity,
            condition=condition
        )
    except Exception as e:
        await ctx.error(f"Validation error: {str(e)}")
        return error_response(
            ErrorCode.VALIDATION_ERROR,
            str(e)
        ).to_json_string()
    
    # Initialize API clients with user token
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
    
    # Override with user token
    rest_client._user_token = user_token
    
    try:
        await ctx.report_progress(0.3, "Creating inventory item...")
        
        # Build inventory item payload
        inventory_item = {
            "availability": {
                "shipToLocationAvailability": {
                    "quantity": input_data.quantity
                }
            },
            "condition": input_data.condition,
            "product": {
                "title": input_data.title,
                "description": input_data.description,
                "categoryId": input_data.category_id,
                "aspects": {}
            },
            "pricing": {
                "price": {
                    "value": str(input_data.price),
                    "currency": input_data.currency
                }
            }
        }
        
        # Add optional fields
        if input_data.brand:
            inventory_item["product"]["brand"] = input_data.brand
        if input_data.mpn:
            inventory_item["product"]["mpn"] = input_data.mpn
        if input_data.upc:
            inventory_item["product"]["upc"] = input_data.upc
        
        # Make API request
        response = await rest_client.put(
            f"/sell/inventory/v1/inventory_item/{input_data.sku}",
            json=inventory_item,
            scope=OAuthScopes.SELL_INVENTORY
        )
        
        await ctx.report_progress(0.8, "Processing inventory item response...")
        
        # Get the created item
        get_response = await rest_client.get(
            f"/sell/inventory/v1/inventory_item/{input_data.sku}",
            scope=OAuthScopes.SELL_INVENTORY
        )
        
        # Convert to our format
        item = _convert_inventory_item(get_response)
        
        # Cache the item
        if mcp.cache_manager:
            await mcp.cache_manager.set(
                f"inventory:item:{input_data.sku}",
                item,
                CacheTTL.BUSINESS_POLICIES
            )
        
        await ctx.report_progress(1.0, "Complete")
        await ctx.info(f"Successfully created inventory item: {input_data.sku}")
        
        return success_response(
            data={
                "inventory_item": item,
                "data_source": "live_api"
            },
            message=f"Inventory item {input_data.sku} created successfully"
        ).to_json_string()
        
    except EbayApiError as e:
        await ctx.error(f"eBay API error: {str(e)}")
        return error_response(
            ErrorCode.EXTERNAL_API_ERROR,
            str(e),
            {"status_code": e.status_code, "sku": sku}
        ).to_json_string()
    except Exception as e:
        await ctx.error(f"Failed to create inventory item: {str(e)}")
        return error_response(
            ErrorCode.INTERNAL_ERROR,
            f"Failed to create inventory item: {str(e)}"
        ).to_json_string()
    finally:
        await rest_client.close()


@mcp.tool
async def get_inventory_items(
    ctx: Context,
    sku: Optional[str] = None,
    title: Optional[str] = None,
    limit: int = 25,
    offset: int = 0
) -> str:
    """
    Get inventory items for the seller.
    
    Retrieves inventory items based on search criteria.
    
    Args:
        sku: Search by specific SKU (optional)
        title: Search by title (optional)
        limit: Number of items to return (default: 25)
        offset: Pagination offset (default: 0)
        ctx: MCP context
    
    Returns:
        JSON response with inventory items
    """
    await ctx.info(f"Getting inventory items (limit: {limit}, offset: {offset})")
    await ctx.report_progress(0.1, "Validating search parameters...")
    
    # Check credentials
    if not mcp.config.app_id or not mcp.config.cert_id:
        await ctx.info("Using static inventory data - set credentials for live inventory")
        
        # Return static inventory items
        items = STATIC_INVENTORY_ITEMS
        
        # Simple filtering
        if sku:
            items = [item for item in items if item["sku"] == sku]
        elif title:
            title_lower = title.lower()
            items = [item for item in items if title_lower in item["title"].lower()]
        
        return success_response(
            data={
                "inventory_items": items,
                "total_items": len(items),
                "offset": offset,
                "limit": limit,
                "data_source": "static_fallback",
                "note": "Live inventory data requires eBay API credentials"
            },
            message=f"Found {len(items)} inventory items (static data)"
        ).to_json_string()
    
    # Check user consent
    user_token = await _check_user_consent(ctx)
    if not user_token:
        return error_response(
            ErrorCode.AUTHENTICATION_ERROR,
            "User consent required for Inventory API. Use initiate_user_consent to authorize access.",
            {"required_scopes": OAuthScopes.USER_CONSENT_SCOPES.split()}
        ).to_json_string()
    
    # Validate input
    try:
        input_data = InventorySearchInput(
            sku=sku,
            title=title,
            limit=limit,
            offset=offset
        )
    except Exception as e:
        await ctx.error(f"Validation error: {str(e)}")
        return error_response(
            ErrorCode.VALIDATION_ERROR,
            str(e)
        ).to_json_string()
    
    # Initialize API clients with user token
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
    
    # Override with user token
    rest_client._user_token = user_token
    
    try:
        await ctx.report_progress(0.3, "Searching inventory items...")
        
        # Build query parameters
        params = {
            "limit": input_data.limit,
            "offset": input_data.offset
        }
        
        # Add search filters
        if input_data.sku:
            params["sku"] = input_data.sku
        if input_data.title:
            params["title"] = input_data.title
        
        # Make API request
        response = await rest_client.get(
            "/sell/inventory/v1/inventory_item",
            params=params,
            scope=OAuthScopes.SELL_INVENTORY
        )
        
        await ctx.report_progress(0.8, "Processing inventory items...")
        
        # Parse response
        items = []
        for item in response.get("inventoryItems", []):
            try:
                converted_item = _convert_inventory_item(item)
                items.append(converted_item)
            except Exception as e:
                await ctx.error(f"Error parsing inventory item: {str(e)}")
                continue
        
        total_items = response.get("total", len(items))
        
        await ctx.report_progress(1.0, "Complete")
        await ctx.info(f"Found {len(items)} inventory items")
        
        return success_response(
            data={
                "inventory_items": items,
                "total_items": total_items,
                "offset": input_data.offset,
                "limit": input_data.limit,
                "has_more": (input_data.offset + len(items)) < total_items,
                "data_source": "live_api"
            },
            message=f"Found {total_items} inventory items"
        ).to_json_string()
        
    except EbayApiError as e:
        await ctx.error(f"eBay API error: {str(e)}")
        return error_response(
            ErrorCode.EXTERNAL_API_ERROR,
            str(e),
            {"status_code": e.status_code}
        ).to_json_string()
    except Exception as e:
        await ctx.error(f"Failed to get inventory items: {str(e)}")
        return error_response(
            ErrorCode.INTERNAL_ERROR,
            f"Failed to get inventory items: {str(e)}"
        ).to_json_string()
    finally:
        await rest_client.close()


@mcp.tool
async def create_offer(
    ctx: Context,
    sku: str,
    category_id: str,
    marketplace_id: str = "EBAY_US",
    format: str = "FIXED_PRICE",
    duration: str = "GTC",
    payment_policy_id: Optional[str] = None,
    shipping_policy_id: Optional[str] = None,
    return_policy_id: Optional[str] = None,
    fulfillment_policy_id: Optional[str] = None
) -> str:
    """
    Create an offer for an inventory item.
    
    Creates an offer that can be published as a listing on eBay.
    The inventory item must exist before creating an offer.
    
    Args:
        sku: Inventory item SKU
        category_id: eBay category ID
        marketplace_id: Marketplace ID (default: EBAY_US)
        format: Listing format (default: FIXED_PRICE)
        duration: Listing duration (default: GTC)
        payment_policy_id: Payment policy ID (optional)
        shipping_policy_id: Shipping policy ID (optional)
        return_policy_id: Return policy ID (optional)
        fulfillment_policy_id: Fulfillment policy ID (optional)
        ctx: MCP context
    
    Returns:
        JSON response with offer details
    """
    await ctx.info(f"Creating offer for SKU: {sku}")
    await ctx.report_progress(0.1, "Validating offer data...")
    
    # Check credentials
    if not mcp.config.app_id or not mcp.config.cert_id:
        await ctx.info("Using static offer data - set credentials for live offers")
        
        # Return static offer
        static_offer = {
            "offer_id": f"offer_{sku}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            "sku": sku,
            "marketplace_id": marketplace_id,
            "format": format,
            "duration": duration,
            "category_id": category_id,
            "listing_id": None,
            "listing_status": "DRAFT",
            "quantity_sold": 0,
            "available_quantity": 0,
            "price": None,
            "currency": "USD",
            "created_date": datetime.utcnow().isoformat() + "Z",
            "status": "UNPUBLISHED"
        }
        
        return success_response(
            data={
                "offer": static_offer,
                "data_source": "static_fallback",
                "note": "Live offer management requires eBay API credentials"
            },
            message=f"Offer created for SKU {sku} (static data)"
        ).to_json_string()
    
    # Check user consent
    user_token = await _check_user_consent(ctx)
    if not user_token:
        return error_response(
            ErrorCode.AUTHENTICATION_ERROR,
            "User consent required for Inventory API. Use initiate_user_consent to authorize access.",
            {"required_scopes": OAuthScopes.USER_CONSENT_SCOPES.split()}
        ).to_json_string()
    
    # Validate input
    try:
        # Build listing policies dict, filtering out None values
        listing_policies = {}
        if payment_policy_id:
            listing_policies["paymentPolicyId"] = payment_policy_id
        if shipping_policy_id:
            listing_policies["shippingPolicyId"] = shipping_policy_id
        if return_policy_id:
            listing_policies["returnPolicyId"] = return_policy_id
        if fulfillment_policy_id:
            listing_policies["fulfillmentPolicyId"] = fulfillment_policy_id
        
        input_data = OfferInput(
            sku=sku,
            marketplace_id=marketplace_id,
            format=format,
            duration=duration,
            category_id=category_id,
            listing_policies=listing_policies if listing_policies else None
        )
    except Exception as e:
        await ctx.error(f"Validation error: {str(e)}")
        return error_response(
            ErrorCode.VALIDATION_ERROR,
            str(e)
        ).to_json_string()
    
    # Initialize API clients with user token
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
    
    # Override with user token
    rest_client._user_token = user_token
    
    try:
        await ctx.report_progress(0.3, "Creating offer...")
        
        # Build offer payload
        offer_data = {
            "sku": input_data.sku,
            "marketplaceId": input_data.marketplace_id,
            "format": input_data.format,
            "categoryId": input_data.category_id,
            "listingDuration": input_data.duration,
            "listingPolicies": {}
        }
        
        # Add policy IDs if provided
        if input_data.listing_policies:
            offer_data["listingPolicies"].update(input_data.listing_policies)
        
        # Make API request
        response = await rest_client.post(
            "/sell/inventory/v1/offer",
            json=offer_data,
            scope=OAuthScopes.SELL_INVENTORY
        )
        
        await ctx.report_progress(0.8, "Processing offer response...")
        
        # Convert to our format
        offer = _convert_offer(response)
        
        # Cache the offer
        if mcp.cache_manager:
            await mcp.cache_manager.set(
                f"inventory:offer:{offer['offer_id']}",
                offer,
                CacheTTL.BUSINESS_POLICIES
            )
        
        await ctx.report_progress(1.0, "Complete")
        await ctx.info(f"Successfully created offer: {offer['offer_id']}")
        
        return success_response(
            data={
                "offer": offer,
                "data_source": "live_api"
            },
            message=f"Offer created successfully"
        ).to_json_string()
        
    except EbayApiError as e:
        await ctx.error(f"eBay API error: {str(e)}")
        return error_response(
            ErrorCode.EXTERNAL_API_ERROR,
            str(e),
            {"status_code": e.status_code, "sku": sku}
        ).to_json_string()
    except Exception as e:
        await ctx.error(f"Failed to create offer: {str(e)}")
        return error_response(
            ErrorCode.INTERNAL_ERROR,
            f"Failed to create offer: {str(e)}"
        ).to_json_string()
    finally:
        await rest_client.close()


@mcp.tool
async def publish_offer(
    ctx: Context,
    offer_id: str
) -> str:
    """
    Publish an offer to create a live listing.
    
    Publishes an offer to eBay, creating a live listing that buyers can purchase.
    
    Args:
        offer_id: The offer ID to publish
        ctx: MCP context
    
    Returns:
        JSON response with publication status
    """
    await ctx.info(f"Publishing offer: {offer_id}")
    await ctx.report_progress(0.1, "Validating offer...")
    
    # Check credentials
    if not mcp.config.app_id or not mcp.config.cert_id:
        return success_response(
            data={
                "offer_id": offer_id,
                "listing_id": f"listing_{offer_id}",
                "status": "PUBLISHED",
                "data_source": "static_fallback",
                "note": "Live offer publishing requires eBay API credentials"
            },
            message=f"Offer {offer_id} published (static data)"
        ).to_json_string()
    
    # Check user consent
    user_token = await _check_user_consent(ctx)
    if not user_token:
        return error_response(
            ErrorCode.AUTHENTICATION_ERROR,
            "User consent required for Inventory API. Use initiate_user_consent to authorize access.",
            {"required_scopes": OAuthScopes.USER_CONSENT_SCOPES.split()}
        ).to_json_string()
    
    # Initialize API clients with user token
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
    
    # Override with user token
    rest_client._user_token = user_token
    
    try:
        await ctx.report_progress(0.3, "Publishing offer...")
        
        # Make API request
        response = await rest_client.post(
            f"/sell/inventory/v1/offer/{offer_id}/publish",
            scope=OAuthScopes.SELL_INVENTORY
        )
        
        await ctx.report_progress(0.8, "Processing publication response...")
        
        # Extract listing ID from response
        listing_id = response.get("listingId")
        
        # Invalidate cache
        if mcp.cache_manager:
            await mcp.cache_manager.delete(f"inventory:offer:{offer_id}")
        
        await ctx.report_progress(1.0, "Complete")
        await ctx.info(f"Successfully published offer {offer_id} as listing {listing_id}")
        
        return success_response(
            data={
                "offer_id": offer_id,
                "listing_id": listing_id,
                "status": "PUBLISHED",
                "data_source": "live_api"
            },
            message=f"Offer {offer_id} published successfully as listing {listing_id}"
        ).to_json_string()
        
    except EbayApiError as e:
        await ctx.error(f"eBay API error: {str(e)}")
        return error_response(
            ErrorCode.EXTERNAL_API_ERROR,
            str(e),
            {"status_code": e.status_code, "offer_id": offer_id}
        ).to_json_string()
    except Exception as e:
        await ctx.error(f"Failed to publish offer: {str(e)}")
        return error_response(
            ErrorCode.INTERNAL_ERROR,
            f"Failed to publish offer: {str(e)}"
        ).to_json_string()
    finally:
        await rest_client.close()