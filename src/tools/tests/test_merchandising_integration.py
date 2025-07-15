"""Integration tests for eBay Merchandising API using real sandbox endpoints.

WARNING: These tests require valid eBay sandbox credentials and will make real API calls.
Set EBAY_RUN_INTEGRATION_TESTS=true and provide valid credentials to run.
"""
import os
import json
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from fastmcp import Context
from data_types import ResponseStatus, ErrorCode
from tools.merchandising_api import (
    get_most_watched_items,
    get_related_category_items,
    get_similar_items,
    get_top_selling_products
)
from config import EbayConfig


# Integration tests are now enabled by default
# To skip them, use: pytest -m "not integration"
pytestmark = pytest.mark.integration


def has_valid_credentials() -> bool:
    """Check if we have valid eBay credentials."""
    app_id = os.getenv("EBAY_APP_ID", "")
    return (
        len(app_id) >= 32 and 
        not app_id.startswith("test") and
        app_id != "your-app-id-here"
    )


@pytest.fixture
def real_config():
    """Create real eBay configuration from environment."""
    if not os.getenv("EBAY_APP_ID"):
        pytest.skip("EBAY_APP_ID not set in environment")
    
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
    logger = logging.getLogger("ebay_merchandising_integration_test")
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


# Known sandbox test data (these may need updates based on actual sandbox content)
SANDBOX_CATEGORY_ELECTRONICS = "293"  # Electronics category
SANDBOX_CATEGORY_COLLECTIBLES = "1"   # Collectibles category
SANDBOX_TEST_ITEM_ID = "110551991234"  # Example sandbox item (may not exist)


class TestRealGetMostWatchedItems:
    """Test get_most_watched_items with real sandbox API."""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_real_most_watched_items_no_category(self, real_context):
        """Test getting most watched items without category filter."""
        result_json = await get_most_watched_items.fn(
            max_results=10,
            ctx=real_context
        )
        
        result = json.loads(result_json)
        print(f"\nMost Watched Items Response: {json.dumps(result, indent=2)}")
        
        if result["status"] == ResponseStatus.SUCCESS.value:
            print(f"\n✓ Found {len(result['data']['items'])} most watched items")
            
            if result["data"]["items"]:
                first_item = result["data"]["items"][0]
                print(f"\nMost watched item:")
                print(f"  - Title: {first_item['title']}")
                print(f"  - Watch count: {first_item.get('watch_count', 'N/A')}")
                print(f"  - Price: ${first_item['price']['value']}")
        else:
            print(f"\n✗ Failed to get most watched items: {result.get('error_message')}")
            # Authentication errors are expected without valid credentials
            if not has_valid_credentials():
                assert "auth" in result.get("error_message", "").lower() or \
                       "invalid" in result.get("error_message", "").lower()
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_real_most_watched_items_with_category(self, real_context):
        """Test getting most watched items in specific category."""
        result_json = await get_most_watched_items.fn(
            category_id=SANDBOX_CATEGORY_ELECTRONICS,
            max_results=5,
            ctx=real_context
        )
        
        result = json.loads(result_json)
        
        if result["status"] == ResponseStatus.SUCCESS.value:
            print(f"\n✓ Found {len(result['data']['items'])} items in Electronics category")
            assert result["data"]["category_id"] == SANDBOX_CATEGORY_ELECTRONICS
        else:
            print(f"\n✗ Category search failed: {result.get('error_message')}")


class TestRealGetRelatedCategoryItems:
    """Test get_related_category_items with real sandbox API."""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_real_related_category_items(self, real_context):
        """Test getting items from related categories."""
        result_json = await get_related_category_items.fn(
            category_id=SANDBOX_CATEGORY_ELECTRONICS,
            max_results=10,
            ctx=real_context
        )
        
        result = json.loads(result_json)
        print(f"\nRelated Category Items: {json.dumps(result, indent=2)}")
        
        if result["status"] == ResponseStatus.SUCCESS.value:
            print(f"\n✓ Found {len(result['data']['items'])} items")
            print(f"✓ From {len(result['data']['related_categories'])} related categories")
            
            if result["data"]["related_categories"]:
                print(f"\nRelated categories found:")
                for cat in result["data"]["related_categories"][:5]:
                    print(f"  - {cat}")
        else:
            print(f"\n✗ Failed to get related items: {result.get('error_message')}")


