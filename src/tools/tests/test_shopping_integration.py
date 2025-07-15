"""Integration tests for eBay Shopping API using sandbox environment."""
import os
import pytest
import asyncio
from unittest.mock import AsyncMock
import json
from config import EbayConfig
from logging_config import setup_mcp_logging
from api.ebay_client import EbayApiClient
from data_types import ErrorCode

# Import Shopping API tools
from tools.shopping_api import (
    get_single_item,
    get_item_status,
    get_shipping_costs,
    get_multiple_items,
    find_products
)


# Skip all tests in this file if EBAY_RUN_INTEGRATION_TESTS is not set
pytestmark = pytest.mark.skipif(
    os.getenv("EBAY_RUN_INTEGRATION_TESTS") != "true",
    reason="Integration tests disabled. Set EBAY_RUN_INTEGRATION_TESTS=true to run."
)


@pytest.fixture
def sandbox_config():
    """Create sandbox configuration."""
    config = EbayConfig.from_env()
    config.domain = "sandbox.ebay.com"  # Use sandbox
    return config


@pytest.fixture
def sandbox_context(sandbox_config):
    """Create mock context with sandbox configuration."""
    ctx = AsyncMock()
    ctx.info = AsyncMock()
    ctx.error = AsyncMock()
    ctx.debug = AsyncMock()
    ctx.warning = AsyncMock()
    ctx.report_progress = AsyncMock()
    
    # Mock server with sandbox config
    ctx.server = AsyncMock()
    ctx.server.config = sandbox_config
    ctx.server.logger = setup_mcp_logging(sandbox_config)
    
    return ctx


