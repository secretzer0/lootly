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
from typing import Optional, Dict, Any, Union
from fastmcp import Context

from api.oauth import OAuthManager, OAuthConfig, ConsentRequiredException
from api.rest_client import EbayRestClient, RestConfig
from api.errors import EbayApiError, extract_ebay_error_details
from models.enums import (
    MarketplaceIdEnum
)
from models.common import TimeDuration
from models.policies import FulfillmentPolicyInput
from data_types import success_response, error_response, ErrorCode
from lootly_server import mcp


# PYDANTIC MODELS - API Documentation → Pydantic Models → MCP Tools


# Using consolidated models from models.common
# These replace the local duplicate definitions:
# - Amount: Consolidated monetary amount model
# - CategoryType: Consolidated business policy category type  
# - TimeDuration: Base time duration (use .for_handling_time() for 30-day constraint)
# - Region: Geographic region model
# - RegionSet: Shipping regions configuration

# Create specialized TimeDuration for handling time (max 30 days)
HandlingTimeDuration = TimeDuration.for_handling_time()


# HELPER FUNCTIONS

def build_policy_data(policy_input: FulfillmentPolicyInput) -> Dict[str, Any]:
    """Convert Pydantic model to eBay API format."""
    policy_data = {
        "name": policy_input.name,
        "marketplaceId": policy_input.marketplaceId.value,
        "categoryTypes": [cat_type.model_dump(mode='json', exclude_none=True) for cat_type in policy_input.categoryTypes]
    }
    
    # Add optional fields
    if policy_input.description:
        policy_data["description"] = policy_input.description
    
    if policy_input.handlingTime:
        handling_time_data = policy_input.handlingTime.model_dump(mode='json', exclude_none=True)
        if handling_time_data:
            policy_data["handlingTime"] = handling_time_data
    
    if policy_input.shippingOptions:
        shipping_options = []
        for option in policy_input.shippingOptions:
            option_data = {
                "costType": option.costType.value,
                "optionType": option.optionType.value
            }
            
            # Add optional shipping option fields
            if option.shippingServices:
                services = []
                for service in option.shippingServices:
                    service_data = {
                        "shippingServiceCode": service.shippingServiceCode.value
                    }
                    
                    # Add optional service fields
                    if service.shippingCarrierCode:
                        service_data["shippingCarrierCode"] = service.shippingCarrierCode
                    if service.shippingCost:
                        shipping_cost_data = service.shippingCost.model_dump(mode='json', exclude_none=True)
                        if shipping_cost_data:
                            service_data["shippingCost"] = shipping_cost_data
                    if service.additionalShippingCost:
                        additional_cost_data = service.additionalShippingCost.model_dump(mode='json', exclude_none=True)
                        if additional_cost_data:
                            service_data["additionalShippingCost"] = additional_cost_data
                    if service.freeShipping is not None:
                        service_data["freeShipping"] = service.freeShipping
                    if service.shipToLocations:
                        ship_to_locations_data = service.shipToLocations.model_dump(mode='json', exclude_none=True)
                        if ship_to_locations_data:
                            service_data["shipToLocations"] = ship_to_locations_data
                    if service.sortOrder is not None:
                        service_data["sortOrder"] = service.sortOrder
                    if service.buyerResponsibleForShipping is not None:
                        service_data["buyerResponsibleForShipping"] = service.buyerResponsibleForShipping
                    if service.buyerResponsibleForPickup is not None:
                        service_data["buyerResponsibleForPickup"] = service.buyerResponsibleForPickup
                    
                    services.append(service_data)
                option_data["shippingServices"] = services
            
            if option.packageHandlingCost:
                handling_cost_data = option.packageHandlingCost.model_dump(mode='json', exclude_none=True)
                if handling_cost_data:
                    option_data["packageHandlingCost"] = handling_cost_data
            if option.rateTableId:
                option_data["rateTableId"] = option.rateTableId
            if option.shippingDiscountProfileId:
                option_data["shippingDiscountProfileId"] = option.shippingDiscountProfileId
            if option.shippingPromotionOffered is not None:
                option_data["shippingPromotionOffered"] = option.shippingPromotionOffered
            
            shipping_options.append(option_data)
        
        policy_data["shippingOptions"] = shipping_options
    
    if policy_input.shipToLocations:
            ship_to_locations_data = policy_input.shipToLocations.model_dump(mode='json', exclude_none=True)
            if ship_to_locations_data:
                policy_data["shipToLocations"] = ship_to_locations_data

    if policy_input.localPickup is not None:
        policy_data["localPickup"] = policy_input.localPickup
    if policy_input.pickupDropOff is not None:
        policy_data["pickupDropOff"] = policy_input.pickupDropOff
    if policy_input.freightShipping is not None:
        policy_data["freightShipping"] = policy_input.freightShipping
    if policy_input.globalShipping is not None:
        policy_data["globalShipping"] = policy_input.globalShipping
    
    return policy_data


