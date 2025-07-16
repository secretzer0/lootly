"""Integration tests for Marketplace Insights API tools."""
import pytest
from unittest.mock import patch, AsyncMock
import json
from datetime import datetime, timedelta
from fastmcp import Context

from tools.marketplace_insights_api import (
    search_item_sales, 
    get_category_sales_insights,
    get_product_sales_history,
    get_trending_items
)
from api.errors import EbayApiError, AuthorizationError


@pytest.fixture
def mock_context():
    """Create a mock FastMCP context."""
    ctx = AsyncMock(spec=Context)
    ctx.info = AsyncMock()
    ctx.error = AsyncMock()
    ctx.debug = AsyncMock()
    ctx.report_progress = AsyncMock()
    return ctx


@pytest.fixture
def mock_rest_client():
    """Create a mock REST client."""
    from unittest.mock import Mock
    client = Mock()
    client.get = AsyncMock()
    client.close = AsyncMock()
    return client


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


class TestSearchItemSalesIntegration:
    """Integration tests for search_item_sales tool."""
    
    @pytest.mark.asyncio
    async def test_search_item_sales_success(self, mock_context, mock_rest_client, mock_sales_response):
        """Test successful item sales search."""
        with patch('tools.marketplace_insights_api.EbayRestClient') as mock_client_class, \
             patch('tools.marketplace_insights_api.mcp') as mock_mcp:
            
            mock_client_class.return_value = mock_rest_client
            mock_rest_client.get.return_value = mock_sales_response
            mock_mcp.config.marketplace_insights_enabled = True
            
            result = await search_item_sales.fn(
                ctx=mock_context,
                query="iPhone 15",
                category_id="9355",
                limit=50
            )
            
            result_data = json.loads(result)
            assert result_data["status"] == "success"
            assert len(result_data["data"]["sales"]) == 2
            assert result_data["data"]["total"] == 2
            assert result_data["data"]["data_source"] == "live_api"
    
    @pytest.mark.asyncio
    async def test_search_item_sales_disabled(self, mock_context):
        """Test when marketplace insights is disabled."""
        with patch('tools.marketplace_insights_api.mcp') as mock_mcp:
            mock_mcp.config.marketplace_insights_enabled = False
            
            result = await search_item_sales.fn(
                ctx=mock_context,
                query="iPhone 15"
            )
            
            result_data = json.loads(result)
            assert result_data["status"] == "error"
            assert result_data["error_code"] == "AUTHORIZATION_ERROR"
    
    @pytest.mark.asyncio
    async def test_search_item_sales_no_credentials(self, mock_context):
        """Test without credentials returns demo data."""
        with patch('tools.marketplace_insights_api.mcp') as mock_mcp:
            mock_mcp.config.app_id = ""
            mock_mcp.config.cert_id = ""
            mock_mcp.config.marketplace_insights_enabled = True
            
            result = await search_item_sales.fn(
                ctx=mock_context,
                query="iPhone 15",
                category_id="9355",
                limit=50
            )
            
            result_data = json.loads(result)
            assert result_data["status"] == "success"
            assert result_data["data"]["data_source"] == "demo_data"
            assert len(result_data["data"]["sales"]) >= 1
    
    @pytest.mark.asyncio
    async def test_search_item_sales_with_filters(self, mock_context, mock_rest_client, mock_sales_response):
        """Test search with price and date filters."""
        with patch('tools.marketplace_insights_api.EbayRestClient') as mock_client_class, \
             patch('tools.marketplace_insights_api.mcp') as mock_mcp:
            
            mock_client_class.return_value = mock_rest_client
            mock_rest_client.get.return_value = mock_sales_response
            mock_mcp.config.marketplace_insights_enabled = True
            
            # Calculate date 30 days ago
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
            
            result = await search_item_sales.fn(
                ctx=mock_context,
                query="iPhone 15",
                category_id="9355",
                price_min=800.0,
                price_max=1200.0,
                sold_date_from=start_date.isoformat(),
                sold_date_to=end_date.isoformat(),
                condition="NEW"
            )
            
            result_data = json.loads(result)
            assert result_data["status"] == "success"
    
    @pytest.mark.asyncio
    async def test_search_item_sales_api_error(self, mock_context, mock_rest_client):
        """Test API error handling."""
        with patch('tools.marketplace_insights_api.EbayRestClient') as mock_client_class, \
             patch('tools.marketplace_insights_api.mcp') as mock_mcp:
            
            mock_client_class.return_value = mock_rest_client
            mock_rest_client.get.side_effect = EbayApiError(
                status_code=403,
                error_response={"message": "Access forbidden"}
            )
            mock_mcp.config.marketplace_insights_enabled = True
            
            result = await search_item_sales.fn(
                ctx=mock_context,
                query="iPhone 15"
            )
            
            result_data = json.loads(result)
            assert result_data["status"] == "error"
            assert result_data["error_code"] == "EXTERNAL_API_ERROR"
    
    @pytest.mark.asyncio
    async def test_search_item_sales_validation_error(self, mock_context):
        """Test validation error handling."""
        with patch('tools.marketplace_insights_api.mcp') as mock_mcp:
            mock_mcp.config.marketplace_insights_enabled = True
            
            result = await search_item_sales.fn(
                ctx=mock_context,
                query="",  # Empty query
                category_id="9355"
            )
            
            result_data = json.loads(result)
            assert result_data["status"] == "error"
            assert result_data["error_code"] == "VALIDATION_ERROR"


