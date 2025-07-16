#!/usr/bin/env python3
"""
Interactive OAuth consent flow test.

This script will guide you through the complete OAuth flow:
1. Check consent status
2. If no consent, initiate OAuth flow (opens browser)
3. Prompt you to enter the callback URL
4. Complete the OAuth flow
5. Test APIs that require consent

Usage:
    uv run python scripts/test_oauth_flow.py
"""
import asyncio
import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from tools.oauth_consent import (
    check_user_consent_status,
    initiate_user_consent,
    complete_user_consent,
    revoke_user_consent
)
from tools.inventory_api import create_inventory_item, get_inventory_items
from tools.account_api import get_seller_standards
from lootly_server import mcp
from fastmcp import Context
from datetime import datetime


class TestContext(Context):
    """Test context that prints messages to console."""
    
    def __init__(self):
        super().__init__(mcp)
        self.session_data = {}
    
    async def info(self, message: str):
        print(f"[INFO] {message}")
    
    async def error(self, message: str):
        print(f"[ERROR] {message}")
    
    async def report_progress(self, progress: float, message: str):
        print(f"[PROGRESS {int(progress * 100)}%] {message}")


async def test_oauth_flow():
    """Test the complete OAuth flow interactively."""
    ctx = TestContext()
    
    print("🚀 eBay OAuth Flow Test")
    print("=" * 60)
    
    # Step 1: Check current consent status
    print("\n1️⃣ Checking current consent status...")
    try:
        status_result = await check_user_consent_status.fn(ctx)
        status_data = json.loads(status_result)
        
        if status_data["status"] == "success" and status_data["data"].get("has_consent", False):
            print("✅ Valid consent found!")
            print(f"   User ID: {status_data['data'].get('user_id', 'N/A')}")
            print(f"   Expires: {status_data['data'].get('expires_at', 'N/A')}")
            
            # Ask if user wants to revoke and start fresh
            response = input("\n🔄 Do you want to revoke existing consent and start fresh? (y/N): ")
            if response.lower() == 'y':
                print("\n🗑️  Revoking existing consent...")
                await revoke_user_consent.fn(ctx)
                print("✅ Consent revoked. Starting fresh OAuth flow...")
            else:
                print("\n✅ Using existing consent. Skipping to API tests...")
                return await test_apis_with_consent(ctx)
        else:
            print("⚠️  No valid consent found. Starting OAuth flow...")
            
    except Exception as e:
        print(f"❌ Error checking consent: {str(e)}")
        return
    
    # Step 2: Initiate OAuth flow
    print("\n2️⃣ Initiating OAuth consent flow...")
    try:
        consent_result = await initiate_user_consent.fn(ctx)
        consent_data = json.loads(consent_result)
        
        if consent_data["status"] != "success":
            print(f"❌ Failed to initiate consent: {consent_data['error_message']}")
            return
        
        auth_url = consent_data['data']['authorization_url']
        browser_opened = consent_data['data'].get('browser_opened', False)
        
        print(f"\n🌐 Authorization URL: {auth_url}")
        print(f"🔍 Browser opened automatically: {browser_opened}")
        
        if browser_opened:
            print("\n✅ Browser should have opened automatically!")
            print("   Complete the authorization in your browser.")
        else:
            print("\n📋 Please copy the URL above and open it in your browser.")
        
        print("\n📝 Instructions:")
        print("1. Log in to your eBay sandbox account")
        print("2. Grant the requested permissions")
        print("3. You'll be redirected to localhost (page won't load - that's normal)")
        print("4. Copy the ENTIRE URL from your browser's address bar")
        print("5. Paste it here when prompted")
        
    except Exception as e:
        print(f"❌ Error initiating consent: {str(e)}")
        return
    
    # Step 3: Get callback URL from user
    print("\n3️⃣ Waiting for authorization completion...")
    while True:
        callback_url = input("\n📋 Paste the complete URL from your browser here: ").strip()
        
        if not callback_url:
            print("❌ No URL provided. Please try again.")
            continue
        
        if "code=" not in callback_url:
            print("❌ Invalid URL. Make sure it contains 'code=' parameter.")
            continue
        
        break
    
    # Step 4: Complete OAuth flow
    print("\n4️⃣ Completing OAuth flow...")
    try:
        complete_result = await complete_user_consent.fn(ctx, callback_url)
        complete_data = json.loads(complete_result)
        
        if complete_data["status"] == "success":
            print("✅ OAuth flow completed successfully!")
            print(f"   User ID: {complete_data['data'].get('user_id', 'N/A')}")
            print(f"   Expires at: {complete_data['data'].get('expires_at', 'N/A')}")
            print(f"   Scopes: {', '.join(complete_data['data'].get('granted_scopes', []))}")
        else:
            print(f"❌ Failed to complete OAuth: {complete_data['error_message']}")
            return
        
    except Exception as e:
        print(f"❌ Error completing OAuth: {str(e)}")
        return
    
    # Step 5: Test APIs that require consent
    await test_apis_with_consent(ctx)


async def test_apis_with_consent(ctx):
    """Test APIs that require user consent."""
    print("\n5️⃣ Testing APIs with user consent...")
    
    # Test 1: Account API
    print("\n🔧 Testing Account API...")
    try:
        result = await get_seller_standards.fn(ctx, program="PROGRAM_US", cycle="CURRENT")
        data = json.loads(result)
        if data["status"] == "success":
            seller_level = data["data"]["seller_standards"]["seller_level"]
            print(f"✅ Account API: Seller level: {seller_level}")
        else:
            print(f"❌ Account API: {data['error_message']}")
    except Exception as e:
        print(f"❌ Account API error: {str(e)}")
    
    # Test 2: Inventory API - Get items
    print("\n📦 Testing Inventory API (get items)...")
    try:
        result = await get_inventory_items.fn(ctx, limit=5)
        data = json.loads(result)
        if data["status"] == "success":
            count = len(data["data"]["inventory_items"])
            print(f"✅ Inventory API (get): Found {count} items")
        else:
            print(f"❌ Inventory API (get): {data['error_message']}")
    except Exception as e:
        print(f"❌ Inventory API (get) error: {str(e)}")
    
    # Test 3: Inventory API - Create item
    print("\n📦 Testing Inventory API (create item)...")
    try:
        test_sku = f"OAUTH-TEST-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        result = await create_inventory_item.fn(
            ctx=ctx,
            sku=test_sku,
            title="OAuth Test Item - Success!",
            description="This item was created after successful OAuth consent flow",
            category_id="166",  # Safe category
            price=9.99,
            quantity=1,
            brand="TestBrand",
            condition="NEW"
        )
        data = json.loads(result)
        if data["status"] == "success":
            print(f"✅ Inventory API (create): Created item {test_sku}")
        else:
            print(f"❌ Inventory API (create): {data['error_message']}")
    except Exception as e:
        print(f"❌ Inventory API (create) error: {str(e)}")
    
    print("\n🎉 OAuth flow and API testing complete!")
    print("✅ All tests used REAL OAuth tokens and REAL API calls - no mocking!")


async def main():
    """Main entry point."""
    try:
        await test_oauth_flow()
    except KeyboardInterrupt:
        print("\n\n⚠️  Process interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())