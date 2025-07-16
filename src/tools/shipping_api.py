"""
eBay Shipping API tools for real-time shipping cost calculations.

Uses eBay's Shopping API to calculate actual shipping costs for items,
helping with pricing decisions and shipping strategy optimization.
"""
from typing import Dict, Any, Optional, List
from fastmcp import Context
from pydantic import BaseModel, Field, field_validator
from decimal import Decimal
from datetime import datetime, timezone

from api.oauth import OAuthManager, OAuthConfig, OAuthScopes
from api.rest_client import EbayRestClient, RestConfig
from api.errors import EbayApiError, ValidationError as ApiValidationError
from data_types import success_response, error_response, ErrorCode
from lootly_server import mcp


class ShippingCalculationInput(BaseModel):
    """Input validation for shipping cost calculations."""
    item_id: str = Field(..., description="eBay item ID")
    destination_country: str = Field("US", description="Destination country code")
    destination_postal_code: str = Field(..., description="Destination postal/zip code")
    quantity: int = Field(1, ge=1, le=99, description="Quantity of items")
    
    @field_validator('item_id')
    @classmethod
    def validate_item_id(cls, v):
        if not v or not v.strip():
            raise ValueError("Item ID cannot be empty")
        return v.strip()
    
    @field_validator('destination_country')
    @classmethod
    def validate_country(cls, v):
        if len(v) != 2:
            raise ValueError("Country code must be 2 characters (e.g., US, GB)")
        return v.upper()
    
    @field_validator('destination_postal_code')
    @classmethod
    def validate_postal_code(cls, v):
        if not v or not v.strip():
            raise ValueError("Postal code cannot be empty")
        return v.strip()


@mcp.tool
async def calculate_shipping_costs(
    ctx: Context,
    item_id: str,
    destination_postal_code: str,
    destination_country: str = "US",
    quantity: int = 1
) -> str:
    """
    Calculate real-time shipping costs for an eBay item.
    
    Uses eBay's Shopping API to get actual shipping costs to help with
    pricing decisions and shipping strategy optimization.
    
    Args:
        item_id: eBay item ID
        destination_postal_code: Destination postal/zip code
        destination_country: Destination country code (default: US)
        quantity: Quantity of items (default: 1)
        ctx: MCP context
    
    Returns:
        JSON response with shipping cost details and pricing recommendations
    """
    await ctx.info(f"Calculating shipping costs for item {item_id} to {destination_postal_code}")
    await ctx.report_progress(0.1, "Validating shipping calculation parameters...")
    
    # Check credentials
    if not mcp.config.app_id or not mcp.config.cert_id:
        return success_response(
            data={
                "item_id": item_id,
                "destination": f"{destination_postal_code}, {destination_country}",
                "shipping_options": [
                    {
                        "service_name": "Standard Shipping",
                        "shipping_cost": {"value": 4.99, "currency": "USD"},
                        "estimated_delivery": "5-7 business days",
                        "service_type": "STANDARD"
                    }
                ],
                "pricing_recommendations": {
                    "include_shipping_in_price": False,
                    "recommended_handling_fee": 0.00,
                    "total_shipping_cost": 4.99
                },
                "data_source": "static_estimate",
                "note": "Live shipping costs require eBay API credentials"
            },
            message="Shipping cost estimate (static data)"
        ).to_json_string()
    
    # Validate input
    try:
        input_data = ShippingCalculationInput(
            item_id=item_id,
            destination_country=destination_country,
            destination_postal_code=destination_postal_code,
            quantity=quantity
        )
    except Exception as e:
        await ctx.error(f"Validation error: {str(e)}")
        return error_response(
            ErrorCode.VALIDATION_ERROR,
            str(e)
        ).to_json_string()
    
    # Initialize API clients - Shopping API uses app credentials only
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
        await ctx.report_progress(0.3, "Fetching shipping costs from eBay...")
        
        # Build Shopping API parameters
        params = {
            "ItemID": input_data.item_id,
            "DestinationCountryCode": input_data.destination_country,
            "DestinationPostalCode": input_data.destination_postal_code,
            "QuantitySold": input_data.quantity,
            "IncludeDetails": "true"
        }
        
        # Make Shopping API request
        # Note: Shopping API may use different authentication pattern
        response = await rest_client.get(
            "/ws/eBayISAPI.dll",
            params={
                **params,
                "callname": "GetShippingCosts",
                "responseencoding": "JSON",
                "appid": mcp.config.app_id,
                "version": "967"
            },
            scope=OAuthScopes.BUY_BROWSE  # Shopping API uses basic scope
        )
        
        await ctx.report_progress(0.8, "Processing shipping cost data...")
        
        # Parse Shopping API response
        shipping_options = []
        total_shipping_cost = 0.0
        
        shipping_details = response.get("ShippingCostSummary", {})
        if shipping_details:
            # Standard shipping cost
            shipping_cost = shipping_details.get("ShippingServiceCost", {})
            cost_value = float(shipping_cost.get("value", 0))
            currency = shipping_cost.get("currencyID", "USD")
            
            shipping_options.append({
                "service_name": "Standard Shipping",
                "shipping_cost": {"value": cost_value, "currency": currency},
                "service_type": "STANDARD",
                "estimated_delivery": shipping_details.get("ShippingServiceName", "Standard")
            })
            
            total_shipping_cost = cost_value
            
            # Expedited shipping if available
            expedited_cost = shipping_details.get("ExpeditedShipping")
            if expedited_cost:
                expedited_value = float(expedited_cost.get("value", 0))
                shipping_options.append({
                    "service_name": "Expedited Shipping",
                    "shipping_cost": {"value": expedited_value, "currency": currency},
                    "service_type": "EXPEDITED",
                    "estimated_delivery": "1-3 business days"
                })
        
        # Generate pricing recommendations
        pricing_recommendations = _generate_pricing_recommendations(
            shipping_options, total_shipping_cost
        )
        
        await ctx.report_progress(1.0, "Complete")
        await ctx.info(f"Found {len(shipping_options)} shipping options, lowest cost: ${total_shipping_cost}")
        
        return success_response(
            data={
                "item_id": input_data.item_id,
                "destination": f"{input_data.destination_postal_code}, {input_data.destination_country}",
                "quantity": input_data.quantity,
                "shipping_options": shipping_options,
                "pricing_recommendations": pricing_recommendations,
                "calculation_date": datetime.now(timezone.utc).isoformat(),
                "data_source": "shopping_api"
            },
            message=f"Calculated shipping costs for {len(shipping_options)} options"
        ).to_json_string()
        
    except EbayApiError as e:
        await ctx.error(f"Shopping API error: {str(e)}")
        return error_response(
            ErrorCode.EXTERNAL_API_ERROR,
            str(e),
            {"status_code": e.status_code, "item_id": item_id}
        ).to_json_string()
    except Exception as e:
        await ctx.error(f"Failed to calculate shipping costs: {str(e)}")
        return error_response(
            ErrorCode.INTERNAL_ERROR,
            f"Failed to calculate shipping costs: {str(e)}"
        ).to_json_string()
    finally:
        await rest_client.close()


