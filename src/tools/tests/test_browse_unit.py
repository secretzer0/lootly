"""Unit tests for Browse API tools."""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from decimal import Decimal
from fastmcp import Context

from tools.browse_api import search_items, get_item_details, get_items_by_category
from api.errors import EbayApiError
import json


@pytest.fixture
def mock_context():
    """Create a mock FastMCP context."""
    ctx = Mock(spec=Context)
    ctx.info = AsyncMock()
    ctx.error = AsyncMock()
    ctx.debug = AsyncMock()
    ctx.report_progress = AsyncMock()
    return ctx


@pytest.fixture
def mock_rest_client():
    """Create a mock REST client."""
    client = Mock()
    client.get = AsyncMock()
    client.close = AsyncMock()
    return client


@pytest.fixture(autouse=True)
def mock_global_mcp():
    """Mock the global mcp instance."""
    with patch('tools.browse_api.mcp') as mock_mcp:
        mock_mcp.config.app_id = "test_app_id"
        mock_mcp.config.cert_id = "test_cert_id"
        mock_mcp.config.sandbox_mode = True
        mock_mcp.config.rate_limit_per_day = 5000
        mock_mcp.logger = Mock()
        yield mock_mcp


class TestSearchItems:
    """Test the search_items tool."""
    
    @pytest.mark.asyncio
    async def test_search_items_success(self, mock_context, mock_rest_client):
        """Test successful item search."""
        # Mock API response
        mock_response = {
            "total": 2,
            "itemSummaries": [
                {
                    "itemId": "v1|123456789|0",
                    "title": "Vintage Camera",
                    "price": {"value": "99.99", "currency": "USD"},
                    "condition": "USED",
                    "seller": {
                        "username": "seller1",
                        "feedbackPercentage": 99.5,
                        "feedbackScore": 1000
                    },
                    "itemLocation": {"country": "US", "city": "New York"},
                    "categories": [
                        {"categoryId": "625", "categoryName": "Cameras & Photo"}
                    ],
                    "image": {"imageUrl": "https://example.com/image1.jpg"},
                    "itemWebUrl": "https://ebay.com/itm/123456789"
                },
                {
                    "itemId": "v1|987654321|0",
                    "title": "Digital Camera",
                    "price": {"value": "299.99", "currency": "USD"},
                    "condition": "NEW",
                    "seller": {
                        "username": "seller2",
                        "feedbackPercentage": 100.0,
                        "feedbackScore": 5000
                    },
                    "itemLocation": {"country": "US", "city": "Los Angeles"},
                    "categories": [
                        {"categoryId": "625", "categoryName": "Cameras & Photo"}
                    ],
                    "image": {"imageUrl": "https://example.com/image2.jpg"},
                    "itemWebUrl": "https://ebay.com/itm/987654321",
                    "shippingOptions": [
                        {
                            "shippingServiceCode": "Standard",
                            "shippingCost": {"value": "0", "currency": "USD"}
                        }
                    ]
                }
            ]
        }
        
        with patch('tools.browse_api.EbayRestClient') as mock_client_class, \
             patch('tools.browse_api.OAuthManager') as mock_oauth_class:
            mock_client_class.return_value = mock_rest_client
            mock_rest_client.get.return_value = mock_response
            
            # Call the tool
            result = await search_items.fn(
                ctx=mock_context,
                query="camera",
                limit=50,
                offset=0
            )
            
            # Parse result
            result_data = json.loads(result)
            
            # Debug print
            print(f"Response keys: {result_data.keys()}")
            print(f"Response: {result_data}")
            
            # Check what errors were logged
            print(f"Context error calls: {mock_context.error.call_args_list}")
            
            # Verify response
            assert result_data["status"] == "success"
            assert result_data["message"] == "Found 2 items matching 'camera'"
            assert len(result_data["data"]["items"]) == 2
            assert result_data["data"]["total"] == 2
            
            # Verify first item
            item1 = result_data["data"]["items"][0]
            assert item1["item_id"] == "v1|123456789|0"
            assert item1["title"] == "Vintage Camera"
            assert float(item1["price"]["value"]) == 99.99
            assert item1["price"]["currency"] == "USD"
            
            # Verify API call
            mock_rest_client.get.assert_called_once_with(
                "/buy/browse/v1/item_summary/search",
                params={
                    "q": "camera",
                    "limit": 50,
                    "offset": 0,
                    "sort": "relevance"
                },
                scope="https://api.ebay.com/oauth/api_scope/buy.browse"
            )
    
    @pytest.mark.asyncio
    async def test_search_items_with_filters(self, mock_context, mock_rest_client):
        """Test search with multiple filters."""
        mock_response = {"total": 0, "itemSummaries": []}
        
        with patch('tools.browse_api.EbayRestClient') as mock_client_class:
            mock_client_class.return_value = mock_rest_client
            mock_rest_client.get.return_value = mock_response
            
            # Call with filters
            result = await search_items.fn(
                ctx=mock_context,
                query="laptop",
                category_ids="175672,111422",
                price_min=500.0,
                price_max=1500.0,
                conditions="NEW,CERTIFIED_REFURBISHED",
                sellers="bestbuy,apple",
                sort="price"
            )
            
            # Verify API call includes filters
            call_args = mock_rest_client.get.call_args
            params = call_args[1]["params"]
            
            assert params["q"] == "laptop"
            assert params["sort"] == "price"
            assert "filter" in params
            
            # Check filter includes all components
            filter_str = params["filter"]
            assert "categoryIds:{175672,111422}" in filter_str
            assert "price:[500.0..1500.0]" in filter_str
            assert "conditions:{NEW,CERTIFIED_REFURBISHED}" in filter_str
            assert "sellers:{bestbuy,apple}" in filter_str
    
    @pytest.mark.asyncio
    @pytest.mark.no_credentials
    async def test_search_items_no_credentials(self, mock_context):
        """Test search without credentials."""
        with patch('tools.browse_api.mcp') as mock_mcp:
            mock_mcp.config.app_id = ""
            mock_mcp.config.cert_id = ""
            
            result = await search_items.fn(
                ctx=mock_context,
                query="test"
            )
            
            result_data = json.loads(result)
            assert result_data["status"] == "success"
            assert "credentials not configured" in result_data["data"]["note"]
            assert result_data["data"]["items"] == []
    
    @pytest.mark.asyncio
    async def test_search_items_api_error(self, mock_context, mock_rest_client):
        """Test handling of API errors."""
        with patch('tools.browse_api.EbayRestClient') as mock_client_class:
            mock_client_class.return_value = mock_rest_client
            mock_rest_client.get.side_effect = EbayApiError(
                status_code=400,
                error_response={"message": "Invalid query"}
            )
            
            result = await search_items.fn(
                ctx=mock_context,
                query=""
            )
            
            result_data = json.loads(result)
            assert result_data["status"] == "error"
            assert result_data["error_code"] == "VALIDATION_ERROR"


