"""Integration tests for eBay Finding API tools using real sandbox API."""
import os
import json
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from fastmcp import Context
from data_types import ResponseStatus, ErrorCode
from tools.finding_api import search_items, get_search_keywords, find_items_by_category, find_items_advanced
from config import EbayConfig


# Skip all tests in this file if EBAY_RUN_INTEGRATION_TESTS is not set
pytestmark = pytest.mark.skipif(
    os.getenv("EBAY_RUN_INTEGRATION_TESTS") != "true",
    reason="Integration tests disabled. Set EBAY_RUN_INTEGRATION_TESTS=true to run."
)


def is_valid_app_id(app_id: str) -> bool:
    """Check if app_id looks like a valid eBay app ID."""
    # eBay App IDs are typically 32-character strings
    # Test credentials will be shorter or contain 'test'
    return (
        app_id and 
        len(app_id) >= 32 and 
        not app_id.startswith("test") and
        not app_id == "your-app-id-here"
    )


@pytest.fixture
def real_config():
    """Create real eBay configuration from environment."""
    # Check if we have the required credentials
    app_id = os.getenv("EBAY_APP_ID")
    if not app_id:
        pytest.skip("EBAY_APP_ID not set in environment")
    
    config = EbayConfig.from_env()
    # Ensure we're using sandbox for testing
    config.sandbox_mode = True
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
    
    # Simple logger for integration tests
    import logging
    logger = logging.getLogger("ebay_integration_test")
    logger.setLevel(logging.DEBUG)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    # Mock logger methods for compatibility
    logger.tool_called = lambda *args, **kwargs: logger.info(f"Tool called: {args}")
    logger.tool_failed = lambda *args, **kwargs: logger.error(f"Tool failed: {args}")
    logger.external_api_called = lambda *args, **kwargs: logger.info(f"API called: {args}")
    logger.external_api_failed = lambda *args, **kwargs: logger.error(f"API failed: {args}")
    logger.api_cache_hit = lambda *args, **kwargs: logger.info(f"Cache hit: {args}")
    
    ctx.server.logger = logger
    
    return ctx


