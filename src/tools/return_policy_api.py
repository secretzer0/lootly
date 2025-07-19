"""
eBay Return Policy API tools for managing seller return policies.

This module provides MCP tools for creating, updating, retrieving, and deleting
return policies in eBay seller accounts. Return policies define the terms under
which buyers can return items.

IMPLEMENTATION FOLLOWS: PYDANTIC-FIRST DEVELOPMENT METHODOLOGY
- All API fields included exactly as documented
- Strong typing with enums throughout
- Validation through Pydantic models only
- Zero manual validation code
"""
from typing import Dict, Any
from fastmcp import Context

from api.oauth import OAuthManager, OAuthConfig, ConsentRequiredException
from api.rest_client import EbayRestClient, RestConfig
from api.errors import EbayApiError
from models.enums import (
    MarketplaceIdEnum
)
from models.policies import ReturnPolicyInput, UpdateReturnPolicyInput
from data_types import success_response, error_response, ErrorCode
from lootly_server import mcp


# PYDANTIC MODELS - API Documentation → Pydantic Models → MCP Tools


# HELPER FUNCTIONS

def _convert_to_api_format(policy_input: ReturnPolicyInput) -> Dict[str, Any]:
    """Convert Pydantic ReturnPolicyInput to eBay API format."""
    policy_data = {
        "name": policy_input.name,
        "marketplaceId": policy_input.marketplace_id.value,
        "categoryTypes": [cat_type.model_dump(mode='json') for cat_type in policy_input.category_types]
    }
    
    # Add optional fields
    if policy_input.description:
        policy_data["description"] = policy_input.description
    
    if policy_input.returns_accepted is not None:
        policy_data["returnsAccepted"] = policy_input.returns_accepted
    
    if policy_input.return_period:
        policy_data["returnPeriod"] = policy_input.return_period.model_dump()
    
    if policy_input.return_method:
        policy_data["returnMethod"] = policy_input.return_method.value
    
    if policy_input.return_shipping_cost_payer:
        policy_data["returnShippingCostPayer"] = policy_input.return_shipping_cost_payer.value
    
    if policy_input.refund_method:
        policy_data["refundMethod"] = policy_input.refund_method.value
    
    if policy_input.return_instructions:
        policy_data["returnInstructions"] = policy_input.return_instructions
    
    if policy_input.restocking_fee_percentage is not None:
        policy_data["restockingFeePercentage"] = policy_input.restocking_fee_percentage
    
    if policy_input.international_override:
        policy_data["internationalOverride"] = policy_input.international_override.model_dump()
    
    return policy_data


def _format_policy_response(policy_data: Dict[str, Any]) -> Dict[str, Any]:
    """Format eBay return policy response for consistent output."""
    formatted = {
        "returnPolicyId": policy_data.get("returnPolicyId"),
        "name": policy_data.get("name"),
        "description": policy_data.get("description"),
        "marketplaceId": policy_data.get("marketplaceId"),
        "categoryTypes": policy_data.get("categoryTypes", []),
        "returnsAccepted": policy_data.get("returnsAccepted"),
        "returnPeriod": policy_data.get("returnPeriod"),
        "returnMethod": policy_data.get("returnMethod"),
        "returnShippingCostPayer": policy_data.get("returnShippingCostPayer"),
        "refundMethod": policy_data.get("refundMethod"),
        "returnInstructions": policy_data.get("returnInstructions"),
        "restockingFeePercentage": policy_data.get("restockingFeePercentage"),
        "internationalOverride": policy_data.get("internationalOverride"),
        "warnings": policy_data.get("warnings", [])
    }
    
    # Clean up None values
    return {k: v for k, v in formatted.items() if v is not None}


