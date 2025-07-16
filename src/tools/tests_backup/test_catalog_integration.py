"""Integration tests for Catalog API tools."""
import pytest
from unittest.mock import patch, AsyncMock
import json
from fastmcp import Context

from tools.catalog_api import (
    search_catalog_products,
    get_product_details,
    find_products_by_image,
    get_product_aspects,
    get_product_reviews_summary
)
from api.errors import EbayApiError


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
def mock_catalog_search_response():
    """Mock catalog search response."""
    return {
        "productSummaries": [
            {
                "epid": "12345678901",
                "title": "Apple iPhone 15 Pro",
                "brand": "Apple",
                "productIdentifiers": [
                    {
                        "type": "GTIN",
                        "value": "194253434894"
                    }
                ],
                "image": {
                    "imageUrl": "https://example.com/iphone15pro.jpg"
                },
                "categoryId": "9355",
                "categoryName": "Cell Phones & Smartphones",
                "marketplaceIds": ["EBAY_US"]
            }
        ],
        "total": 1
    }


@pytest.fixture
def mock_product_details_response():
    """Mock product details response."""
    return {
        "epid": "12345678901",
        "title": "Apple iPhone 15 Pro",
        "brand": "Apple",
        "description": "Latest iPhone with advanced camera system",
        "productIdentifiers": [
            {
                "type": "GTIN",
                "value": "194253434894"
            },
            {
                "type": "MPN",
                "value": "A2848"
            }
        ],
        "image": {
            "imageUrls": [
                "https://example.com/iphone15pro.jpg",
                "https://example.com/iphone15pro_2.jpg"
            ]
        },
        "categoryId": "9355",
        "categoryName": "Cell Phones & Smartphones",
        "aspects": [
            {
                "name": "Brand",
                "values": ["Apple"]
            },
            {
                "name": "Model",
                "values": ["iPhone 15 Pro"]
            },
            {
                "name": "Storage Capacity",
                "values": ["128GB", "256GB", "512GB"]
            }
        ],
        "productWebUrl": "https://www.ebay.com/itm/12345678901",
        "marketplaceIds": ["EBAY_US"]
    }


@pytest.fixture
def mock_reviews_response():
    """Mock product reviews response."""
    return {
        "reviews": {
            "averageRating": 4.5,
            "totalReviews": 1250
        },
        "ratingDistribution": {
            "5": 800,
            "4": 300,
            "3": 100,
            "2": 30,
            "1": 20
        }
    }


class TestSearchCatalogProductsIntegration:
    """Integration tests for search_catalog_products tool."""
    
    @pytest.mark.asyncio
    async def test_search_catalog_products_success(self, mock_context, mock_rest_client, mock_catalog_search_response):
        """Test successful catalog search."""
        with patch('tools.catalog_api.EbayRestClient') as mock_client_class:
            mock_client_class.return_value = mock_rest_client
            mock_rest_client.get.return_value = mock_catalog_search_response
            
            result = await search_catalog_products.fn(
                ctx=mock_context,
                query="iPhone 15",
                limit=50,
                offset=0
            )
            
            result_data = json.loads(result)
            assert result_data["status"] == "success"
            assert len(result_data["data"]["products"]) == 1
            assert result_data["data"]["products"][0]["epid"] == "12345678901"
            assert result_data["data"]["total_results"] == 1
            assert result_data["data"]["data_source"] == "live_api"
            
            # Verify API call
            mock_rest_client.get.assert_called_once_with(
                "/commerce/catalog/v1/product_summary/search",
                params={"q": "iPhone 15", "limit": 50, "offset": 0},
                scope="https://api.ebay.com/oauth/api_scope/commerce.catalog.readonly"
            )
    
    @pytest.mark.asyncio
    async def test_search_catalog_products_no_credentials(self, mock_context):
        """Test search without credentials returns static data."""
        with patch('tools.catalog_api.mcp') as mock_mcp:
            mock_mcp.config.app_id = ""
            mock_mcp.config.cert_id = ""
            
            result = await search_catalog_products.fn(
                ctx=mock_context,
                query="iPhone 15"
            )
            
            result_data = json.loads(result)
            assert result_data["status"] == "success"
            assert result_data["data"]["data_source"] == "static_catalog"
            assert len(result_data["data"]["products"]) == 1
            assert "Live catalog data requires eBay API credentials" in result_data["data"]["note"]
    
    @pytest.mark.asyncio
    async def test_search_catalog_products_by_gtin(self, mock_context, mock_rest_client, mock_catalog_search_response):
        """Test search by GTIN."""
        with patch('tools.catalog_api.EbayRestClient') as mock_client_class:
            mock_client_class.return_value = mock_rest_client
            mock_rest_client.get.return_value = mock_catalog_search_response
            
            result = await search_catalog_products.fn(
                ctx=mock_context,
                gtin="194253434894"
            )
            
            result_data = json.loads(result)
            assert result_data["status"] == "success"
            
            # Verify API call with GTIN
            mock_rest_client.get.assert_called_once_with(
                "/commerce/catalog/v1/product_summary/search",
                params={"gtin": "194253434894", "limit": 50, "offset": 0},
                scope="https://api.ebay.com/oauth/api_scope/commerce.catalog.readonly"
            )
    
    @pytest.mark.asyncio
    async def test_search_catalog_products_validation_error(self, mock_context):
        """Test validation error handling."""
        result = await search_catalog_products.fn(
            ctx=mock_context,
            query=None,  # No query
            gtin=None,   # No GTIN
            brand=None,  # No brand
            mpn=None,    # No MPN
            category_ids=None  # No category IDs
        )
        
        result_data = json.loads(result)
        assert result_data["status"] == "error"
        assert result_data["error_code"] == "VALIDATION_ERROR"
    
    @pytest.mark.asyncio
    async def test_search_catalog_products_api_error(self, mock_context, mock_rest_client):
        """Test API error handling."""
        with patch('tools.catalog_api.EbayRestClient') as mock_client_class:
            mock_client_class.return_value = mock_rest_client
            mock_rest_client.get.side_effect = EbayApiError(
                status_code=400,
                error_response={"message": "Invalid query"}
            )
            
            result = await search_catalog_products.fn(
                ctx=mock_context,
                query="invalid query"
            )
            
            result_data = json.loads(result)
            assert result_data["status"] == "error"
            assert result_data["error_code"] == "EXTERNAL_API_ERROR"


