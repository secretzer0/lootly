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
from typing import Optional, Dict, Any, List
from fastmcp import Context

from api.oauth import OAuthManager, OAuthConfig, ConsentRequiredException
from api.rest_client import EbayRestClient, RestConfig
from api.errors import EbayApiError, extract_ebay_error_details
from models.inventory import (
    InventoryItemInput,
    BulkInventoryItemInput, BulkPriceQuantityInput
)
from data_types import success_response, error_response, ErrorCode
from lootly_server import mcp


# HELPER FUNCTIONS

def _validate_sku_format(sku: str) -> None:
    """Validate SKU format requirements."""
    if not sku or not sku.strip():
        raise ValueError("SKU is required")
    
    if len(sku) > 50:
        raise ValueError("SKU cannot exceed 50 characters")
    
    # Allow alphanumeric, hyphens, and underscores
    import re
    if not re.match(r'^[a-zA-Z0-9_-]+$', sku):
        raise ValueError("SKU can only contain alphanumeric characters, hyphens, and underscores")


def _build_inventory_item_data(inventory_item: InventoryItemInput) -> Dict[str, Any]:
    """Convert Pydantic InventoryItemInput to eBay API format."""
    item_data = {}
    
    # Add availability
    if inventory_item.availability:
        availability_data = {}
        
        if inventory_item.availability.pickup_at_location_availability:
            pickup = inventory_item.availability.pickup_at_location_availability
            pickup_data = {}
            if pickup.availability_type:
                pickup_data["availabilityType"] = pickup.availability_type.value
            if pickup.fulfillment_time:
                pickup_data["fulfillmentTime"] = pickup.fulfillment_time
            if pickup.merchant_location_key:
                pickup_data["merchantLocationKey"] = pickup.merchant_location_key
            if pickup.quantity is not None:
                pickup_data["quantity"] = pickup.quantity
            availability_data["pickupAtLocationAvailability"] = [pickup_data]
        
        if inventory_item.availability.ship_to_location_availability:
            ship = inventory_item.availability.ship_to_location_availability
            ship_data = {}
            if ship.allocation_by_format:
                ship_data["allocationByFormat"] = ship.allocation_by_format
            if ship.availability_distributions:
                ship_data["availabilityDistributions"] = ship.availability_distributions
            if ship.quantity is not None:
                ship_data["quantity"] = ship.quantity
            availability_data["shipToLocationAvailability"] = ship_data
        
        if availability_data:
            item_data["availability"] = availability_data
    
    # Add condition
    if inventory_item.condition:
        item_data["condition"] = inventory_item.condition.value
    
    # Add package weight and size
    if inventory_item.packageWeightAndSize:
        package_data = {}
        pkg = inventory_item.packageWeightAndSize
        
        if pkg.dimensions:
            dims = {}
            if pkg.dimensions.height is not None:
                dims["height"] = pkg.dimensions.height
            if pkg.dimensions.length is not None:
                dims["length"] = pkg.dimensions.length
            if pkg.dimensions.width is not None:
                dims["width"] = pkg.dimensions.width
            if pkg.dimensions.unit:
                dims["unit"] = pkg.dimensions.unit.value
            package_data["dimensions"] = dims
        
        if pkg.package_type:
            package_data["packageType"] = pkg.package_type.value
        
        if pkg.weight:
            weight_data = {}
            if pkg.weight.unit:
                weight_data["unit"] = pkg.weight.unit.value
            if pkg.weight.value is not None:
                weight_data["value"] = pkg.weight.value
            package_data["weight"] = weight_data
        
        if package_data:
            item_data["packageWeightAndSize"] = package_data
    
    # Add product
    if inventory_item.product:
        product_data = {}
        prod = inventory_item.product
        
        if prod.aspects:
            product_data["aspects"] = prod.aspects
        if prod.brand:
            product_data["brand"] = prod.brand
        if prod.description:
            product_data["description"] = prod.description
        if prod.ean:
            product_data["ean"] = prod.ean
        if prod.epid:
            product_data["epid"] = prod.epid
        if prod.imageUrls:
            product_data["imageUrls"] = prod.imageUrls
        if prod.isbn:
            product_data["isbn"] = prod.isbn
        if prod.mpn:
            product_data["mpn"] = prod.mpn
        if prod.title:
            product_data["title"] = prod.title
        if prod.upc:
            product_data["upc"] = prod.upc
        
        if product_data:
            item_data["product"] = product_data
    
    return item_data


def _format_inventory_item_response(item_data: Dict[str, Any]) -> Dict[str, Any]:
    """Format eBay inventory item response for consistent output."""
    formatted = {
        "sku": item_data.get("sku"),
        "locale": item_data.get("locale"),
        "availability": item_data.get("availability"),
        "condition": item_data.get("condition"),
        "conditionDescription": item_data.get("conditionDescription"),
        "packageWeightAndSize": item_data.get("packageWeightAndSize"),
        "product": item_data.get("product")
    }
    
    # Clean up None values
    return {k: v for k, v in formatted.items() if v is not None}




# MCP TOOLS - Using imported models from models.inventory

@mcp.tool
async def create_or_replace_inventory_item(
    ctx: Context,
    sku: str,
    inventory_item: InventoryItemInput
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
        inventory_item: Complete inventory item configuration
        ctx: MCP context
    
    Returns:
        JSON response confirming creation/update
    
    OAuth Scope Required: https://api.ebay.com/oauth/api_scope/sell.inventory
    """
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
    bulk_input: BulkInventoryItemInput
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
    await ctx.info(f"Bulk creating/replacing {len(bulk_input.requests)} inventory items")
    await ctx.report_progress(0.1, "Validating input parameters...")
    
    # Pydantic validation already handled - no manual validation needed!
    
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
    bulk_updates: BulkPriceQuantityInput
) -> str:
    """
    Update price and quantity for multiple inventory items efficiently.
    
    Optimized for high-frequency updates to pricing and inventory levels.
    Processes up to 25 items simultaneously with minimal data transfer.
    
    Args:
        bulk_updates: Bulk price and quantity update data (max 25 items)
        ctx: MCP context
    
    Returns:
        JSON response with individual update results and overall status
    
    OAuth Scope Required: https://api.ebay.com/oauth/api_scope/sell.inventory
    """
    await ctx.info(f"Bulk updating price/quantity for {len(bulk_updates.requests)} inventory items")
    await ctx.report_progress(0.1, "Validating input parameters...")
    
    # Pydantic validation already handled - no manual validation needed!
    
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
            
            # Add price if provided
            if req.price_quantity.price is not None:
                price_quantity_data["price"] = str(req.price_quantity.price)
            
            # Add quantity if provided  
            if req.price_quantity.quantity is not None:
                price_quantity_data["quantity"] = req.price_quantity.quantity
            
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