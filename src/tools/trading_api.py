"""eBay Trading API tools for selling and user management."""
from typing import Dict, Any, Optional, List
from fastmcp import Context
from data_types import success_response, error_response, ErrorCode, validate_tool_input
from logging_config import log_performance
from pydantic import BaseModel, Field, field_validator
from api.ebay_client import EbayApiClient
from datetime import datetime
import uuid
from lootly_server import mcp


class CreateListingInput(BaseModel):
    """Input model for create_listing tool."""
    title: str = Field(..., min_length=1, max_length=80, description="Item title (max 80 characters)")
    description: str = Field(..., min_length=10, description="Detailed item description")
    category_id: str = Field(..., description="eBay category ID for the item")
    start_price: float = Field(..., gt=0, description="Starting price in USD")
    buy_it_now_price: Optional[float] = Field(None, description="Buy It Now price (optional)")
    quantity: int = Field(1, ge=1, description="Number of items available")
    duration: str = Field("Days_7", description="Listing duration: Days_1, Days_3, Days_5, Days_7, Days_10, Days_30, GTC")
    condition_id: str = Field(..., description="Item condition ID: 1000 (New), 3000 (Used), etc.")
    shipping_service: str = Field(..., description="Shipping service: USPSPriority, FedExHomeDelivery, etc.")
    shipping_cost: float = Field(..., ge=0, description="Shipping cost in USD (0 for free shipping)")
    return_policy_days: str = Field("Days_30", description="Return period: Days_14, Days_30, Days_60")
    payment_methods: List[str] = Field(["PayPal"], description="Accepted payment methods")
    picture_urls: Optional[List[str]] = Field(None, description="List of picture URLs (up to 12)")
    
    @field_validator('duration')
    @classmethod
    def validate_duration(cls, v):
        valid_durations = ["Days_1", "Days_3", "Days_5", "Days_7", "Days_10", "Days_30", "GTC"]
        if v not in valid_durations:
            raise ValueError(f"Duration must be one of: {', '.join(valid_durations)}")
        return v
    
    @field_validator('picture_urls')
    @classmethod
    def validate_pictures(cls, v):
        if v and len(v) > 12:
            raise ValueError("Maximum 12 pictures allowed")
        return v


