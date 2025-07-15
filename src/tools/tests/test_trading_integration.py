"""Integration tests for eBay Trading API tools using real sandbox API.

WARNING: These tests require valid eBay sandbox credentials and will make real API calls.
Set EBAY_RUN_INTEGRATION_TESTS=true and provide valid credentials to run.
"""
import os
import json
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime
from fastmcp import Context
from data_types import ResponseStatus, ErrorCode
from tools.trading_api import (
    create_listing,
    revise_listing,
    end_listing,
    get_my_ebay_selling,
    get_user_info
)
from config import EbayConfig


# Integration tests are now enabled by default
# To skip them, use: pytest -m "not integration"
pytestmark = pytest.mark.integration


def has_valid_trading_credentials() -> bool:
    """Check if we have valid Trading API credentials."""
    app_id = os.getenv("EBAY_APP_ID", "")
    cert_id = os.getenv("EBAY_CERT_ID", "")
    dev_id = os.getenv("EBAY_DEV_ID", "")
    
    return (
        len(app_id) >= 32 and 
        len(cert_id) >= 32 and
        len(dev_id) >= 32 and
        not any(cred.startswith("test") for cred in [app_id, cert_id, dev_id])
    )


@pytest.fixture
def real_config():
    """Create real eBay configuration from environment."""
    if not has_valid_trading_credentials():
        pytest.skip("Valid Trading API credentials not found in environment")
    
    config = EbayConfig.from_env()
    config.sandbox_mode = True  # Always use sandbox for testing
    return config


@pytest.fixture
def real_context(real_config):
    """Create a mock context with real configuration."""
    ctx = AsyncMock(spec=Context)
    ctx.info = AsyncMock()
    ctx.error = AsyncMock()
    ctx.debug = AsyncMock()
    ctx.warning = AsyncMock()
    ctx.report_progress = AsyncMock()
    
    # Mock server with real config
    ctx.server = MagicMock()
    ctx.server.config = real_config
    
    # Setup real logger
    import logging
    logger = logging.getLogger("ebay_trading_integration_test")
    logger.setLevel(logging.DEBUG)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    # Mock logger methods
    logger.tool_called = lambda *args, **kwargs: logger.info(f"Tool called: {args}")
    logger.tool_failed = lambda *args, **kwargs: logger.error(f"Tool failed: {args}")
    logger.external_api_called = lambda *args, **kwargs: logger.info(f"API called: {args}")
    logger.external_api_failed = lambda *args, **kwargs: logger.error(f"API failed: {args}")
    
    ctx.server.logger = logger
    
    return ctx


