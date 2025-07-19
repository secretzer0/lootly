"""eBay shipping reference guide and rate estimates.

IMPORTANT: This resource provides REFERENCE DATA ONLY for shipping planning.
Actual shipping rates vary significantly based on:
- Exact package dimensions and weight
- Origin and destination ZIP codes  
- Current carrier rates and fuel surcharges
- Account-specific discounts

Always use official carrier calculators or eBay's shipping calculator for accurate pricing.

This resource contains:
- Common shipping service options and typical cost ranges
- Delivery time estimates by service
- Weight/size limits and restrictions
- Best practices for different item types
- Important warnings about each service

Note: eBay does not provide a shipping rates API. This reference data helps sellers
understand their options, but should not be used for final pricing decisions.
"""
from typing import Dict, Any
from fastmcp import Context
from data_types import MCPResourceData
from lootly_server import mcp


# IMPORTANT: These are ESTIMATED costs for reference only. Actual shipping costs 
# vary significantly based on exact dimensions, weight, distance, and current rates.
# ALWAYS use carrier calculators or eBay's shipping calculator for accurate pricing.

# Shipping service reference data with cost estimates and important limitations
SHIPPING_SERVICES = {
    "domestic": {
        "USPS": {
            "USPSFirstClass": {
                "name": "USPS First Class Package",
                "typical_cost_range": "3.50-7.00",
                "delivery_time": "1-5 business days",
                "weight_limit": "1 lb (16 oz)",
                "best_for": "Small, lightweight items under 1 lb",
                "cost_factors": ["Weight", "Distance (Zone)", "Package thickness"],
                "warnings": [
                    "Cannot be used for items over 1 lb",
                    "Thickness limits apply (flexible packages)",
                    "Limited tracking compared to Priority Mail"
                ]
            },
            "USPSPriority": {
                "name": "USPS Priority Mail",
                "typical_cost_range": "8.00-15.00",
                "delivery_time": "1-3 business days",
                "weight_limit": "70 lbs",
                "best_for": "General purpose shipping, includes tracking",
                "cost_factors": ["Weight", "Distance (Zone)", "Package size"],
                "warnings": [
                    "Flat rate boxes only save money if item is heavy",
                    "Regional rate boxes can be cheaper for nearby zones",
                    "Dimensional weight pricing applies to large packages"
                ]
            },
            "USPSPriorityFlatRate": {
                "name": "USPS Priority Mail Flat Rate",
                "typical_cost_range": "9.00-22.00",
                "delivery_time": "1-3 business days",
                "weight_limit": "70 lbs (if it fits, it ships)",
                "box_options": {
                    "Small": {"cost": "~9.00", "size": "8.625\" x 5.375\" x 1.625\""},
                    "Medium": {"cost": "~16.00", "size": "11\" x 8.5\" x 5.5\" OR 14\" x 12\" x 3.5\""},
                    "Large": {"cost": "~22.00", "size": "12\" x 12\" x 5.5\""}
                },
                "best_for": "Heavy items that fit in provided boxes",
                "warnings": [
                    "Only cost-effective for heavy items",
                    "Must use USPS-provided boxes",
                    "Cannot modify or combine boxes"
                ]
            },
            "USPSParcelSelect": {
                "name": "USPS Parcel Select Ground",
                "typical_cost_range": "8.00-30.00",
                "delivery_time": "2-8 business days",
                "weight_limit": "70 lbs",
                "best_for": "Large/heavy items where speed isn't critical",
                "warnings": [
                    "Slowest USPS service",
                    "Limited tracking updates",
                    "Not available at retail counters (commercial only)"
                ]
            }
        },
        "UPS": {
            "UPSGround": {
                "name": "UPS Ground",
                "typical_cost_range": "10.00-40.00",
                "delivery_time": "1-5 business days",
                "weight_limit": "150 lbs",
                "best_for": "Heavy or valuable items needing reliable tracking",
                "cost_factors": ["Weight", "Dimensions", "Distance", "Fuel surcharges"],
                "warnings": [
                    "More expensive than USPS for lightweight items",
                    "Additional fees for residential delivery",
                    "Dimensional weight pricing is strict"
                ]
            }
        },
        "FedEx": {
            "FedExHomeDelivery": {
                "name": "FedEx Home Delivery",
                "typical_cost_range": "10.00-40.00",
                "delivery_time": "1-5 business days",
                "weight_limit": "70 lbs",
                "best_for": "Residential deliveries with evening/weekend options",
                "warnings": [
                    "Only for residential addresses",
                    "More expensive than USPS for small items",
                    "Surcharges for large/oversized packages"
                ]
            }
        }
    },
    "international": {
        "USPS": {
            "USPSFirstClassInternational": {
                "name": "USPS First-Class International",
                "typical_cost_range": "15.00-35.00",
                "delivery_time": "7-21 business days",
                "weight_limit": "4 lbs",
                "best_for": "Small, lightweight international shipments",
                "warnings": [
                    "Limited tracking (often ends at US border)",
                    "No insurance available",
                    "Customs forms required"
                ]
            },
            "USPSPriorityInternational": {
                "name": "USPS Priority Mail International",
                "typical_cost_range": "35.00-80.00",
                "delivery_time": "6-10 business days",
                "weight_limit": "70 lbs",
                "best_for": "Faster international shipping with tracking",
                "warnings": [
                    "Tracking may be limited in destination country",
                    "Customs delays not included in delivery estimate",
                    "Additional duties/taxes paid by buyer"
                ]
            }
        },
        "eBayInternationalShipping": {
            "GlobalShippingProgram": {
                "name": "eBay Global Shipping Program",
                "cost_to_seller": "Domestic shipping only",
                "delivery_time": "11-35 business days",
                "best_for": "Sellers wanting protection from international hassles",
                "benefits": [
                    "Seller only ships to US hub",
                    "eBay handles customs and international leg",
                    "Seller protected from international issues"
                ],
                "warnings": [
                    "Total cost to buyer can be high",
                    "Not available for all categories",
                    "Cannot combine shipping for multiple items"
                ]
            }
        }
    }
}