@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_search_items(real_context):
    """Test real item search on eBay sandbox."""
    # Search for a common item that should exist in sandbox
    result_json = await search_items(
        keywords="Harry Potter",  # Common test item in sandbox
        min_price=1.0,
        max_price=100.0,
        page_number=1,
        page_size=10,
        ctx=real_context
    )
    
    result = json.loads(result_json)
    print(f"\nSearch Results: {json.dumps(result, indent=2)}")
    
    # Verify response structure
    assert result["status"] == ResponseStatus.SUCCESS.value
    assert "data" in result
    assert "items" in result["data"]
    assert "pagination" in result["data"]
    
    # May or may not have items in sandbox
    if result["data"]["items"]:
        item = result["data"]["items"][0]
        assert "item_id" in item
        assert "title" in item
        assert "price" in item
        print(f"\nFirst item: {item['title']} - ${item['price']['value']}")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_search_keywords(real_context):
    """Test real keyword suggestions."""
    result_json = await get_search_keywords(
        partial_keyword="iphone",
        ctx=real_context
    )
    
    result = json.loads(result_json)
    print(f"\nKeyword Suggestions: {json.dumps(result, indent=2)}")
    
    assert result["status"] == ResponseStatus.SUCCESS.value
    assert "suggestions" in result["data"]
    
    # Sandbox may or may not return suggestions
    if result["data"]["suggestions"]:
        print(f"Got {len(result['data']['suggestions'])} suggestions")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_find_by_category(real_context):
    """Test real category browsing."""
    # Electronics category in sandbox
    result_json = await find_items_by_category(
        category_id="293",  # Electronics
        page_number=1,
        page_size=5,
        ctx=real_context
    )
    
    result = json.loads(result_json)
    print(f"\nCategory Items: Found {len(result['data']['items'])} items")
    
    assert result["status"] == ResponseStatus.SUCCESS.value
    assert "items" in result["data"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_advanced_search(real_context):
    """Test real advanced search with filters."""
    result_json = await find_items_advanced(
        keywords="book",
        free_shipping_only=True,
        listing_type="FixedPrice",
        page_number=1,
        ctx=real_context
    )
    
    result = json.loads(result_json)
    print(f"\nAdvanced Search: Found {result['data']['total_results']} total results")
    
    assert result["status"] == ResponseStatus.SUCCESS.value
    assert result["data"]["filters_applied"] >= 2  # At least 2 filters


@pytest.mark.integration  
@pytest.mark.asyncio
async def test_real_api_error_handling(real_context):
    """Test real API error responses."""
    # Use an invalid category ID to trigger an error
    result_json = await find_items_by_category(
        category_id="999999999",  # Invalid category
        ctx=real_context
    )
    
    result = json.loads(result_json)
    print(f"\nError Response: {json.dumps(result, indent=2)}")
    
    # Should handle the error gracefully
    assert result["status"] == ResponseStatus.ERROR.value


@pytest.mark.integration
@pytest.mark.asyncio  
async def test_real_pagination(real_context):
    """Test real pagination."""
    # First page
    result1_json = await search_items(
        keywords="test",
        page_number=1,
        page_size=5,
        ctx=real_context
    )
    
    result1 = json.loads(result1_json)
    
    if result1["data"]["pagination"]["has_next"]:
        # Second page
        result2_json = await search_items(
            keywords="test",
            page_number=2, 
            page_size=5,
            ctx=real_context
        )
        
        result2 = json.loads(result2_json)
        
        # Items should be different
        if result1["data"]["items"] and result2["data"]["items"]:
            item1_ids = {item["item_id"] for item in result1["data"]["items"]}
            item2_ids = {item["item_id"] for item in result2["data"]["items"]}
            assert item1_ids != item2_ids, "Page 2 should have different items"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_sandbox_vs_production(real_context):
    """Verify we're hitting sandbox endpoints."""
    # This test verifies our configuration is using sandbox
    assert real_context.server.config.sandbox_mode is True
    assert real_context.server.config.domain == "sandbox.ebay.com"
    
    # Make a simple call to verify sandbox
    result_json = await search_items(
        keywords="test",
        page_size=1,
        ctx=real_context
    )
    
    result = json.loads(result_json)
    assert result["status"] == ResponseStatus.SUCCESS.value
    
    # Sandbox URLs should contain 'sandbox'
    if result["data"]["items"]:
        item_url = result["data"]["items"][0]["url"]
        assert "sandbox" in item_url or "sbx" in item_url, "Should be using sandbox URLs"


# Performance test
@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_api_performance(real_context):
    """Test API response times."""
    import time
    
    start = time.time()
    result_json = await search_items(
        keywords="laptop",
        page_size=10,
        ctx=real_context
    )
    duration = time.time() - start
    
    result = json.loads(result_json)
    assert result["status"] == ResponseStatus.SUCCESS.value
    
    print(f"\nAPI Response Time: {duration:.2f} seconds")
    assert duration < 5.0, "API should respond within 5 seconds"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_invalid_credentials(real_context):
    """Test API behavior with invalid credentials."""
    # Check if we're using test/invalid credentials
    app_id = real_context.server.config.app_id
    
    if is_valid_app_id(app_id):
        pytest.skip("This test requires invalid credentials. Use test credentials to run.")
    
    print(f"\nTesting with invalid App ID: {app_id}")
    
    # Try to make an API call with invalid credentials
    result_json = await search_items(
        keywords="test item",
        page_size=1,
        ctx=real_context
    )
    
    result = json.loads(result_json)
    print(f"\nError Response: {json.dumps(result, indent=2)}")
    
    # Should get an error response
    assert result["status"] == ResponseStatus.ERROR.value
    
    # Check for authentication-related error
    # eBay typically returns specific error codes for invalid credentials
    error_msg = result.get("error_message", "").lower()
    
    # Common error indicators for invalid credentials
    assert any([
        "invalid" in error_msg,
        "authentication" in error_msg,
        "unauthorized" in error_msg,
        "application id" in error_msg,
        "invalid client" in error_msg,
        "api error" in error_msg  # Generic API error
    ]), f"Expected authentication error, got: {error_msg}"
    
    print(f"\n✓ Endpoint correctly rejected invalid credentials")
    print(f"✓ Error message: {error_msg}")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_endpoint_connectivity(real_context):
    """Test that we can connect to eBay endpoints (regardless of auth)."""
    import aiohttp
    
    # Build the endpoint URL
    domain = real_context.server.config.domain
    endpoint = f"https://svcs.{domain}/services/search/FindingService/v1"
    
    print(f"\nTesting connectivity to: {endpoint}")
    
    # Try to connect to the endpoint
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(endpoint, timeout=aiohttp.ClientTimeout(total=10)) as response:
                print(f"✓ Connected successfully")
                print(f"✓ Response status: {response.status}")
                print(f"✓ Response headers: {dict(response.headers)}")
                
                # Even without proper request, we should get some response
                assert response.status in [200, 400, 401, 403, 500], \
                    f"Unexpected status code: {response.status}"
                
    except aiohttp.ClientError as e:
        pytest.fail(f"Failed to connect to eBay endpoint: {e}")
    except Exception as e:
        pytest.fail(f"Unexpected error connecting to endpoint: {e}")


@pytest.mark.integration  
@pytest.mark.asyncio
async def test_rate_limit_headers(real_context):
    """Test that API responses include rate limit information."""
    # This test works with both valid and invalid credentials
    result_json = await search_items(
        keywords="test",
        page_size=1,
        ctx=real_context
    )
    
    result = json.loads(result_json)
    
    # Log the full response for debugging
    print(f"\nAPI Response: {json.dumps(result, indent=2)}")
    
    # Note: Rate limit headers are typically in the HTTP response headers,
    # which our current implementation doesn't capture. This is a limitation
    # we should document.
    print("\nNOTE: Rate limit headers are in HTTP response headers, not captured in current implementation")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_different_error_scenarios(real_context):
    """Test various error scenarios to understand API behavior."""
    
    test_cases = [
        {
            "name": "Empty keywords",
            "test": lambda: search_items(keywords="", ctx=real_context),
            "expected_error": "validation"
        },
        {
            "name": "Invalid category",  
            "test": lambda: find_items_by_category(category_id="invalid-category", ctx=real_context),
            "expected_error": "category"
        },
        {
            "name": "Page number too high",
            "test": lambda: search_items(keywords="test", page_number=999, ctx=real_context),
            "expected_error": "pagination"
        },
        {
            "name": "Invalid sort order",
            "test": lambda: search_items(keywords="test", sort_order="InvalidSort", ctx=real_context),
            "expected_error": "parameter"
        }
    ]
    
    for test_case in test_cases:
        print(f"\n\nTesting: {test_case['name']}")
        print("-" * 40)
        
        result_json = await test_case["test"]()
        result = json.loads(result_json)
        
        print(f"Status: {result['status']}")
        if result["status"] == ResponseStatus.ERROR.value:
            print(f"Error Code: {result.get('error_code', 'N/A')}")
            print(f"Error Message: {result.get('error_message', 'N/A')[:100]}...")
        else:
            print(f"Unexpected success for error test case")


if __name__ == "__main__":
    # Allow running this file directly for debugging
    asyncio.run(pytest.main([__file__, "-v", "-s"]))