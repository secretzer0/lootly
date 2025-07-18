#!/usr/bin/env python3
"""
Interactive OAuth consent flow test for the NEW OAuth architecture.

This script will guide you through the complete OAuth flow using the new
centralized OAuthManager system:
1. Check consent status using OAuthManager
2. If no consent, initiate OAuth flow (opens browser)
3. Prompt you to enter the callback URL
4. Complete the OAuth flow
5. Test APIs that require consent

Usage:
    uv run python scripts/test_oauth_flow_new.py

NEW ARCHITECTURE:
- Uses centralized OAuthManager in oauth.py
- MCP tools are thin wrappers around OAuthManager
- ConsentRequiredException is properly raised when needed
- Single source of truth for all token management
"""
import asyncio
import json
import sys
import logging
from pathlib import Path
from datetime import datetime

# Enable debug logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logging.getLogger('api.oauth').setLevel(logging.DEBUG)

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from api.oauth import OAuthManager, OAuthConfig, ConsentRequiredException
from api.rest_client import EbayRestClient, RestConfig
from api.ebay_enums import MarketplaceIdEnum
# Import the MCP tools - these are FunctionTool objects
import tools.oauth_consent as oauth_consent_tools
from tools.account_api import get_seller_standards
from lootly_server import mcp
from fastmcp import Context


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


async def test_oauth_architecture():
    """Test the OAuth architecture directly."""
    print("🔧 Testing OAuth Architecture Directly...")
    print("-" * 50)
    
    # Initialize OAuth manager
    oauth_config = OAuthConfig(
        client_id=mcp.config.app_id,
        client_secret=mcp.config.cert_id,
        sandbox=mcp.config.sandbox_mode
    )
    oauth_manager = OAuthManager(oauth_config)
    
    print(f"✅ OAuth manager initialized (sandbox: {mcp.config.sandbox_mode})")
    
    # Check for existing user token
    user_token_info = oauth_manager.get_user_token_info()
    if user_token_info:
        print(f"✅ Found existing user token:")
        print(f"   Created: {user_token_info.created_at}")
        print(f"   Expires: {user_token_info.expires_at}")
        print(f"   User ID: {user_token_info.user_id or 'N/A'}")
        print(f"   Scopes: {len(user_token_info.scope.split())} scopes")
        
        # Test token access
        try:
            token = await oauth_manager.get_token()
            print(f"✅ Token retrieved successfully: {token[:20]}...")
            return True
        except ConsentRequiredException as e:
            print(f"⚠️  Token expired or invalid: {e}")
            return False
    else:
        print("⚠️  No user token found")
        return False


