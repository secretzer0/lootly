"""
eBay Account API tools for business policies and seller account management.

Provides access to eBay's Account API for managing business policies,
rate tables, and seller account settings.
"""
from typing import Dict, Any, Optional, List
from fastmcp import Context
from pydantic import BaseModel, Field, field_validator, ConfigDict
from datetime import datetime

from api.oauth import OAuthManager, OAuthConfig, OAuthScopes
from api.rest_client import EbayRestClient, RestConfig
from api.errors import EbayApiError, ValidationError as ApiValidationError
from data_types import success_response, error_response, ErrorCode
from lootly_server import mcp
from tools.oauth_consent import get_user_access_token


async def _check_user_consent(ctx: Context) -> Optional[str]:
    """Check if user has valid consent and return access token."""
    if not mcp.config.app_id:
        return None
    
    user_token = await get_user_access_token(mcp.config.app_id)
    if not user_token:
        await ctx.info("⚠️  User consent required for Account API. Use check_user_consent_status and initiate_user_consent tools.")
        return None
    
    return user_token


class PolicySearchInput(BaseModel):
    """Input validation for policy search."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    policy_type: str = Field(..., description="Type of policy to search for")
    marketplace_id: str = Field(default="EBAY_US", description="Marketplace ID")
    
    @field_validator('policy_type')
    @classmethod
    def validate_policy_type(cls, v):
        valid_types = ["PAYMENT", "RETURN", "SHIPPING", "FULFILLMENT"]
        if v not in valid_types:
            raise ValueError(f"Policy type must be one of: {', '.join(valid_types)}")
        return v


class RateTableInput(BaseModel):
    """Input validation for rate table operations."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    country_code: str = Field(..., description="Country code (e.g., US, GB)")
    
    @field_validator('country_code')
    @classmethod
    def validate_country_code(cls, v):
        if len(v) != 2:
            raise ValueError("Country code must be 2 characters")
        return v.upper()


# Static fallback data for policies
STATIC_POLICIES = {
    "PAYMENT": [
        {
            "paymentPolicyId": "static_payment_001",
            "name": "Standard Payment Policy",
            "description": "Accept PayPal, Credit Cards, and other standard payment methods",
            "marketplaceId": "EBAY_US",
            "categoryTypes": [{"name": "ALL_EXCLUDING_MOTORS_VEHICLES"}],
            "paymentMethods": [
                {"paymentMethodType": "PAYPAL", "brands": ["PAYPAL"]},
                {"paymentMethodType": "CREDIT_CARD", "brands": ["VISA", "MASTERCARD", "AMEX", "DISCOVER"]}
            ],
            "immediatePayRequired": False
        }
    ],
    "RETURN": [
        {
            "returnPolicyId": "static_return_001",
            "name": "30-Day Return Policy",
            "description": "30-day return policy with buyer pays return shipping",
            "marketplaceId": "EBAY_US",
            "categoryTypes": [{"name": "ALL_EXCLUDING_MOTORS_VEHICLES"}],
            "returnsAccepted": True,
            "returnPeriod": {"value": 30, "unit": "DAY"},
            "returnShippingCostPayer": "BUYER",
            "returnMethod": "REPLACEMENT_OR_EXCHANGE"
        }
    ],
    "SHIPPING": [
        {
            "shippingPolicyId": "static_shipping_001",
            "name": "Standard Shipping Policy",
            "description": "Standard shipping with calculated rates",
            "marketplaceId": "EBAY_US",
            "categoryTypes": [{"name": "ALL_EXCLUDING_MOTORS_VEHICLES"}],
            "shippingOptions": [
                {
                    "optionType": "DOMESTIC",
                    "shippingServices": [
                        {
                            "sortOrderId": 1,
                            "shippingServiceCode": "USPSGround",
                            "shippingCarrierCode": "USPS",
                            "shippingServiceName": "USPS Ground Advantage",
                            "shippingCost": {"value": "8.95", "currency": "USD"},
                            "additionalShippingCost": {"value": "2.00", "currency": "USD"}
                        }
                    ]
                }
            ]
        }
    ],
    "FULFILLMENT": [
        {
            "fulfillmentPolicyId": "static_fulfillment_001",
            "name": "Standard Fulfillment Policy",
            "description": "1-day handling time with tracking",
            "marketplaceId": "EBAY_US",
            "categoryTypes": [{"name": "ALL_EXCLUDING_MOTORS_VEHICLES"}],
            "handlingTime": {"value": 1, "unit": "DAY"},
            "shipToLocations": {
                "regionIncluded": [{"regionName": "DOMESTIC"}]
            },
            "globalShipping": False,
            "pickupDropOff": False
        }
    ]
}


