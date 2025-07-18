"""
eBay Fulfillment Policy API tools for managing seller shipping and delivery policies.

This module provides MCP tools for creating, updating, retrieving, and deleting
fulfillment policies in eBay seller accounts. Fulfillment policies define shipping
options, handling times, and delivery terms for listings.

IMPLEMENTATION FOLLOWS: PYDANTIC-FIRST DEVELOPMENT METHODOLOGY
- All API fields included exactly as documented
- Strong typing with enums throughout
- Validation through Pydantic models only
- Zero manual validation code

API Documentation: https://developer.ebay.com/api-docs/sell/account/resources/methods#h2-fulfillment_policy
OAuth Scope Required: https://api.ebay.com/oauth/api_scope/sell.account
"""
from typing import Optional, Dict, Any, List
from fastmcp import Context
from pydantic import BaseModel, Field, model_validator, ConfigDict

from api.oauth import OAuthManager, OAuthConfig, ConsentRequiredException
from api.rest_client import EbayRestClient, RestConfig
from api.errors import EbayApiError, extract_ebay_error_details
from api.ebay_enums import (
    MarketplaceIdEnum,
    CategoryTypeEnum,
    ShippingCostTypeEnum,
    ShippingOptionTypeEnum,
    TimeDurationUnitEnum,
    CurrencyCodeEnum,
    RegionTypeEnum
)
from data_types import success_response, error_response, ErrorCode
from lootly_server import mcp


# PYDANTIC MODELS - API Documentation → Pydantic Models → MCP Tools


class CategoryType(BaseModel):
    """Category type for a business policy."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    name: CategoryTypeEnum = Field(..., description="Category type name")
    default: Optional[bool] = Field(None, description="Deprecated - no longer used")


class TimeDuration(BaseModel):
    """Time duration for handling time."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    value: int = Field(..., gt=0, le=30, description="Number of time units (max 30 days)")
    unit: TimeDurationUnitEnum = Field(..., description="Time unit")


class Amount(BaseModel):
    """
    Monetary amount with currency.
    Used for all monetary values in the API (shipping costs, handling fees, etc).
    """
    model_config = ConfigDict(str_strip_whitespace=True)
    
    currency: CurrencyCodeEnum = Field(..., description="3-letter ISO 4217 currency code")
    value: str = Field(..., description="Monetary amount as decimal string")


class Region(BaseModel):
    """
    Geographic region for shipping locations.
    Can represent world regions, countries, states/provinces, or special domestic regions.
    """
    model_config = ConfigDict(str_strip_whitespace=True)
    
    region_name: str = Field(..., description="Name of region as defined by eBay (e.g., 'US', 'Asia', 'CA')")
    region_type: Optional[RegionTypeEnum] = Field(None, description="Type of region (reserved for future use)")


class RegionSet(BaseModel):
    """Shipping regions configuration for included and excluded locations."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    region_included: Optional[List[Region]] = Field(None, description="List of regions where shipping is offered")
    region_excluded: Optional[List[Region]] = Field(None, description="List of regions excluded from shipping")


class ShippingService(BaseModel):
    """Individual shipping service configuration."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    # REQUIRED FIELDS
    shipping_service_code: str = Field(..., description="eBay shipping service code")
    
    # OPTIONAL FIELDS
    shipping_carrier_code: Optional[str] = Field(None, description="Shipping carrier code (e.g., USPS, FedEx)")
    shipping_cost: Optional[Amount] = Field(None, description="Base shipping cost for first item")
    additional_shipping_cost: Optional[Amount] = Field(None, description="Additional item shipping cost")
    free_shipping: Optional[bool] = Field(None, description="Whether this service offers free shipping")
    ship_to_locations: Optional[RegionSet] = Field(None, description="Regions this service ships to")
    sort_order: Optional[int] = Field(None, ge=1, le=5, description="Display order (1-4 domestic, 1-5 international)")
    buyer_responsible_for_shipping: Optional[bool] = Field(False, description="Buyer pays shipping (motors only)")
    buyer_responsible_for_pickup: Optional[bool] = Field(False, description="Buyer arranges pickup (motors only)")