@mcp.tool
async def compare_shipping_strategies(
    ctx: Context,
    item_price: float,
    item_id: str,
    test_destinations: Optional[List[str]] = None
) -> str:
    """
    Compare different shipping strategies for pricing optimization.
    
    Tests shipping costs to multiple destinations and provides recommendations
    on whether to include shipping in the item price or charge separately.
    
    Args:
        item_price: Current item price
        item_id: eBay item ID
        test_destinations: List of postal codes to test (default: common zones)
        ctx: MCP context
    
    Returns:
        JSON response with shipping strategy analysis and recommendations
    """
    await ctx.info(f"Comparing shipping strategies for item {item_id} at ${item_price}")
    
    if test_destinations is None:
        test_destinations = ["10001", "90210", "75201", "60601", "33101"]  # Major US cities
    
    # Check credentials
    if not mcp.config.app_id or not mcp.config.cert_id:
        return success_response(
            data={
                "item_id": item_id,
                "item_price": item_price,
                "strategy_analysis": {
                    "free_shipping_recommended": item_price > 25.0,
                    "estimated_shipping_range": {"min": 4.99, "max": 12.99},
                    "recommended_strategy": "separate_shipping" if item_price < 25.0 else "free_shipping"
                },
                "data_source": "static_analysis",
                "note": "Live shipping analysis requires eBay API credentials"
            },
            message="Shipping strategy analysis (static data)"
        ).to_json_string()
    
    shipping_costs = []
    total_costs = 0.0
    
    await ctx.report_progress(0.1, f"Testing shipping to {len(test_destinations)} destinations...")
    
    for i, destination in enumerate(test_destinations):
        try:
            # Calculate shipping for each destination
            result = await calculate_shipping_costs.fn(
                ctx=ctx,
                item_id=item_id,
                destination_postal_code=destination
            )
            
            # Parse result
            import json
            result_data = json.loads(result)
            if result_data["status"] == "success":
                shipping_data = result_data["data"]
                if shipping_data["shipping_options"]:
                    cost = shipping_data["shipping_options"][0]["shipping_cost"]["value"]
                    shipping_costs.append({"destination": destination, "cost": cost})
                    total_costs += cost
            
            await ctx.report_progress(0.1 + (0.7 * (i + 1) / len(test_destinations)), 
                                    f"Tested {i+1}/{len(test_destinations)} destinations")
            
        except Exception as e:
            await ctx.error(f"Failed to test destination {destination}: {str(e)}")
            continue
    
    if not shipping_costs:
        return error_response(
            ErrorCode.EXTERNAL_API_ERROR,
            "Failed to get shipping costs for any test destinations"
        ).to_json_string()
    
    # Analyze shipping strategy
    avg_shipping = total_costs / len(shipping_costs)
    max_shipping = max(cost["cost"] for cost in shipping_costs)
    min_shipping = min(cost["cost"] for cost in shipping_costs)
    
    # Generate strategy recommendations
    strategy_analysis = {
        "shipping_cost_range": {"min": min_shipping, "max": max_shipping, "average": avg_shipping},
        "free_shipping_recommended": _should_offer_free_shipping(item_price, avg_shipping),
        "price_adjustment_needed": max_shipping * 1.1,  # Add 10% buffer
        "estimated_conversion_impact": _estimate_conversion_impact(item_price, avg_shipping),
        "recommended_strategy": _recommend_strategy(item_price, avg_shipping, max_shipping)
    }
    
    await ctx.report_progress(1.0, "Strategy analysis complete")
    await ctx.info(f"Analyzed {len(shipping_costs)} destinations, avg shipping: ${avg_shipping:.2f}")
    
    return success_response(
        data={
            "item_id": item_id,
            "item_price": item_price,
            "shipping_costs": shipping_costs,
            "strategy_analysis": strategy_analysis,
            "test_destinations_count": len(shipping_costs),
            "analysis_date": datetime.now(timezone.utc).isoformat(),
            "data_source": "shipping_api_analysis"
        },
        message=f"Shipping strategy analysis complete for {len(shipping_costs)} destinations"
    ).to_json_string()