class TestGetProductDetailsIntegration:
    """Integration tests for get_product_details tool."""
    
    @pytest.mark.asyncio
    async def test_get_product_details_success(self, mock_context, mock_rest_client, mock_product_details_response):
        """Test successful product details retrieval."""
        with patch('tools.catalog_api.EbayRestClient') as mock_client_class:
            mock_client_class.return_value = mock_rest_client
            mock_rest_client.get.return_value = mock_product_details_response
            
            result = await get_product_details.fn(
                ctx=mock_context,
                epid="12345678901"
            )
            
            result_data = json.loads(result)
            assert result_data["status"] == "success"
            assert result_data["data"]["epid"] == "12345678901"
            assert result_data["data"]["title"] == "Apple iPhone 15 Pro"
            assert result_data["data"]["brand"] == "Apple"
            assert result_data["data"]["gtin"] == "194253434894"
            assert result_data["data"]["mpn"] == "A2848"
            assert len(result_data["data"]["images"]) == 2
            
            # Verify API call
            mock_rest_client.get.assert_called_once_with(
                "/commerce/catalog/v1/product/12345678901",
                scope="https://api.ebay.com/oauth/api_scope/commerce.catalog.readonly"
            )
    
    @pytest.mark.asyncio
    async def test_get_product_details_no_credentials(self, mock_context):
        """Test product details without credentials."""
        with patch('tools.catalog_api.mcp') as mock_mcp:
            mock_mcp.config.app_id = ""
            mock_mcp.config.cert_id = ""
            
            result = await get_product_details.fn(
                ctx=mock_context,
                epid="12345678901"
            )
            
            result_data = json.loads(result)
            assert result_data["status"] == "success"
            assert result_data["data"]["data_source"] == "static_catalog"
            assert "Live product details require eBay API credentials" in result_data["data"]["note"]
    
    @pytest.mark.asyncio
    async def test_get_product_details_not_found(self, mock_context, mock_rest_client):
        """Test product not found error."""
        with patch('tools.catalog_api.EbayRestClient') as mock_client_class:
            mock_client_class.return_value = mock_rest_client
            mock_rest_client.get.side_effect = EbayApiError(
                status_code=404,
                error_response={"message": "Product not found"}
            )
            
            result = await get_product_details.fn(
                ctx=mock_context,
                epid="999999999"
            )
            
            result_data = json.loads(result)
            assert result_data["status"] == "error"
            assert result_data["error_code"] == "RESOURCE_NOT_FOUND"
    
    @pytest.mark.asyncio
    async def test_get_product_details_validation_error(self, mock_context):
        """Test validation error handling."""
        result = await get_product_details.fn(
            ctx=mock_context,
            epid=""  # Empty EPID
        )
        
        result_data = json.loads(result)
        assert result_data["status"] == "error"
        assert result_data["error_code"] == "VALIDATION_ERROR"


