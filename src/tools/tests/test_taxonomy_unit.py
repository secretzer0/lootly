"""Unit tests for Taxonomy API tools."""
import pytest
from unittest.mock import Mock, patch, AsyncMock
import json
from datetime import datetime
from fastmcp import Context

from tools.taxonomy_api import (
    get_default_category_tree_id,
    get_category_tree,
    get_category_suggestions,
    get_item_aspects_for_category,
    get_compatibility_properties,
    _convert_category_node,
    _convert_category_subtree
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
    with patch('tools.taxonomy_api.mcp') as mock_mcp:
        mock_mcp.config.app_id = "test_app_id"
        mock_mcp.config.cert_id = "test_cert_id"
        mock_mcp.config.sandbox_mode = True
        mock_mcp.config.rate_limit_per_day = 5000
        mock_mcp.logger = Mock()
        yield mock_mcp


@pytest.fixture
def mock_category_tree_response():
    """Mock category tree response."""
    return {
        "categoryTreeId": "0",
        "categoryTreeVersion": "119",
        "applicableMarketplaceIds": ["EBAY_US"],
        "rootCategoryNode": {
            "categoryId": "20081",
            "categoryName": "Root",
            "categoryTreeNodeLevel": 0,
            "leafCategory": False,
            "childCategoryTreeNodes": [
                {
                    "categoryId": "267",
                    "categoryName": "Books, Movies & Music",
                    "categoryTreeNodeLevel": 1,
                    "leafCategory": False,
                    "childCategoryTreeNodes": [
                        {
                            "categoryId": "377",
                            "categoryName": "Books",
                            "categoryTreeNodeLevel": 2,
                            "leafCategory": True,
                            "childCategoryTreeNodes": []
                        }
                    ]
                },
                {
                    "categoryId": "293",
                    "categoryName": "Consumer Electronics",
                    "categoryTreeNodeLevel": 1,
                    "leafCategory": False,
                    "childCategoryTreeNodes": []
                }
            ]
        }
    }


@pytest.fixture
def mock_category_suggestions_response():
    """Mock category suggestions response."""
    return {
        "categorySuggestions": [
            {
                "category": {
                    "categoryId": "9355",
                    "categoryName": "Cell Phones & Smartphones",
                    "categoryTreeNodeLevel": 3,
                    "categoryTreeNodeAncestors": [
                        {
                            "categoryId": "293",
                            "categoryName": "Consumer Electronics",
                            "categoryTreeNodeLevel": 1
                        },
                        {
                            "categoryId": "15032",
                            "categoryName": "Cell Phones & Accessories",
                            "categoryTreeNodeLevel": 2
                        }
                    ]
                },
                "relevancy": "95.0"
            },
            {
                "category": {
                    "categoryId": "166",
                    "categoryName": "Mobile Phone Accessories",
                    "categoryTreeNodeLevel": 3
                },
                "relevancy": "75.0"
            }
        ]
    }


@pytest.fixture
def mock_item_aspects_response():
    """Mock item aspects response."""
    return {
        "aspects": [
            {
                "localizedAspectName": "Brand",
                "aspectConstraint": "SELECTION_ONLY",
                "aspectDataType": "STRING",
                "aspectEnabledForVariations": False,
                "aspectRequired": True,
                "aspectUsage": "REQUIRED",
                "itemToAspectCardinality": "SINGLE",
                "relevanceIndicator": "REQUIRED",
                "aspectValues": [
                    {
                        "localizedValue": "Apple",
                        "suggestedInputValue": "Apple"
                    },
                    {
                        "localizedValue": "Samsung",
                        "suggestedInputValue": "Samsung"
                    }
                ]
            },
            {
                "localizedAspectName": "Model",
                "aspectConstraint": "OPEN_TEXT",
                "aspectDataType": "STRING",
                "aspectEnabledForVariations": False,
                "aspectRequired": False,
                "aspectUsage": "RECOMMENDED",
                "itemToAspectCardinality": "SINGLE",
                "relevanceIndicator": "RECOMMENDED"
            }
        ]
    }


class TestDataConversion:
    """Test data conversion functions."""
    
    def test_convert_category_node_complete(self):
        """Test conversion with complete node data."""
        node = {
            "categoryId": "267",
            "categoryName": "Books, Movies & Music",
            "categoryTreeNodeLevel": 1,
            "leafCategory": False,
            "parentCategoryId": "20081",
            "childCategoryTreeNodes": [
                {"categoryId": "377", "categoryName": "Books"}
            ]
        }
        
        result = _convert_category_node(node)
        
        assert result["category_id"] == "267"
        assert result["category_name"] == "Books, Movies & Music"
        assert result["level"] == 1
        assert result["leaf"] == False
        assert result["parent_id"] == "20081"
        assert result["child_count"] == 1
        assert result["has_children"] == True
    
    def test_convert_category_node_minimal(self):
        """Test conversion with minimal node data."""
        node = {
            "categoryId": "377",
            "categoryName": "Books"
        }
        
        result = _convert_category_node(node)
        
        assert result["category_id"] == "377"
        assert result["category_name"] == "Books"
        assert result["level"] == 1  # Default
        assert result["leaf"] == False  # Default
        assert result["parent_id"] is None
        assert result["child_count"] == 0
        assert result["has_children"] == False
    
    def test_convert_category_subtree(self):
        """Test subtree conversion."""
        subtree = {
            "categoryId": "267",
            "categoryName": "Books, Movies & Music",
            "categoryTreeNodeLevel": 1,
            "leafCategory": False,
            "childCategoryTreeNodes": [
                {
                    "categoryId": "377",
                    "categoryName": "Books",
                    "categoryTreeNodeLevel": 2,
                    "leafCategory": True
                }
            ]
        }
        
        result = _convert_category_subtree(subtree)
        
        assert len(result) == 2  # Parent + child
        assert result[0]["category_id"] == "267"
        assert result[0]["category_name"] == "Books, Movies & Music"
        assert result[1]["category_id"] == "377"
        assert result[1]["category_name"] == "Books"
        assert result[1]["parent_id"] == "267"


class TestGetDefaultCategoryTreeId:
    """Test the get_default_category_tree_id tool."""
    
    @pytest.mark.asyncio
    async def test_get_default_category_tree_id_success(self, mock_context, mock_rest_client):
        """Test successful category tree ID retrieval."""
        with patch('tools.taxonomy_api.EbayRestClient') as mock_client_class:
            mock_client_class.return_value = mock_rest_client
            mock_rest_client.get.return_value = {"categoryTreeId": "100"}
            
            result = await get_default_category_tree_id.fn(
                ctx=mock_context,
                marketplace_id="EBAY_GB"
            )
            
            result_data = json.loads(result)
            assert result_data["status"] == "success"
            assert result_data["data"]["category_tree_id"] == "100"
            assert result_data["data"]["marketplace_id"] == "EBAY_GB"
            assert result_data["data"]["data_source"] == "live_api"
            
            # Verify API call
            mock_rest_client.get.assert_called_once_with(
                "/commerce/taxonomy/v1/get_default_category_tree_id",
                params={"marketplace_id": "EBAY_GB"},
                scope="https://api.ebay.com/oauth/api_scope/commerce.taxonomy.readonly"
            )
    
    @pytest.mark.asyncio
    async def test_get_default_category_tree_id_no_credentials(self, mock_context):
        """Test without credentials returns default."""
        with patch('tools.taxonomy_api.mcp') as mock_mcp:
            mock_mcp.config.app_id = ""
            mock_mcp.config.cert_id = ""
            
            result = await get_default_category_tree_id.fn(
                ctx=mock_context,
                marketplace_id="EBAY_US"
            )
            
            result_data = json.loads(result)
            assert result_data["status"] == "success"
            assert result_data["data"]["category_tree_id"] == "0"
            assert result_data["data"]["data_source"] == "static_default"
    
    @pytest.mark.asyncio
    async def test_get_default_category_tree_id_api_error(self, mock_context, mock_rest_client):
        """Test API error handling."""
        with patch('tools.taxonomy_api.EbayRestClient') as mock_client_class:
            mock_client_class.return_value = mock_rest_client
            mock_rest_client.get.side_effect = EbayApiError(
                status_code=404,
                error_response={"message": "Marketplace not found"}
            )
            
            result = await get_default_category_tree_id.fn(
                ctx=mock_context,
                marketplace_id="INVALID"
            )
            
            result_data = json.loads(result)
            assert result_data["status"] == "error"
            assert result_data["error_code"] == "EXTERNAL_API_ERROR"


class TestGetCategoryTree:
    """Test the get_category_tree tool."""
    
    @pytest.mark.asyncio
    async def test_get_category_tree_full_tree(self, mock_context, mock_rest_client, mock_category_tree_response):
        """Test full category tree retrieval."""
        with patch('tools.taxonomy_api.EbayRestClient') as mock_client_class:
            mock_client_class.return_value = mock_rest_client
            mock_rest_client.get.return_value = mock_category_tree_response
            
            result = await get_category_tree.fn(
                ctx=mock_context,
                category_tree_id="0"
            )
            
            result_data = json.loads(result)
            assert result_data["status"] == "success"
            assert len(result_data["data"]["categories"]) == 4  # Root + 2 level 1 + 1 level 2
            assert result_data["data"]["metadata"]["category_tree_id"] == "0"
            assert result_data["data"]["metadata"]["category_tree_version"] == "119"
            assert result_data["data"]["metadata"]["data_source"] == "live_api"
            
            # Verify API call
            mock_rest_client.get.assert_called_once_with(
                "/commerce/taxonomy/v1/category_tree/0",
                params={},
                scope="https://api.ebay.com/oauth/api_scope/commerce.taxonomy.readonly"
            )
    
    @pytest.mark.asyncio
    async def test_get_category_tree_subtree(self, mock_context, mock_rest_client):
        """Test category subtree retrieval."""
        subtree_response = {
            "categoryId": "267",
            "categoryName": "Books, Movies & Music",
            "categoryTreeNodeLevel": 1,
            "leafCategory": False,
            "childCategoryTreeNodes": [
                {
                    "categoryId": "377",
                    "categoryName": "Books",
                    "categoryTreeNodeLevel": 2,
                    "leafCategory": True
                }
            ]
        }
        
        with patch('tools.taxonomy_api.EbayRestClient') as mock_client_class:
            mock_client_class.return_value = mock_rest_client
            mock_rest_client.get.return_value = subtree_response
            
            result = await get_category_tree.fn(
                ctx=mock_context,
                category_tree_id="0",
                category_id="267"
            )
            
            result_data = json.loads(result)
            assert result_data["status"] == "success"
            assert len(result_data["data"]["categories"]) == 2  # Parent + child
            assert result_data["data"]["query"]["subtree_only"] == True
            assert result_data["data"]["query"]["category_id"] == "267"
            
            # Verify API call
            mock_rest_client.get.assert_called_once_with(
                "/commerce/taxonomy/v1/category_tree/0/get_category_subtree",
                params={"category_id": "267"},
                scope="https://api.ebay.com/oauth/api_scope/commerce.taxonomy.readonly"
            )
    
    @pytest.mark.asyncio
    async def test_get_category_tree_no_credentials(self, mock_context):
        """Test without credentials returns static data."""
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
            assert len(result_data["data"]["categories"]) == 10  # Static categories
    
    @pytest.mark.asyncio
    async def test_get_category_tree_validation_error(self, mock_context):
        """Test validation error handling."""
        result = await get_category_tree.fn(
            ctx=mock_context,
            category_tree_id=""  # Empty tree ID
        )
        
        result_data = json.loads(result)
        assert result_data["status"] == "error"
        assert result_data["error_code"] == "VALIDATION_ERROR"


class TestGetCategorySuggestions:
    """Test the get_category_suggestions tool."""
    
    @pytest.mark.asyncio
    async def test_get_category_suggestions_success(self, mock_context, mock_rest_client, mock_category_suggestions_response):
        """Test successful category suggestions."""
        with patch('tools.taxonomy_api.EbayRestClient') as mock_client_class:
            mock_client_class.return_value = mock_rest_client
            mock_rest_client.get.return_value = mock_category_suggestions_response
            
            result = await get_category_suggestions.fn(
                ctx=mock_context,
                query="iPhone 15 Pro",
                category_tree_id="0"
            )
            
            result_data = json.loads(result)
            assert result_data["status"] == "success"
            assert len(result_data["data"]["suggestions"]) == 2
            assert result_data["data"]["suggestions"][0]["category_id"] == "9355"
            assert result_data["data"]["suggestions"][0]["category_name"] == "Cell Phones & Smartphones"
            assert result_data["data"]["suggestions"][0]["relevancy"] == "95.0"
            assert result_data["data"]["data_source"] == "live_api"
            
            # Verify API call
            mock_rest_client.get.assert_called_once_with(
                "/commerce/taxonomy/v1/category_tree/0/get_category_suggestions",
                params={"q": "iPhone 15 Pro"},
                scope="https://api.ebay.com/oauth/api_scope/commerce.taxonomy.readonly"
            )
    
    @pytest.mark.asyncio
    async def test_get_category_suggestions_no_credentials(self, mock_context):
        """Test without credentials returns pattern matching."""
        with patch('tools.taxonomy_api.mcp') as mock_mcp:
            mock_mcp.config.app_id = ""
            mock_mcp.config.cert_id = ""
            
            result = await get_category_suggestions.fn(
                ctx=mock_context,
                query="iPhone 15 Pro"
            )
            
            result_data = json.loads(result)
            assert result_data["status"] == "success"
            assert result_data["data"]["data_source"] == "static_pattern_matching"
            assert len(result_data["data"]["suggestions"]) == 1
            assert result_data["data"]["suggestions"][0]["category_name"] == "Cell Phones & Smartphones"
    
    @pytest.mark.asyncio
    async def test_get_category_suggestions_laptop(self, mock_context):
        """Test laptop suggestion without credentials."""
        with patch('tools.taxonomy_api.mcp') as mock_mcp:
            mock_mcp.config.app_id = ""
            mock_mcp.config.cert_id = ""
            
            result = await get_category_suggestions.fn(
                ctx=mock_context,
                query="MacBook Pro laptop"
            )
            
            result_data = json.loads(result)
            assert result_data["status"] == "success"
            assert result_data["data"]["suggestions"][0]["category_name"] == "Computers & Tablets"
    
    @pytest.mark.asyncio
    async def test_get_category_suggestions_validation_error(self, mock_context):
        """Test validation error handling."""
        result = await get_category_suggestions.fn(
            ctx=mock_context,
            query=""  # Empty query
        )
        
        result_data = json.loads(result)
        assert result_data["status"] == "error"
        assert result_data["error_code"] == "VALIDATION_ERROR"


class TestGetItemAspectsForCategory:
    """Test the get_item_aspects_for_category tool."""
    
    @pytest.mark.asyncio
    async def test_get_item_aspects_success(self, mock_context, mock_rest_client, mock_item_aspects_response):
        """Test successful item aspects retrieval."""
        with patch('tools.taxonomy_api.EbayRestClient') as mock_client_class:
            mock_client_class.return_value = mock_rest_client
            mock_rest_client.get.return_value = mock_item_aspects_response
            
            result = await get_item_aspects_for_category.fn(
                ctx=mock_context,
                category_id="9355",
                category_tree_id="0"
            )
            
            result_data = json.loads(result)
            assert result_data["status"] == "success"
            assert len(result_data["data"]["aspects"]) == 2
            assert result_data["data"]["aspects"][0]["localizedAspectName"] == "Brand"
            assert result_data["data"]["aspects"][0]["aspectRequired"] == True
            assert result_data["data"]["aspects"][1]["localizedAspectName"] == "Model"
            assert result_data["data"]["aspects"][1]["aspectRequired"] == False
            assert result_data["data"]["data_source"] == "live_api"
            
            # Verify API call
            mock_rest_client.get.assert_called_once_with(
                "/commerce/taxonomy/v1/category_tree/0/get_item_aspects_for_category",
                params={"category_id": "9355"},
                scope="https://api.ebay.com/oauth/api_scope/commerce.taxonomy.readonly"
            )
    
    @pytest.mark.asyncio
    async def test_get_item_aspects_no_credentials(self, mock_context):
        """Test without credentials returns empty aspects."""
        with patch('tools.taxonomy_api.mcp') as mock_mcp:
            mock_mcp.config.app_id = ""
            mock_mcp.config.cert_id = ""
            
            result = await get_item_aspects_for_category.fn(
                ctx=mock_context,
                category_id="9355"
            )
            
            result_data = json.loads(result)
            assert result_data["status"] == "success"
            assert result_data["data"]["aspects"] == []
            assert result_data["data"]["data_source"] == "static_fallback"
    
    @pytest.mark.asyncio
    async def test_get_item_aspects_validation_error(self, mock_context):
        """Test validation error handling."""
        result = await get_item_aspects_for_category.fn(
            ctx=mock_context,
            category_id=""  # Empty category ID
        )
        
        result_data = json.loads(result)
        assert result_data["status"] == "error"
        assert result_data["error_code"] == "VALIDATION_ERROR"


class TestGetCompatibilityProperties:
    """Test the get_compatibility_properties tool."""
    
    @pytest.mark.asyncio
    async def test_get_compatibility_properties_success(self, mock_context, mock_rest_client):
        """Test successful compatibility properties retrieval."""
        compatibility_response = {
            "compatibilityProperties": [
                {
                    "name": "Year",
                    "localizedName": "Year",
                    "dataType": "STRING"
                },
                {
                    "name": "Make",
                    "localizedName": "Make",
                    "dataType": "STRING"
                }
            ]
        }
        
        with patch('tools.taxonomy_api.EbayRestClient') as mock_client_class:
            mock_client_class.return_value = mock_rest_client
            mock_rest_client.get.return_value = compatibility_response
            
            result = await get_compatibility_properties.fn(
                ctx=mock_context,
                category_id="6028",  # Auto parts category
                category_tree_id="0"
            )
            
            result_data = json.loads(result)
            assert result_data["status"] == "success"
            assert len(result_data["data"]["compatibility_properties"]) == 2
            assert result_data["data"]["data_source"] == "live_api"
            
            # Verify API call
            mock_rest_client.get.assert_called_once_with(
                "/commerce/taxonomy/v1/category_tree/0/get_compatibility_properties",
                params={"category_id": "6028"},
                scope="https://api.ebay.com/oauth/api_scope/commerce.taxonomy.readonly"
            )
    
    @pytest.mark.asyncio
    async def test_get_compatibility_properties_no_credentials(self, mock_context):
        """Test without credentials returns empty properties."""
        with patch('tools.taxonomy_api.mcp') as mock_mcp:
            mock_mcp.config.app_id = ""
            mock_mcp.config.cert_id = ""
            
            result = await get_compatibility_properties.fn(
                ctx=mock_context,
                category_id="6028"
            )
            
            result_data = json.loads(result)
            assert result_data["status"] == "success"
            assert result_data["data"]["compatibility_properties"] == []
            assert result_data["data"]["data_source"] == "static_fallback"