@pytest.fixture
def test_listing_data():
    """Generate test listing data for sandbox."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return {
        "title": f"Test Item - MCP Integration Test {timestamp}",
        "description": "This is a test listing created by the MCP Trading API integration tests. Please ignore.",
        "category_id": "377",  # Sandbox category: Other -> Test Auctions
        "start_price": 0.99,
        "buy_it_now_price": 9.99,
        "quantity": 1,
        "duration": "Days_3",
        "condition_id": "1000",  # New
        "shipping_service": "USPSPriority",
        "shipping_cost": 5.99,
        "dispatch_time": 1,
        "returns_accepted": True,
        "return_period": "Days_30",
        "payment_methods": ["PayPal"],
        "paypal_email": "test@example.com",
        "postal_code": "90210",
        "country": "US",
        "picture_urls": [
            "https://i.ebayimg.com/images/g/0w4AAOSwYIxX2oIH/s-l1600.jpg"  # eBay sample image
        ]
    }


class TestRealGetUserInfo:
    """Test get_user_info with real sandbox API."""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_real_get_authenticated_user(self, real_context):
        """Test getting authenticated user info from sandbox."""
        result_json = await get_user_info.fn(ctx=real_context)
        
        result = json.loads(result_json)
        print(f"\nUser Info Response: {json.dumps(result, indent=2)}")
        
        if result["status"] == ResponseStatus.SUCCESS.value:
            # Successful authentication
            assert "user_id" in result["data"]
            assert "email" in result["data"]
            assert "feedback" in result["data"]
            print(f"\n✓ Successfully authenticated as: {result['data']['user_id']}")
            print(f"✓ Feedback score: {result['data']['feedback']['score']}")
            print(f"✓ Account status: {result['data']['status']}")
        else:
            # Authentication failed - expected with invalid credentials
            assert result["status"] == ResponseStatus.ERROR.value
            print(f"\n✗ Authentication failed (expected with test credentials)")
            print(f"✗ Error: {result.get('error_message', 'Unknown error')}")


class TestRealGetMyEbaySelling:
    """Test get_my_ebay_selling with real sandbox API."""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_real_get_active_listings(self, real_context):
        """Test getting active listings from sandbox."""
        result_json = await get_my_ebay_selling.fn(
            listing_type="Active",
            page_size=10,
            ctx=real_context
        )
        
        result = json.loads(result_json)
        print(f"\nActive Listings Response: {json.dumps(result, indent=2)}")
        
        if result["status"] == ResponseStatus.SUCCESS.value:
            print(f"\n✓ Found {len(result['data']['listings'])} active listings")
            print(f"✓ Total value: ${result['data']['summary']['total_value']:.2f}")
            
            # Display first listing if any
            if result["data"]["listings"]:
                first = result["data"]["listings"][0]
                print(f"\nFirst listing:")
                print(f"  - Title: {first['title']}")
                print(f"  - Price: ${first['current_price']}")
                print(f"  - Item ID: {first['item_id']}")
        else:
            print(f"\n✗ Failed to get listings: {result.get('error_message', 'Unknown error')}")
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_real_get_sold_listings(self, real_context):
        """Test getting sold listings from sandbox."""
        result_json = await get_my_ebay_selling.fn(
            listing_type="Sold",
            page_size=10,
            ctx=real_context
        )
        
        result = json.loads(result_json)
        print(f"\nSold Listings: Found {len(result.get('data', {}).get('listings', []))} items")


class TestRealCreateListing:
    """Test creating real listings in sandbox."""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_real_create_basic_listing(self, real_context, test_listing_data):
        """Test creating a basic listing in sandbox."""
        result_json = await create_listing.fn(
            title=test_listing_data["title"],
            description=test_listing_data["description"],
            category_id=test_listing_data["category_id"],
            start_price=test_listing_data["start_price"],
            quantity=test_listing_data["quantity"],
            duration=test_listing_data["duration"],
            condition_id=test_listing_data["condition_id"],
            shipping_service=test_listing_data["shipping_service"],
            shipping_cost=test_listing_data["shipping_cost"],
            dispatch_time=test_listing_data["dispatch_time"],
            postal_code=test_listing_data["postal_code"],
            country=test_listing_data["country"],
            ctx=real_context
        )
        
        result = json.loads(result_json)
        print(f"\nCreate Listing Response: {json.dumps(result, indent=2)}")
        
        if result["status"] == ResponseStatus.SUCCESS.value:
            item_id = result["data"]["item_id"]
            print(f"\n✓ Successfully created listing: {item_id}")
            print(f"✓ Title: {result['data']['title']}")
            print(f"✓ Listing URL: {result['data']['listing_url']}")
            print(f"✓ Total fees: ${result['data']['fees']['total']:.2f}")
            
            # Return item_id for cleanup
            return item_id
        else:
            print(f"\n✗ Failed to create listing: {result.get('error_message', 'Unknown error')}")
            return None
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_real_create_with_pictures(self, real_context, test_listing_data):
        """Test creating a listing with pictures in sandbox."""
        # Add multiple pictures
        test_listing_data["picture_urls"] = [
            "https://i.ebayimg.com/images/g/0w4AAOSwYIxX2oIH/s-l1600.jpg",
            "https://i.ebayimg.com/images/g/H~MAAOSwZQxW4kRH/s-l1600.jpg"
        ]
        
        result_json = await create_listing.fn(
            **test_listing_data,
            ctx=real_context
        )
        
        result = json.loads(result_json)
        
        if result["status"] == ResponseStatus.SUCCESS.value:
            print(f"\n✓ Created listing with {len(test_listing_data['picture_urls'])} pictures")
            return result["data"]["item_id"]
        else:
            print(f"\n✗ Failed to create listing with pictures")
            return None


class TestRealReviseEndListing:
    """Test revising and ending listings in sandbox."""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_real_listing_lifecycle(self, real_context, test_listing_data):
        """Test complete lifecycle: create, revise, and end a listing."""
        # Step 1: Create a listing
        print("\n=== Step 1: Creating listing ===")
        create_result = await create_listing.fn(
            **test_listing_data,
            ctx=real_context
        )
        
        create_response = json.loads(create_result)
        if create_response["status"] != ResponseStatus.SUCCESS.value:
            pytest.skip(f"Cannot test lifecycle - listing creation failed: {create_response.get('error_message')}")
        
        item_id = create_response["data"]["item_id"]
        print(f"✓ Created listing: {item_id}")
        
        # Wait a moment for eBay to process
        await asyncio.sleep(2)
        
        # Step 2: Revise the listing
        print("\n=== Step 2: Revising listing ===")
        new_price = test_listing_data["start_price"] + 5.00
        revise_result = await revise_listing.fn(
            item_id=item_id,
            title=f"{test_listing_data['title']} - REVISED",
            price=new_price,
            quantity=2,
            ctx=real_context
        )
        
        revise_response = json.loads(revise_result)
        if revise_response["status"] == ResponseStatus.SUCCESS.value:
            print(f"✓ Successfully revised listing {item_id}")
            print(f"✓ Updated fields: {', '.join(revise_response['data']['revised_fields'])}")
        else:
            print(f"✗ Failed to revise: {revise_response.get('error_message')}")
        
        # Wait a moment
        await asyncio.sleep(2)
        
        # Step 3: End the listing
        print("\n=== Step 3: Ending listing ===")
        end_result = await end_listing.fn(
            item_id=item_id,
            reason="NotAvailable",
            ctx=real_context
        )
        
        end_response = json.loads(end_result)
        if end_response["status"] == ResponseStatus.SUCCESS.value:
            print(f"✓ Successfully ended listing {item_id}")
            print(f"✓ End time: {end_response['data']['end_time']}")
        else:
            print(f"✗ Failed to end listing: {end_response.get('error_message')}")


class TestRealErrorScenarios:
    """Test error handling with real API."""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_real_invalid_category(self, real_context):
        """Test creating listing with invalid category."""
        result_json = await create_listing.fn(
            title="Test Invalid Category",
            description="This should fail",
            category_id="999999999",  # Invalid category
            start_price=0.99,
            quantity=1,
            condition_id="1000",
            shipping_service="USPSPriority",
            shipping_cost=5.99,
            ctx=real_context
        )
        
        result = json.loads(result_json)
        assert result["status"] == ResponseStatus.ERROR.value
        print(f"\n✓ Correctly handled invalid category error: {result.get('error_message', '')[:100]}...")
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_real_revise_nonexistent_item(self, real_context):
        """Test revising a non-existent item."""
        result_json = await revise_listing.fn(
            item_id="999999999999",  # Non-existent item
            title="New Title",
            ctx=real_context
        )
        
        result = json.loads(result_json)
        assert result["status"] == ResponseStatus.ERROR.value
        print(f"\n✓ Correctly handled non-existent item error: {result.get('error_message', '')[:100]}...")


class TestRealAuthenticationErrors:
    """Test authentication error handling."""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_invalid_credentials_error(self, real_context):
        """Test API behavior with invalid credentials."""
        # Only run this if we're using test/invalid credentials
        if has_valid_trading_credentials():
            pytest.skip("This test requires invalid credentials")
        
        print("\n=== Testing with invalid credentials ===")
        
        # Try to get user info with bad credentials
        result_json = await get_user_info.fn(ctx=real_context)
        result = json.loads(result_json)
        
        print(f"\nError Response: {json.dumps(result, indent=2)}")
        
        assert result["status"] == ResponseStatus.ERROR.value
        
        # Check for auth-related error
        error_msg = result.get("error_message", "").lower()
        assert any([
            "auth" in error_msg,
            "invalid" in error_msg,
            "credential" in error_msg,
            "token" in error_msg
        ]), f"Expected authentication error, got: {error_msg}"
        
        print("✓ API correctly rejected invalid credentials")


class TestRealSandboxBehavior:
    """Test sandbox-specific behaviors."""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_sandbox_test_user(self, real_context):
        """Test that we can identify sandbox test users."""
        # Get authenticated user info
        result_json = await get_user_info.fn(ctx=real_context)
        result = json.loads(result_json)
        
        if result["status"] == ResponseStatus.SUCCESS.value:
            user_id = result["data"]["user_id"]
            print(f"\n✓ Sandbox user: {user_id}")
            
            # Sandbox users often have specific patterns
            if "testuser" in user_id.lower() or "TESTUSER" in user_id:
                print("✓ Confirmed sandbox test user pattern")
        else:
            print("\n✗ Could not verify sandbox user")


if __name__ == "__main__":
    # Allow running this file directly for debugging
    print("\n" + "="*60)
    print("eBay Trading API Sandbox Integration Tests")
    print("="*60)
    print("\nRequirements:")
    print("1. Set EBAY_RUN_INTEGRATION_TESTS=true")
    print("2. Provide valid sandbox credentials:")
    print("   - EBAY_APP_ID (32+ characters)")
    print("   - EBAY_CERT_ID (32+ characters)")
    print("   - EBAY_DEV_ID (32+ characters)")
    print("3. Have a sandbox test user account")
    print("\nNote: These tests will create real listings in the sandbox!")
    print("="*60 + "\n")
    
    asyncio.run(pytest.main([__file__, "-v", "-s"]))