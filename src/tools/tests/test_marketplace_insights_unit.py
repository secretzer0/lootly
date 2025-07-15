"""Unit tests for Marketplace Insights API tools."""
import pytest
from unittest.mock import Mock, patch, AsyncMock
import json
from datetime import datetime, timedelta
from fastmcp import Context

from tools.marketplace_insights_api import (
    search_item_sales, 
    get_category_sales_insights,
    get_product_sales_history,
    get_trending_items,
    _has_marketplace_insights_access,
    _convert_sales_data
)
from api.errors import EbayApiError, AuthorizationError


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
    with patch('tools.marketplace_insights_api.mcp') as mock_mcp:
        mock_mcp.config.app_id = "test_app_id"
        mock_mcp.config.cert_id = "test_cert_id"
        mock_mcp.config.sandbox_mode = True
        mock_mcp.config.rate_limit_per_day = 5000
        mock_mcp.config.marketplace_insights_enabled = True
        mock_mcp.logger = Mock()
        yield mock_mcp


@pytest.fixture
def mock_sales_response():
    """Mock sales data response."""
    return {
        "itemSales": [
            {
                "itemId": "v1|123456789|0",
                "title": "iPhone 15 Pro 256GB",
                "categoryId": "9355",
                "categoryName": "Cell Phones & Smartphones",
                "lastSoldDate": "2024-01-15T12:30:00.000Z",
                "lastSoldPrice": {
                    "value": "899.99",
                    "currency": "USD"
                },
                "totalSoldQuantity": 5,
                "condition": "NEW",
                "itemWebUrl": "https://ebay.com/itm/123456789",
                "image": {
                    "imageUrl": "https://i.ebayimg.com/images/g/123/s-l1600.jpg"
                }
            },
            {
                "itemId": "v1|987654321|0",
                "title": "iPhone 15 Pro 128GB",
                "categoryId": "9355",
                "categoryName": "Cell Phones & Smartphones",
                "lastSoldDate": "2024-01-14T08:15:00.000Z",
                "lastSoldPrice": {
                    "value": "799.99",
                    "currency": "USD"
                },
                "totalSoldQuantity": 3,
                "condition": "NEW",
                "itemWebUrl": "https://ebay.com/itm/987654321",
                "image": {
                    "imageUrl": "https://i.ebayimg.com/images/g/456/s-l1600.jpg"
                }
            }
        ],
        "total": 2
    }


class TestMarketplaceInsightsAccess:
    """Test access control for Marketplace Insights API."""
    
    def test_has_marketplace_insights_access_enabled(self):
        """Test access when enabled in config."""
        with patch('tools.marketplace_insights_api.mcp') as mock_mcp:
            mock_mcp.config.marketplace_insights_enabled = True
            assert _has_marketplace_insights_access() == True
    
    def test_has_marketplace_insights_access_disabled(self):
        """Test access when disabled in config."""
        with patch('tools.marketplace_insights_api.mcp') as mock_mcp:
            mock_mcp.config.marketplace_insights_enabled = False
            assert _has_marketplace_insights_access() == False
    
    def test_has_marketplace_insights_access_not_configured(self):
        """Test access when not configured."""
        with patch('tools.marketplace_insights_api.mcp') as mock_mcp:
            # No marketplace_insights_enabled attribute
            del mock_mcp.config.marketplace_insights_enabled
            assert _has_marketplace_insights_access() == False


class TestDataConversion:
    """Test data conversion functions."""
    
    def test_convert_sales_data_complete(self):
        """Test conversion with complete sales data."""
        sales_data = {
            "itemId": "v1|123456789|0",
            "title": "Test Item",
            "categoryId": "12345",
            "categoryName": "Test Category",
            "lastSoldDate": "2024-01-15T12:30:00.000Z",
            "lastSoldPrice": {
                "value": "99.99",
                "currency": "USD"
            },
            "totalSoldQuantity": 10,
            "condition": "NEW",
            "itemWebUrl": "https://ebay.com/itm/123456789",
            "image": {
                "imageUrl": "https://example.com/image.jpg"
            }
        }
        
        result = _convert_sales_data(sales_data)
        
        assert result["item_id"] == "v1|123456789|0"
        assert result["title"] == "Test Item"
        assert result["category_id"] == "12345"
        assert result["category_name"] == "Test Category"
        assert result["last_sold_date"] == "2024-01-15T12:30:00+00:00"
        assert result["last_sold_price"]["value"] == 99.99
        assert result["last_sold_price"]["currency"] == "USD"
        assert result["total_sold_quantity"] == 10
        assert result["condition"] == "NEW"
        assert result["listing_url"] == "https://ebay.com/itm/123456789"
        assert result["image_url"] == "https://example.com/image.jpg"
    
    def test_convert_sales_data_minimal(self):
        """Test conversion with minimal sales data."""
        sales_data = {
            "itemId": "v1|123456789|0",
            "title": "Test Item"
        }
        
        result = _convert_sales_data(sales_data)
        
        assert result["item_id"] == "v1|123456789|0"
        assert result["title"] == "Test Item"
        assert result["last_sold_date"] is None
        assert result["last_sold_price"]["value"] == 0.0
        assert result["last_sold_price"]["currency"] == "USD"
        assert result["total_sold_quantity"] == 0


