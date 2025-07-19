"""
eBay Payment Policy API tools for managing seller payment policies.

This module provides MCP tools for creating, updating, retrieving, and deleting
payment policies in eBay seller accounts. Payment policies define accepted payment
methods, payment terms, and special handling for motor vehicle listings.

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
from models.policies import PaymentPolicyInput, UpdatePaymentPolicyInput
from data_types import success_response, error_response, ErrorCode
from lootly_server import mcp


# PYDANTIC MODELS - API Documentation → Pydantic Models → MCP Tools


# HELPER FUNCTIONS

def _convert_to_api_format(policy_input: PaymentPolicyInput) -> Dict[str, Any]:
    """Convert Pydantic PaymentPolicyInput to eBay API format."""
    policy_data = {
        "name": policy_input.name,
        "marketplaceId": policy_input.marketplaceId.value,
        "categoryTypes": [cat_type.model_dump(mode='json') for cat_type in policy_input.categoryTypes]
    }
    
    # Add optional fields
    if policy_input.description:
        policy_data["description"] = policy_input.description
    
    if policy_input.paymentMethods:
        paymentMethods = []
        for method in policy_input.paymentMethods:
            method_data = {
                "paymentMethodType": method.payment_method_type.value
            }
            if method.brands:
                method_data["brands"] = [brand.value for brand in method.brands]
            paymentMethods.append(method_data)
        policy_data["paymentMethods"] = paymentMethods
    
    if policy_input.deposit:
        deposit_data = {}
        if policy_input.deposit.dueIn:
            deposit_data["dueIn"] = policy_input.deposit.dueIn.model_dump(mode='json')
        if policy_input.deposit.amount:
            deposit_data["amount"] = policy_input.deposit.amount.model_dump(mode='json')
        policy_data["deposit"] = deposit_data
    
    if policy_input.fullPaymentDueIn:
        policy_data["fullPaymentDueIn"] = policy_input.fullPaymentDueIn.model_dump(mode='json')
    
    if policy_input.immediatePay is not None:
        policy_data["immediatePay"] = policy_input.immediatePay
    
    return policy_data


def _format_policy_response(policy_data: Dict[str, Any]) -> Dict[str, Any]:
    """Format eBay payment policy response for consistent output."""
    formatted = {
        "paymentPolicyId": policy_data.get("paymentPolicyId"),
        "name": policy_data.get("name"),
        "description": policy_data.get("description"),
        "marketplaceId": policy_data.get("marketplaceId"),
        "categoryTypes": policy_data.get("categoryTypes", []),
        "paymentMethods": policy_data.get("paymentMethods", []),
        "deposit": policy_data.get("deposit"),
        "fullPaymentDueIn": policy_data.get("fullPaymentDueIn"),
        "immediatePay": policy_data.get("immediatePay"),
        "warnings": policy_data.get("warnings", [])
    }
    
    # Clean up None values
    return {k: v for k, v in formatted.items() if v is not None}


@mcp.tool
async def create_payment_policy(
    ctx: Context,
    policy_input: PaymentPolicyInput
) -> str:
    """
    Create a new payment policy for your eBay seller account.
    
    Payment policies define accepted payment methods and terms. Special
    handling is required for motor vehicle listings including deposits
    and payment due dates.
    
    Args:
        policy_input: Complete payment policy configuration with all required fields
        ctx: MCP context
    
    Returns:
        JSON response with created policy details including policy_id
    """
    await ctx.info(f"Creating payment policy: {policy_input.name}")
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
            "/sell/account/v1/payment_policy",
            json=policy_data
        )
        response_body = response["body"]
        
        await ctx.report_progress(0.8, "Processing response...")
        
        # Format response
        formatted_response = _format_policy_response(response_body)
        
        await ctx.report_progress(1.0, "Complete")
        await ctx.info(f"Payment policy created successfully with ID: {formatted_response['paymentPolicyId']}")
        
        return success_response(
            data=formatted_response,
            message=f"Payment policy '{policy_input.name}' created successfully"
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
        await ctx.error(f"Failed to create payment policy: {str(e)}")
        return error_response(
            ErrorCode.INTERNAL_ERROR,
            f"Failed to create payment policy: {str(e)}"
        ).to_json_string()
    finally:
        await rest_client.close()


@mcp.tool
async def get_payment_policies(
    ctx: Context,
    marketplaceId: MarketplaceIdEnum,
    limit: int = 20,
    offset: int = 0
) -> str:
    """
    Get all payment policies for a specific marketplace.
    
    Retrieves a paginated list of all payment policies configured for
    the specified marketplace in your seller account.
    
    Args:
        marketplace_id: eBay marketplace
        limit: Number of policies to return (1-100, default 20)
        offset: Number of policies to skip for pagination (default 0)
        ctx: MCP context
    
    Returns:
        JSON response with list of payment policies and pagination info
    """
    await ctx.info(f"Getting payment policies for {marketplaceId.value}")
    
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
            "marketplaceId": marketplaceId.value,
            "limit": limit,
            "offset": offset
        }
        
        response = await rest_client.get(
            "/sell/account/v1/payment_policy",
            params=params
        )
        response_body = response["body"]
        
        await ctx.report_progress(0.8, "Processing policies...")
        
        # Format response
        policies = []
        for policy in response_body.get("paymentPolicies", []):
            policies.append(_format_policy_response(policy))
        
        result = {
            "policies": policies,
            "total": response_body.get("total", 0),
            "limit": limit,
            "offset": offset,
            "has_more": offset + len(policies) < response_body.get("total", 0)
        }
        
        await ctx.report_progress(1.0, "Complete")
        await ctx.info(f"Found {len(policies)} payment policies")
        
        return success_response(
            data=result,
            message=f"Retrieved {len(policies)} payment policies"
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
        await ctx.error(f"Failed to get payment policies: {str(e)}")
        return error_response(
            ErrorCode.INTERNAL_ERROR,
            f"Failed to get payment policies: {str(e)}"
        ).to_json_string()
    finally:
        await rest_client.close()


@mcp.tool
async def get_payment_policy(
    ctx: Context,
    payment_policy_id: str
) -> str:
    """
    Get a specific payment policy by its ID.
    
    Retrieves detailed information about a single payment policy
    using its unique policy ID.
    
    Args:
        payment_policy_id: The unique identifier of the payment policy
        ctx: MCP context
    
    Returns:
        JSON response with complete policy details
    """
    await ctx.info(f"Getting payment policy: {payment_policy_id}")
    
    if not payment_policy_id:
        return error_response(
            ErrorCode.VALIDATION_ERROR,
            "Payment policy ID is required"
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
            f"/sell/account/v1/payment_policy/{payment_policy_id}"
        )
        response_body = response["body"]
        
        await ctx.report_progress(0.8, "Processing policy...")
        
        # Format response
        formatted_response = _format_policy_response(response_body)
        
        await ctx.report_progress(1.0, "Complete")
        await ctx.info(f"Retrieved payment policy: {formatted_response.get('name', 'Unknown')}")
        
        return success_response(
            data=formatted_response,
            message=f"Retrieved payment policy successfully"
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
        await ctx.error(f"Failed to get payment policy: {str(e)}")
        return error_response(
            ErrorCode.INTERNAL_ERROR,
            f"Failed to get payment policy: {str(e)}"
        ).to_json_string()
    finally:
        await rest_client.close()


@mcp.tool
async def get_payment_policy_by_name(
    ctx: Context,
    marketplaceId: MarketplaceIdEnum,
    name: str
) -> str:
    """
    Get a payment policy by its name.
    
    Retrieves a payment policy using its name and marketplace.
    Policy names must be unique within a marketplace.
    
    Args:
        marketplace_id: eBay marketplace where the policy exists
        name: The exact name of the payment policy
        ctx: MCP context
    
    Returns:
        JSON response with policy details if found
    """
    await ctx.info(f"Searching for payment policy by name: {name}")
    
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
            "marketplaceId": marketplaceId.value,
            "name": name
        }
        
        response = await rest_client.get(
            "/sell/account/v1/payment_policy/get_by_policy_name",
            params=params
        )
        response_body = response["body"]
        
        await ctx.report_progress(0.8, "Processing policy...")
        
        # Format response
        formatted_response = _format_policy_response(response_body)
        
        await ctx.report_progress(1.0, "Complete")
        await ctx.info(f"Found payment policy: {name}")
        
        return success_response(
            data=formatted_response,
            message=f"Found payment policy '{name}'"
        ).to_json_string()
        
    except EbayApiError as e:
        # Log comprehensive error details
        await ctx.error(f"eBay API error: {e.get_comprehensive_message()}")
        
        # Handle 404 specially for not found
        if e.status_code == 404:
            return error_response(
                ErrorCode.RESOURCE_NOT_FOUND,
                f"No payment policy found with name '{name}' in marketplace {marketplaceId.value}",
                e.get_full_error_details()
            ).to_json_string()
        
        # Return full error details in response
        return error_response(
            ErrorCode.EXTERNAL_API_ERROR,
            e.get_comprehensive_message(),
            e.get_full_error_details()
        ).to_json_string()
    except Exception as e:
        await ctx.error(f"Failed to get payment policy by name: {str(e)}")
        return error_response(
            ErrorCode.INTERNAL_ERROR,
            f"Failed to get payment policy by name: {str(e)}"
        ).to_json_string()
    finally:
        await rest_client.close()


@mcp.tool
async def update_payment_policy(
    ctx: Context,
    payment_policy_id: str,
    policy_input: UpdatePaymentPolicyInput
) -> str:
    """
    Update an existing payment policy.
    
    Updates all fields of an existing payment policy. You must provide
    all fields, not just the ones you want to change.
    
    Args:
        payment_policy_id: The ID of the policy to update
        policy_input: Complete updated policy configuration
        ctx: MCP context
    
    Returns:
        JSON response with updated policy details
    """
    await ctx.info(f"Updating payment policy: {payment_policy_id}")
    await ctx.report_progress(0.1, "Validating input parameters...")
    
    if not payment_policy_id:
        return error_response(
            ErrorCode.VALIDATION_ERROR,
            "Payment policy ID is required"
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
            f"/sell/account/v1/payment_policy/{payment_policy_id}",
            json=policy_data
        )
        response_body = response["body"]
        
        await ctx.report_progress(0.8, "Processing response...")
        
        # Format response
        formatted_response = _format_policy_response(response_body)
        
        await ctx.report_progress(1.0, "Complete")
        await ctx.info(f"Payment policy updated successfully: {policy_input.name}")
        
        return success_response(
            data=formatted_response,
            message=f"Payment policy '{policy_input.name}' updated successfully"
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
        await ctx.error(f"Failed to update payment policy: {str(e)}")
        return error_response(
            ErrorCode.INTERNAL_ERROR,
            f"Failed to update payment policy: {str(e)}"
        ).to_json_string()
    finally:
        await rest_client.close()


@mcp.tool
async def delete_payment_policy(
    ctx: Context,
    payment_policy_id: str
) -> str:
    """
    Delete a payment policy.
    
    Permanently deletes a payment policy. This action cannot be undone.
    The policy must not be associated with any active listings.
    
    Args:
        payment_policy_id: The ID of the policy to delete
        ctx: MCP context
    
    Returns:
        JSON response confirming deletion
    """
    await ctx.info(f"Deleting payment policy: {payment_policy_id}")
    
    if not payment_policy_id:
        return error_response(
            ErrorCode.VALIDATION_ERROR,
            "Payment policy ID is required"
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
            f"/sell/account/v1/payment_policy/{payment_policy_id}"
        )
        
        await ctx.report_progress(0.8, "Processing response...")
        
        # Delete typically returns 204 No Content
        await ctx.report_progress(1.0, "Complete")
        await ctx.info(f"Payment policy deleted successfully")
        
        return success_response(
            data={"deleted": True, "policy_id": payment_policy_id},
            message=f"Payment policy {payment_policy_id} deleted successfully"
        ).to_json_string()
        
    except EbayApiError as e:
        # Log comprehensive error details
        await ctx.error(f"eBay API error: {e.get_comprehensive_message()}")
        
        # Handle special cases
        if e.status_code == 404:
            return error_response(
                ErrorCode.RESOURCE_NOT_FOUND,
                f"Payment policy {payment_policy_id} not found",
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
        await ctx.error(f"Failed to delete payment policy: {str(e)}")
        return error_response(
            ErrorCode.INTERNAL_ERROR,
            f"Failed to delete payment policy: {str(e)}"
        ).to_json_string()
    finally:
        await rest_client.close()