@mcp.resource("ebay://shipping/rates")
async def ebay_all_shipping_rates_resource(ctx: Context) -> str:
    """Get all eBay shipping rate information."""
    try:
        return MCPResourceData(
            data={
                "CRITICAL_WARNINGS": {
                    "cost_accuracy": "⚠️ ESTIMATES ONLY - Actual shipping costs vary significantly by weight, dimensions, and distance",
                    "seller_liability": "💰 SELLER RESPONSIBILITY - You pay the difference if actual shipping exceeds what buyer paid",
                    "calculation_required": "📊 ALWAYS CALCULATE - Use carrier calculators or eBay's shipping calculator before listing",
                    "package_requirements": "📦 PACKAGING MATTERS - Odd shapes, fragile items, and oversized packages incur extra fees"
                },
                "domestic": SHIPPING_SERVICES["domestic"],
                "international": SHIPPING_SERVICES["international"],
                "shipping_cost_guardrails": {
                    "before_listing": [
                        "Weigh your packaged item (including box, padding, tape)",
                        "Measure dimensions: Length x Width x Height",
                        "Calculate dimensional weight if package is large but light",
                        "Test shipping costs to multiple zip codes using carrier calculators",
                        "Factor in handling fees if you charge them"
                    ],
                    "cost_protection_strategies": [
                        "Use calculated shipping (buyer pays actual cost)",
                        "If offering free shipping, test costs to furthest zones first",
                        "Add 10-15% buffer to estimated costs for free shipping",
                        "Consider shipping insurance for valuable items",
                        "Use eBay labels for discounted rates"
                    ],
                    "common_mistakes": [
                        "Forgetting dimensional weight charges for large boxes",
                        "Not accounting for packaging weight",
                        "Underestimating costs to Alaska, Hawaii, Puerto Rico",
                        "Missing fuel surcharges and residential fees",
                        "Not checking holiday season rate increases"
                    ]
                }
            },
            metadata={
                "last_updated": "2024-01-15",
                "disclaimer": "Rates are estimates only. Always verify with carriers.",
                "data_source": "static_reference"
            }
        ).to_json_string()
        
    except Exception as e:
        return MCPResourceData(
            error=str(e),
            metadata={"error_type": type(e).__name__}
        ).to_json_string()


