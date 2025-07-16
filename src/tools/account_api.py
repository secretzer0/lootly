"""
eBay Account API tools for seller account management.

Provides access to eBay's Account API for managing seller account settings,
rate tables, and seller standards.
"""
from typing import Optional
from fastmcp import Context

from api.oauth import OAuthManager, OAuthConfig, OAuthScopes
from api.rest_client import EbayRestClient, RestConfig
from api.errors import EbayApiError
from api.sandbox_retry import with_sandbox_retry, RetryConfig
from data_types import success_response, error_response, ErrorCode
from lootly_server import mcp
from tools.oauth_consent import get_user_access_token
from tools.tests.test_data import TestDataGood


async def _check_user_consent(ctx: Context) -> Optional[str]:
    """Check if user has valid consent and return access token."""
    if not mcp.config.app_id:
        return None
    
    user_token = await get_user_access_token(mcp.config.app_id)
    if not user_token:
        await ctx.info("⚠️  User consent required for Account API. Use check_user_consent_status and initiate_user_consent tools.")
        return None
    
    return user_token


@mcp.tool
async def get_seller_standards(
    ctx: Context,
    program: str = "PROGRAM_US",
    cycle: str = "CURRENT"
) -> str:
    """
    Get seller standards and performance metrics using Analytics API.
    
    Retrieves seller performance data including defect rates,
    late shipment rates, and seller level information from the Analytics API.
    
    Args:
        program: Seller standards program (PROGRAM_US, PROGRAM_UK, PROGRAM_DE, PROGRAM_GLOBAL)
        cycle: Evaluation cycle (CURRENT, PROJECTED)
        ctx: MCP context
    
    Returns:
        JSON response with seller standards
    """
    await ctx.info(f"Getting seller standards for program: {program}, cycle: {cycle}")
    
    # Check credentials
    if not mcp.config.app_id or not mcp.config.cert_id:
        await ctx.info("Using static seller standards - set credentials for live data")
        
        # Return static seller standards from test_data.py
        test_data = TestDataGood.SELLER_STANDARDS_RESPONSE
        
        # Extract seller level - now from 'standardsLevel' field
        seller_level = test_data.get("standardsLevel")
        if not seller_level and test_data.get("metrics"):
            for metric in test_data.get("metrics", []):
                if metric.get("level"):
                    seller_level = metric.get("level")
                    break
        
        # Extract cycle info
        cycle_info = test_data.get("cycle", {})
        cycle_type = cycle_info.get("cycleType", cycle) if isinstance(cycle_info, dict) else cycle
        evaluation_date = cycle_info.get("evaluationDate") if isinstance(cycle_info, dict) else None
        
        # Extract rate metrics from the metrics array
        defect_rate = {}
        late_shipment_rate = {}
        cases_not_resolved = {}
        
        for metric in test_data.get("metrics", []):
            if metric.get("metricKey") == "DEFECTIVE_TRANSACTION_RATE":
                defect_rate = metric.get("value", {})
            elif metric.get("metricKey") == "SHIPPING_MISS_RATE":
                late_shipment_rate = metric.get("value", {})
            elif metric.get("metricKey") == "CLAIMS_SAF_RATE":
                cases_not_resolved = metric.get("value", {})
        
        standards = {
            "program": test_data.get("program", program),
            "cycle": cycle_type,
            "seller_level": seller_level,
            "defect_rate": defect_rate,
            "late_shipment_rate": late_shipment_rate,
            "cases_not_resolved": cases_not_resolved,
            "evaluation_date": evaluation_date,
            "next_evaluation_date": test_data.get("nextEvaluationDate"),
            "metrics": test_data.get("metrics", [])
        }
        
        return success_response(
            data={
                "seller_standards": standards,
                "data_source": "static_fallback",
                "note": "Live seller standards require eBay API credentials"
            },
            message="Seller standards retrieved (static data)"
        ).to_json_string()
    
    # Check user consent (now includes SELL_ANALYTICS scope in initial OAuth)
    user_token = await _check_user_consent(ctx)
    if not user_token:
        return error_response(
            ErrorCode.AUTHENTICATION_ERROR,
            "User consent required for Analytics API. Use initiate_user_consent to authorize access.",
            {"required_scopes": [OAuthScopes.SELL_ANALYTICS]}
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
        await ctx.report_progress(0.3, "Fetching seller standards from Analytics API...")
        
        # Define the API call function for retry logic
        async def make_seller_standards_request():
            return await rest_client.get(
                f"/sell/analytics/v1/seller_standards_profile/{program}/{cycle}",
                scope=OAuthScopes.SELL_ANALYTICS
            )
        
        # Execute with sandbox retry logic
        retry_config = RetryConfig(
            max_attempts=3,
            base_delay=1.5,  # Analytics API is usually more reliable
            max_delay=10.0
        )
        
        response = await with_sandbox_retry(
            make_seller_standards_request,
            ctx=ctx,
            retry_config=retry_config
        )
        
        await ctx.report_progress(0.8, "Processing seller standards...")
        
        # Parse response - Analytics API has different structure based on actual response
        # The API returns 'standardsLevel' not 'sellerLevel'
        seller_level = response.get("standardsLevel")
        if not seller_level and response.get("metrics"):
            # Fallback: Check metrics for level information
            for metric in response.get("metrics", []):
                if metric.get("level"):
                    seller_level = metric.get("level")
                    break
        
        # Extract cycle info - it's an object in the real response
        cycle_info = response.get("cycle", {})
        cycle_type = cycle_info.get("cycleType", cycle) if isinstance(cycle_info, dict) else cycle
        evaluation_date = cycle_info.get("evaluationDate") if isinstance(cycle_info, dict) else None
        
        # Extract rate metrics from the metrics array
        defect_rate = {}
        late_shipment_rate = {}
        cases_not_resolved = {}
        
        for metric in response.get("metrics", []):
            if metric.get("metricKey") == "DEFECTIVE_TRANSACTION_RATE":
                defect_rate = metric.get("value", {})
            elif metric.get("metricKey") == "SHIPPING_MISS_RATE":
                late_shipment_rate = metric.get("value", {})
            elif metric.get("metricKey") == "CLAIMS_SAF_RATE":
                cases_not_resolved = metric.get("value", {})
        
        standards = {
            "program": response.get("program", program),
            "cycle": cycle_type,
            "seller_level": seller_level,
            "defect_rate": defect_rate,
            "late_shipment_rate": late_shipment_rate,
            "cases_not_resolved": cases_not_resolved,
            "evaluation_date": evaluation_date,
            "next_evaluation_date": response.get("nextEvaluationDate"),
            "metrics": response.get("metrics", []),
            "data_source": "analytics_api"
        }
        
        await ctx.report_progress(1.0, "Complete")
        await ctx.info(f"Retrieved seller standards: {standards['seller_level']}")
        
        return success_response(
            data={
                "seller_standards": standards,
                "data_source": "analytics_api",
                "sandbox_retry_enabled": True
            },
            message="Seller standards retrieved successfully from Analytics API"
        ).to_json_string()
        
    except EbayApiError as e:
        await ctx.error(f"Analytics API error (after retries): {str(e)}")
        
        # Provide helpful guidance for common permission errors
        error_message = str(e)
        if "Access denied" in error_message or "Unauthorized" in error_message:
            error_message = (
                f"Access denied to seller account data. {str(e)}. "
                "To access real seller standards data, the seller must authorize this app. "
                "Use check_user_consent_status() and initiate_user_consent() tools to get seller authorization."
            )
        
        return error_response(
            ErrorCode.EXTERNAL_API_ERROR,
            error_message,
            {
                "status_code": e.status_code,
                "program": program,
                "cycle": cycle,
                "retry_attempted": True,
                "error_type": "analytics_api_error",
                "requires_user_consent": "Access denied" in str(e) or "Unauthorized" in str(e),
                "consent_tools": ["check_user_consent_status", "initiate_user_consent", "complete_user_consent"]
            }
        ).to_json_string()
    except Exception as e:
        await ctx.error(f"Failed to get seller standards (after retries): {str(e)}")
        return error_response(
            ErrorCode.INTERNAL_ERROR,
            f"Failed to get seller standards: {str(e)}",
            {"retry_attempted": True, "error_type": "unexpected_error"}
        ).to_json_string()
    finally:
        await rest_client.close()