class TestSearchItemSales:
    """Test the search_item_sales tool."""
    
    @pytest.mark.asyncio
    async def test_search_item_sales_no_access(self, mock_context):
        """Test search without API access returns static data."""
        with patch('tools.marketplace_insights_api._has_marketplace_insights_access', return_value=False):
            result = await search_item_sales.fn(
                ctx=mock_context,
                query="iPhone"
            )
            
            result_data = json.loads(result)
            assert result_data["status"] == "success"
            assert "trending_searches" in result_data["data"]
            assert result_data["data"]["data_source"] == "static_trends"
            assert "note" in result_data["data"]
    
    @pytest.mark.asyncio
    async def test_search_item_sales_with_category_no_access(self, mock_context):
        """Test category search without API access."""
        with patch('tools.marketplace_insights_api._has_marketplace_insights_access', return_value=False):
            result = await search_item_sales.fn(
                ctx=mock_context,
                category_ids="293"
            )
            
            result_data = json.loads(result)
            assert result_data["status"] == "success"
            assert "sales_data" in result_data["data"]
            assert result_data["data"]["sales_data"][0]["category_id"] == "293"
            assert result_data["data"]["data_source"] == "static_trends"
    
    @pytest.mark.asyncio
    async def test_search_item_sales_success(self, mock_context, mock_rest_client, mock_sales_response):
        """Test successful sales search."""
        with patch('tools.marketplace_insights_api._has_marketplace_insights_access', return_value=True), \
             patch('tools.marketplace_insights_api.EbayRestClient') as mock_client_class, \
             patch('tools.marketplace_insights_api.OAuthManager') as mock_oauth_class:
            
            mock_client_class.return_value = mock_rest_client
            mock_rest_client.get.return_value = mock_sales_response
            
            result = await search_item_sales.fn(
                ctx=mock_context,
                query="iPhone 15",
                limit=50,
                offset=0
            )
            
            result_data = json.loads(result)
            
            assert result_data["status"] == "success"
            assert len(result_data["data"]["sales_items"]) == 2
            assert result_data["data"]["total_results"] == 2
            assert result_data["data"]["insights"]["total_items_sold"] == 8  # 5 + 3
            assert result_data["data"]["insights"]["avg_sale_price"] == 849.99  # (899.99 + 799.99) / 2
            
            # Verify API call - just check that it was called with correct endpoint
            mock_rest_client.get.assert_called_once()
            call_args = mock_rest_client.get.call_args
            assert call_args[0][0] == "/buy/marketplace_insights/v1_beta/item_sales/search"
            assert call_args[1]["params"]["limit"] == 50
            assert call_args[1]["params"]["offset"] == 0
            assert call_args[1]["params"]["q"] == "iPhone 15"
            assert "lastSoldDate:" in call_args[1]["params"]["filter"]
            assert call_args[1]["scope"] == "https://api.ebay.com/oauth/api_scope/buy.marketplace.insights"
    
    @pytest.mark.asyncio
    async def test_search_item_sales_with_filters(self, mock_context, mock_rest_client, mock_sales_response):
        """Test search with price and condition filters."""
        with patch('tools.marketplace_insights_api._has_marketplace_insights_access', return_value=True), \
             patch('tools.marketplace_insights_api.EbayRestClient') as mock_client_class:
            
            mock_client_class.return_value = mock_rest_client
            mock_rest_client.get.return_value = mock_sales_response
            
            result = await search_item_sales.fn(
                ctx=mock_context,
                query="iPhone",
                price_min=500.0,
                price_max=1000.0,
                conditions="NEW,CERTIFIED_REFURBISHED",
                category_ids="9355"
            )
            
            result_data = json.loads(result)
            assert result_data["status"] == "success"
            
            # Check that filters were applied
            call_args = mock_rest_client.get.call_args
            params = call_args[1]["params"]
            
            assert "q" in params
            assert "category_ids" in params
            assert "filter" in params
            
            filter_str = params["filter"]
            assert "price:[500.0..1000.0]" in filter_str
            assert "conditions:{NEW,CERTIFIED_REFURBISHED}" in filter_str
            assert "lastSoldDate:" in filter_str
    
    @pytest.mark.asyncio
    async def test_search_item_sales_validation_error(self, mock_context):
        """Test search with invalid input."""
        with patch('tools.marketplace_insights_api._has_marketplace_insights_access', return_value=True):
            # No search criteria provided
            result = await search_item_sales.fn(
                ctx=mock_context
            )
            
            result_data = json.loads(result)
            assert result_data["status"] == "error"
            assert result_data["error_code"] == "VALIDATION_ERROR"
    
    @pytest.mark.asyncio
    async def test_search_item_sales_authorization_error(self, mock_context, mock_rest_client):
        """Test search with authorization error."""
        with patch('tools.marketplace_insights_api._has_marketplace_insights_access', return_value=True), \
             patch('tools.marketplace_insights_api.EbayRestClient') as mock_client_class:
            
            mock_client_class.return_value = mock_rest_client
            mock_rest_client.get.side_effect = AuthorizationError(
                "Marketplace Insights API requires special access"
            )
            
            result = await search_item_sales.fn(
                ctx=mock_context,
                query="iPhone"
            )
            
            result_data = json.loads(result)
            assert result_data["status"] == "error"
            assert result_data["error_code"] == "PERMISSION_DENIED"
    
    @pytest.mark.asyncio
    async def test_search_item_sales_api_error(self, mock_context, mock_rest_client):
        """Test search with API error."""
        with patch('tools.marketplace_insights_api._has_marketplace_insights_access', return_value=True), \
             patch('tools.marketplace_insights_api.EbayRestClient') as mock_client_class:
            
            mock_client_class.return_value = mock_rest_client
            mock_rest_client.get.side_effect = EbayApiError(
                status_code=500,
                error_response={"message": "Internal server error"}
            )
            
            result = await search_item_sales.fn(
                ctx=mock_context,
                query="iPhone"
            )
            
            result_data = json.loads(result)
            assert result_data["status"] == "error"
            assert result_data["error_code"] == "EXTERNAL_API_ERROR"


