"""
eBay Account Programs API tools for managing seller program enrollment.

This module provides MCP tools for managing seller enrollment in various 
eBay programs like Out of Stock Control, Partner Motors Dealer, and 
Selling Policy Management.

IMPLEMENTATION FOLLOWS: PYDANTIC-FIRST DEVELOPMENT METHODOLOGY
- All API fields included exactly as documented
- Strong typing with enums throughout
- Validation through Pydantic models only
- Zero manual validation code

API Documentation: https://developer.ebay.com/api-docs/sell/account/resources/methods#h2-program
OAuth Scope Required: https://api.ebay.com/oauth/api_scope/sell.account
"""
from typing import List, Optional
from fastmcp import Context
from pydantic import BaseModel, Field, field_validator, ConfigDict

from api.oauth import OAuthManager, OAuthConfig, ConsentRequiredException
from api.rest_client import EbayRestClient, RestConfig
from api.errors import EbayApiError, extract_ebay_error_details
from models.enums import ProgramTypeEnum
from data_types import success_response, error_response, ErrorCode
from lootly_server import mcp


# PYDANTIC MODELS - API Documentation → Pydantic Models → MCP Tools


class Program(BaseModel):
    """Represents an eBay seller program."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    program_type: ProgramTypeEnum = Field(
        ..., 
        alias="programType",
        description="Type of the eBay program"
    )


class ProgramsResponse(BaseModel):
    """Response model for getting opted-in programs."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    programs: List[Program] = Field(
        default_factory=list,
        description="List of programs the seller has opted into"
    )


class OptInOutInput(BaseModel):
    """Input validation for opt-in/opt-out operations."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    program_type: ProgramTypeEnum = Field(
        ...,
        description="Type of program to opt in/out of"
    )


# MCP TOOLS - Pydantic Models → MCP Tools → API Integration


@mcp.tool
async def get_opted_in_programs(ctx: Context) -> str:
    """
    Get all programs the seller has opted into.
    
    Returns a list of eBay programs that the seller is currently enrolled in,
    such as Out of Stock Control, Partner Motors Dealer, or Selling Policy 
    Management.
    
    Args:
        ctx: MCP context
    
    Returns:
        JSON response with list of opted-in programs
    """
    await ctx.info("Getting seller's opted-in programs")
    
    # Check credentials
    if not mcp.config.app_id or not mcp.config.cert_id:
        return error_response(
            ErrorCode.CONFIGURATION_ERROR,
            "eBay API credentials required for program management"
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
        await ctx.info("Fetching opted-in programs from eBay API")
        
        # Make API request - using user token
        response = await rest_client.get(
            "/sell/account/v1/program/get_opted_in_programs"
        )
        response_body = response["body"]
        
        # Parse response with Pydantic model
        programs_data = ProgramsResponse(**response_body)
        
        # Convert to response format
        result = {
            "programs": [
                {
                    "program_type": program.program_type.value,
                    "description": ProgramTypeEnum.get_description(program.program_type.value)
                }
                for program in programs_data.programs
            ],
            "total_programs": len(programs_data.programs)
        }
        
        await ctx.info(f"Found {len(programs_data.programs)} opted-in programs")
        
        return success_response(
            data=result,
            message=f"Found {len(programs_data.programs)} opted-in programs"
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
        await ctx.error(f"Failed to get opted-in programs: {str(e)}")
        return error_response(
            ErrorCode.INTERNAL_ERROR,
            f"Failed to get opted-in programs: {str(e)}"
        ).to_json_string()
    finally:
        await rest_client.close()


@mcp.tool
async def opt_in_to_program(
    ctx: Context,
    program_type: ProgramTypeEnum
) -> str:
    """
    Opt into an eBay seller program.
    
    Enrolls the seller into the specified eBay program. Each program provides
    different benefits and features for sellers.
    
    Args:
        program_type: Type of program to opt into
        ctx: MCP context
    
    Returns:
        JSON response confirming opt-in status
    """
    await ctx.info(f"Opting into program: {program_type.value}")
    
    # Validate input
    try:
        input_data = OptInOutInput(program_type=program_type)
    except Exception as e:
        await ctx.error(f"Validation error: {str(e)}")
        return error_response(
            ErrorCode.VALIDATION_ERROR,
            str(e)
        ).to_json_string()
    
    # Check credentials
    if not mcp.config.app_id or not mcp.config.cert_id:
        return error_response(
            ErrorCode.CONFIGURATION_ERROR,
            "eBay API credentials required for program management"
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
        await ctx.info(f"Opting into {input_data.program_type.value} program")
        
        # Make API request - using user token
        # Note: opt_in_to_program is a POST with programType in body
        await rest_client.post(
            "/sell/account/v1/program/opt_in",
            json={"programType": input_data.program_type.value}
        )
        
        await ctx.info(f"Successfully opted into {input_data.program_type.value}")
        
        return success_response(
            data={
                "program_type": input_data.program_type.value,
                "description": ProgramTypeEnum.get_description(input_data.program_type.value),
                "status": "opted_in"
            },
            message=f"Successfully opted into {input_data.program_type.value} program"
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
        error_details["program_type"] = input_data.program_type.value
        
        return error_response(
            ErrorCode.EXTERNAL_API_ERROR,
            e.get_comprehensive_message(),
            error_details
        ).to_json_string()
    except Exception as e:
        await ctx.error(f"Failed to opt into program: {str(e)}")
        return error_response(
            ErrorCode.INTERNAL_ERROR,
            f"Failed to opt into program: {str(e)}"
        ).to_json_string()
    finally:
        await rest_client.close()


@mcp.tool
async def opt_out_of_program(
    ctx: Context,
    program_type: ProgramTypeEnum
) -> str:
    """
    Opt out of an eBay seller program.
    
    Removes the seller from the specified eBay program. The seller will no
    longer have access to the program's features and benefits.
    
    Args:
        program_type: Type of program to opt out of
        ctx: MCP context
    
    Returns:
        JSON response confirming opt-out status
    """
    await ctx.info(f"Opting out of program: {program_type.value}")
    
    # Validate input
    try:
        input_data = OptInOutInput(program_type=program_type)
    except Exception as e:
        await ctx.error(f"Validation error: {str(e)}")
        return error_response(
            ErrorCode.VALIDATION_ERROR,
            str(e)
        ).to_json_string()
    
    # Check credentials
    if not mcp.config.app_id or not mcp.config.cert_id:
        return error_response(
            ErrorCode.CONFIGURATION_ERROR,
            "eBay API credentials required for program management"
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
        await ctx.info(f"Opting out of {input_data.program_type.value} program")
        
        # Make API request - using user token
        # Note: opt_out_of_program is a POST with programType in body
        await rest_client.post(
            "/sell/account/v1/program/opt_out",
            json={"programType": input_data.program_type.value}
        )
        
        await ctx.info(f"Successfully opted out of {input_data.program_type.value}")
        
        return success_response(
            data={
                "program_type": input_data.program_type.value,
                "description": ProgramTypeEnum.get_description(input_data.program_type.value),
                "status": "opted_out"
            },
            message=f"Successfully opted out of {input_data.program_type.value} program"
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
        error_details["program_type"] = input_data.program_type.value
        
        return error_response(
            ErrorCode.EXTERNAL_API_ERROR,
            e.get_comprehensive_message(),
            error_details
        ).to_json_string()
    except Exception as e:
        await ctx.error(f"Failed to opt out of program: {str(e)}")
        return error_response(
            ErrorCode.INTERNAL_ERROR,
            f"Failed to opt out of program: {str(e)}"
        ).to_json_string()
    finally:
        await rest_client.close()