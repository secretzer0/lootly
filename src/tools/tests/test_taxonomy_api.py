"""
Tests for Taxonomy API that can run in unit or integration mode.

Environment Variables:
    TEST_MODE=unit (default): Run with mocked dependencies
    TEST_MODE=integration: Run against real eBay API
"""
import pytest
from unittest.mock import patch, AsyncMock
import json

from tools.tests.base_test import BaseApiTest, TestMode
from tools.tests.test_data import TestDataGood
from tools.tests.test_helpers import (
    validate_field,
    assert_api_response_success
)
from tools.taxonomy_api import (
    get_default_category_tree_id,
    get_category_tree,
    get_category_subtree,
    get_category_suggestions,
    get_expired_categories
)
from models.enums import MarketplaceIdEnum


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
        
        from tools.browse_api import search_items, BrowseSearchInput
        print("Testing integration infrastructure with Browse API...")
        print("This API uses basic scope (no user consent required)")
        
        search_input = BrowseSearchInput(query="test", limit=1)
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
                marketplace_id=MarketplaceIdEnum.EBAY_US
            )
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
                    "body": {
                        "categoryTreeId": "0"
                    },
                    "headers": {}
                })
                mock_client.close = AsyncMock()
                
                with patch('tools.taxonomy_api.mcp.config.app_id', mock_credentials["app_id"]), \
                     patch('tools.taxonomy_api.mcp.config.cert_id', mock_credentials["cert_id"]):
                    
                    result = await get_default_category_tree_id.fn(
                        ctx=mock_context,
                        marketplace_id=MarketplaceIdEnum.EBAY_US
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
            response = await get_category_tree.fn(
                ctx=mock_context,
                category_tree_id="0"
            )
            
            data = assert_api_response_success(response)
            
            # Should now return raw eBay JSON structure
            validate_field(data["data"], "categoryTreeId", str)
            validate_field(data["data"], "categoryTreeVersion", str)
            validate_field(data["data"], "applicableMarketplaceIds", list)
            validate_field(data["data"], "rootCategoryNode", dict)
            
            # Check that we got the raw eBay structure
            assert data["data"]["categoryTreeId"] == "0"
            
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
                    
                    response = await get_category_tree.fn(
                        ctx=mock_context,
                        category_tree_id="0"
                    )
                    
                    data = assert_api_response_success(response)
                    
                    # Should return raw JSON from test_data.py
                    assert data["data"]["categoryTreeId"] == "0"
                    assert data["data"]["categoryTreeVersion"] == "123"
                    assert data["data"]["applicableMarketplaceIds"] == ["EBAY_US"]
                    assert data["data"]["rootCategoryNode"] == TestDataGood.CATEGORY_NODE_ELECTRONICS
    
    # ==============================================================================
    # Get Category Subtree Tests (Both unit and integration)
    # ==============================================================================
    
    @pytest.mark.asyncio
    async def test_get_category_subtree(self, mock_context, mock_credentials):
        """Test getting category subtree."""
        if self.is_integration_mode:
            # Integration test - get electronics subtree
            response = await get_category_subtree.fn(
                ctx=mock_context,
                category_tree_id="0",
                category_id="58058"  # Consumer Electronics
            )
            
            data = assert_api_response_success(response)
            
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
                    
                    response = await get_category_subtree.fn(
                        ctx=mock_context,
                        category_tree_id="0",
                        category_id="58058"
                    )
                    
                    data = assert_api_response_success(response)
                    
                    # Should return the subtree from test_data.py
                    assert data["data"] == TestDataGood.CATEGORY_NODE_ELECTRONICS
                    
                    # Verify find_category_subtree was called
                    mock_find_subtree.assert_called_once_with(mock_tree_response, "58058")
    
    # ==============================================================================
    # Get Category Suggestions Tests (Both unit and integration)
    # ==============================================================================
    
    @pytest.mark.asyncio
    async def test_get_category_suggestions(self, mock_context, mock_credentials):
        """Test getting category suggestions."""
        if self.is_integration_mode:
            # Integration test - search for "phone" categories
            from lootly_server import mcp
            environment = "sandbox" if mcp.config.sandbox_mode else "production"
            print(f"\nTesting category suggestions API in {environment} environment...")
            result = await get_category_suggestions.fn(
                ctx=mock_context,
                category_tree_id="0",
                q="phone"
            )
            response = json.loads(result)
            
            # Check if the request failed
            if response["status"] == "error":
                error_code = response.get("error_code")
                error_msg = response.get("error_message", "")
                status_code = response.get("details", {}).get("status_code")
                errors = response.get("details", {}).get("errors", [])
                
                # Check if we're in sandbox mode
                is_sandbox = mcp.config.sandbox_mode
                
                # Only skip for known sandbox limitations when actually in sandbox mode
                if is_sandbox:
                    # Known sandbox limitations:
                    # 1. HTTP 500 with error ID 62000
                    # 2. HTTP 404 indicating endpoint not available in sandbox
                    if status_code == 500 and any(e.get("error_id") == 62000 for e in errors):
                        pytest.skip("Known eBay sandbox limitation: Category suggestions endpoint returns HTTP 500 (error ID 62000)")
                    elif status_code == 404:
                        pytest.skip("Known eBay sandbox limitation: Category suggestions endpoint not available (HTTP 404)")
                    elif error_code == "EXTERNAL_API_ERROR" and "not available" in error_msg.lower():
                        pytest.skip(f"Known eBay sandbox limitation: {error_msg}")
                
                # For production or unexpected sandbox errors - fail the test
                pytest.fail(f"Error from category suggestions API: {error_code} - {error_msg}\nDetails: {json.dumps(response.get('details', {}), indent=2)}")
            
            # If we got here, the request succeeded!
            print(f"Category suggestions API worked in {environment}!")
            data = response
            
            # Should have categorySuggestions array
            validate_field(data["data"], "categorySuggestions", list)
            
            # If we have suggestions, validate their structure
            if data["data"]["categorySuggestions"]:
                print(f"Found {len(data['data']['categorySuggestions'])} category suggestions")
                for suggestion in data["data"]["categorySuggestions"][:3]:  # Check first 3
                    validate_field(suggestion, "categoryId", str)
                    validate_field(suggestion, "categoryName", str)
                    validate_field(suggestion, "categoryTreeNodeLevel", int)
                    print(f"  - {suggestion['categoryName']} (ID: {suggestion['categoryId']})")
            else:
                print("No category suggestions returned (but API call succeeded)")
        else:
            # Unit test
            with patch('tools.taxonomy_api.EbayRestClient') as MockClient:
                mock_client = MockClient.return_value
                mock_client.get = AsyncMock(return_value={
                    "body": {
                        "categorySuggestions": [
                            {
                                "categoryId": "9355",
                                "categoryName": "Cell Phones & Smartphones",
                                "categoryTreeNodeLevel": 3
                            },
                            {
                                "categoryId": "15032",
                                "categoryName": "Cell Phone Accessories",
                                "categoryTreeNodeLevel": 3
                            }
                        ]
                    },
                    "headers": {}
                })
                mock_client.close = AsyncMock()
                
                with patch('tools.taxonomy_api.mcp.config.app_id', mock_credentials["app_id"]), \
                     patch('tools.taxonomy_api.mcp.config.cert_id', mock_credentials["cert_id"]):
                    
                    response = await get_category_suggestions.fn(
                        ctx=mock_context,
                        category_tree_id="0",
                        q="phone"
                    )
                    
                    data = assert_api_response_success(response)
                    
                    assert len(data["data"]["categorySuggestions"]) == 2
                    assert data["data"]["categorySuggestions"][0]["categoryId"] == "9355"
                    assert data["data"]["categorySuggestions"][0]["categoryName"] == "Cell Phones & Smartphones"
    
    # ==============================================================================
    # Get Expired Categories Tests (Both unit and integration)
    # ==============================================================================
    
    @pytest.mark.asyncio
    async def test_get_expired_categories(self, mock_context, mock_credentials):
        """Test getting expired categories."""
        if self.is_integration_mode:
            # Integration test
            response = await get_expired_categories.fn(
                ctx=mock_context,
                category_tree_id="0",
                marketplace_id=MarketplaceIdEnum.EBAY_US
            )
            
            data = assert_api_response_success(response)
            
            # Should have expiredCategories array (may be empty)
            validate_field(data["data"], "expiredCategories", list)
            
            # If we have expired categories, validate their structure
            if data["data"]["expiredCategories"]:
                for expired in data["data"]["expiredCategories"][:3]:  # Check first 3
                    validate_field(expired, "fromCategoryId", str)
                    validate_field(expired, "toCategoryId", str)
        else:
            # Unit test
            with patch('tools.taxonomy_api.EbayRestClient') as MockClient:
                mock_client = MockClient.return_value
                mock_client.get = AsyncMock(return_value={
                    "body": {
                        "expiredCategories": [
                            {
                                "fromCategoryId": "12345",
                                "toCategoryId": "67890"
                            }
                        ]
                    },
                    "headers": {}
                })
                mock_client.close = AsyncMock()
                
                with patch('tools.taxonomy_api.mcp.config.app_id', mock_credentials["app_id"]), \
                     patch('tools.taxonomy_api.mcp.config.cert_id', mock_credentials["cert_id"]):
                    
                    response = await get_expired_categories.fn(
                        ctx=mock_context,
                        category_tree_id="0",
                        marketplace_id=MarketplaceIdEnum.EBAY_US
                    )
                    
                    data = assert_api_response_success(response)
                    
                    assert len(data["data"]["expiredCategories"]) == 1
                    assert data["data"]["expiredCategories"][0]["fromCategoryId"] == "12345"
                    assert data["data"]["expiredCategories"][0]["toCategoryId"] == "67890"
    
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
    async def test_get_default_category_tree_id_no_credentials(self, mock_context):
        """Test category tree ID with no credentials returns error."""
        with patch('tools.taxonomy_api.mcp.config.app_id', ''), \
             patch('tools.taxonomy_api.mcp.config.cert_id', ''):
            
            result = await get_default_category_tree_id.fn(
                ctx=mock_context,
                marketplace_id=MarketplaceIdEnum.EBAY_US
            )
            
            # Should return configuration error
            data = json.loads(result)
            assert data["status"] == "error"
            assert data["error_code"] == "CONFIGURATION_ERROR"
            assert "eBay API credentials required" in data["error_message"]
            assert "developer.ebay.com" in data["error_message"]
    
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