@mcp.tool
async def create_return_policy(
    ctx: Context,
    policy_input: ReturnPolicyInput
) -> str:
    """
    Create a new return policy for your eBay seller account.
    
    Return policies define the terms under which buyers can return items.
    You can create multiple policies for different types of products.
    
    Args:
        policy_input: Complete return policy configuration with all required fields
        ctx: MCP context
    
    Returns:
        JSON response with created policy details including policy_id
    """
    await ctx.info(f"Creating return policy: {policy_input.name}")
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
        await ctx.report_progress(0.3, "Creating policy with eBay API...")
        
        # Convert Pydantic model to API format
        policy_data = _convert_to_api_format(policy_input)
        
        # Make API request
        response = await rest_client.post(
            "/sell/account/v1/return_policy",
            json=policy_data
        )
        response_body = response["body"]
        
        await ctx.report_progress(0.8, "Processing response...")
        
        # Format response
        formatted_response = _format_policy_response(response_body)
        
        await ctx.report_progress(1.0, "Complete")
        await ctx.info(f"Return policy created successfully with ID: {formatted_response['policy_id']}")
        
        return success_response(
            data=formatted_response,
            message=f"Return policy '{policy_input.name}' created successfully"
        ).to_json_string()
        
    except ConsentRequiredException as e:
        await ctx.error(f"User consent required: {str(e)}")
        return error_response(
            ErrorCode.AUTHENTICATION_ERROR,
            "User consent required. Use initiate_user_consent tool to authorize eBay API access."
        ).to_json_string()
    except EbayApiError as e:
        # Log comprehensive error details
        await ctx.error(f"eBay API error: {e.get_comprehensive_message()}")
        
        # Return full error details in response
        return error_response(
            ErrorCode.EXTERNAL_API_ERROR,
            e.get_comprehensive_message(),
            e.get_full_error_details()
        ).to_json_string()
    except Exception as e:
        await ctx.error(f"Failed to create return policy: {str(e)}")
        return error_response(
            ErrorCode.INTERNAL_ERROR,
            f"Failed to create return policy: {str(e)}"
        ).to_json_string()
    finally:
        await rest_client.close()