@mcp.tool
async def create_listing(
    title: str,
    description: str,
    category_id: str,
    start_price: float,
    condition_id: str,
    shipping_service: str,
    shipping_cost: float,
    buy_it_now_price: Optional[float] = None,
    quantity: int = 1,
    duration: str = "Days_7",
    return_policy_days: str = "Days_30",
    payment_methods: List[str] = ["PayPal"],
    picture_urls: Optional[List[str]] = None,
    *,
    ctx: Context
) -> str:
    """
    Create a new eBay listing.
    
    This tool creates a new item listing on eBay with all necessary details including
    pricing, shipping, return policy, and pictures.
    
    Args:
        title: Item title (max 80 characters)
        description: Detailed item description with condition, features, etc.
        category_id: eBay category ID (use categories resource to find)
        start_price: Starting price for auction or fixed price
        condition_id: Item condition (1000=New, 3000=Used, etc.)
        shipping_service: Shipping method (USPSPriority, FedExHomeDelivery, etc.)
        shipping_cost: Shipping cost in USD (0 for free shipping)
        buy_it_now_price: Optional Buy It Now price
        quantity: Number of items available
        duration: Listing duration (Days_7, Days_30, GTC, etc.)
        return_policy_days: Return acceptance period
        payment_methods: List of accepted payment methods
        picture_urls: URLs of item pictures (up to 12)
        ctx: MCP context for logging
    
    Returns:
        JSON response with the created listing details including item ID and fees
    """
    # Import mcp at function level
    from lootly_server import mcp
    
    await ctx.info(f"Creating new eBay listing: {title}")
    await ctx.report_progress(0.1, "Validating listing parameters...")
    
    # Check if credentials are available
    if not mcp.config.app_id or not mcp.config.cert_id or not mcp.config.dev_id:
        return success_response(
            data={
                "item_id": None,
                "listing_url": None,
                "fees": {"total": 0, "currency": "USD"},
                "status": "Not Created",
                "note": "eBay API credentials not configured. To create listings, please set EBAY_APP_ID, EBAY_CERT_ID, and EBAY_DEV_ID environment variables."
            },
            message="eBay API credentials not available - see note for setup instructions"
        ).to_json_string()
    
    # Create client after credential check
    client = EbayApiClient(mcp.config, mcp.logger)
    
    try:
        # Validate input
        input_data = validate_tool_input(CreateListingInput, {
            "title": title,
            "description": description,
            "category_id": category_id,
            "start_price": start_price,
            "buy_it_now_price": buy_it_now_price,
            "quantity": quantity,
            "duration": duration,
            "condition_id": condition_id,
            "shipping_service": shipping_service,
            "shipping_cost": shipping_cost,
            "return_policy_days": return_policy_days,
            "payment_methods": payment_methods,
            "picture_urls": picture_urls
        })
        
        await ctx.report_progress(0.2, "Building listing data...")
        
        # Build the item data for AddItem call
        item_data = {
            "Item": {
                "Title": input_data.title,
                "Description": input_data.description,
                "PrimaryCategory": {"CategoryID": input_data.category_id},
                "StartPrice": str(input_data.start_price),
                "ConditionID": input_data.condition_id,
                "Country": "US",
                "Currency": "USD",
                "DispatchTimeMax": "3",
                "ListingDuration": input_data.duration,
                "ListingType": "FixedPriceItem" if not input_data.buy_it_now_price else "Chinese",
                "PaymentMethods": input_data.payment_methods,
                "Quantity": str(input_data.quantity),
                "ReturnPolicy": {
                    "ReturnsAcceptedOption": "ReturnsAccepted",
                    "RefundOption": "MoneyBack",
                    "ReturnsWithinOption": input_data.return_policy_days,
                    "ShippingCostPaidByOption": "Buyer"
                },
                "ShippingDetails": {
                    "ShippingType": "Flat",
                    "ShippingServiceOptions": {
                        "ShippingServicePriority": "1",
                        "ShippingService": input_data.shipping_service,
                        "ShippingServiceCost": str(input_data.shipping_cost)
                    }
                },
                "Site": "US"
            }
        }
        
        # Add Buy It Now price if provided
        if input_data.buy_it_now_price:
            item_data["Item"]["BuyItNowPrice"] = str(input_data.buy_it_now_price)
        
        # Add pictures if provided
        if input_data.picture_urls:
            item_data["Item"]["PictureDetails"] = {
                "PictureURL": input_data.picture_urls
            }
        
        await ctx.report_progress(0.4, "Submitting listing to eBay...")
        
        # Execute the AddItem call
        response = await client.execute_with_retry(
            "trading",
            "AddItem",
            item_data,
            use_cache=False
        )
        
        await ctx.report_progress(0.8, "Processing response...")
        
        # Extract key information from response
        item_id = response.get("ItemID", [None])[0]
        fees = response.get("Fees", {})
        
        # Calculate total fees
        total_fee = 0
        fee_details = []
        for fee in fees.get("Fee", []):
            fee_name = fee.get("Name", "Unknown")
            fee_amount = float(fee.get("Fee", {}).get("value", 0))
            if fee_amount > 0:
                fee_details.append({
                    "name": fee_name,
                    "amount": fee_amount
                })
                total_fee += fee_amount
        
        await ctx.report_progress(1.0, "Listing created successfully")
        await ctx.info(f"Created listing with Item ID: {item_id}")
        
        return success_response(
            data={
                "item_id": item_id,
                "title": input_data.title,
                "status": "active",
                "listing_url": f"https://www.{mcp.config.domain}/itm/{item_id}",
                "fees": {
                    "total": round(total_fee, 2),
                    "details": fee_details
                },
                "listing_details": {
                    "start_price": input_data.start_price,
                    "buy_it_now_price": input_data.buy_it_now_price,
                    "quantity": input_data.quantity,
                    "duration": input_data.duration,
                    "category_id": input_data.category_id
                }
            },
            message=f"Successfully created listing '{title}' with ID {item_id}"
        ).to_json_string()
        
    except ValueError as e:
        await ctx.error(f"Invalid listing parameters: {str(e)}")
        return error_response(
            ErrorCode.VALIDATION_ERROR,
            str(e)
        ).to_json_string()
    except Exception as e:
        await ctx.error(f"Failed to create listing: {str(e)}")
        mcp.logger.tool_failed("create_listing", str(e), 0)
        return error_response(
            ErrorCode.INTERNAL_ERROR,
            f"Failed to create listing: {str(e)}"
        ).to_json_string()