def _generate_pricing_recommendations(shipping_options: List[Dict], total_cost: float) -> Dict[str, Any]:
    """Generate pricing recommendations based on shipping costs."""
    return {
        "include_shipping_in_price": total_cost < 5.0,  # Include if shipping is low
        "recommended_handling_fee": 0.99 if total_cost > 10.0 else 0.0,
        "total_shipping_cost": total_cost,
        "competitiveness": "high" if total_cost < 6.0 else "medium" if total_cost < 12.0 else "low",
        "buyer_psychology": {
            "free_shipping_threshold": total_cost + 5.0,  # Price to offer "free" shipping
            "separate_shipping_advantage": total_cost > 8.0  # Better to show separately if high
        }
    }


def _should_offer_free_shipping(item_price: float, avg_shipping: float) -> bool:
    """Determine if free shipping should be offered."""
    # Offer free shipping if item price is high enough to absorb shipping costs
    return item_price > (avg_shipping * 5)


def _estimate_conversion_impact(item_price: float, avg_shipping: float) -> Dict[str, Any]:
    """Estimate conversion rate impact of shipping strategies."""
    shipping_percentage = (avg_shipping / item_price) * 100
    
    return {
        "shipping_percentage_of_price": shipping_percentage,
        "estimated_conversion_boost": {
            "free_shipping": 15 if shipping_percentage > 15 else 8,  # % improvement
            "fast_shipping": 5,
            "combined": 20 if shipping_percentage > 15 else 12
        },
        "psychological_impact": "high" if shipping_percentage > 20 else "medium" if shipping_percentage > 10 else "low"
    }


def _recommend_strategy(item_price: float, avg_shipping: float, max_shipping: float) -> str:
    """Recommend optimal shipping strategy."""
    if item_price > (max_shipping * 4):
        return "free_shipping_increase_price"
    elif avg_shipping < 6.0:
        return "include_shipping_in_price"
    elif max_shipping - avg_shipping > 3.0:
        return "calculated_shipping"
    else:
        return "separate_shipping_fixed_rate"