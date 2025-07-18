"""
Base test class for eBay API tests with unit/integration mode switching.

This module provides the foundation for tests that can run in two modes:
- Unit mode: Uses mocked dependencies and validates interface contracts
- Integration mode: Uses real API calls and validates actual responses
"""
import os
import pytest
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any, Optional, Type, Callable
import json
from fastmcp import Context
import logging
import sys
import os

# Enable detailed aiohttp debugging for integration tests
if "--test-mode=integration" in sys.argv and os.getenv("LOOTLY_LOG_LEVEL", "").lower() == "debug":
    # Set root logger to DEBUG
    logging.basicConfig(
        level=logging.DEBUG, 
        format='%(asctime)s - %(name)s:%(filename)s:%(lineno)d - %(levelname)s - %(message)s',
        force=True  # Override any existing configuration
    )
    
    # Enable ALL aiohttp loggers
    logging.getLogger('aiohttp').setLevel(logging.DEBUG)
    logging.getLogger('aiohttp.client').setLevel(logging.DEBUG)
    logging.getLogger('aiohttp.connector').setLevel(logging.DEBUG)
    logging.getLogger('aiohttp.internal').setLevel(logging.DEBUG)
    logging.getLogger('aiohttp.access').setLevel(logging.DEBUG)
    logging.getLogger('aiohttp.client_reqrep').setLevel(logging.DEBUG)
    logging.getLogger('aiohttp.streams').setLevel(logging.DEBUG)
    logging.getLogger('aiohttp.worker').setLevel(logging.DEBUG)
    
    # Also enable asyncio debugging
    logging.getLogger('asyncio').setLevel(logging.DEBUG)
    
    # Enable our own module's logging
    logging.getLogger('api.oauth').setLevel(logging.DEBUG)
    logging.getLogger('api.rest_client').setLevel(logging.DEBUG)
    
    print("=== AIOHTTP DEBUG LOGGING ENABLED ===")