class TestRealGetSimilarItems:
    """Test get_similar_items with real sandbox API."""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_real_similar_items(self, real_context):
        """Test finding similar items."""
        # First, try to get a real item ID from most watched
        watched_result = await get_most_watched_items.fn(
            max_results=1,
            ctx=real_context
        )
        
        watched_data = json.loads(watched_result)
        
        if watched_data["status"] == ResponseStatus.SUCCESS.value and watched_data["data"]["items"]:
            test_item_id = watched_data["data"]["items"][0]["item_id"]
            print(f"\nUsing item ID from most watched: {test_item_id}")
        else:
            test_item_id = SANDBOX_TEST_ITEM_ID
            print(f"\nUsing default test item ID: {test_item_id}")
        
        # Now find similar items
        result_json = await get_similar_items.fn(
            item_id=test_item_id,
            max_results=10,
            ctx=real_context
        )
        
        result = json.loads(result_json)
        print(f"\nSimilar Items Response: {json.dumps(result, indent=2)}")
        
        if result["status"] == ResponseStatus.SUCCESS.value:
            print(f"\n✓ Found {len(result['data']['items'])} similar items")
            assert result["data"]["source_item_id"] == test_item_id
        else:
            print(f"\n✗ Failed to find similar items: {result.get('error_message')}")
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_real_similar_items_invalid_id(self, real_context):
        """Test error handling for invalid item ID."""
        result_json = await get_similar_items.fn(
            item_id="999999999999999",  # Invalid ID
            max_results=5,
            ctx=real_context
        )
        
        result = json.loads(result_json)
        
        if not has_valid_credentials():
            # With invalid credentials, we expect auth error
            assert result["status"] == ResponseStatus.ERROR.value
        else:
            # With valid credentials, might get item not found or empty results
            print(f"\nResult for invalid item: {result['status']}")


class TestRealGetTopSellingProducts:
    """Test get_top_selling_products with real sandbox API."""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_real_top_selling_products(self, real_context):
        """Test getting top selling products."""
        result_json = await get_top_selling_products.fn(
            max_results=10,
            ctx=real_context
        )
        
        result = json.loads(result_json)
        print(f"\nTop Selling Products Response: {json.dumps(result, indent=2)}")
        
        if result["status"] == ResponseStatus.SUCCESS.value:
            print(f"\n✓ Found {len(result['data']['products'])} top selling products")
            
            if result["data"]["products"]:
                first_product = result["data"]["products"][0]
                print(f"\nTop product:")
                print(f"  - Title: {first_product['title']}")
                print(f"  - Price range: ${first_product['price_range']['min']} - ${first_product['price_range']['max']}")
                print(f"  - Reviews: {first_product.get('review_count', 0)}")
                print(f"  - Rating: {first_product.get('rating', 'N/A')}")
        else:
            print(f"\n✗ Failed to get top products: {result.get('error_message')}")
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_real_top_selling_products_by_category(self, real_context):
        """Test getting top selling products in specific category."""
        result_json = await get_top_selling_products.fn(
            category_id=SANDBOX_CATEGORY_COLLECTIBLES,
            max_results=5,
            ctx=real_context
        )
        
        result = json.loads(result_json)
        
        if result["status"] == ResponseStatus.SUCCESS.value:
            print(f"\n✓ Found {len(result['data']['products'])} products in Collectibles")
            assert result["data"]["category_id"] == SANDBOX_CATEGORY_COLLECTIBLES
        else:
            print(f"\n✗ Category product search failed")


class TestRealErrorScenarios:
    """Test error handling with real API."""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_real_invalid_category_error(self, real_context):
        """Test with invalid category ID."""
        result_json = await get_related_category_items.fn(
            category_id="999999999",  # Invalid category
            ctx=real_context
        )
        
        result = json.loads(result_json)
        assert result["status"] == ResponseStatus.ERROR.value
        print(f"\n✓ Correctly handled invalid category: {result.get('error_message', '')[:100]}...")
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_real_rate_limiting(self, real_context):
        """Test API behavior under rapid requests."""
        # Make 5 rapid requests
        tasks = []
        for i in range(5):
            task = get_most_watched_items.fn(max_results=1, ctx=real_context)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        success_count = sum(1 for r in results if not isinstance(r, Exception) 
                          and json.loads(r)["status"] == ResponseStatus.SUCCESS.value)
        
        print(f"\n✓ Completed {success_count}/5 rapid requests successfully")
        
        # With sandbox, we shouldn't hit rate limits with just 5 requests
        if has_valid_credentials():
            assert success_count >= 3, "Too many requests failed"


class TestRealAuthenticationErrors:
    """Test authentication error handling."""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_invalid_credentials_merchandising(self, real_context):
        """Test Merchandising API with invalid credentials."""
        if has_valid_credentials():
            pytest.skip("This test requires invalid credentials")
        
        print("\n=== Testing Merchandising API with invalid credentials ===")
        
        result_json = await get_most_watched_items.fn(ctx=real_context)
        result = json.loads(result_json)
        
        print(f"\nError Response: {json.dumps(result, indent=2)}")
        
        assert result["status"] == ResponseStatus.ERROR.value
        
        error_msg = result.get("error_message", "").lower()
        assert any([
            "auth" in error_msg,
            "invalid" in error_msg,
            "credential" in error_msg,
            "application" in error_msg
        ]), f"Expected authentication error, got: {error_msg}"
        
        print("✓ Merchandising API correctly rejected invalid credentials")


if __name__ == "__main__":
    # Allow running this file directly for debugging
    print("\n" + "="*60)
    print("eBay Merchandising API Sandbox Integration Tests")
    print("="*60)
    print("\nRequirements:")
    print("1. Set EBAY_RUN_INTEGRATION_TESTS=true")
    print("2. Provide valid sandbox credentials:")
    print("   - EBAY_APP_ID (32+ characters)")
    print("\nNote: These tests will make real API calls to eBay sandbox!")
    print("="*60 + "\n")
    
    asyncio.run(pytest.main([__file__, "-v", "-s"]))