class ShippingOption(BaseModel):
    """Shipping option configuration for domestic or international shipping."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    # REQUIRED FIELDS
    cost_type: ShippingCostTypeEnum = Field(..., description="How shipping costs are calculated (FLAT_RATE or CALCULATED)")
    option_type: ShippingOptionTypeEnum = Field(..., description="Domestic or international shipping")
    
    # OPTIONAL FIELDS
    shipping_services: Optional[List[ShippingService]] = Field(None, description="Available shipping services")
    package_handling_cost: Optional[Amount] = Field(None, description="Handling charges for shipments")
    rate_table_id: Optional[str] = Field(None, description="ID of shipping rate table to use")
    shipping_discount_profile_id: Optional[str] = Field(None, description="ID of shipping discount profile")
    shipping_promotion_offered: Optional[bool] = Field(None, description="Whether promotional shipping discount is offered")
    
    @model_validator(mode='after')
    def validate_service_limits(self):
        """Validate shipping service limits."""
        if self.shipping_services:
            max_services = 4 if self.option_type == ShippingOptionTypeEnum.DOMESTIC else 5
            if len(self.shipping_services) > max_services:
                service_type = "domestic" if self.option_type == ShippingOptionTypeEnum.DOMESTIC else "international"
                raise ValueError(f"Maximum {max_services} {service_type} shipping services allowed")
        return self


class FulfillmentPolicyInput(BaseModel):
    """
    Complete input validation for fulfillment policy operations.
    
    Maps ALL fields from eBay API createFulfillmentPolicy Request Fields exactly.
    Documentation: https://developer.ebay.com/api-docs/sell/account/resources/fulfillment_policy/methods/createFulfillmentPolicy
    """
    model_config = ConfigDict(str_strip_whitespace=True)
    
    # REQUIRED FIELDS
    name: str = Field(..., min_length=1, max_length=64, description="Policy name")
    marketplace_id: MarketplaceIdEnum = Field(..., description="eBay marketplace ID")
    category_types: List[CategoryType] = Field(..., description="Category types this policy applies to")
    
    # CONDITIONAL FIELDS (required when offering shipping services)
    handling_time: Optional[TimeDuration] = Field(None, description="Time to ship after payment")
    
    # OPTIONAL FIELDS
    description: Optional[str] = Field(None, max_length=250, description="Internal policy description")
    shipping_options: Optional[List[ShippingOption]] = Field(None, description="Shipping service options")
    ship_to_locations: Optional[RegionSet] = Field(None, description="Global shipping locations for this policy")
    local_pickup: Optional[bool] = Field(False, description="Whether local pickup is offered")
    pickup_drop_off: Optional[bool] = Field(False, description="Whether pickup/drop-off is available")
    freight_shipping: Optional[bool] = Field(False, description="Whether freight shipping is offered")
    global_shipping: Optional[bool] = Field(False, description="Whether Global Shipping Program is used")
    
    @model_validator(mode='after')
    def validate_conditional_fields(self):
        """Validate conditional requirements for fulfillment policies."""
        # If shipping options are provided, handling time is required
        if self.shipping_options and any(opt.shipping_services for opt in self.shipping_options):
            if not self.handling_time:
                raise ValueError("handling_time is required when shipping services are defined")
        
        # Validate shipping option limits
        if self.shipping_options:
            domestic_count = sum(1 for opt in self.shipping_options if opt.option_type == ShippingOptionTypeEnum.DOMESTIC)
            international_count = sum(1 for opt in self.shipping_options if opt.option_type == ShippingOptionTypeEnum.INTERNATIONAL)
            
            if domestic_count > 1:
                raise ValueError("Only one domestic shipping option allowed per policy")
            if international_count > 1:
                raise ValueError("Only one international shipping option allowed per policy")
        
        return self


class FulfillmentPolicyResponse(FulfillmentPolicyInput):
    """
    Response model for fulfillment policy operations.
    
    Extends FulfillmentPolicyInput with response-only fields from eBay API.
    This ensures type safety and structure validation for all API responses.
    """
    fulfillment_policy_id: str = Field(..., description="eBay-assigned unique policy ID")
    warnings: Optional[List[Dict[str, Any]]] = Field(None, description="Optional warnings from eBay API")
    
    # Note: created_at and updated_at are not documented in the API response
    # but are included in _format_policy_response, so we'll keep them optional
    created_at: Optional[str] = Field(None, description="Policy creation timestamp")
    updated_at: Optional[str] = Field(None, description="Policy last update timestamp")


# HELPER FUNCTIONS - Convert between Pydantic models and eBay API format


def _build_policy_data(input_data: FulfillmentPolicyInput) -> Dict[str, Any]:
    """
    Convert Pydantic model to eBay API request format.
    
    This follows the exact field mapping from eBay's createFulfillmentPolicy API.
    """
    policy_data = {
        "name": input_data.name,
        "marketplaceId": input_data.marketplace_id.value,
        "categoryTypes": [
            {
                "name": cat.name.value,
                **({"default": cat.default} if cat.default is not None else {})
            }
            for cat in input_data.category_types
        ]
    }
    
    # Add optional description
    if input_data.description:
        policy_data["description"] = input_data.description
    
    # Add handling time if provided
    if input_data.handling_time:
        policy_data["handlingTime"] = {
            "value": input_data.handling_time.value,
            "unit": input_data.handling_time.unit.value
        }
    
    # Add shipping options
    if input_data.shipping_options:
        policy_data["shippingOptions"] = []
        for option in input_data.shipping_options:
            option_data = {
                "costType": option.cost_type.value,
                "optionType": option.option_type.value
            }
            
            if option.package_handling_cost:
                option_data["packageHandlingCost"] = {
                    "currency": option.package_handling_cost.currency.value,
                    "value": option.package_handling_cost.value
                }
            
            if option.rate_table_id:
                option_data["rateTableId"] = option.rate_table_id
            
            if option.shipping_discount_profile_id:
                option_data["shippingDiscountProfileId"] = option.shipping_discount_profile_id
            
            if option.shipping_promotion_offered is not None:
                option_data["shippingPromotionOffered"] = option.shipping_promotion_offered
            
            if option.shipping_services:
                option_data["shippingServices"] = []
                for service in option.shipping_services:
                    service_data = {
                        "shippingServiceCode": service.shipping_service_code
                    }
                    
                    if service.shipping_carrier_code:
                        service_data["shippingCarrierCode"] = service.shipping_carrier_code
                    
                    if service.shipping_cost:
                        service_data["shippingCost"] = {
                            "currency": service.shipping_cost.currency.value,
                            "value": service.shipping_cost.value
                        }
                    
                    if service.additional_shipping_cost:
                        service_data["additionalShippingCost"] = {
                            "currency": service.additional_shipping_cost.currency.value,
                            "value": service.additional_shipping_cost.value
                        }
                    
                    if service.free_shipping is not None:
                        service_data["freeShipping"] = service.free_shipping
                    
                    if service.ship_to_locations:
                        locations_data = {}
                        if service.ship_to_locations.region_included:
                            locations_data["regionIncluded"] = [
                                {"regionName": r.region_name, **({"regionType": r.region_type.value} if r.region_type else {})}
                                for r in service.ship_to_locations.region_included
                            ]
                        if service.ship_to_locations.region_excluded:
                            locations_data["regionExcluded"] = [
                                {"regionName": r.region_name, **({"regionType": r.region_type.value} if r.region_type else {})}
                                for r in service.ship_to_locations.region_excluded
                            ]
                        if locations_data:
                            service_data["shipToLocations"] = locations_data
                    
                    if service.sort_order is not None:
                        service_data["sortOrder"] = service.sort_order
                    
                    if service.buyer_responsible_for_shipping is not None:
                        service_data["buyerResponsibleForShipping"] = service.buyer_responsible_for_shipping
                    
                    if service.buyer_responsible_for_pickup is not None:
                        service_data["buyerResponsibleForPickup"] = service.buyer_responsible_for_pickup
                    
                    option_data["shippingServices"].append(service_data)
            
            policy_data["shippingOptions"].append(option_data)
    
    # Add ship to locations at policy level
    if input_data.ship_to_locations:
        ship_to_data = {}
        if input_data.ship_to_locations.region_included:
            ship_to_data["regionIncluded"] = [
                {"regionName": r.region_name, **({"regionType": r.region_type.value} if r.region_type else {})}
                for r in input_data.ship_to_locations.region_included
            ]
        if input_data.ship_to_locations.region_excluded:
            ship_to_data["regionExcluded"] = [
                {"regionName": r.region_name, **({"regionType": r.region_type.value} if r.region_type else {})}
                for r in input_data.ship_to_locations.region_excluded
            ]
        if ship_to_data:
            policy_data["shipToLocations"] = ship_to_data
    
    # Add boolean flags
    if input_data.local_pickup is not None:
        policy_data["localPickup"] = input_data.local_pickup
    
    if input_data.pickup_drop_off is not None:
        policy_data["pickupDropOff"] = input_data.pickup_drop_off
    
    if input_data.freight_shipping is not None:
        policy_data["freightShipping"] = input_data.freight_shipping
    
    if input_data.global_shipping is not None:
        policy_data["globalShipping"] = input_data.global_shipping
    
    return policy_data


def _api_response_to_pydantic(api_response: Dict[str, Any]) -> FulfillmentPolicyResponse:
    """
    Convert eBay API response to Pydantic FulfillmentPolicyResponse model.
    
    This ensures type safety and validates the response structure.
    """
    # Map API response fields to our Pydantic model fields
    response_data = {
        # Required fields from FulfillmentPolicyInput
        "name": api_response.get("name"),
        "marketplace_id": api_response.get("marketplaceId"),
        "fulfillment_policy_id": api_response.get("fulfillmentPolicyId"),
        
        # Category types - convert from API format
        "category_types": [
            CategoryType(
                name=CategoryTypeEnum(ct["name"]), 
                default=ct.get("default")
            )
            for ct in api_response.get("categoryTypes", [])
        ],
        
        # Optional fields
        "description": api_response.get("description"),
        "local_pickup": api_response.get("localPickup", False),
        "pickup_drop_off": api_response.get("pickupDropOff", False),
        "freight_shipping": api_response.get("freightShipping", False),
        "global_shipping": api_response.get("globalShipping", False),
        
        # Timestamps
        "created_at": api_response.get("createdAt"),
        "updated_at": api_response.get("updatedAt"),
        
        # Warnings
        "warnings": api_response.get("warnings")
    }
    
    # Handle handling time
    if api_response.get("handlingTime"):
        ht = api_response["handlingTime"]
        response_data["handling_time"] = TimeDuration(
            value=ht["value"],
            unit=TimeDurationUnitEnum(ht["unit"])
        )
    
    # Handle shipping options
    if api_response.get("shippingOptions"):
        response_data["shipping_options"] = []
        for opt in api_response["shippingOptions"]:
            shipping_option = {
                "cost_type": ShippingCostTypeEnum(opt["costType"]),
                "option_type": ShippingOptionTypeEnum(opt["optionType"])
            }
            
            # Package handling cost
            if opt.get("packageHandlingCost"):
                phc = opt["packageHandlingCost"]
                shipping_option["package_handling_cost"] = Amount(
                    currency=CurrencyCodeEnum(phc["currency"]),
                    value=phc["value"]
                )
            
            # Shipping services
            if opt.get("shippingServices"):
                shipping_option["shipping_services"] = []
                for svc in opt["shippingServices"]:
                    service = {
                        "shipping_service_code": svc["shippingServiceCode"]
                    }
                    
                    if svc.get("shippingCarrierCode"):
                        service["shipping_carrier_code"] = svc["shippingCarrierCode"]
                    
                    if svc.get("shippingCost"):
                        sc = svc["shippingCost"]
                        service["shipping_cost"] = Amount(
                            currency=CurrencyCodeEnum(sc["currency"]),
                            value=sc["value"]
                        )
                    
                    if svc.get("additionalShippingCost"):
                        asc = svc["additionalShippingCost"]
                        service["additional_shipping_cost"] = Amount(
                            currency=CurrencyCodeEnum(asc["currency"]),
                            value=asc["value"]
                        )
                    
                    if svc.get("freeShipping") is not None:
                        service["free_shipping"] = svc["freeShipping"]
                    
                    if svc.get("sortOrder") is not None:
                        service["sort_order"] = svc["sortOrder"]
                    
                    shipping_option["shipping_services"].append(ShippingService(**service))
            
            response_data["shipping_options"].append(ShippingOption(**shipping_option))
    
    # Handle ship to locations
    if api_response.get("shipToLocations"):
        stl = api_response["shipToLocations"]
        response_data["ship_to_locations"] = RegionSet(
            region_included=[Region(region_name=r["regionName"], region_type=r.get("regionType")) 
                           for r in stl.get("regionIncluded", [])] if stl.get("regionIncluded") else None,
            region_excluded=[Region(region_name=r["regionName"], region_type=r.get("regionType")) 
                           for r in stl.get("regionExcluded", [])] if stl.get("regionExcluded") else None
        )
    
    return FulfillmentPolicyResponse(**response_data)


# MCP TOOLS - Using Pydantic Models


@mcp.tool
async def create_fulfillment_policy(
    ctx: Context,
    policy_input: FulfillmentPolicyInput
) -> str:
    """
    Create a new fulfillment policy for your eBay seller account.
    
    Fulfillment policies define shipping options, handling times, and delivery terms
    for your listings. You can create multiple policies for different shipping scenarios.
    
    Key features:
    - Configure domestic and international shipping services
    - Set handling time for order processing
    - Enable local pickup, freight shipping, Global Shipping Program
    - Support up to 4 domestic and 5 international shipping services
    
    Args:
        policy_input: Complete fulfillment policy configuration with all required fields
        ctx: MCP context
    
    Returns:
        JSON response with created policy details including policy_id
    
    OAuth Scope Required: https://api.ebay.com/oauth/api_scope/sell.account
    """
    await ctx.info(f"Creating fulfillment policy: {policy_input.name}")
    await ctx.report_progress(0.1, "Validating input parameters...")
    
    # Pydantic validation already handled - no manual validation needed!
    
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
        policy_data = _build_policy_data(policy_input)
        
        await ctx.report_progress(0.5, "Creating fulfillment policy via eBay API...")
        
        # Make API call with headers - OAuth scope validation automatic
        response = await rest_client.post(
            "/sell/account/v1/fulfillment_policy",
            json=policy_data
        )
        
        await ctx.report_progress(0.8, "Processing response...")
        
        # Extract response body and headers
        response_body = response["body"]
        response_headers = response["headers"]
        
        # Convert API response to Pydantic model
        policy_response = _api_response_to_pydantic(response_body)
        
        # Extract Location header and other metadata
        metadata = {
            "location_url": response_headers.get("Location"),
            "request_id": response_headers.get("X-EBAY-C-REQUEST-ID")
        }
        
        await ctx.report_progress(1.0, "Fulfillment policy created successfully")
        await ctx.success(f"Created fulfillment policy '{policy_input.name}' with ID: {policy_response.fulfillment_policy_id}")
        
        return success_response(
            data=policy_response.model_dump(exclude_none=True),
            message=f"Fulfillment policy '{policy_input.name}' created successfully",
            metadata=metadata
        ).to_json_string()
        
    except ConsentRequiredException as e:
        await ctx.warning("User consent required for sell.account scope")
        return error_response(
            ErrorCode.AUTHENTICATION_ERROR,
            "User consent required for sell.account scope",
            {"consent_url": str(e), "scope_required": "sell.account"}
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
            "An unexpected error occurred while creating the fulfillment policy",
            {"error": str(e)}
        ).to_json_string()
        
    finally:
        await rest_client.close()


@mcp.tool
async def get_fulfillment_policies(
    ctx: Context,
    marketplace_id: MarketplaceIdEnum,
    limit: Optional[int] = 50,
    offset: Optional[int] = 0
) -> str:
    """
    Retrieve all fulfillment policies for a specific marketplace.
    
    Returns a paginated list of all fulfillment policies configured for the
    specified eBay marketplace. Use this to review existing shipping configurations.
    
    Args:
        marketplace_id: eBay marketplace to retrieve policies for
        limit: Maximum number of policies to return (default: 50)
        offset: Number of policies to skip for pagination (default: 0)
        ctx: MCP context
    
    Returns:
        JSON response with list of fulfillment policies and pagination info
    
    OAuth Scope Required: https://api.ebay.com/oauth/api_scope/sell.account
    """
    await ctx.info(f"Retrieving fulfillment policies for marketplace: {marketplace_id.value}")
    await ctx.report_progress(0.1, "Validating parameters...")
    
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
        await ctx.report_progress(0.5, "Fetching fulfillment policies...")
        
        # Build query parameters
        params = {
            "marketplace_id": marketplace_id.value
        }
        if limit is not None:
            params["limit"] = str(limit)
        if offset is not None:
            params["offset"] = str(offset)
        
        # Make API call
        response = await rest_client.get(
            "/sell/account/v1/fulfillment_policy",
            params=params
        )
        response_body = response["body"]
        
        await ctx.report_progress(0.8, "Processing response...")
        
        # Format policies
        policies = response_body.get("fulfillmentPolicies", [])
        formatted_policies = [_format_policy_response(policy) for policy in policies]
        
        # Build response with pagination
        result = {
            "policies": formatted_policies,
            "total": response_body.get("total", len(formatted_policies)),
            "limit": limit,
            "offset": offset,
            "marketplace_id": marketplace_id.value
        }
        
        # Add pagination links if available
        if response_body.get("href"):
            result["href"] = response_body["href"]
        if response.get("next"):
            result["next"] = response["next"]
        if response.get("prev"):
            result["prev"] = response["prev"]
        
        await ctx.report_progress(1.0, f"Retrieved {len(formatted_policies)} fulfillment policies")
        await ctx.success(f"Found {len(formatted_policies)} fulfillment policies for {marketplace_id.value}")
        
        return success_response(
            data=result,
            message=f"Retrieved {len(formatted_policies)} fulfillment policies"
        ).to_json_string()
        
    except ConsentRequiredException as e:
        await ctx.warning("User consent required for sell.account scope")
        return error_response(
            ErrorCode.AUTHENTICATION_ERROR,
            "User consent required for sell.account scope",
            {"consent_url": str(e), "scope_required": "sell.account"}
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
            "An unexpected error occurred while retrieving fulfillment policies",
            {"error": str(e)}
        ).to_json_string()
        
    finally:
        await rest_client.close()


@mcp.tool
async def get_fulfillment_policy(
    ctx: Context,
    policy_id: str
) -> str:
    """
    Retrieve a specific fulfillment policy by its ID.
    
    Returns detailed information about a single fulfillment policy including
    all shipping options, handling time, and service configurations.
    
    Args:
        policy_id: eBay fulfillment policy ID
        ctx: MCP context
    
    Returns:
        JSON response with complete fulfillment policy details
    
    OAuth Scope Required: https://api.ebay.com/oauth/api_scope/sell.account
    """
    await ctx.info(f"Retrieving fulfillment policy: {policy_id}")
    await ctx.report_progress(0.1, "Validating parameters...")
    
    if not policy_id or not policy_id.strip():
        return error_response(
            ErrorCode.VALIDATION_ERROR,
            "policy_id is required and cannot be empty"
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
        await ctx.report_progress(0.5, f"Fetching fulfillment policy {policy_id}...")
        
        # Make API call
        response = await rest_client.get(f"/sell/account/v1/fulfillment_policy/{policy_id}")
        response_body = response["body"]
        
        await ctx.report_progress(0.8, "Processing response...")
        
        # Format response
        formatted_response = _format_policy_response(response_body)
        
        await ctx.report_progress(1.0, "Fulfillment policy retrieved successfully")
        await ctx.success(f"Retrieved fulfillment policy '{formatted_response.get('name')}'")
        
        return success_response(
            data=formatted_response,
            message=f"Fulfillment policy retrieved successfully"
        ).to_json_string()
        
    except ConsentRequiredException as e:
        await ctx.warning("User consent required for sell.account scope")
        return error_response(
            ErrorCode.AUTHENTICATION_ERROR,
            "User consent required for sell.account scope",
            {"consent_url": str(e), "scope_required": "sell.account"}
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
            "An unexpected error occurred while retrieving the fulfillment policy",
            {"error": str(e)}
        ).to_json_string()
        
    finally:
        await rest_client.close()


@mcp.tool
async def get_fulfillment_policy_by_name(
    ctx: Context,
    marketplace_id: MarketplaceIdEnum,
    name: str
) -> str:
    """
    Retrieve a specific fulfillment policy by its name and marketplace.
    
    Looks up a fulfillment policy using its seller-defined name within
    a specific marketplace. Policy names must be unique per marketplace.
    
    Args:
        marketplace_id: eBay marketplace where the policy exists
        name: Seller-defined name of the fulfillment policy
        ctx: MCP context
    
    Returns:
        JSON response with complete fulfillment policy details
    
    OAuth Scope Required: https://api.ebay.com/oauth/api_scope/sell.account
    """
    await ctx.info(f"Retrieving fulfillment policy '{name}' for marketplace: {marketplace_id.value}")
    await ctx.report_progress(0.1, "Validating parameters...")
    
    if not name or not name.strip():
        return error_response(
            ErrorCode.VALIDATION_ERROR,
            "name is required and cannot be empty"
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
        await ctx.report_progress(0.5, f"Searching for fulfillment policy '{name}'...")
        
        # Build query parameters
        params = {
            "marketplace_id": marketplace_id.value,
            "name": name
        }
        
        # Make API call
        response = await rest_client.get(
            "/sell/account/v1/fulfillment_policy/get_by_policy_name",
            params=params
        )
        response_body = response["body"]
        
        await ctx.report_progress(0.8, "Processing response...")
        
        # Format response
        formatted_response = _format_policy_response(response_body)
        
        await ctx.report_progress(1.0, "Fulfillment policy retrieved successfully")
        await ctx.success(f"Found fulfillment policy '{name}' with ID: {formatted_response.get('policy_id')}")
        
        return success_response(
            data=formatted_response,
            message=f"Fulfillment policy '{name}' retrieved successfully"
        ).to_json_string()
        
    except ConsentRequiredException as e:
        await ctx.warning("User consent required for sell.account scope")
        return error_response(
            ErrorCode.AUTHENTICATION_ERROR,
            "User consent required for sell.account scope",
            {"consent_url": str(e), "scope_required": "sell.account"}
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
            "An unexpected error occurred while retrieving the fulfillment policy",
            {"error": str(e)}
        ).to_json_string()
        
    finally:
        await rest_client.close()


@mcp.tool
async def update_fulfillment_policy(
    ctx: Context,
    policy_id: str,
    policy_input: FulfillmentPolicyInput
) -> str:
    """
    Update an existing fulfillment policy.
    
    Modifies the configuration of an existing fulfillment policy. All fields
    will be replaced with the provided values - this is a complete replacement,
    not a partial update.
    
    Args:
        policy_id: eBay fulfillment policy ID to update
        policy_input: Complete updated fulfillment policy configuration
        ctx: MCP context
    
    Returns:
        JSON response with updated policy details
    
    OAuth Scope Required: https://api.ebay.com/oauth/api_scope/sell.account
    """
    await ctx.info(f"Updating fulfillment policy: {policy_id}")
    await ctx.report_progress(0.1, "Validating parameters...")
    
    if not policy_id or not policy_id.strip():
        return error_response(
            ErrorCode.VALIDATION_ERROR,
            "policy_id is required and cannot be empty"
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
        policy_data = _build_policy_data(policy_input)
        
        await ctx.report_progress(0.5, f"Updating fulfillment policy {policy_id}...")
        
        # Make API call
        response = await rest_client.put(
            f"/sell/account/v1/fulfillment_policy/{policy_id}",
            json=policy_data
        )
        response_body = response["body"]
        
        await ctx.report_progress(0.8, "Processing response...")
        
        # Format response
        formatted_response = _format_policy_response(response_body)
        
        await ctx.report_progress(1.0, "Fulfillment policy updated successfully")
        await ctx.success(f"Updated fulfillment policy '{policy_input.name}' (ID: {policy_id})")
        
        return success_response(
            data=formatted_response,
            message=f"Fulfillment policy '{policy_input.name}' updated successfully"
        ).to_json_string()
        
    except ConsentRequiredException as e:
        await ctx.warning("User consent required for sell.account scope")
        return error_response(
            ErrorCode.AUTHENTICATION_ERROR,
            "User consent required for sell.account scope",
            {"consent_url": str(e), "scope_required": "sell.account"}
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
            "An unexpected error occurred while updating the fulfillment policy",
            {"error": str(e)}
        ).to_json_string()
        
    finally:
        await rest_client.close()


@mcp.tool
async def delete_fulfillment_policy(
    ctx: Context,
    policy_id: str
) -> str:
    """
    Delete a fulfillment policy from your eBay seller account.
    
    Permanently removes a fulfillment policy. The policy cannot be deleted if
    it's currently being used by active listings or listing templates.
    
    Args:
        policy_id: eBay fulfillment policy ID to delete
        ctx: MCP context
    
    Returns:
        JSON response confirming deletion
    
    OAuth Scope Required: https://api.ebay.com/oauth/api_scope/sell.account
    """
    await ctx.info(f"Deleting fulfillment policy: {policy_id}")
    await ctx.report_progress(0.1, "Validating parameters...")
    
    if not policy_id or not policy_id.strip():
        return error_response(
            ErrorCode.VALIDATION_ERROR,
            "policy_id is required and cannot be empty"
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
        await ctx.report_progress(0.5, f"Deleting fulfillment policy {policy_id}...")
        
        # Make API call
        await rest_client.delete(f"/sell/account/v1/fulfillment_policy/{policy_id}")
        
        await ctx.report_progress(1.0, "Fulfillment policy deleted successfully")
        await ctx.success(f"Fulfillment policy {policy_id} deleted successfully")
        
        return success_response(
            data={"policy_id": policy_id, "deleted": True},
            message=f"Fulfillment policy {policy_id} deleted successfully"
        ).to_json_string()
        
    except ConsentRequiredException as e:
        await ctx.warning("User consent required for sell.account scope")
        return error_response(
            ErrorCode.AUTHENTICATION_ERROR,
            "User consent required for sell.account scope",
            {"consent_url": str(e), "scope_required": "sell.account"}
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
            "An unexpected error occurred while deleting the fulfillment policy",
            {"error": str(e)}
        ).to_json_string()
        
    finally:
        await rest_client.close()