class TestGetCategorySalesInsightsIntegration:
    """Integration tests for get_category_sales_insights tool."""
    
    @pytest.mark.asyncio
    async def test_get_category_sales_insights_success(self, mock_context, mock_rest_client):
        """Test successful category insights retrieval."""
        mock_response = {
            "categoryId": "9355",
            "categoryName": "Cell Phones & Smartphones",
            "totalSales": 15420,
            "averagePrice": {"value": "650.25", "currency": "USD"},
            "topSellingItems": [
                {
                    "itemId": "v1|123456789|0",
                    "title": "iPhone 15 Pro",
                    "soldQuantity": 152
                }
            ]
        }
        
        with patch('tools.marketplace_insights_api.EbayRestClient') as mock_client_class, \
             patch('tools.marketplace_insights_api.mcp') as mock_mcp:
            
            mock_client_class.return_value = mock_rest_client
            mock_rest_client.get.return_value = mock_response
            mock_mcp.config.marketplace_insights_enabled = True
            
            result = await get_category_sales_insights.fn(
                ctx=mock_context,
                category_id="9355"
            )
            
            result_data = json.loads(result)
            assert result_data["status"] == "success"
            assert result_data["data"]["category_id"] == "9355"
            assert result_data["data"]["total_sales"] == 15420


class TestGetProductSalesHistoryIntegration:
    """Integration tests for get_product_sales_history tool."""
    
    @pytest.mark.asyncio
    async def test_get_product_sales_history_success(self, mock_context, mock_rest_client):
        """Test successful product sales history retrieval."""
        mock_response = {
            "epid": "12345678901",
            "title": "Apple iPhone 15 Pro",
            "salesHistory": [
                {
                    "date": "2024-01-15",
                    "soldQuantity": 5,
                    "averagePrice": {"value": "899.99", "currency": "USD"}
                }
            ]
        }
        
        with patch('tools.marketplace_insights_api.EbayRestClient') as mock_client_class, \
             patch('tools.marketplace_insights_api.mcp') as mock_mcp:
            
            mock_client_class.return_value = mock_rest_client
            mock_rest_client.get.return_value = mock_response
            mock_mcp.config.marketplace_insights_enabled = True
            
            result = await get_product_sales_history.fn(
                ctx=mock_context,
                epid="12345678901"
            )
            
            result_data = json.loads(result)
            assert result_data["status"] == "success"
            assert result_data["data"]["epid"] == "12345678901"
    
    @pytest.mark.asyncio
    async def test_get_product_sales_history_not_found(self, mock_context, mock_rest_client):
        """Test product not found error."""
        with patch('tools.marketplace_insights_api.EbayRestClient') as mock_client_class, \
             patch('tools.marketplace_insights_api.mcp') as mock_mcp:
            
            mock_client_class.return_value = mock_rest_client
            mock_rest_client.get.side_effect = EbayApiError(
                status_code=404,
                error_response={"message": "Product not found"}
            )
            mock_mcp.config.marketplace_insights_enabled = True
            
            result = await get_product_sales_history.fn(
                ctx=mock_context,
                epid="999999999"
            )
            
            result_data = json.loads(result)
            assert result_data["status"] == "error"
            assert result_data["error_code"] == "RESOURCE_NOT_FOUND"
    
    @pytest.mark.asyncio
    async def test_get_product_sales_history_validation_error(self, mock_context):
        """Test validation error handling."""
        result = await get_product_sales_history.fn(
            ctx=mock_context,
            epid=""  # Empty EPID
        )
        
        result_data = json.loads(result)
        assert result_data["status"] == "error"
        assert result_data["error_code"] == "VALIDATION_ERROR"


class TestGetTrendingItemsIntegration:
    """Integration tests for get_trending_items tool."""
    
    @pytest.mark.asyncio
    async def test_get_trending_items_success(self, mock_context, mock_rest_client, mock_sales_response):
        """Test successful trending items retrieval."""
        with patch('tools.marketplace_insights_api.EbayRestClient') as mock_client_class, \
             patch('tools.marketplace_insights_api.mcp') as mock_mcp:
            
            mock_client_class.return_value = mock_rest_client
            mock_rest_client.get.return_value = mock_sales_response
            mock_mcp.config.marketplace_insights_enabled = True
            
            result = await get_trending_items.fn(
                ctx=mock_context,
                category_id="9355",
                limit=20
            )
            
            result_data = json.loads(result)
            assert result_data["status"] == "success"
            assert len(result_data["data"]["trending_items"]) == 2
    
    @pytest.mark.asyncio
    async def test_get_trending_items_no_credentials(self, mock_context):
        """Test trending items without credentials."""
        with patch('tools.marketplace_insights_api.mcp') as mock_mcp:
            mock_mcp.config.app_id = ""
            mock_mcp.config.cert_id = ""
            mock_mcp.config.marketplace_insights_enabled = True
            
            result = await get_trending_items.fn(
                ctx=mock_context,
                category_id="9355"
            )
            
            result_data = json.loads(result)
            assert result_data["status"] == "success"
            assert result_data["data"]["data_source"] == "demo_data"