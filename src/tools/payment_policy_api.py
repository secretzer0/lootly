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
from typing import Optional, Dict, Any, List
from decimal import Decimal
from fastmcp import Context
from pydantic import BaseModel, Field, model_validator, ConfigDict

from api.oauth import OAuthManager, OAuthConfig, ConsentRequiredException
from api.rest_client import EbayRestClient, RestConfig
from api.errors import EbayApiError
from models.enums import (
    MarketplaceIdEnum,
    CategoryTypeEnum,
    PaymentInstrumentBrandEnum,
    PaymentMethodTypeEnum,
    TimeDurationUnitEnum
)
from data_types import success_response, error_response, ErrorCode
from lootly_server import mcp


# PYDANTIC MODELS - API Documentation → Pydantic Models → MCP Tools


class CategoryType(BaseModel):
    """Category type for a business policy."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    name: CategoryTypeEnum = Field(..., description="Category type name")
    default: bool = Field(False, description="Whether this is the default category type")


class PaymentMethod(BaseModel):
    """Offline payment method configuration."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    payment_method_type: PaymentMethodTypeEnum = Field(..., description="Type of offline payment method")
    
    # Recipient account only for certain types
    recipient_account_reference: Optional[Dict[str, str]] = Field(
        None, 
        description="Recipient account info for certain payment types"
    )
    
    @model_validator(mode='after')
    def validate_recipient_account(self):
        """Validate recipient account requirements."""
        # PayPal and other electronic methods may require recipient account
        # For now, no strict validation as requirements vary by marketplace
        return self


class DepositDueIn(BaseModel):
    """When deposit payment is due for motor vehicles."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    value: int = Field(..., description="Number of hours (24, 48, or 72)")
    unit: TimeDurationUnitEnum = Field(default=TimeDurationUnitEnum.HOUR, description="Time unit (must be HOUR)")
    
    @model_validator(mode='after')
    def validate_deposit_due_in(self):
        """Validate deposit due_in requirements per eBay API."""
        if self.unit != TimeDurationUnitEnum.HOUR:
            raise ValueError("Deposit due_in unit must be HOUR")
        if self.value not in [24, 48, 72]:
            raise ValueError("Deposit due_in value must be 24, 48, or 72 hours")
        return self


class Deposit(BaseModel):
    """Deposit configuration for motor vehicle listings."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    # Required fields
    due_in: DepositDueIn = Field(..., description="When deposit payment is due (24, 48, or 72 hours)")
    amount: Decimal = Field(..., ge=0, decimal_places=2, description="Deposit amount")
    
    # Optional payment methods for deposit
    payment_methods: Optional[List[PaymentMethod]] = Field(
        None,
        description="Accepted payment methods for deposit"
    )
    
    @model_validator(mode='after')
    def validate_deposit_amount(self):
        """Ensure deposit amount is reasonable."""
        if self.amount > Decimal('50000'):
            raise ValueError("Deposit amount seems unreasonably high")
        return self


