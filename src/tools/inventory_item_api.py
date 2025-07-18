"""
eBay Inventory Item API tools for managing seller product inventory.

This module provides MCP tools for creating, updating, retrieving, and deleting
inventory items in eBay seller accounts. Inventory items represent products
available for sale and serve as the foundation for listing management.

IMPLEMENTATION FOLLOWS: PYDANTIC-FIRST DEVELOPMENT METHODOLOGY
- All API fields included exactly as documented
- Strong typing with enums throughout
- Validation through Pydantic models only
- Zero manual validation code

API Documentation: https://developer.ebay.com/api-docs/sell/inventory/resources/methods
OAuth Scope Required: https://api.ebay.com/oauth/api_scope/sell.inventory
"""
from typing import Optional, Dict, Any, List, Union
from fastmcp import Context
from pydantic import BaseModel, Field, model_validator, ConfigDict, field_validator, ValidationError
from decimal import Decimal
import decimal
import json

from api.oauth import OAuthManager, OAuthConfig, ConsentRequiredException
from api.rest_client import EbayRestClient, RestConfig
from api.errors import EbayApiError, extract_ebay_error_details
from api.ebay_enums import (
    MarketplaceIdEnum,
    ConditionEnum,
    CurrencyCodeEnum,
    AvailabilityTypeEnum,
    LocaleEnum,
    LengthUnitOfMeasureEnum,
    WeightUnitOfMeasureEnum,
    PackageTypeEnum,
    TimeDurationUnitEnum
)
from data_types import success_response, error_response, ErrorCode
from lootly_server import mcp


# PYDANTIC MODELS - API Documentation → Pydantic Models → MCP Tools


class Dimension(BaseModel):
    """Physical dimension with value and unit."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    value: Decimal = Field(..., description="Dimension value")
    unit: LengthUnitOfMeasureEnum = Field(..., description="Unit of measurement")
    
    @field_validator('value', mode='before')
    @classmethod
    def coerce_decimal(cls, v):
        """Convert string values to Decimal."""
        if v is None:
            return v
        if isinstance(v, str):
            try:
                return Decimal(v)
            except (ValueError, decimal.InvalidOperation) as e:
                raise ValueError(f"Invalid decimal value: {v}")
        return v


class Weight(BaseModel):
    """Package weight with value and unit."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    value: Decimal = Field(..., description="Weight value")
    unit: WeightUnitOfMeasureEnum = Field(..., description="Unit of measurement")
    
    @field_validator('value', mode='before')
    @classmethod
    def coerce_decimal(cls, v):
        """Convert string values to Decimal."""
        if v is None:
            return v
        if isinstance(v, str):
            try:
                return Decimal(v)
            except (ValueError, decimal.InvalidOperation) as e:
                raise ValueError(f"Invalid decimal value: {v}")
        return v


class PackageWeightAndSize(BaseModel):
    """Package dimensions and weight for shipping calculation."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    # OPTIONAL FIELDS
    dimensions: Optional[Dict[str, Dimension]] = Field(None, description="Package dimensions (length, width, height)")
    package_type: Optional[PackageTypeEnum] = Field(None, description="Type of package")
    weight: Optional[Weight] = Field(None, description="Package weight")


class PickupAtLocationAvailability(BaseModel):
    """Local pickup availability settings."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    availability_type: AvailabilityTypeEnum = Field(..., description="Availability type")
    fulfillment_time: Optional[Dict[str, Any]] = Field(None, description="Pickup fulfillment time")
    merchant_location_key: Optional[str] = Field(None, description="Merchant location identifier")


class ShipToLocationAvailability(BaseModel):
    """Ship-to-home availability settings."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    # OPTIONAL FIELDS
    allocation_by_format: Optional[Dict[str, int]] = Field(None, description="Quantity allocation by listing format")
    availability_distributions: Optional[List[Dict[str, Any]]] = Field(None, description="Inventory location distributions")
    quantity: Optional[int] = Field(None, ge=0, description="Total available quantity")


class Availability(BaseModel):
    """Inventory availability configuration."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    # OPTIONAL FIELDS
    pickup_at_location_availability: Optional[List[PickupAtLocationAvailability]] = Field(None, description="Local pickup availability")
    ship_to_location_availability: Optional[ShipToLocationAvailability] = Field(None, description="Ship-to-home availability")


