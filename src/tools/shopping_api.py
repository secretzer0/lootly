"""eBay Shopping API tools for public data access."""
from typing import List, Optional, Dict, Any
from fastmcp import Context
from pydantic import BaseModel, Field, field_validator
from data_types import success_response, error_response, ErrorCode, validate_tool_input
from logging_config import log_performance
from api.ebay_client import EbayApiClient
from lootly_server import mcp


class GetSingleItemInput(BaseModel):
    """Input model for get_single_item tool."""
    item_id: str = Field(..., description="The eBay item ID")
    include_selector: Optional[str] = Field(
        None,
        description="Comma-separated list of data to include: Description, Details, ItemSpecifics, ShippingCosts, TextDescription, Variations"
    )


class GetMultipleItemsInput(BaseModel):
    """Input model for get_multiple_items tool."""
    item_ids: List[str] = Field(..., description="List of eBay item IDs (max 20)")
    include_selector: Optional[str] = Field(
        None,
        description="Comma-separated list of data to include: Description, Details, ItemSpecifics, ShippingCosts, TextDescription, Variations"
    )
    
    @field_validator("item_ids")
    @classmethod
    def validate_item_count(cls, v):
        if len(v) > 20:
            raise ValueError("Maximum 20 items allowed per request")
        if len(v) == 0:
            raise ValueError("At least one item ID required")
        return v


class GetItemStatusInput(BaseModel):
    """Input model for get_item_status tool."""
    item_id: str = Field(..., description="The eBay item ID to check status for")


class GetShippingCostsInput(BaseModel):
    """Input model for get_shipping_costs tool."""
    item_id: str = Field(..., description="The eBay item ID")
    destination_country_code: str = Field("US", description="Destination country code (e.g., US, GB, DE)")
    destination_postal_code: Optional[str] = Field(None, description="Destination postal code")
    quantity: int = Field(1, description="Quantity of items")


class FindProductsInput(BaseModel):
    """Input model for find_products tool."""
    query_keywords: Optional[str] = Field(None, description="Keywords to search for products")
    product_id: Optional[str] = Field(None, description="Specific product ID to search for")
    category_id: Optional[str] = Field(None, description="Category ID to search within")
    max_entries: int = Field(20, description="Maximum number of products to return")
    
    @field_validator("max_entries")
    @classmethod
    def validate_search_criteria(cls, v, info):
        # Check if at least one search criterion is provided
        if info.data:
            has_keywords = bool(info.data.get("query_keywords"))
            has_product_id = bool(info.data.get("product_id"))
            if not has_keywords and not has_product_id:
                raise ValueError("Either query_keywords or product_id must be provided")
        return v