class BaseApiTest:
    """
    Base class for API tests that can run in unit or integration mode.
    
    Environment Variables:
        TEST_MODE: Set to "integration" to run real API tests (default: "unit")
        EBAY_APP_ID: Required for integration tests
        EBAY_CERT_ID: Required for integration tests
    """
    
    @property
    def is_integration_mode(self) -> bool:
        """Check if running in integration mode."""
        return os.getenv("TEST_MODE", "unit").lower() == "integration"
    
    @pytest.fixture
    def mock_context(self):
        """Create a mock FastMCP context."""
        ctx = AsyncMock(spec=Context)
        ctx.info = AsyncMock()
        ctx.error = AsyncMock()
        ctx.debug = AsyncMock()
        ctx.report_progress = AsyncMock()
        ctx.success = AsyncMock()
        ctx.warning = AsyncMock()
        return ctx
    
    @pytest.fixture
    def mock_rest_client(self):
        """Create a mock REST client for unit tests."""
        if self.is_integration_mode:
            pytest.skip("Skipping mock client in integration mode")
        
        from unittest.mock import Mock
        client = Mock()
        client.get = AsyncMock()
        client.post = AsyncMock()
        client.put = AsyncMock()
        client.delete = AsyncMock()
        client.close = AsyncMock()
        return client
    
    @pytest.fixture
    def mock_credentials(self):
        """Mock or validate credentials based on test mode."""
        if self.is_integration_mode:
            # In integration mode, ensure real credentials exist
            app_id = os.getenv("EBAY_APP_ID")
            cert_id = os.getenv("EBAY_CERT_ID")
            if not app_id or not cert_id:
                pytest.skip("Integration tests require EBAY_APP_ID and EBAY_CERT_ID")
            return {"app_id": app_id, "cert_id": cert_id}
        else:
            # In unit mode, return mock credentials
            return {"app_id": "test_app_id", "cert_id": "test_cert_id"}
    
    def setup_mocks(self, mock_patches: Dict[str, Any]) -> Dict[str, Any]:
        """
        Set up mocks for unit tests.
        
        Args:
            mock_patches: Dictionary of module paths to mock objects
            
        Returns:
            Dictionary of mock objects
        """
        if self.is_integration_mode:
            return {}
        
        mocks = {}
        for path, mock_obj in mock_patches.items():
            patcher = patch(path, mock_obj)
            mocks[path] = patcher.start()
        
        return mocks
    
    def validate_response_structure(self, response: str, expected_fields: Dict[str, Type]):
        """
        Validate that a JSON response has the expected structure.
        
        Args:
            response: JSON string response
            expected_fields: Dictionary of field names to expected types
        """
        try:
            data = json.loads(response)
        except json.JSONDecodeError:
            pytest.fail(f"Response is not valid JSON: {response}")
        
        # Check status
        assert "status" in data, "Response missing 'status' field"
        
        if data["status"] == "error":
            # Validate error response structure
            assert "error_code" in data, "Error response missing 'error_code'"
            assert "error_message" in data, "Error response missing 'error_message'"
        else:
            # Validate success response structure
            assert "data" in data, "Success response missing 'data' field"
            
            # Validate expected fields in data
            for field, expected_type in expected_fields.items():
                if "." in field:
                    # Handle nested fields
                    parts = field.split(".")
                    current = data["data"]
                    for part in parts[:-1]:
                        assert part in current, f"Missing nested field: {part}"
                        current = current[part]
                    assert parts[-1] in current, f"Missing field: {field}"
                    value = current[parts[-1]]
                else:
                    assert field in data["data"], f"Missing field: {field}"
                    value = data["data"][field]
                
                # Type validation for non-None values
                if value is not None and expected_type is not None:
                    assert isinstance(value, expected_type), \
                        f"Field '{field}' expected type {expected_type}, got {type(value)}"
    
    def assert_api_response_matches_schema(self, actual: Dict, expected_schema: Dict):
        """
        Assert that an API response matches the expected schema.
        Used in integration tests to validate real API responses.
        
        Args:
            actual: Actual API response
            expected_schema: Expected response structure from test data
        """
        for key, expected_value in expected_schema.items():
            assert key in actual, f"Missing key '{key}' in API response"
            
            if isinstance(expected_value, dict) and not key.endswith("_id"):
                # Recursively check nested dictionaries
                self.assert_api_response_matches_schema(actual[key], expected_value)
            elif isinstance(expected_value, list) and expected_value:
                # Check list structure using first item as template
                assert isinstance(actual[key], list), f"Expected '{key}' to be a list"
                if actual[key] and isinstance(expected_value[0], dict):
                    # Check structure of first item in list
                    self.assert_api_response_matches_schema(actual[key][0], expected_value[0])
            else:
                # Just verify the key exists and has the same type
                if expected_value is not None:
                    assert type(actual[key]) == type(expected_value), \
                        f"Type mismatch for '{key}': expected {type(expected_value)}, got {type(actual[key])}"
    
    @pytest.fixture(autouse=True)
    def setup_test_mode(self, request):
        """Auto-configure test based on mode."""
        if self.is_integration_mode:
            # Mark integration tests
            request.node.add_marker(pytest.mark.integration)
            # Ensure we have credentials
            if not os.getenv("EBAY_APP_ID") or not os.getenv("EBAY_CERT_ID"):
                pytest.skip("Integration tests require eBay credentials")
        else:
            # Mark unit tests
            request.node.add_marker(pytest.mark.unit)
    
    def get_test_function(self, module_name: str, function_name: str) -> Callable:
        """
        Import and return a test function dynamically.
        
        Args:
            module_name: Name of the module (e.g., 'browse_api')
            function_name: Name of the function to test
            
        Returns:
            The function object
        """
        import importlib
        module = importlib.import_module(f"tools.{module_name}")
        return getattr(module, function_name)
    
    async def run_api_test(self, api_function: Callable, test_args: Dict[str, Any], 
                          mock_response: Any = None, expected_fields: Dict[str, Type] = None):
        """
        Run an API test in either unit or integration mode.
        
        Args:
            api_function: The API function to test
            test_args: Arguments to pass to the function
            mock_response: Mock response for unit tests
            expected_fields: Expected fields in the response
        """
        if self.is_integration_mode:
            # Integration test - call real API
            result = await api_function.fn(**test_args)
            
            # Validate response structure
            if expected_fields:
                self.validate_response_structure(result, expected_fields)
            
            return json.loads(result)
        else:
            # Unit test - use mocks
            # This will be implemented by subclasses with specific mocking logic
            raise NotImplementedError("Subclasses must implement unit test mocking")


class TestMode:
    """Test mode markers and utilities."""
    
    unit = pytest.mark.unit
    integration = pytest.mark.integration
    
    @staticmethod
    def skip_in_unit(reason="Not applicable in unit test mode"):
        """Skip test in unit mode."""
        return pytest.mark.skipif(
            os.getenv("TEST_MODE", "unit").lower() == "unit",
            reason=reason
        )
    
    @staticmethod
    def skip_in_integration(reason="Not applicable in integration test mode"):
        """Skip test in integration mode."""
        return pytest.mark.skipif(
            os.getenv("TEST_MODE", "unit").lower() == "integration",
            reason=reason
        )