def _format_policy_response(policy_data: Dict[str, Any]) -> Dict[str, Any]:
    """Format eBay fulfillment policy response for consistent output."""
    formatted = {
        "fulfillmentPolicyId": policy_data.get("fulfillmentPolicyId"),
        "name": policy_data.get("name"),
        "description": policy_data.get("description"),
        "marketplaceId": policy_data.get("marketplaceId"),
        "categoryTypes": policy_data.get("categoryTypes", []),
        "handlingTime": policy_data.get("handlingTime"),
        "shippingOptions": policy_data.get("shippingOptions", []),
        "shipToLocations": policy_data.get("shipToLocations"),
        "localPickup": policy_data.get("localPickup"),
        "pickupDropOff": policy_data.get("pickupDropOff"),
        "freightShipping": policy_data.get("freightShipping"),
        "globalShipping": policy_data.get("globalShipping"),
        "warnings": policy_data.get("warnings", [])
    }
    
    # Clean up None values
    return {k: v for k, v in formatted.items() if v is not None}


def _api_response_to_pydantic(response_body: Dict[str, Any]) -> Any:
    """Convert eBay API response to response pydantic model."""
    # For now, just return the formatted response
    # In future, can create proper response models
    class Response:
        def __init__(self):
            self.fulfillmentPolicyId = response_body.get("fulfillmentPolicyId")
        
        def model_dump(self, **kwargs):
            return _format_policy_response(response_body)
    
    return Response()


# MCP TOOLS - Using Pydantic Models