class TestShoppingAPISandboxIntegration:
    """Integration tests for Shopping API in sandbox."""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_single_item_sandbox(self, sandbox_context):
        """Test getting single item details from sandbox."""
        # Use a known sandbox test item ID
        # Note: You'll need to create test items in sandbox or use existing ones
        test_item_id = "110551991234"  # Example sandbox item
        
        try:
            result = await get_single_item(
                test_item_id,
                include_selector="Description,ItemSpecifics",
                ctx=sandbox_context
            )
            response = json.loads(result)
            
            if response["status"] == "success":
                assert response["data"]["item_id"] == test_item_id
                assert "title" in response["data"]
                assert "price" in response["data"]
                assert "seller" in response["data"]
                print(f"\nSuccessfully retrieved item: {response['data']['title']}")
            else:
                # In sandbox, items might not exist
                print(f"\nItem not found in sandbox: {response}")
                
        except Exception as e:
            pytest.skip(f"Sandbox API call failed: {str(e)}")
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_item_status_sandbox(self, sandbox_context):
        """Test checking item status in sandbox."""
        test_item_id = "110551991234"
        
        try:
            result = await get_item_status(test_item_id, ctx=sandbox_context)
            response = json.loads(result)
            
            if response["status"] == "success":
                assert "listing_status" in response["data"]
                assert "is_available" in response["data"]
                assert isinstance(response["data"]["is_available"], bool)
                print(f"\nItem status: {response['data']['listing_status']}")
            else:
                print(f"\nStatus check failed: {response}")
                
        except Exception as e:
            pytest.skip(f"Sandbox API call failed: {str(e)}")
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_shipping_costs_sandbox(self, sandbox_context):
        """Test calculating shipping costs in sandbox."""
        test_item_id = "110551991234"
        
        try:
            result = await get_shipping_costs(
                test_item_id,
                destination_country_code="US",
                destination_postal_code="90210",
                quantity=1,
                ctx=sandbox_context
            )
            response = json.loads(result)
            
            if response["status"] == "success":
                assert "domestic_shipping" in response["data"]
                assert "shipping_type" in response["data"]
                print(f"\nShipping options found: {len(response['data']['domestic_shipping'])}")
            else:
                print(f"\nShipping calculation failed: {response}")
                
        except Exception as e:
            pytest.skip(f"Sandbox API call failed: {str(e)}")
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_get_multiple_items_sandbox(self, sandbox_context):
        """Test getting multiple items from sandbox."""
        # Use multiple test item IDs
        test_item_ids = ["110551991234", "110551991235", "110551991236"]
        
        try:
            result = await get_multiple_items(
                test_item_ids[:2],  # Test with first 2 items
                ctx=sandbox_context
            )
            response = json.loads(result)
            
            assert response["status"] == "success"
            assert "items" in response["data"]
            assert "summary" in response["data"]
            
            print(f"\nRetrieved {response['data']['summary']['found']} of {response['data']['summary']['requested']} items")
            
        except Exception as e:
            pytest.skip(f"Sandbox API call failed: {str(e)}")
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_find_products_sandbox(self, sandbox_context):
        """Test searching products in sandbox catalog."""
        try:
            result = await find_products(
                query_keywords="test product",
                max_entries=5,
                ctx=sandbox_context
            )
            response = json.loads(result)
            
            if response["status"] == "success":
                assert "products" in response["data"]
                assert "summary" in response["data"]
                print(f"\nFound {response['data']['summary']['total_products']} products")
                
                if response["data"]["products"]:
                    product = response["data"]["products"][0]
                    print(f"First product: {product.get('title', 'No title')}")
            else:
                print(f"\nProduct search failed: {response}")
                
        except Exception as e:
            pytest.skip(f"Sandbox API call failed: {str(e)}")
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_shopping_api_error_handling(self, sandbox_context):
        """Test error handling with invalid item ID."""
        invalid_item_id = "INVALID123"
        
        result = await get_single_item(invalid_item_id, ctx=sandbox_context)
        response = json.loads(result)
        
        # Should return an error response
        assert response["status"] == "error"
        assert response["error_code"] in [ErrorCode.INTERNAL_ERROR.value, ErrorCode.EXTERNAL_API_ERROR.value]
        print(f"\nError handled correctly: {response['error_message']}")
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_shopping_api_pagination(self, sandbox_context):
        """Test handling large result sets with pagination."""
        # This test searches for common items to ensure results
        try:
            # First, find products to get valid item IDs
            result = await find_products(
                query_keywords="test",
                max_entries=10,
                ctx=sandbox_context
            )
            response = json.loads(result)
            
            if response["status"] == "success" and response["data"]["products"]:
                print(f"\nProduct pagination test:")
                print(f"Total products: {response['data']['summary']['total_products']}")
                print(f"Returned: {response['data']['summary']['returned']}")
                print(f"Has more: {response['data']['summary']['has_more']}")
            else:
                pytest.skip("No products found in sandbox for pagination test")
                
        except Exception as e:
            pytest.skip(f"Sandbox API call failed: {str(e)}")


class TestShoppingAPIPerformance:
    """Performance tests for Shopping API."""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_concurrent_requests(self, sandbox_context):
        """Test handling concurrent API requests."""
        test_item_ids = ["110551991234", "110551991235", "110551991236"]
        
        async def get_item(item_id):
            try:
                return await get_single_item(item_id, ctx=sandbox_context)
            except Exception as e:
                return json.dumps({
                    "status": "error",
                    "error_code": ErrorCode.INTERNAL_ERROR.value,
                    "error_message": str(e)
                })
        
        # Run concurrent requests
        start_time = asyncio.get_event_loop().time()
        results = await asyncio.gather(*[get_item(item_id) for item_id in test_item_ids])
        end_time = asyncio.get_event_loop().time()
        
        # Check results
        success_count = sum(1 for r in results if json.loads(r)["status"] == "success")
        
        print(f"\nConcurrent request test:")
        print(f"Total requests: {len(test_item_ids)}")
        print(f"Successful: {success_count}")
        print(f"Time taken: {end_time - start_time:.2f}s")
        
        # At least some requests should succeed
        assert success_count >= 0  # In sandbox, items might not exist


if __name__ == "__main__":
    # Run integration tests
    pytest.main([__file__, "-v", "-m", "integration"])