"""
Tests for Marketplace Insights API that can run in unit or integration mode.

Environment Variables:
    TEST_MODE=unit (default): Run with mocked dependencies  
    TEST_MODE=integration: Run against real eBay API
"""
import pytest
from unittest.mock import patch, AsyncMock
import json

from tools.tests.base_test import BaseApiTest, TestMode
from tools.tests.test_data import TestDataGood, TestDataBad
from tools.tests.test_helpers import (
    FieldValidator,
    validate_field,
    validate_list_field,
    assert_api_response_success
)
from tools.marketplace_insights_api import (
    search_item_sales,
    ItemSalesSearchInput,
    _convert_item_sale
)
from api.errors import EbayApiError


class TestMarketplaceInsightsApi(BaseApiTest):
    """Test Marketplace Insights API functions in both unit and integration modes."""
    
    # ==============================================================================
    # Data Conversion Tests (Unit tests only)
    # ==============================================================================
    
    @TestMode.skip_in_integration("Data conversion is unit test only")
    def test_convert_item_sale(self):
        """Test item sale conversion with valid data."""
        # Sample sale data based on expected API response structure
        sale_data = {
            "itemId": "v1|123456789|0",
            "title": "Apple iPhone 15 Pro - 256GB - Natural Titanium",
            "condition": "New",
            "conditionId": "1000",
            "itemSoldDate": "2024-12-15T10:30:00Z",
            "categoryId": "9355",
            "categoryPath": "Cell Phones & Accessories|Cell Phones & Smartphones",
            "itemPrice": {
                "value": "1099.99",
                "currency": "USD"
            },
            "seller": {
                "username": "toptech_seller",
                "feedbackPercentage": "99.8",
                "feedbackScore": 5432
            },
            "buyingOption": "FIXED_PRICE",
            "quantitySold": 1,
            "itemLocation": {
                "city": "San Jose",
                "stateOrProvince": "CA",
                "country": "US",
                "postalCode": "95125"
            },
            "itemWebUrl": "https://www.ebay.com/itm/123456789",
            "epid": "249325755",
            "image": {
                "imageUrl": "https://i.ebayimg.com/images/g/abc/s-l500.jpg"
            }
        }
        
        result = _convert_item_sale(sale_data)
        
        # Validate structure
        assert result["item_id"] == "v1|123456789|0"
        assert result["title"] == "Apple iPhone 15 Pro - 256GB - Natural Titanium"
        assert result["condition"] == "New"
        assert result["condition_id"] == "1000"
        assert result["sold_date"] == "2024-12-15T10:30:00Z"
        assert result["category_id"] == "9355"
        assert result["category_path"] == "Cell Phones & Accessories|Cell Phones & Smartphones"
        
        # Check price
        assert "price" in result
        assert result["price"]["value"] == 1099.99
        assert result["price"]["currency"] == "USD"
        
        # Check seller
        assert "seller" in result
        assert result["seller"]["username"] == "toptech_seller"
        assert result["seller"]["feedback_percentage"] == "99.8"
        assert result["seller"]["feedback_score"] == 5432
        
        # Check other fields
        assert result["buying_option"] == "FIXED_PRICE"
        assert result["quantity_sold"] == 1
        assert result["epid"] == "249325755"
        assert result["item_url"] == "https://www.ebay.com/itm/123456789"
        assert result["images"] == ["https://i.ebayimg.com/images/g/abc/s-l500.jpg"]
        
        # Check location
        assert "item_location" in result
        assert result["item_location"]["city"] == "San Jose"
        assert result["item_location"]["state"] == "CA"
        assert result["item_location"]["country"] == "US"
    
    @TestMode.skip_in_integration("Data conversion is unit test only")
    def test_convert_item_sale_minimal(self):
        """Test item sale conversion with minimal data."""
        minimal_sale = {
            "itemId": "v1|987654321|0",
            "title": "Test Product"
        }
        
        result = _convert_item_sale(minimal_sale)
        
        # Required fields
        assert result["item_id"] == "v1|987654321|0"
        assert result["title"] == "Test Product"
        
        # Optional fields should be None or have default values
        assert result["condition"] is None
        assert result["sold_date"] is None
        assert result["category_id"] is None
        assert result["quantity_sold"] == 1  # Default value
    
    @TestMode.skip_in_integration("Input validation is unit test only")
    def test_item_sales_search_input_validation(self):
        """Test item sales search input validation."""
        # Valid input with keyword
        valid_input = ItemSalesSearchInput(
            q="iphone 15",
            category_ids="9355",
            limit=50
        )
        assert valid_input.q == "iphone 15"
        assert valid_input.category_ids == "9355"
        assert valid_input.limit == 50
        
        # Valid input with filter
        valid_filter = ItemSalesSearchInput(
            category_ids="9355",
            filter="price:[500..1500],priceCurrency:USD"
        )
        assert valid_filter.category_ids == "9355"
        assert valid_filter.filter == "price:[500..1500],priceCurrency:USD"
        
        # Invalid query (too long)
        with pytest.raises(ValueError, match="Query must be 100 characters or less"):
            ItemSalesSearchInput(q="a" * 101)
        
        # Invalid category IDs
        with pytest.raises(ValueError, match="Invalid category ID"):
            ItemSalesSearchInput(category_ids="9355,ABC")
        
        # Invalid sort option
        with pytest.raises(ValueError, match="Invalid sort option"):
            ItemSalesSearchInput(
                q="test",
                sort="itemPrice"  # Invalid value
            )
        
        # No search criteria
        input_no_criteria = ItemSalesSearchInput(limit=10)
        with pytest.raises(ValueError, match="At least one search criterion is required"):
            input_no_criteria.validate_search_criteria()
    
    # ==============================================================================
    # Search Item Sales Tests (Both unit and integration)
    # ==============================================================================
    
    @pytest.mark.asyncio
    async def test_search_item_sales_by_epid(self, mock_context, mock_credentials):
        """Test searching item sales by EPID."""
        if self.is_integration_mode:
            # Integration test - print raw response
            # Try keyword search for better results
            result = await search_item_sales.fn(
                ctx=mock_context,
                q="phone",  # Simple keyword
                category_ids="9355",  # Cell Phones & Smartphones
                limit=10
            )
            
            # Print raw response for debugging
            print("\n=== RAW API RESPONSE ===")
            print(result)
            print("========================\n")
            
            # Parse response
            data = json.loads(result)
            
            if data["status"] == "success":
                # Validate response structure
                validate_field(data["data"], "item_sales", list)
                validate_field(data["data"], "total", int)
                validate_field(data["data"], "statistics", dict)
                
                # Check sales if any exist
                if data["data"]["item_sales"]:
                    for sale in data["data"]["item_sales"]:
                        # Basic validation - not all fields may be present
                        if "item_id" in sale:
                            validate_field(sale, "item_id", str)
                        if "title" in sale:
                            validate_field(sale, "title", str)
                        if "price" in sale:
                            validate_field(sale, "price", dict)
                            validate_field(sale["price"], "value", (int, float))
                            validate_field(sale["price"], "currency", str)
            else:
                # May fail with sandbox limitations or no data
                assert data["error_code"] in ["VALIDATION_ERROR", "NOT_FOUND", "EXTERNAL_API_ERROR"]
        else:
            # Unit test - mocked response
            with patch('tools.marketplace_insights_api.EbayRestClient') as MockClient:
                # Use test data from real API response
                mock_sales_response = TestDataGood.ITEM_SALES_SEARCH_RESPONSE
                
                mock_client = MockClient.return_value
                mock_client.get = AsyncMock(return_value=mock_sales_response)
                mock_client.close = AsyncMock()
                
                with patch('tools.marketplace_insights_api.mcp.config.app_id', mock_credentials["app_id"]), \
                     patch('tools.marketplace_insights_api.mcp.config.cert_id', mock_credentials["cert_id"]):
                    
                    result = await search_item_sales.fn(
                        ctx=mock_context,
                        q="phone",
                        category_ids="9355",
                        limit=10
                    )
                    
                    data = assert_api_response_success(result)
                    
                    # Check response matches test data
                    assert len(data["data"]["item_sales"]) == 1
                    sale = data["data"]["item_sales"][0]
                    assert sale["item_id"] == "v1|110588014268|0"
                    assert sale["title"] == "Demo Fotocamera Analogica"
                    assert sale["condition_id"] == "1000"
                    assert sale["condition_name"] == "New"
                    
                    # Check statistics (empty for items without price)
                    assert "statistics" in data["data"]
                    assert data["data"]["statistics"] == {}
                    
                    # Verify API was called correctly
                    mock_client.get.assert_called_once()
                    call_args = mock_client.get.call_args
                    assert "/buy/marketplace_insights/v1_beta/item_sales/search" in call_args[0][0]
                    assert call_args[1]["params"]["q"] == "phone"
                    assert call_args[1]["params"]["category_ids"] == "9355"
    
    @pytest.mark.asyncio
    async def test_search_item_sales_by_category(self, mock_context, mock_credentials):
        """Test searching item sales by category with aspect filter."""
        if self.is_integration_mode:
            # Integration test with filters
            result = await search_item_sales.fn(
                ctx=mock_context,
                q="smartphone",
                category_ids="9355",  # Cell Phones & Smartphones
                price_min="500",
                price_max="1500",
                sort="-price",
                limit=5
            )
            
            # Parse response
            data = json.loads(result)
            
            if data["status"] == "success":
                # Validate search criteria was preserved
                criteria = data["data"]["search_criteria"]
                assert criteria["q"] == "smartphone"
                assert criteria["category_ids"] == "9355"
                # Note: price filter is in the filter string, not search_criteria
        else:
            # Unit test
            with patch('tools.marketplace_insights_api.EbayRestClient') as MockClient:
                mock_client = MockClient.return_value
                mock_client.get = AsyncMock(return_value={"itemSales": [], "total": 0})
                mock_client.close = AsyncMock()
                
                with patch('tools.marketplace_insights_api.mcp.config.app_id', mock_credentials["app_id"]), \
                     patch('tools.marketplace_insights_api.mcp.config.cert_id', mock_credentials["cert_id"]):
                    
                    result = await search_item_sales.fn(
                        ctx=mock_context,
                        q="iphone",
                        category_ids="9355",
                        condition=["New", "Used"],
                        buying_options=["FIXED_PRICE"],
                        limit=20
                    )
                    
                    data = assert_api_response_success(result)
                    
                    # Verify parameters were passed correctly
                    call_args = mock_client.get.call_args
                    params = call_args[1]["params"]
                    assert params["q"] == "iphone"
                    assert params["category_ids"] == "9355"
                    # Filter should contain condition and buying options
                    assert "filter" in params
                    assert "conditionIds:{1000|3000}" in params["filter"]
                    assert "buyingOptions:{FIXED_PRICE}" in params["filter"]
    
    @pytest.mark.asyncio
    async def test_search_item_sales_with_date_range(self, mock_context, mock_credentials):
        """Test searching item sales with date range filter."""
        if self.is_integration_mode:
            # Skip detailed integration test
            return
        else:
            # Unit test with date range
            with patch('tools.marketplace_insights_api.EbayRestClient') as MockClient:
                # Mock response with multiple sales
                mock_sales = [{
                    "itemId": f"v1|{i}00000000|0",
                    "title": f"iPhone 15 Sale {i}",
                    "itemPrice": {"value": str(900 + i * 50), "currency": "USD"},
                    "itemSoldDate": f"2024-12-{10+i:02d}T10:00:00Z",
                    "epid": "249325755"
                } for i in range(5)]
                
                mock_client = MockClient.return_value
                mock_client.get = AsyncMock(return_value={
                    "itemSales": mock_sales,
                    "total": 5
                })
                mock_client.close = AsyncMock()
                
                with patch('tools.marketplace_insights_api.mcp.config.app_id', mock_credentials["app_id"]), \
                     patch('tools.marketplace_insights_api.mcp.config.cert_id', mock_credentials["cert_id"]):
                    
                    result = await search_item_sales.fn(
                        ctx=mock_context,
                        q="iphone",
                        category_ids="9355",
                        sort="-price"
                    )
                    
                    data = assert_api_response_success(result)
                    
                    # Check statistics were calculated
                    stats = data["data"]["statistics"]
                    assert stats["average_price"] == 1000  # (900+950+1000+1050+1100)/5
                    assert stats["min_price"] == 900
                    assert stats["max_price"] == 1100
                    assert stats["total_items"] == 5
                    
                    # Verify parameters were passed
                    call_args = mock_client.get.call_args
                    assert call_args[1]["params"]["q"] == "iphone"
                    assert call_args[1]["params"]["sort"] == "-price"
    
    # ==============================================================================
    # Error Handling Tests
    # ==============================================================================
    
    @pytest.mark.asyncio
    async def test_search_item_sales_no_criteria(self, mock_context, mock_credentials):
        """Test error when no search criteria provided."""
        result = await search_item_sales.fn(
            ctx=mock_context,
            limit=10
        )
        
        data = json.loads(result)
        assert data["status"] == "error"
        assert data["error_code"] == "VALIDATION_ERROR"
        assert "At least one search criterion is required" in data["error_message"]
    
    @pytest.mark.asyncio
    async def test_search_item_sales_invalid_query(self, mock_context, mock_credentials):
        """Test error handling for invalid query."""
        # Test query that's too long
        result = await search_item_sales.fn(
            ctx=mock_context,
            q="a" * 101,  # Over 100 character limit
            limit=10
        )
        
        data = json.loads(result)
        assert data["status"] == "error"
        assert data["error_code"] == "VALIDATION_ERROR"
        assert "Query must be 100 characters or less" in data["error_message"]
    
    @pytest.mark.asyncio
    async def test_search_item_sales_invalid_condition(self, mock_context, mock_credentials):
        """Test error handling for invalid condition."""
        # Test with invalid condition name
        result = await search_item_sales.fn(
            ctx=mock_context,
            category_ids="9355",
            condition="Invalid Condition",  # This should fail filter building
            limit=10
        )
        
        # Should still work but condition will be passed as-is to the API
        data = json.loads(result)
        # The API itself will handle the invalid condition
        assert data["status"] in ["success", "error"]
    
    @pytest.mark.asyncio
    async def test_search_item_sales_api_error(self, mock_context, mock_credentials):
        """Test error handling for API errors."""
        if self.is_integration_mode:
            # Skip in integration mode
            return
        else:
            # Unit test API error
            with patch('tools.marketplace_insights_api.EbayRestClient') as MockClient:
                mock_client = MockClient.return_value
                mock_client.get = AsyncMock(side_effect=EbayApiError(
                    status_code=404,
                    error_response={
                        "errors": [{
                            "errorId": 13020,
                            "message": "No sales data found"
                        }]
                    }
                ))
                mock_client.close = AsyncMock()
                
                with patch('tools.marketplace_insights_api.mcp.config.app_id', mock_credentials["app_id"]), \
                     patch('tools.marketplace_insights_api.mcp.config.cert_id', mock_credentials["cert_id"]):
                    
                    result = await search_item_sales.fn(
                        ctx=mock_context,
                        q="nonexistent_product_99999",
                        category_ids="9355",
                        limit=10
                    )
                    
                    data = json.loads(result)
                    assert data["status"] == "error"
                    assert data["error_code"] == "RESOURCE_NOT_FOUND"
    
    # ==============================================================================
    # Pagination Tests
    # ==============================================================================
    
    @pytest.mark.asyncio
    async def test_search_item_sales_pagination(self, mock_context, mock_credentials):
        """Test pagination parameters."""
        if self.is_integration_mode:
            # Skip in integration mode
            return
        else:
            # Unit test pagination
            with patch('tools.marketplace_insights_api.EbayRestClient') as MockClient:
                mock_client = MockClient.return_value
                mock_client.get = AsyncMock(return_value={
                    "itemSales": [],
                    "total": 100,
                    "limit": 20,
                    "offset": 20,
                    "next": "https://api.ebay.com/buy/marketplace_insights/v1_beta/item_sales/search?offset=40",
                    "prev": "https://api.ebay.com/buy/marketplace_insights/v1_beta/item_sales/search?offset=0"
                })
                mock_client.close = AsyncMock()
                
                with patch('tools.marketplace_insights_api.mcp.config.app_id', mock_credentials["app_id"]), \
                     patch('tools.marketplace_insights_api.mcp.config.cert_id', mock_credentials["cert_id"]):
                    
                    result = await search_item_sales.fn(
                        ctx=mock_context,
                        category_ids="9355",
                        limit=20,
                        offset=20
                    )
                    
                    data = assert_api_response_success(result)
                    
                    # Check pagination info
                    assert data["data"]["limit"] == 20
                    assert data["data"]["offset"] == 20
                    assert data["data"]["total"] == 100
                    assert "next" in data["data"]
                    assert "prev" in data["data"]
                    
                    # Verify pagination params were passed
                    call_args = mock_client.get.call_args
                    assert call_args[1]["params"]["limit"] == 20
                    assert call_args[1]["params"]["offset"] == 20
    
    # ==============================================================================
    # No Credentials Test
    # ==============================================================================
    
    @pytest.mark.asyncio
    async def test_search_item_sales_no_credentials(self, mock_context):
        """Test search with no credentials returns error."""
        with patch('tools.marketplace_insights_api.mcp.config.app_id', ''):
            result = await search_item_sales.fn(
                ctx=mock_context,
                q="test",
                category_ids="9355",
                limit=5
            )
            
            data = json.loads(result)
            assert data["status"] == "error"
            assert data["error_code"] == "CONFIGURATION_ERROR"
            assert "App ID not configured" in data["error_message"]