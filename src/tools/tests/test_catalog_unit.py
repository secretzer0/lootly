"""Unit tests for Catalog API tools."""
import pytest
from unittest.mock import Mock, patch, AsyncMock
import json
from datetime import datetime
from fastmcp import Context

from tools.catalog_api import (
    search_catalog_products,
    get_product_details,
    find_products_by_image,
    get_product_aspects,
    get_product_reviews_summary,
    _convert_catalog_product,
    _convert_product_summary,
    CatalogSearchInput,
    ProductDetailsInput
)
from api.errors import EbayApiError


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
    with patch('tools.catalog_api.mcp') as mock_mcp:
        mock_mcp.config.app_id = "test_app_id"
        mock_mcp.config.cert_id = "test_cert_id"
        mock_mcp.config.sandbox_mode = True
        mock_mcp.config.rate_limit_per_day = 5000
        mock_mcp.logger = Mock()
        yield mock_mcp


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


class TestInputValidation:
    """Test input validation models."""
    
    def test_catalog_search_input_valid(self):
        """Test valid catalog search input."""
        input_data = CatalogSearchInput(
            query="iPhone 15",
            limit=50,
            offset=0
        )
        
        assert input_data.query == "iPhone 15"
        assert input_data.limit == 50
        assert input_data.offset == 0
        assert input_data.gtin is None
        assert input_data.brand is None
        assert input_data.mpn is None
        assert input_data.category_ids is None
    
    def test_catalog_search_input_validation_error(self):
        """Test validation error when no criteria provided."""
        with pytest.raises(ValueError, match="At least one search criteria required"):
            CatalogSearchInput(
                query=None,
                gtin=None,
                brand=None,
                mpn=None,
                category_ids=None,
                limit=50,
                offset=0
            )
    
    def test_catalog_search_input_limit_validation(self):
        """Test limit validation."""
        with pytest.raises(ValueError):
            CatalogSearchInput(
                query="iPhone 15",
                limit=300  # Exceeds max of 200
            )
    
    def test_product_details_input_valid(self):
        """Test valid product details input."""
        input_data = ProductDetailsInput(epid="12345678901")
        
        assert input_data.epid == "12345678901"
    
    def test_product_details_input_validation_error(self):
        """Test validation error for empty epid."""
        with pytest.raises(ValueError):
            ProductDetailsInput(epid="   ")


class TestDataConversion:
    """Test data conversion functions."""
    
    def test_convert_product_summary_complete(self):
        """Test conversion with complete product summary."""
        summary = {
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
        
        result = _convert_product_summary(summary)
        
        assert result["epid"] == "12345678901"
        assert result["title"] == "Apple iPhone 15 Pro"
        assert result["brand"] == "Apple"
        assert result["gtin"] == "194253434894"
        assert result["image_url"] == "https://example.com/iphone15pro.jpg"
        assert result["category_id"] == "9355"
        assert result["category_name"] == "Cell Phones & Smartphones"
        assert result["marketplace_ids"] == ["EBAY_US"]
    
    def test_convert_product_summary_minimal(self):
        """Test conversion with minimal product summary."""
        summary = {
            "epid": "12345678901",
            "title": "Apple iPhone 15 Pro"
        }
        
        result = _convert_product_summary(summary)
        
        assert result["epid"] == "12345678901"
        assert result["title"] == "Apple iPhone 15 Pro"
        assert result["brand"] is None
        assert result["gtin"] is None
        assert result["image_url"] is None
        assert result["category_id"] is None
        assert result["category_name"] is None
        assert result["marketplace_ids"] == []
    
    def test_convert_catalog_product_complete(self):
        """Test conversion with complete catalog product."""
        product = {
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
                    "name": "Storage Capacity",
                    "values": ["128GB", "256GB", "512GB"]
                }
            ],
            "productWebUrl": "https://www.ebay.com/itm/12345678901",
            "marketplaceIds": ["EBAY_US"]
        }
        
        result = _convert_catalog_product(product)
        
        assert result["epid"] == "12345678901"
        assert result["title"] == "Apple iPhone 15 Pro"
        assert result["brand"] == "Apple"
        assert result["mpn"] == "A2848"
        assert result["gtin"] == "194253434894"
        assert result["description"] == "Latest iPhone with advanced camera system"
        assert result["category_id"] == "9355"
        assert result["category_name"] == "Cell Phones & Smartphones"
        assert len(result["images"]) == 2
        assert result["primary_image"] == "https://example.com/iphone15pro.jpg"
        assert result["aspects"]["Brand"] == "Apple"
        assert result["aspects"]["Storage Capacity"] == ["128GB", "256GB", "512GB"]
        assert result["product_web_url"] == "https://www.ebay.com/itm/12345678901"
        assert result["marketplace_ids"] == ["EBAY_US"]


