"""
Tests for Browse API endpoints.

This module tests all 3 browse API endpoints with both unit tests (using mocks)
and integration tests (using real eBay sandbox API).

Run modes:
- Unit tests: pytest test_browse_api.py
- Integration tests: pytest test_browse_api.py -v -s --test-mode=integration

CRITICAL: Integration tests use Browse API which requires only basic scope (no user consent).
Browse API should SUCCEED in integration mode with 2-5 second timing.

TEST METHODOLOGY:
1. Infrastructure validation (Browse API should succeed)
2. Test all endpoints with proper Pydantic model validation
3. Test error cases with proper classification
4. Use diagnostic approach to distinguish real problems from expected failures

Professional implementation - no emojis, professional output only.
"""
import json
import pytest
import os
from decimal import Decimal
from unittest.mock import AsyncMock, patch

from tools.browse_api import (
    search_items,
    get_item_details,
    get_items_by_category,
    BrowseSearchInput,
    ItemDetailsInput,
    CategoryBrowseInput
)
from api.errors import EbayApiError
from tools.tests.test_data import (
    TestDataBrowse,
    TestDataError
)


class TestBrowseAPI:
    """Test suite for Browse API endpoints."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Determine test mode
        self.is_integration_mode = os.getenv("TEST_MODE") == "integration"
        
        # Test data
        self.test_query = "iPhone"
        self.test_item_id = "v1|123456789|0"
        self.test_category_id = "9355"  # Cell Phones & Smartphones
    
    @pytest.fixture
    def mock_context(self):
        """Create mock MCP context."""
        context = AsyncMock()
        context.info = AsyncMock()
        context.error = AsyncMock()
        context.report_progress = AsyncMock()
        return context
    
    
    # ==============================================================================
    # CRITICAL INFRASTRUCTURE VALIDATION TEST
    # ==============================================================================
    
    @pytest.mark.asyncio
    async def test_infrastructure_validation(self, mock_context):
        """CRITICAL: Validates integration infrastructure works before testing restricted APIs."""
        if not self.is_integration_mode:
            pytest.skip("Infrastructure validation only runs in integration mode")
        
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
    # PYDANTIC MODEL VALIDATION TESTS (Unit tests only)
    # ==============================================================================
    
    def test_browse_search_input_validation(self):
        """Test BrowseSearchInput Pydantic model validation."""
        if self.is_integration_mode:
            pytest.skip("Pydantic validation tests only run in unit mode")
        
        # Valid input
        valid_input = BrowseSearchInput(
            query="iPhone",
            category_ids="9355",
            limit=50,
            price_min=Decimal("100.00"),
            price_max=Decimal("500.00")
        )
        assert valid_input.query == "iPhone"
        assert valid_input.limit == 50
        assert valid_input.price_min == Decimal("100.00")
        
        # Invalid query - too short
        with pytest.raises(ValueError, match="String should have at least 1 character"):
            BrowseSearchInput(query="", limit=50)
        
        # Invalid limit - too high
        with pytest.raises(ValueError, match="Input should be less than or equal to 200"):
            BrowseSearchInput(query="test", limit=300)
        
        # Invalid price range - max < min
        with pytest.raises(ValueError, match="price_max must be greater than price_min"):
            BrowseSearchInput(
                query="test",
                price_min=Decimal("500.00"),
                price_max=Decimal("100.00")
            )
        
        # Invalid sort value
        with pytest.raises(ValueError, match="sort must be one of"):
            BrowseSearchInput(query="test", sort="invalid_sort")
    
    def test_item_details_input_validation(self):
        """Test ItemDetailsInput Pydantic model validation."""
        if self.is_integration_mode:
            pytest.skip("Pydantic validation tests only run in unit mode")
        
        # Valid input
        valid_input = ItemDetailsInput(
            item_id="v1|123456789|0",
            include_description=True
        )
        assert valid_input.item_id == "v1|123456789|0"
        assert valid_input.include_description is True
        
        # Invalid item_id - empty
        with pytest.raises(ValueError, match="String should have at least 1 character"):
            ItemDetailsInput(item_id="")
        
        # Invalid item_id - just whitespace
        with pytest.raises(ValueError, match="String should have at least 1 character"):
            ItemDetailsInput(item_id="   ")
    
    def test_category_browse_input_validation(self):
        """Test CategoryBrowseInput Pydantic model validation."""
        if self.is_integration_mode:
            pytest.skip("Pydantic validation tests only run in unit mode")
        
        # Valid input
        valid_input = CategoryBrowseInput(
            category_id="9355",
            sort="price",
            limit=100,
            price_min=Decimal("50.00"),
            price_max=Decimal("200.00")
        )
        assert valid_input.category_id == "9355"
        assert valid_input.sort == "price"
        
        # Invalid category_id - empty
        with pytest.raises(ValueError, match="String should have at least 1 character"):
            CategoryBrowseInput(category_id="")
        
        # Invalid price range
        with pytest.raises(ValueError, match="price_max must be greater than price_min"):
            CategoryBrowseInput(
                category_id="9355",
                price_min=Decimal("200.00"),
                price_max=Decimal("100.00")
            )
    
    # ==============================================================================
    # SEARCH ITEMS TESTS
    # ==============================================================================
    
    @pytest.mark.asyncio
    async def test_search_items_basic(self, mock_context):
        """Test basic item search functionality."""
        search_input = BrowseSearchInput(
            query="iPhone",
            limit=10
        )
        
        if self.is_integration_mode:
            # Integration test - real API call
            print(f"\nTesting real API call to eBay Browse API...")
            print(f"Query: {search_input.query}, Limit: {search_input.limit}")
            
            result = await search_items.fn(
                ctx=mock_context,
                search_input=search_input
            )
            response = json.loads(result)

            print(f"API Response status: {response['status']}")
            
            if response["status"] == "error":
                error_code = response.get("error_code")
                error_msg = response.get("error_message", "")
                details = response.get("details", {})
                pytest.fail(f"API call failed - {error_code}: {error_msg}\nDetails: {details}")
            
            # Test succeeded - verify we got expected data
            assert response["status"] == "success"
            assert "items" in response["data"]
            assert "total" in response["data"]
            assert isinstance(response["data"]["items"], list)
            assert isinstance(response["data"]["total"], int)
            print(f"Successfully found {response['data']['total']} items")
        
        else:
            # Unit test - mocked dependencies
            with patch('tools.browse_api.EbayRestClient') as MockClient, \
                 patch('tools.browse_api.mcp.config') as MockConfig:
                
                # Setup all mocks
                mock_client = MockClient.return_value
                mock_client.get = AsyncMock(return_value={
                    "body": TestDataBrowse.SEARCH_RESPONSE,
                    "headers": {}
                })
                mock_client.close = AsyncMock()
                
                MockConfig.app_id = "test_app"
                MockConfig.cert_id = "test_cert"
                MockConfig.sandbox_mode = True
                MockConfig.rate_limit_per_day = 5000
                
                # Execute test
                result = await search_items.fn(
                    ctx=mock_context,
                    search_input=search_input
                )
                
                response = json.loads(result)
                assert response["status"] == "success"
                assert "items" in response["data"]
                assert "total" in response["data"]
                
                # Verify API was called correctly
                mock_client.get.assert_called_once()
                call_args = mock_client.get.call_args
                assert "/buy/browse/v1/item_summary/search" in call_args[0][0]
                assert call_args[1]["params"]["q"] == "iPhone"
                assert call_args[1]["params"]["limit"] == 10
    
    @pytest.mark.asyncio
    async def test_search_items_with_filters(self, mock_context):
        """Test item search with filters."""
        search_input = BrowseSearchInput(
            query="laptop",
            category_ids="177",  # PC Laptops
            price_min=Decimal("500.00"),
            price_max=Decimal("2000.00"),
            conditions="NEW,USED_EXCELLENT",
            sort="price",
            limit=20
        )
        
        if self.is_integration_mode:
            # Integration test - real API call
            result = await search_items.fn(
                ctx=mock_context,
                search_input=search_input
            )
            response = json.loads(result)

            if response["status"] == "error":
                error_code = response.get("error_code")
                error_msg = response.get("error_message", "")
                details = response.get("details", {})
                pytest.fail(f"API call failed - {error_code}: {error_msg}\nDetails: {details}")
            
            assert response["status"] == "success"
            assert len(response["data"]["items"]) <= 20
            print(f"Search with filters returned {len(response['data']['items'])} items")
        
        else:
            # Unit test - mocked dependencies
            with patch('tools.browse_api.EbayRestClient') as MockClient, \
                 patch('tools.browse_api.mcp.config') as MockConfig:
                
                # Setup all mocks
                mock_client = MockClient.return_value
                mock_client.get = AsyncMock(return_value={
                    "body": TestDataBrowse.SEARCH_RESPONSE_FILTERED,
                    "headers": {}
                })
                mock_client.close = AsyncMock()
                
                MockConfig.app_id = "test_app"
                MockConfig.cert_id = "test_cert"
                MockConfig.sandbox_mode = True
                MockConfig.rate_limit_per_day = 5000
                
                # Execute test
                result = await search_items.fn(
                    ctx=mock_context,
                    search_input=search_input
                )
                
                response = json.loads(result)
                assert response["status"] == "success"
                
                # Verify filters were passed correctly
                call_args = mock_client.get.call_args
                params = call_args[1]["params"]
                assert params["q"] == "laptop"
                assert params["limit"] == 20
                assert params["sort"] == "price"
                
                # Verify filter string was built correctly
                filter_str = params["filter"]
                assert "categoryIds:{177}" in filter_str
                assert "price:[500.00..2000.00]" in filter_str
                assert "conditions:{NEW,USED_EXCELLENT}" in filter_str
    
    @pytest.mark.asyncio
    async def test_search_items_empty_results(self, mock_context):
        """Test handling of empty search results."""
        search_input = BrowseSearchInput(
            query="xyzabc123notexist",
            limit=10
        )
        
        if self.is_integration_mode:
            # Integration test - search for something unlikely to exist
            result = await search_items.fn(
                ctx=mock_context,
                search_input=search_input
            )
            response = json.loads(result)
            
            if response["status"] == "error":
                error_code = response.get("error_code")
                error_msg = response.get("error_message", "")
                details = response.get("details", {})
                pytest.fail(f"API call failed - {error_code}: {error_msg}\nDetails: {details}")
            
            assert response["status"] == "success"
            assert isinstance(response["data"]["items"], list)
            # Empty results are acceptable
            print(f"Empty search returned {len(response['data']['items'])} items")
        
        else:
            # Unit test with empty response
            with patch('tools.browse_api.EbayRestClient') as MockClient, \
                 patch('tools.browse_api.OAuthManager') as MockOAuth, \
                 patch('tools.browse_api.mcp.config') as MockConfig:
                
                # Setup all mocks
                mock_client = MockClient.return_value
                mock_client.get = AsyncMock(return_value={
                    "body": TestDataBrowse.SEARCH_RESPONSE_EMPTY,
                    "headers": {}
                })
                mock_client.close = AsyncMock()
                
                MockConfig.app_id = "test_app"
                MockConfig.cert_id = "test_cert"
                MockConfig.sandbox_mode = True
                MockConfig.rate_limit_per_day = 5000
                
                # Execute test
                result = await search_items.fn(
                    ctx=mock_context,
                    search_input=search_input
                )
                
                response = json.loads(result)
                assert response["status"] == "success"
                assert response["data"]["items"] == []
                assert response["data"]["total"] == 0
    
    # ==============================================================================
    # GET ITEM DETAILS TESTS
    # ==============================================================================
    
    @pytest.mark.asyncio
    async def test_get_item_details_basic(self, mock_context):
        """Test getting item details."""
        details_input = ItemDetailsInput(
            item_id="v1|123456789|0",
            include_description=True
        )
        
        if self.is_integration_mode:
            # First search for a real item to get item ID
            search_input = BrowseSearchInput(query="iPhone", limit=1)
            search_result = await search_items.fn(ctx=mock_context, search_input=search_input)
            search_response = json.loads(search_result)
            
            if search_response["status"] == "success" and search_response["data"]["items"]:
                real_item_id = search_response["data"]["items"][0]["item_id"]
                details_input.item_id = real_item_id
                
                print(f"\nTesting real API call for item details...")
                print(f"Item ID: {details_input.item_id}")
                
                result = await get_item_details.fn(
                    ctx=mock_context,
                    details_input=details_input
                )
                
                response = json.loads(result)
                if response["status"] == "error":
                    error_code = response.get("error_code")
                    error_msg = response.get("error_message", "")
                    details = response.get("details", {})
                    pytest.fail(f"API call failed - {error_code}: {error_msg}\nDetails: {details}")
                
                assert response["status"] == "success"
                assert "item_id" in response["data"]
                assert response["data"]["item_id"] == real_item_id
                print(f"Successfully retrieved item details")
            else:
                pytest.skip("No items found for details test")
        
        else:
            # Unit test - mocked dependencies
            with patch('tools.browse_api.EbayRestClient') as MockClient, \
                 patch('tools.browse_api.mcp.config') as MockConfig:
                
                # Setup all mocks
                mock_client = MockClient.return_value
                mock_client.get = AsyncMock(return_value={
                    "body": TestDataBrowse.ITEM_DETAILS_RESPONSE,
                    "headers": {}
                })
                mock_client.close = AsyncMock()
                
                MockConfig.app_id = "test_app"
                MockConfig.cert_id = "test_cert"
                MockConfig.sandbox_mode = True
                MockConfig.rate_limit_per_day = 5000
                
                # Execute test
                result = await get_item_details.fn(
                    ctx=mock_context,
                    details_input=details_input
                )
                
                response = json.loads(result)
                assert response["status"] == "success"
                assert "item_id" in response["data"]
                
                # Verify API was called correctly
                mock_client.get.assert_called_once()
                call_args = mock_client.get.call_args
                assert f"/buy/browse/v1/item/{details_input.item_id}" in call_args[0][0]
                assert call_args[1]["params"]["fieldgroups"] == "PRODUCT,ADDITIONAL_SELLER_DETAILS"
    
    @pytest.mark.asyncio
    async def test_get_item_details_compact(self, mock_context):
        """Test getting item details in compact mode."""
        details_input = ItemDetailsInput(
            item_id="v1|123456789|0",
            include_description=False
        )
        
        if self.is_integration_mode:
            # Skip detailed integration test for compact mode
            pytest.skip("Compact mode test runs in unit mode only")
        
        else:
            # Unit test - mocked dependencies
            with patch('tools.browse_api.EbayRestClient') as MockClient, \
                 patch('tools.browse_api.mcp.config') as MockConfig:
                
                # Setup all mocks
                mock_client = MockClient.return_value
                mock_client.get = AsyncMock(return_value={
                    "body": TestDataBrowse.ITEM_DETAILS_RESPONSE_COMPACT,
                    "headers": {}
                })
                mock_client.close = AsyncMock()
                
                MockConfig.app_id = "test_app"
                MockConfig.cert_id = "test_cert"
                MockConfig.sandbox_mode = True
                MockConfig.rate_limit_per_day = 5000
                
                # Execute test
                result = await get_item_details.fn(
                    ctx=mock_context,
                    details_input=details_input
                )
                
                response = json.loads(result)
                assert response["status"] == "success"
                
                # Verify compact fieldgroups was used
                call_args = mock_client.get.call_args
                assert call_args[1]["params"]["fieldgroups"] == "COMPACT"
    
    # ==============================================================================
    # GET ITEMS BY CATEGORY TESTS
    # ==============================================================================
    
    @pytest.mark.asyncio
    async def test_get_items_by_category_basic(self, mock_context):
        """Test browsing items by category."""
        category_input = CategoryBrowseInput(
            category_id="9355",  # Cell Phones & Smartphones
            limit=10
        )
        
        if self.is_integration_mode:
            # Integration test - real API call
            print(f"\nTesting real API call for category browsing...")
            print(f"Category ID: {category_input.category_id}")
            
            result = await get_items_by_category.fn(
                ctx=mock_context,
                category_input=category_input
            )
            response = json.loads(result)

            if response["status"] == "error":
                error_code = response.get("error_code")
                error_msg = response.get("error_message", "")
                details = response.get("details", {})
                pytest.fail(f"API call failed - {error_code}: {error_msg}\nDetails: {details}")
            
            assert response["status"] == "success"
            assert "items" in response["data"]
            assert "total" in response["data"]
            print(f"Successfully found {response['data']['total']} items in category")
        
        else:
            # Unit test - mocked dependencies
            with patch('tools.browse_api.EbayRestClient') as MockClient, \
                 patch('tools.browse_api.mcp.config') as MockConfig:
                
                # Setup all mocks
                mock_client = MockClient.return_value
                mock_client.get = AsyncMock(return_value={
                    "body": TestDataBrowse.CATEGORY_RESPONSE,
                    "headers": {}
                })
                mock_client.close = AsyncMock()
                
                MockConfig.app_id = "test_app"
                MockConfig.cert_id = "test_cert"
                MockConfig.sandbox_mode = True
                MockConfig.rate_limit_per_day = 5000
                
                # Execute test
                result = await get_items_by_category.fn(
                    ctx=mock_context,
                    category_input=category_input
                )
                
                response = json.loads(result)
                assert response["status"] == "success"
                
                # Verify API was called correctly
                mock_client.get.assert_called_once()
                call_args = mock_client.get.call_args
                params = call_args[1]["params"]
                assert params["q"] == "item"  # Generic query for category browsing
                assert "categoryIds:{9355}" in params["filter"]
    
    @pytest.mark.asyncio
    async def test_get_items_by_category_with_filters(self, mock_context):
        """Test category browsing with price filters."""
        category_input = CategoryBrowseInput(
            category_id="9355",
            price_min=Decimal("100.00"),
            price_max=Decimal("500.00"),
            sort="price",
            limit=20
        )
        
        if self.is_integration_mode:
            # Integration test - real API call
            result = await get_items_by_category.fn(
                ctx=mock_context,
                category_input=category_input
            )
            response = json.loads(result)

            if response["status"] == "error":
                error_code = response.get("error_code")
                error_msg = response.get("error_message", "")
                details = response.get("details", {})
                pytest.fail(f"API call failed - {error_code}: {error_msg}\nDetails: {details}")
            
            assert response["status"] == "success"
            print(f"Category browsing with filters returned {len(response['data']['items'])} items")
        
        else:
            # Unit test - mocked dependencies
            with patch('tools.browse_api.EbayRestClient') as MockClient, \
                 patch('tools.browse_api.mcp.config') as MockConfig:
                
                # Setup all mocks
                mock_client = MockClient.return_value
                mock_client.get = AsyncMock(return_value={
                    "body": TestDataBrowse.CATEGORY_RESPONSE_FILTERED,
                    "headers": {}
                })
                mock_client.close = AsyncMock()
                
                MockConfig.app_id = "test_app"
                MockConfig.cert_id = "test_cert"
                MockConfig.sandbox_mode = True
                MockConfig.rate_limit_per_day = 5000
                
                # Execute test
                result = await get_items_by_category.fn(
                    ctx=mock_context,
                    category_input=category_input
                )
                
                response = json.loads(result)
                assert response["status"] == "success"
                
                # Verify filters were applied correctly
                call_args = mock_client.get.call_args
                params = call_args[1]["params"]
                assert params["sort"] == "price"
                assert params["limit"] == 20
                filter_str = params["filter"]
                assert "categoryIds:{9355}" in filter_str
                assert "price:[100.00..500.00]" in filter_str
    
    # ==============================================================================
    # ERROR HANDLING TESTS
    # ==============================================================================
    
    @pytest.mark.asyncio
    async def test_search_items_api_error(self, mock_context):
        """Test handling of API errors in search."""
        search_input = BrowseSearchInput(query="test", limit=10)
        
        if self.is_integration_mode:
            # Integration test - test with invalid category
            search_input.category_ids = "99999999"  # Invalid category
            
            result = await search_items.fn(
                ctx=mock_context,
                search_input=search_input
            )
            response = json.loads(result)

            if response["status"] == "error":
                # This is expected for invalid category
                assert response["error_code"] == "EXTERNAL_API_ERROR"
                print("Successfully handled API error for invalid category")
            else:
                # API might be lenient with invalid categories
                print("API was lenient with invalid category")
        
        else:
            # Unit test - mock API error
            with patch('tools.browse_api.EbayRestClient') as MockClient, \
                 patch('tools.browse_api.OAuthManager') as MockOAuth, \
                 patch('tools.browse_api.mcp.config') as MockConfig:
                
                # Setup all mocks
                mock_client = MockClient.return_value
                mock_client.get = AsyncMock(side_effect=EbayApiError(
                    status_code=400,
                    error_response=TestDataError.ERROR_INVALID_CATEGORY
                ))
                mock_client.close = AsyncMock()
                
                MockConfig.app_id = "test_app"
                MockConfig.cert_id = "test_cert"
                MockConfig.sandbox_mode = True
                MockConfig.rate_limit_per_day = 5000
                
                # Execute test
                result = await search_items.fn(
                    ctx=mock_context,
                    search_input=search_input
                )
                
                response = json.loads(result)
                assert response["status"] == "error"
                assert response["error_code"] == "EXTERNAL_API_ERROR"
    
    @pytest.mark.asyncio
    async def test_get_item_details_not_found(self, mock_context):
        """Test handling of item not found error."""
        details_input = ItemDetailsInput(item_id="v1|999999999|0")
        
        if self.is_integration_mode:
            # Integration test - test with non-existent item
            result = await get_item_details.fn(
                ctx=mock_context,
                details_input=details_input
            )
            response = json.loads(result)
            
            if response["status"] == "error":
                # This is expected for non-existent item
                assert response["error_code"] == "RESOURCE_NOT_FOUND"
                print("Successfully handled item not found error")
            else:
                # API might return default data
                print("API was lenient with non-existent item")
        
        else:
            # Unit test - mock 404 error
            with patch('tools.browse_api.EbayRestClient') as MockClient, \
                 patch('tools.browse_api.OAuthManager') as MockOAuth, \
                 patch('tools.browse_api.mcp.config') as MockConfig:
                
                # Setup all mocks
                mock_client = MockClient.return_value
                mock_client.get = AsyncMock(side_effect=EbayApiError(
                    status_code=404,
                    error_response=TestDataError.ERROR_NOT_FOUND
                ))
                mock_client.close = AsyncMock()
                
                MockConfig.app_id = "test_app"
                MockConfig.cert_id = "test_cert"
                MockConfig.sandbox_mode = True
                MockConfig.rate_limit_per_day = 5000
                
                # Execute test
                result = await get_item_details.fn(
                    ctx=mock_context,
                    details_input=details_input
                )
                
                response = json.loads(result)
                assert response["status"] == "error"
                assert response["error_code"] == "RESOURCE_NOT_FOUND"
    
    @pytest.mark.asyncio
    async def test_missing_credentials(self, mock_context):
        """Test handling of missing credentials."""
        search_input = BrowseSearchInput(query="test", limit=10)
        
        if self.is_integration_mode:
            pytest.skip("Missing credentials test only runs in unit mode")
        
        else:
            # Unit test - mock missing credentials
            with patch('tools.browse_api.mcp.config') as MockConfig:
                MockConfig.app_id = ""
                MockConfig.cert_id = ""
                
                # Execute test
                result = await search_items.fn(
                    ctx=mock_context,
                    search_input=search_input
                )
                
                response = json.loads(result)
                assert response["status"] == "error"
                assert response["error_code"] == "CONFIGURATION_ERROR"
                assert "eBay App ID and Cert ID must be configured" in response["error_message"]