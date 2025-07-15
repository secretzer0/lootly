"""Tests for eBay Finding API tools."""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastmcp import Context
from data_types import ResponseStatus, ErrorCode
from tools.finding_api import search_items, get_search_keywords, find_items_by_category, find_items_advanced


@pytest.fixture
def mock_context():
    """Create a mock MCP context."""
    ctx = AsyncMock(spec=Context)
    ctx.info = AsyncMock()
    ctx.error = AsyncMock()
    ctx.report_progress = AsyncMock()
    
    # Mock server with config and logger
    ctx.server = MagicMock()
    ctx.server.config = MagicMock()
    ctx.server.config.app_id = "test-app-id"
    ctx.server.config.sandbox_mode = True
    ctx.server.config.site_id = "EBAY-US"
    ctx.server.config.cache_ttl = 300
    ctx.server.config.max_pages = 10
    ctx.server.config.domain = "sandbox.ebay.com"
    ctx.server.config.max_retries = 3
    
    ctx.server.logger = MagicMock()
    ctx.server.logger.tool_failed = MagicMock()
    
    return ctx


@pytest.fixture
def mock_ebay_response():
    """Create a mock eBay API response."""
    return {
        "searchResult": [{
            "item": [
                {
                    "itemId": ["123456789"],
                    "title": ["Test Item"],
                    "sellingStatus": [{
                        "currentPrice": [{
                            "value": "99.99",
                            "_currencyId": "USD"
                        }]
                    }],
                    "condition": [{
                        "conditionDisplayName": ["New"]
                    }],
                    "listingInfo": [{
                        "listingType": ["FixedPrice"],
                        "endTime": ["2024-12-31T23:59:59.000Z"]
                    }],
                    "location": ["United States"],
                    "shippingInfo": [{
                        "shippingServiceCost": [{
                            "value": "0.00"
                        }],
                        "shippingType": ["Free"]
                    }],
                    "viewItemURL": ["https://www.ebay.com/itm/123456789"],
                    "galleryURL": ["https://i.ebayimg.com/images/test.jpg"]
                }
            ]
        }],
        "paginationOutput": [{
            "totalEntries": ["100"],
            "totalPages": ["2"]
        }]
    }


@pytest.mark.asyncio
async def test_search_items_success(mock_context, mock_ebay_response):
    """Test successful item search."""
    with patch("tools.finding_api.EbayApiClient") as MockClient:
        # Setup mock client
        mock_client = MockClient.return_value
        mock_client.validate_pagination = MagicMock()
        mock_client.execute_with_retry = AsyncMock(return_value=mock_ebay_response)
        
        # Execute search
        result_json = await search_items.fn(
            keywords="test item",
            min_price=10.0,
            max_price=200.0,
            page_number=1,
            ctx=mock_context
        )
        
        # Parse result
        result = json.loads(result_json)
        
        # Verify response structure
        assert result["status"] == ResponseStatus.SUCCESS.value
        assert "data" in result
        assert "items" in result["data"]
        assert len(result["data"]["items"]) == 1
        
        # Verify item data
        item = result["data"]["items"][0]
        assert item["item_id"] == "123456789"
        assert item["title"] == "Test Item"
        assert item["price"]["value"] == 99.99
        assert item["price"]["currency"] == "USD"
        
        # Verify pagination
        assert result["data"]["pagination"]["total_items"] == 100
        assert result["data"]["pagination"]["total_pages"] == 2
        
        # Verify context calls
        mock_context.info.assert_called()
        mock_context.report_progress.assert_called()


@pytest.mark.asyncio
async def test_search_items_validation_error(mock_context):
    """Test search with invalid parameters."""
    with patch("tools.finding_api.EbayApiClient"):
        # We don't need to mock the client for validation errors
        # as they should be caught before API calls
        result_json = await search_items.fn(
            keywords="",  # Empty keywords
            ctx=mock_context
        )
        
        result = json.loads(result_json)
        assert result["status"] == ResponseStatus.ERROR.value
        assert result["error_code"] == ErrorCode.VALIDATION_ERROR.value