class Product(BaseModel):
    """Product information and details."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    # OPTIONAL FIELDS (required for publishing offers)
    title: Optional[str] = Field(None, max_length=80, description="Product title")
    description: Optional[str] = Field(None, max_length=4000, description="Product description")
    aspects: Optional[Dict[str, List[str]]] = Field(None, description="Product aspects/attributes")
    brand: Optional[str] = Field(None, description="Product brand")
    mpn: Optional[str] = Field(None, description="Manufacturer Part Number")
    
    # PRODUCT IDENTIFIERS
    upc: Optional[List[str]] = Field(None, description="UPC codes")
    ean: Optional[List[str]] = Field(None, description="EAN codes")
    isbn: Optional[List[str]] = Field(None, description="ISBN codes")
    epid: Optional[str] = Field(None, description="eBay Product ID")
    gtin: Optional[List[str]] = Field(None, description="GTIN codes")
    
    # MEDIA
    image_urls: Optional[List[str]] = Field(None, description="Product image URLs (HTTPS required)")
    video_ids: Optional[List[str]] = Field(None, description="eBay video IDs")
    
    # ADDITIONAL DETAILS
    subtitle: Optional[str] = Field(None, max_length=55, description="Product subtitle")
    
    @model_validator(mode='after')
    def validate_image_urls(self):
        """Validate that all image URLs use HTTPS."""
        if self.image_urls:
            for url in self.image_urls:
                if not url.startswith("https://"):
                    raise ValueError(f"Image URLs must use HTTPS: {url}")
        return self


class InventoryItemInput(BaseModel):
    """
    Complete input validation for inventory item operations.
    
    Maps ALL fields from eBay API createOrReplaceInventoryItem Request Fields exactly.
    Documentation: https://developer.ebay.com/api-docs/sell/inventory/resources/inventory_item/methods/createOrReplaceInventoryItem
    """
    model_config = ConfigDict(str_strip_whitespace=True)
    
    # SKU is passed as path parameter, not in body
    
    # CONDITIONAL FIELDS (required for publishing offers)
    availability: Optional[Availability] = Field(None, description="Availability and quantity settings")
    condition: Optional[ConditionEnum] = Field(None, description="Item condition")
    condition_description: Optional[str] = Field(None, max_length=1000, description="Detailed condition description")
    package_weight_and_size: Optional[PackageWeightAndSize] = Field(None, description="Package dimensions and weight")
    product: Optional[Product] = Field(None, description="Product information and details")
    
    # LOCALE SETTINGS
    locale: Optional[LocaleEnum] = Field(None, description="Locale for item details")


class BulkInventoryItemRequest(BaseModel):
    """Single inventory item request for bulk operations."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    sku: str = Field(..., max_length=50, description="Unique SKU identifier")
    inventory_item: InventoryItemInput = Field(..., description="Inventory item data")


class BulkInventoryItemInput(BaseModel):
    """Bulk inventory item creation/update input."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    requests: List[BulkInventoryItemRequest] = Field(..., max_length=25, description="Inventory item requests (max 25)")
    
    @model_validator(mode='after')
    def validate_unique_skus(self):
        """Validate that all SKUs in the bulk request are unique."""
        skus = [req.sku for req in self.requests]
        if len(skus) != len(set(skus)):
            raise ValueError("All SKUs in bulk request must be unique")
        return self


class PriceQuantity(BaseModel):
    """Price and quantity update for bulk operations."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    # OPTIONAL FIELDS
    offers: Optional[List[Dict[str, Any]]] = Field(None, description="Offer-specific price/quantity updates")
    ship_to_location_availability: Optional[ShipToLocationAvailability] = Field(None, description="Quantity updates")


class BulkPriceQuantityRequest(BaseModel):
    """Single price/quantity update request for bulk operations."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    sku: str = Field(..., max_length=50, description="Unique SKU identifier")
    price_quantity: PriceQuantity = Field(..., description="Price and quantity updates")


class BulkPriceQuantityInput(BaseModel):
    """Bulk price and quantity update input."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    requests: List[BulkPriceQuantityRequest] = Field(..., max_length=25, description="Price/quantity update requests (max 25)")
    
    @model_validator(mode='after')
    def validate_unique_skus(self):
        """Validate that all SKUs in the bulk request are unique."""
        skus = [req.sku for req in self.requests]
        if len(skus) != len(set(skus)):
            raise ValueError("All SKUs in bulk request must be unique")
        return self


# HELPER FUNCTIONS - Convert between Pydantic models and eBay API format


def _build_inventory_item_data(input_data: InventoryItemInput) -> Dict[str, Any]:
    """
    Convert Pydantic model to eBay API request format.
    
    This follows the exact field mapping from eBay's createOrReplaceInventoryItem API.
    """
    item_data = {}
    
    # Add availability
    if input_data.availability:
        availability_data = {}
        
        if input_data.availability.pickup_at_location_availability:
            availability_data["pickupAtLocationAvailability"] = [
                {
                    "availabilityType": pickup.availability_type.value,
                    **({"fulfillmentTime": pickup.fulfillment_time} if pickup.fulfillment_time else {}),
                    **({"merchantLocationKey": pickup.merchant_location_key} if pickup.merchant_location_key else {})
                }
                for pickup in input_data.availability.pickup_at_location_availability
            ]
        
        if input_data.availability.ship_to_location_availability:
            ship_data = {}
            ship_avail = input_data.availability.ship_to_location_availability
            
            if ship_avail.allocation_by_format:
                ship_data["allocationByFormat"] = ship_avail.allocation_by_format
            if ship_avail.availability_distributions:
                ship_data["availabilityDistributions"] = ship_avail.availability_distributions
            if ship_avail.quantity is not None:
                ship_data["quantity"] = ship_avail.quantity
            
            if ship_data:
                availability_data["shipToLocationAvailability"] = ship_data
        
        if availability_data:
            item_data["availability"] = availability_data
    
    # Add condition
    if input_data.condition:
        item_data["condition"] = input_data.condition.value
    
    if input_data.condition_description:
        item_data["conditionDescription"] = input_data.condition_description
    
    # Add package weight and size
    if input_data.package_weight_and_size:
        package_data = {}
        pkg = input_data.package_weight_and_size
        
        if pkg.dimensions:
            package_data["dimensions"] = {
                key: {
                    "value": str(dim.value),
                    "unit": dim.unit.value
                }
                for key, dim in pkg.dimensions.items()
            }
        
        if pkg.package_type:
            package_data["packageType"] = pkg.package_type.value
        
        if pkg.weight:
            package_data["weight"] = {
                "value": str(pkg.weight.value),
                "unit": pkg.weight.unit.value
            }
        
        if package_data:
            item_data["packageWeightAndSize"] = package_data
    
    # Add product information
    if input_data.product:
        product_data = {}
        prod = input_data.product
        
        # Basic product fields
        if prod.title:
            product_data["title"] = prod.title
        if prod.description:
            product_data["description"] = prod.description
        if prod.aspects:
            product_data["aspects"] = prod.aspects
        if prod.brand:
            product_data["brand"] = prod.brand
        if prod.mpn:
            product_data["mpn"] = prod.mpn
        if prod.subtitle:
            product_data["subtitle"] = prod.subtitle
        
        # Product identifiers
        if prod.upc:
            product_data["upc"] = prod.upc
        if prod.ean:
            product_data["ean"] = prod.ean
        if prod.isbn:
            product_data["isbn"] = prod.isbn
        if prod.epid:
            product_data["epid"] = prod.epid
        if prod.gtin:
            product_data["gtin"] = prod.gtin
        
        # Media
        if prod.image_urls:
            product_data["imageUrls"] = prod.image_urls
        if prod.video_ids:
            product_data["videoIds"] = prod.video_ids
        
        if product_data:
            item_data["product"] = product_data
    
    # Add locale
    if input_data.locale:
        item_data["locale"] = input_data.locale.value
    
    return item_data


