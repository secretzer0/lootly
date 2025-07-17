"""
Tests for Account API that can run in unit or integration mode.

Environment Variables:
    TEST_MODE=unit (default): Run with mocked dependencies
    TEST_MODE=integration: Run against real eBay API
"""
import pytest
from unittest.mock import patch, AsyncMock, Mock
import json

from tools.tests.base_test import BaseApiTest, TestMode
from tools.tests.test_data import TestDataGood, TestDataError
from tools.tests.test_helpers import (
    validate_field,
    assert_api_response_success
)
from tools.account_api import (
    get_seller_standards,
    _check_user_consent
)
from api.errors import EbayApiError


class TestAccountApi(BaseApiTest):
    """Test Account API functions in both unit and integration modes."""
    
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
    # Get Seller Standards Tests (Both unit and integration)
    # ==============================================================================
    
    @pytest.mark.asyncio
    async def test_get_seller_standards_basic(self, mock_context, mock_credentials):
        """Test getting seller standards."""
        if self.is_integration_mode:
            # Integration test - real API call (will likely fail without user consent)
            print(f"\nTesting real API call to eBay sandbox...")
            print(f"Program: PROGRAM_US, Cycle: CURRENT")
            
            result = await get_seller_standards.fn(
                ctx=mock_context,
                program="PROGRAM_US",
                cycle="CURRENT"
            )
            
            # Parse response
            response = json.loads(result)
            print(f"API Response status: {response['status']}")
            
            # Real integration test will likely fail with auth error without user consent
            if response["status"] == "error":
                error_code = response.get("error_code")
                error_msg = response.get("error_message", "")
                details = response.get("details", {})
                
                # Expected auth error without real user consent in integration mode
                if error_code in ["AUTHENTICATION_ERROR", "EXTERNAL_API_ERROR"]:
                    print(f"Expected: User consent required for Account API - {error_msg}")
                else:
                    pytest.fail(f"Unexpected error - {error_code}: {error_msg}\nDetails: {details}")
            else:
                # If somehow we have real user consent, validate the response
                print("SUCCESS: User consent available, validating response structure")
                standards = response["data"]["seller_standards"]
                
                # Validate structure and types, not specific values
                validate_field(standards, "program", str, validator=lambda x: len(x) > 0)
                validate_field(standards, "cycle", str, validator=lambda x: len(x) > 0)
                validate_field(standards, "seller_level", str, validator=lambda x: len(x) > 0)
                
                # Validate metrics array exists and has proper structure
                validate_field(standards, "metrics", list)
                if standards["metrics"]:
                    # Check first metric has expected structure
                    first_metric = standards["metrics"][0]
                    validate_field(first_metric, "metricKey", str)
                    validate_field(first_metric, "name", str)
                    validate_field(first_metric, "level", str)
                    
                # Check optional rate fields if present - they are objects with value/numerator/denominator
                if "defect_rate" in standards and standards["defect_rate"]:
                    validate_field(standards["defect_rate"], "value", str)  # Value is a string
                    validate_field(standards["defect_rate"], "numerator", int, required=False)
                    validate_field(standards["defect_rate"], "denominator", int, required=False)
                    
                print(f"Successfully validated seller standards for {standards['program']}")
        else:
            # Unit test - mocked response
            with patch('tools.account_api._check_user_consent', return_value="test_user_token"), \
                 patch('tools.account_api.EbayRestClient') as MockClient:
                
                mock_client = MockClient.return_value
                mock_client.get = AsyncMock(return_value=TestDataGood.SELLER_STANDARDS_RESPONSE)
                mock_client.close = AsyncMock()
                # Mock the _user_token property
                type(mock_client)._user_token = "test_user_token"
                
                with patch('tools.account_api.mcp.config.app_id', mock_credentials["app_id"]), \
                     patch('tools.account_api.mcp.config.cert_id', mock_credentials["cert_id"]):
                    
                    result = await get_seller_standards.fn(
                        ctx=mock_context,
                        program="PROGRAM_US",
                        cycle="CURRENT"
                    )
                    
                    data = assert_api_response_success(result)
                    
                    standards = data["data"]["seller_standards"]
                    # Validate types and structure, not specific values
                    validate_field(standards, "program", str, validator=lambda x: len(x) > 0)
                    validate_field(standards, "cycle", str, validator=lambda x: len(x) > 0)
                    validate_field(standards, "seller_level", str, validator=lambda x: len(x) > 0)
                    
                    # Check metrics structure - rates are objects with value/numerator/denominator
                    if "defect_rate" in standards and standards["defect_rate"]:
                        validate_field(standards["defect_rate"], "value", str)  # Value is a string like "0.14"
                        validate_field(standards["defect_rate"], "numerator", int, required=False)
                        validate_field(standards["defect_rate"], "denominator", int, required=False)
                    
                    # Verify API was called correctly
                    mock_client.get.assert_called()
                    call_args = mock_client.get.call_args
                    assert "/sell/analytics/v1/seller_standards_profile/PROGRAM_US/CURRENT" in call_args[0][0]
    
    @pytest.mark.asyncio
    @TestMode.skip_in_integration("No consent test is unit mode only")
    async def test_get_seller_standards_no_consent(self, mock_context, mock_credentials):
        """Test seller standards without user consent - unit test only."""
        # Mock no user consent
        with patch('tools.account_api._check_user_consent', return_value=None):
            with patch('tools.account_api.mcp.config.app_id', mock_credentials["app_id"]), \
                 patch('tools.account_api.mcp.config.cert_id', mock_credentials["cert_id"]):
                
                result = await get_seller_standards.fn(
                    ctx=mock_context,
                    program="PROGRAM_US"
                )
                
                data = json.loads(result)
                assert data["status"] == "error"
                assert data["error_code"] == "AUTHENTICATION_ERROR"
                assert "consent required" in data["error_message"].lower()
    
    @pytest.mark.asyncio
    async def test_get_seller_standards_different_programs(self, mock_context, mock_credentials):
        """Test seller standards for different programs."""
        programs = ["PROGRAM_US", "PROGRAM_UK", "PROGRAM_DE", "PROGRAM_GLOBAL"]
        
        for program in programs:
            if self.is_integration_mode:
                # Skip in integration mode as it requires real user consent
                continue
            else:
                # Unit test
                with patch('tools.account_api._check_user_consent', return_value="test_user_token"), \
                     patch('tools.account_api.EbayRestClient') as MockClient:
                    
                    mock_client = MockClient.return_value
                    # Modify response for different programs
                    response = TestDataGood.SELLER_STANDARDS_RESPONSE.copy()
                    response["program"] = program
                    mock_client.get = AsyncMock(return_value=response)
                    mock_client.close = AsyncMock()
                    type(mock_client)._user_token = "test_user_token"
                    
                    with patch('tools.account_api.mcp.config.app_id', mock_credentials["app_id"]), \
                         patch('tools.account_api.mcp.config.cert_id', mock_credentials["cert_id"]):
                        
                        result = await get_seller_standards.fn(
                            ctx=mock_context,
                            program=program,
                            cycle="CURRENT"
                        )
                        
                        data = assert_api_response_success(result)
                        # Just validate the structure, not specific values
                        validate_field(data["data"]["seller_standards"], "program", str)
    
    # ==============================================================================
    # Error Handling Tests
    # ==============================================================================
    
    @pytest.mark.asyncio
    async def test_get_seller_standards_error_handling(self, mock_context, mock_credentials):
        """Test error handling in seller standards."""
        if self.is_integration_mode:
            # Integration test - real API call with invalid program
            result = await get_seller_standards.fn(
                ctx=mock_context,
                program="INVALID_PROGRAM",
                cycle="CURRENT"
            )
            
            response = json.loads(result)
            print(f"API Response status: {response['status']}")
            
            if response["status"] == "error":
                error_code = response.get("error_code")
                error_msg = response.get("error_message", "")
                details = response.get("details", {})
                
                # Expected auth error or validation error
                if error_code in ["EXTERNAL_API_ERROR", "VALIDATION_ERROR", "AUTHENTICATION_ERROR"]:
                    print(f"Expected: Invalid program rejected - {error_msg}")
                else:
                    pytest.fail(f"Unexpected error - {error_code}: {error_msg}\nDetails: {details}")
            else:
                pytest.fail(f"Expected error for invalid program, but got success: {response}")
        else:
            # Unit test error handling
            with patch('tools.account_api._check_user_consent', return_value="test_user_token"), \
                 patch('tools.account_api.EbayRestClient') as MockClient:
                
                mock_client = MockClient.return_value
                mock_client.get = AsyncMock(side_effect=EbayApiError(
                    status_code=404,
                    error_response=TestDataError.ERROR_NOT_FOUND
                ))
                mock_client.close = AsyncMock()
                type(mock_client)._user_token = "test_user_token"
                
                with patch('tools.account_api.mcp.config.app_id', mock_credentials["app_id"]), \
                     patch('tools.account_api.mcp.config.cert_id', mock_credentials["cert_id"]):
                    
                    result = await get_seller_standards.fn(
                        ctx=mock_context,
                        program="PROGRAM_US"
                    )
                    
                    data = json.loads(result)
                    assert data["status"] == "error"
                    assert data["error_code"] == "EXTERNAL_API_ERROR"
                    # Don't check additional_info as it may vary in implementation
    
    # ==============================================================================
    # Static Fallback Tests
    # ==============================================================================
    
    @pytest.mark.asyncio
    async def test_get_seller_standards_no_credentials(self, mock_context):
        """Test seller standards with no credentials uses static fallback."""
        with patch('tools.account_api.mcp.config.app_id', ''), \
             patch('tools.account_api.mcp.config.cert_id', ''):
            
            result = await get_seller_standards.fn(
                ctx=mock_context,
                program="PROGRAM_US"
            )
            
            data = assert_api_response_success(result)
            # Static fallback returns sample data
            assert "seller_standards" in data["data"]
            assert data["data"]["data_source"] == "static_fallback"
            
            standards = data["data"]["seller_standards"]
            # Validate structure and types, not specific values
            validate_field(standards, "seller_level", str, validator=lambda x: len(x) > 0)
            validate_field(standards, "metrics", list)
    
    # ==============================================================================
    # Helper Function Tests
    # ==============================================================================
    
    @pytest.mark.asyncio
    @TestMode.skip_in_integration("Helper function test is unit only")
    async def test_check_user_consent(self, mock_context):
        """Test user consent check helper."""
        # Test with no app_id
        with patch('tools.account_api.mcp.config.app_id', ''):
            result = await _check_user_consent(mock_context)
            assert result is None
        
        # Test with no user token
        with patch('tools.account_api.mcp.config.app_id', 'test_app_id'), \
             patch('tools.account_api.get_user_access_token', return_value=None) as mock_get_token:
            result = await _check_user_consent(mock_context)
            assert result is None
            mock_get_token.assert_called_once_with('test_app_id')
            mock_context.info.assert_called()
        
        # Test with valid user token
        with patch('tools.account_api.mcp.config.app_id', 'test_app_id'), \
             patch('tools.account_api.get_user_access_token', return_value='valid_token'):
            result = await _check_user_consent(mock_context)
            assert result == 'valid_token'