@mcp.tool
async def get_single_item(
    item_id: str,
    include_selector: Optional[str] = None,
    *,
    ctx: Context
) -> str:
    """
    Get detailed public information about a specific eBay item.
    
    This tool retrieves comprehensive information about a single eBay listing,
    including price, description, seller info, shipping details, and more.
    The Shopping API provides public data and doesn't require user authentication.
    
    Args:
        item_id: The eBay item ID (e.g., "123456789012")
        include_selector: Optional comma-separated list of additional data to include:
            - Description: Full item description
            - Details: Additional item details
            - ItemSpecifics: Item condition and specifications
            - ShippingCosts: Calculated shipping costs
            - TextDescription: Plain text description
            - Variations: Color, size, and other variations
        ctx: MCP context for logging
    
    Returns:
        JSON response with detailed item information
    """
    server = ctx.server
    client = EbayApiClient(server.config, server.logger)
    
    await ctx.info(f"Getting details for item ID: {item_id}")
    await ctx.report_progress(0.1, "Validating input...")
    
    try:
        # Validate input
        input_data = validate_tool_input(GetSingleItemInput, {
            "item_id": item_id,
            "include_selector": include_selector
        })
        
        # Build API parameters
        params = {"ItemID": input_data.item_id}
        if input_data.include_selector:
            params["IncludeSelector"] = input_data.include_selector
        
        await ctx.report_progress(0.3, "Fetching item details from eBay...")
        
        # Execute API call
        response = await client.execute_with_retry(
            "shopping",
            "GetSingleItem",
            params
        )
        
        await ctx.report_progress(0.8, "Processing item data...")
        
        # Extract and format item data
        item = response.get("Item", {})
        
        formatted_item = {
            "item_id": item.get("ItemID"),
            "title": item.get("Title"),
            "subtitle": item.get("Subtitle"),
            "price": {
                "value": float(item.get("CurrentPrice", {}).get("value", 0)),
                "currency": item.get("CurrentPrice", {}).get("_currencyID", "USD")
            },
            "condition": {
                "id": item.get("ConditionID"),
                "name": item.get("ConditionDisplayName")
            },
            "quantity": {
                "available": item.get("Quantity"),
                "sold": item.get("QuantitySold")
            },
            "seller": {
                "user_id": item.get("Seller", {}).get("UserID"),
                "feedback_score": item.get("Seller", {}).get("FeedbackScore"),
                "positive_feedback_percent": item.get("Seller", {}).get("PositiveFeedbackPercent"),
                "top_rated": item.get("Seller", {}).get("TopRatedSeller")
            },
            "location": {
                "city": item.get("Location"),
                "country": item.get("Country"),
                "postal_code": item.get("PostalCode")
            },
            "listing_info": {
                "type": item.get("ListingType"),
                "status": item.get("ListingStatus"),
                "start_time": item.get("StartTime"),
                "end_time": item.get("EndTime"),
                "view_url": item.get("ViewItemURLForNaturalSearch")
            },
            "images": {
                "gallery_url": item.get("GalleryURL"),
                "picture_urls": item.get("PictureURL", [])
            },
            "shipping": {
                "cost": float(item.get("ShippingCostSummary", {}).get("ShippingServiceCost", {}).get("value", 0)) if item.get("ShippingCostSummary") else None,
                "type": item.get("ShippingCostSummary", {}).get("ShippingType")
            },
            "payment_methods": item.get("PaymentMethods", []),
            "return_policy": {
                "accepted": item.get("ReturnPolicy", {}).get("ReturnsAccepted"),
                "days": item.get("ReturnPolicy", {}).get("ReturnsWithin"),
                "shipping_paid_by": item.get("ReturnPolicy", {}).get("ShippingCostPaidBy")
            }
        }
        
        # Add optional data if requested
        if include_selector:
            if "Description" in include_selector:
                formatted_item["description"] = item.get("Description")
            if "ItemSpecifics" in include_selector:
                formatted_item["item_specifics"] = item.get("ItemSpecifics", {}).get("NameValueList", [])
            if "Variations" in include_selector and item.get("Variations"):
                formatted_item["variations"] = item.get("Variations", {}).get("Variation", [])
        
        await ctx.report_progress(1.0, "Complete")
        await ctx.info(f"Successfully retrieved details for item: {item.get('Title', 'Unknown')}")
        
        return success_response(
            data=formatted_item,
            message=f"Successfully retrieved item details"
        ).to_json_string()
        
    except ValueError as e:
        await ctx.error(f"Invalid input: {str(e)}")
        return error_response(
            ErrorCode.VALIDATION_ERROR,
            str(e)
        ).to_json_string()
    except Exception as e:
        await ctx.error(f"Failed to get item details: {str(e)}")
        server.logger.tool_failed("get_single_item", str(e), 0)
        return error_response(
            ErrorCode.INTERNAL_ERROR,
            f"Failed to retrieve item details: {str(e)}"
        ).to_json_string()


