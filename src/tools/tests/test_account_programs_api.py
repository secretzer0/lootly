"""
Tests for Account Programs API that can run in unit or integration mode.

Environment Variables:
    TEST_MODE=unit (default): Run with mocked dependencies
    TEST_MODE=integration: Run against real eBay API
"""
import pytest
from unittest.mock import patch, AsyncMock
import json

from tools.tests.base_test import BaseApiTest, TestMode
from tools.tests.test_helpers import (
    assert_api_response_success
)
from tools.account_programs_api import (
    get_opted_in_programs,
    opt_in_to_program,
    opt_out_of_program
)
from models.enums import ProgramTypeEnum


class TestAccountProgramsApi(BaseApiTest):
    """Test Account Programs API functions in both unit and integration modes."""
    
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
    # Get Opted-In Programs Tests (Both unit and integration)
    # ==============================================================================
    
    @pytest.mark.asyncio
    async def test_get_opted_in_programs(self, mock_context, mock_credentials):
        """Test getting seller's opted-in programs."""
        if self.is_integration_mode:
            # Integration test - real API call
            print(f"\\nTesting real API call to get opted-in programs...")
            print(f"Note: This requires user authentication")
            
            # Try to call the API
            result = await get_opted_in_programs.fn(ctx=mock_context)
            response = json.loads(result)
            
            if response["status"] == "error":
                if response["error_code"] == "CONSENT_REQUIRED":
                    print("User consent required - this is expected")
                    pytest.skip("User authentication required - run 'ebay auth' first")
                else:
                    pytest.fail(f"Unexpected error: {response['error_code']} - {response['error_message']}")
            else:
                # Success - user is authenticated
                print("User is authenticated, checking response...")
                assert response["status"] == "success"
                assert "programs" in response["data"]
                print(f"Found {response['data']['total_programs']} opted-in programs")
        else:
            # Unit test - mocked response
            with patch('tools.account_programs_api.EbayRestClient') as MockClient:
                mock_client = MockClient.return_value
                mock_client.get = AsyncMock(return_value={
                    "body": {
                        "programs": [
                            {"programType": "OUT_OF_STOCK_CONTROL"},
                            {"programType": "SELLING_POLICY_MANAGEMENT"}
                        ]
                    },
                    "headers": {}
                })
                mock_client.close = AsyncMock()
                
                with patch('tools.account_programs_api.mcp.config.app_id', mock_credentials["app_id"]), \
                     patch('tools.account_programs_api.mcp.config.cert_id', mock_credentials["cert_id"]):
                    
                    result = await get_opted_in_programs.fn(ctx=mock_context)
                    
                    data = assert_api_response_success(result)
                    
                    # Validate response structure
                    assert data["data"]["total_programs"] == 2
                    assert len(data["data"]["programs"]) == 2
                    
                    # Check first program
                    program1 = data["data"]["programs"][0]
                    assert program1["program_type"] == "OUT_OF_STOCK_CONTROL"
                    assert "description" in program1
                    
                    # Check second program
                    program2 = data["data"]["programs"][1]
                    assert program2["program_type"] == "SELLING_POLICY_MANAGEMENT"
                    assert "description" in program2
                    
                    # Verify API was called correctly
                    mock_client.get.assert_called_once()
                    call_args = mock_client.get.call_args
                    assert call_args[0][0] == "/sell/account/v1/program/get_opted_in_programs"
    
    @pytest.mark.asyncio
    async def test_opt_in_to_program(self, mock_context, mock_credentials):
        """Test opting into a program."""
        if self.is_integration_mode:
            # Integration test - requires user auth
            print(f"\\nTesting opt-in to program...")
            print(f"Note: This requires user authentication")
            
            result = await opt_in_to_program.fn(
                ctx=mock_context,
                program_type=ProgramTypeEnum.OUT_OF_STOCK_CONTROL
            )
            response = json.loads(result)
            
            if response["status"] == "error":
                if response["error_code"] == "CONSENT_REQUIRED":
                    print("User consent required - this is expected")
                    pytest.skip("User authentication required - run 'ebay auth' first")
                else:
                    pytest.fail(f"Unexpected error: {response['error_code']} - {response['error_message']}")
            else:
                # Success - user is authenticated
                print("Successfully opted into program")
                assert response["status"] == "success"
                assert response["data"]["status"] == "opted_in"
        else:
            # Unit test - mocked response
            with patch('tools.account_programs_api.EbayRestClient') as MockClient:
                mock_client = MockClient.return_value
                mock_client.post = AsyncMock(return_value={
                    "body": None,
                    "headers": {}
                })  # Empty response on success
                mock_client.close = AsyncMock()
                
                with patch('tools.account_programs_api.mcp.config.app_id', mock_credentials["app_id"]), \
                     patch('tools.account_programs_api.mcp.config.cert_id', mock_credentials["cert_id"]):
                    
                    result = await opt_in_to_program.fn(
                        ctx=mock_context,
                        program_type=ProgramTypeEnum.OUT_OF_STOCK_CONTROL
                    )
                    
                    data = assert_api_response_success(result)
                    
                    # Validate response
                    assert data["data"]["program_type"] == "OUT_OF_STOCK_CONTROL"
                    assert data["data"]["status"] == "opted_in"
                    assert "description" in data["data"]
                    
                    # Verify API was called correctly
                    mock_client.post.assert_called_once()
                    call_args = mock_client.post.call_args
                    assert call_args[0][0] == "/sell/account/v1/program/opt_in"
                    assert call_args[1]["json"]["programType"] == "OUT_OF_STOCK_CONTROL"
    
    # ==============================================================================
    # Opt-Out of Program Tests (Both unit and integration)
    # ==============================================================================
    
    @pytest.mark.asyncio
    async def test_opt_out_of_program(self, mock_context, mock_credentials):
        """Test opting out of a program."""
        if self.is_integration_mode:
            # Integration test - requires user auth
            print(f"\\nTesting opt-out of program...")
            print(f"Note: This requires user authentication")
            
            result = await opt_out_of_program.fn(
                ctx=mock_context,
                program_type=ProgramTypeEnum.SELLING_POLICY_MANAGEMENT
            )
            response = json.loads(result)
            
            if response["status"] == "error":
                if response["error_code"] == "CONSENT_REQUIRED":
                    print("User consent required - this is expected")
                    pytest.skip("User authentication required - run 'ebay auth' first")
                else:
                    pytest.fail(f"Unexpected error: {response['error_code']} - {response['error_message']}")
            else:
                # Success - user is authenticated
                print("Successfully opted out of program")
                assert response["status"] == "success"
                assert response["data"]["status"] == "opted_out"
        else:
            # Unit test - mocked response
            with patch('tools.account_programs_api.EbayRestClient') as MockClient:
                mock_client = MockClient.return_value
                mock_client.post = AsyncMock(return_value={
                    "body": None,
                    "headers": {}
                })  # Empty response on success
                mock_client.close = AsyncMock()
                
                with patch('tools.account_programs_api.mcp.config.app_id', mock_credentials["app_id"]), \
                     patch('tools.account_programs_api.mcp.config.cert_id', mock_credentials["cert_id"]):
                    
                    result = await opt_out_of_program.fn(
                        ctx=mock_context,
                        program_type=ProgramTypeEnum.SELLING_POLICY_MANAGEMENT
                    )
                    
                    data = assert_api_response_success(result)
                    
                    # Validate response
                    assert data["data"]["program_type"] == "SELLING_POLICY_MANAGEMENT"
                    assert data["data"]["status"] == "opted_out"
                    assert "description" in data["data"]
                    
                    # Verify API was called correctly
                    mock_client.post.assert_called_once()
                    call_args = mock_client.post.call_args
                    assert call_args[0][0] == "/sell/account/v1/program/opt_out"
                    assert call_args[1]["json"]["programType"] == "SELLING_POLICY_MANAGEMENT"
    
    # ==============================================================================
    # Error Handling Tests
    # ==============================================================================
    
    @pytest.mark.asyncio
    async def test_get_programs_no_credentials(self, mock_context):
        """Test programs with no credentials returns error."""
        with patch('tools.account_programs_api.mcp.config.app_id', ''), \
             patch('tools.account_programs_api.mcp.config.cert_id', ''):
            
            result = await get_opted_in_programs.fn(ctx=mock_context)
            
            # Should return error for missing credentials
            data = json.loads(result)
            assert data["status"] == "error"
            assert data["error_code"] == "CONFIGURATION_ERROR"
            assert "eBay API credentials required" in data["error_message"]
    
    @pytest.mark.asyncio
    async def test_opt_in_invalid_program(self, mock_context, mock_credentials):
        """Test opt-in with invalid program type."""
        from unittest.mock import MagicMock
        
        # Create a mock invalid enum value
        invalid_program = MagicMock()
        invalid_program.value = "INVALID_PROGRAM"
        invalid_program.name = "INVALID_PROGRAM"
        
        # Call the function with the mock invalid enum
        result = await opt_in_to_program.fn(
            ctx=mock_context,
            program_type=invalid_program
        )
        
        # Parse response
        response = json.loads(result)
        
        # Should get validation error when trying to create OptInOutInput
        assert response["status"] == "error"
        assert response["error_code"] == "VALIDATION_ERROR"
        # Pydantic validation error will mention valid enum values
        assert "Input should be" in response["error_message"]
        assert "validation error" in response["error_message"].lower()
    
    @pytest.mark.asyncio
    @TestMode.skip_in_integration("API error test is unit only")
    async def test_opt_in_api_error(self, mock_context, mock_credentials):
        """Test handling of API errors during opt-in."""
        from api.errors import EbayApiError
        
        with patch('tools.account_programs_api.EbayRestClient') as MockClient:
            mock_client = MockClient.return_value
            mock_error = EbayApiError(
                status_code=409,
                error_response={
                    "errors": [{
                        "errorId": 20001,
                        "domain": "API_ACCOUNT",
                        "category": "REQUEST",
                        "message": "Already opted into program"
                    }]
                }
            )
            mock_client.post = AsyncMock(side_effect=mock_error)
            mock_client.close = AsyncMock()
            
            with patch('tools.account_programs_api.mcp.config.app_id', mock_credentials["app_id"]), \
                 patch('tools.account_programs_api.mcp.config.cert_id', mock_credentials["cert_id"]):
                
                result = await opt_in_to_program.fn(
                    ctx=mock_context,
                    program_type=ProgramTypeEnum.OUT_OF_STOCK_CONTROL
                )
                
                # Should return API error
                data = json.loads(result)
                assert data["status"] == "error"
                assert data["error_code"] == "EXTERNAL_API_ERROR"
                assert "Already opted into program" in data["error_message"]
                assert data["details"]["program_type"] == "OUT_OF_STOCK_CONTROL"