def _format_inventory_item_response(item: Dict[str, Any]) -> Dict[str, Any]:
    """Format API response for consistent output."""
    formatted = {
        "sku": item.get("sku"),
        "locale": item.get("locale")
    }
    
    # Add availability
    if item.get("availability"):
        formatted["availability"] = item["availability"]
    
    # Add condition
    if item.get("condition"):
        formatted["condition"] = item["condition"]
    if item.get("conditionDescription"):
        formatted["condition_description"] = item["conditionDescription"]
    
    # Add package info
    if item.get("packageWeightAndSize"):
        formatted["package_weight_and_size"] = item["packageWeightAndSize"]
    
    # Add product info
    if item.get("product"):
        formatted["product"] = item["product"]
    
    return formatted


def _validate_sku_format(sku: str) -> None:
    """Validate SKU format according to eBay requirements."""
    if not sku or not sku.strip():
        raise ValueError("SKU is required and cannot be empty")
    
    if len(sku) > 50:
        raise ValueError("SKU cannot exceed 50 characters")
    
    # eBay allows alphanumeric characters, hyphens, and underscores
    if not all(c.isalnum() or c in ['-', '_'] for c in sku):
        raise ValueError("SKU can only contain alphanumeric characters, hyphens, and underscores")


# MCP TOOLS - Using Pydantic Models


