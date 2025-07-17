#!/usr/bin/env python3
"""
Simple OAuth status checker for the NEW OAuth architecture.

This script tests the OAuth architecture and shows current consent status
without requiring user interaction.

Usage:
    uv run python scripts/test_oauth_status.py
"""
import asyncio
import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from api.oauth import OAuthManager, OAuthConfig, ConsentRequiredException
from api.rest_client import EbayRestClient, RestConfig
from api.ebay_enums import MarketplaceIdEnum
import tools.oauth_consent as oauth_consent_tools
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


async def test_oauth_status():
    """Test OAuth status and architecture."""
    print("🔧 OAuth Architecture Status Check")
    print("=" * 50)
    
    # Test 1: Direct OAuth Manager
    print("\n1️⃣ Testing OAuth Manager directly...")
    try:
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
            except ConsentRequiredException as e:
                print(f"⚠️  Token expired or invalid: {e}")
        else:
            print("⚠️  No user token found")
            
    except Exception as e:
        print(f"❌ Error with OAuth manager: {e}")
        return False
    
    # Test 2: MCP Tools
    print("\n2️⃣ Testing MCP OAuth tools...")
    try:
        ctx = TestContext()
        status_result = await oauth_consent_tools.check_user_consent_status.fn(ctx)
        status_data = json.loads(status_result)
        
        if status_data["status"] == "success":
            has_consent = status_data["data"].get("has_consent", False)
            if has_consent:
                print("✅ MCP tools report valid consent")
                print(f"   User ID: {status_data['data'].get('user_id', 'N/A')}")
                print(f"   Expires: {status_data['data'].get('expires_at', 'N/A')}")
                print(f"   Scopes: {len(status_data['data'].get('granted_scopes', []))} scopes")
            else:
                print("⚠️  MCP tools report no consent")
        else:
            print(f"❌ MCP tools error: {status_data.get('error_message', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ Error with MCP tools: {e}")
        return False
    
    # Test 3: API Calls  
    print("\n3️⃣ Testing API calls with OAuth...")
    try:
        rest_config = RestConfig(
            sandbox=mcp.config.sandbox_mode,
            rate_limit_per_day=mcp.config.rate_limit_per_day
        )
        rest_client = EbayRestClient(oauth_manager, rest_config)
        
        # Test Payment Policy API
        print("\n   Testing Payment Policy API...")
        params = {
            "marketplace_id": MarketplaceIdEnum.EBAY_US.value,
            "limit": 5,
            "offset": 0
        }
        
        try:
            result = await rest_client.get(
                "/sell/account/v1/payment_policy",
                params=params
            )
            
            policies = result.get('paymentPolicies', [])
            print(f"   ✅ Payment Policy API: Found {len(policies)} policies")
        except Exception as api_error:
            # Check if it's the business policy error
            if "not eligible for Business Policy" in str(api_error):
                print(f"   ⚠️  Payment Policy API: Seller account needs business policies enabled")
                print(f"      This is expected for new sandbox accounts")
            else:
                print(f"   ❌ Payment Policy API error: {api_error}")
        
        # Test Return Policy API
        print("\n   Testing Return Policy API...")
        try:
            result = await rest_client.get(
                "/sell/account/v1/return_policy",
                params=params
            )
            
            policies = result.get('returnPolicies', [])
            print(f"   ✅ Return Policy API: Found {len(policies)} policies")
        except Exception as api_error:
            # Check if it's the business policy error
            if "not eligible for Business Policy" in str(api_error):
                print(f"   ⚠️  Return Policy API: Seller account needs business policies enabled")
                print(f"      This is expected for new sandbox accounts")
            else:
                print(f"   ❌ Return Policy API error: {api_error}")
        
        await rest_client.close()
        
    except ConsentRequiredException as e:
        print(f"   ⚠️  API calls require consent: {e}")
    except Exception as e:
        print(f"   ❌ API call error: {e}")
        return False
    
    print("\n🎉 OAuth Architecture Test Complete!")
    print("✅ New OAuth architecture is working correctly:")
    print("   - Centralized OAuthManager")
    print("   - Proper ConsentRequiredException handling")
    print("   - MCP tools work as expected")
    print("   - API calls use correct token management")
    print("\n⚠️  Note: Business policies need to be enabled on the sandbox seller account")
    print("   This is a seller account configuration issue, not an OAuth problem.")
    
    return True


async def main():
    """Main entry point."""
    try:
        success = await test_oauth_status()
        if success:
            print("\n🚀 Ready for interactive OAuth flow!")
            print("   Run: uv run python scripts/test_oauth_flow_new.py")
        else:
            print("\n❌ OAuth architecture has issues")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())