class ReviseListingInput(BaseModel):
    """Input model for revise_listing tool."""
    item_id: str = Field(..., description="eBay item ID to revise")
    title: Optional[str] = Field(None, max_length=80, description="New title")
    description: Optional[str] = Field(None, description="New description")
    price: Optional[float] = Field(None, gt=0, description="New price")
    quantity: Optional[int] = Field(None, ge=0, description="New quantity")
    shipping_cost: Optional[float] = Field(None, ge=0, description="New shipping cost")
    picture_urls: Optional[List[str]] = Field(None, description="New picture URLs")


@mcp.tool
async def revise_listing(
    item_id: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    price: Optional[float] = None,
    quantity: Optional[int] = None,
    shipping_cost: Optional[float] = None,
    picture_urls: Optional[List[str]] = None,
    *,
    ctx: Context
) -> str:
    """
    Update an existing eBay listing.
    
    This tool allows you to revise various aspects of an active listing including
    title, description, price, quantity, and pictures.
    
    Args:
        item_id: The eBay item ID to revise
        title: New title (optional)
        description: New description (optional)
        price: New price (optional)
        quantity: New quantity (optional)
        shipping_cost: New shipping cost (optional)
        picture_urls: New picture URLs (optional)
        ctx: MCP context for logging
    
    Returns:
        JSON response confirming the revision with updated details
    """
    # Import mcp at function level
    from lootly_server import mcp
    
    await ctx.info(f"Revising eBay listing: {item_id}")
    await ctx.report_progress(0.1, "Validating revision parameters...")
    
    # Check if credentials are available
    if not mcp.config.app_id or not mcp.config.cert_id or not mcp.config.dev_id:
        return success_response(
            data={
                "item_id": item_id,
                "revised_fields": [],
                "status": "Not Revised",
                "note": "eBay API credentials not configured. To revise listings, please set EBAY_APP_ID, EBAY_CERT_ID, and EBAY_DEV_ID environment variables."
            },
            message="eBay API credentials not available - see note for setup instructions"
        ).to_json_string()
    
    # Create client after credential check
    client = EbayApiClient(mcp.config, mcp.logger)
    
    try:
        # Validate input
        input_data = validate_tool_input(ReviseListingInput, {
            "item_id": item_id,
            "title": title,
            "description": description,
            "price": price,
            "quantity": quantity,
            "shipping_cost": shipping_cost,
            "picture_urls": picture_urls
        })
        
        # Check if any fields to update
        if not any([title, description, price, quantity, shipping_cost, picture_urls]):
            return error_response(
                ErrorCode.VALIDATION_ERROR,
                "At least one field must be provided to update"
            ).to_json_string()
        
        await ctx.report_progress(0.3, "Building revision data...")
        
        # Build revision data
        revision_data = {
            "Item": {
                "ItemID": input_data.item_id
            }
        }
        
        # Add fields to revise
        if input_data.title:
            revision_data["Item"]["Title"] = input_data.title
        if input_data.description:
            revision_data["Item"]["Description"] = input_data.description
        if input_data.price:
            revision_data["Item"]["StartPrice"] = str(input_data.price)
        if input_data.quantity is not None:
            revision_data["Item"]["Quantity"] = str(input_data.quantity)
        if input_data.shipping_cost is not None:
            revision_data["Item"]["ShippingDetails"] = {
                "ShippingServiceOptions": {
                    "ShippingServiceCost": str(input_data.shipping_cost)
                }
            }
        if input_data.picture_urls:
            revision_data["Item"]["PictureDetails"] = {
                "PictureURL": input_data.picture_urls
            }
        
        await ctx.report_progress(0.5, "Submitting revisions to eBay...")
        
        # Execute ReviseItem call
        response = await client.execute_with_retry(
            "trading",
            "ReviseItem",
            revision_data,
            use_cache=False
        )
        
        await ctx.report_progress(0.9, "Processing response...")
        
        # Extract revision details
        revised_fields = []
        if input_data.title:
            revised_fields.append("title")
        if input_data.description:
            revised_fields.append("description")
        if input_data.price:
            revised_fields.append("price")
        if input_data.quantity is not None:
            revised_fields.append("quantity")
        if input_data.shipping_cost is not None:
            revised_fields.append("shipping_cost")
        if input_data.picture_urls:
            revised_fields.append("pictures")
        
        await ctx.report_progress(1.0, "Listing revised successfully")
        await ctx.info(f"Successfully revised {len(revised_fields)} fields")
        
        return success_response(
            data={
                "item_id": input_data.item_id,
                "revised_fields": revised_fields,
                "revision_time": datetime.now().isoformat(),
                "listing_url": f"https://www.{mcp.config.domain}/itm/{input_data.item_id}"
            },
            message=f"Successfully revised listing {item_id}"
        ).to_json_string()
        
    except ValueError as e:
        await ctx.error(f"Invalid revision parameters: {str(e)}")
        return error_response(
            ErrorCode.VALIDATION_ERROR,
            str(e)
        ).to_json_string()
    except Exception as e:
        await ctx.error(f"Failed to revise listing: {str(e)}")
        return error_response(
            ErrorCode.INTERNAL_ERROR,
            f"Failed to revise listing: {str(e)}"
        ).to_json_string()


