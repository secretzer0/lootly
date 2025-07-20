"""
Tests for Enhanced Browse API endpoints.

This module tests the enhanced Browse API with comprehensive filtering, sorting,
and both RESTful and legacy item ID support. Tests run in both unit and integration modes.

Run modes:
- Unit tests: pytest test_browse_api_enhanced.py
- Integration tests: pytest test_browse_api_enhanced.py -v -s --test-mode=integration

IMPLEMENTATION FOLLOWS: PYDANTIC-FIRST DEVELOPMENT METHODOLOGY
- All inputs use Pydantic models with strong validation
- Tests cover all new enums and filter capabilities
- Comprehensive error handling validation
- Support for both ID formats (RESTful and legacy)
"""
import json
import pytest
from unittest.mock import AsyncMock, patch

from tools.browse_api import (
    search_items,
    get_item_details,
    build_price_filter,
    build_conditions_filter,
    build_sellers_filter,
    combine_filters,
    BrowseSearchInput,
    ItemDetailsInput
)
from models.browse_enums import SortField
from api.errors import EbayApiError
from tools.tests.test_data import TestDataGood, TestDataError, TestDataBrowseEnhanced
from tools.tests.base_test import BaseApiTest


class TestBrowseAPIEnhanced(BaseApiTest):
    """Test suite for enhanced Browse API endpoints."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Test data
        self.test_query = "iPhone"
        self.test_restful_id = "v1|123456789|0"
        self.test_legacy_id = "272662989093"
        self.test_category_id = "9355"  # Cell Phones & Smartphones
    
    @pytest.fixture
    def mock_context(self):
        """Create mock MCP context."""
        context = AsyncMock()
        context.info = AsyncMock()
        context.error = AsyncMock()
        context.report_progress = AsyncMock()
        context.warning = AsyncMock()
        context.success = AsyncMock()
        return context
    
    # ==============================================================================
    # INFRASTRUCTURE VALIDATION TEST
    # ==============================================================================
    
    @pytest.mark.asyncio
    async def test_infrastructure_validation(self, mock_context):
        """CRITICAL: Validates integration infrastructure works before testing."""
        if not self.is_integration_mode:
            pytest.skip("Infrastructure validation only runs in integration mode")
        
        print("Testing integration infrastructure with Browse API...")
        print("This API uses basic scope (no user consent required)")
        
        search_input = BrowseSearchInput(q="test", limit=1)
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
    
    def test_browse_search_input_enhanced_validation(self):
        """Test enhanced BrowseSearchInput with all new fields."""
        if self.is_integration_mode:
            pytest.skip("Pydantic validation tests only run in unit mode")
        
        # Valid input with all fields
        valid_input = BrowseSearchInput(
            q="laptop",
            category_ids="175672",
            filter="price:[500..2000],conditions:{NEW}",
            sort=SortField.PRICE_ASC,
            limit=100,
            offset=50
        )
        assert valid_input.q == "laptop"
        assert valid_input.category_ids == "175672"
        assert valid_input.sort == SortField.PRICE_ASC
        assert valid_input.limit == 100
        assert valid_input.offset == 50
        
        # Test enum validation - sort field must be valid enum
        with pytest.raises(ValueError):
            BrowseSearchInput(q="test", sort="invalid_sort")
        
        # Test category_ids pattern validation - must be numeric
        with pytest.raises(ValueError, match="String should match pattern"):
            BrowseSearchInput(q="test", category_ids="abc123")
        
        # Test single category constraint - comma not allowed in pattern
        with pytest.raises(ValueError, match="String should match pattern"):
            BrowseSearchInput(q="test", category_ids="9355,175672")
        
        # Test limit constraints
        with pytest.raises(ValueError, match="Input should be less than or equal to 200"):
            BrowseSearchInput(q="test", limit=300)
        
        # Test query length constraints
        with pytest.raises(ValueError, match="String should have at most 300 characters"):
            BrowseSearchInput(q="x" * 301)
    
    def test_item_details_input_id_formats(self):
        """Test ItemDetailsInput with both ID formats."""
        if self.is_integration_mode:
            pytest.skip("Pydantic validation tests only run in unit mode")
        
        # RESTful ID
        restful_input = ItemDetailsInput(item_id="v1|123456789|0")
        assert restful_input.item_id == "v1|123456789|0"
        
        # RESTful ID with multi-SKU
        multi_sku_input = ItemDetailsInput(item_id="v1|162862654321|422363059871")
        assert multi_sku_input.item_id == "v1|162862654321|422363059871"
        
        # Legacy ID - minimum length
        legacy_input = ItemDetailsInput(item_id="1234567890")
        assert legacy_input.item_id == "1234567890"
        
        # Legacy ID - maximum length
        legacy_long_input = ItemDetailsInput(item_id="1234567890123456789")
        assert legacy_long_input.item_id == "1234567890123456789"
        
        # Invalid formats
        with pytest.raises(ValueError, match="Invalid item ID format"):
            ItemDetailsInput(item_id="abc123")
        
        with pytest.raises(ValueError, match="Invalid item ID format"):
            ItemDetailsInput(item_id="123")  # Too short
        
        with pytest.raises(ValueError, match="Invalid RESTful item ID format"):
            ItemDetailsInput(item_id="v1|abc|0")  # Non-numeric in RESTful
        
        with pytest.raises(ValueError, match="Invalid item ID format"):
            ItemDetailsInput(item_id="v1|123")  # Incomplete RESTful
    
    # ==============================================================================
    # FILTER HELPER FUNCTION TESTS (Unit tests only)
    # ==============================================================================
    
    def test_build_price_filter(self):
        """Test price filter building."""
        if self.is_integration_mode:
            pytest.skip("Helper function tests only run in unit mode")
        
        assert build_price_filter(10, 50) == "price:[10..50]"
        assert build_price_filter(min_price=10) == "price:[10..]"
        assert build_price_filter(max_price=50) == "price:[..50]"
        assert build_price_filter() == ""
        
        # Test with decimals
        assert build_price_filter(10.99, 50.50) == "price:[10.99..50.5]"
    
    def test_build_conditions_filter(self):
        """Test conditions filter building."""
        if self.is_integration_mode:
            pytest.skip("Helper function tests only run in unit mode")
        
        assert build_conditions_filter("NEW") == "conditions:{NEW}"
        assert build_conditions_filter("NEW", "LIKE_NEW") == "conditions:{NEW|LIKE_NEW}"
        assert build_conditions_filter("NEW", "LIKE_NEW", "CERTIFIED_REFURBISHED") == "conditions:{NEW|LIKE_NEW|CERTIFIED_REFURBISHED}"
        assert build_conditions_filter() == ""
    
    def test_build_sellers_filter(self):
        """Test sellers filter building."""
        if self.is_integration_mode:
            pytest.skip("Helper function tests only run in unit mode")
        
        assert build_sellers_filter("techstore") == "sellers:{techstore}"
        assert build_sellers_filter("store1", "store2") == "sellers:{store1|store2}"
        assert build_sellers_filter("bestbuy", "dell", "hp") == "sellers:{bestbuy|dell|hp}"
        assert build_sellers_filter() == ""
    
    def test_combine_filters(self):
        """Test combining multiple filters."""
        if self.is_integration_mode:
            pytest.skip("Helper function tests only run in unit mode")
        
        filters = combine_filters(
            build_price_filter(10, 100),
            build_conditions_filter("NEW"),
            build_sellers_filter("bestbuy")
        )
        assert filters == "price:[10..100],conditions:{NEW},sellers:{bestbuy}"
        
        # Test with empty filters
        assert combine_filters("", "", "price:[10..20]") == "price:[10..20]"
        assert combine_filters("", "", "") == ""
        
        # Test complex combination
        complex_filters = combine_filters(
            build_price_filter(50, 200),
            build_conditions_filter("NEW", "CERTIFIED_REFURBISHED"),
            build_sellers_filter("dell", "hp"),
            "buyingOptions:{FIXED_PRICE|BEST_OFFER}",
            "charityOnly:true"
        )
        expected = "price:[50..200],conditions:{NEW|CERTIFIED_REFURBISHED},sellers:{dell|hp},buyingOptions:{FIXED_PRICE|BEST_OFFER},charityOnly:true"
        assert complex_filters == expected
    
    # ==============================================================================
    # SEARCH ITEMS TESTS
    # ==============================================================================
    
    @pytest.mark.asyncio
    async def test_search_items_basic(self, mock_context):
        """Test basic item search functionality with enhanced features."""
        search_input = BrowseSearchInput(
            q="iPhone",
            sort=SortField.BEST_MATCH,
            limit=10
        )
        
        if self.is_integration_mode:
            # Integration test - real API call
            print(f"\nTesting real API call to eBay Browse API...")
            print(f"Query: {search_input.q}, Sort: {search_input.sort.value}")
            
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
                    "body": TestDataBrowseEnhanced.SEARCH_RESPONSE_FILTERED,
                    "headers": {}
                })
                mock_client.close = AsyncMock()
                
                MockConfig.app_id = "test_app"
                MockConfig.cert_id = "test_cert"
                MockConfig.sandbox_mode = True
                MockConfig.rate_limit_per_day = 5000
                MockConfig.redirect_uri = "https://localhost:3000/callback"
                
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
                assert call_args[1]["params"]["sort"] == "BestMatch"
    
    @pytest.mark.asyncio
    async def test_search_items_with_advanced_filters(self, mock_context):
        """Test search with comprehensive filter combinations."""
        # Build complex filter
        filter_str = combine_filters(
            build_price_filter(500, 1500),
            build_conditions_filter("NEW", "CERTIFIED_REFURBISHED"),
            build_sellers_filter("dell", "hp")
        )
        
        search_input = BrowseSearchInput(
            q="gaming laptop",
            category_ids="175672",
            filter=filter_str,
            sort=SortField.PRICE_ASC,
            limit=50
        )
        
        if self.is_integration_mode:
            # Real API test
            result = await search_items.fn(ctx=mock_context, search_input=search_input)
            response = json.loads(result)
            
            if response["status"] == "error":
                error_code = response.get("error_code")
                error_msg = response.get("error_message", "")
                # Some filters might not work in sandbox
                print(f"Note: Filter test returned error - {error_code}: {error_msg}")
                # Don't fail test as sandbox may have limitations
            else:
                assert response["status"] == "success"
                print(f"Advanced filter search returned {len(response['data']['items'])} items")
        else:
            # Unit test with mocks
            with patch('tools.browse_api.EbayRestClient') as MockClient, \
                 patch('tools.browse_api.mcp.config') as MockConfig:
                
                mock_client = MockClient.return_value
                mock_client.get = AsyncMock(return_value={
                    "body": TestDataBrowseEnhanced.SEARCH_RESPONSE_FILTERED,
                    "headers": {}
                })
                mock_client.close = AsyncMock()
                
                MockConfig.app_id = "test_app"
                MockConfig.cert_id = "test_cert"
                MockConfig.sandbox_mode = True
                MockConfig.rate_limit_per_day = 5000
                MockConfig.redirect_uri = "https://localhost:3000/callback"
                
                result = await search_items.fn(ctx=mock_context, search_input=search_input)
                response = json.loads(result)
                
                assert response["status"] == "success"
                
                # Verify filter was passed correctly
                call_args = mock_client.get.call_args
                params = call_args[1]["params"]
                assert params["filter"] == filter_str
                assert params["category_ids"] == "175672"
                assert params["sort"] == "price"
    
    @pytest.mark.asyncio
    async def test_all_sort_options(self, mock_context):
        """Test all available sort options."""
        for sort_name, sort_value in [
            ("BestMatch", SortField.BEST_MATCH),
            ("price", SortField.PRICE_ASC),
            ("-price", SortField.PRICE_DESC),
            ("newlyListed", SortField.NEWLY_LISTED),
            ("endingSoonest", SortField.ENDING_SOONEST)
        ]:
            search_input = BrowseSearchInput(
                q="test item",
                sort=sort_value,
                limit=5
            )
            
            if self.is_integration_mode:
                # Test each sort option
                result = await search_items.fn(ctx=mock_context, search_input=search_input)
                response = json.loads(result)
                
                if response["status"] == "success":
                    print(f"Sort by {sort_name}: {len(response['data']['items'])} items")
                else:
                    print(f"Sort by {sort_name}: {response.get('error_message', 'Error')}")
            else:
                # Unit test - just verify sort value is passed
                with patch('tools.browse_api.EbayRestClient') as MockClient, \
                     patch('tools.browse_api.mcp.config') as MockConfig:
                    
                    mock_client = MockClient.return_value
                    mock_client.get = AsyncMock(return_value={
                        "body": TestDataGood.BROWSE_SEARCH_RESPONSE,
                        "headers": {}
                    })
                    mock_client.close = AsyncMock()
                    
                    MockConfig.app_id = "test_app"
                    MockConfig.cert_id = "test_cert"
                    MockConfig.sandbox_mode = True
                    MockConfig.rate_limit_per_day = 5000
                    MockConfig.redirect_uri = "https://localhost:3000/callback"
                    
                    result = await search_items.fn(ctx=mock_context, search_input=search_input)
                    response = json.loads(result)
                    assert response["status"] == "success"
                    
                    # Verify sort parameter
                    call_args = mock_client.get.call_args
                    assert call_args[1]["params"]["sort"] == sort_value.value
    
    @pytest.mark.asyncio
    async def test_category_search_replacement(self, mock_context):
        """Test category search using search_items (replaces get_items_by_category)."""
        search_input = BrowseSearchInput(
            q="phone",  # Specific search term instead of wildcard
            category_ids="9355",  # Cell Phones & Smartphones
            sort=SortField.BEST_MATCH,
            limit=20
        )
        
        if self.is_integration_mode:
            result = await search_items.fn(ctx=mock_context, search_input=search_input)
            response = json.loads(result)
            
            # MUST succeed for test to pass
            assert response["status"] == "success", \
                f"Category search failed: {response.get('error_message', 'Unknown error')}"
            
            # Verify we got results
            assert len(response["data"]["items"]) > 0, "No items returned for category search"
            
            print(f"Category search found {response['data']['total']} items in category 9355")
            
            # Verify at least some items are in the correct category
            items_checked = 0
            items_in_category = 0
            
            for item in response["data"]["items"][:5]:  # Check first 5 items
                categories = item.get("categories", [])
                if categories:
                    items_checked += 1
                    category_ids = [cat.get("categoryId", "") for cat in categories]
                    if any(cid == "9355" or cid.startswith("9355") for cid in category_ids):
                        items_in_category += 1
            
            # Log results for debugging
            print(f"Checked {items_checked} items, {items_in_category} were in category 9355")
            
            # At least some items should be in the category (sandbox data may vary)
            if items_checked > 0:
                assert items_in_category > 0, \
                    f"None of the {items_checked} items checked were in category 9355"
        else:
            # Unit test
            with patch('tools.browse_api.EbayRestClient') as MockClient, \
                 patch('tools.browse_api.mcp.config') as MockConfig:
                
                mock_client = MockClient.return_value
                mock_client.get = AsyncMock(return_value={
                    "body": TestDataGood.BROWSE_SEARCH_RESPONSE,
                    "headers": {}
                })
                mock_client.close = AsyncMock()
                
                MockConfig.app_id = "test_app"
                MockConfig.cert_id = "test_cert"
                MockConfig.sandbox_mode = True
                MockConfig.rate_limit_per_day = 5000
                MockConfig.redirect_uri = "https://localhost:3000/callback"
                
                result = await search_items.fn(ctx=mock_context, search_input=search_input)
                response = json.loads(result)
                
                assert response["status"] == "success"
                
                # Verify category_ids parameter
                call_args = mock_client.get.call_args
                assert call_args[1]["params"]["category_ids"] == "9355"
    
    @pytest.mark.asyncio
    async def test_search_items_pagination(self, mock_context):
        """Test pagination functionality."""
        search_input = BrowseSearchInput(
            q="phone",
            limit=50,
            offset=100
        )
        
        if self.is_integration_mode:
            result = await search_items.fn(ctx=mock_context, search_input=search_input)
            response = json.loads(result)
            
            if response["status"] == "success":
                assert response["data"]["limit"] == 50
                assert response["data"]["offset"] == 100
                print(f"Pagination test: offset={response['data']['offset']}, limit={response['data']['limit']}")
        else:
            # Unit test
            with patch('tools.browse_api.EbayRestClient') as MockClient, \
                 patch('tools.browse_api.mcp.config') as MockConfig:
                
                mock_client = MockClient.return_value
                mock_client.get = AsyncMock(return_value={
                    "body": {
                        **TestDataGood.BROWSE_SEARCH_RESPONSE,
                        "limit": 50,
                        "offset": 100
                    },
                    "headers": {}
                })
                mock_client.close = AsyncMock()
                
                MockConfig.app_id = "test_app"
                MockConfig.cert_id = "test_cert"
                MockConfig.sandbox_mode = True
                MockConfig.rate_limit_per_day = 5000
                MockConfig.redirect_uri = "https://localhost:3000/callback"
                
                result = await search_items.fn(ctx=mock_context, search_input=search_input)
                response = json.loads(result)
                
                assert response["status"] == "success"
                assert response["data"]["limit"] == 50
                assert response["data"]["offset"] == 100
    
    # ==============================================================================
    # GET ITEM DETAILS TESTS
    # ==============================================================================
    
    @pytest.mark.asyncio
    async def test_get_item_details_restful_id(self, mock_context):
        """Test with RESTful item ID format."""
        details_input = ItemDetailsInput(item_id="v1|272662989093|0")
        
        if self.is_integration_mode:
            # First search for a real item to get valid ID
            search_result = await search_items.fn(
                ctx=mock_context,
                search_input=BrowseSearchInput(q="test", limit=1)
            )
            search_response = json.loads(search_result)
            
            if search_response["status"] == "success" and search_response["data"]["items"]:
                real_item_id = search_response["data"]["items"][0]["itemId"]
                details_input.item_id = real_item_id
                
                print(f"\nTesting real API call for item details...")
                print(f"RESTful Item ID: {details_input.item_id}")
                
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
                assert "itemId" in response["data"]
                assert response["data"]["itemId"] == real_item_id
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
                    "body": TestDataGood.BROWSE_ITEM_DETAILS,
                    "headers": {}
                })
                mock_client.close = AsyncMock()
                
                MockConfig.app_id = "test_app"
                MockConfig.cert_id = "test_cert"
                MockConfig.sandbox_mode = True
                MockConfig.rate_limit_per_day = 5000
                MockConfig.redirect_uri = "https://localhost:3000/callback"
                
                # Execute test
                result = await get_item_details.fn(
                    ctx=mock_context,
                    details_input=details_input
                )
                
                response = json.loads(result)
                assert response["status"] == "success"
                assert "itemId" in response["data"]
                
                # Verify API was called correctly - standard endpoint for RESTful ID
                mock_client.get.assert_called_once()
                call_args = mock_client.get.call_args
                assert f"/buy/browse/v1/item/{details_input.item_id}" in call_args[0][0]
                assert call_args[1]["params"]["fieldgroups"] == "PRODUCT,ADDITIONAL_SELLER_DETAILS"
    
    @pytest.mark.asyncio
    async def test_get_item_details_legacy_id_detection(self, mock_context):
        """Test automatic legacy ID detection and conversion."""
        # Test with legacy ID
        details_input = ItemDetailsInput(item_id="272662989093")
        
        if self.is_integration_mode:
            # First search for real item to extract legacy ID
            search_result = await search_items.fn(
                ctx=mock_context,
                search_input=BrowseSearchInput(q="test", limit=1)
            )
            search_response = json.loads(search_result)
            
            if search_response["status"] == "success" and search_response["data"]["items"]:
                # Extract legacy ID from RESTful ID
                restful_id = search_response["data"]["items"][0]["itemId"]
                if "|" in restful_id:
                    legacy_id = restful_id.split("|")[1]
                    
                    # Test with legacy ID
                    details_input.item_id = legacy_id
                    print(f"\nTesting legacy ID: {legacy_id}")
                    
                    result = await get_item_details.fn(ctx=mock_context, details_input=details_input)
                    response = json.loads(result)
                    
                    if response["status"] == "success":
                        # Should return RESTful ID format
                        assert response["data"]["itemId"].startswith("v1|")
                        assert legacy_id in response["data"]["itemId"]
                        print("Legacy ID successfully converted to RESTful format")
                    else:
                        # Legacy ID might not work in sandbox
                        print(f"Legacy ID test: {response.get('error_message', 'Error')}")
            else:
                pytest.skip("No items found for legacy ID test")
        else:
            # Unit test with mocks
            with patch('tools.browse_api.EbayRestClient') as MockClient, \
                 patch('tools.browse_api.mcp.config') as MockConfig:
                
                mock_client = MockClient.return_value
                # Mock returns RESTful ID even though we passed legacy
                mock_response_body = {
                    **TestDataGood.BROWSE_ITEM_DETAILS,
                    "itemId": f"v1|{details_input.item_id}|0"
                }
                mock_client.get = AsyncMock(return_value={
                    "body": mock_response_body,
                    "headers": {}
                })
                mock_client.close = AsyncMock()
                
                MockConfig.app_id = "test_app"
                MockConfig.cert_id = "test_cert"
                MockConfig.sandbox_mode = True
                MockConfig.rate_limit_per_day = 5000
                MockConfig.redirect_uri = "https://localhost:3000/callback"
                
                result = await get_item_details.fn(ctx=mock_context, details_input=details_input)
                response = json.loads(result)
                
                assert response["status"] == "success"
                
                # Verify legacy endpoint is called
                call_args = mock_client.get.call_args
                assert "/buy/browse/v1/item/get_item_by_legacy_id" in call_args[0][0]
                assert call_args[1]["params"]["legacy_item_id"] == "272662989093"
    
    # ==============================================================================
    # ERROR HANDLING TESTS
    # ==============================================================================
    
    @pytest.mark.asyncio
    async def test_search_items_invalid_filter_syntax(self, mock_context):
        """Test handling of invalid filter syntax."""
        search_input = BrowseSearchInput(
            q="test",
            filter="invalid:filter:syntax"  # Invalid syntax
        )
        
        if self.is_integration_mode:
            result = await search_items.fn(ctx=mock_context, search_input=search_input)
            response = json.loads(result)
            
            if response["status"] == "error":
                assert response["error_code"] in ["EXTERNAL_API_ERROR", "VALIDATION_ERROR"]
                print(f"Invalid filter test: {response['error_message']}")
            else:
                # API might be lenient
                print("API accepted invalid filter syntax")
        else:
            # Unit test - mock API error
            with patch('tools.browse_api.EbayRestClient') as MockClient, \
                 patch('tools.browse_api.mcp.config') as MockConfig:
                
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
                MockConfig.redirect_uri = "https://localhost:3000/callback"
                
                result = await search_items.fn(ctx=mock_context, search_input=search_input)
                response = json.loads(result)
                
                assert response["status"] == "error"
                assert response["error_code"] == "EXTERNAL_API_ERROR"
    
    @pytest.mark.asyncio
    async def test_get_item_details_not_found(self, mock_context):
        """Test 404 handling for non-existent item."""
        details_input = ItemDetailsInput(item_id="v1|9999999999999|0")
        
        if self.is_integration_mode:
            result = await get_item_details.fn(ctx=mock_context, details_input=details_input)
            response = json.loads(result)
            
            if response["status"] == "error":
                # Expected for non-existent item
                assert response["error_code"] in ["RESOURCE_NOT_FOUND", "EXTERNAL_API_ERROR"]
                print("Successfully handled item not found error")
            else:
                # Sandbox might return success
                print("API was lenient with non-existent item")
        else:
            # Unit test - mock 404 error
            with patch('tools.browse_api.EbayRestClient') as MockClient, \
                 patch('tools.browse_api.mcp.config') as MockConfig:
                
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
                MockConfig.redirect_uri = "https://localhost:3000/callback"
                
                result = await get_item_details.fn(ctx=mock_context, details_input=details_input)
                response = json.loads(result)
                
                assert response["status"] == "error"
                assert response["error_code"] == "RESOURCE_NOT_FOUND"
    
    @pytest.mark.asyncio
    async def test_missing_credentials(self, mock_context):
        """Test handling of missing credentials."""
        search_input = BrowseSearchInput(q="test", limit=10)
        
        if self.is_integration_mode:
            pytest.skip("Missing credentials test only runs in unit mode")
        else:
            # Unit test - mock missing credentials
            with patch('tools.browse_api.mcp.config') as MockConfig:
                MockConfig.app_id = ""
                MockConfig.cert_id = ""
                
                result = await search_items.fn(ctx=mock_context, search_input=search_input)
                response = json.loads(result)
                
                assert response["status"] == "error"
                assert response["error_code"] == "CONFIGURATION_ERROR"
                assert "eBay App ID and Cert ID must be configured" in response["error_message"]
    
    @pytest.mark.asyncio
    async def test_wildcard_search_error_handling(self, mock_context):
        """Test that wildcard searches that are too large return appropriate errors."""
        if not self.is_integration_mode:
            pytest.skip("Wildcard error handling test only runs in integration mode")
        
        search_input = BrowseSearchInput(
            q="*",  # Wildcard that should trigger error
            category_ids="9355",
            limit=20
        )
        
        result = await search_items.fn(ctx=mock_context, search_input=search_input)
        response = json.loads(result)
        
        # This SHOULD return an error
        assert response["status"] == "error", "Expected error for wildcard search"
        assert response["error_code"] == "EXTERNAL_API_ERROR"
        
        # Check for the specific error indicators
        error_msg = response.get("error_message", "").lower()
        details = str(response.get("details", {}))
        
        assert ("12023" in details or "too large" in error_msg), \
            f"Expected error 12023 or 'too large' message, got: {error_msg}"
        
        print(f"Wildcard search correctly returned error: {response.get('error_message')}")