@mcp.tool
async def get_item_status(
    item_id: str,
    *,
    ctx: Context
) -> str:
    """
    Get the current listing status of an eBay item.
    
    This tool quickly checks whether an item is still active, sold, ended,
    or otherwise unavailable. Useful for verifying item availability before
    taking further actions.
    
    Args:
        item_id: The eBay item ID to check
        ctx: MCP context for logging
    
    Returns:
        JSON response with item status, quantity available, and basic info
    """
    server = ctx.server
    client = EbayApiClient(server.config, server.logger)
    
    await ctx.info(f"Checking status for item ID: {item_id}")
    
    try:
        # Validate input
        input_data = validate_tool_input(GetItemStatusInput, {
            "item_id": item_id
        })
        
        # Execute API call with minimal data
        params = {"ItemID": input_data.item_id}
        response = await client.execute_with_retry(
            "shopping",
            "GetItemStatus",
            params
        )
        
        # Extract status information
        item = response.get("Item", {})
        
        status_info = {
            "item_id": item.get("ItemID"),
            "title": item.get("Title"),
            "listing_status": item.get("ListingStatus"),
            "quantity_available": item.get("Quantity", 0) - item.get("QuantitySold", 0),
            "quantity_sold": item.get("QuantitySold", 0),
            "current_price": {
                "value": float(item.get("CurrentPrice", {}).get("value", 0)),
                "currency": item.get("CurrentPrice", {}).get("_currencyID", "USD")
            },
            "end_time": item.get("EndTime"),
            "bid_count": item.get("BidCount", 0),
            "watch_count": item.get("WatchCount", 0),
            "is_available": item.get("ListingStatus") == "Active" and (item.get("Quantity", 0) - item.get("QuantitySold", 0)) > 0
        }
        
        await ctx.info(f"Item status: {status_info['listing_status']} (Available: {status_info['is_available']})")
        
        return success_response(
            data=status_info,
            message=f"Item is {'available' if status_info['is_available'] else 'not available'}"
        ).to_json_string()
        
    except ValueError as e:
        await ctx.error(f"Invalid input: {str(e)}")
        return error_response(
            ErrorCode.VALIDATION_ERROR,
            str(e)
        ).to_json_string()
    except Exception as e:
        await ctx.error(f"Failed to check item status: {str(e)}")
        server.logger.tool_failed("get_item_status", str(e), 0)
        return error_response(
            ErrorCode.INTERNAL_ERROR,
            f"Failed to check item status: {str(e)}"
        ).to_json_string()


