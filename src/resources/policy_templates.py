"""eBay seller policy templates and best practices.

IMPORTANT: This resource provides policy templates and strategic guidance.
To create and manage actual eBay policies, use these API tools:
- return_policy_api: Create/manage return policies
- payment_policy_api: Create/manage payment policies  
- fulfillment_policy_api: Create/manage shipping/fulfillment policies

This resource contains:
- Best-practice policy templates with pros/cons
- Strategic guidance for different seller types
- Policy recommendations by product category
- Trust-building tips for sellers

Note: These are template suggestions. Actual policy creation requires the API tools above.
"""
from fastmcp import Context
from data_types import MCPResourceData
from lootly_server import mcp


# Best practice seller policy templates
SELLER_POLICIES = {
    "return": {
        "buyer_friendly": {
            "name": "Buyer-Friendly 60-Day Returns",
            "duration": "60 days",
            "who_pays": "Seller pays return shipping",
            "restocking_fee": "No restocking fee",
            "condition": "Item must be in original condition",
            "template": "We offer 60-day returns. If you're not satisfied with your purchase, you may return it within 60 days of delivery for a full refund. We'll provide a prepaid return shipping label. Items must be returned in original condition with all accessories and packaging.",
            "pros": ["Increases buyer confidence", "Can boost sales", "Reduces negative feedback risk"],
            "cons": ["Higher return costs", "Risk of buyer abuse", "Ties up inventory longer"],
            "best_for": ["New sellers building reputation", "High-margin items", "Competitive categories"]
        },
        "standard": {
            "name": "Standard 30-Day Returns",
            "duration": "30 days",
            "who_pays": "Buyer pays return shipping",
            "restocking_fee": "No restocking fee",
            "condition": "Item must be in original condition",
            "template": "We accept returns within 30 days of delivery. To initiate a return, please contact us through eBay messages. Buyer is responsible for return shipping costs. Items must be returned in the same condition as received.",
            "pros": ["Industry standard", "Balanced approach", "Protects against long-term returns"],
            "cons": ["May lose sales to sellers with better policies", "Buyer pays shipping"],
            "best_for": ["Most sellers", "Standard merchandise", "Established sellers"]
        },
        "no_returns": {
            "name": "No Returns Policy",
            "duration": "N/A",
            "who_pays": "N/A",
            "template": "All sales are final. Please review the listing carefully and ask any questions before purchasing. We accurately describe all items and provide detailed photos.",
            "pros": ["No return hassles", "Reduces costs", "Clear expectations"],
            "cons": ["Significantly reduces sales", "May get more disputes", "Looks less professional"],
            "best_for": ["Custom/personalized items", "Perishables", "Very low-value items"],
            "warning": "eBay may still force returns for 'not as described' claims"
        }
    },
    "payment": {
        "standard": {
            "name": "Standard Payment Policy",
            "accepted_methods": ["eBay Managed Payments"],
            "payment_due": "Immediate payment required for Buy It Now",
            "template": "Payment is due immediately upon purchase through eBay's secure payment system. We ship within 1 business day of cleared payment.",
            "notes": ["eBay Managed Payments is now mandatory", "Includes credit cards, debit cards, PayPal, Apple Pay, Google Pay"]
        }
    },
    "shipping": {
        "fast_shipper": {
            "name": "Fast Shipping Policy",
            "handling_time": "Same day or 1 business day",
            "template": "We ship all orders the same business day if purchased before 2 PM PST, or next business day for later orders. You'll receive tracking information via eBay messages once your item ships.",
            "benefits": ["Qualifies for Fast 'N Free badge", "Improves search ranking", "Increases buyer satisfaction"]
        },
        "standard_shipper": {
            "name": "Standard Shipping Policy",
            "handling_time": "2-3 business days",
            "template": "Orders ship within 2-3 business days of cleared payment. Tracking information will be provided through eBay. We carefully package all items to ensure safe delivery.",
            "notes": ["Most common policy", "Allows time for order processing", "Good for part-time sellers"]
        },
        "combined_shipping": {
            "name": "Combined Shipping Discount",
            "template": "We offer combined shipping! Purchase multiple items and save on shipping costs. Add items to your cart and request a total for accurate combined shipping rates.",
            "calculation": "Highest shipping cost + $1-2 per additional item",
            "benefits": ["Encourages multiple purchases", "Saves buyer money", "Increases average order value"]
        }
    }
}