async def test_oauth_flow():
    """Test the complete OAuth flow interactively."""
    ctx = TestContext()
    
    print("🚀 eBay OAuth Flow Test (NEW Architecture)")
    print("=" * 60)
    
    # First, test the OAuth architecture directly
    has_valid_token = await test_oauth_architecture()
    
    # Step 1: Check current consent status via MCP tools
    print("\n1️⃣ Checking current consent status via MCP tools...")
    try:
        status_result = await oauth_consent_tools.check_user_consent_status.fn(ctx)
        status_data = json.loads(status_result)
        
        if status_data["status"] == "success" and status_data["data"].get("has_consent", False):
            print("✅ Valid consent found via MCP tools!")
            print(f"   User ID: {status_data['data'].get('user_id', 'N/A')}")
            print(f"   Expires: {status_data['data'].get('expires_at', 'N/A')}")
            print(f"   Scopes: {len(status_data['data'].get('granted_scopes', []))} scopes")
            
            # Ask if user wants to revoke and start fresh
            response = input("\n🔄 Do you want to revoke existing consent and start fresh? (y/N): ")
            if response.lower() == 'y':
                print("\n🗑️  Revoking existing consent...")
                await oauth_consent_tools.revoke_user_consent.fn(ctx)
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
        consent_result = await oauth_consent_tools.initiate_user_consent.fn(ctx)
        consent_data = json.loads(consent_result)
        
        if consent_data["status"] != "success":
            print(f"❌ Failed to initiate consent: {consent_data['error_message']}")
            return
        
        auth_url = consent_data['data']['authorization_url']
        browser_opened = consent_data['data'].get('browser_opened', False)
        redirect_uri = consent_data['data'].get('redirect_uri', 'localhost')
        
        print(f"\n🌐 Authorization URL: {auth_url}")
        print(f"🔍 Browser opened automatically: {browser_opened}")
        print(f"🔗 Redirect URI: {redirect_uri}")
        
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
        complete_result = await oauth_consent_tools.complete_user_consent.fn(ctx, callback_url)
        complete_data = json.loads(complete_result)
        
        if complete_data["status"] == "success":
            print("✅ OAuth flow completed successfully!")
            expires_at = complete_data['data'].get('expires_at', 'N/A')
            scopes = complete_data['data'].get('scopes', [])
            
            print(f"   Expires at: {expires_at}")
            print(f"   Scopes: {len(scopes)} scopes granted")
            
            # Show a few sample scopes
            if scopes:
                print("   Sample scopes:")
                for scope in scopes[:5]:  # Show first 5 scopes
                    print(f"     - {scope}")
                if len(scopes) > 5:
                    print(f"     ... and {len(scopes) - 5} more")
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
    
    # Test 1: Account API via MCP tool
    print("\n🔧 Testing Account API via MCP tool...")
    try:
        result = await get_seller_standards.fn(ctx, program="PROGRAM_US", cycle="CURRENT")
        data = json.loads(result)
        if data["status"] == "success":
            seller_level = data["data"]["seller_standards"]["seller_level"]
            data_source = data["data"]["seller_standards"].get("data_source", "unknown")
            print(f"✅ Account API: Seller level: {seller_level} (source: {data_source})")
        else:
            print(f"❌ Account API: {data['error_message']}")
    except Exception as e:
        print(f"❌ Account API error: {str(e)}")
    
    # Test 2: Payment Policy API via REST client directly
    print("\n💳 Testing Payment Policy API via REST client...")
    try:
        # Initialize OAuth manager and REST client
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
        
        # Test API call
        params = {
            "marketplace_id": MarketplaceIdEnum.EBAY_US.value,
            "limit": 5,
            "offset": 0
        }
        
        result = await rest_client.get(
            "/sell/account/v1/payment_policy",
            params=params
        )
        
        policies = result.get('paymentPolicies', [])
        print(f"✅ Payment Policy API: Found {len(policies)} policies")
        
        # Show policy details
        for i, policy in enumerate(policies[:3]):  # Show first 3 policies
            print(f"   Policy {i+1}: {policy.get('name', 'Unknown')} (ID: {policy.get('paymentPolicyId', 'N/A')})")
        
        await rest_client.close()
        
    except ConsentRequiredException as e:
        print(f"⚠️  Payment Policy API: User consent required: {e}")
    except Exception as e:
        print(f"❌ Payment Policy API error: {str(e)}")
    
    # Test 3: Return Policy API via REST client directly
    print("\n🔄 Testing Return Policy API via REST client...")
    try:
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
        
        # Test API call
        params = {
            "marketplace_id": MarketplaceIdEnum.EBAY_US.value,
            "limit": 5,
            "offset": 0
        }
        
        result = await rest_client.get(
            "/sell/account/v1/return_policy",
            params=params
        )
        
        policies = result.get('returnPolicies', [])
        print(f"✅ Return Policy API: Found {len(policies)} policies")
        
        # Show policy details
        for i, policy in enumerate(policies[:3]):  # Show first 3 policies
            print(f"   Policy {i+1}: {policy.get('name', 'Unknown')} (ID: {policy.get('returnPolicyId', 'N/A')})")
        
        await rest_client.close()
        
    except ConsentRequiredException as e:
        print(f"⚠️  Return Policy API: User consent required: {e}")
    except Exception as e:
        print(f"❌ Return Policy API error: {str(e)}")
    
    print("\n🎉 OAuth flow and API testing complete!")
    print("✅ All tests used the NEW OAuth architecture:")
    print("   - Centralized OAuthManager in oauth.py")
    print("   - ConsentRequiredException for proper error handling")
    print("   - MCP tools as thin wrappers around OAuthManager")
    print("   - Single source of truth for token management")


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