def _convert_policy(policy: Dict[str, Any]) -> Dict[str, Any]:
    """Convert API policy data to our format."""
    return {
        "policy_id": policy.get("paymentPolicyId") or policy.get("returnPolicyId") or 
                    policy.get("shippingPolicyId") or policy.get("fulfillmentPolicyId"),
        "name": policy.get("name"),
        "description": policy.get("description"),
        "marketplace_id": policy.get("marketplaceId"),
        "category_types": policy.get("categoryTypes", []),
        "policy_data": policy,
        "created_date": policy.get("createdDate"),
        "last_modified_date": policy.get("lastModifiedDate")
    }


def _convert_rate_table(rate_table: Dict[str, Any]) -> Dict[str, Any]:
    """Convert API rate table data to our format."""
    return {
        "rate_table_id": rate_table.get("rateTableId"),
        "name": rate_table.get("name"),
        "description": rate_table.get("description"),
        "country_code": rate_table.get("countryCode"),
        "locality": rate_table.get("locality"),
        "rate_table_type": rate_table.get("rateTableType"),
        "shipping_services": rate_table.get("shippingServices", []),
        "created_date": rate_table.get("createdDate"),
        "last_modified_date": rate_table.get("lastModifiedDate")
    }


@mcp.tool
async def get_business_policies(
    ctx: Context,
    policy_type: str,
    marketplace_id: str = "EBAY_US"
) -> str:
    """
    Get business policies for a seller account.
    
    Retrieves payment, return, shipping, or fulfillment policies
    that can be applied to listings.
    
    Args:
        policy_type: Type of policy (PAYMENT, RETURN, SHIPPING, FULFILLMENT)
        marketplace_id: Marketplace ID (default: EBAY_US)
        ctx: MCP context
    
    Returns:
        JSON response with business policies
    """
    await ctx.info(f"Getting {policy_type} policies for {marketplace_id}")
    await ctx.report_progress(0.1, "Validating policy parameters...")
    
    # Check credentials
    if not mcp.config.app_id or not mcp.config.cert_id:
        await ctx.info("Using static policy data - set credentials for live policies")
        
        # Return static policies
        policies = STATIC_POLICIES.get(policy_type, [])
        
        return success_response(
            data={
                "policies": policies,
                "total_policies": len(policies),
                "policy_type": policy_type,
                "marketplace_id": marketplace_id,
                "data_source": "static_fallback",
                "note": "Live policy data requires eBay API credentials"
            },
            message=f"Found {len(policies)} {policy_type} policies (static data)"
        ).to_json_string()
    
    # Check user consent
    user_token = await _check_user_consent(ctx)
    if not user_token:
        return error_response(
            ErrorCode.AUTHENTICATION_ERROR,
            "User consent required for Account API. Use initiate_user_consent to authorize access.",
            {"required_scopes": OAuthScopes.USER_CONSENT_SCOPES.split()}
        ).to_json_string()
    
    # Validate input
    try:
        input_data = PolicySearchInput(
            policy_type=policy_type,
            marketplace_id=marketplace_id
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
        await ctx.report_progress(0.3, f"Fetching {policy_type} policies...")
        
        # Build endpoint based on policy type
        endpoint_map = {
            "PAYMENT": "/sell/account/v1/payment_policy",
            "RETURN": "/sell/account/v1/return_policy",
            "SHIPPING": "/sell/account/v1/shipping_policy",
            "FULFILLMENT": "/sell/account/v1/fulfillment_policy"
        }
        
        endpoint = endpoint_map.get(input_data.policy_type)
        if not endpoint:
            return error_response(
                ErrorCode.VALIDATION_ERROR,
                f"Unsupported policy type: {input_data.policy_type}"
            ).to_json_string()
        
        # Make API request
        response = await rest_client.get(
            endpoint,
            params={"marketplace_id": input_data.marketplace_id},
            scope=OAuthScopes.SELL_ACCOUNT
        )
        
        await ctx.report_progress(0.8, "Processing policy data...")
        
        # Parse response - different policy types have different response structures
        policies = []
        policy_key_map = {
            "PAYMENT": "paymentPolicies",
            "RETURN": "returnPolicies", 
            "SHIPPING": "shippingPolicies",
            "FULFILLMENT": "fulfillmentPolicies"
        }
        
        policy_list = response.get(policy_key_map[input_data.policy_type], [])
        
        for policy in policy_list:
            try:
                converted_policy = _convert_policy(policy)
                policies.append(converted_policy)
            except Exception as e:
                await ctx.error(f"Error parsing policy: {str(e)}")
                continue
        
        await ctx.report_progress(1.0, "Complete")
        await ctx.info(f"Found {len(policies)} {policy_type} policies")
        
        return success_response(
            data={
                "policies": policies,
                "total_policies": len(policies),
                "policy_type": input_data.policy_type,
                "marketplace_id": input_data.marketplace_id,
                "data_source": "live_api"
            },
            message=f"Found {len(policies)} {policy_type} policies"
        ).to_json_string()
        
    except EbayApiError as e:
        await ctx.error(f"eBay API error: {str(e)}")
        return error_response(
            ErrorCode.EXTERNAL_API_ERROR,
            str(e),
            {"status_code": e.status_code, "policy_type": policy_type}
        ).to_json_string()
    except Exception as e:
        await ctx.error(f"Failed to get policies: {str(e)}")
        return error_response(
            ErrorCode.INTERNAL_ERROR,
            f"Failed to get business policies: {str(e)}"
        ).to_json_string()
    finally:
        await rest_client.close()


@mcp.tool
async def get_rate_tables(
    ctx: Context,
    country_code: str = "US"
) -> str:
    """
    Get shipping rate tables for a seller account.
    
    Retrieves rate tables that can be used in shipping policies
    for calculated shipping costs.
    
    Args:
        country_code: Country code for rate tables (default: US)
        ctx: MCP context
    
    Returns:
        JSON response with rate tables
    """
    await ctx.info(f"Getting rate tables for country: {country_code}")
    await ctx.report_progress(0.1, "Validating parameters...")
    
    # Check credentials
    if not mcp.config.app_id or not mcp.config.cert_id:
        await ctx.info("Using static rate table data - set credentials for live data")
        
        # Return static rate table
        rate_tables = [
            {
                "rate_table_id": "static_rate_001",
                "name": "Standard US Shipping Rates",
                "description": "Standard rate table for US domestic shipping",
                "country_code": "US",
                "locality": "DOMESTIC",
                "rate_table_type": "SHIPPING",
                "shipping_services": [
                    {
                        "shipping_service_code": "USPSGround",
                        "shipping_carrier_code": "USPS",
                        "base_shipping_cost": {"value": "8.95", "currency": "USD"},
                        "additional_shipping_cost": {"value": "2.00", "currency": "USD"}
                    }
                ]
            }
        ]
        
        return success_response(
            data={
                "rate_tables": rate_tables,
                "total_rate_tables": len(rate_tables),
                "country_code": country_code,
                "data_source": "static_fallback",
                "note": "Live rate table data requires eBay API credentials"
            },
            message=f"Found {len(rate_tables)} rate tables (static data)"
        ).to_json_string()
    
    # Check user consent
    user_token = await _check_user_consent(ctx)
    if not user_token:
        return error_response(
            ErrorCode.AUTHENTICATION_ERROR,
            "User consent required for Account API. Use initiate_user_consent to authorize access.",
            {"required_scopes": OAuthScopes.USER_CONSENT_SCOPES.split()}
        ).to_json_string()
    
    # Validate input
    try:
        input_data = RateTableInput(country_code=country_code)
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
        await ctx.report_progress(0.3, "Fetching rate tables...")
        
        # Make API request
        response = await rest_client.get(
            "/sell/account/v1/rate_table",
            params={"country_code": input_data.country_code},
            scope=OAuthScopes.SELL_ACCOUNT
        )
        
        await ctx.report_progress(0.8, "Processing rate table data...")
        
        # Parse response
        rate_tables = []
        for rate_table in response.get("rateTables", []):
            try:
                converted_table = _convert_rate_table(rate_table)
                rate_tables.append(converted_table)
            except Exception as e:
                await ctx.error(f"Error parsing rate table: {str(e)}")
                continue
        
        await ctx.report_progress(1.0, "Complete")
        await ctx.info(f"Found {len(rate_tables)} rate tables")
        
        return success_response(
            data={
                "rate_tables": rate_tables,
                "total_rate_tables": len(rate_tables),
                "country_code": input_data.country_code,
                "data_source": "live_api"
            },
            message=f"Found {len(rate_tables)} rate tables"
        ).to_json_string()
        
    except EbayApiError as e:
        await ctx.error(f"eBay API error: {str(e)}")
        return error_response(
            ErrorCode.EXTERNAL_API_ERROR,
            str(e),
            {"status_code": e.status_code, "country_code": country_code}
        ).to_json_string()
    except Exception as e:
        await ctx.error(f"Failed to get rate tables: {str(e)}")
        return error_response(
            ErrorCode.INTERNAL_ERROR,
            f"Failed to get rate tables: {str(e)}"
        ).to_json_string()
    finally:
        await rest_client.close()


@mcp.tool
async def get_seller_standards(
    ctx: Context,
    marketplace_id: str = "EBAY_US"
) -> str:
    """
    Get seller standards and performance metrics.
    
    Retrieves seller performance data including defect rates,
    late shipment rates, and seller level information.
    
    Args:
        marketplace_id: Marketplace ID (default: EBAY_US)
        ctx: MCP context
    
    Returns:
        JSON response with seller standards
    """
    await ctx.info(f"Getting seller standards for {marketplace_id}")
    
    # Check credentials
    if not mcp.config.app_id or not mcp.config.cert_id:
        await ctx.info("Using static seller standards - set credentials for live data")
        
        # Return static seller standards
        standards = {
            "marketplace_id": marketplace_id,
            "seller_level": "ABOVE_STANDARD",
            "defect_rate": {"value": 0.5, "threshold": 2.0},
            "late_shipment_rate": {"value": 1.2, "threshold": 3.0},
            "cases_not_resolved": {"value": 0.3, "threshold": 0.5},
            "evaluation_date": "2024-01-15T00:00:00Z",
            "next_evaluation_date": "2024-04-15T00:00:00Z"
        }
        
        return success_response(
            data={
                "seller_standards": standards,
                "data_source": "static_fallback",
                "note": "Live seller standards require eBay API credentials"
            },
            message="Seller standards retrieved (static data)"
        ).to_json_string()
    
    # Check user consent
    user_token = await _check_user_consent(ctx)
    if not user_token:
        return error_response(
            ErrorCode.AUTHENTICATION_ERROR,
            "User consent required for Account API. Use initiate_user_consent to authorize access.",
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
        await ctx.report_progress(0.3, "Fetching seller standards...")
        
        # Make API request
        response = await rest_client.get(
            "/sell/account/v1/seller_standards_profile",
            params={"marketplace_id": marketplace_id},
            scope=OAuthScopes.SELL_ACCOUNT
        )
        
        await ctx.report_progress(0.8, "Processing seller standards...")
        
        # Parse response
        standards = {
            "marketplace_id": marketplace_id,
            "seller_level": response.get("sellerLevel"),
            "defect_rate": response.get("defectRate", {}),
            "late_shipment_rate": response.get("lateShipmentRate", {}),
            "cases_not_resolved": response.get("casesNotResolved", {}),
            "evaluation_date": response.get("evaluationDate"),
            "next_evaluation_date": response.get("nextEvaluationDate"),
            "data_source": "live_api"
        }
        
        await ctx.report_progress(1.0, "Complete")
        await ctx.info(f"Retrieved seller standards: {standards['seller_level']}")
        
        return success_response(
            data={
                "seller_standards": standards,
                "data_source": "live_api"
            },
            message="Seller standards retrieved successfully"
        ).to_json_string()
        
    except EbayApiError as e:
        await ctx.error(f"eBay API error: {str(e)}")
        return error_response(
            ErrorCode.EXTERNAL_API_ERROR,
            str(e),
            {"status_code": e.status_code, "marketplace_id": marketplace_id}
        ).to_json_string()
    except Exception as e:
        await ctx.error(f"Failed to get seller standards: {str(e)}")
        return error_response(
            ErrorCode.INTERNAL_ERROR,
            f"Failed to get seller standards: {str(e)}"
        ).to_json_string()
    finally:
        await rest_client.close()