@mcp.tool
async def get_shipping_costs(
    item_id: str,
    destination_country_code: str = "US",
    destination_postal_code: Optional[str] = None,
    quantity: int = 1,
    *,
    ctx: Context
) -> str:
    """
    Calculate shipping costs for an eBay item to a specific destination.
    
    This tool calculates the shipping cost for an item based on the buyer's
    location. Useful for determining total cost including shipping before purchase.
    
    Args:
        item_id: The eBay item ID
        destination_country_code: Destination country code (e.g., US, GB, DE)
        destination_postal_code: Optional postal/ZIP code for more accurate rates
        quantity: Number of items (default: 1)
        ctx: MCP context for logging
    
    Returns:
        JSON response with shipping options and costs
    """
    server = ctx.server
    client = EbayApiClient(server.config, server.logger)
    
    await ctx.info(f"Calculating shipping for item {item_id} to {destination_country_code}")
    await ctx.report_progress(0.1, "Validating shipping parameters...")
    
    try:
        # Validate input
        input_data = validate_tool_input(GetShippingCostsInput, {
            "item_id": item_id,
            "destination_country_code": destination_country_code,
            "destination_postal_code": destination_postal_code,
            "quantity": quantity
        })
        
        # Build API parameters
        params = {
            "ItemID": input_data.item_id,
            "DestinationCountryCode": input_data.destination_country_code,
            "QuantitySold": input_data.quantity,
            "IncludeDetails": "true"
        }
        
        if input_data.destination_postal_code:
            params["DestinationPostalCode"] = input_data.destination_postal_code
        
        await ctx.report_progress(0.3, "Fetching shipping rates...")
        
        # Execute API call
        response = await client.execute_with_retry(
            "shopping",
            "GetShippingCosts",
            params
        )
        
        await ctx.report_progress(0.8, "Processing shipping options...")
        
        # Extract shipping details
        shipping_details = response.get("ShippingDetails", {})
        shipping_cost_summary = response.get("ShippingCostSummary", {})
        
        # Format shipping options
        shipping_options = []
        for service in shipping_details.get("ShippingServiceOptions", []):
            option = {
                "service_name": service.get("ShippingServiceName"),
                "cost": {
                    "value": float(service.get("ShippingServiceCost", {}).get("value", 0)),
                    "currency": service.get("ShippingServiceCost", {}).get("_currencyID", "USD")
                },
                "priority": service.get("ShippingServicePriority"),
                "estimated_delivery": service.get("EstimatedDeliveryTime")
            }
            shipping_options.append(option)
        
        # International shipping options if applicable
        international_options = []
        for service in shipping_details.get("InternationalShippingServiceOptions", []):
            option = {
                "service_name": service.get("ShippingServiceName"),
                "cost": {
                    "value": float(service.get("ShippingServiceCost", {}).get("value", 0)),
                    "currency": service.get("ShippingServiceCost", {}).get("_currencyID", "USD")
                },
                "priority": service.get("ShippingServicePriority"),
                "ships_to": service.get("ShipToLocation", [])
            }
            international_options.append(option)
        
        result = {
            "item_id": item_id,
            "destination": {
                "country_code": input_data.destination_country_code,
                "postal_code": input_data.destination_postal_code
            },
            "quantity": input_data.quantity,
            "shipping_type": shipping_cost_summary.get("ShippingType"),
            "listing_currency": shipping_cost_summary.get("ListedShippingServiceCost", {}).get("_currencyID", "USD"),
            "domestic_shipping": shipping_options,
            "international_shipping": international_options if destination_country_code != "US" else [],
            "insurance_available": shipping_details.get("InsuranceOption") == "Optional",
            "insurance_cost": float(shipping_details.get("InsuranceCost", {}).get("value", 0)) if shipping_details.get("InsuranceCost") else None
        }
        
        await ctx.report_progress(1.0, "Complete")
        await ctx.info(f"Found {len(shipping_options)} shipping options")
        
        return success_response(
            data=result,
            message=f"Successfully calculated shipping costs to {destination_country_code}"
        ).to_json_string()
        
    except ValueError as e:
        await ctx.error(f"Invalid input: {str(e)}")
        return error_response(
            ErrorCode.VALIDATION_ERROR,
            str(e)
        ).to_json_string()
    except Exception as e:
        await ctx.error(f"Failed to calculate shipping: {str(e)}")
        server.logger.tool_failed("get_shipping_costs", str(e), 0)
        return error_response(
            ErrorCode.INTERNAL_ERROR,
            f"Failed to calculate shipping costs: {str(e)}"
        ).to_json_string()