class TestCategorySalesInsights:
    """Test the get_category_sales_insights tool."""
    
    @pytest.mark.asyncio
    async def test_get_category_sales_insights(self, mock_context):
        """Test that category insights delegates to search."""
        with patch('tools.marketplace_insights_api.search_item_sales.fn') as mock_search:
            mock_search.return_value = '{"status": "success"}'
            
            result = await get_category_sales_insights.fn(
                ctx=mock_context,
                category_id="9355",
                last_sold_days=30,
                limit=100
            )
            
            # Verify it calls search_item_sales with correct params
            mock_search.assert_called_once_with(
                ctx=mock_context,
                category_ids="9355",
                last_sold_days=30,
                limit=100
            )
            
            assert result == '{"status": "success"}'


class TestProductSalesHistory:
    """Test the get_product_sales_history tool."""
    
    @pytest.mark.asyncio
    async def test_get_product_sales_history_with_epid(self, mock_context):
        """Test product history with ePID."""
        with patch('tools.marketplace_insights_api.search_item_sales.fn') as mock_search:
            mock_search.return_value = '{"status": "success"}'
            
            result = await get_product_sales_history.fn(
                ctx=mock_context,
                epid="123456789",
                last_sold_days=90
            )
            
            mock_search.assert_called_once_with(
                ctx=mock_context,
                epid="123456789",
                gtin=None,
                last_sold_days=90,
                limit=200
            )
    
    @pytest.mark.asyncio
    async def test_get_product_sales_history_with_gtin(self, mock_context):
        """Test product history with GTIN."""
        with patch('tools.marketplace_insights_api.search_item_sales.fn') as mock_search:
            mock_search.return_value = '{"status": "success"}'
            
            result = await get_product_sales_history.fn(
                ctx=mock_context,
                gtin="123456789012",
                last_sold_days=60
            )
            
            mock_search.assert_called_once_with(
                ctx=mock_context,
                epid=None,
                gtin="123456789012",
                last_sold_days=60,
                limit=200
            )
    
    @pytest.mark.asyncio
    async def test_get_product_sales_history_no_identifiers(self, mock_context):
        """Test product history without identifiers."""
        result = await get_product_sales_history.fn(
            ctx=mock_context
        )
        
        result_data = json.loads(result)
        assert result_data["status"] == "error"
        assert result_data["error_code"] == "VALIDATION_ERROR"
        assert "Either epid or gtin must be provided" in result_data["error_message"]


class TestTrendingItems:
    """Test the get_trending_items tool."""
    
    @pytest.mark.asyncio
    async def test_get_trending_items(self, mock_context):
        """Test trending items search."""
        with patch('tools.marketplace_insights_api.search_item_sales.fn') as mock_search:
            mock_search.return_value = '{"status": "success"}'
            
            result = await get_trending_items.fn(
                ctx=mock_context,
                category_ids="9355",
                limit=20
            )
            
            # Verify it calls search_item_sales with 7-day window
            mock_search.assert_called_once_with(
                ctx=mock_context,
                category_ids="9355",
                last_sold_days=7,
                limit=20,
                offset=0
            )
            
            assert result == '{"status": "success"}'
    
    @pytest.mark.asyncio
    async def test_get_trending_items_no_category(self, mock_context):
        """Test trending items without category filter."""
        with patch('tools.marketplace_insights_api.search_item_sales.fn') as mock_search:
            mock_search.return_value = '{"status": "success"}'
            
            result = await get_trending_items.fn(
                ctx=mock_context,
                limit=50
            )
            
            mock_search.assert_called_once_with(
                ctx=mock_context,
                category_ids=None,
                last_sold_days=7,
                limit=50,
                offset=0
            )