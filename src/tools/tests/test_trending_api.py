"""
Tests for Trending API that can run in unit or integration mode.

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
from tools.trending_api import (
    get_most_watched_items,
    get_trending_items_by_category,
    TrendingItemsInput,
    _search_trending_items,
    _convert_trending_item
)
from api.errors import EbayApiError


class TestTrendingApi(BaseApiTest):
    """Test Trending API functions in both unit and integration modes."""
    
    # ==============================================================================
    # Infrastructure Validation Tests (Integration mode only)
    # ==============================================================================
    
    @pytest.mark.asyncio
    async def test_infrastructure_validation(self, mock_context):
        """CRITICAL: Validates integration infrastructure works before testing restricted APIs."""
        if not self.is_integration_mode:
            pytest.skip("Infrastructure validation only runs in integration mode")
        
        from tools.browse_api import search_items
        print("Testing integration infrastructure with Browse API...")
        print("This API uses basic scope (no user consent required)")
        
        result = await search_items.fn(ctx=mock_context, query="test", limit=1)
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
    def test_convert_trending_item(self):
        """Test trending item conversion with valid data."""
        # Create a Browse API item format (input to _convert_trending_item)
        browse_item = {
            "itemId": "v1|999888777|0",
            "title": "Pokemon Trading Card Game Booster Box",
            "price": {
                "value": "149.99",
                "currency": "USD"
            },
            "seller": {
                "username": "cardshop123",
                "feedbackScore": 9876,
                "feedbackPercentage": "99.5"
            },
            "condition": "NEW",
            "itemWebUrl": "https://www.ebay.com/itm/999888777",
            "image": {
                "imageUrl": "https://i.ebayimg.com/images/g/trending/s-l1600.jpg"
            },
            "categories": [
                {"categoryName": "Trading Card Games"}
            ],
            "itemLocation": {
                "city": "Los Angeles",
                "stateOrProvince": "CA"
            },
            "shippingOptions": [
                {"shippingCost": {"value": "0"}}
            ],
            "itemCreationDate": "2024-01-01T00:00:00Z",
            "itemEndDate": "2024-02-01T00:00:00Z"
        }
        
        result = _convert_trending_item(browse_item)
        
        # Validate structure, not specific values
        assert result["item_id"] is not None
        assert FieldValidator.is_non_empty_string(result["item_id"])
        
        assert result["title"] is not None
        assert FieldValidator.is_non_empty_string(result["title"])
        
        # Check price
        assert isinstance(result["price"]["value"], (int, float))
        assert result["price"]["value"] >= 0
        assert result["price"]["currency"] == "USD"
        
        # Check seller
        assert FieldValidator.is_non_empty_string(result["seller"]["username"])
        assert isinstance(result["seller"]["feedback_score"], int)
        assert isinstance(result["seller"]["positive_feedback_percent"], (int, float, str))
        # If it's a string, validate it can be converted to float
        if isinstance(result["seller"]["positive_feedback_percent"], str):
            feedback_pct = float(result["seller"]["positive_feedback_percent"])
            assert 0 <= feedback_pct <= 100
        else:
            assert 0 <= result["seller"]["positive_feedback_percent"] <= 100
        
        # Check URLs
        assert FieldValidator.is_valid_url(result["url"])
        assert FieldValidator.is_valid_url(result["image_url"])
        
        # Check other fields
        assert result["condition"] == "NEW"
        assert result["category"] == "Trading Card Games"
        assert "Los Angeles, CA" in result["location"]
        assert result["free_shipping"] is True  # 0 shipping cost
        assert result["watch_count"] is None  # Not available in Browse API
        assert result["trending_score"] == "high"
    
    @TestMode.skip_in_integration("Data conversion is unit test only")
    def test_convert_trending_item_minimal(self):
        """Test trending item conversion with minimal data."""
        minimal_item = {
            "itemId": "v1|123|0",
            "title": "Test Item"
        }
        
        result = _convert_trending_item(minimal_item)
        
        # Required fields should exist
        assert result["item_id"] == "v1|123|0"
        assert result["title"] == "Test Item"
        
        # Optional fields should have defaults
        assert result["price"]["value"] == 0
        assert result["price"]["currency"] == "USD"
        assert result["seller"]["username"] == "Unknown"
        assert result["condition"] == "NEW"
        assert result["url"] == ""
        assert result["image_url"] == ""
    
    @TestMode.skip_in_integration("Input validation is unit test only")
    def test_trending_items_input_validation(self):
        """Test trending items input validation."""
        # Valid input
        valid_input = TrendingItemsInput(
            category_id="2536",
            max_results=50,
            marketplace_id="EBAY_US"
        )
        assert valid_input.category_id == "2536"
        assert valid_input.max_results == 50
        
        # Empty category ID (should be allowed as it's optional)
        input_no_cat = TrendingItemsInput(max_results=20)
        assert input_no_cat.category_id is None
        
        # Invalid max_results
        with pytest.raises(ValueError):
            TrendingItemsInput(max_results=150)  # Over 100 limit
        
        with pytest.raises(ValueError):
            TrendingItemsInput(max_results=0)  # Under 1 limit
    
    # ==============================================================================
    # Get Most Watched Items Tests (Both unit and integration)
    # ==============================================================================
    
    @pytest.mark.asyncio
    async def test_get_most_watched_items_basic(self, mock_context, mock_credentials):
        """Test getting most watched items."""
        if self.is_integration_mode:
            # Integration test - real API call
            print(f"\\nTesting real API call to eBay Trending API...")
            print(f"Max results: 10")
            
            result = await get_most_watched_items.fn(
                ctx=mock_context,
                max_results=10
            )
            
            # Parse and validate response
            response = json.loads(result)
            print(f"API Response status: {response['status']}")
            
            if response["status"] == "error":
                error_code = response.get("error_code")
                error_msg = response.get("error_message", "")
                details = response.get("details", {})
                pytest.fail(f"API call failed - {error_code}: {error_msg}\\nDetails: {details}")
            
            data = response["data"]
            print(f"Found {data['total_count']} trending items")
            
            # Validate response structure
            validate_list_field(data, "items")
            validate_field(data, "total_count", int, validator=lambda x: x >= 0)
            validate_field(data, "search_strategy", str)
            validate_field(data, "api_used", str)
            
            # If items exist, validate their structure
            if data["items"]:
                for item in data["items"]:
                    validate_field(item, "item_id", str)
                    validate_field(item, "title", str)
                    validate_field(item, "price", dict)
                    validate_field(item["price"], "value", (int, float))
                    validate_field(item["price"], "currency", str)
                print(f"Successfully validated {len(data['items'])} trending items")
        else:
            # Unit test - mocked response
            with patch('tools.trending_api.EbayRestClient') as MockClient:
                mock_client = MockClient.return_value
                # Mock the Browse API search response
                mock_search_response = {
                    "itemSummaries": [
                        {
                            "itemId": "v1|999888777|0",
                            "title": "Pokemon Trading Card Game Booster Box",
                            "price": {"value": "149.99", "currency": "USD"},
                            "itemWebUrl": "https://www.ebay.com/itm/999888777",
                            "image": {"imageUrl": "https://i.ebayimg.com/images/g/trending/s-l1600.jpg"},
                            "seller": {"username": "cardshop123", "feedbackScore": 9876, "feedbackPercentage": "99.5"},
                            "condition": "NEW"
                        }
                    ]
                }
                mock_client.get = AsyncMock(return_value=mock_search_response)
                mock_client.close = AsyncMock()
                
                with patch('tools.trending_api.mcp.config.app_id', mock_credentials["app_id"]), \
                     patch('tools.trending_api.mcp.config.cert_id', mock_credentials["cert_id"]):
                    
                    result = await get_most_watched_items.fn(
                        ctx=mock_context,
                        max_results=20
                    )
                    
                    data = assert_api_response_success(result)
                    
                    # Validate response structure
                    assert len(data["data"]["items"]) > 0
                    item = data["data"]["items"][0]
                    assert item["item_id"] == "v1|999888777|0"
                    assert item["title"] == "Pokemon Trading Card Game Booster Box"
                    assert item["price"]["value"] == 149.99
                    
                    # Verify API was called for searches
                    assert mock_client.get.call_count >= 2  # Multiple search strategies
    
    @pytest.mark.asyncio
    async def test_get_most_watched_items_with_category(self, mock_context, mock_credentials):
        """Test getting most watched items filtered by category."""
        if self.is_integration_mode:
            # Integration test
            result = await get_most_watched_items.fn(
                ctx=mock_context,
                category_id="2536",  # Trading Card Games
                max_results=5
            )
            
            data = assert_api_response_success(result)
            validate_list_field(data["data"], "items")
            
            # Check category filter was applied
            assert data["data"]["category_id"] == "2536"
        else:
            # Unit test
            with patch('tools.trending_api.EbayRestClient') as MockClient:
                mock_client = MockClient.return_value
                mock_client.get = AsyncMock(return_value={"itemSummaries": []})
                mock_client.close = AsyncMock()
                
                with patch('tools.trending_api.mcp.config.app_id', mock_credentials["app_id"]), \
                     patch('tools.trending_api.mcp.config.cert_id', mock_credentials["cert_id"]):
                    
                    result = await get_most_watched_items.fn(
                        ctx=mock_context,
                        category_id="2536",
                        max_results=10
                    )
                    
                    data = assert_api_response_success(result)
                    
                    # Verify category filter was passed to API calls
                    for call in mock_client.get.call_args_list:
                        call_params = call[1]["params"]
                        assert "categoryIds:{2536}" in call_params.get("filter", "")
    
    # ==============================================================================
    # Get Trending Items by Category Tests
    # ==============================================================================
    
    @pytest.mark.asyncio
    async def test_get_trending_items_by_category_basic(self, mock_context, mock_credentials):
        """Test getting trending items by category."""
        if self.is_integration_mode:
            # Integration test
            result = await get_trending_items_by_category.fn(
                ctx=mock_context,
                category_id="9355",  # Cell Phones
                max_results=10
            )
            
            data = assert_api_response_success(result)
            validate_list_field(data["data"], "items")
            assert data["data"]["category_id"] == "9355"
        else:
            # Unit test - this function delegates to get_most_watched_items
            with patch('tools.trending_api.get_most_watched_items.fn') as mock_get_watched:
                mock_get_watched.return_value = json.dumps({
                    "status": "success",
                    "data": {
                        "items": [],
                        "total_count": 0,
                        "category_id": "9355"
                    }
                })
                
                result = await get_trending_items_by_category.fn(
                    ctx=mock_context,
                    category_id="9355",
                    max_results=15
                )
                
                # Verify it called get_most_watched_items with correct params
                mock_get_watched.assert_called_once_with(
                    ctx=mock_context,
                    category_id="9355",
                    max_results=15
                )
    
    # ==============================================================================
    # Helper Function Tests (Unit tests only)
    # ==============================================================================
    
    @TestMode.skip_in_integration("Helper function is unit test only")
    @pytest.mark.asyncio
    async def test_search_trending_items(self, mock_context, mock_credentials):
        """Test the _search_trending_items helper function."""
        from api.oauth import OAuthManager, OAuthConfig
        from api.rest_client import EbayRestClient, RestConfig
        
        # Create mock clients
        oauth_config = OAuthConfig(
            client_id="test_app_id",
            client_secret="test_cert_id",
            sandbox=True
        )
        oauth_manager = OAuthManager(oauth_config)
        
        with patch.object(EbayRestClient, 'get') as mock_get:
            mock_get.return_value = {
                "itemSummaries": [
                    {
                        "itemId": "v1|123|0",
                        "title": "Test Item",
                        "price": {"value": "99.99", "currency": "USD"}
                    }
                ]
            }
            
            rest_client = EbayRestClient(oauth_manager, RestConfig(sandbox=True))
            
            items = await _search_trending_items(
                rest_client,
                mock_context,
                "trending popular",
                "9355",
                "newlyListed",
                max_results=10
            )
            
            assert len(items) == 1
            assert items[0]["item_id"] == "v1|123|0"
            assert items[0]["title"] == "Test Item"
            assert items[0]["price"]["value"] == 99.99
            
            # Verify search parameters
            call_params = mock_get.call_args[1]["params"]
            assert call_params["q"] == "trending popular"
            assert call_params["sort"] == "newlyListed"
            assert "categoryIds:{9355}" in call_params["filter"]
    
    # ==============================================================================
    # Error Handling Tests
    # ==============================================================================
    
    @pytest.mark.asyncio
    async def test_get_most_watched_items_error_handling(self, mock_context, mock_credentials):
        """Test error handling in most watched items."""
        # Test error handling based on test mode
        if self.is_integration_mode:
            # Test with invalid input
            try:
                result = await get_most_watched_items.fn(
                    ctx=mock_context,
                    max_results=200  # Over limit
                )
                
                data = json.loads(result)
                if data["status"] == "error":
                    if data["error_code"] != "VALIDATION_ERROR":
                        error_msg = data.get("error_message", "")
                        details = data.get("details", {})
                        pytest.fail(f"Unexpected error - {data['error_code']}: {error_msg}\nDetails: {details}")
                else:
                    pytest.fail(f"Expected validation error for over-limit, but got success: {data}")
            except Exception as e:
                pytest.fail(f"Exception during error handling test: {e}")
        else:
            # Unit test error handling
            with patch('tools.trending_api.EbayRestClient') as MockClient:
                mock_client = MockClient.return_value
                mock_client.get = AsyncMock(side_effect=EbayApiError(
                    status_code=429,
                    error_response=TestDataError.ERROR_RATE_LIMIT
                ))
                mock_client.close = AsyncMock()
                
                with patch('tools.trending_api.mcp.config.app_id', mock_credentials["app_id"]), \
                     patch('tools.trending_api.mcp.config.cert_id', mock_credentials["cert_id"]):
                    
                    result = await get_most_watched_items.fn(
                        ctx=mock_context
                    )
                    
                    data = json.loads(result)
                    # Since _search_trending_items catches errors and returns empty list,
                    # we should get a success response with empty items
                    if data["status"] == "error":
                        # If error propagated, check it's the rate limit error
                        if data["error_code"] not in ["EXTERNAL_API_ERROR", "RATE_LIMIT_ERROR"]:
                            error_msg = data.get("error_message", "")
                            details = data.get("details", {})
                            pytest.fail(f"Unexpected error - {data['error_code']}: {error_msg}\nDetails: {details}")
                    else:
                        # If successful, should have empty items due to error handling
                        assert data["data"]["items"] == []
                        assert data["data"]["total_count"] == 0
    
    # ==============================================================================
    # Static Fallback Tests
    # ==============================================================================
    
    @pytest.mark.asyncio
    async def test_get_most_watched_items_no_credentials(self, mock_context):
        """Test most watched items with no credentials returns empty response."""
        with patch('tools.trending_api.mcp.config.app_id', ''), \
             patch('tools.trending_api.mcp.config.cert_id', ''):
            
            result = await get_most_watched_items.fn(
                ctx=mock_context,
                max_results=10
            )
            
            data = assert_api_response_success(result)
            # Should return empty items with a note
            assert data["data"]["items"] == []
            assert data["data"]["total_count"] == 0
            assert "note" in data["data"]
            assert "credentials" in data["data"]["note"].lower()