@mcp.tool
async def get_multiple_items(
    item_ids: List[str],
    include_selector: Optional[str] = None,
    *,
    ctx: Context
) -> str:
    """
    Get details for multiple eBay items in a single request.
    
    This tool efficiently retrieves information for up to 20 items at once,
    reducing the number of API calls needed when checking multiple listings.
    
    Args:
        item_ids: List of eBay item IDs (maximum 20)
        include_selector: Optional comma-separated list of additional data to include
        ctx: MCP context for logging
    
    Returns:
        JSON response with details for all requested items
    """
    server = ctx.server
    client = EbayApiClient(server.config, server.logger)
    
    await ctx.info(f"Getting details for {len(item_ids)} items")
    await ctx.report_progress(0.1, "Validating item IDs...")
    
    try:
        # Validate input
        input_data = validate_tool_input(GetMultipleItemsInput, {
            "item_ids": item_ids,
            "include_selector": include_selector
        })
        
        # Build API parameters
        params = {"ItemID": ",".join(input_data.item_ids)}
        if input_data.include_selector:
            params["IncludeSelector"] = input_data.include_selector
        
        await ctx.report_progress(0.3, f"Fetching details for {len(input_data.item_ids)} items...")
        
        # Execute API call
        response = await client.execute_with_retry(
            "shopping",
            "GetMultipleItems",
            params
        )
        
        await ctx.report_progress(0.8, "Processing items...")
        
        # Extract and format items
        items = response.get("Item", [])
        if not isinstance(items, list):
            items = [items]
        
        formatted_items = []
        for item in items:
            formatted_item = {
                "item_id": item.get("ItemID"),
                "title": item.get("Title"),
                "price": {
                    "value": float(item.get("CurrentPrice", {}).get("value", 0)),
                    "currency": item.get("CurrentPrice", {}).get("_currencyID", "USD")
                },
                "condition": {
                    "id": item.get("ConditionID"),
                    "name": item.get("ConditionDisplayName")
                },
                "quantity_available": item.get("Quantity", 0) - item.get("QuantitySold", 0),
                "seller": {
                    "user_id": item.get("Seller", {}).get("UserID"),
                    "feedback_score": item.get("Seller", {}).get("FeedbackScore")
                },
                "location": item.get("Location"),
                "listing_status": item.get("ListingStatus"),
                "end_time": item.get("EndTime"),
                "view_url": item.get("ViewItemURLForNaturalSearch"),
                "gallery_url": item.get("GalleryURL")
            }
            formatted_items.append(formatted_item)
        
        # Check for items not found
        items_found = {item["item_id"] for item in formatted_items}
        items_not_found = [item_id for item_id in input_data.item_ids if item_id not in items_found]
        
        await ctx.report_progress(1.0, "Complete")
        await ctx.info(f"Retrieved {len(formatted_items)} of {len(input_data.item_ids)} items")
        
        return success_response(
            data={
                "items": formatted_items,
                "summary": {
                    "requested": len(input_data.item_ids),
                    "found": len(formatted_items),
                    "not_found": items_not_found
                }
            },
            message=f"Successfully retrieved {len(formatted_items)} items"
        ).to_json_string()
        
    except ValueError as e:
        await ctx.error(f"Invalid input: {str(e)}")
        return error_response(
            ErrorCode.VALIDATION_ERROR,
            str(e)
        ).to_json_string()
    except Exception as e:
        await ctx.error(f"Failed to get multiple items: {str(e)}")
        server.logger.tool_failed("get_multiple_items", str(e), 0)
        return error_response(
            ErrorCode.INTERNAL_ERROR,
            f"Failed to retrieve items: {str(e)}"
        ).to_json_string()