class TestFindProductsByImageIntegration:
    """Integration tests for find_products_by_image tool."""
    
    @pytest.mark.asyncio
    async def test_find_products_by_image_success(self, mock_context, mock_rest_client, mock_catalog_search_response):
        """Test successful image-based product search."""
        with patch('tools.catalog_api.EbayRestClient') as mock_client_class:
            mock_client_class.return_value = mock_rest_client
            mock_rest_client.get.return_value = mock_catalog_search_response
            
            result = await find_products_by_image.fn(
                ctx=mock_context,
                image_url="https://example.com/test-image.jpg",
                category_ids="9355"
            )
            
            result_data = json.loads(result)
            assert result_data["status"] == "success"
            assert len(result_data["data"]["products"]) == 1
    
    @pytest.mark.asyncio
    async def test_find_products_by_image_no_credentials(self, mock_context):
        """Test image search without credentials."""
        with patch('tools.catalog_api.mcp') as mock_mcp:
            mock_mcp.config.app_id = ""
            mock_mcp.config.cert_id = ""
            
            result = await find_products_by_image.fn(
                ctx=mock_context,
                image_url="https://example.com/test-image.jpg"
            )
            
            result_data = json.loads(result)
            assert result_data["status"] == "success"
            assert result_data["data"]["data_source"] == "static_catalog"
    
    @pytest.mark.asyncio
    async def test_find_products_by_image_validation_error(self, mock_context):
        """Test validation error with invalid image URL."""
        result = await find_products_by_image.fn(
            ctx=mock_context,
            image_url="invalid-url"
        )
        
        result_data = json.loads(result)
        assert result_data["status"] == "error"
        assert result_data["error_code"] == "VALIDATION_ERROR"


class TestGetProductAspectsIntegration:
    """Integration tests for get_product_aspects tool."""
    
    @pytest.mark.asyncio
    async def test_get_product_aspects_success(self, mock_context, mock_rest_client):
        """Test successful aspects retrieval."""
        mock_response = {
            "categoryTreeId": "1",
            "aspects": {
                "Brand": {
                    "aspectConstraint": {
                        "aspectDataType": "STRING",
                        "aspectRequired": True
                    },
                    "expectedInputValues": ["Apple", "Samsung", "Google"]
                },
                "Storage Capacity": {
                    "aspectConstraint": {
                        "aspectDataType": "STRING_ARRAY",
                        "aspectRequired": False
                    },
                    "expectedInputValues": ["128GB", "256GB", "512GB", "1TB"]
                }
            }
        }
        
        with patch('tools.catalog_api.EbayRestClient') as mock_client_class:
            mock_client_class.return_value = mock_rest_client
            mock_rest_client.get.return_value = mock_response
            
            result = await get_product_aspects.fn(
                ctx=mock_context,
                category_id="9355"
            )
            
            result_data = json.loads(result)
            assert result_data["status"] == "success"
            assert "Brand" in result_data["data"]["aspects"]
            assert "Storage Capacity" in result_data["data"]["aspects"]
    
    @pytest.mark.asyncio
    async def test_get_product_aspects_no_credentials(self, mock_context):
        """Test aspects without credentials."""
        with patch('tools.catalog_api.mcp') as mock_mcp:
            mock_mcp.config.app_id = ""
            mock_mcp.config.cert_id = ""
            
            result = await get_product_aspects.fn(
                ctx=mock_context,
                category_id="9355"
            )
            
            result_data = json.loads(result)
            assert result_data["status"] == "success"
            assert result_data["data"]["data_source"] == "static_data"


class TestGetProductReviewsSummaryIntegration:
    """Integration tests for get_product_reviews_summary tool."""
    
    @pytest.mark.asyncio
    async def test_get_product_reviews_success(self, mock_context, mock_rest_client, mock_reviews_response):
        """Test successful reviews retrieval."""
        with patch('tools.catalog_api.EbayRestClient') as mock_client_class:
            mock_client_class.return_value = mock_rest_client
            mock_rest_client.get.return_value = mock_reviews_response
            
            result = await get_product_reviews_summary.fn(
                ctx=mock_context,
                epid="12345678901"
            )
            
            result_data = json.loads(result)
            assert result_data["status"] == "success"
            assert result_data["data"]["reviews"]["averageRating"] == 4.5
            assert result_data["data"]["reviews"]["totalReviews"] == 1250
    
    @pytest.mark.asyncio
    async def test_get_product_reviews_no_credentials(self, mock_context):
        """Test reviews without credentials."""
        with patch('tools.catalog_api.mcp') as mock_mcp:
            mock_mcp.config.app_id = ""
            mock_mcp.config.cert_id = ""
            
            result = await get_product_reviews_summary.fn(
                ctx=mock_context,
                epid="12345678901"
            )
            
            result_data = json.loads(result)
            assert result_data["status"] == "success"
            assert result_data["data"]["data_source"] == "static_data"
    
    @pytest.mark.asyncio
    async def test_get_product_reviews_not_found(self, mock_context, mock_rest_client):
        """Test reviews not found error."""
        with patch('tools.catalog_api.EbayRestClient') as mock_client_class:
            mock_client_class.return_value = mock_rest_client
            mock_rest_client.get.side_effect = EbayApiError(
                status_code=404,
                error_response={"message": "Reviews not found"}
            )
            
            result = await get_product_reviews_summary.fn(
                ctx=mock_context,
                epid="999999999"
            )
            
            result_data = json.loads(result)
            assert result_data["status"] == "error"
            assert result_data["error_code"] == "RESOURCE_NOT_FOUND"