@pytest.mark.asyncio
async def test_search_items_api_error(mock_context):
    """Test search with API error."""
    with patch("tools.finding_api.EbayApiClient") as MockClient, \
         patch("lootly_server.mcp") as mock_mcp:
        # Setup mock client to raise error
        mock_client = MockClient.return_value
        mock_client.validate_pagination = MagicMock()
        mock_client.execute_with_retry = AsyncMock(side_effect=Exception("API Error"))
        
        result_json = await search_items.fn(
            keywords="test item",
            ctx=mock_context
        )
        
        result = json.loads(result_json)
        assert result["status"] == ResponseStatus.ERROR.value
        assert result["error_code"] == ErrorCode.INTERNAL_ERROR.value
        assert "API Error" in result["error_message"]
        
        # Verify error logging
        mock_context.error.assert_called()
        mock_mcp.logger.tool_failed.assert_called()


@pytest.mark.asyncio
async def test_get_search_keywords_success(mock_context):
    """Test keyword suggestions."""
    with patch("tools.finding_api.EbayApiClient") as MockClient:
        # Setup mock response
        mock_client = MockClient.return_value
        mock_client.execute_with_retry = AsyncMock(return_value={
            "keywords": [
                {"keyword": ["iphone 15"]},
                {"keyword": ["iphone 15 pro"]},
                {"keyword": ["iphone 15 case"]}
            ]
        })
        
        result_json = await get_search_keywords.fn(
            partial_keyword="iphone",
            ctx=mock_context
        )
        
        result = json.loads(result_json)
        assert result["status"] == ResponseStatus.SUCCESS.value
        assert len(result["data"]["suggestions"]) == 3
        assert "iphone 15" in result["data"]["suggestions"]


@pytest.mark.asyncio
async def test_get_search_keywords_short_input(mock_context):
    """Test keyword suggestions with too short input."""
    result_json = await get_search_keywords.fn(
        partial_keyword="i",  # Too short
        ctx=mock_context
    )
    
    result = json.loads(result_json)
    assert result["status"] == ResponseStatus.ERROR.value
    assert result["error_code"] == ErrorCode.VALIDATION_ERROR.value


@pytest.mark.asyncio
async def test_find_items_by_category_success(mock_context, mock_ebay_response):
    """Test category browsing."""
    with patch("tools.finding_api.EbayApiClient") as MockClient:
        mock_client = MockClient.return_value
        mock_client.validate_pagination = MagicMock()
        mock_client.execute_with_retry = AsyncMock(return_value=mock_ebay_response)
        
        result_json = await find_items_by_category.fn(
            category_id="12345",
            ctx=mock_context
        )
        
        result = json.loads(result_json)
        assert result["status"] == ResponseStatus.SUCCESS.value
        assert result["data"]["category_id"] == "12345"
        assert len(result["data"]["items"]) == 1


@pytest.mark.asyncio
async def test_find_items_advanced_success(mock_context, mock_ebay_response):
    """Test advanced search with multiple filters."""
    with patch("tools.finding_api.EbayApiClient") as MockClient:
        mock_client = MockClient.return_value
        mock_client.execute_with_retry = AsyncMock(return_value=mock_ebay_response)
        
        result_json = await find_items_advanced.fn(
            keywords="test",
            seller_id="test_seller",
            free_shipping_only=True,
            min_feedback_score=100,
            ctx=mock_context
        )
        
        result = json.loads(result_json)
        assert result["status"] == ResponseStatus.SUCCESS.value
        assert result["data"]["filters_applied"] == 3  # seller, shipping, feedback
        
        # Verify API was called with filters
        call_args = mock_client.execute_with_retry.call_args[0]
        assert call_args[1] == "findItemsAdvanced"
        params = call_args[2]
        assert "itemFilter" in params
        assert len(params["itemFilter"]) == 3


@pytest.mark.asyncio
async def test_find_items_advanced_no_criteria(mock_context):
    """Test advanced search without keywords or category."""
    result_json = await find_items_advanced.fn(
        # No keywords or category_id
        ctx=mock_context
    )
    
    result = json.loads(result_json)
    assert result["status"] == ResponseStatus.ERROR.value
    assert result["error_code"] == ErrorCode.VALIDATION_ERROR.value
    assert "keywords or category_id" in result["error_message"]