@mcp.resource("ebay://policies")
async def ebay_all_policies_resource(ctx: Context) -> str:
    """Get all eBay seller policy templates."""
    try:
        return MCPResourceData(
            data={
                "policies": SELLER_POLICIES,
                "best_practices": {
                    "general": [
                        "Be clear and specific to avoid disputes",
                        "Follow eBay's policy requirements",
                        "Consider your category's standards",
                        "Update policies seasonally (holidays, etc.)"
                    ],
                    "trust_builders": [
                        "Respond to messages within 24 hours",
                        "Ship on time or early",
                        "Provide tracking information",
                        "Leave feedback for buyers"
                    ]
                },
                "policy_types": list(SELLER_POLICIES.keys())
            },
            metadata={
                "last_updated": "2024-01-15",
                "source": "eBay best practices"
            }
        ).to_json_string()
        
    except Exception as e:
        return MCPResourceData(
            error=str(e),
            metadata={"error_type": type(e).__name__}
        ).to_json_string()


@mcp.resource("ebay://policies/return")
async def ebay_return_policies_resource(ctx: Context) -> str:
    """Get return policy templates."""
    try:
        return MCPResourceData(
            data={
                "return_policies": SELLER_POLICIES["return"],
                "recommendations": {
                    "new_sellers": "Start with buyer-friendly policy to build trust",
                    "established_sellers": "Standard 30-day policy is usually sufficient",
                    "high_value_items": "Consider buyer-friendly to reduce purchase hesitation",
                    "custom_items": "No returns may be appropriate with clear disclosure"
                },
                "ebay_requirements": {
                    "money_back_guarantee": "eBay Money Back Guarantee applies regardless of your policy",
                    "not_as_described": "You must accept returns for items not as described",
                    "defective_items": "Defective items must be accepted for return"
                }
            },
            metadata={
                "category": "return_policies"
            }
        ).to_json_string()
        
    except Exception as e:
        return MCPResourceData(
            error=str(e),
            metadata={"error_type": type(e).__name__}
        ).to_json_string()


@mcp.resource("ebay://policies/shipping")
async def ebay_shipping_policies_resource(ctx: Context) -> str:
    """Get shipping policy templates."""
    try:
        return MCPResourceData(
            data={
                "shipping_policies": SELLER_POLICIES["shipping"],
                "handling_time_impact": {
                    "same_day": "Significant search boost, Fast 'N Free eligible",
                    "1_day": "Good search boost, Fast 'N Free eligible",
                    "2_days": "Standard, no significant impact",
                    "3+_days": "May reduce visibility and sales"
                },
                "tips": [
                    "Print labels through eBay for discounts",
                    "Always use tracking for seller protection",
                    "Consider offering free shipping on higher-priced items",
                    "Be realistic about handling time during busy periods"
                ]
            },
            metadata={
                "category": "shipping_policies"
            }
        ).to_json_string()
        
    except Exception as e:
        return MCPResourceData(
            error=str(e),
            metadata={"error_type": type(e).__name__}
        ).to_json_string()


@mcp.resource("ebay://policies/payment")
async def ebay_payment_policies_resource(ctx: Context) -> str:
    """Get payment policy information."""
    try:
        return MCPResourceData(
            data={
                "payment_policies": SELLER_POLICIES["payment"],
                "managed_payments_info": {
                    "mandatory": True,
                    "included_methods": [
                        "Credit and debit cards",
                        "PayPal",
                        "Apple Pay",
                        "Google Pay",
                        "Gift cards and coupons"
                    ],
                    "payout_schedule": "Daily or weekly payouts available",
                    "fees": "Included in eBay selling fees"
                },
                "immediate_payment": {
                    "buy_it_now": "Can require immediate payment",
                    "auctions": "Cannot require immediate payment",
                    "best_offer": "Payment due when offer accepted"
                }
            },
            metadata={
                "category": "payment_policies"
            }
        ).to_json_string()
        
    except Exception as e:
        return MCPResourceData(
            error=str(e),
            metadata={"error_type": type(e).__name__}
        ).to_json_string()