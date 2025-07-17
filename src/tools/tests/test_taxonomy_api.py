"""
Tests for Taxonomy API that can run in unit or integration mode.

Environment Variables:
    TEST_MODE=unit (default): Run with mocked dependencies
    TEST_MODE=integration: Run against real eBay API
"""
import pytest
from unittest.mock import patch, AsyncMock
import json
from typing import Dict, Any, List

from tools.tests.base_test import BaseApiTest, TestMode
from tools.tests.test_data import TestDataGood
from tools.tests.test_helpers import (
    validate_field,
    assert_api_response_success
)
from tools.taxonomy_api import (
    get_default_category_tree_id,
    get_category_tree,
    get_item_aspects_for_category,
    get_compatibility_properties
)


class TestTaxonomyApi(BaseApiTest):
    """Test Taxonomy API functions in both unit and integration modes."""
    
    # ==============================================================================
    # Infrastructure Validation Tests (Integration mode only)
    # ==============================================================================
    
    @pytest.mark.asyncio
    async def test_infrastructure_validation(self, mock_context):
        """CRITICAL: Validates integration infrastructure works before testing restricted APIs."""
        if not self.is_integration_mode:
            pytest.skip("Infrastructure validation only runs in integration mode")
        
        from tools.browse_api import search_items
        print("Testing integration infrastructure with Browse API...")
        print("This API uses basic scope (no user consent required)")
        
        result = await search_items.fn(ctx=mock_context, query="test", limit=1)
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
    # Get Default Category Tree ID Tests (Both unit and integration)
    # ==============================================================================
    
    @pytest.mark.asyncio
    async def test_get_default_category_tree_id(self, mock_context, mock_credentials):
        """Test getting default category tree ID for a marketplace."""
        if self.is_integration_mode:
            # Integration test - real API call
            print(f"\\nTesting real API call to eBay Taxonomy API...")
            print(f"Marketplace: EBAY_US")
            
            result = await get_default_category_tree_id.fn(
                ctx=mock_context,
                marketplace_id="EBAY_US"
            )
            
            # Parse and validate response
            response = json.loads(result)
            print(f"API Response status: {response['status']}")
            
            if response["status"] == "error":
                error_code = response.get("error_code")
                error_msg = response.get("error_message", "")
                details = response.get("details", {})
                pytest.fail(f"API call failed - {error_code}: {error_msg}\\nDetails: {details}")
            
            data = response["data"]
            validate_field(data, "category_tree_id", str)
            validate_field(data, "marketplace_id", str)
            assert data["marketplace_id"] == "EBAY_US"
            
            # US marketplace should have tree ID "0"
            assert data["category_tree_id"] == "0"
            print(f"Successfully retrieved category tree ID: {data['category_tree_id']}")
        else:
            # Unit test - mocked response
            with patch('tools.taxonomy_api.EbayRestClient') as MockClient:
                mock_client = MockClient.return_value
                mock_client.get = AsyncMock(return_value={
                    "categoryTreeId": "0"
                })
                mock_client.close = AsyncMock()
                
                with patch('tools.taxonomy_api.mcp.config.app_id', mock_credentials["app_id"]), \
                     patch('tools.taxonomy_api.mcp.config.cert_id', mock_credentials["cert_id"]):
                    
                    result = await get_default_category_tree_id.fn(
                        ctx=mock_context,
                        marketplace_id="EBAY_US"
                    )
                    
                    data = assert_api_response_success(result)
                    
                    assert data["data"]["category_tree_id"] == "0"
                    assert data["data"]["marketplace_id"] == "EBAY_US"
                    
                    # Verify API was called correctly
                    mock_client.get.assert_called_once()
                    call_args = mock_client.get.call_args
                    assert "/commerce/taxonomy/v1/get_default_category_tree_id" in call_args[0][0]
    
    # ==============================================================================
    # Get Category Tree Tests (Both unit and integration)
    # ==============================================================================
    
    @pytest.mark.asyncio
    async def test_get_category_tree_full(self, mock_context, mock_credentials):
        """Test getting full category tree."""
        if self.is_integration_mode:
            # Integration test - get full category tree as raw JSON
            result = await get_category_tree.fn(
                ctx=mock_context,
                category_tree_id="0"
            )
            
            data = assert_api_response_success(result)
            
            # Should now return raw eBay JSON structure
            validate_field(data["data"], "categoryTreeId", str)
            validate_field(data["data"], "categoryTreeVersion", str)
            validate_field(data["data"], "applicableMarketplaceIds", list)
            validate_field(data["data"], "rootCategoryNode", dict)
            
            # Check that we got the raw eBay structure
            assert data["data"]["categoryTreeId"] == "0"
            # applicableMarketplaceIds might be empty in sandbox, that's fine
            
            # Validate root category node structure
            root_node = data["data"]["rootCategoryNode"]
            validate_field(root_node, "category", dict)
            validate_field(root_node, "categoryTreeNodeLevel", int)
            
            # Check category structure
            category_info = root_node["category"]
            validate_field(category_info, "categoryId", str)
            validate_field(category_info, "categoryName", str)
        else:
            # Unit test - mocked response using test_data.py
            mock_tree_response = {
                "categoryTreeId": "0",
                "categoryTreeVersion": "123",
                "applicableMarketplaceIds": ["EBAY_US"],
                "rootCategoryNode": TestDataGood.CATEGORY_NODE_ELECTRONICS
            }
            
            with patch('tools.taxonomy_api.get_category_tree_json') as mock_get_tree:
                mock_get_tree.return_value = mock_tree_response
                
                with patch('tools.taxonomy_api.mcp.config.app_id', mock_credentials["app_id"]), \
                     patch('tools.taxonomy_api.mcp.config.cert_id', mock_credentials["cert_id"]):
                    
                    result = await get_category_tree.fn(
                        ctx=mock_context,
                        category_tree_id="0"
                    )
                    
                    data = assert_api_response_success(result)
                    
                    # Should return raw JSON from test_data.py
                    assert data["data"]["categoryTreeId"] == "0"
                    assert data["data"]["categoryTreeVersion"] == "123"
                    assert data["data"]["applicableMarketplaceIds"] == ["EBAY_US"]
                    assert data["data"]["rootCategoryNode"] == TestDataGood.CATEGORY_NODE_ELECTRONICS
    
    @pytest.mark.asyncio
    async def test_get_category_tree_subtree(self, mock_context, mock_credentials):
        """Test getting category subtree."""
        if self.is_integration_mode:
            # Integration test - get electronics subtree
            result = await get_category_tree.fn(
                ctx=mock_context,
                category_tree_id="0",
                category_id="58058"  # Consumer Electronics
            )
            
            data = assert_api_response_success(result)
            
            # Should return raw JSON subtree
            validate_field(data["data"], "category", dict)
            validate_field(data["data"], "categoryTreeNodeLevel", int)
            
            # Should be the requested category
            category_info = data["data"]["category"]
            assert category_info["categoryId"] == "58058"
        else:
            # Unit test - mock subtree using test_data.py
            mock_tree_response = {
                "categoryTreeId": "0",
                "categoryTreeVersion": "123",
                "applicableMarketplaceIds": ["EBAY_US"],
                "rootCategoryNode": TestDataGood.CATEGORY_NODE_ELECTRONICS
            }
            
            with patch('tools.taxonomy_api.get_category_tree_json') as mock_get_tree, \
                 patch('tools.taxonomy_api.find_category_subtree') as mock_find_subtree:
                
                mock_get_tree.return_value = mock_tree_response
                mock_find_subtree.return_value = TestDataGood.CATEGORY_NODE_ELECTRONICS
                
                with patch('tools.taxonomy_api.mcp.config.app_id', mock_credentials["app_id"]), \
                     patch('tools.taxonomy_api.mcp.config.cert_id', mock_credentials["cert_id"]):
                    
                    result = await get_category_tree.fn(
                        ctx=mock_context,
                        category_tree_id="0",
                        category_id="58058"
                    )
                    
                    data = assert_api_response_success(result)
                    
                    # Should return the subtree from test_data.py
                    assert data["data"] == TestDataGood.CATEGORY_NODE_ELECTRONICS
                    
                    # Verify find_category_subtree was called
                    mock_find_subtree.assert_called_once_with(mock_tree_response, "58058")
    
    # ==============================================================================
    # Get Item Aspects Tests (Both unit and integration)
    # ==============================================================================
    
    @pytest.mark.asyncio
    async def test_get_item_aspects_for_category(self, mock_context, mock_credentials):
        """Test getting item aspects for a category."""
        if self.is_integration_mode:
            # Integration test - use cell phones category
            result = await get_item_aspects_for_category.fn(
                ctx=mock_context,
                category_id="9355",  # Cell Phones & Smartphones
                category_tree_id="0"
            )
            
            data = assert_api_response_success(result)
            
            validate_field(data["data"], "aspects", list)
            validate_field(data["data"], "total_aspects", int, validator=lambda x: x >= 0)
            
            # Cell phones should have aspects like Brand, Model, etc.
            if data["data"]["aspects"]:
                for aspect in data["data"]["aspects"][:5]:  # Check first 5
                    validate_field(aspect, "localizedAspectName", str)
                    validate_field(aspect, "aspectConstraint", dict, required=False)
                    validate_field(aspect, "aspectRequired", bool, required=False)
        else:
            # Unit test
            with patch('tools.taxonomy_api.EbayRestClient') as MockClient:
                mock_client = MockClient.return_value
                mock_client.get = AsyncMock(return_value={
                    "aspects": [
                        {
                            "localizedAspectName": "Brand",
                            "aspectRequired": True,
                            "aspectDataType": "STRING",
                            "aspectValues": [
                                {"localizedValue": "Apple"},
                                {"localizedValue": "Samsung"},
                                {"localizedValue": "Google"}
                            ]
                        },
                        {
                            "localizedAspectName": "Model",
                            "aspectRequired": True,
                            "aspectDataType": "STRING"
                        }
                    ]
                })
                mock_client.close = AsyncMock()
                
                with patch('tools.taxonomy_api.mcp.config.app_id', mock_credentials["app_id"]), \
                     patch('tools.taxonomy_api.mcp.config.cert_id', mock_credentials["cert_id"]):
                    
                    result = await get_item_aspects_for_category.fn(
                        ctx=mock_context,
                        category_id="9355",
                        category_tree_id="0"
                    )
                    
                    data = assert_api_response_success(result)
                    
                    assert len(data["data"]["aspects"]) == 2
                    assert data["data"]["total_aspects"] == 2
                    
                    # Check first aspect
                    brand_aspect = data["data"]["aspects"][0]
                    assert brand_aspect["localizedAspectName"] == "Brand"
                    assert brand_aspect["aspectRequired"] is True
                    assert len(brand_aspect["aspectValues"]) == 3
    
    # ==============================================================================
    # Get Compatibility Properties Tests (Both unit and integration)
    # ==============================================================================
    
    @pytest.mark.asyncio
    async def test_get_compatibility_properties(self, mock_context, mock_credentials):
        """Test getting compatibility properties for automotive categories."""
        if self.is_integration_mode:
            # Integration test - use a category that may or may not have compatibility properties
            result = await get_compatibility_properties.fn(
                ctx=mock_context,
                category_id="9355",  # Cell Phones - should have no compatibility properties
                category_tree_id="0"
            )
            
            # Parse response - may succeed with empty list or fail in sandbox
            result_data = json.loads(result)
            
            if result_data["status"] == "error":
                # If error, check it's a reasonable error (API limitations in sandbox)
                if result_data["error_code"] not in ["EXTERNAL_API_ERROR", "INTERNAL_ERROR"]:
                    error_msg = result_data.get("error_message", "")
                    details = result_data.get("details", {})
                    pytest.fail(f"Unexpected error - {result_data['error_code']}: {error_msg}\nDetails: {details}")
            else:
                # If successful, should return empty list for non-automotive categories
                validate_field(result_data["data"], "compatibility_properties", list)
                validate_field(result_data["data"], "total_properties", int, validator=lambda x: x >= 0)
                # For non-automotive categories, expect empty results
                assert result_data["data"]["total_properties"] == 0
        else:
            # Unit test
            with patch('tools.taxonomy_api.EbayRestClient') as MockClient:
                mock_client = MockClient.return_value
                mock_client.get = AsyncMock(return_value={
                    "compatibilityProperties": [
                        {
                            "localizedName": "Year",
                            "propertyConstraint": {
                                "selectionMode": "SINGLE_SELECT"
                            }
                        },
                        {
                            "localizedName": "Make",
                            "propertyConstraint": {
                                "selectionMode": "SINGLE_SELECT"
                            }
                        }
                    ]
                })
                mock_client.close = AsyncMock()
                
                with patch('tools.taxonomy_api.mcp.config.app_id', mock_credentials["app_id"]), \
                     patch('tools.taxonomy_api.mcp.config.cert_id', mock_credentials["cert_id"]):
                    
                    result = await get_compatibility_properties.fn(
                        ctx=mock_context,
                        category_id="6028",
                        category_tree_id="0"
                    )
                    
                    data = assert_api_response_success(result)
                    
                    assert len(data["data"]["compatibility_properties"]) == 2
                    assert data["data"]["total_properties"] == 2
                    
                    # Check first property
                    year_prop = data["data"]["compatibility_properties"][0]
                    assert year_prop["localizedName"] == "Year"
                    assert year_prop["propertyConstraint"]["selectionMode"] == "SINGLE_SELECT"
    
    # ==============================================================================
    # Error Handling Tests
    # ==============================================================================
    
    @pytest.mark.asyncio
    @TestMode.skip_in_integration("Malformed response is unit test only")
    async def test_get_category_tree_malformed_response(self, mock_context, mock_credentials):
        """Test handling of malformed API responses."""
        # Mock malformed response using test_data.py
        malformed_response = {
            "categoryTreeId": "0",
            # Missing rootCategoryNode - this is malformed
            "randomField": "unexpected"
        }
        
        with patch('tools.taxonomy_api.get_category_tree_json') as mock_get_tree:
            mock_get_tree.return_value = malformed_response
            
            with patch('tools.taxonomy_api.mcp.config.app_id', mock_credentials["app_id"]), \
                 patch('tools.taxonomy_api.mcp.config.cert_id', mock_credentials["cert_id"]):
                
                result = await get_category_tree.fn(
                    ctx=mock_context,
                    category_tree_id="0"
                )
                
                data = assert_api_response_success(result)
                # Should return the malformed response as-is (raw JSON)
                assert data["data"]["categoryTreeId"] == "0"
                assert "rootCategoryNode" not in data["data"]
                assert data["data"]["randomField"] == "unexpected"
    
    # ==============================================================================
    # Static Fallback Tests
    # ==============================================================================
    
    @pytest.mark.asyncio
    async def test_get_category_tree_no_credentials(self, mock_context):
        """Test category tree with no credentials returns error."""
        with patch('tools.taxonomy_api.mcp.config.app_id', ''), \
             patch('tools.taxonomy_api.mcp.config.cert_id', ''):
            
            result = await get_category_tree.fn(
                ctx=mock_context,
                category_tree_id="0"
            )
            
            # Should return error for missing credentials (no static fallback)
            data = json.loads(result)
            assert data["status"] == "error"
            assert data["error_code"] == "CONFIGURATION_ERROR"
            assert "eBay API credentials required" in data["error_message"]