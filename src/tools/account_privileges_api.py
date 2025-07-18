"""
eBay Account Privileges API tools for managing seller account privileges.

This module provides MCP tools for retrieving seller account privileges and 
selling limits from eBay. It shows registration status and monthly selling 
limits for the seller account.

IMPLEMENTATION FOLLOWS: PYDANTIC-FIRST DEVELOPMENT METHODOLOGY
- All API fields included exactly as documented
- Strong typing with enums throughout
- Validation through Pydantic models only
- Zero manual validation code

API Documentation: https://developer.ebay.com/api-docs/sell/account/resources/methods#h2-privilege
OAuth Scope Required: https://api.ebay.com/oauth/api_scope/sell.account
"""
from typing import Optional
from fastmcp import Context
from pydantic import BaseModel, Field, ConfigDict

from api.oauth import OAuthManager, OAuthConfig, ConsentRequiredException
from api.rest_client import EbayRestClient, RestConfig
from api.errors import EbayApiError
from api.ebay_enums import CurrencyCodeEnum
from data_types import success_response, error_response, ErrorCode
from lootly_server import mcp


# PYDANTIC MODELS - API Documentation → Pydantic Models → MCP Tools


class Amount(BaseModel):
    """Monetary amount with currency."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    currency: CurrencyCodeEnum = Field(..., description="3-letter ISO 4217 currency code")
    value: str = Field(..., description="Amount value as a string")


class SellingLimit(BaseModel):
    """Monthly selling limits for the seller account."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    amount: Optional[Amount] = Field(None, description="Monthly sales amount limit")
    quantity: Optional[int] = Field(None, description="Monthly quantity limit")


class PrivilegesResponse(BaseModel):
    """Response model for get privileges API."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    seller_registration_completed: bool = Field(
        ..., 
        alias="sellerRegistrationCompleted",
        description="Whether seller registration is complete"
    )
    selling_limit: Optional[SellingLimit] = Field(
        None, 
        alias="sellingLimit",
        description="Monthly selling limits"
    )


# MCP TOOLS - Pydantic Models → MCP Tools → API Integration


@mcp.tool
async def get_privileges(ctx: Context) -> str:
    """
    Get seller account privileges and selling limits.
    
    Retrieves the current set of privileges for the seller account, including
    registration status and monthly selling limits (quantity and value).
    
    Args:
        ctx: MCP context
    
    Returns:
        JSON response with seller privileges and limits
    """
    await ctx.info("Getting seller account privileges")
    
    # Check credentials
    if not mcp.config.app_id or not mcp.config.cert_id:
        return error_response(
            ErrorCode.CONFIGURATION_ERROR,
            "eBay API credentials required for account privileges"
        ).to_json_string()
    
    # Initialize API clients
    oauth_config = OAuthConfig(
        client_id=mcp.config.app_id,
        client_secret=mcp.config.cert_id,
        redirect_uri=mcp.config.redirect_uri,
        sandbox=mcp.config.sandbox_mode
    )
    oauth_manager = OAuthManager(oauth_config)
    
    rest_config = RestConfig(
        sandbox=mcp.config.sandbox_mode,
        rate_limit_per_day=mcp.config.rate_limit_per_day
    )
    rest_client = EbayRestClient(oauth_manager, rest_config)
    
    try:
        await ctx.info("Fetching account privileges from eBay API")
        
        # Make API request - using user token
        response = await rest_client.get(
            "/sell/account/v1/privilege"
        )
        
        # Parse response with Pydantic model
        privileges_data = PrivilegesResponse(**response)
        
        # Convert to response format
        result = {
            "seller_registration_completed": privileges_data.seller_registration_completed,
            "selling_limit": None
        }
        
        if privileges_data.selling_limit:
            result["selling_limit"] = {}
            if privileges_data.selling_limit.amount:
                result["selling_limit"]["amount"] = {
                    "currency": privileges_data.selling_limit.amount.currency.value,
                    "value": privileges_data.selling_limit.amount.value
                }
            if privileges_data.selling_limit.quantity is not None:
                result["selling_limit"]["quantity"] = privileges_data.selling_limit.quantity
        
        await ctx.info("Successfully retrieved account privileges")
        
        return success_response(
            data=result,
            message="Successfully retrieved seller account privileges"
        ).to_json_string()
        
    except ConsentRequiredException as e:
        await ctx.error(f"User consent required: {str(e)}")
        return error_response(
            ErrorCode.CONSENT_REQUIRED,
            str(e),
            {"required_scopes": e.scopes, "auth_url": e.auth_url}
        ).to_json_string()
    except EbayApiError as e:
        await ctx.error(f"eBay API error: {e.get_comprehensive_message()}")
        error_details = e.get_full_error_details()
        
        return error_response(
            ErrorCode.EXTERNAL_API_ERROR,
            e.get_comprehensive_message(),
            error_details
        ).to_json_string()
    except Exception as e:
        await ctx.error(f"Failed to get account privileges: {str(e)}")
        return error_response(
            ErrorCode.INTERNAL_ERROR,
            f"Failed to get account privileges: {str(e)}"
        ).to_json_string()
    finally:
        await rest_client.close()