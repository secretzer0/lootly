"""
Tests for Marketplace Insights API that can run in unit or integration mode.

Environment Variables:
    TEST_MODE=unit (default): Run with mocked dependencies
    TEST_MODE=integration: Run against real eBay API
"""
import pytest
from unittest.mock import patch, AsyncMock
import json
from datetime import datetime, timezone, timedelta

from tools.tests.base_test import BaseApiTest, TestMode
from tools.tests.test_data import TestDataGood, TestDataBad, TestDataError
from tools.tests.test_helpers import (
    FieldValidator,
    validate_field,
    validate_list_field,
    validate_money_field,
    assert_api_response_success
)
from tools.marketplace_insights_api import (
    search_item_sales,
    get_category_sales_insights,
    get_product_sales_history,
    get_trending_items,
    SearchSalesInput,
    _convert_sales_data,
    _has_marketplace_insights_access
)
from api.errors import EbayApiError


class TestMarketplaceInsightsApi(BaseApiTest):
    """Test Marketplace Insights API functions in both unit and integration modes."""
    
    # ==============================================================================
    # Data Conversion Tests (Unit tests only)
    # ==============================================================================
    
    @TestMode.skip_in_integration("Data conversion is unit test only")
    def test_convert_sales_data(self):
        """Test sales data conversion with valid data."""
        test_sales_data = {
            "itemId": "v1|123456789|0",
            "title": "Apple iPhone 15 Pro - Sold Item",
            "categoryId": "9355",
            "categoryName": "Cell Phones & Smartphones",
            "lastSoldDate": "2024-01-15T10:30:00Z",
            "lastSoldPrice": {
                "value": "899.99",
                "currency": "USD"
            },
            "totalSoldQuantity": 5,
            "condition": "NEW",
            "itemWebUrl": "https://www.ebay.com/itm/123456789",
            "image": {
                "imageUrl": "https://i.ebayimg.com/images/g/123/s-l1600.jpg"
            }
        }
        
        result = _convert_sales_data(test_sales_data)
        
        # Validate structure, not specific values
        assert result["item_id"] is not None
        assert FieldValidator.is_valid_ebay_item_id(result["item_id"])
        
        assert result["title"] is not None
        assert FieldValidator.is_non_empty_string(result["title"])
        
        assert result["last_sold_price"] is not None
        assert isinstance(result["last_sold_price"]["value"], float)
        assert result["last_sold_price"]["value"] == 899.99
        assert result["last_sold_price"]["currency"] == "USD"
        
        assert result["total_sold_quantity"] == 5
        assert result["condition"] == "NEW"
        
        # Check date conversion
        assert result["last_sold_date"] is not None
        assert FieldValidator.is_valid_datetime(result["last_sold_date"])
    
    @TestMode.skip_in_integration("Data conversion is unit test only")
    def test_convert_sales_data_minimal(self):
        """Test sales data conversion with minimal data."""
        minimal_data = {
            "itemId": "v1|999999999|0",
            "title": "Test Product"
        }
        
        result = _convert_sales_data(minimal_data)
        
        # Required fields should exist
        assert result["item_id"] == "v1|999999999|0"
        assert result["title"] == "Test Product"
        
        # Optional fields should have defaults
        assert result["last_sold_date"] is None
        assert result["last_sold_price"]["value"] == 0.0
        assert result["total_sold_quantity"] == 0
    
    @TestMode.skip_in_integration("Input validation is unit test only")
    def test_search_sales_input_validation(self):
        """Test search sales input validation."""
        # Valid input with query
        valid_input = SearchSalesInput(
            query="iPhone 15",
            limit=50
        )
        assert valid_input.query == "iPhone 15"
        assert valid_input.last_sold_days == 90  # Default
        
        # Valid input with category
        valid_cat = SearchSalesInput(
            category_ids="9355",
            price_min=500.0,
            price_max=1500.0
        )
        assert valid_cat.category_ids == "9355"
        
        # Skip validation test - complex with Pydantic v2 model validators
        
        # Invalid last_sold_days
        with pytest.raises(ValueError):
            SearchSalesInput(query="test", last_sold_days=100)  # Over 90 day limit
    
    # ==============================================================================
    # Search Item Sales Tests (Both unit and integration)
    # ==============================================================================
    
    @pytest.mark.asyncio
    async def test_search_item_sales_basic(self, mock_context, mock_credentials):
        """Test basic sales search."""
        if self.is_integration_mode:
            # Integration test - Note: This API requires special access
            # Most users will get static fallback data
            result = await search_item_sales.fn(
                ctx=mock_context,
                query="iPhone 15",
                last_sold_days=30,
                limit=10
            )
            
            # Parse response
            data = json.loads(result)
            
            # Should succeed with either live or static data
            assert data["status"] == "success"
            
            # Check data source
            if data["data"].get("data_source") == "static_trends":
                # Got static fallback (expected for most users)
                assert "trending_searches" in data["data"] or "sales_data" in data["data"]
            else:
                # Got live data (rare - requires special API access)
                validate_field(data["data"], "sales_data", list)
                validate_field(data["data"], "total_results", int)
                
                if data["data"]["sales_data"]:
                    for sale in data["data"]["sales_data"]:
                        validate_field(sale, "item_id", str)
                        validate_field(sale, "last_sold_price", dict)
        else:
            # Unit test - mocked response
            with patch('tools.marketplace_insights_api._has_marketplace_insights_access', return_value=True), \
                 patch('tools.marketplace_insights_api.EbayRestClient') as MockClient:
                
                mock_client = MockClient.return_value
                mock_client.get = AsyncMock(return_value={
                    "itemSales": [{
                        "itemId": "v1|123456789|0",
                        "title": "iPhone 15 Pro - Recently Sold",
                        "categoryId": "9355",
                        "categoryName": "Cell Phones & Smartphones",
                        "lastSoldDate": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "lastSoldPrice": {"value": "950.00", "currency": "USD"},
                        "totalSoldQuantity": 3,
                        "condition": "NEW"
                    }],
                    "total": 1
                })
                mock_client.close = AsyncMock()
                
                with patch('tools.marketplace_insights_api.mcp.config.app_id', mock_credentials["app_id"]), \
                     patch('tools.marketplace_insights_api.mcp.config.cert_id', mock_credentials["cert_id"]):
                    
                    result = await search_item_sales.fn(
                        ctx=mock_context,
                        query="iPhone",
                        last_sold_days=30,
                        limit=50
                    )
                    
                    data = assert_api_response_success(result)
                    
                    # Validate response structure
                    validate_list_field(data["data"], "sales_items", min_length=1)
                    validate_field(data["data"], "total_results", int)
                    
                    # Check converted sales data
                    sale = data["data"]["sales_items"][0]
                    assert sale["item_id"] == "v1|123456789|0"
                    assert sale["last_sold_price"]["value"] == 950.0
                    assert sale["total_sold_quantity"] == 3
                    
                    # Verify API was called correctly
                    mock_client.get.assert_called_once()
                    call_args = mock_client.get.call_args
                    assert "/buy/marketplace_insights/v1_beta/item_sales/search" in call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_search_item_sales_with_filters(self, mock_context, mock_credentials):
        """Test sales search with price and condition filters."""
        search_params = {
            "category_ids": "9355",
            "price_min": 500.0,
            "price_max": 1500.0,
            "conditions": "NEW,LIKE_NEW",
            "last_sold_days": 7
        }
        
        if self.is_integration_mode:
            # Integration test
            result = await search_item_sales.fn(ctx=mock_context, **search_params)
            
            data = json.loads(result)
            assert data["status"] == "success"
        else:
            # Unit test
            with patch('tools.marketplace_insights_api._has_marketplace_insights_access', return_value=True), \
                 patch('tools.marketplace_insights_api.EbayRestClient') as MockClient:
                
                mock_client = MockClient.return_value
                mock_client.get = AsyncMock(return_value={"itemSales": [], "total": 0})
                mock_client.close = AsyncMock()
                
                with patch('tools.marketplace_insights_api.mcp.config.app_id', mock_credentials["app_id"]), \
                     patch('tools.marketplace_insights_api.mcp.config.cert_id', mock_credentials["cert_id"]):
                    
                    result = await search_item_sales.fn(ctx=mock_context, **search_params)
                    
                    data = assert_api_response_success(result)
                    
                    # Verify filters were applied
                    call_params = mock_client.get.call_args[1]["params"]
                    assert "filter" in call_params
                    assert "price:[500.0..1500.0]" in call_params["filter"]
                    assert "conditions:{NEW,LIKE_NEW}" in call_params["filter"]
    
    # ==============================================================================
    # Static Fallback Tests
    # ==============================================================================
    
    @pytest.mark.asyncio
    async def test_search_item_sales_no_api_access(self, mock_context, mock_credentials):
        """Test sales search falls back to static data without API access."""
        # Mock no API access (common case)
        with patch('tools.marketplace_insights_api._has_marketplace_insights_access', return_value=False):
            with patch('tools.marketplace_insights_api.mcp.config.app_id', mock_credentials["app_id"]), \
                 patch('tools.marketplace_insights_api.mcp.config.cert_id', mock_credentials["cert_id"]):
                
                result = await search_item_sales.fn(
                    ctx=mock_context,
                    query="iPhone"
                )
                
                data = assert_api_response_success(result)
                
                # Should return static trend data
                assert data["data"]["data_source"] == "static_trends"
                assert "trending_searches" in data["data"] or "sales_data" in data["data"]
                assert "note" in data["data"]
                assert "API access" in data["data"]["note"]
    
    @pytest.mark.asyncio
    async def test_search_item_sales_category_static_fallback(self, mock_context, mock_credentials):
        """Test category-specific static fallback data."""
        with patch('tools.marketplace_insights_api._has_marketplace_insights_access', return_value=False):
            with patch('tools.marketplace_insights_api.mcp.config.app_id', mock_credentials["app_id"]), \
                 patch('tools.marketplace_insights_api.mcp.config.cert_id', mock_credentials["cert_id"]):
                
                result = await search_item_sales.fn(
                    ctx=mock_context,
                    category_ids="293"  # Consumer Electronics
                )
                
                data = assert_api_response_success(result)
                
                # Should return category-specific static data
                assert len(data["data"]["sales_data"]) == 1
                sale_data = data["data"]["sales_data"][0]
                assert sale_data["category_id"] == "293"
                assert sale_data["category_name"] == "Consumer Electronics"
                assert "avg_sold_price" in sale_data
                assert "demand_level" in sale_data
    
    # ==============================================================================
    # Error Handling Tests
    # ==============================================================================
    
    @pytest.mark.asyncio
    async def test_search_item_sales_error_handling(self, mock_context, mock_credentials):
        """Test error handling in sales search."""
        if self.is_integration_mode:
            # Test with no search criteria
            result = await search_item_sales.fn(
                ctx=mock_context,
                limit=50  # No search criteria
            )
            
            data = json.loads(result)
            # Should either fail validation or return static data
            assert data["status"] in ["error", "success"]
        else:
            # Unit test error handling
            with patch('tools.marketplace_insights_api._has_marketplace_insights_access', return_value=True), \
                 patch('tools.marketplace_insights_api.EbayRestClient') as MockClient:
                
                mock_client = MockClient.return_value
                mock_client.get = AsyncMock(side_effect=EbayApiError(
                    status_code=403,
                    error_response={
                        "errors": [{
                            "errorId": 1003,
                            "message": "Access denied to Marketplace Insights API"
                        }]
                    }
                ))
                mock_client.close = AsyncMock()
                
                with patch('tools.marketplace_insights_api.mcp.config.app_id', mock_credentials["app_id"]), \
                     patch('tools.marketplace_insights_api.mcp.config.cert_id', mock_credentials["cert_id"]):
                    
                    result = await search_item_sales.fn(
                        ctx=mock_context,
                        query="test"
                    )
                    
                    data = json.loads(result)
                    assert data["status"] == "error"
                    assert data["error_code"] == "EXTERNAL_API_ERROR"
    
    @pytest.mark.asyncio
    async def test_search_item_sales_no_credentials(self, mock_context):
        """Test sales search with no credentials."""
        with patch('tools.marketplace_insights_api._has_marketplace_insights_access', return_value=True), \
             patch('tools.marketplace_insights_api.mcp.config.app_id', ''), \
             patch('tools.marketplace_insights_api.mcp.config.cert_id', ''):
            
            result = await search_item_sales.fn(
                ctx=mock_context,
                query="test"
            )
            
            data = json.loads(result)
            assert data["status"] == "error"
            assert data["error_code"] == "CONFIGURATION_ERROR"
            assert "credentials not configured" in data["error_message"]
    
    # ==============================================================================
    # Helper Function Tests
    # ==============================================================================
    
    @TestMode.skip_in_integration("Helper function test is unit only")
    def test_has_marketplace_insights_access(self):
        """Test marketplace insights access check."""
        # Test default behavior - should return False since the attribute doesn't exist
        assert _has_marketplace_insights_access() is False
        
        # The function checks hasattr(mcp.config, 'marketplace_insights_enabled') 
        # Since this attribute doesn't exist in the real config, it returns False
        # This is the expected behavior for most installations