@mcp.tool
async def create_fulfillment_policy(
    ctx: Context,
    policy_input: Union[FulfillmentPolicyInput, str, Dict[str, Any]]
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
        JSON response with created policy details including policyId
    
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
        policy_data = build_policy_data(policy_input)
        
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
        await ctx.success(f"Created fulfillment policy '{policy_input.name}' with ID: {policy_response.fulfillmentPolicyId}")
        
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
    marketplaceId: MarketplaceIdEnum
) -> str:
    """
    Retrieve all fulfillment policies for a specific marketplace.
    
    Returns a paginated list of all fulfillment policies configured for the
    specified eBay marketplace. Use this to review existing shipping configurations.
    
    Args:
        marketplaceId: eBay marketplace to retrieve policies for
        ctx: MCP context
    
    Returns:
        JSON response with list of fulfillment policies and pagination info
    
    OAuth Scope Required: https://api.ebay.com/oauth/api_scope/sell.account
    """
    await ctx.info(f"Retrieving fulfillment policies for marketplace: {marketplaceId.value}")
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
            "marketplace_id": marketplaceId.value
        }
        
        # Make API call
        response = await rest_client.get(
            f"/sell/account/v1/fulfillment_policy",
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
            "marketplaceId": marketplaceId.value
        }
        
        # Add pagination links if available
        if response_body.get("href"):
            result["href"] = response_body["href"]
        if response.get("next"):
            result["next"] = response["next"]
        if response.get("prev"):
            result["prev"] = response["prev"]
        
        await ctx.report_progress(1.0, f"Retrieved {len(formatted_policies)} fulfillment policies")
        await ctx.success(f"Found {len(formatted_policies)} fulfillment policies for {marketplaceId.value}")
        
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
    policyId: str
) -> str:
    """
    Retrieve a specific fulfillment policy by its ID.
    
    Returns detailed information about a single fulfillment policy including
    all shipping options, handling time, and service configurations.
    
    Args:
        policyId: eBay fulfillment policy ID
        ctx: MCP context
    
    Returns:
        JSON response with complete fulfillment policy details
    
    OAuth Scope Required: https://api.ebay.com/oauth/api_scope/sell.account
    """
    await ctx.info(f"Retrieving fulfillment policy: {policyId}")
    await ctx.report_progress(0.1, "Validating parameters...")
    
    if not policyId or not policyId.strip():
        return error_response(
            ErrorCode.VALIDATION_ERROR,
            "policyId is required and cannot be empty"
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
        await ctx.report_progress(0.5, f"Fetching fulfillment policy {policyId}...")
        
        # Make API call
        response = await rest_client.get(f"/sell/account/v1/fulfillment_policy/{policyId}")
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
    marketplaceId: MarketplaceIdEnum,
    name: str
) -> str:
    """
    Retrieve a specific fulfillment policy by its name and marketplace.
    
    Looks up a fulfillment policy using its seller-defined name within
    a specific marketplace. Policy names must be unique per marketplace.
    
    Args:
        marketplaceId: eBay marketplace where the policy exists
        name: Seller-defined name of the fulfillment policy
        ctx: MCP context
    
    Returns:
        JSON response with complete fulfillment policy details
    
    OAuth Scope Required: https://api.ebay.com/oauth/api_scope/sell.account
    """
    await ctx.info(f"Retrieving fulfillment policy '{name}' for marketplace: {marketplaceId.value}")
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
            "marketplace_id": marketplaceId.value,
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
        await ctx.success(f"Found fulfillment policy '{name}' with ID: {formatted_response.get('policyId')}")
        
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
    policyId: str,
    policy_input: Union[FulfillmentPolicyInput, str, Dict[str, Any]]
) -> str:
    """
    Update an existing fulfillment policy.
    
    Modifies the configuration of an existing fulfillment policy. All fields
    will be replaced with the provided values - this is a complete replacement,
    not a partial update.
    
    Args:
        policyId: eBay fulfillment policy ID to update
        policy_input: Complete updated fulfillment policy configuration
        ctx: MCP context
    
    Returns:
        JSON response with updated policy details
    
    OAuth Scope Required: https://api.ebay.com/oauth/api_scope/sell.account
    """
    await ctx.info(f"Updating fulfillment policy: {policyId}")
    await ctx.report_progress(0.1, "Validating parameters...")
    
    if not policyId or not policyId.strip():
        return error_response(
            ErrorCode.VALIDATION_ERROR,
            "policyId is required and cannot be empty"
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
        policy_data = build_policy_data(policy_input)
        
        await ctx.report_progress(0.5, f"Updating fulfillment policy {policyId}...")
        
        # Make API call
        response = await rest_client.put(
            f"/sell/account/v1/fulfillment_policy/{policyId}",
            json=policy_data
        )
        response_body = response["body"]
        
        await ctx.report_progress(0.8, "Processing response...")
        
        # Format response
        formatted_response = _format_policy_response(response_body)
        
        await ctx.report_progress(1.0, "Fulfillment policy updated successfully")
        await ctx.success(f"Updated fulfillment policy '{policy_input.name}' (ID: {policyId})")
        
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
    policyId: str
) -> str:
    """
    Delete a fulfillment policy from your eBay seller account.
    
    Permanently removes a fulfillment policy. The policy cannot be deleted if
    it's currently being used by active listings or listing templates.
    
    Args:
        policyId: eBay fulfillment policy ID to delete
        ctx: MCP context
    
    Returns:
        JSON response confirming deletion
    
    OAuth Scope Required: https://api.ebay.com/oauth/api_scope/sell.account
    """
    await ctx.info(f"Deleting fulfillment policy: {policyId}")
    await ctx.report_progress(0.1, "Validating parameters...")
    
    if not policyId or not policyId.strip():
        return error_response(
            ErrorCode.VALIDATION_ERROR,
            "policyId is required and cannot be empty"
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
        await ctx.report_progress(0.5, f"Deleting fulfillment policy {policyId}...")
        
        # Make API call
        await rest_client.delete(f"/sell/account/v1/fulfillment_policy/{policyId}")
        
        await ctx.report_progress(1.0, "Fulfillment policy deleted successfully")
        await ctx.success(f"Fulfillment policy {policyId} deleted successfully")
        
        return success_response(
            data={"policyId": policyId, "deleted": True},
            message=f"Fulfillment policy {policyId} deleted successfully"
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