@mcp.tool
async def find_products(
    query_keywords: Optional[str] = None,
    product_id: Optional[str] = None,
    category_id: Optional[str] = None,
    max_entries: int = 20,
    *,
    ctx: Context
) -> str:
    """
    Search the eBay product catalog for product information.
    
    This tool searches eBay's product catalog to find standardized product
    information, including specifications, reviews, and stock photos. Products
    represent items that multiple sellers might be offering.
    
    Args:
        query_keywords: Keywords to search for products (e.g., "iPhone 15 Pro")
        product_id: Specific eBay product ID if known
        category_id: Category ID to search within
        max_entries: Maximum number of products to return (default: 20)
        ctx: MCP context for logging
    
    Returns:
        JSON response with product catalog information
    """
    server = ctx.server
    client = EbayApiClient(server.config, server.logger)
    
    search_criteria = query_keywords or product_id or "general search"
    await ctx.info(f"Searching product catalog: {search_criteria}")
    await ctx.report_progress(0.1, "Preparing product search...")
    
    try:
        # Validate input
        input_data = validate_tool_input(FindProductsInput, {
            "query_keywords": query_keywords,
            "product_id": product_id,
            "category_id": category_id,
            "max_entries": max_entries
        })
        
        # Build API parameters
        params = {"MaxEntries": input_data.max_entries}
        
        if input_data.query_keywords:
            params["QueryKeywords"] = input_data.query_keywords
        if input_data.product_id:
            params["ProductID"] = input_data.product_id
        if input_data.category_id:
            params["CategoryID"] = input_data.category_id
        
        await ctx.report_progress(0.3, "Searching eBay product catalog...")
        
        # Execute API call
        response = await client.execute_with_retry(
            "shopping",
            "FindProducts",
            params
        )
        
        await ctx.report_progress(0.8, "Processing product data...")
        
        # Extract products
        products = response.get("Product", [])
        if not isinstance(products, list):
            products = [products] if products else []
        
        formatted_products = []
        for product in products:
            formatted_product = {
                "product_id": product.get("ProductID", {}).get("Value") if product.get("ProductID") else None,
                "title": product.get("Title"),
                "details_url": product.get("DetailsURL"),
                "stock_photo_url": product.get("StockPhotoURL"),
                "display_stock_photos": product.get("DisplayStockPhotos", False),
                "item_specifics": {},
                "review_info": {
                    "count": product.get("ReviewCount", 0),
                    "average_rating": product.get("ReviewDetails", {}).get("AverageRating") if product.get("ReviewDetails") else None
                },
                "min_price": {
                    "value": float(product.get("MinPrice", {}).get("value", 0)) if product.get("MinPrice") else None,
                    "currency": product.get("MinPrice", {}).get("_currencyID", "USD") if product.get("MinPrice") else "USD"
                },
                "domain_name": product.get("DomainName"),
                "item_count": product.get("ItemCount", 0)
            }
            
            # Extract item specifics
            specifics = product.get("ItemSpecifics", {}).get("NameValueList", [])
            if not isinstance(specifics, list):
                specifics = [specifics] if specifics else []
            
            for spec in specifics:
                name = spec.get("Name")
                values = spec.get("Value", [])
                if not isinstance(values, list):
                    values = [values]
                formatted_product["item_specifics"][name] = values
            
            formatted_products.append(formatted_product)
        
        # Get total products found
        total_products = int(response.get("TotalProducts", 0))
        
        await ctx.report_progress(1.0, "Complete")
        await ctx.info(f"Found {len(formatted_products)} products in catalog")
        
        return success_response(
            data={
                "products": formatted_products,
                "summary": {
                    "total_products": total_products,
                    "returned": len(formatted_products),
                    "has_more": total_products > len(formatted_products)
                },
                "search_criteria": {
                    "keywords": input_data.query_keywords,
                    "product_id": input_data.product_id,
                    "category_id": input_data.category_id
                }
            },
            message=f"Found {total_products} products in catalog"
        ).to_json_string()
        
    except ValueError as e:
        await ctx.error(f"Invalid input: {str(e)}")
        return error_response(
            ErrorCode.VALIDATION_ERROR,
            str(e)
        ).to_json_string()
    except Exception as e:
        await ctx.error(f"Product search failed: {str(e)}")
        server.logger.tool_failed("find_products", str(e), 0)
        return error_response(
            ErrorCode.INTERNAL_ERROR,
            f"Failed to search products: {str(e)}"
        ).to_json_string()


# Legacy functions maintained for compatibility
@mcp.tool
async def get_user_profile(ctx: Context) -> str:
    """Get public user profile. (Deprecated - use Trading API get_user_info instead)"""
    return error_response(
        ErrorCode.NOT_IMPLEMENTED,
        "get_user_profile is deprecated. Use Trading API get_user_info instead for user information."
    ).to_json_string()


@mcp.tool
async def get_category_info(ctx: Context) -> str:
    """Get category information. (Deprecated - use Categories resource instead)"""
    return error_response(
        ErrorCode.NOT_IMPLEMENTED,
        "get_category_info is deprecated. Use the ebay_categories resource for category information."
    ).to_json_string()