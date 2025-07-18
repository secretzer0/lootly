"""
Tests for Account Privileges API that can run in unit or integration mode.

Environment Variables:
    TEST_MODE=unit (default): Run with mocked dependencies
    TEST_MODE=integration: Run against real eBay API
"""
import pytest
from unittest.mock import patch, AsyncMock
import json

from tools.tests.base_test import BaseApiTest, TestMode
from tools.tests.test_helpers import (
    validate_field,
    assert_api_response_success
)
from tools.account_privileges_api import get_privileges
from api.ebay_enums import CurrencyCodeEnum


class TestAccountPrivilegesApi(BaseApiTest):
    """Test Account Privileges API functions in both unit and integration modes."""
    
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
    # Get Privileges Tests (Both unit and integration)
    # ==============================================================================
    
    @pytest.mark.asyncio
    async def test_get_privileges(self, mock_context, mock_credentials):
        """Test getting seller account privileges."""
        if self.is_integration_mode:
            # Integration test - real API call
            print(f"\\nTesting real API call to get account privileges...")
            print(f"Note: This requires user authentication")
            
            # Try to call without mocking - will check for real user token
            result = await get_privileges.fn(ctx=mock_context)
            response = json.loads(result)
            
            if response["status"] == "error":
                if response["error_code"] == "AUTHENTICATION_ERROR":
                    pytest.skip("User authentication required - run 'ebay auth' first")
                else:
                    pytest.fail(f"Unexpected error: {response['error_code']} - {response['error_message']}")
            else:
                # Success - user is authenticated
                print("User is authenticated, checking response...")
                assert response["status"] == "success"
                data = response["data"]
                validate_field(data, "seller_registration_completed", bool)
                print(f"Seller registration completed: {data['seller_registration_completed']}")
                if "selling_limit" in data and data["selling_limit"]:
                    print(f"Selling limits: {data['selling_limit']}")
        else:
            # Unit test - mocked response
            with patch('tools.account_privileges_api.EbayRestClient') as MockClient:
                mock_client = MockClient.return_value
                mock_client.get = AsyncMock(return_value={
                    "sellerRegistrationCompleted": True,
                    "sellingLimit": {
                        "amount": {
                            "currency": "USD",
                            "value": "5000.00"
                        },
                        "quantity": 100
                    }
                })
                mock_client.close = AsyncMock()
                
                with patch('tools.account_privileges_api.mcp.config.app_id', mock_credentials["app_id"]), \
                     patch('tools.account_privileges_api.mcp.config.cert_id', mock_credentials["cert_id"]):
                    
                    result = await get_privileges.fn(ctx=mock_context)
                    
                    data = assert_api_response_success(result)
                    
                    # Validate response structure
                    assert data["data"]["seller_registration_completed"] is True
                    assert data["data"]["selling_limit"]["amount"]["currency"] == "USD"
                    assert data["data"]["selling_limit"]["amount"]["value"] == "5000.00"
                    assert data["data"]["selling_limit"]["quantity"] == 100
                    
                    # Verify API was called correctly
                    mock_client.get.assert_called_once()
                    call_args = mock_client.get.call_args
                    assert call_args[0][0] == "/sell/account/v1/privilege"
    
    @pytest.mark.asyncio
    async def test_get_privileges_no_limits(self, mock_context, mock_credentials):
        """Test getting privileges when seller has no selling limits."""
        if self.is_integration_mode:
            pytest.skip("Integration test covered in main test")
        
        # Unit test - seller with no limits
        with patch('tools.account_privileges_api.EbayRestClient') as MockClient:
            mock_client = MockClient.return_value
            mock_client.get = AsyncMock(return_value={
                "sellerRegistrationCompleted": True
                # No sellingLimit field
            })
            mock_client.close = AsyncMock()
            
            with patch('tools.account_privileges_api.mcp.config.app_id', mock_credentials["app_id"]), \
                 patch('tools.account_privileges_api.mcp.config.cert_id', mock_credentials["cert_id"]), \
                 patch('tools.account_privileges_api.mcp.config.user_refresh_token', 'test_token'):
                
                result = await get_privileges.fn(ctx=mock_context)
                
                data = assert_api_response_success(result)
                
                # Should have registration status but no limits
                assert data["data"]["seller_registration_completed"] is True
                assert data["data"]["selling_limit"] is None
    
    # ==============================================================================
    # Error Handling Tests
    # ==============================================================================
    
    @pytest.mark.asyncio
    async def test_get_privileges_no_credentials(self, mock_context):
        """Test privileges with no credentials returns error."""
        with patch('tools.account_privileges_api.mcp.config.app_id', ''), \
             patch('tools.account_privileges_api.mcp.config.cert_id', ''):
            
            result = await get_privileges.fn(ctx=mock_context)
            
            # Should return error for missing credentials
            data = json.loads(result)
            assert data["status"] == "error"
            assert data["error_code"] == "CONFIGURATION_ERROR"
            assert "eBay API credentials required" in data["error_message"]
    
    @pytest.mark.asyncio
    async def test_get_privileges_no_user_token(self, mock_context, mock_credentials):
        """Test privileges without user token returns authentication error."""
        with patch('tools.account_privileges_api.mcp.config.app_id', mock_credentials["app_id"]), \
             patch('tools.account_privileges_api.mcp.config.cert_id', mock_credentials["cert_id"]), \
             patch('tools.account_privileges_api.mcp.config.user_refresh_token', None):
            
            result = await get_privileges.fn(ctx=mock_context)
            
            # Should return authentication error
            data = json.loads(result)
            assert data["status"] == "error"
            assert data["error_code"] == "AUTHENTICATION_ERROR"
            assert "User authentication required" in data["error_message"]
            assert "ebay auth" in data["error_message"]
    
    @pytest.mark.asyncio
    @TestMode.skip_in_integration("Consent required test is unit only")
    async def test_get_privileges_consent_required(self, mock_context, mock_credentials):
        """Test handling of consent required error."""
        from api.oauth import ConsentRequiredException
        
        with patch('tools.account_privileges_api.EbayRestClient') as MockClient:
            mock_client = MockClient.return_value
            mock_client.get = AsyncMock(
                side_effect=ConsentRequiredException(
                    ["sell.account"],
                    "https://auth.ebay.com/oauth2/authorize?..."
                )
            )
            mock_client.close = AsyncMock()
            
            with patch('tools.account_privileges_api.mcp.config.app_id', mock_credentials["app_id"]), \
                 patch('tools.account_privileges_api.mcp.config.cert_id', mock_credentials["cert_id"]), \
                 patch('tools.account_privileges_api.mcp.config.user_refresh_token', 'test_token'):
                
                result = await get_privileges.fn(ctx=mock_context)
                
                # Should return consent required error
                data = json.loads(result)
                assert data["status"] == "error"
                assert data["error_code"] == "CONSENT_REQUIRED"
                assert data["details"]["required_scopes"] == ["sell.account"]
                assert "auth_url" in data["details"]