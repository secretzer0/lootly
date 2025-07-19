"""
Tests for Marketing API that can run in unit or integration mode.

Environment Variables:
    TEST_MODE=unit (default): Run with mocked dependencies  
    TEST_MODE=integration: Run against real eBay API
"""
import pytest
from unittest.mock import patch, AsyncMock
import json

from tools.tests.base_test import BaseApiTest, TestMode
from tools.tests.test_data import TestDataGood
from tools.tests.test_helpers import (
    validate_field,
    assert_api_response_success
)
from tools.marketing_api import (
    get_merchandised_products,
    MerchandisedProductsInput,
    _convert_merchandised_product
)
from api.errors import EbayApiError


class TestMarketingApi(BaseApiTest):
    """Test Marketing API functions in both unit and integration modes."""
    
    # ==============================================================================
    # Infrastructure Validation Tests (Integration mode only)
    # ==============================================================================
    
    @pytest.mark.asyncio
    async def test_infrastructure_validation(self, mock_context):
        """CRITICAL: Validates integration infrastructure works before testing restricted APIs."""
        if not self.is_integration_mode:
            pytest.skip("Infrastructure validation only runs in integration mode")
        
        from tools.browse_api import search_items, BrowseSearchInput
        print("Testing integration infrastructure with Browse API...")
        print("This API uses basic scope (no user consent required)")
        
        search_input = BrowseSearchInput(query="test", limit=1)
        result = await search_items.fn(ctx=mock_context, search_input=search_input)
        response = json.loads(result)
        
        if response["status"] == "error":
            error_code = response["error_code"]
            error_msg = response["error_message"]
            
            if error_code == "CONFIGURATION_ERROR":
                pytest.fail(f"CREDENTIALS PROBLEM: {error_msg}")
            elif error_code == "EXTERNAL_API_ERROR":
                pytest.fail(f"eBay API CONNECTIVITY ISSUE: {error_msg}")
            else:
                pytest.fail(f"UNEXPECTED INFRASTRUCTURE ISSUE: {error_code} - {error_msg}")
        
        assert response["status"] == "success", "Infrastructure should be working"
        print("Infrastructure validation PASSED - credentials and connectivity OK")
    
    # ==============================================================================
    # Data Conversion Tests (Unit tests only)
    # ==============================================================================
    
    @TestMode.skip_in_integration("Data conversion is unit test only")
    def test_convert_merchandised_product(self):
        """Test merchandised product conversion with valid data."""
        # Sample product data based on API response structure
        product_data = {
            "epid": "249325755",
            "title": "Apple iPhone 15 Pro - 256GB",
            "image": {
                "imageUrl": "https://i.ebayimg.com/images/g/abc/s-l500.jpg"
            },
            "marketPriceDetails": [{
                "estimatedStartPrice": {
                    "value": "899.99",
                    "currency": "USD"
                },
                "estimatedEndPrice": {
                    "value": "1099.99",
                    "currency": "USD"
                }
            }],
            "averageRating": 4.8,
            "ratingCount": 1250,
            "reviewCount": 856
        }
        
        result = _convert_merchandised_product(product_data)
        
        # Validate structure
        assert result["epid"] == "249325755"
        assert result["title"] == "Apple iPhone 15 Pro - 256GB"
        assert result["image_url"] == "https://i.ebayimg.com/images/g/abc/s-l500.jpg"
        assert result["average_rating"] == 4.8
        assert result["rating_count"] == 1250
        assert result["review_count"] == 856
        
        # Check price info
        assert "price_info" in result
        assert result["price_info"]["min_price"] == 899.99
        assert result["price_info"]["max_price"] == 1099.99
        assert result["price_info"]["currency"] == "USD"
        
        # Check web URL
        assert result["web_url"] == "https://www.ebay.com/p/249325755"
    
    @TestMode.skip_in_integration("Data conversion is unit test only")
    def test_convert_merchandised_product_minimal(self):
        """Test merchandised product conversion with minimal data."""
        minimal_product = {
            "epid": "123456",
            "title": "Test Product"
        }
        
        result = _convert_merchandised_product(minimal_product)
        
        # Required fields
        assert result["epid"] == "123456"
        assert result["title"] == "Test Product"
        
        # Optional fields should have defaults
        assert result["image_url"] is None
        assert result["average_rating"] == 0
        assert result["rating_count"] == 0
        assert result["review_count"] == 0
        assert result["price_info"] == {}
    
    @TestMode.skip_in_integration("Input validation is unit test only")
    def test_merchandised_products_input_validation(self):
        """Test merchandised products input validation."""
        # Valid input
        valid_input = MerchandisedProductsInput(
            category_id="9355",
            metric_name="BEST_SELLING",
            limit=20
        )
        assert valid_input.category_id == "9355"
        assert valid_input.metric_name == "BEST_SELLING"
        assert valid_input.limit == 20
        
        # Invalid category ID (non-numeric)
        with pytest.raises(ValueError, match="Category ID must be numeric"):
            MerchandisedProductsInput(
                category_id="ABC123",
                metric_name="BEST_SELLING"
            )
        
        # Invalid metric name
        with pytest.raises(ValueError, match="Only BEST_SELLING metric"):
            MerchandisedProductsInput(
                category_id="9355",
                metric_name="INVALID_METRIC"
            )
        
        # Invalid limit
        with pytest.raises(ValueError):
            MerchandisedProductsInput(
                category_id="9355",
                limit=150  # Over 100
            )
    
    # ==============================================================================
    # Get Merchandised Products Tests (Both unit and integration)
    # ==============================================================================
    
    @pytest.mark.asyncio
    async def test_get_merchandised_products_basic(self, mock_context, mock_credentials):
        """Test getting merchandised products for a category."""
        if self.is_integration_mode:
            # Integration test - use sandbox test category
            from lootly_server import mcp
            environment = "sandbox" if mcp.config.sandbox_mode else "production"
            print(f"\\nTesting real API call to eBay Marketing API in {environment} environment...")
            print(f"Category: 9355 (Cell Phones), Limit: 10")
            
            result = await get_merchandised_products.fn(
                ctx=mock_context,
                category_id="9355",  # Required test category for sandbox
                limit=10
            )
            response = json.loads(result)
            
            print(f"API Response status: {response['status']}")
            
            if response["status"] == "error":
                error_code = response.get("error_code")
                error_msg = response.get("error_message", "")
                details = response.get("details", {})
                status_code = details.get("status_code")
                
                # Check if we're in sandbox mode
                from lootly_server import mcp
                is_sandbox = mcp.config.sandbox_mode
                
                # Only skip for known sandbox limitations when actually in sandbox mode
                if is_sandbox:
                    # Known sandbox limitations for merchandised products
                    if error_code == "VALIDATION_ERROR" and "category" in error_msg.lower():
                        pytest.skip(f"Known eBay sandbox limitation: {error_msg}")
                    elif error_code == "NOT_FOUND":
                        pytest.skip("Known eBay sandbox limitation: No merchandised products data in sandbox")
                    elif error_code == "EXTERNAL_API_ERROR" and status_code in [403, 404, 500]:
                        # 403 Access denied is common in sandbox for marketing APIs
                        if status_code == 403:
                            pytest.skip("Known eBay sandbox limitation: Marketing API access denied (HTTP 403) - insufficient permissions in sandbox")
                        else:
                            pytest.skip(f"Known eBay sandbox limitation: Marketing API returns HTTP {status_code}")
                
                # For production or unexpected errors - fail the test
                pytest.fail(f"Error from merchandised products API: {error_code} - {error_msg}\nDetails: {json.dumps(details, indent=2)}")
            else:
                # Validate response structure
                data = response["data"]
                print(f"Found {data['total']} merchandised products")
                
                validate_field(data, "merchandised_products", list)
                validate_field(data, "total", int)
                validate_field(data, "category_id", str)
                validate_field(data, "metric_name", str)
                
                # Check products if any exist
                if data["merchandised_products"]:
                    for product in data["merchandised_products"]:
                        # Basic validation - not all fields may be present
                        if "epid" in product:
                            validate_field(product, "epid", str)
                        if "title" in product:
                            validate_field(product, "title", str)
                    print(f"Successfully validated {len(data['merchandised_products'])} products")
        else:
            # Unit test - mocked response
            with patch('tools.marketing_api.EbayRestClient') as MockClient:
                mock_client = MockClient.return_value
                mock_client.get = AsyncMock(return_value={
                    "body": TestDataGood.MERCHANDISED_PRODUCTS_RESPONSE,
                    "headers": {}
                })
                mock_client.close = AsyncMock()
                
                with patch('tools.marketing_api.mcp.config.app_id', mock_credentials["app_id"]), \
                     patch('tools.marketing_api.mcp.config.cert_id', mock_credentials["cert_id"]):
                    
                    result = await get_merchandised_products.fn(
                        ctx=mock_context,
                        category_id="9355",
                        limit=20
                    )
                    
                    data = assert_api_response_success(result)
                    
                    # Check response matches test data
                    assert len(data["data"]["merchandised_products"]) == 1
                    product = data["data"]["merchandised_products"][0]
                    assert product["epid"] == "210746054"
                    assert product["title"] == "Samsung Galaxy S6 SM-G920V - 32GB - Black Sapphire (Verizon) Smartphone"
                    assert product["average_rating"] == 4.2
                    
                    # Verify API was called correctly
                    mock_client.get.assert_called_once()
                    call_args = mock_client.get.call_args
                    assert "/buy/marketing/v1_beta/merchandised_product" in call_args[0][0]
                    assert call_args[1]["params"]["category_id"] == "9355"
                    assert call_args[1]["params"]["metric_name"] == "BEST_SELLING"
    
    @pytest.mark.asyncio
    async def test_get_merchandised_products_with_aspect_filter(self, mock_context, mock_credentials):
        """Test getting merchandised products with aspect filter."""
        if self.is_integration_mode:
            # Skip detailed integration test
            return
        else:
            # Unit test with aspect filter
            with patch('tools.marketing_api.EbayRestClient') as MockClient:
                mock_client = MockClient.return_value
                mock_client.get = AsyncMock(return_value={
                    "body": {
                        "merchandisedProducts": []  # Empty result
                    },
                    "headers": {}
                })
                mock_client.close = AsyncMock()
                
                with patch('tools.marketing_api.mcp.config.app_id', mock_credentials["app_id"]), \
                     patch('tools.marketing_api.mcp.config.cert_id', mock_credentials["cert_id"]):
                    
                    result = await get_merchandised_products.fn(
                        ctx=mock_context,
                        category_id="9355",
                        limit=10,
                        aspect_filter="Brand:Apple"
                    )
                    
                    assert_api_response_success(result)
                    
                    # Verify aspect filter was passed
                    call_args = mock_client.get.call_args
                    assert call_args[1]["params"]["aspect_filter"] == "Brand:Apple"
    
    # ==============================================================================
    # Error Handling Tests
    # ==============================================================================
    
    @pytest.mark.asyncio
    async def test_get_merchandised_products_invalid_category(self, mock_context, mock_credentials):
        """Test error handling for invalid category."""
        # Test with non-numeric category ID
        result = await get_merchandised_products.fn(
            ctx=mock_context,
            category_id="INVALID",
            limit=10
        )
        
        data = json.loads(result)
        assert data["status"] == "error"
        assert data["error_code"] == "VALIDATION_ERROR"
        assert "Category ID must be numeric" in data["error_message"]
    
    @pytest.mark.asyncio
    async def test_get_merchandised_products_api_error(self, mock_context, mock_credentials):
        """Test error handling for API errors."""
        if self.is_integration_mode:
            # Skip in integration mode
            return
        else:
            # Unit test API error
            with patch('tools.marketing_api.EbayRestClient') as MockClient:
                mock_client = MockClient.return_value
                mock_client.get = AsyncMock(side_effect=EbayApiError(
                    status_code=404,
                    error_response={
                        "errors": [{
                            "errorId": 13020,
                            "message": "Category not found"
                        }]
                    }
                ))
                mock_client.close = AsyncMock()
                
                with patch('tools.marketing_api.mcp.config.app_id', mock_credentials["app_id"]), \
                     patch('tools.marketing_api.mcp.config.cert_id', mock_credentials["cert_id"]):
                    
                    result = await get_merchandised_products.fn(
                        ctx=mock_context,
                        category_id="99999",
                        limit=10
                    )
                    
                    data = json.loads(result)
                    assert data["status"] == "error"
                    assert data["error_code"] == "RESOURCE_NOT_FOUND"
    
    # ==============================================================================
    # Static Fallback Tests
    # ==============================================================================
    
    @pytest.mark.asyncio
    async def test_get_merchandised_products_no_credentials(self, mock_context):
        """Test merchandised products with no credentials returns error."""
        with patch('tools.marketing_api.mcp.config.app_id', ''):
            result = await get_merchandised_products.fn(
                ctx=mock_context,
                category_id="9355",
                limit=5
            )
            
            data = json.loads(result)
            assert data["status"] == "error"
            assert data["error_code"] == "CONFIGURATION_ERROR"
            assert "App ID not configured" in data["error_message"]