class TestSearchCatalogProducts:
    """Test the search_catalog_products tool."""
    
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


class TestGetProductDetails:
    """Test the get_product_details tool."""
    
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
            assert result_data["data"]["epid"] == "12345678901"
            assert result_data["data"]["title"] == "Apple iPhone 15 Pro"
    
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
                epid="nonexistent"
            )
            
            result_data = json.loads(result)
            assert result_data["status"] == "error"
            assert result_data["error_code"] == "RESOURCE_NOT_FOUND"
    
    @pytest.mark.asyncio
    async def test_get_product_details_validation_error(self, mock_context):
        """Test validation error handling."""
        result = await get_product_details.fn(
            ctx=mock_context,
            epid="   "  # Whitespace epid
        )
        
        result_data = json.loads(result)
        assert result_data["status"] == "error"
        assert result_data["error_code"] == "VALIDATION_ERROR"


class TestFindProductsByImage:
    """Test the find_products_by_image tool."""
    
    @pytest.mark.asyncio
    async def test_find_products_by_image_success(self, mock_context, mock_rest_client, mock_catalog_search_response):
        """Test successful image search."""
        with patch('tools.catalog_api.EbayRestClient') as mock_client_class:
            mock_client_class.return_value = mock_rest_client
            mock_rest_client.get.return_value = mock_catalog_search_response
            
            result = await find_products_by_image.fn(
                ctx=mock_context,
                image_url="https://example.com/product.jpg",
                limit=20
            )
            
            result_data = json.loads(result)
            assert result_data["status"] == "success"
            assert len(result_data["data"]["products"]) == 1
            assert result_data["data"]["image_url"] == "https://example.com/product.jpg"
            assert result_data["data"]["data_source"] == "live_api"
            
            # Verify API call
            mock_rest_client.get.assert_called_once_with(
                "/commerce/catalog/v1/product_summary/search",
                params={"image": "https://example.com/product.jpg", "limit": 20},
                scope="https://api.ebay.com/oauth/api_scope/commerce.catalog.readonly"
            )
    
    @pytest.mark.asyncio
    async def test_find_products_by_image_no_credentials(self, mock_context):
        """Test image search without credentials."""
        with patch('tools.catalog_api.mcp') as mock_mcp:
            mock_mcp.config.app_id = ""
            mock_mcp.config.cert_id = ""
            
            result = await find_products_by_image.fn(
                ctx=mock_context,
                image_url="https://example.com/product.jpg"
            )
            
            result_data = json.loads(result)
            assert result_data["status"] == "success"
            assert result_data["data"]["data_source"] == "static_fallback"
            assert result_data["data"]["products"] == []
            assert "Image search requires eBay API credentials" in result_data["data"]["note"]
    
    @pytest.mark.asyncio
    async def test_find_products_by_image_invalid_url(self, mock_context):
        """Test invalid image URL."""
        result = await find_products_by_image.fn(
            ctx=mock_context,
            image_url="invalid-url"
        )
        
        result_data = json.loads(result)
        assert result_data["status"] == "error"
        assert result_data["error_code"] == "VALIDATION_ERROR"