@mcp.tool
async def end_listing(
    item_id: str,
    reason: str = "NotAvailable",
    *,
    ctx: Context
) -> str:
    """
    End an active eBay listing.
    
    This tool ends an active listing before its scheduled end time.
    
    Args:
        item_id: The eBay item ID to end
        reason: Reason for ending (NotAvailable, LostOrBroken, Incorrect, OtherListingError)
        ctx: MCP context for logging
    
    Returns:
        JSON response confirming the listing was ended
    """
    # Import mcp at function level
    from lootly_server import mcp
    
    await ctx.info(f"Ending eBay listing: {item_id}")
    
    # Check if credentials are available
    if not mcp.config.app_id or not mcp.config.cert_id or not mcp.config.dev_id:
        return success_response(
            data={
                "item_id": item_id,
                "end_time": None,
                "reason": reason,
                "note": "eBay API credentials not configured. To end listings, please set EBAY_APP_ID, EBAY_CERT_ID, and EBAY_DEV_ID environment variables."
            },
            message="eBay API credentials not available - see note for setup instructions"
        ).to_json_string()
    
    # Create client after credential check
    client = EbayApiClient(mcp.config, mcp.logger)
    
    try:
        # Validate reason
        valid_reasons = ["NotAvailable", "LostOrBroken", "Incorrect", "OtherListingError"]
        if reason not in valid_reasons:
            return error_response(
                ErrorCode.VALIDATION_ERROR,
                f"Invalid reason. Must be one of: {', '.join(valid_reasons)}"
            ).to_json_string()
        
        # Build EndItem request
        end_data = {
            "ItemID": item_id,
            "EndingReason": reason
        }
        
        await ctx.report_progress(0.5, "Ending listing...")
        
        # Execute EndItem call
        response = await client.execute_with_retry(
            "trading",
            "EndItem",
            end_data,
            use_cache=False
        )
        
        end_time = response.get("EndTime", [datetime.now().isoformat()])[0]
        
        await ctx.info(f"Successfully ended listing {item_id}")
        
        return success_response(
            data={
                "item_id": item_id,
                "end_time": end_time,
                "reason": reason
            },
            message=f"Successfully ended listing {item_id}"
        ).to_json_string()
        
    except Exception as e:
        await ctx.error(f"Failed to end listing: {str(e)}")
        return error_response(
            ErrorCode.INTERNAL_ERROR,
            f"Failed to end listing: {str(e)}"
        ).to_json_string()