@mcp.tool
async def create_or_replace_inventory_item(
    ctx: Context,
    sku: str,
    inventory_item: Union[str, InventoryItemInput]
) -> str:
    """
    Create or replace an inventory item in your eBay seller account.
    
    Inventory items represent products available for sale and serve as the foundation
    for creating eBay listings. This operation creates a new inventory item or
    completely replaces an existing one with the same SKU.
    
    Key features:
    - SKU-based management (must be unique across your inventory)
    - Product details: title, description, images, brand, identifiers
    - Availability and quantity management
    - Package dimensions and weight for shipping
    - Condition and condition description
    
    Args:
        sku: Unique Stock Keeping Unit identifier (max 50 chars, alphanumeric + hyphens/underscores)
        inventory_item: Either a JSON string or InventoryItemInput object with inventory item data
        ctx: MCP context
    
    Returns:
        JSON response confirming creation/update
    
    OAuth Scope Required: https://api.ebay.com/oauth/api_scope/sell.inventory
    """
    # Parse input - handles both JSON strings (from Claude) and Pydantic objects (from tests)
    try:
        if isinstance(inventory_item, str):
            await ctx.info("Parsing JSON inventory item parameters...")
            data = json.loads(inventory_item)
            inventory_item = InventoryItemInput(**data)
        elif not isinstance(inventory_item, InventoryItemInput):
            raise ValueError(f"Expected JSON string or InventoryItemInput object, got {type(inventory_item)}")
    except json.JSONDecodeError as e:
        await ctx.error(f"Invalid JSON in inventory_item: {str(e)}")
        return error_response(
            ErrorCode.VALIDATION_ERROR,
            f"Invalid JSON in inventory_item: {str(e)}. Please provide valid JSON with inventory item data."
        ).to_json_string()
    except ValidationError as e:
        await ctx.error(f"Invalid inventory item parameters: {str(e)}")
        error_details = []
        # Create a serializable version of validation errors
        # IMPORTANT: Exclude 'ctx' field which contains non-serializable ValueError objects
        serializable_errors = []
        for error in e.errors():
            field = " -> ".join(str(x) for x in error["loc"])
            error_details.append(f"{field}: {error['msg']}")
            # Only include serializable fields, excluding 'ctx' which has ValueError object
            serializable_errors.append({
                "field": field,
                "message": error["msg"],
                "type": error.get("type", "validation_error"),
                "input": error.get("input", "")
            })
        return error_response(
            ErrorCode.VALIDATION_ERROR,
            f"Invalid inventory item parameters: {'; '.join(error_details)}",
            {"validation_errors": serializable_errors, "required_fields": ["availability", "condition", "product"]}
        ).to_json_string()
    
    await ctx.info(f"Creating/replacing inventory item: {sku}")
    await ctx.report_progress(0.1, "Validating input parameters...")
    
    # Validate SKU format
    try:
        _validate_sku_format(sku)
    except ValueError as e:
        return error_response(
            ErrorCode.VALIDATION_ERROR,
            str(e)
        ).to_json_string()
    
    # Check credentials
    if not mcp.config.app_id or not mcp.config.cert_id:
        return error_response(
            ErrorCode.CONFIGURATION_ERROR,
            "eBay App ID and Cert ID must be configured"
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
        await ctx.report_progress(0.3, "Converting input to eBay API format...")
        
        # Convert Pydantic model to eBay API format
        item_data = _build_inventory_item_data(inventory_item)
        
        await ctx.report_progress(0.5, f"Creating/replacing inventory item {sku}...")
        
        # Make API call - OAuth scope validation automatic
        await rest_client.put(
            f"/sell/inventory/v1/inventory_item/{sku}",
            json=item_data
        )
        
        await ctx.report_progress(0.8, "Processing response...")
        
        # Format response (PUT returns 204 No Content on success)
        result_data = {
            "sku": sku,
            "operation": "create_or_replace",
            "success": True
        }
        
        await ctx.report_progress(1.0, "Inventory item created/replaced successfully")
        await ctx.success(f"Inventory item '{sku}' created/replaced successfully")
        
        return success_response(
            data=result_data,
            message=f"Inventory item '{sku}' created/replaced successfully"
        ).to_json_string()
        
    except ConsentRequiredException as e:
        await ctx.warning("User consent required for sell.inventory scope")
        return error_response(
            ErrorCode.AUTHENTICATION_ERROR,
            "User consent required for sell.inventory scope",
            {"consent_url": str(e), "scope_required": "sell.inventory"}
        ).to_json_string()
        
    except EbayApiError as e:
        await ctx.error(f"eBay API error: {e.get_comprehensive_message()}")
        return error_response(
            ErrorCode.EXTERNAL_API_ERROR,
            e.get_comprehensive_message(),
            extract_ebay_error_details(e)
        ).to_json_string()
        
    except Exception as e:
        await ctx.error(f"Unexpected error: {e}")
        return error_response(
            ErrorCode.INTERNAL_ERROR,
            "An unexpected error occurred while creating/replacing the inventory item",
            {"error": str(e)}
        ).to_json_string()
        
    finally:
        await rest_client.close()


@mcp.tool
async def get_inventory_item(
    ctx: Context,
    sku: str
) -> str:
    """
    Retrieve a specific inventory item by its SKU.
    
    Returns detailed information about a single inventory item including
    product details, availability, condition, and package information.
    
    Args:
        sku: Stock Keeping Unit identifier
        ctx: MCP context
    
    Returns:
        JSON response with complete inventory item details
    
    OAuth Scope Required: https://api.ebay.com/oauth/api_scope/sell.inventory
    """
    await ctx.info(f"Retrieving inventory item: {sku}")
    await ctx.report_progress(0.1, "Validating parameters...")
    
    # Validate SKU format
    try:
        _validate_sku_format(sku)
    except ValueError as e:
        return error_response(
            ErrorCode.VALIDATION_ERROR,
            str(e)
        ).to_json_string()
    
    # Check credentials
    if not mcp.config.app_id or not mcp.config.cert_id:
        return error_response(
            ErrorCode.CONFIGURATION_ERROR,
            "eBay App ID and Cert ID must be configured"
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
        await ctx.report_progress(0.5, f"Fetching inventory item {sku}...")
        
        # Make API call
        response = await rest_client.get(f"/sell/inventory/v1/inventory_item/{sku}")
        response_body = response["body"]
        
        await ctx.report_progress(0.8, "Processing response...")
        
        # Format response
        formatted_response = _format_inventory_item_response(response_body)
        
        await ctx.report_progress(1.0, "Inventory item retrieved successfully")
        await ctx.success(f"Retrieved inventory item '{sku}'")
        
        return success_response(
            data=formatted_response,
            message=f"Inventory item '{sku}' retrieved successfully"
        ).to_json_string()
        
    except ConsentRequiredException as e:
        await ctx.warning("User consent required for sell.inventory scope")
        return error_response(
            ErrorCode.AUTHENTICATION_ERROR,
            "User consent required for sell.inventory scope",
            {"consent_url": str(e), "scope_required": "sell.inventory"}
        ).to_json_string()
        
    except EbayApiError as e:
        await ctx.error(f"eBay API error: {e.get_comprehensive_message()}")
        return error_response(
            ErrorCode.EXTERNAL_API_ERROR,
            e.get_comprehensive_message(),
            extract_ebay_error_details(e)
        ).to_json_string()
        
    except Exception as e:
        await ctx.error(f"Unexpected error: {e}")
        return error_response(
            ErrorCode.INTERNAL_ERROR,
            "An unexpected error occurred while retrieving the inventory item",
            {"error": str(e)}
        ).to_json_string()
        
    finally:
        await rest_client.close()


@mcp.tool
async def get_inventory_items(
    ctx: Context,
    limit: Optional[int] = 25,
    offset: Optional[int] = 0
) -> str:
    """
    Retrieve all inventory items for your eBay seller account.
    
    Returns a paginated list of all inventory items configured for the seller.
    Use this to review your complete product inventory.
    
    Args:
        limit: Maximum number of items to return (1-200, default: 25)
        offset: Number of items to skip for pagination (default: 0)
        ctx: MCP context
    
    Returns:
        JSON response with list of inventory items and pagination info
    
    OAuth Scope Required: https://api.ebay.com/oauth/api_scope/sell.inventory
    """
    await ctx.info("Retrieving inventory items")
    await ctx.report_progress(0.1, "Validating parameters...")
    
    # Validate pagination parameters
    if limit is not None and (limit < 1 or limit > 200):
        return error_response(
            ErrorCode.VALIDATION_ERROR,
            "limit must be between 1 and 200"
        ).to_json_string()
    
    if offset is not None and offset < 0:
        return error_response(
            ErrorCode.VALIDATION_ERROR,
            "offset must be non-negative"
        ).to_json_string()
    
    # Check credentials
    if not mcp.config.app_id or not mcp.config.cert_id:
        return error_response(
            ErrorCode.CONFIGURATION_ERROR,
            "eBay App ID and Cert ID must be configured"
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
        await ctx.report_progress(0.5, "Fetching inventory items...")
        
        # Build query parameters
        params = {}
        if limit is not None:
            params["limit"] = str(limit)
        if offset is not None:
            params["offset"] = str(offset)
        
        # Make API call
        response = await rest_client.get(
            "/sell/inventory/v1/inventory_item",
            params=params if params else None
        )
        response_body = response["body"]
        
        await ctx.report_progress(0.8, "Processing response...")
        
        # Format items
        items = response_body.get("inventoryItems", [])
        formatted_items = [_format_inventory_item_response(item) for item in items]
        
        # Build response with pagination
        result = {
            "inventory_items": formatted_items,
            "total": response_body.get("total", len(formatted_items)),
            "size": response_body.get("size", 1),
            "limit": limit,
            "offset": offset
        }
        
        # Add pagination links if available
        if response_body.get("next"):
            result["next"] = response_body["next"]
        if response_body.get("prev"):
            result["prev"] = response_body["prev"]
        
        await ctx.report_progress(1.0, f"Retrieved {len(formatted_items)} inventory items")
        await ctx.success(f"Found {len(formatted_items)} inventory items")
        
        return success_response(
            data=result,
            message=f"Retrieved {len(formatted_items)} inventory items"
        ).to_json_string()
        
    except ConsentRequiredException as e:
        await ctx.warning("User consent required for sell.inventory scope")
        return error_response(
            ErrorCode.AUTHENTICATION_ERROR,
            "User consent required for sell.inventory scope",
            {"consent_url": str(e), "scope_required": "sell.inventory"}
        ).to_json_string()
        
    except EbayApiError as e:
        await ctx.error(f"eBay API error: {e.get_comprehensive_message()}")
        return error_response(
            ErrorCode.EXTERNAL_API_ERROR,
            e.get_comprehensive_message(),
            extract_ebay_error_details(e)
        ).to_json_string()
        
    except Exception as e:
        await ctx.error(f"Unexpected error: {e}")
        return error_response(
            ErrorCode.INTERNAL_ERROR,
            "An unexpected error occurred while retrieving inventory items",
            {"error": str(e)}
        ).to_json_string()
        
    finally:
        await rest_client.close()


@mcp.tool
async def delete_inventory_item(
    ctx: Context,
    sku: str
) -> str:
    """
    Delete an inventory item from your eBay seller account.
    
    Permanently removes an inventory item and any associated unpublished offers.
    Published offers (active listings) must be ended before the inventory item can be deleted.
    
    Args:
        sku: Stock Keeping Unit identifier
        ctx: MCP context
    
    Returns:
        JSON response confirming deletion
    
    OAuth Scope Required: https://api.ebay.com/oauth/api_scope/sell.inventory
    """
    await ctx.info(f"Deleting inventory item: {sku}")
    await ctx.report_progress(0.1, "Validating parameters...")
    
    # Validate SKU format
    try:
        _validate_sku_format(sku)
    except ValueError as e:
        return error_response(
            ErrorCode.VALIDATION_ERROR,
            str(e)
        ).to_json_string()
    
    # Check credentials
    if not mcp.config.app_id or not mcp.config.cert_id:
        return error_response(
            ErrorCode.CONFIGURATION_ERROR,
            "eBay App ID and Cert ID must be configured"
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
        await ctx.report_progress(0.5, f"Deleting inventory item {sku}...")
        
        # Make API call
        await rest_client.delete(f"/sell/inventory/v1/inventory_item/{sku}")
        
        await ctx.report_progress(1.0, "Inventory item deleted successfully")
        await ctx.success(f"Inventory item '{sku}' deleted successfully")
        
        return success_response(
            data={"sku": sku, "deleted": True},
            message=f"Inventory item '{sku}' deleted successfully"
        ).to_json_string()
        
    except ConsentRequiredException as e:
        await ctx.warning("User consent required for sell.inventory scope")
        return error_response(
            ErrorCode.AUTHENTICATION_ERROR,
            "User consent required for sell.inventory scope",
            {"consent_url": str(e), "scope_required": "sell.inventory"}
        ).to_json_string()
        
    except EbayApiError as e:
        await ctx.error(f"eBay API error: {e.get_comprehensive_message()}")
        return error_response(
            ErrorCode.EXTERNAL_API_ERROR,
            e.get_comprehensive_message(),
            extract_ebay_error_details(e)
        ).to_json_string()
        
    except Exception as e:
        await ctx.error(f"Unexpected error: {e}")
        return error_response(
            ErrorCode.INTERNAL_ERROR,
            "An unexpected error occurred while deleting the inventory item",
            {"error": str(e)}
        ).to_json_string()
        
    finally:
        await rest_client.close()


@mcp.tool
async def bulk_create_or_replace_inventory_item(
    ctx: Context,
    bulk_input: Union[str, BulkInventoryItemInput]
) -> str:
    """
    Create or replace multiple inventory items in a single operation.
    
    Efficiently processes up to 25 inventory items simultaneously. Each item
    can be created or completely replaced based on its SKU. This is ideal for
    importing product catalogs or updating multiple items at once.
    
    Args:
        bulk_input: Bulk inventory item data (max 25 items)
        ctx: MCP context
    
    Returns:
        JSON response with individual item results and overall status
    
    OAuth Scope Required: https://api.ebay.com/oauth/api_scope/sell.inventory
    """
    # Parse input - handles both JSON strings (from Claude) and Pydantic objects (from tests)
    try:
        if isinstance(bulk_input, str):
            await ctx.info("Parsing JSON bulk inventory parameters...")
            data = json.loads(bulk_input)
            bulk_input = BulkInventoryItemInput(**data)
        elif not isinstance(bulk_input, BulkInventoryItemInput):
            raise ValueError(f"Expected JSON string or BulkInventoryItemInput object, got {type(bulk_input)}")
    except json.JSONDecodeError as e:
        await ctx.error(f"Invalid JSON in bulk_input: {str(e)}")
        return error_response(
            ErrorCode.VALIDATION_ERROR,
            f"Invalid JSON in bulk_input: {str(e)}. Please provide valid JSON with bulk inventory data."
        ).to_json_string()
    except ValidationError as e:
        await ctx.error(f"Invalid bulk inventory parameters: {str(e)}")
        error_details = []
        # Create a serializable version of validation errors
        # IMPORTANT: Exclude 'ctx' field which contains non-serializable ValueError objects
        serializable_errors = []
        for error in e.errors():
            field = " -> ".join(str(x) for x in error["loc"])
            error_details.append(f"{field}: {error['msg']}")
            # Only include serializable fields, excluding 'ctx' which has ValueError object
            serializable_errors.append({
                "field": field,
                "message": error["msg"],
                "type": error.get("type", "validation_error"),
                "input": error.get("input", "")
            })
        return error_response(
            ErrorCode.VALIDATION_ERROR,
            f"Invalid bulk inventory parameters: {'; '.join(error_details)}",
            {"validation_errors": serializable_errors, "required_fields": ["requests"]}
        ).to_json_string()
    
    await ctx.info(f"Bulk creating/replacing {len(bulk_input.requests)} inventory items")
    await ctx.report_progress(0.1, "Validating input parameters...")
    
    # Validate individual SKUs
    for req in bulk_input.requests:
        try:
            _validate_sku_format(req.sku)
        except ValueError as e:
            return error_response(
                ErrorCode.VALIDATION_ERROR,
                f"Invalid SKU '{req.sku}': {e}"
            ).to_json_string()
    
    # Check credentials
    if not mcp.config.app_id or not mcp.config.cert_id:
        return error_response(
            ErrorCode.CONFIGURATION_ERROR,
            "eBay App ID and Cert ID must be configured"
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
        await ctx.report_progress(0.3, "Converting input to eBay API format...")
        
        # Convert Pydantic model to eBay API format
        requests_data = []
        for req in bulk_input.requests:
            item_data = _build_inventory_item_data(req.inventory_item)
            requests_data.append({
                "sku": req.sku,
                **item_data
            })
        
        bulk_data = {"requests": requests_data}
        
        await ctx.report_progress(0.5, f"Processing {len(bulk_input.requests)} items via eBay API...")
        
        # Make API call
        response = await rest_client.post(
            "/sell/inventory/v1/bulk_create_or_replace_inventory_item",
            json=bulk_data
        )
        response_body = response["body"]
        
        await ctx.report_progress(0.8, "Processing bulk response...")
        
        # Format response
        responses = response_body.get("responses", [])
        
        # Categorize results
        successful = [r for r in responses if r.get("statusCode") in [200, 201, 204]]
        failed = [r for r in responses if r.get("statusCode") not in [200, 201, 204]]
        
        result_data = {
            "total_items": len(bulk_input.requests),
            "successful": len(successful),
            "failed": len(failed),
            "responses": responses
        }
        
        await ctx.report_progress(1.0, f"Bulk operation completed: {len(successful)}/{len(bulk_input.requests)} successful")
        
        if failed:
            await ctx.warning(f"Bulk operation partially successful: {len(failed)} items failed")
        else:
            await ctx.success(f"All {len(successful)} inventory items processed successfully")
        
        return success_response(
            data=result_data,
            message=f"Bulk operation completed: {len(successful)}/{len(bulk_input.requests)} items successful"
        ).to_json_string()
        
    except ConsentRequiredException as e:
        await ctx.warning("User consent required for sell.inventory scope")
        return error_response(
            ErrorCode.AUTHENTICATION_ERROR,
            "User consent required for sell.inventory scope",
            {"consent_url": str(e), "scope_required": "sell.inventory"}
        ).to_json_string()
        
    except EbayApiError as e:
        await ctx.error(f"eBay API error: {e.get_comprehensive_message()}")
        return error_response(
            ErrorCode.EXTERNAL_API_ERROR,
            e.get_comprehensive_message(),
            extract_ebay_error_details(e)
        ).to_json_string()
        
    except Exception as e:
        await ctx.error(f"Unexpected error: {e}")
        return error_response(
            ErrorCode.INTERNAL_ERROR,
            "An unexpected error occurred during bulk inventory item operation",
            {"error": str(e)}
        ).to_json_string()
        
    finally:
        await rest_client.close()


@mcp.tool
async def bulk_get_inventory_item(
    ctx: Context,
    skus: List[str]
) -> str:
    """
    Retrieve multiple inventory items by their SKUs in a single operation.
    
    Efficiently fetches up to 25 inventory items simultaneously. This is ideal for
    retrieving specific products or checking the status of multiple items.
    
    Args:
        skus: List of Stock Keeping Unit identifiers (max 25)
        ctx: MCP context
    
    Returns:
        JSON response with individual item details and overall status
    
    OAuth Scope Required: https://api.ebay.com/oauth/api_scope/sell.inventory
    """
    await ctx.info(f"Bulk retrieving {len(skus)} inventory items")
    await ctx.report_progress(0.1, "Validating input parameters...")
    
    # Validate SKU count
    if len(skus) == 0:
        return error_response(
            ErrorCode.VALIDATION_ERROR,
            "At least one SKU is required"
        ).to_json_string()
    
    if len(skus) > 25:
        return error_response(
            ErrorCode.VALIDATION_ERROR,
            "Maximum 25 SKUs allowed per bulk request"
        ).to_json_string()
    
    # Validate individual SKUs
    for sku in skus:
        try:
            _validate_sku_format(sku)
        except ValueError as e:
            return error_response(
                ErrorCode.VALIDATION_ERROR,
                f"Invalid SKU '{sku}': {e}"
            ).to_json_string()
    
    # Check for duplicate SKUs
    if len(skus) != len(set(skus)):
        return error_response(
            ErrorCode.VALIDATION_ERROR,
            "All SKUs must be unique"
        ).to_json_string()
    
    # Check credentials
    if not mcp.config.app_id or not mcp.config.cert_id:
        return error_response(
            ErrorCode.CONFIGURATION_ERROR,
            "eBay App ID and Cert ID must be configured"
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
        await ctx.report_progress(0.5, f"Fetching {len(skus)} inventory items...")
        
        # Build query parameters
        params = {"sku": ",".join(skus)}
        
        # Make API call
        response = await rest_client.get(
            "/sell/inventory/v1/bulk_get_inventory_item",
            params=params
        )
        response_body = response["body"]
        
        await ctx.report_progress(0.8, "Processing bulk response...")
        
        # Format response
        responses = response_body.get("responses", [])
        
        # Format individual items
        formatted_items = []
        for item_response in responses:
            if item_response.get("statusCode") in [200, 201]:
                if "inventoryItem" in item_response:
                    formatted_item = _format_inventory_item_response(item_response["inventoryItem"])
                    formatted_items.append({
                        "sku": item_response.get("sku"),
                        "status_code": item_response.get("statusCode"),
                        "inventory_item": formatted_item
                    })
                else:
                    formatted_items.append({
                        "sku": item_response.get("sku"),
                        "status_code": item_response.get("statusCode"),
                        "error": "No inventory item data returned"
                    })
            else:
                formatted_items.append({
                    "sku": item_response.get("sku"),
                    "status_code": item_response.get("statusCode"),
                    "error": item_response.get("message", "Unknown error")
                })
        
        # Categorize results
        successful = [r for r in responses if r.get("statusCode") in [200, 201]]
        failed = [r for r in responses if r.get("statusCode") not in [200, 201]]
        
        result_data = {
            "total_requested": len(skus),
            "successful": len(successful),
            "failed": len(failed),
            "items": formatted_items
        }
        
        await ctx.report_progress(1.0, f"Bulk retrieval completed: {len(successful)}/{len(skus)} found")
        
        if failed:
            await ctx.warning(f"Bulk retrieval partially successful: {len(failed)} items not found")
        else:
            await ctx.success(f"All {len(successful)} inventory items retrieved successfully")
        
        return success_response(
            data=result_data,
            message=f"Bulk retrieval completed: {len(successful)}/{len(skus)} items found"
        ).to_json_string()
        
    except ConsentRequiredException as e:
        await ctx.warning("User consent required for sell.inventory scope")
        return error_response(
            ErrorCode.AUTHENTICATION_ERROR,
            "User consent required for sell.inventory scope",
            {"consent_url": str(e), "scope_required": "sell.inventory"}
        ).to_json_string()
        
    except EbayApiError as e:
        await ctx.error(f"eBay API error: {e.get_comprehensive_message()}")
        return error_response(
            ErrorCode.EXTERNAL_API_ERROR,
            e.get_comprehensive_message(),
            extract_ebay_error_details(e)
        ).to_json_string()
        
    except Exception as e:
        await ctx.error(f"Unexpected error: {e}")
        return error_response(
            ErrorCode.INTERNAL_ERROR,
            "An unexpected error occurred during bulk inventory retrieval",
            {"error": str(e)}
        ).to_json_string()
        
    finally:
        await rest_client.close()


@mcp.tool
async def bulk_update_price_quantity(
    ctx: Context,
    bulk_updates: Union[str, BulkPriceQuantityInput]
) -> str:
    """
    Update price and quantity for multiple inventory items efficiently.
    
    Optimized for high-frequency updates to pricing and inventory levels.
    Processes up to 25 items simultaneously with minimal data transfer.
    
    Args:
        bulk_updates: Either a JSON string or BulkPriceQuantityInput object with bulk update data (max 25 items)
        ctx: MCP context
    
    Returns:
        JSON response with individual update results and overall status
    
    OAuth Scope Required: https://api.ebay.com/oauth/api_scope/sell.inventory
    """
    # Parse input - handles both JSON strings (from Claude) and Pydantic objects (from tests)
    try:
        if isinstance(bulk_updates, str):
            await ctx.info("Parsing JSON bulk price/quantity update parameters...")
            data = json.loads(bulk_updates)
            bulk_updates = BulkPriceQuantityInput(**data)
        elif not isinstance(bulk_updates, BulkPriceQuantityInput):
            raise ValueError(f"Expected JSON string or BulkPriceQuantityInput object, got {type(bulk_updates)}")
    except json.JSONDecodeError as e:
        await ctx.error(f"Invalid JSON in bulk_updates: {str(e)}")
        return error_response(
            ErrorCode.VALIDATION_ERROR,
            f"Invalid JSON in bulk_updates: {str(e)}. Please provide valid JSON with bulk update data."
        ).to_json_string()
    except ValidationError as e:
        await ctx.error(f"Invalid bulk update parameters: {str(e)}")
        error_details = []
        # Create a serializable version of validation errors
        # IMPORTANT: Exclude 'ctx' field which contains non-serializable ValueError objects
        serializable_errors = []
        for error in e.errors():
            field = " -> ".join(str(x) for x in error["loc"])
            error_details.append(f"{field}: {error['msg']}")
            # Only include serializable fields, excluding 'ctx' which has ValueError object
            serializable_errors.append({
                "field": field,
                "message": error["msg"],
                "type": error.get("type", "validation_error"),
                "input": error.get("input", "")
            })
        return error_response(
            ErrorCode.VALIDATION_ERROR,
            f"Invalid bulk update parameters: {'; '.join(error_details)}",
            {"validation_errors": serializable_errors, "required_fields": ["requests"]}
        ).to_json_string()
    
    await ctx.info(f"Bulk updating price/quantity for {len(bulk_updates.requests)} inventory items")
    await ctx.report_progress(0.1, "Validating input parameters...")
    
    # Validate individual SKUs
    for req in bulk_updates.requests:
        try:
            _validate_sku_format(req.sku)
        except ValueError as e:
            return error_response(
                ErrorCode.VALIDATION_ERROR,
                f"Invalid SKU '{req.sku}': {e}"
            ).to_json_string()
    
    # Check credentials
    if not mcp.config.app_id or not mcp.config.cert_id:
        return error_response(
            ErrorCode.CONFIGURATION_ERROR,
            "eBay App ID and Cert ID must be configured"
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
        await ctx.report_progress(0.3, "Converting input to eBay API format...")
        
        # Convert Pydantic model to eBay API format
        requests_data = []
        for req in bulk_updates.requests:
            price_quantity_data = {}
            
            if req.price_quantity.offers:
                price_quantity_data["offers"] = req.price_quantity.offers
            
            if req.price_quantity.ship_to_location_availability:
                ship_data = {}
                ship_avail = req.price_quantity.ship_to_location_availability
                
                if ship_avail.allocation_by_format:
                    ship_data["allocationByFormat"] = ship_avail.allocation_by_format
                if ship_avail.availability_distributions:
                    ship_data["availabilityDistributions"] = ship_avail.availability_distributions
                if ship_avail.quantity is not None:
                    ship_data["quantity"] = ship_avail.quantity
                
                if ship_data:
                    price_quantity_data["shipToLocationAvailability"] = ship_data
            
            requests_data.append({
                "sku": req.sku,
                "priceQuantity": price_quantity_data
            })
        
        bulk_data = {"requests": requests_data}
        
        await ctx.report_progress(0.5, f"Updating {len(bulk_updates.requests)} items via eBay API...")
        
        # Make API call
        response = await rest_client.post(
            "/sell/inventory/v1/bulk_update_price_quantity",
            json=bulk_data
        )
        response_body = response["body"]
        
        await ctx.report_progress(0.8, "Processing bulk response...")
        
        # Format response
        responses = response_body.get("responses", [])
        
        # Categorize results
        successful = [r for r in responses if r.get("statusCode") in [200, 201, 204]]
        failed = [r for r in responses if r.get("statusCode") not in [200, 201, 204]]
        
        result_data = {
            "total_items": len(bulk_updates.requests),
            "successful": len(successful),
            "failed": len(failed),
            "responses": responses
        }
        
        await ctx.report_progress(1.0, f"Bulk price/quantity update completed: {len(successful)}/{len(bulk_updates.requests)} successful")
        
        if failed:
            await ctx.warning(f"Bulk update partially successful: {len(failed)} items failed")
        else:
            await ctx.success(f"All {len(successful)} inventory items updated successfully")
        
        return success_response(
            data=result_data,
            message=f"Bulk price/quantity update completed: {len(successful)}/{len(bulk_updates.requests)} items successful"
        ).to_json_string()
        
    except ConsentRequiredException as e:
        await ctx.warning("User consent required for sell.inventory scope")
        return error_response(
            ErrorCode.AUTHENTICATION_ERROR,
            "User consent required for sell.inventory scope",
            {"consent_url": str(e), "scope_required": "sell.inventory"}
        ).to_json_string()
        
    except EbayApiError as e:
        await ctx.error(f"eBay API error: {e.get_comprehensive_message()}")
        return error_response(
            ErrorCode.EXTERNAL_API_ERROR,
            e.get_comprehensive_message(),
            extract_ebay_error_details(e)
        ).to_json_string()
        
    except Exception as e:
        await ctx.error(f"Unexpected error: {e}")
        return error_response(
            ErrorCode.INTERNAL_ERROR,
            "An unexpected error occurred during bulk price/quantity update",
            {"error": str(e)}
        ).to_json_string()
        
    finally:
        await rest_client.close()