@mcp.resource("ebay://shipping/rates/domestic")
async def ebay_domestic_shipping_rates_resource(ctx: Context) -> str:
    """Get domestic shipping rate information."""
    try:
        return MCPResourceData(
            data={
                "region": "domestic",
                "services": SHIPPING_SERVICES["domestic"],
                "quick_reference": {
                    "lightweight_under_1lb": "USPS First Class ($3.50-$7.00)",
                    "general_purpose": "USPS Priority Mail ($8.00-$15.00)",
                    "heavy_items": "USPS Flat Rate or UPS Ground",
                    "time_sensitive": "USPS Priority or UPS/FedEx express options"
                },
                "warnings": [
                    "Weekend delivery affects some services",
                    "Rural addresses may have surcharges",
                    "Holiday seasons have delays and higher rates"
                ]
            },
            metadata={
                "region_scope": "USA domestic (48 contiguous states)",
                "special_regions": "Alaska, Hawaii, territories may cost more"
            }
        ).to_json_string()
        
    except Exception as e:
        return MCPResourceData(
            error=str(e),
            metadata={"error_type": type(e).__name__}
        ).to_json_string()


@mcp.resource("ebay://shipping/rates/international")
async def ebay_international_shipping_rates_resource(ctx: Context) -> str:
    """Get international shipping rate information."""
    try:
        return MCPResourceData(
            data={
                "region": "international",
                "services": SHIPPING_SERVICES["international"],
                "global_shipping_program": {
                    "description": "eBay handles international portion",
                    "seller_ships_to": "Kentucky hub only",
                    "seller_cost": "Domestic shipping rate only",
                    "benefits": [
                        "No customs forms for seller",
                        "Protection from international issues",
                        "Tracking to domestic hub only"
                    ]
                },
                "customs_considerations": {
                    "forms_required": ["CN22 for under $400", "CN23 for over $400"],
                    "prohibited_items_vary_by_country": True,
                    "buyer_pays_duties": True,
                    "delivery_delays": "Customs can add 1-4 weeks"
                }
            },
            metadata={
                "complexity_warning": "International shipping has many variables",
                "recommendation": "Consider Global Shipping Program for simplicity"
            }
        ).to_json_string()
        
    except Exception as e:
        return MCPResourceData(
            error=str(e),
            metadata={"error_type": type(e).__name__}
        ).to_json_string()


@mcp.resource("ebay://shipping/rates/domestic/{carrier}")
async def ebay_carrier_specific_rates_resource(carrier: str, ctx: Context) -> str:
    """Get shipping rates for a specific carrier."""
    try:
        carrier_upper = carrier.upper()
        
        if carrier_upper in SHIPPING_SERVICES["domestic"]:
            carrier_services = SHIPPING_SERVICES["domestic"][carrier_upper]
        else:
            return MCPResourceData(
                error=f"Carrier '{carrier}' not found",
                metadata={
                    "available_carriers": list(SHIPPING_SERVICES["domestic"].keys()),
                    "requested_carrier": carrier
                }
            ).to_json_string()
        
        return MCPResourceData(
            data={
                "carrier": carrier_upper,
                "services": carrier_services,
                "carrier_tips": _get_carrier_tips(carrier_upper)
            },
            metadata={
                "region": "domestic",
                "carrier": carrier_upper
            }
        ).to_json_string()
        
    except Exception as e:
        return MCPResourceData(
            error=str(e),
            metadata={"error_type": type(e).__name__}
        ).to_json_string()


def _get_carrier_tips(carrier: str) -> Dict[str, Any]:
    """Get carrier-specific tips."""
    tips = {
        "USPS": {
            "pros": [
                "Cheapest for lightweight items",
                "Saturday delivery included",
                "Flat rate options for heavy items",
                "Pickup available"
            ],
            "cons": [
                "Limited insurance on some services",
                "Less reliable tracking than UPS/FedEx",
                "Can be slow during holidays"
            ],
            "best_practices": [
                "Use First Class for under 1 lb",
                "Compare flat rate vs calculated for heavy items",
                "Schedule pickups online to save time"
            ]
        },
        "UPS": {
            "pros": [
                "Excellent tracking",
                "Reliable for valuable items",
                "Good for heavy packages",
                "Business-friendly"
            ],
            "cons": [
                "More expensive for light items",
                "Residential surcharges",
                "Strict on dimensions"
            ],
            "best_practices": [
                "Best for items over 5 lbs",
                "Use for high-value shipments",
                "Get business rates if possible"
            ]
        },
        "FEDEX": {
            "pros": [
                "Home delivery option",
                "Good tracking",
                "Evening/weekend delivery",
                "Reliable service"
            ],
            "cons": [
                "Higher cost",
                "Surcharges common",
                "Complex rate structure"
            ],
            "best_practices": [
                "Compare with UPS rates",
                "Good for residential areas",
                "Watch for fuel surcharges"
            ]
        }
    }
    
    return tips.get(carrier, {
        "note": "Carrier-specific information not available",
        "suggestion": "Check carrier website for details"
    })