@mcp.tool
async def get_my_ebay_selling(
    listing_type: str = "Active",
    page_number: int = 1,
    page_size: int = 50,
    *,
    ctx: Context
) -> str:
    """
    Get seller's eBay listings (active, sold, unsold).
    
    This tool retrieves the authenticated seller's listings with detailed information
    about each item including current price, watchers, and time left.
    
    Args:
        listing_type: Type of listings to retrieve (Active, Sold, Unsold)
        page_number: Page number for pagination
        page_size: Number of items per page (max 200)
        ctx: MCP context for logging
    
    Returns:
        JSON response with seller's listings and summary statistics
    """
    # Import mcp at function level
    from lootly_server import mcp
    
    await ctx.info(f"Getting seller's {listing_type} listings")
    await ctx.report_progress(0.1, "Validating parameters...")
    
    # Check if credentials are available
    if not mcp.config.app_id or not mcp.config.cert_id or not mcp.config.dev_id:
        return success_response(
            data={
                "listings": [],
                "summary": {
                    "total_listings": 0,
                    "total_value": 0,
                    "listing_type": listing_type
                },
                "pagination": {
                    "page": page_number,
                    "page_size": 0,
                    "total_pages": 0,
                    "total_items": 0,
                    "has_next": False
                },
                "note": "eBay API credentials not configured. To get your eBay listings, please set EBAY_APP_ID, EBAY_CERT_ID, and EBAY_DEV_ID environment variables."
            },
            message="eBay API credentials not available - see note for setup instructions"
        ).to_json_string()
    
    # Create client after credential check
    client = EbayApiClient(mcp.config, mcp.logger)
    
    try:
        # Validate listing type
        valid_types = ["Active", "Sold", "Unsold", "Scheduled"]
        if listing_type not in valid_types:
            return error_response(
                ErrorCode.VALIDATION_ERROR,
                f"Invalid listing type. Must be one of: {', '.join(valid_types)}"
            ).to_json_string()
        
        # Validate pagination
        client.validate_pagination(page_number)
        page_size = min(page_size, 200)  # eBay max is 200 for GetMyeBaySelling
        
        await ctx.report_progress(0.3, f"Fetching {listing_type} listings...")
        
        # Build request
        request_data = {
            f"{listing_type}List": {
                "Include": True,
                "Pagination": {
                    "EntriesPerPage": page_size,
                    "PageNumber": page_number
                }
            },
            "DetailLevel": "ReturnAll"
        }
        
        # Execute GetMyeBaySelling call
        response = await client.execute_with_retry(
            "trading",
            "GetMyeBaySelling",
            request_data
        )
        
        await ctx.report_progress(0.7, "Processing listings...")
        
        # Extract listings based on type
        list_key = f"{listing_type}List"
        listing_data = response.get(list_key, {})
        items = listing_data.get("ItemArray", {}).get("Item", [])
        
        # Ensure items is a list
        if not isinstance(items, list):
            items = [items] if items else []
        
        # Format items
        formatted_items = []
        total_value = 0
        
        for item in items:
            selling_status = item.get("SellingStatus", {})
            current_price = float(selling_status.get("CurrentPrice", {}).get("value", 0))
            quantity_sold = int(selling_status.get("QuantitySold", 0))
            
            formatted_item = {
                "item_id": item.get("ItemID"),
                "title": item.get("Title"),
                "current_price": current_price,
                "quantity": {
                    "available": int(item.get("Quantity", 0)) - quantity_sold,
                    "sold": quantity_sold,
                    "total": int(item.get("Quantity", 0))
                },
                "listing_type": item.get("ListingType"),
                "time_left": item.get("TimeLeft"),
                "watchers": int(item.get("WatchCount", 0)),
                "views": int(item.get("HitCount", 0)),
                "listing_url": item.get("ListingDetails", {}).get("ViewItemURL"),
                "start_time": item.get("ListingDetails", {}).get("StartTime"),
                "end_time": item.get("ListingDetails", {}).get("EndTime")
            }
            
            # Add sold-specific data
            if listing_type == "Sold":
                formatted_item["sold_price"] = current_price
                formatted_item["buyer_id"] = selling_status.get("HighBidder", {}).get("UserID")
                total_value += current_price * quantity_sold
            else:
                total_value += current_price * formatted_item["quantity"]["available"]
            
            formatted_items.append(formatted_item)
        
        # Get pagination info
        pagination_result = listing_data.get("PaginationResult", {})
        total_pages = int(pagination_result.get("TotalNumberOfPages", 1))
        total_entries = int(pagination_result.get("TotalNumberOfEntries", 0))
        
        await ctx.report_progress(1.0, "Complete")
        await ctx.info(f"Found {len(formatted_items)} {listing_type.lower()} listings")
        
        return success_response(
            data={
                "listings": formatted_items,
                "summary": {
                    "total_listings": total_entries,
                    "total_value": round(total_value, 2),
                    "listing_type": listing_type
                },
                "pagination": {
                    "page": page_number,
                    "page_size": len(formatted_items),
                    "total_pages": total_pages,
                    "total_items": total_entries,
                    "has_next": page_number < total_pages
                }
            },
            message=f"Retrieved {len(formatted_items)} {listing_type.lower()} listings"
        ).to_json_string()
        
    except Exception as e:
        await ctx.error(f"Failed to get seller listings: {str(e)}")
        return error_response(
            ErrorCode.INTERNAL_ERROR,
            f"Failed to get seller listings: {str(e)}"
        ).to_json_string()