class TestGetItemDetails:
    """Test the get_item_details tool."""
    
    @pytest.mark.asyncio
    async def test_get_item_details_success(self, mock_context, mock_rest_client):
        """Test successful item details retrieval."""
        mock_response = {
            "itemId": "v1|123456789|0",
            "title": "Vintage Camera with Accessories",
            "description": "A beautiful vintage camera in excellent condition.",
            "price": {"value": "299.99", "currency": "USD"},
            "condition": "USED",
            "seller": {
                "username": "vintagecollector",
                "feedbackPercentage": 99.8,
                "feedbackScore": 2500
            },
            "itemLocation": {"country": "US", "city": "Portland", "stateOrProvince": "OR"},
            "categories": [
                {"categoryId": "625", "categoryName": "Cameras & Photo"}
            ],
            "image": {"imageUrl": "https://example.com/main.jpg"},
            "additionalImages": [
                {"imageUrl": "https://example.com/img2.jpg"},
                {"imageUrl": "https://example.com/img3.jpg"}
            ],
            "itemWebUrl": "https://ebay.com/itm/123456789",
            "brand": "Canon",
            "mpn": "AE-1"
        }
        
        with patch('tools.browse_api.EbayRestClient') as mock_client_class:
            mock_client_class.return_value = mock_rest_client
            mock_rest_client.get.return_value = mock_response
            
            result = await get_item_details.fn(
                ctx=mock_context,
                item_id="v1|123456789|0",
                include_description=True
            )
            
            result_data = json.loads(result)
            
            # Verify response
            assert result_data["status"] == "success"
            assert result_data["message"] == "Successfully retrieved item details"
            
            item = result_data["data"]
            assert item["item_id"] == "v1|123456789|0"
            assert item["title"] == "Vintage Camera with Accessories"
            assert item["description"] == "A beautiful vintage camera in excellent condition."
            assert item["brand"] == "Canon"
            assert item["mpn"] == "AE-1"
            assert len(item["images"]) == 3  # Main + 2 additional
            
            # Verify API call
            mock_rest_client.get.assert_called_once_with(
                "/buy/browse/v1/item/v1|123456789|0",
                params={"fieldgroups": "PRODUCT,COMPACT,ADDITIONAL_SELLER_DETAILS"},
                scope="https://api.ebay.com/oauth/api_scope/buy.browse"
            )
    
    @pytest.mark.asyncio
    async def test_get_item_details_not_found(self, mock_context, mock_rest_client):
        """Test item not found error."""
        with patch('tools.browse_api.EbayRestClient') as mock_client_class:
            mock_client_class.return_value = mock_rest_client
            mock_rest_client.get.side_effect = EbayApiError(
                status_code=404,
                error_response={"message": "Item not found"}
            )
            
            result = await get_item_details.fn(
                ctx=mock_context,
                item_id="v1|999999999|0"
            )
            
            result_data = json.loads(result)
            assert result_data["status"] == "error"
            assert result_data["error_code"] == "RESOURCE_NOT_FOUND"
            assert "not found" in result_data["error_message"]


class TestGetItemsByCategory:
    """Test the get_items_by_category tool."""
    
    @pytest.mark.asyncio
    async def test_get_items_by_category(self, mock_context):
        """Test that category browsing delegates to search."""
        with patch('tools.browse_api.search_items.fn') as mock_search:
            mock_search.return_value = '{"success": true}'
            
            result = await get_items_by_category.fn(
                ctx=mock_context,
                category_id="625",
                sort="price",
                limit=100,
                offset=50
            )
            
            # Verify it calls search_items with correct params
            mock_search.assert_called_once_with(
                ctx=mock_context,
                query="*",
                category_ids="625",
                sort="price",
                limit=100,
                offset=50
            )