@mcp.tool
async def get_return_policies(
    ctx: Context,
    marketplace_id: MarketplaceIdEnum,
    limit: int = 20,
    offset: int = 0
) -> str:
    """
    Get all return policies for a specific marketplace.
    
    Retrieves a paginated list of all return policies configured for
    the specified marketplace in your seller account.
    
    Args:
        marketplace_id: eBay marketplace
        limit: Number of policies to return (1-100, default 20)
        offset: Number of policies to skip for pagination (default 0)
        ctx: MCP context
    
    Returns:
        JSON response with list of return policies and pagination info
    """
    await ctx.info(f"Getting return policies for {marketplace_id.value}")
    
    if limit < 1 or limit > 100:
        return error_response(
            ErrorCode.VALIDATION_ERROR,
            "Limit must be between 1 and 100"
        ).to_json_string()
    
    if offset < 0:
        return error_response(
            ErrorCode.VALIDATION_ERROR,
            "Offset must be non-negative"
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
        await ctx.report_progress(0.3, "Fetching policies from eBay...")
        
        # Make API request
        params = {
            "marketplace_id": marketplace_id.value,
            "limit": limit,
            "offset": offset
        }
        
        response = await rest_client.get(
            "/sell/account/v1/return_policy",
            params=params
        )
        response_body = response["body"]
        
        await ctx.report_progress(0.8, "Processing policies...")
        
        # Format response
        policies = []
        for policy in response_body.get("returnPolicies", []):
            policies.append(_format_policy_response(policy))
        
        result = {
            "policies": policies,
            "total": response_body.get("total", 0),
            "limit": limit,
            "offset": offset,
            "has_more": offset + len(policies) < response_body.get("total", 0)
        }
        
        await ctx.report_progress(1.0, "Complete")
        await ctx.info(f"Found {len(policies)} return policies")
        
        return success_response(
            data=result,
            message=f"Retrieved {len(policies)} return policies"
        ).to_json_string()
        
    except ConsentRequiredException as e:
        await ctx.error(f"User consent required: {str(e)}")
        return error_response(
            ErrorCode.AUTHENTICATION_ERROR,
            "User consent required. Use initiate_user_consent tool to authorize eBay API access."
        ).to_json_string()
    except EbayApiError as e:
        # Log comprehensive error details
        await ctx.error(f"eBay API error: {e.get_comprehensive_message()}")
        
        # Return full error details in response
        return error_response(
            ErrorCode.EXTERNAL_API_ERROR,
            e.get_comprehensive_message(),
            e.get_full_error_details()
        ).to_json_string()
    except Exception as e:
        await ctx.error(f"Failed to get return policies: {str(e)}")
        return error_response(
            ErrorCode.INTERNAL_ERROR,
            f"Failed to get return policies: {str(e)}"
        ).to_json_string()
    finally:
        await rest_client.close()


@mcp.tool
async def get_return_policy(
    ctx: Context,
    return_policy_id: str
) -> str:
    """
    Get a specific return policy by its ID.
    
    Retrieves detailed information about a single return policy
    using its unique policy ID.
    
    Args:
        return_policy_id: The unique identifier of the return policy
        ctx: MCP context
    
    Returns:
        JSON response with complete policy details
    """
    await ctx.info(f"Getting return policy: {return_policy_id}")
    
    if not return_policy_id:
        return error_response(
            ErrorCode.VALIDATION_ERROR,
            "Return policy ID is required"
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
        await ctx.report_progress(0.3, "Fetching policy from eBay...")
        
        # Make API request
        response = await rest_client.get(
            f"/sell/account/v1/return_policy/{return_policy_id}"
        )
        response_body = response["body"]
        
        await ctx.report_progress(0.8, "Processing policy...")
        
        # Format response
        formatted_response = _format_policy_response(response_body)
        
        await ctx.report_progress(1.0, "Complete")
        await ctx.info(f"Retrieved return policy: {formatted_response.get('name', 'Unknown')}")
        
        return success_response(
            data=formatted_response,
            message=f"Retrieved return policy successfully"
        ).to_json_string()
        
    except ConsentRequiredException as e:
        await ctx.error(f"User consent required: {str(e)}")
        return error_response(
            ErrorCode.AUTHENTICATION_ERROR,
            "User consent required. Use initiate_user_consent tool to authorize eBay API access."
        ).to_json_string()
    except EbayApiError as e:
        # Log comprehensive error details
        await ctx.error(f"eBay API error: {e.get_comprehensive_message()}")
        
        # Return full error details in response
        return error_response(
            ErrorCode.EXTERNAL_API_ERROR,
            e.get_comprehensive_message(),
            e.get_full_error_details()
        ).to_json_string()
    except Exception as e:
        await ctx.error(f"Failed to get return policy: {str(e)}")
        return error_response(
            ErrorCode.INTERNAL_ERROR,
            f"Failed to get return policy: {str(e)}"
        ).to_json_string()
    finally:
        await rest_client.close()


@mcp.tool
async def get_return_policy_by_name(
    ctx: Context,
    marketplace_id: MarketplaceIdEnum,
    name: str
) -> str:
    """
    Get a return policy by its name.
    
    Retrieves a return policy using its name and marketplace.
    Policy names must be unique within a marketplace.
    
    Args:
        marketplace_id: eBay marketplace where the policy exists
        name: The exact name of the return policy
        ctx: MCP context
    
    Returns:
        JSON response with policy details if found
    """
    await ctx.info(f"Searching for return policy by name: {name}")
    
    if not name:
        return error_response(
            ErrorCode.VALIDATION_ERROR,
            "Policy name is required"
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
        await ctx.report_progress(0.3, "Searching for policy...")
        
        # Make API request
        params = {
            "marketplace_id": marketplace_id.value,
            "name": name
        }
        
        response = await rest_client.get(
            "/sell/account/v1/return_policy/get_by_policy_name",
            params=params
        )
        response_body = response["body"]
        
        await ctx.report_progress(0.8, "Processing policy...")
        
        # Format response
        formatted_response = _format_policy_response(response_body)
        
        await ctx.report_progress(1.0, "Complete")
        await ctx.info(f"Found return policy: {name}")
        
        return success_response(
            data=formatted_response,
            message=f"Found return policy '{name}'"
        ).to_json_string()
        
    except EbayApiError as e:
        # Log comprehensive error details
        await ctx.error(f"eBay API error: {e.get_comprehensive_message()}")
        
        # Handle 404 specially for not found
        if e.status_code == 404:
            return error_response(
                ErrorCode.RESOURCE_NOT_FOUND,
                f"No return policy found with name '{name}' in marketplace {marketplace_id.value}",
                e.get_full_error_details()
            ).to_json_string()
        
        # Return full error details in response
        return error_response(
            ErrorCode.EXTERNAL_API_ERROR,
            e.get_comprehensive_message(),
            e.get_full_error_details()
        ).to_json_string()
    except Exception as e:
        await ctx.error(f"Failed to get return policy by name: {str(e)}")
        return error_response(
            ErrorCode.INTERNAL_ERROR,
            f"Failed to get return policy by name: {str(e)}"
        ).to_json_string()
    finally:
        await rest_client.close()


# Update model is same as create model
# eBay API uses the same structure for both
UpdateReturnPolicyInput = ReturnPolicyInput


@mcp.tool
async def update_return_policy(
    ctx: Context,
    return_policy_id: str,
    policy_input: UpdateReturnPolicyInput
) -> str:
    """
    Update an existing return policy.
    
    Updates all fields of an existing return policy. You must provide
    all fields, not just the ones you want to change.
    
    Args:
        return_policy_id: The ID of the policy to update
        policy_input: Complete updated policy configuration
        ctx: MCP context
    
    Returns:
        JSON response with updated policy details
    """
    await ctx.info(f"Updating return policy: {return_policy_id}")
    await ctx.report_progress(0.1, "Validating input parameters...")
    
    if not return_policy_id:
        return error_response(
            ErrorCode.VALIDATION_ERROR,
            "Return policy ID is required"
        ).to_json_string()
    
    # Pydantic validation already handled for policy_input
    
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
        await ctx.report_progress(0.3, "Updating policy with eBay API...")
        
        # Convert Pydantic model to API format
        policy_data = _convert_to_api_format(policy_input)
        
        # Make API request
        response = await rest_client.put(
            f"/sell/account/v1/return_policy/{return_policy_id}",
            json=policy_data
        )
        response_body = response["body"]
        
        await ctx.report_progress(0.8, "Processing response...")
        
        # Format response
        formatted_response = _format_policy_response(response_body)
        
        await ctx.report_progress(1.0, "Complete")
        await ctx.info(f"Return policy updated successfully: {policy_input.name}")
        
        return success_response(
            data=formatted_response,
            message=f"Return policy '{policy_input.name}' updated successfully"
        ).to_json_string()
        
    except ConsentRequiredException as e:
        await ctx.error(f"User consent required: {str(e)}")
        return error_response(
            ErrorCode.AUTHENTICATION_ERROR,
            "User consent required. Use initiate_user_consent tool to authorize eBay API access."
        ).to_json_string()
    except EbayApiError as e:
        # Log comprehensive error details
        await ctx.error(f"eBay API error: {e.get_comprehensive_message()}")
        
        # Return full error details in response
        return error_response(
            ErrorCode.EXTERNAL_API_ERROR,
            e.get_comprehensive_message(),
            e.get_full_error_details()
        ).to_json_string()
    except Exception as e:
        await ctx.error(f"Failed to update return policy: {str(e)}")
        return error_response(
            ErrorCode.INTERNAL_ERROR,
            f"Failed to update return policy: {str(e)}"
        ).to_json_string()
    finally:
        await rest_client.close()


@mcp.tool
async def delete_return_policy(
    ctx: Context,
    return_policy_id: str
) -> str:
    """
    Delete a return policy.
    
    Permanently deletes a return policy. This action cannot be undone.
    The policy must not be associated with any active listings.
    
    Args:
        return_policy_id: The ID of the policy to delete
        ctx: MCP context
    
    Returns:
        JSON response confirming deletion
    """
    await ctx.info(f"Deleting return policy: {return_policy_id}")
    
    if not return_policy_id:
        return error_response(
            ErrorCode.VALIDATION_ERROR,
            "Return policy ID is required"
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
        await ctx.report_progress(0.3, "Deleting policy from eBay...")
        
        # Make API request
        await rest_client.delete(
            f"/sell/account/v1/return_policy/{return_policy_id}"
        )
        
        await ctx.report_progress(0.8, "Processing response...")
        
        # Delete typically returns 204 No Content
        await ctx.report_progress(1.0, "Complete")
        await ctx.info(f"Return policy deleted successfully")
        
        return success_response(
            data={"deleted": True, "policy_id": return_policy_id},
            message=f"Return policy {return_policy_id} deleted successfully"
        ).to_json_string()
        
    except EbayApiError as e:
        # Log comprehensive error details
        await ctx.error(f"eBay API error: {e.get_comprehensive_message()}")
        
        # Handle special cases
        if e.status_code == 404:
            return error_response(
                ErrorCode.RESOURCE_NOT_FOUND,
                f"Return policy {return_policy_id} not found",
                e.get_full_error_details()
            ).to_json_string()
        elif e.status_code == 409:
            return error_response(
                ErrorCode.PERMISSION_DENIED,
                "Cannot delete policy that is associated with active listings",
                e.get_full_error_details()
            ).to_json_string()
        
        # Return full error details in response
        return error_response(
            ErrorCode.EXTERNAL_API_ERROR,
            e.get_comprehensive_message(),
            e.get_full_error_details()
        ).to_json_string()
    except Exception as e:
        await ctx.error(f"Failed to delete return policy: {str(e)}")
        return error_response(
            ErrorCode.INTERNAL_ERROR,
            f"Failed to delete return policy: {str(e)}"
        ).to_json_string()
    finally:
        await rest_client.close()