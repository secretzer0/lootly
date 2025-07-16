#!/usr/bin/env python3
"""
Example: Create a complete eBay listing without Business Policies.

This shows how to create listings with inline payment, shipping, and return
details, bypassing the need for Business Policies entirely.
"""
import asyncio
import aiohttp
import json
from pathlib import Path
from datetime import datetime, timezone


async def create_listing_without_policies():
    """Create a complete listing using only inline policies."""
    
    # Load OAuth token
    token_file = Path.home() / ".ebay" / "oauth_tokens.json"
    with open(token_file) as f:
        tokens = json.load(f)
    
    # Get the token for your app
    app_id = "TravisMe-Lootly-SBX-e0bd59c28-7f9d9fa9"
    if app_id not in tokens:
        print("❌ No OAuth token found. Run test_oauth_consent.py first!")
        return
    
    access_token = tokens[app_id]["access_token"]
    
    # Generate unique SKU
    sku = f"DEMO-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    
    # Common headers for all requests
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Content-Language": "en-US"
    }
    
    async with aiohttp.ClientSession() as session:
        # Step 1: Create Inventory Item
        print(f"\n1️⃣ Creating inventory item with SKU: {sku}")
        
        inventory_data = {
            "availability": {
                "shipToLocationAvailability": {
                    "quantity": 10
                }
            },
            "condition": "NEW",
            "product": {
                "title": "Premium Phone Case - Universal Fit",
                "description": (
                    "High-quality protective phone case with shock absorption. "
                    "Compatible with most smartphones. Durable TPU material with "
                    "reinforced corners for drop protection. Precise cutouts for "
                    "all ports and buttons."
                ),
                "imageUrls": [
                    "https://picsum.photos/800/600?random=1",
                    "https://picsum.photos/800/600?random=2"
                ],
                "aspects": {
                    "Brand": ["Generic"],
                    "Type": ["Protective Case"],
                    "Material": ["TPU"],
                    "Compatible Brand": ["Universal"],
                    "Color": ["Black"]
                }
            }
        }
        
        inventory_url = f"https://api.sandbox.ebay.com/sell/inventory/v1/inventory_item/{sku}"
        
        async with session.put(inventory_url, headers=headers, json=inventory_data) as response:
            if response.status in [200, 201, 204]:
                print("✅ Inventory item created successfully!")
            else:
                error = await response.text()
                print(f"❌ Failed to create inventory: {error}")
                return
        
        # Step 2: Create Offer with Inline Policies
        print(f"\n2️⃣ Creating offer with inline payment/shipping/return policies...")
        
        offer_data = {
            "sku": sku,
            "marketplaceId": "EBAY_US",
            "format": "FIXED_PRICE",
            "listingDuration": "GTC",  # Good Till Cancelled
            "pricingSummary": {
                "price": {
                    "currency": "USD",
                    "value": "19.99"
                }
            },
            # Category - Cell Phone Accessories
            "categoryId": "9394",
            
            # Item location (inline - no need for location API)
            "merchantLocationKey": "DEFAULT",
            "location": {
                "country": "US",
                "address": {
                    "addressLine1": "123 Main St",
                    "city": "San Jose",
                    "stateOrProvince": "CA",
                    "postalCode": "95125",
                    "countryCode": "US"
                }
            },
            
            # INLINE SHIPPING (instead of shippingPolicyId)
            "shippingCostOverrides": [
                {
                    "shippingServiceType": "DOMESTIC",
                    "shippingCost": {
                        "currency": "USD",
                        "value": "4.99"
                    }
                }
            ],
            
            # INLINE PAYMENT METHODS (instead of paymentPolicyId)
            "paymentMethods": [
                {
                    "paymentMethodType": "PAYPAL",
                    "recipientAccountReference": {
                        "referenceType": "PAYPAL_EMAIL",
                        "referenceValue": "seller@example.com"
                    }
                }
            ],
            
            # INLINE RETURN POLICY (instead of returnPolicyId)
            "returnTerms": {
                "returnsAccepted": True,
                "returnPeriod": {
                    "unit": "DAY",
                    "value": 30
                },
                "returnShippingCostPayer": "BUYER",
                "returnMethod": "EXCHANGE",
                "description": "30-day return policy. Buyer pays return shipping."
            },
            
            # Listing details
            "listingDescription": (
                "<h2>Premium Universal Phone Case</h2>"
                "<p>Protect your phone with this high-quality case!</p>"
                "<ul>"
                "<li>Shock-absorbing TPU material</li>"
                "<li>Raised edges for screen protection</li>"
                "<li>Precise cutouts for all ports</li>"
                "<li>Wireless charging compatible</li>"
                "</ul>"
            )
        }
        
        offer_url = "https://api.sandbox.ebay.com/sell/inventory/v1/offer"
        
        async with session.post(offer_url, headers=headers, json=offer_data) as response:
            if response.status in [200, 201]:
                offer_response = await response.json()
                offer_id = offer_response.get("offerId")
                print(f"✅ Offer created successfully! Offer ID: {offer_id}")
                
                # Step 3: Publish the offer
                print(f"\n3️⃣ Publishing offer to make it live...")
                
                publish_url = f"https://api.sandbox.ebay.com/sell/inventory/v1/offer/{offer_id}/publish"
                
                async with session.post(publish_url, headers=headers) as publish_response:
                    if publish_response.status in [200, 201]:
                        publish_data = await publish_response.json()
                        listing_id = publish_data.get("listingId")
                        print(f"✅ Listing published successfully!")
                        print(f"   Listing ID: {listing_id}")
                        print(f"   View at: https://sandbox.ebay.com/itm/{listing_id}")
                    else:
                        error = await publish_response.text()
                        print(f"❌ Failed to publish: {error}")
            else:
                error = await response.text()
                print(f"❌ Failed to create offer: {error}")
                
                # Try to parse error details
                try:
                    error_data = json.loads(error)
                    if "errors" in error_data:
                        print("\nError details:")
                        for err in error_data["errors"]:
                            print(f"  - {err.get('message', 'Unknown error')}")
                            if "longMessage" in err:
                                print(f"    {err['longMessage']}")
                except:
                    pass


async def main():
    """Run the example."""
    print("🚀 Creating eBay Listing Without Business Policies")
    print("=" * 50)
    
    await create_listing_without_policies()
    
    print("\n✨ Done!")


if __name__ == "__main__":
    asyncio.run(main())