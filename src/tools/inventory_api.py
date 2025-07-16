"""
eBay Inventory API tools for modern listing management.

Provides access to eBay's Inventory API for creating and managing
inventory items, offers, and listings using the new REST architecture.
"""
from typing import Dict, Any, Optional, List, Union
from fastmcp import Context
from pydantic import BaseModel, Field, field_validator, ConfigDict
from datetime import datetime, timezone
import json

from api.oauth import OAuthManager, OAuthConfig, OAuthScopes
from api.rest_client import EbayRestClient, RestConfig
from api.errors import EbayApiError, ValidationError as ApiValidationError
from api.cache import CacheTTL
from api.sandbox_retry import with_sandbox_retry, handle_inventory_error, RetryConfig
from api.inline_policies import (
    CompletePolicySet, InlinePaymentPolicy, InlineShippingPolicy, InlineReturnPolicy,
    create_basic_policies, create_premium_policies, create_auction_policies, create_no_returns_policies
)
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
        "price": float(pricing.get("price", {}).get("value", 0)) if pricing.get("price", {}).get("value") else 0.0,
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
            "created_date": datetime.now(timezone.utc).isoformat() + "Z"
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
        
        # Create helpful URLs for the user
        seller_hub_url = "https://www.ebay.com/sh/ovw"
        inventory_url = "https://www.ebay.com/sh/lst?ListingType=Active"
        create_offer_url = f"https://www.ebay.com/sh/lst/drafts"
        category_research_url = f"https://www.ebay.com/sch/i.html?_nkw={input_data.title.replace(' ', '+')}"
        
        return success_response(
            data={
                "inventory_item": item,
                "data_source": "live_api",
                "urls": {
                    "seller_hub": seller_hub_url,
                    "inventory_management": inventory_url,
                    "create_offer": create_offer_url,
                    "category_research": category_research_url,
                    "help_url": "https://www.ebay.com/help/selling/listings/creating-managing-listings"
                },
                "next_steps": [
                    f"📦 Inventory item '{input_data.sku}' created successfully",
                    f"🎯 Next: Create an offer to list this item for sale",
                    f"💡 Use create_offer(sku='{input_data.sku}', category_id='{input_data.category_id}')",
                    f"📊 Monitor performance: {seller_hub_url}",
                    f"🔍 Research competition: {category_research_url}"
                ],
                "recommendations": {
                    "immediate_action": f"Create offer with create_offer(sku='{input_data.sku}', category_id='{input_data.category_id}')",
                    "pricing_strategy": "Research similar items before setting final price",
                    "optimization": "Add high-quality images and detailed descriptions for better performance"
                }
            },
            message=f"✅ Inventory item {input_data.sku} created - ready for offer creation"
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
        
        # Define the API call function for retry logic
        async def make_inventory_request():
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
            return await rest_client.get(
                "/sell/inventory/v1/inventory_item",
                params=params,
                scope=OAuthScopes.SELL_INVENTORY
            )
        
        # Execute with enhanced sandbox retry logic
        retry_config = RetryConfig(
            max_attempts=3,
            base_delay=2.0,  # Slightly longer delays for inventory API
            max_delay=15.0   # Cap at 15 seconds for better UX
        )
        
        response = await with_sandbox_retry(
            make_inventory_request,
            ctx=ctx,
            retry_config=retry_config
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
                "data_source": "live_api",
                "sandbox_retry_enabled": True
            },
            message=f"Found {total_items} inventory items"
        ).to_json_string()
        
    except EbayApiError as e:
        # Try to handle known sandbox errors with smart fallbacks
        fallback_response = await handle_inventory_error(e, ctx)
        if fallback_response:
            return fallback_response
            
        await ctx.error(f"eBay API error (after retries): {str(e)}")
        return error_response(
            ErrorCode.EXTERNAL_API_ERROR,
            str(e),
            {
                "status_code": e.status_code,
                "retry_attempted": True,
                "error_type": "ebay_api_error"
            }
        ).to_json_string()
    except Exception as e:
        # Try to handle any unexpected inventory errors
        fallback_response = await handle_inventory_error(e, ctx)
        if fallback_response:
            return fallback_response
            
        await ctx.error(f"Failed to get inventory items (after retries): {str(e)}")
        return error_response(
            ErrorCode.INTERNAL_ERROR,
            f"Failed to get inventory items: {str(e)}",
            {"retry_attempted": True, "error_type": "unexpected_error"}
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
    policy_type: str = "standard",
    shipping_cost: Optional[float] = None,
    payment_email: str = "seller@example.com",
    return_days: Optional[int] = None,
    merchant_location_key: str = "DEFAULT"
) -> str:
    """
    Create an offer for an inventory item using modern inline policies.
    
    Creates an offer that can be published as a listing on eBay.
    Uses structured inline payment, shipping, and return policies instead of requiring
    Business Policy IDs. Supports multiple policy templates for different use cases.
    
    Args:
        sku: Inventory item SKU
        category_id: eBay category ID
        marketplace_id: Marketplace ID (default: EBAY_US)
        format: Listing format (default: FIXED_PRICE)
        duration: Listing duration (default: GTC)
        policy_type: Policy template - 'standard', 'premium', 'auction', 'no_returns' (default: standard)
        shipping_cost: Shipping cost - if None, uses policy defaults
        payment_email: PayPal email for payments (default: seller@example.com)
        return_days: Return period in days - if None, uses policy defaults
        merchant_location_key: Location key (default: DEFAULT)
        ctx: MCP context
    
    Returns:
        JSON response with offer details including listing URL
    """
    await ctx.info(f"Creating offer for SKU: {sku}")
    await ctx.report_progress(0.1, "Validating offer data...")
    
    # Check credentials
    if not mcp.config.app_id or not mcp.config.cert_id:
        await ctx.info("Using static offer data - set credentials for live offers")
        
        # Return static offer
        static_offer = {
            "offer_id": f"offer_{sku}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
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
            "created_date": datetime.now(timezone.utc).isoformat() + "Z",
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
        input_data = OfferInput(
            sku=sku,
            marketplace_id=marketplace_id,
            format=format,
            duration=duration,
            category_id=category_id
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
        await ctx.report_progress(0.3, "Creating offer with structured inline policies...")
        
        # Create appropriate policy set based on policy_type
        if policy_type == "premium":
            policies = create_premium_policies(
                paypal_email=payment_email,
                free_shipping=shipping_cost == 0 if shipping_cost is not None else True,
                extended_returns=return_days is None or return_days >= 60
            )
        elif policy_type == "auction":
            policies = create_auction_policies(
                paypal_email=payment_email,
                shipping_cost=shipping_cost if shipping_cost is not None else 9.99
            )
        elif policy_type == "no_returns":
            policies = create_no_returns_policies(
                paypal_email=payment_email,
                shipping_cost=shipping_cost if shipping_cost is not None else 6.99
            )
        else:  # standard
            policies = create_basic_policies(
                paypal_email=payment_email,
                shipping_cost=shipping_cost if shipping_cost is not None else 4.99,
                return_days=return_days if return_days is not None else 30
            )
        
        # Override with custom values if provided
        if shipping_cost is not None and policy_type in ["standard", "premium"]:
            if shipping_cost == 0:
                policies.shipping_policy = InlineShippingPolicy.create_free_shipping_policy()
            else:
                policies.shipping_policy = InlineShippingPolicy.create_flat_rate_policy(shipping_cost)
        
        if return_days is not None and policy_type != "no_returns":
            policies.return_policy = InlineReturnPolicy.create_standard_policy(return_days)
        
        # Convert policies to eBay API format
        policy_data = policies.to_ebay_format()
        
        # Build offer payload with structured policies
        offer_data = {
            "sku": input_data.sku,
            "marketplaceId": input_data.marketplace_id,
            "format": input_data.format,
            "categoryId": input_data.category_id,
            "listingDuration": input_data.duration,
            "merchantLocationKey": merchant_location_key,
            **policy_data
        }
        
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
        
        # Build helpful URLs
        base_url = "https://sandbox.ebay.com" if mcp.config.sandbox_mode else "https://www.ebay.com"
        seller_hub_url = f"{base_url}/sh/lstg/drft"  # Draft listings
        seller_hub_offers_url = f"{base_url}/sh/sellr/offers"
        
        return success_response(
            data={
                "offer": offer,
                "offer_id": offer['offer_id'],
                "sku": offer['sku'],
                "status": "CREATED",
                "policy_type_used": policy_type,
                "data_source": "live_api",
                "urls": {
                    "seller_hub_drafts": seller_hub_url,
                    "seller_hub_offers": seller_hub_offers_url,
                    "help_url": "https://www.ebay.com/help/selling"
                },
                "next_steps": [
                    f"📋 Offer created successfully with {policy_type} policies",
                    f"🚀 Use publish_offer('{offer['offer_id']}') to create live listing",
                    f"📊 View draft listings: {seller_hub_url}",
                    f"🔧 Modify with update_offer('{offer['offer_id']}', ...) if needed"
                ],
                "sandbox_retry_enabled": True
            },
            message=f"Offer created successfully with inline policies"
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
        
        # Build URLs for viewing the listing
        base_url = "https://sandbox.ebay.com" if mcp.config.sandbox_mode else "https://www.ebay.com"
        listing_url = f"{base_url}/itm/{listing_id}"
        seller_hub_url = f"{base_url}/sh/lstg/active"
        
        return success_response(
            data={
                "offer_id": offer_id,
                "listing_id": listing_id,
                "status": "PUBLISHED",
                "data_source": "live_api",
                "listing_url": listing_url,
                "seller_hub_url": seller_hub_url,
                "next_steps": [
                    f"View your live listing at: {listing_url}",
                    f"Manage all listings in Seller Hub: {seller_hub_url}",
                    f"Monitor performance with analytics tools"
                ]
            },
            message=f"✅ Listing published successfully!\n📍 View at: {listing_url}\n🎯 Listing ID: {listing_id}"
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


@mcp.tool
async def create_location(
    ctx: Context,
    location_key: str,
    location_type: str = "WAREHOUSE",
    name: str = "Default Location",
    address_line1: str = "123 Main St",
    city: str = "San Jose",
    state_or_province: str = "CA",
    postal_code: str = "95125",
    country_code: str = "US"
) -> str:
    """
    Create an inventory location.
    
    Creates a new inventory location that can be used for offers and listings.
    
    Args:
        location_key: Unique identifier for the location
        location_type: Type of location (WAREHOUSE, STORE, etc.)
        name: Display name for the location
        address_line1: Street address
        city: City name
        state_or_province: State or province
        postal_code: Postal/ZIP code
        country_code: Country code (US, CA, etc.)
        ctx: MCP context
    
    Returns:
        JSON response with location details
    """
    await ctx.info(f"Creating location: {location_key}")
    await ctx.report_progress(0.1, "Validating location data...")
    
    # Check credentials
    if not mcp.config.app_id or not mcp.config.cert_id:
        return success_response(
            data={
                "location_key": location_key,
                "location_type": location_type,
                "name": name,
                "address": {
                    "address_line1": address_line1,
                    "city": city,
                    "state_or_province": state_or_province,
                    "postal_code": postal_code,
                    "country_code": country_code
                },
                "data_source": "static_fallback",
                "note": "Live location management requires eBay API credentials"
            },
            message=f"Location {location_key} created (static data)"
        ).to_json_string()
    
    # Check user consent
    user_token = await _check_user_consent(ctx)
    if not user_token:
        return error_response(
            ErrorCode.AUTHENTICATION_ERROR,
            "User consent required for Inventory API. Use initiate_user_consent to authorize access.",
            {"required_scopes": OAuthScopes.USER_CONSENT_SCOPES.split()}
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
    rest_client._user_token = user_token
    
    try:
        await ctx.report_progress(0.3, "Creating location...")
        
        location_data = {
            "location": {
                "address": {
                    "addressLine1": address_line1,
                    "city": city,
                    "stateOrProvince": state_or_province,
                    "postalCode": postal_code,
                    "countryCode": country_code
                }
            },
            "locationAdditionalInformation": {
                "locationInstructions": f"Inventory location: {name}"
            },
            "locationWebUrl": "",
            "name": name,
            "phone": "",
            "locationTypes": [location_type]
        }
        
        response = await rest_client.post(
            f"/sell/inventory/v1/location/{location_key}",
            json=location_data,
            scope=OAuthScopes.SELL_INVENTORY
        )
        
        await ctx.report_progress(1.0, "Complete")
        await ctx.info(f"Successfully created location: {location_key}")
        
        return success_response(
            data={
                "location_key": location_key,
                "location_data": location_data,
                "data_source": "live_api"
            },
            message=f"Location {location_key} created successfully"
        ).to_json_string()
        
    except EbayApiError as e:
        await ctx.error(f"eBay API error: {str(e)}")
        return error_response(
            ErrorCode.EXTERNAL_API_ERROR,
            str(e),
            {"status_code": e.status_code, "location_key": location_key}
        ).to_json_string()
    except Exception as e:
        await ctx.error(f"Failed to create location: {str(e)}")
        return error_response(
            ErrorCode.INTERNAL_ERROR,
            f"Failed to create location: {str(e)}"
        ).to_json_string()
    finally:
        await rest_client.close()


@mcp.tool
async def delete_location(
    ctx: Context,
    location_key: str
) -> str:
    """
    Delete an inventory location.
    
    Deletes an existing inventory location.
    
    Args:
        location_key: Unique identifier for the location to delete
        ctx: MCP context
    
    Returns:
        JSON response with deletion status
    """
    await ctx.info(f"Deleting location: {location_key}")
    await ctx.report_progress(0.1, "Validating location...")
    
    # Check credentials
    if not mcp.config.app_id or not mcp.config.cert_id:
        return success_response(
            data={
                "location_key": location_key,
                "status": "DELETED",
                "data_source": "static_fallback",
                "note": "Live location management requires eBay API credentials"
            },
            message=f"Location {location_key} deleted (static data)"
        ).to_json_string()
    
    # Check user consent
    user_token = await _check_user_consent(ctx)
    if not user_token:
        return error_response(
            ErrorCode.AUTHENTICATION_ERROR,
            "User consent required for Inventory API. Use initiate_user_consent to authorize access.",
            {"required_scopes": OAuthScopes.USER_CONSENT_SCOPES.split()}
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
    rest_client._user_token = user_token
    
    try:
        await ctx.report_progress(0.3, "Deleting location...")
        
        response = await rest_client.delete(
            f"/sell/inventory/v1/location/{location_key}",
            scope=OAuthScopes.SELL_INVENTORY
        )
        
        await ctx.report_progress(1.0, "Complete")
        await ctx.info(f"Successfully deleted location: {location_key}")
        
        return success_response(
            data={
                "location_key": location_key,
                "status": "DELETED",
                "data_source": "live_api"
            },
            message=f"Location {location_key} deleted successfully"
        ).to_json_string()
        
    except EbayApiError as e:
        await ctx.error(f"eBay API error: {str(e)}")
        return error_response(
            ErrorCode.EXTERNAL_API_ERROR,
            str(e),
            {"status_code": e.status_code, "location_key": location_key}
        ).to_json_string()
    except Exception as e:
        await ctx.error(f"Failed to delete location: {str(e)}")
        return error_response(
            ErrorCode.INTERNAL_ERROR,
            f"Failed to delete location: {str(e)}"
        ).to_json_string()
    finally:
        await rest_client.close()


@mcp.tool
async def get_inventory_item(
    ctx: Context,
    sku: str
) -> str:
    """
    Get a single inventory item by SKU.
    
    Retrieves detailed information about a specific inventory item.
    
    Args:
        sku: The SKU of the inventory item to retrieve
        ctx: MCP context
    
    Returns:
        JSON response with inventory item details
    """
    await ctx.info(f"Getting inventory item: {sku}")
    await ctx.report_progress(0.1, "Validating SKU...")
    
    # Check credentials
    if not mcp.config.app_id or not mcp.config.cert_id:
        await ctx.info("Using static inventory data - set credentials for live inventory")
        
        # Return static inventory item
        item = {
            "sku": sku,
            "title": f"Sample Product - {sku}",
            "description": f"Sample description for {sku}",
            "price": {"value": 19.99, "currency": "USD"},
            "quantity": 5,
            "condition": "NEW",
            "category_id": "625",
            "listing_status": "ACTIVE",
            "created_date": datetime.now(timezone.utc).isoformat(),
            "last_modified_date": datetime.now(timezone.utc).isoformat()
        }
        
        return success_response(
            data={
                "inventory_item": item,
                "data_source": "static_fallback",
                "note": "Live inventory data requires eBay API credentials"
            },
            message=f"Retrieved inventory item {sku} (static data)"
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
    rest_client._user_token = user_token
    
    try:
        await ctx.report_progress(0.3, "Fetching inventory item...")
        
        # Define the API call function for retry logic
        async def make_get_item_request():
            return await rest_client.get(
                f"/sell/inventory/v1/inventory_item/{sku}",
                scope=OAuthScopes.SELL_INVENTORY
            )
        
        # Execute with enhanced sandbox retry logic
        retry_config = RetryConfig(max_attempts=3, base_delay=1.0, max_delay=10.0)
        response = await with_sandbox_retry(
            make_get_item_request,
            ctx=ctx,
            retry_config=retry_config
        )
        
        await ctx.report_progress(0.8, "Processing inventory item...")
        
        # Convert response
        item = _convert_inventory_item(response)
        
        await ctx.report_progress(1.0, "Complete")
        await ctx.info(f"Retrieved inventory item: {sku}")
        
        # Create helpful URLs for the user
        seller_hub_url = "https://www.ebay.com/sh/ovw"
        edit_item_url = f"https://www.ebay.com/sh/lst/active"
        create_offer_url = "https://www.ebay.com/sh/lst/drafts"
        pricing_research_url = f"https://www.ebay.com/sch/i.html?_nkw={item.get('title', '').replace(' ', '+') if item.get('title') else sku}"
        
        return success_response(
            data={
                "inventory_item": item,
                "data_source": "live_api",
                "sandbox_retry_enabled": True,
                "urls": {
                    "seller_hub": seller_hub_url,
                    "edit_item": edit_item_url,
                    "create_offer": create_offer_url,
                    "pricing_research": pricing_research_url,
                    "help_url": "https://www.ebay.com/help/selling/listings/creating-managing-listings"
                },
                "next_steps": [
                    f"📦 Inventory item '{sku}' details retrieved",
                    f"✏️  Edit item: {edit_item_url}",
                    f"💰 Research pricing: {pricing_research_url}",
                    f"🎯 Create offer if needed: create_offer(sku='{sku}')",
                    f"📊 Monitor in Seller Hub: {seller_hub_url}"
                ],
                "available_actions": {
                    "update": f"Use update_inventory_item(sku='{sku}', ...) to modify details",
                    "create_offer": f"Use create_offer(sku='{sku}', category_id='...') to list for sale",
                    "delete": f"Use delete_inventory_item(sku='{sku}') to remove (if no active offers)"
                }
            },
            message=f"📋 Inventory item {sku} retrieved successfully"
        ).to_json_string()
        
    except EbayApiError as e:
        if e.status_code == 404:
            return error_response(
                ErrorCode.RESOURCE_NOT_FOUND,
                f"Inventory item '{sku}' not found",
                {"sku": sku, "status_code": 404}
            ).to_json_string()
        
        # Try to handle known sandbox errors
        fallback_response = await handle_inventory_error(e, ctx)
        if fallback_response:
            return fallback_response
            
        await ctx.error(f"eBay API error (after retries): {str(e)}")
        return error_response(
            ErrorCode.EXTERNAL_API_ERROR,
            str(e),
            {"status_code": e.status_code, "sku": sku, "retry_attempted": True}
        ).to_json_string()
    except Exception as e:
        # Try to handle any unexpected inventory errors
        fallback_response = await handle_inventory_error(e, ctx)
        if fallback_response:
            return fallback_response
            
        await ctx.error(f"Failed to get inventory item (after retries): {str(e)}")
        return error_response(
            ErrorCode.INTERNAL_ERROR,
            f"Failed to get inventory item: {str(e)}",
            {"sku": sku, "retry_attempted": True}
        ).to_json_string()
    finally:
        await rest_client.close()


@mcp.tool
async def update_inventory_item(
    ctx: Context,
    sku: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    price: Optional[float] = None,
    currency: str = "USD",
    quantity: Optional[int] = None,
    condition: Optional[str] = None,
    brand: Optional[str] = None,
    mpn: Optional[str] = None,
    upc: Optional[str] = None
) -> str:
    """
    Update an existing inventory item.
    
    Updates specific fields of an inventory item identified by SKU.
    Only provided fields will be updated.
    
    Args:
        sku: The SKU of the inventory item to update
        title: New item title (optional)
        description: New item description (optional)
        price: New item price (optional)
        currency: Currency code (default: USD)
        quantity: New available quantity (optional)
        condition: New item condition (optional)
        brand: New brand name (optional)
        mpn: New Manufacturer Part Number (optional)
        upc: New Universal Product Code (optional)
        ctx: MCP context
    
    Returns:
        JSON response with update status
    """
    await ctx.info(f"Updating inventory item: {sku}")
    await ctx.report_progress(0.1, "Validating update parameters...")
    
    # Check credentials
    if not mcp.config.app_id or not mcp.config.cert_id:
        return success_response(
            data={
                "sku": sku,
                "update_status": "UPDATED",
                "updated_fields": [k for k, v in locals().items() if v is not None and k not in ['ctx', 'sku', 'currency']],
                "data_source": "static_fallback",
                "note": "Live inventory updates require eBay API credentials"
            },
            message=f"Inventory item {sku} updated (static data)"
        ).to_json_string()
    
    # Check user consent
    user_token = await _check_user_consent(ctx)
    if not user_token:
        return error_response(
            ErrorCode.AUTHENTICATION_ERROR,
            "User consent required for Inventory API. Use initiate_user_consent to authorize access.",
            {"required_scopes": OAuthScopes.USER_CONSENT_SCOPES.split()}
        ).to_json_string()
    
    # Build update payload with only provided fields
    update_data = {}
    
    if title or description:
        update_data["product"] = {}
        if title:
            update_data["product"]["title"] = title
        if description:
            update_data["product"]["description"] = description
        if brand:
            update_data["product"]["brand"] = brand
        if mpn:
            update_data["product"]["mpn"] = mpn
        if upc:
            update_data["product"]["upc"] = [upc]
    
    if condition:
        update_data["condition"] = condition
    
    if price is not None:
        update_data["pricing"] = {
            "quantity": 1,
            "priceType": "FIXED",
            "price": {
                "value": str(price),
                "currency": currency
            }
        }
    
    if quantity is not None:
        update_data["availability"] = {
            "shipToLocationAvailability": {
                "quantity": quantity
            }
        }
    
    if not update_data:
        return error_response(
            ErrorCode.VALIDATION_ERROR,
            "No update fields provided. At least one field must be specified for update.",
            {"sku": sku}
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
    rest_client._user_token = user_token
    
    try:
        await ctx.report_progress(0.3, "Updating inventory item...")
        
        # Define the API call function for retry logic
        async def make_update_request():
            return await rest_client.put(
                f"/sell/inventory/v1/inventory_item/{sku}",
                json=update_data,
                scope=OAuthScopes.SELL_INVENTORY
            )
        
        # Execute with enhanced sandbox retry logic
        retry_config = RetryConfig(max_attempts=3, base_delay=2.0, max_delay=15.0)
        response = await with_sandbox_retry(
            make_update_request,
            ctx=ctx,
            retry_config=retry_config
        )
        
        await ctx.report_progress(1.0, "Complete")
        await ctx.info(f"Successfully updated inventory item: {sku}")
        
        # Create helpful URLs for the user
        seller_hub_url = "https://www.ebay.com/sh/ovw"
        view_item_url = f"https://www.ebay.com/sh/lst/active"
        pricing_research_url = f"https://www.ebay.com/sch/i.html?_nkw={sku}"
        
        return success_response(
            data={
                "sku": sku,
                "update_status": "UPDATED",
                "updated_fields": list(update_data.keys()),
                "data_source": "live_api",
                "sandbox_retry_enabled": True,
                "urls": {
                    "seller_hub": seller_hub_url,
                    "view_item": view_item_url,
                    "pricing_research": pricing_research_url,
                    "help_url": "https://www.ebay.com/help/selling/listings/creating-managing-listings"
                },
                "next_steps": [
                    f"✅ Inventory item '{sku}' updated successfully",
                    f"📝 Updated fields: {', '.join(update_data.keys())}",
                    f"👀 View changes: {view_item_url}",
                    f"📊 Monitor performance: {seller_hub_url}",
                    f"💡 Consider updating related offers if pricing changed"
                ],
                "recommendations": {
                    "verify_changes": f"Use get_inventory_item(sku='{sku}') to confirm updates",
                    "sync_offers": "Update related offers if price or quantity changed",
                    "monitor_impact": "Track performance changes in Seller Hub"
                }
            },
            message=f"🔄 Inventory item {sku} updated successfully"
        ).to_json_string()
        
    except EbayApiError as e:
        if e.status_code == 404:
            return error_response(
                ErrorCode.RESOURCE_NOT_FOUND,
                f"Inventory item '{sku}' not found for update",
                {"sku": sku, "status_code": 404}
            ).to_json_string()
        
        await ctx.error(f"eBay API error (after retries): {str(e)}")
        return error_response(
            ErrorCode.EXTERNAL_API_ERROR,
            str(e),
            {"status_code": e.status_code, "sku": sku, "retry_attempted": True}
        ).to_json_string()
    except Exception as e:
        await ctx.error(f"Failed to update inventory item (after retries): {str(e)}")
        return error_response(
            ErrorCode.INTERNAL_ERROR,
            f"Failed to update inventory item: {str(e)}",
            {"sku": sku, "retry_attempted": True}
        ).to_json_string()
    finally:
        await rest_client.close()


@mcp.tool
async def delete_inventory_item(
    ctx: Context,
    sku: str
) -> str:
    """
    Delete an inventory item by SKU.
    
    Permanently removes an inventory item from the seller's inventory.
    This will also end any active listings for this item.
    
    Args:
        sku: The SKU of the inventory item to delete
        ctx: MCP context
    
    Returns:
        JSON response with deletion status
    """
    await ctx.info(f"Deleting inventory item: {sku}")
    await ctx.report_progress(0.1, "Validating deletion...")
    
    # Check credentials
    if not mcp.config.app_id or not mcp.config.cert_id:
        return success_response(
            data={
                "sku": sku,
                "deletion_status": "DELETED",
                "data_source": "static_fallback",
                "note": "Live inventory deletions require eBay API credentials"
            },
            message=f"Inventory item {sku} deleted (static data)"
        ).to_json_string()
    
    # Check user consent
    user_token = await _check_user_consent(ctx)
    if not user_token:
        return error_response(
            ErrorCode.AUTHENTICATION_ERROR,
            "User consent required for Inventory API. Use initiate_user_consent to authorize access.",
            {"required_scopes": OAuthScopes.USER_CONSENT_SCOPES.split()}
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
    rest_client._user_token = user_token
    
    try:
        await ctx.report_progress(0.3, "Deleting inventory item...")
        
        # Define the API call function for retry logic
        async def make_delete_request():
            return await rest_client.delete(
                f"/sell/inventory/v1/inventory_item/{sku}",
                scope=OAuthScopes.SELL_INVENTORY
            )
        
        # Execute with enhanced sandbox retry logic
        retry_config = RetryConfig(max_attempts=3, base_delay=1.5, max_delay=10.0)
        response = await with_sandbox_retry(
            make_delete_request,
            ctx=ctx,
            retry_config=retry_config
        )
        
        await ctx.report_progress(1.0, "Complete")
        await ctx.info(f"Successfully deleted inventory item: {sku}")
        
        # Create helpful URLs for the user
        seller_hub_url = "https://www.ebay.com/sh/ovw"
        create_new_url = "https://www.ebay.com/sh/lst/drafts"
        inventory_management_url = "https://www.ebay.com/sh/lst?ListingType=Active"
        
        return success_response(
            data={
                "sku": sku,
                "deletion_status": "DELETED",
                "data_source": "live_api",
                "sandbox_retry_enabled": True,
                "urls": {
                    "seller_hub": seller_hub_url,
                    "create_new_item": create_new_url,
                    "inventory_management": inventory_management_url,
                    "help_url": "https://www.ebay.com/help/selling/listings/creating-managing-listings"
                },
                "next_steps": [
                    f"🗑️  Inventory item '{sku}' deleted permanently",
                    f"📝 Create new item: {create_new_url}",
                    f"📦 Manage inventory: {inventory_management_url}",
                    f"📊 Monitor in Seller Hub: {seller_hub_url}",
                    f"💡 Use create_inventory_item() to add new items"
                ],
                "important_notes": [
                    "⚠️  This action cannot be undone",
                    "📋 Related offers were automatically removed",
                    "💾 Consider backing up important item data before deletion"
                ]
            },
            message=f"🗑️  Inventory item {sku} deleted successfully"
        ).to_json_string()
        
    except EbayApiError as e:
        if e.status_code == 404:
            return error_response(
                ErrorCode.RESOURCE_NOT_FOUND,
                f"Inventory item '{sku}' not found for deletion",
                {"sku": sku, "status_code": 404}
            ).to_json_string()
        
        await ctx.error(f"eBay API error (after retries): {str(e)}")
        return error_response(
            ErrorCode.EXTERNAL_API_ERROR,
            str(e),
            {"status_code": e.status_code, "sku": sku, "retry_attempted": True}
        ).to_json_string()
    except Exception as e:
        await ctx.error(f"Failed to delete inventory item (after retries): {str(e)}")
        return error_response(
            ErrorCode.INTERNAL_ERROR,
            f"Failed to delete inventory item: {str(e)}",
            {"sku": sku, "retry_attempted": True}
        ).to_json_string()
    finally:
        await rest_client.close()


class BulkInventoryUpdate(BaseModel):
    """Input model for bulk inventory updates."""
    sku: str = Field(..., description="SKU of the item to update")
    title: Optional[str] = Field(None, description="New title")
    description: Optional[str] = Field(None, description="New description")
    price: Optional[float] = Field(None, ge=0, description="New price")
    quantity: Optional[int] = Field(None, ge=0, description="New quantity")
    condition: Optional[str] = Field(None, description="New condition")


@mcp.tool
async def bulk_update_inventory(
    ctx: Context,
    updates: List[Dict[str, Any]],
    currency: str = "USD"
) -> str:
    """
    Update multiple inventory items in a single operation.
    
    Efficiently updates multiple inventory items with different field changes.
    Each update can modify different fields as needed.
    
    Args:
        updates: List of update objects, each containing 'sku' and optional fields to update
        currency: Currency code for price updates (default: USD)
        ctx: MCP context
    
    Returns:
        JSON response with bulk update results
    """
    await ctx.info(f"Bulk updating {len(updates)} inventory items")
    await ctx.report_progress(0.1, "Validating bulk update data...")
    
    # Validate input
    try:
        validated_updates = []
        for update in updates:
            validated_update = BulkInventoryUpdate(**update)
            validated_updates.append(validated_update)
    except Exception as e:
        return error_response(
            ErrorCode.VALIDATION_ERROR,
            f"Invalid bulk update data: {str(e)}",
            {"total_updates": len(updates)}
        ).to_json_string()
    
    # Check credentials
    if not mcp.config.app_id or not mcp.config.cert_id:
        results = []
        for update in validated_updates:
            results.append({
                "sku": update.sku,
                "status": "UPDATED",
                "updated_fields": [k for k, v in update.model_dump().items() if v is not None and k != 'sku'],
                "message": "Static update simulation"
            })
        
        return success_response(
            data={
                "bulk_update_results": results,
                "total_updates": len(updates),
                "successful_updates": len(updates),
                "failed_updates": 0,
                "data_source": "static_fallback",
                "note": "Live bulk updates require eBay API credentials"
            },
            message=f"Bulk updated {len(updates)} inventory items (static data)"
        ).to_json_string()
    
    # Check user consent
    user_token = await _check_user_consent(ctx)
    if not user_token:
        return error_response(
            ErrorCode.AUTHENTICATION_ERROR,
            "User consent required for Inventory API. Use initiate_user_consent to authorize access.",
            {"required_scopes": OAuthScopes.USER_CONSENT_SCOPES.split()}
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
    rest_client._user_token = user_token
    
    results = []
    successful_updates = 0
    failed_updates = 0
    
    try:
        await ctx.report_progress(0.3, "Processing bulk updates...")
        
        for i, update in enumerate(validated_updates):
            try:
                # Build update payload
                update_data = {}
                
                if update.title or update.description:
                    update_data["product"] = {}
                    if update.title:
                        update_data["product"]["title"] = update.title
                    if update.description:
                        update_data["product"]["description"] = update.description
                
                if update.condition:
                    update_data["condition"] = update.condition
                
                if update.price is not None:
                    update_data["pricing"] = {
                        "quantity": 1,
                        "priceType": "FIXED",
                        "price": {
                            "value": str(update.price),
                            "currency": currency
                        }
                    }
                
                if update.quantity is not None:
                    update_data["availability"] = {
                        "shipToLocationAvailability": {
                            "quantity": update.quantity
                        }
                    }
                
                if update_data:
                    # Define the API call function for retry logic
                    async def make_bulk_update_request():
                        return await rest_client.put(
                            f"/sell/inventory/v1/inventory_item/{update.sku}",
                            json=update_data,
                            scope=OAuthScopes.SELL_INVENTORY
                        )
                    
                    # Execute with retry logic but shorter delays for bulk operations
                    retry_config = RetryConfig(max_attempts=2, base_delay=1.0, max_delay=5.0)
                    response = await with_sandbox_retry(
                        make_bulk_update_request,
                        ctx=ctx,
                        retry_config=retry_config
                    )
                    
                    results.append({
                        "sku": update.sku,
                        "status": "UPDATED",
                        "updated_fields": list(update_data.keys()),
                        "message": "Successfully updated"
                    })
                    successful_updates += 1
                else:
                    results.append({
                        "sku": update.sku,
                        "status": "SKIPPED",
                        "updated_fields": [],
                        "message": "No fields to update"
                    })
                
                # Update progress
                progress = 0.3 + (0.6 * (i + 1) / len(validated_updates))
                await ctx.report_progress(progress, f"Updated {i+1}/{len(validated_updates)} items")
                
            except EbayApiError as e:
                results.append({
                    "sku": update.sku,
                    "status": "FAILED",
                    "updated_fields": [],
                    "message": str(e),
                    "error_code": e.status_code
                })
                failed_updates += 1
                await ctx.error(f"Failed to update {update.sku}: {str(e)}")
            except Exception as e:
                results.append({
                    "sku": update.sku,
                    "status": "FAILED",
                    "updated_fields": [],
                    "message": str(e)
                })
                failed_updates += 1
                await ctx.error(f"Failed to update {update.sku}: {str(e)}")
        
        await ctx.report_progress(1.0, "Bulk update complete")
        await ctx.info(f"Bulk update completed: {successful_updates} successful, {failed_updates} failed")
        
        # Create helpful URLs for the user
        seller_hub_url = "https://www.ebay.com/sh/ovw"
        inventory_management_url = "https://www.ebay.com/sh/lst?ListingType=Active"
        
        return success_response(
            data={
                "bulk_update_results": results,
                "total_updates": len(validated_updates),
                "successful_updates": successful_updates,
                "failed_updates": failed_updates,
                "data_source": "live_api",
                "sandbox_retry_enabled": True,
                "urls": {
                    "seller_hub": seller_hub_url,
                    "inventory_management": inventory_management_url,
                    "help_url": "https://www.ebay.com/help/selling/listings/creating-managing-listings"
                },
                "summary": [
                    f"📊 Bulk update completed: {successful_updates}/{len(validated_updates)} successful",
                    f"✅ {successful_updates} items updated successfully",
                    f"❌ {failed_updates} items failed to update" if failed_updates > 0 else "🎉 All items updated successfully",
                    f"📈 View updates: {inventory_management_url}",
                    f"📊 Monitor performance: {seller_hub_url}"
                ],
                "recommendations": {
                    "review_failures": "Check failed items and retry with corrected data if needed",
                    "monitor_changes": "Track performance impact of price/quantity changes",
                    "sync_offers": "Update related offers if pricing changed significantly"
                }
            },
            message=f"📦 Bulk update completed: {successful_updates}/{len(validated_updates)} successful"
        ).to_json_string()
        
    except Exception as e:
        await ctx.error(f"Bulk update failed: {str(e)}")
        return error_response(
            ErrorCode.INTERNAL_ERROR,
            f"Bulk update failed: {str(e)}",
            {"total_updates": len(updates), "processed_updates": len(results)}
        ).to_json_string()
    finally:
        await rest_client.close()


@mcp.tool
async def get_offer(
    ctx: Context,
    offer_id: str
) -> str:
    """
    Get details of a specific offer by offer ID.
    
    Retrieves detailed information about an offer including its status,
    listing details, and current settings.
    
    Args:
        offer_id: The eBay offer ID to retrieve
        ctx: MCP context
    
    Returns:
        JSON response with offer details
    """
    await ctx.info(f"Getting offer: {offer_id}")
    await ctx.report_progress(0.1, "Validating offer ID...")
    
    # Check credentials
    if not mcp.config.app_id or not mcp.config.cert_id:
        return success_response(
            data={
                "offer": {
                    "offer_id": offer_id,
                    "sku": "SAMPLE-SKU-001",
                    "marketplace_id": "EBAY_US",
                    "format": "FIXED_PRICE",
                    "status": "PUBLISHED",
                    "listing_id": "123456789012",
                    "available_quantity": 5,
                    "price": {"value": "19.99", "currency": "USD"},
                    "category_id": "625",
                    "created_date": datetime.now(timezone.utc).isoformat(),
                    "last_modified_date": datetime.now(timezone.utc).isoformat()
                },
                "data_source": "static_fallback",
                "note": "Live offer data requires eBay API credentials"
            },
            message=f"Retrieved offer {offer_id} (static data)"
        ).to_json_string()
    
    # Check user consent
    user_token = await _check_user_consent(ctx)
    if not user_token:
        return error_response(
            ErrorCode.AUTHENTICATION_ERROR,
            "User consent required for Inventory API. Use initiate_user_consent to authorize access.",
            {"required_scopes": OAuthScopes.USER_CONSENT_SCOPES.split()}
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
    rest_client._user_token = user_token
    
    try:
        await ctx.report_progress(0.3, "Fetching offer details...")
        
        # Define the API call function for retry logic
        async def make_get_offer_request():
            return await rest_client.get(
                f"/sell/inventory/v1/offer/{offer_id}",
                scope=OAuthScopes.SELL_INVENTORY
            )
        
        # Execute with enhanced sandbox retry logic
        retry_config = RetryConfig(max_attempts=3, base_delay=1.0, max_delay=10.0)
        response = await with_sandbox_retry(
            make_get_offer_request,
            ctx=ctx,
            retry_config=retry_config
        )
        
        await ctx.report_progress(0.8, "Processing offer details...")
        
        # Convert response
        offer = _convert_offer(response)
        
        await ctx.report_progress(1.0, "Complete")
        await ctx.info(f"Retrieved offer: {offer_id}")
        
        # Create helpful URLs for the user
        seller_hub_url = "https://www.ebay.com/sh/ovw"
        listing_url = f"https://www.ebay.com/itm/{offer.get('listing_id', '')}" if offer.get('listing_id') else None
        edit_offer_url = "https://www.ebay.com/sh/lst/active"
        
        return success_response(
            data={
                "offer": offer,
                "data_source": "live_api",
                "sandbox_retry_enabled": True,
                "urls": {
                    "seller_hub": seller_hub_url,
                    "listing_page": listing_url,
                    "edit_offer": edit_offer_url,
                    "help_url": "https://www.ebay.com/help/selling/listings/creating-managing-listings"
                },
                "next_steps": [
                    f"📋 Offer '{offer_id}' details retrieved",
                    f"📊 Status: {offer.get('status', 'Unknown')}",
                    f"🔗 View listing: {listing_url}" if listing_url else "📝 Not yet published",
                    f"✏️  Edit offer: {edit_offer_url}",
                    f"📈 Monitor performance: {seller_hub_url}"
                ],
                "available_actions": {
                    "update": f"Use update_offer(offer_id='{offer_id}', ...) to modify",
                    "publish": f"Use publish_offer(offer_id='{offer_id}') if status is DRAFT",
                    "withdraw": f"Use withdraw_offer(offer_id='{offer_id}') to end listing",
                    "delete": f"Use delete_offer(offer_id='{offer_id}') to remove permanently"
                }
            },
            message=f"📋 Offer {offer_id} retrieved successfully"
        ).to_json_string()
        
    except EbayApiError as e:
        if e.status_code == 404:
            return error_response(
                ErrorCode.RESOURCE_NOT_FOUND,
                f"Offer '{offer_id}' not found",
                {"offer_id": offer_id, "status_code": 404}
            ).to_json_string()
        
        await ctx.error(f"eBay API error (after retries): {str(e)}")
        return error_response(
            ErrorCode.EXTERNAL_API_ERROR,
            str(e),
            {"status_code": e.status_code, "offer_id": offer_id, "retry_attempted": True}
        ).to_json_string()
    except Exception as e:
        await ctx.error(f"Failed to get offer (after retries): {str(e)}")
        return error_response(
            ErrorCode.INTERNAL_ERROR,
            f"Failed to get offer: {str(e)}",
            {"offer_id": offer_id, "retry_attempted": True}
        ).to_json_string()
    finally:
        await rest_client.close()


@mcp.tool
async def update_offer(
    ctx: Context,
    offer_id: str,
    price: Optional[float] = None,
    currency: str = "USD",
    quantity: Optional[int] = None,
    category_id: Optional[str] = None,
    listing_duration: Optional[str] = None,
    tax_percentage: Optional[float] = None,
    charity_id: Optional[str] = None,
    charity_percentage: Optional[float] = None
) -> str:
    """
    Update an existing offer's settings.
    
    Updates specific fields of an offer. Only provided fields will be updated.
    Common updates include price changes, quantity adjustments, and listing settings.
    
    Args:
        offer_id: The eBay offer ID to update
        price: New listing price (optional)
        currency: Currency code (default: USD)
        quantity: New available quantity (optional)
        category_id: New eBay category ID (optional)
        listing_duration: New listing duration like 'GTC', 'Days_7' (optional)
        tax_percentage: Tax percentage for the item (optional)
        charity_id: Charity ID for donations (optional)
        charity_percentage: Percentage to donate to charity (optional)
        ctx: MCP context
    
    Returns:
        JSON response with update status
    """
    await ctx.info(f"Updating offer: {offer_id}")
    await ctx.report_progress(0.1, "Validating update parameters...")
    
    # Check credentials
    if not mcp.config.app_id or not mcp.config.cert_id:
        updated_fields = [k for k, v in locals().items() if v is not None and k not in ['ctx', 'offer_id', 'currency']]
        return success_response(
            data={
                "offer_id": offer_id,
                "update_status": "UPDATED",
                "updated_fields": updated_fields,
                "data_source": "static_fallback",
                "note": "Live offer updates require eBay API credentials"
            },
            message=f"Offer {offer_id} updated (static data)"
        ).to_json_string()
    
    # Check user consent
    user_token = await _check_user_consent(ctx)
    if not user_token:
        return error_response(
            ErrorCode.AUTHENTICATION_ERROR,
            "User consent required for Inventory API. Use initiate_user_consent to authorize access.",
            {"required_scopes": OAuthScopes.USER_CONSENT_SCOPES.split()}
        ).to_json_string()
    
    # Build update payload with only provided fields
    update_data = {}
    
    if price is not None:
        update_data["pricingSummary"] = {
            "price": {
                "value": str(price),
                "currency": currency
            }
        }
    
    if quantity is not None:
        update_data["availableQuantity"] = quantity
    
    if category_id is not None:
        update_data["categoryId"] = category_id
    
    if listing_duration is not None:
        update_data["listingDuration"] = listing_duration
    
    if tax_percentage is not None:
        update_data["tax"] = {
            "vatPercentage": tax_percentage
        }
    
    if charity_id is not None and charity_percentage is not None:
        update_data["charity"] = {
            "charityId": charity_id,
            "donationPercentage": charity_percentage
        }
    
    if not update_data:
        return error_response(
            ErrorCode.VALIDATION_ERROR,
            "No update fields provided. At least one field must be specified for update.",
            {"offer_id": offer_id}
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
    rest_client._user_token = user_token
    
    try:
        await ctx.report_progress(0.3, "Updating offer...")
        
        # Define the API call function for retry logic
        async def make_update_offer_request():
            return await rest_client.put(
                f"/sell/inventory/v1/offer/{offer_id}",
                json=update_data,
                scope=OAuthScopes.SELL_INVENTORY
            )
        
        # Execute with enhanced sandbox retry logic
        retry_config = RetryConfig(max_attempts=3, base_delay=2.0, max_delay=15.0)
        response = await with_sandbox_retry(
            make_update_offer_request,
            ctx=ctx,
            retry_config=retry_config
        )
        
        await ctx.report_progress(1.0, "Complete")
        await ctx.info(f"Successfully updated offer: {offer_id}")
        
        # Build helpful URLs and feedback
        base_url = "https://sandbox.ebay.com" if mcp.config.sandbox_mode else "https://www.ebay.com"
        seller_hub_url = f"{base_url}/sh/lstg/active"
        seller_hub_offers_url = f"{base_url}/sh/sellr/offers"
        
        updated_fields_friendly = []
        for field in update_data.keys():
            if field == "pricingSummary":
                updated_fields_friendly.append("💰 Price")
            elif field == "availableQuantity":
                updated_fields_friendly.append("📦 Quantity")
            elif field == "categoryId":
                updated_fields_friendly.append("🏷️ Category")
            elif field == "listingDuration":
                updated_fields_friendly.append("⏰ Duration")
            else:
                updated_fields_friendly.append(f"🔧 {field}")
        
        return success_response(
            data={
                "offer_id": offer_id,
                "update_status": "UPDATED",
                "updated_fields": list(update_data.keys()),
                "updated_fields_friendly": updated_fields_friendly,
                "data_source": "live_api",
                "sandbox_retry_enabled": True,
                "urls": {
                    "seller_hub_active": seller_hub_url,
                    "seller_hub_offers": seller_hub_offers_url,
                    "help_url": "https://www.ebay.com/help/selling/listings/editing-active-listings"
                },
                "next_steps": [
                    f"✅ Updated {len(updated_fields_friendly)} field(s): {', '.join(updated_fields_friendly)}",
                    f"🔍 Check offer details: get_offer('{offer_id}')",
                    f"🚀 If not published yet: publish_offer('{offer_id}')",
                    f"📊 Manage in Seller Hub: {seller_hub_url}"
                ]
            },
            message=f"Offer {offer_id} updated successfully - {len(updated_fields_friendly)} field(s) modified"
        ).to_json_string()
        
    except EbayApiError as e:
        if e.status_code == 404:
            return error_response(
                ErrorCode.RESOURCE_NOT_FOUND,
                f"Offer '{offer_id}' not found for update",
                {"offer_id": offer_id, "status_code": 404}
            ).to_json_string()
        
        await ctx.error(f"eBay API error (after retries): {str(e)}")
        return error_response(
            ErrorCode.EXTERNAL_API_ERROR,
            str(e),
            {"status_code": e.status_code, "offer_id": offer_id, "retry_attempted": True}
        ).to_json_string()
    except Exception as e:
        await ctx.error(f"Failed to update offer (after retries): {str(e)}")
        return error_response(
            ErrorCode.INTERNAL_ERROR,
            f"Failed to update offer: {str(e)}",
            {"offer_id": offer_id, "retry_attempted": True}
        ).to_json_string()
    finally:
        await rest_client.close()


@mcp.tool
async def delete_offer(
    ctx: Context,
    offer_id: str
) -> str:
    """
    Delete an offer permanently.
    
    Permanently removes an offer from the seller's inventory.
    If the offer is published as a listing, this will end the listing.
    
    Args:
        offer_id: The eBay offer ID to delete
        ctx: MCP context
    
    Returns:
        JSON response with deletion status
    """
    await ctx.info(f"Deleting offer: {offer_id}")
    await ctx.report_progress(0.1, "Validating deletion...")
    
    # Check credentials
    if not mcp.config.app_id or not mcp.config.cert_id:
        return success_response(
            data={
                "offer_id": offer_id,
                "deletion_status": "DELETED",
                "data_source": "static_fallback",
                "note": "Live offer deletions require eBay API credentials"
            },
            message=f"Offer {offer_id} deleted (static data)"
        ).to_json_string()
    
    # Check user consent
    user_token = await _check_user_consent(ctx)
    if not user_token:
        return error_response(
            ErrorCode.AUTHENTICATION_ERROR,
            "User consent required for Inventory API. Use initiate_user_consent to authorize access.",
            {"required_scopes": OAuthScopes.USER_CONSENT_SCOPES.split()}
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
    rest_client._user_token = user_token
    
    try:
        await ctx.report_progress(0.3, "Deleting offer...")
        
        # Define the API call function for retry logic
        async def make_delete_offer_request():
            return await rest_client.delete(
                f"/sell/inventory/v1/offer/{offer_id}",
                scope=OAuthScopes.SELL_INVENTORY
            )
        
        # Execute with enhanced sandbox retry logic
        retry_config = RetryConfig(max_attempts=3, base_delay=1.5, max_delay=10.0)
        response = await with_sandbox_retry(
            make_delete_offer_request,
            ctx=ctx,
            retry_config=retry_config
        )
        
        await ctx.report_progress(1.0, "Complete")
        await ctx.info(f"Successfully deleted offer: {offer_id}")
        
        # Build helpful URLs and feedback
        base_url = "https://sandbox.ebay.com" if mcp.config.sandbox_mode else "https://www.ebay.com"
        seller_hub_url = f"{base_url}/sh/lstg/sold"  # Sold/ended listings
        create_listing_url = f"{base_url}/sl/sell"
        
        return success_response(
            data={
                "offer_id": offer_id,
                "deletion_status": "DELETED",
                "data_source": "live_api",
                "sandbox_retry_enabled": True,
                "urls": {
                    "seller_hub_ended": seller_hub_url,
                    "create_new_listing": create_listing_url,
                    "help_url": "https://www.ebay.com/help/selling/listings/ending-your-listing-early"
                },
                "next_steps": [
                    f"🗑️ Offer {offer_id} permanently deleted",
                    f"📝 Create new listing: {create_listing_url}",
                    f"📊 View ended listings: {seller_hub_url}",
                    f"💡 Consider using withdraw_offer() instead for temporary removal"
                ],
                "alternatives": {
                    "temporary_removal": "Use withdraw_offer() to temporarily end listing but keep offer",
                    "create_new": "Use create_inventory_item() + create_offer() for new listings",
                    "bulk_management": "Use bulk_update_inventory() for multiple item changes"
                }
            },
            message=f"Offer {offer_id} deleted permanently - any active listing has ended"
        ).to_json_string()
        
    except EbayApiError as e:
        if e.status_code == 404:
            return error_response(
                ErrorCode.RESOURCE_NOT_FOUND,
                f"Offer '{offer_id}' not found for deletion",
                {"offer_id": offer_id, "status_code": 404}
            ).to_json_string()
        
        await ctx.error(f"eBay API error (after retries): {str(e)}")
        return error_response(
            ErrorCode.EXTERNAL_API_ERROR,
            str(e),
            {"status_code": e.status_code, "offer_id": offer_id, "retry_attempted": True}
        ).to_json_string()
    except Exception as e:
        await ctx.error(f"Failed to delete offer (after retries): {str(e)}")
        return error_response(
            ErrorCode.INTERNAL_ERROR,
            f"Failed to delete offer: {str(e)}",
            {"offer_id": offer_id, "retry_attempted": True}
        ).to_json_string()
    finally:
        await rest_client.close()


@mcp.tool
async def withdraw_offer(
    ctx: Context,
    offer_id: str
) -> str:
    """
    Withdraw an offer from eBay (end the listing but keep the offer).
    
    Withdraws a published offer from eBay, ending the active listing
    while preserving the offer for potential republishing later.
    This is different from delete_offer which removes the offer entirely.
    
    Args:
        offer_id: The eBay offer ID to withdraw
        ctx: MCP context
    
    Returns:
        JSON response with withdrawal status
    """
    await ctx.info(f"Withdrawing offer: {offer_id}")
    await ctx.report_progress(0.1, "Validating withdrawal...")
    
    # Check credentials
    if not mcp.config.app_id or not mcp.config.cert_id:
        return success_response(
            data={
                "offer_id": offer_id,
                "withdrawal_status": "WITHDRAWN",
                "listing_status": "ENDED",
                "data_source": "static_fallback",
                "note": "Live offer withdrawals require eBay API credentials"
            },
            message=f"Offer {offer_id} withdrawn (static data)"
        ).to_json_string()
    
    # Check user consent
    user_token = await _check_user_consent(ctx)
    if not user_token:
        return error_response(
            ErrorCode.AUTHENTICATION_ERROR,
            "User consent required for Inventory API. Use initiate_user_consent to authorize access.",
            {"required_scopes": OAuthScopes.USER_CONSENT_SCOPES.split()}
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
    rest_client._user_token = user_token
    
    try:
        await ctx.report_progress(0.3, "Withdrawing offer...")
        
        # Define the API call function for retry logic
        async def make_withdraw_offer_request():
            return await rest_client.post(
                f"/sell/inventory/v1/offer/{offer_id}/withdraw",
                scope=OAuthScopes.SELL_INVENTORY
            )
        
        # Execute with enhanced sandbox retry logic
        retry_config = RetryConfig(max_attempts=3, base_delay=1.5, max_delay=10.0)
        response = await with_sandbox_retry(
            make_withdraw_offer_request,
            ctx=ctx,
            retry_config=retry_config
        )
        
        await ctx.report_progress(1.0, "Complete")
        await ctx.info(f"Successfully withdrew offer: {offer_id}")
        
        # Create helpful URLs for the user
        seller_hub_url = "https://www.ebay.com/sh/ovw"
        ended_listings_url = "https://www.ebay.com/sh/lst?ListingType=Ended"
        draft_listings_url = "https://www.ebay.com/sh/lst/drafts"
        
        return success_response(
            data={
                "offer_id": offer_id,
                "withdrawal_status": "WITHDRAWN",
                "listing_status": "ENDED",
                "data_source": "live_api",
                "sandbox_retry_enabled": True,
                "urls": {
                    "seller_hub": seller_hub_url,
                    "ended_listings": ended_listings_url,
                    "draft_listings": draft_listings_url,
                    "help_url": "https://www.ebay.com/help/selling/listings/ending-your-listing-early"
                },
                "next_steps": [
                    f"🔄 Offer '{offer_id}' withdrawn successfully",
                    f"📋 Listing ended but offer preserved for republishing",
                    f"📝 View in drafts: {draft_listings_url}",
                    f"📊 Check ended listings: {ended_listings_url}",
                    f"🔄 Republish when ready: publish_offer('{offer_id}')"
                ],
                "available_actions": {
                    "republish": f"Use publish_offer('{offer_id}') to create a new listing",
                    "modify_first": f"Use update_offer('{offer_id}', ...) to modify before republishing",
                    "permanent_delete": f"Use delete_offer('{offer_id}') to remove permanently"
                },
                "important_notes": [
                    "✅ Offer is preserved and can be republished",
                    "🔄 Listing has ended but inventory item remains",
                    "💡 Consider modifying before republishing for better performance"
                ]
            },
            message=f"🔄 Offer {offer_id} withdrawn - listing ended but offer preserved"
        ).to_json_string()
        
    except EbayApiError as e:
        if e.status_code == 404:
            return error_response(
                ErrorCode.RESOURCE_NOT_FOUND,
                f"Offer '{offer_id}' not found for withdrawal",
                {"offer_id": offer_id, "status_code": 404}
            ).to_json_string()
        elif e.status_code == 409:
            return error_response(
                ErrorCode.EXTERNAL_API_ERROR,
                f"Offer '{offer_id}' cannot be withdrawn (may not be published or already ended)",
                {"offer_id": offer_id, "status_code": 409, "suggestion": "Check offer status with get_offer()"}
            ).to_json_string()
        
        await ctx.error(f"eBay API error (after retries): {str(e)}")
        return error_response(
            ErrorCode.EXTERNAL_API_ERROR,
            str(e),
            {"status_code": e.status_code, "offer_id": offer_id, "retry_attempted": True}
        ).to_json_string()
    except Exception as e:
        await ctx.error(f"Failed to withdraw offer (after retries): {str(e)}")
        return error_response(
            ErrorCode.INTERNAL_ERROR,
            f"Failed to withdraw offer: {str(e)}",
            {"offer_id": offer_id, "retry_attempted": True}
        ).to_json_string()
    finally:
        await rest_client.close()