class TestGetProductAspects:
    """Test the get_product_aspects tool."""
    
    @pytest.mark.asyncio
    async def test_get_product_aspects_success(self, mock_context, mock_rest_client, mock_product_details_response):
        """Test successful product aspects retrieval."""
        with patch('tools.catalog_api.EbayRestClient') as mock_client_class:
            mock_client_class.return_value = mock_rest_client
            mock_rest_client.get.return_value = mock_product_details_response
            
            result = await get_product_aspects.fn(
                ctx=mock_context,
                epid="12345678901"
            )
            
            result_data = json.loads(result)
            assert result_data["status"] == "success"
            assert result_data["data"]["epid"] == "12345678901"
            assert len(result_data["data"]["aspects"]) == 3
            assert result_data["data"]["aspects"]["Brand"] == "Apple"
            assert result_data["data"]["aspects"]["Model"] == "iPhone 15 Pro"
            assert result_data["data"]["total_aspects"] == 3
    
    @pytest.mark.asyncio
    async def test_get_product_aspects_error(self, mock_context):
        """Test error handling when product details fails."""
        with patch('tools.catalog_api.get_product_details.fn') as mock_get_details:
            mock_get_details.return_value = json.dumps({
                "status": "error",
                "error_code": "RESOURCE_NOT_FOUND",
                "message": "Product not found"
            })
            
            result = await get_product_aspects.fn(
                ctx=mock_context,
                epid="nonexistent"
            )
            
            result_data = json.loads(result)
            assert result_data["status"] == "error"
            assert result_data["error_code"] == "RESOURCE_NOT_FOUND"


class TestGetProductReviewsSummary:
    """Test the get_product_reviews_summary tool."""
    
    @pytest.mark.asyncio
    async def test_get_product_reviews_summary_success(self, mock_context, mock_rest_client, mock_reviews_response):
        """Test successful review summary retrieval."""
        with patch('tools.catalog_api.EbayRestClient') as mock_client_class:
            mock_client_class.return_value = mock_rest_client
            mock_rest_client.get.return_value = mock_reviews_response
            
            result = await get_product_reviews_summary.fn(
                ctx=mock_context,
                epid="12345678901"
            )
            
            result_data = json.loads(result)
            assert result_data["status"] == "success"
            assert result_data["data"]["epid"] == "12345678901"
            assert result_data["data"]["reviews"]["average_rating"] == 4.5
            assert result_data["data"]["reviews"]["total_reviews"] == 1250
            assert result_data["data"]["data_source"] == "live_api"
            
            # Verify API call
            mock_rest_client.get.assert_called_once_with(
                "/commerce/catalog/v1/product/12345678901/get_product_reviews",
                scope="https://api.ebay.com/oauth/api_scope/commerce.catalog.readonly"
            )
    
    @pytest.mark.asyncio
    async def test_get_product_reviews_summary_no_credentials(self, mock_context):
        """Test review summary without credentials."""
        with patch('tools.catalog_api.mcp') as mock_mcp:
            mock_mcp.config.app_id = ""
            mock_mcp.config.cert_id = ""
            
            result = await get_product_reviews_summary.fn(
                ctx=mock_context,
                epid="12345678901"
            )
            
            result_data = json.loads(result)
            assert result_data["status"] == "success"
            assert result_data["data"]["data_source"] == "static_fallback"
            assert result_data["data"]["reviews"]["average_rating"] == 0
            assert result_data["data"]["reviews"]["total_reviews"] == 0
            assert "Review data requires eBay API credentials" in result_data["data"]["note"]
    
    @pytest.mark.asyncio
    async def test_get_product_reviews_summary_not_found(self, mock_context, mock_rest_client):
        """Test review summary not found error."""
        with patch('tools.catalog_api.EbayRestClient') as mock_client_class:
            mock_client_class.return_value = mock_rest_client
            mock_rest_client.get.side_effect = EbayApiError(
                status_code=404,
                error_response={"message": "No reviews found"}
            )
            
            result = await get_product_reviews_summary.fn(
                ctx=mock_context,
                epid="12345678901"
            )
            
            result_data = json.loads(result)
            assert result_data["status"] == "error"
            assert result_data["error_code"] == "RESOURCE_NOT_FOUND"