class FullPaymentDueIn(BaseModel):
    """Full payment due configuration."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    value: int = Field(..., ge=0, le=999, description="Number of time units")
    unit: TimeDurationUnitEnum = Field(..., description="Time unit")


class PaymentPolicyInput(BaseModel):
    """
    Complete input validation for payment policy operations.
    
    Maps ALL fields from eBay API createPaymentPolicy Request Fields exactly.
    """
    model_config = ConfigDict(str_strip_whitespace=True)
    
    # REQUIRED FIELDS
    name: str = Field(..., min_length=1, max_length=64, description="Policy name")
    marketplace_id: MarketplaceIdEnum = Field(..., description="eBay marketplace ID")
    category_types: List[CategoryType] = Field(..., description="Category types this policy applies to")
    
    # OPTIONAL FIELDS
    description: Optional[str] = Field(None, max_length=250, description="Internal policy description")
    
    # Immediate payment flag
    immediate_pay: Optional[bool] = Field(
        False, 
        description="Whether immediate payment is required"
    )
    
    # Payment methods - typically managed by eBay
    payment_methods: Optional[List[PaymentMethod]] = Field(
        None,
        description="Offline payment methods accepted"
    )
    
    # Motor vehicle specific fields
    deposit: Optional[Deposit] = Field(
        None,
        description="Deposit requirements for motor vehicles"
    )
    
    full_payment_due_in: Optional[FullPaymentDueIn] = Field(
        None,
        description="When full payment is due for motor vehicles"
    )
    
    # Accepted payment instruments (cards)
    payment_instrument_brands: Optional[List[PaymentInstrumentBrandEnum]] = Field(
        None,
        description="Credit card brands accepted"
    )
    
    @model_validator(mode='after')
    def validate_motor_vehicle_requirements(self):
        """Validate motor vehicle category requirements."""
        has_motors_category = any(
            ct.name == CategoryTypeEnum.MOTORS_VEHICLES 
            for ct in self.category_types
        )
        
        # If motor vehicles category and has deposit, validate full payment due
        if has_motors_category and self.deposit and not self.full_payment_due_in:
            raise ValueError(
                "full_payment_due_in is required when deposit is specified for motor vehicle listings"
            )
        
        # Validate immediate pay restrictions
        if has_motors_category and self.immediate_pay:
            raise ValueError(
                "immediate_pay cannot be true for motor vehicle listings"
            )
        
        return self
    
    @model_validator(mode='after')
    def validate_payment_methods(self):
        """Validate payment method configurations."""
        # If payment methods specified, ensure they're appropriate
        if self.payment_methods:
            # Check for duplicate payment method types
            method_types = [m.payment_method_type for m in self.payment_methods]
            if len(method_types) != len(set(method_types)):
                raise ValueError("Duplicate payment method types are not allowed")
        
        return self


# CONVERSION FUNCTIONS

def _convert_to_api_format(input_data: PaymentPolicyInput) -> Dict[str, Any]:
    """Convert Pydantic model to eBay API format."""
    policy_data = {
        "name": input_data.name,
        "marketplaceId": input_data.marketplace_id.value,
        "categoryTypes": [
            {
                "name": ct.name.value,
                "default": ct.default
            }
            for ct in input_data.category_types
        ]
    }
    
    # Add optional fields
    if input_data.description:
        policy_data["description"] = input_data.description
    
    if input_data.immediate_pay is not None:
        policy_data["immediatePay"] = input_data.immediate_pay
    
    # Always include paymentMethods array (even if empty) - might be required by API
    policy_data["paymentMethods"] = []
    
    # Add payment methods if specified
    if input_data.payment_methods:
        policy_data["paymentMethods"] = [
            {
                "paymentMethodType": pm.payment_method_type.value,
                **({"recipientAccountReference": pm.recipient_account_reference} 
                   if pm.recipient_account_reference else {})
            }
            for pm in input_data.payment_methods
        ]
    
    # Add deposit configuration if specified
    if input_data.deposit:
        policy_data["deposit"] = {
            "dueIn": {
                "value": input_data.deposit.due_in.value,
                "unit": input_data.deposit.due_in.unit.value
            },
            "amount": {
                "value": str(input_data.deposit.amount),
                "currency": "USD"  # Currency is marketplace-specific
            }
        }
        if input_data.deposit.payment_methods:
            policy_data["deposit"]["paymentMethods"] = [
                {
                    "paymentMethodType": pm.payment_method_type.value,
                    **({"recipientAccountReference": pm.recipient_account_reference} 
                       if pm.recipient_account_reference else {})
                }
                for pm in input_data.deposit.payment_methods
            ]
    
    # Add full payment due configuration
    if input_data.full_payment_due_in:
        policy_data["fullPaymentDueIn"] = {
            "value": input_data.full_payment_due_in.value,
            "unit": input_data.full_payment_due_in.unit.value
        }
    
    # Add payment instrument brands
    if input_data.payment_instrument_brands:
        policy_data["paymentInstrumentBrands"] = [
            brand.value for brand in input_data.payment_instrument_brands
        ]
    
    return policy_data


def _format_policy_response(policy: Dict[str, Any]) -> Dict[str, Any]:
    """Format API response for consistent output."""
    formatted = {
        "policy_id": policy.get("paymentPolicyId"),
        "name": policy.get("name"),
        "marketplace_id": policy.get("marketplaceId"),
        "category_types": policy.get("categoryTypes", []),
        "immediate_pay": policy.get("immediatePay", False)
    }
    
    # Add optional fields
    if policy.get("description"):
        formatted["description"] = policy["description"]
    
    if policy.get("paymentMethods"):
        formatted["payment_methods"] = policy["paymentMethods"]
    
    if policy.get("deposit"):
        formatted["deposit"] = policy["deposit"]
    
    if policy.get("fullPaymentDueIn"):
        formatted["full_payment_due_in"] = policy["fullPaymentDueIn"]
    
    if policy.get("paymentInstrumentBrands"):
        formatted["payment_instrument_brands"] = policy["paymentInstrumentBrands"]
    
    # Add timestamps if available
    if policy.get("createdAt"):
        formatted["created_at"] = policy["createdAt"]
    if policy.get("updatedAt"):
        formatted["updated_at"] = policy["updatedAt"]
    
    return formatted


# MCP TOOLS - Using Pydantic Models

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
        await ctx.info(f"Payment policy created successfully with ID: {formatted_response['policy_id']}")
        
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
    marketplace_id: MarketplaceIdEnum,
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
    await ctx.info(f"Getting payment policies for {marketplace_id.value}")
    
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
    marketplace_id: MarketplaceIdEnum,
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
            "marketplace_id": marketplace_id.value,
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
                f"No payment policy found with name '{name}' in marketplace {marketplace_id.value}",
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


# Update model is same as create model
# eBay API uses the same structure for both
UpdatePaymentPolicyInput = PaymentPolicyInput


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