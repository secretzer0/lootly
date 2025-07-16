"""Integration tests for Taxonomy API tools."""
import pytest
from unittest.mock import patch, AsyncMock
import json
from fastmcp import Context

from tools.taxonomy_api import (
    get_default_category_tree_id,
    get_category_tree,
    get_category_suggestions,
    get_item_aspects_for_category,
    get_compatibility_properties
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
def mock_category_tree_response():
    """Mock category tree response."""
    return {
        "categoryTreeId": "0",
        "categoryTreeVersion": "119",
        "rootCategoryNode": {
            "categoryId": "20081",
            "categoryName": "Root",
            "childCategoryTreeNodes": [
                {
                    "categoryId": "550",
                    "categoryName": "Art",
                    "categorySubtreeNodeHref": "https://api.ebay.com/commerce/taxonomy/v1/category_tree/0/get_category_subtree?category_id=550",
                    "leafCategoryTreeNode": False
                },
                {
                    "categoryId": "2984",
                    "categoryName": "Baby",
                    "categorySubtreeNodeHref": "https://api.ebay.com/commerce/taxonomy/v1/category_tree/0/get_category_subtree?category_id=2984",
                    "leafCategoryTreeNode": False
                }
            ]
        }
    }


class TestGetDefaultCategoryTreeIdIntegration:
    """Integration tests for get_default_category_tree_id tool."""
    
    @pytest.mark.asyncio
    async def test_get_default_category_tree_id_success(self, mock_context, mock_rest_client):
        """Test successful category tree ID retrieval."""
        mock_response = {
            "categoryTreeId": "0",
            "categoryTreeVersion": "119"
        }
        
        with patch('tools.taxonomy_api.EbayRestClient') as mock_client_class:
            mock_client_class.return_value = mock_rest_client
            mock_rest_client.get.return_value = mock_response
            
            result = await get_default_category_tree_id.fn(
                ctx=mock_context,
                marketplace_id="EBAY_US"
            )
            
            result_data = json.loads(result)
            assert result_data["status"] == "success"
            assert result_data["data"]["category_tree_id"] == "0"
            assert result_data["data"]["category_tree_version"] == "119"
            assert result_data["data"]["marketplace_id"] == "EBAY_US"
            assert result_data["data"]["data_source"] == "live_api"
    
    @pytest.mark.asyncio
    async def test_get_default_category_tree_id_no_credentials(self, mock_context):
        """Test category tree ID without credentials."""
        with patch('tools.taxonomy_api.mcp') as mock_mcp:
            mock_mcp.config.app_id = ""
            mock_mcp.config.cert_id = ""
            
            result = await get_default_category_tree_id.fn(
                ctx=mock_context,
                marketplace_id="EBAY_US"
            )
            
            result_data = json.loads(result)
            assert result_data["status"] == "success"
            assert result_data["data"]["data_source"] == "static_fallback"
            assert result_data["data"]["category_tree_id"] == "0"
    
    @pytest.mark.asyncio
    async def test_get_default_category_tree_id_api_error(self, mock_context, mock_rest_client):
        """Test API error handling."""
        with patch('tools.taxonomy_api.EbayRestClient') as mock_client_class:
            mock_client_class.return_value = mock_rest_client
            mock_rest_client.get.side_effect = EbayApiError(
                status_code=400,
                error_response={"message": "Invalid marketplace"}
            )
            
            result = await get_default_category_tree_id.fn(
                ctx=mock_context,
                marketplace_id="INVALID"
            )
            
            result_data = json.loads(result)
            assert result_data["status"] == "error"
            assert result_data["error_code"] == "EXTERNAL_API_ERROR"


class TestGetCategoryTreeIntegration:
    """Integration tests for get_category_tree tool."""
    
    @pytest.mark.asyncio
    async def test_get_category_tree_success(self, mock_context, mock_rest_client, mock_category_tree_response):
        """Test successful category tree retrieval."""
        with patch('tools.taxonomy_api.EbayRestClient') as mock_client_class:
            mock_client_class.return_value = mock_rest_client
            mock_rest_client.get.return_value = mock_category_tree_response
            
            result = await get_category_tree.fn(
                ctx=mock_context,
                category_tree_id="0",
                category_id="20081"
            )
            
            result_data = json.loads(result)
            assert result_data["status"] == "success"
            assert result_data["data"]["category_tree_id"] == "0"
            assert result_data["data"]["category_tree_version"] == "119"
            assert len(result_data["data"]["categories"]) == 3  # Root + 2 children
    
    @pytest.mark.asyncio
    async def test_get_category_tree_no_credentials(self, mock_context):
        """Test category tree without credentials."""
        with patch('tools.taxonomy_api.mcp') as mock_mcp:
            mock_mcp.config.app_id = ""
            mock_mcp.config.cert_id = ""
            
            result = await get_category_tree.fn(
                ctx=mock_context,
                category_tree_id="0"
            )
            
            result_data = json.loads(result)
            assert result_data["status"] == "success"
            assert result_data["data"]["data_source"] == "static_fallback"
    
    @pytest.mark.asyncio
    async def test_get_category_tree_not_found(self, mock_context, mock_rest_client):
        """Test category tree not found error."""
        with patch('tools.taxonomy_api.EbayRestClient') as mock_client_class:
            mock_client_class.return_value = mock_rest_client
            mock_rest_client.get.side_effect = EbayApiError(
                status_code=404,
                error_response={"message": "Category tree not found"}
            )
            
            result = await get_category_tree.fn(
                ctx=mock_context,
                category_tree_id="999"
            )
            
            result_data = json.loads(result)
            assert result_data["status"] == "error"
            assert result_data["error_code"] == "RESOURCE_NOT_FOUND"
    
    @pytest.mark.asyncio
    async def test_get_category_tree_validation_error(self, mock_context):
        """Test validation error handling."""
        result = await get_category_tree.fn(
            ctx=mock_context,
            category_tree_id=""  # Empty category tree ID
        )
        
        result_data = json.loads(result)
        assert result_data["status"] == "error"
        assert result_data["error_code"] == "VALIDATION_ERROR"


class TestGetCategorySuggestionsIntegration:
    """Integration tests for get_category_suggestions tool."""
    
    @pytest.mark.asyncio
    async def test_get_category_suggestions_success(self, mock_context, mock_rest_client):
        """Test successful category suggestions retrieval."""
        mock_response = {
            "categorySuggestions": [
                {
                    "category": {
                        "categoryId": "9355",
                        "categoryName": "Cell Phones & Smartphones"
                    },
                    "categoryTreeNodeAncestors": [
                        {
                            "categoryId": "58058",
                            "categoryName": "Cell Phones & Accessories"
                        }
                    ],
                    "categoryTreeNodeLevel": 2,
                    "relevancy": "HIGH"
                }
            ]
        }
        
        with patch('tools.taxonomy_api.EbayRestClient') as mock_client_class:
            mock_client_class.return_value = mock_rest_client
            mock_rest_client.get.return_value = mock_response
            
            result = await get_category_suggestions.fn(
                ctx=mock_context,
                category_tree_id="0",
                query="iPhone 15"
            )
            
            result_data = json.loads(result)
            assert result_data["status"] == "success"
            assert len(result_data["data"]["suggestions"]) == 1
            assert result_data["data"]["suggestions"][0]["category_id"] == "9355"
    
    @pytest.mark.asyncio
    async def test_get_category_suggestions_no_credentials(self, mock_context):
        """Test category suggestions without credentials."""
        with patch('tools.taxonomy_api.mcp') as mock_mcp:
            mock_mcp.config.app_id = ""
            mock_mcp.config.cert_id = ""
            
            result = await get_category_suggestions.fn(
                ctx=mock_context,
                category_tree_id="0",
                query="laptop"
            )
            
            result_data = json.loads(result)
            assert result_data["status"] == "success"
            assert result_data["data"]["data_source"] == "static_fallback"
    
    @pytest.mark.asyncio
    async def test_get_category_suggestions_empty_query(self, mock_context):
        """Test category suggestions with empty query."""
        result = await get_category_suggestions.fn(
            ctx=mock_context,
            category_tree_id="0",
            query=""
        )
        
        result_data = json.loads(result)
        assert result_data["status"] == "error"
        assert result_data["error_code"] == "VALIDATION_ERROR"
    
    @pytest.mark.asyncio
    async def test_get_category_suggestions_validation_error(self, mock_context):
        """Test validation error handling."""
        result = await get_category_suggestions.fn(
            ctx=mock_context,
            category_tree_id="",  # Empty category tree ID
            query="laptop"
        )
        
        result_data = json.loads(result)
        assert result_data["status"] == "error"
        assert result_data["error_code"] == "VALIDATION_ERROR"


class TestGetItemAspectsForCategoryIntegration:
    """Integration tests for get_item_aspects_for_category tool."""
    
    @pytest.mark.asyncio
    async def test_get_item_aspects_for_category_success(self, mock_context, mock_rest_client):
        """Test successful item aspects retrieval."""
        mock_response = {
            "categoryTreeId": "0",
            "categoryId": "9355",
            "aspects": [
                {
                    "localizedAspectName": "Brand",
                    "aspectConstraint": {
                        "aspectDataType": "STRING",
                        "aspectRequired": True,
                        "aspectUsage": "REQUIRED",
                        "expectedRequiredByDate": "2024-12-31T00:00:00Z"
                    },
                    "aspectValues": [
                        {"localizedValue": "Apple"},
                        {"localizedValue": "Samsung"},
                        {"localizedValue": "Google"}
                    ]
                },
                {
                    "localizedAspectName": "Storage Capacity",
                    "aspectConstraint": {
                        "aspectDataType": "STRING",
                        "aspectRequired": False,
                        "aspectUsage": "RECOMMENDED"
                    },
                    "aspectValues": [
                        {"localizedValue": "128 GB"},
                        {"localizedValue": "256 GB"},
                        {"localizedValue": "512 GB"}
                    ]
                }
            ]
        }
        
        with patch('tools.taxonomy_api.EbayRestClient') as mock_client_class:
            mock_client_class.return_value = mock_rest_client
            mock_rest_client.get.return_value = mock_response
            
            result = await get_item_aspects_for_category.fn(
                ctx=mock_context,
                category_tree_id="0",
                category_id="9355"
            )
            
            result_data = json.loads(result)
            assert result_data["status"] == "success"
            assert result_data["data"]["category_id"] == "9355"
            assert len(result_data["data"]["aspects"]) == 2
            assert result_data["data"]["aspects"]["Brand"]["required"] is True
    
    @pytest.mark.asyncio
    async def test_get_item_aspects_for_category_no_credentials(self, mock_context):
        """Test item aspects without credentials."""
        with patch('tools.taxonomy_api.mcp') as mock_mcp:
            mock_mcp.config.app_id = ""
            mock_mcp.config.cert_id = ""
            
            result = await get_item_aspects_for_category.fn(
                ctx=mock_context,
                category_tree_id="0",
                category_id="9355"
            )
            
            result_data = json.loads(result)
            assert result_data["status"] == "success"
            assert result_data["data"]["data_source"] == "static_fallback"
    
    @pytest.mark.asyncio
    async def test_get_item_aspects_for_category_validation_error(self, mock_context):
        """Test validation error handling."""
        result = await get_item_aspects_for_category.fn(
            ctx=mock_context,
            category_tree_id="0",
            category_id=""  # Empty category ID
        )
        
        result_data = json.loads(result)
        assert result_data["status"] == "error"
        assert result_data["error_code"] == "VALIDATION_ERROR"


class TestGetCompatibilityPropertiesIntegration:
    """Integration tests for get_compatibility_properties tool."""
    
    @pytest.mark.asyncio
    async def test_get_compatibility_properties_success(self, mock_context, mock_rest_client):
        """Test successful compatibility properties retrieval."""
        mock_response = {
            "categoryTreeId": "100",
            "categoryId": "33559",
            "compatibilityProperties": [
                {
                    "localizedName": "Year",
                    "name": "Year"
                },
                {
                    "localizedName": "Make",
                    "name": "Make"
                },
                {
                    "localizedName": "Model",
                    "name": "Model"
                }
            ]
        }
        
        with patch('tools.taxonomy_api.EbayRestClient') as mock_client_class:
            mock_client_class.return_value = mock_rest_client
            mock_rest_client.get.return_value = mock_response
            
            result = await get_compatibility_properties.fn(
                ctx=mock_context,
                category_tree_id="100",
                category_id="33559"
            )
            
            result_data = json.loads(result)
            assert result_data["status"] == "success"
            assert result_data["data"]["category_id"] == "33559"
            assert len(result_data["data"]["compatibility_properties"]) == 3
    
    @pytest.mark.asyncio
    async def test_get_compatibility_properties_no_credentials(self, mock_context):
        """Test compatibility properties without credentials."""
        with patch('tools.taxonomy_api.mcp') as mock_mcp:
            mock_mcp.config.app_id = ""
            mock_mcp.config.cert_id = ""
            
            result = await get_compatibility_properties.fn(
                ctx=mock_context,
                category_tree_id="100",
                category_id="33559"
            )
            
            result_data = json.loads(result)
            assert result_data["status"] == "success"
            assert result_data["data"]["data_source"] == "static_fallback"