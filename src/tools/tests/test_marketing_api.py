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
from tools.tests.test_data import TestDataGood, TestDataBad, TestDataError
from tools.tests.test_helpers import (
    FieldValidator,
    validate_field,
    validate_list_field,
    assert_api_response_success
)
from tools.marketing_api import (
    get_top_selling_products,
    get_merchandised_products,
    MarketingProductsInput,
    _convert_marketing_product
)
from api.errors import EbayApiError


class TestMarketingApi(BaseApiTest):
    """Test Marketing API functions in both unit and integration modes."""
    
    # ==============================================================================
    # Data Conversion Tests (Unit tests only)
    # ==============================================================================
    
    @TestMode.skip_in_integration("Data conversion is unit test only")
    def test_convert_marketing_product(self):
        """Test marketing product conversion with valid data."""
        result = _convert_marketing_product(TestDataGood.MARKETING_PRODUCT_IPHONE)
        
        # Validate structure, not specific values
        assert result["product_id"] is not None
        assert FieldValidator.is_non_empty_string(result["product_id"])
        
        assert result["title"] is not None
        assert FieldValidator.is_non_empty_string(result["title"])
        
        # Check price range
        assert "price_range" in result
        assert isinstance(result["price_range"]["min"], (int, float))
        assert isinstance(result["price_range"]["max"], (int, float))
        assert result["price_range"]["min"] <= result["price_range"]["max"]
        assert result["price_range"]["currency"] == "USD"
        
        # Check ratings
        assert isinstance(result["review_count"], int) and result["review_count"] >= 0
        assert isinstance(result["rating"], (int, float))
        assert 0 <= result["rating"] <= 5
        
        # Check URLs
        assert FieldValidator.is_valid_url(result["image_url"])
        assert FieldValidator.is_valid_url(result["url"])
    
    @TestMode.skip_in_integration("Data conversion is unit test only")
    def test_convert_marketing_product_minimal(self):
        """Test marketing product conversion with minimal data."""
        minimal_product = {
            "productId": "EPID123",
            "title": "Test Product"
        }
        
        result = _convert_marketing_product(minimal_product)
        
        # Required fields should exist
        assert result["product_id"] == "EPID123"
        assert result["title"] == "Test Product"
        
        # Optional fields should have defaults
        assert result["price_range"]["min"] == 0
        assert result["price_range"]["max"] == 0
        assert result["review_count"] == 0
        assert result["rating"] == 0
    
    @TestMode.skip_in_integration("Data conversion is unit test only")
    def test_convert_marketing_product_bad_data(self):
        """Test marketing product conversion handles bad data gracefully."""
        result = _convert_marketing_product(TestDataBad.MARKETING_PRODUCT_IPHONE)
        
        # Should handle empty/invalid data
        assert result["product_id"] == ""  # Empty ID
        assert result["title"] == ""  # Empty title
        
        # Should handle invalid price
        assert result["price_range"]["min"] == 0  # Handles negative/invalid
        assert result["price_range"]["currency"] == "XXX"  # Preserves invalid currency
    
    @TestMode.skip_in_integration("Input validation is unit test only")
    def test_marketing_products_input_validation(self):
        """Test marketing products input validation."""
        # Valid input
        valid_input = MarketingProductsInput(
            category_id="9355",
            marketplace_id="EBAY_US",
            max_results=50
        )
        assert valid_input.category_id == "9355"
        assert valid_input.max_results == 50
        
        # Empty category ID
        with pytest.raises(ValueError, match="Category ID cannot be empty"):
            MarketingProductsInput(category_id="")
        
        # Invalid marketplace
        with pytest.raises(ValueError, match="Invalid marketplace ID"):
            MarketingProductsInput(marketplace_id="INVALID_MARKETPLACE")
        
        # Invalid max_results
        with pytest.raises(ValueError):
            MarketingProductsInput(max_results=150)  # Over 100 limit
    
    # ==============================================================================
    # Get Top Selling Products Tests (Both unit and integration)
    # ==============================================================================
    
    @pytest.mark.asyncio
    async def test_get_top_selling_products_basic(self, mock_context, mock_credentials):
        """Test getting top selling products."""
        if self.is_integration_mode:
            # Integration test - real API call
            result = await get_top_selling_products.fn(
                ctx=mock_context,
                marketplace_id="EBAY_US",
                max_results=10
            )
            
            # Parse and validate response
            data = assert_api_response_success(result)
            
            # Validate response structure
            validate_field(data["data"], "products", list)
            validate_field(data["data"], "total_count", int, validator=lambda x: x >= 0)
            validate_field(data["data"], "marketplace_id", str)
            
            # If products exist, validate their structure
            if data["data"]["products"]:
                for product in data["data"]["products"]:
                    validate_field(product, "product_id", str)
                    validate_field(product, "title", str)
                    validate_field(product, "price_range", dict)
        else:
            # Unit test - mocked response
            with patch('tools.marketing_api.EbayRestClient') as MockClient:
                mock_client = MockClient.return_value
                mock_client.get = AsyncMock(return_value=TestDataGood.MERCHANDISED_PRODUCTS_RESPONSE)
                mock_client.close = AsyncMock()
                
                with patch('tools.marketing_api.mcp.config.app_id', mock_credentials["app_id"]), \
                     patch('tools.marketing_api.mcp.config.cert_id', mock_credentials["cert_id"]):
                    
                    result = await get_top_selling_products.fn(
                        ctx=mock_context,
                        marketplace_id="EBAY_US",
                        max_results=20
                    )
                    
                    data = assert_api_response_success(result)
                    
                    # Validate response structure
                    assert len(data["data"]["products"]) == 1
                    product = data["data"]["products"][0]
                    assert product["product_id"] == "EPID249325755"
                    assert product["title"] == "Apple iPhone 15 Pro - 256GB"
                    assert product["price_range"]["min"] == 899.99
                    
                    # Verify API was called correctly
                    mock_client.get.assert_called_once()
                    call_args = mock_client.get.call_args
                    assert "/buy/marketing/v1_beta/merchandised_product" in call_args[0][0]
                    assert call_args[1]["params"]["metric"] == "BEST_SELLING"
    
    @pytest.mark.asyncio
    async def test_get_top_selling_products_with_category(self, mock_context, mock_credentials):
        """Test getting top selling products filtered by category."""
        if self.is_integration_mode:
            # Integration test
            result = await get_top_selling_products.fn(
                ctx=mock_context,
                category_id="9355",  # Cell Phones
                marketplace_id="EBAY_US",
                max_results=5
            )
            
            data = assert_api_response_success(result)
            validate_list_field(data["data"], "products")
            
            # Check category filter was applied
            assert data["data"]["category_id"] == "9355"
        else:
            # Unit test
            with patch('tools.marketing_api.EbayRestClient') as MockClient:
                mock_client = MockClient.return_value
                mock_response = TestDataGood.MERCHANDISED_PRODUCTS_RESPONSE.copy()
                mock_response["categoryId"] = "9355"
                mock_client.get = AsyncMock(return_value=mock_response)
                mock_client.close = AsyncMock()
                
                with patch('tools.marketing_api.mcp.config.app_id', mock_credentials["app_id"]), \
                     patch('tools.marketing_api.mcp.config.cert_id', mock_credentials["cert_id"]):
                    
                    result = await get_top_selling_products.fn(
                        ctx=mock_context,
                        category_id="9355",
                        max_results=10
                    )
                    
                    data = assert_api_response_success(result)
                    
                    # Verify category filter was passed
                    call_params = mock_client.get.call_args[1]["params"]
                    assert call_params["category_id"] == "9355"
    
    @pytest.mark.asyncio
    async def test_get_top_selling_products_with_aspect_filter(self, mock_context, mock_credentials):
        """Test getting top selling products with aspect filter."""
        aspect_filter = "Brand:Apple"
        
        if self.is_integration_mode:
            # Integration test
            result = await get_top_selling_products.fn(
                ctx=mock_context,
                aspect_filter=aspect_filter,
                max_results=10
            )
            
            data = assert_api_response_success(result)
            validate_list_field(data["data"], "products")
        else:
            # Unit test
            with patch('tools.marketing_api.EbayRestClient') as MockClient:
                mock_client = MockClient.return_value
                mock_client.get = AsyncMock(return_value=TestDataGood.MERCHANDISED_PRODUCTS_RESPONSE)
                mock_client.close = AsyncMock()
                
                with patch('tools.marketing_api.mcp.config.app_id', mock_credentials["app_id"]), \
                     patch('tools.marketing_api.mcp.config.cert_id', mock_credentials["cert_id"]):
                    
                    result = await get_top_selling_products.fn(
                        ctx=mock_context,
                        aspect_filter=aspect_filter
                    )
                    
                    data = assert_api_response_success(result)
                    
                    # Verify aspect filter was passed
                    call_params = mock_client.get.call_args[1]["params"]
                    assert call_params["aspect_filter"] == "Brand:Apple"
    
    # ==============================================================================
    # Get Merchandised Products Tests
    # ==============================================================================
    
    @pytest.mark.asyncio
    async def test_get_merchandised_products_basic(self, mock_context, mock_credentials):
        """Test getting merchandised products."""
        if self.is_integration_mode:
            # Integration test
            result = await get_merchandised_products.fn(
                ctx=mock_context,
                category_id="9355",
                marketplace_id="EBAY_US"
            )
            
            data = assert_api_response_success(result)
            validate_field(data["data"], "products", list)
            validate_field(data["data"], "category_id", str)
        else:
            # Unit test
            with patch('tools.marketing_api.EbayRestClient') as MockClient:
                mock_client = MockClient.return_value
                mock_client.get = AsyncMock(return_value=TestDataGood.MERCHANDISED_PRODUCTS_RESPONSE)
                mock_client.close = AsyncMock()
                
                with patch('tools.marketing_api.mcp.config.app_id', mock_credentials["app_id"]), \
                     patch('tools.marketing_api.mcp.config.cert_id', mock_credentials["cert_id"]):
                    
                    result = await get_merchandised_products.fn(
                        ctx=mock_context,
                        category_id="9355"
                    )
                    
                    data = assert_api_response_success(result)
                    
                    # Verify category was passed
                    assert data["data"]["category_id"] == "9355"
    
    # ==============================================================================
    # Error Handling Tests
    # ==============================================================================
    
    @pytest.mark.asyncio
    async def test_get_top_selling_products_error_handling(self, mock_context, mock_credentials):
        """Test error handling in top selling products."""
        if self.is_integration_mode:
            # Test with invalid input
            result = await get_top_selling_products.fn(
                ctx=mock_context,
                marketplace_id="INVALID_MARKET"
            )
            
            data = json.loads(result)
            assert data["status"] == "error"
            assert data["error_code"] == "VALIDATION_ERROR"
        else:
            # Unit test error handling
            with patch('tools.marketing_api.EbayRestClient') as MockClient:
                mock_client = MockClient.return_value
                mock_client.get = AsyncMock(side_effect=EbayApiError(
                    status_code=403,
                    error_response=TestDataError.ERROR_AUTHENTICATION
                ))
                mock_client.close = AsyncMock()
                
                with patch('tools.marketing_api.mcp.config.app_id', mock_credentials["app_id"]), \
                     patch('tools.marketing_api.mcp.config.cert_id', mock_credentials["cert_id"]):
                    
                    result = await get_top_selling_products.fn(
                        ctx=mock_context
                    )
                    
                    data = json.loads(result)
                    assert data["status"] == "error"
                    # Marketing API returns 403, which triggers Browse API fallback
                    # Since Browse API is not mocked, the fallback fails with INTERNAL_ERROR
                    assert data["error_code"] == "INTERNAL_ERROR"
    
    # ==============================================================================
    # Static Fallback Tests
    # ==============================================================================
    
    @pytest.mark.asyncio
    async def test_get_top_selling_products_no_credentials(self, mock_context):
        """Test top selling products with no credentials returns empty response."""
        with patch('tools.marketing_api.mcp.config.app_id', ''), \
             patch('tools.marketing_api.mcp.config.cert_id', ''):
            
            result = await get_top_selling_products.fn(
                ctx=mock_context,
                marketplace_id="EBAY_US"
            )
            
            data = assert_api_response_success(result)
            # Should return empty products with a note
            assert data["data"]["products"] == []
            assert data["data"]["total_count"] == 0
            assert "note" in data["data"]
            assert "credentials" in data["data"]["note"].lower()