@mcp.tool
async def get_user_info(
    user_id: Optional[str] = None,
    *,
    ctx: Context
) -> str:
    """
    Get user account information.
    
    This tool retrieves detailed information about an eBay user account including
    feedback score, registration date, and seller status. If no user_id is provided,
    it returns information about the authenticated user.
    
    Args:
        user_id: eBay user ID to look up (optional, defaults to authenticated user)
        ctx: MCP context for logging
    
    Returns:
        JSON response with user account details and statistics
    """
    # Import mcp at function level
    from lootly_server import mcp
    
    user_desc = f"user {user_id}" if user_id else "authenticated user"
    await ctx.info(f"Getting information for {user_desc}")
    
    # Check if credentials are available
    if not mcp.config.app_id or not mcp.config.cert_id or not mcp.config.dev_id:
        return success_response(
            data={
                "user_id": user_id,
                "email": None,
                "registration_date": None,
                "status": "Unknown",
                "feedback": {},
                "seller_info": {},
                "business_info": {},
                "note": "eBay API credentials not configured. To get user information, please set EBAY_APP_ID, EBAY_CERT_ID, and EBAY_DEV_ID environment variables."
            },
            message="eBay API credentials not available - see note for setup instructions"
        ).to_json_string()
    
    # Create client after credential check
    client = EbayApiClient(mcp.config, mcp.logger)
    
    try:
        # Build request
        request_data = {}
        if user_id:
            request_data["UserID"] = user_id
        request_data["DetailLevel"] = "ReturnAll"
        
        await ctx.report_progress(0.5, "Fetching user data...")
        
        # Execute GetUser call
        response = await client.execute_with_retry(
            "trading",
            "GetUser",
            request_data
        )
        
        # Extract user data
        user = response.get("User", {})
        
        # Format user information
        user_info = {
            "user_id": user.get("UserID"),
            "email": user.get("Email"),
            "registration_date": user.get("RegistrationDate"),
            "status": user.get("Status"),
            "site": user.get("Site"),
            "feedback": {
                "score": int(user.get("FeedbackScore", 0)),
                "positive_percentage": float(user.get("PositiveFeedbackPercent", 0)),
                "star_color": user.get("FeedbackRatingStar"),
                "unique_positive": int(user.get("UniquePositiveFeedbackCount", 0)),
                "unique_negative": int(user.get("UniqueNegativeFeedbackCount", 0))
            },
            "seller_info": {
                "is_seller": user.get("SellerInfo", {}).get("CheckoutEnabled", False),
                "store_owner": user.get("SellerInfo", {}).get("StoreOwner", False),
                "store_url": user.get("SellerInfo", {}).get("StoreURL"),
                "seller_level": user.get("SellerInfo", {}).get("SellerLevel"),
                "top_rated_seller": user.get("SellerInfo", {}).get("TopRatedSeller", False)
            },
            "verified": {
                "email": user.get("UserIDVerified", False),
                "paypal": user.get("PayPalAccountStatus") == "Verified"
            }
        }
        
        await ctx.info(f"Successfully retrieved user information")
        
        return success_response(
            data=user_info,
            message=f"Successfully retrieved information for {user_desc}"
        ).to_json_string()
        
    except Exception as e:
        await ctx.error(f"Failed to get user info: {str(e)}")
        return error_response(
            ErrorCode.INTERNAL_ERROR,
            f"Failed to get user information: {str(e)}"
        ).to_json_string()