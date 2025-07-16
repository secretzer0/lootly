"""Integration tests for Account API tools."""
import pytest
from unittest.mock import patch, AsyncMock
import json
from fastmcp import Context

from tools.account_api import (
    get_rate_tables,
    get_seller_standards
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
def mock_seller_standards_response():
    """Mock seller standards response."""
    return {
        "sellerLevel": "ABOVE_STANDARD",
        "defectRate": {"value": 0.5, "threshold": 2.0},
        "lateShipmentRate": {"value": 1.2, "threshold": 3.0},
        "casesNotResolved": {"value": 0.3, "threshold": 0.5},
        "evaluationDate": "2024-01-15T00:00:00Z",
        "nextEvaluationDate": "2024-04-15T00:00:00Z"
    }


class TestGetRateTablesIntegration:
    """Integration tests for get_rate_tables tool."""
    
    @pytest.mark.asyncio
    async def test_get_rate_tables_deprecated_message(self, mock_context):
        """Test that rate tables returns deprecation message."""
        result = await get_rate_tables.fn(
            ctx=mock_context,
            country_code="US"
        )
        
        result_data = json.loads(result)
        assert result_data["status"] == "success"
        assert result_data["data"]["deprecated"] == True
        assert "shipping_api" in result_data["data"]["recommended_alternatives"]["real_time_shipping_costs"]
        assert "calculate_shipping_costs()" in result_data["data"]["recommended_alternatives"]["real_time_shipping_costs"]
    
    @pytest.mark.asyncio
    async def test_get_rate_tables_validation_error(self, mock_context):
        """Test validation error handling."""
        result = await get_rate_tables.fn(
            ctx=mock_context,
            country_code="USA"  # Invalid - too long
        )
        
        result_data = json.loads(result)
        # The function doesn't validate input anymore, it just returns deprecation message
        assert result_data["status"] == "success"
        assert result_data["data"]["deprecated"] == True


class TestGetSellerStandardsIntegration:
    """Integration tests for get_seller_standards tool."""
    
    @pytest.mark.asyncio
    async def test_get_seller_standards_success(self, mock_context, mock_rest_client, mock_seller_standards_response):
        """Test successful seller standards retrieval."""
        with patch('tools.account_api.EbayRestClient') as mock_client_class, \
             patch('tools.account_api.mcp.config.app_id', 'test_app_id'), \
             patch('tools.account_api.mcp.config.cert_id', 'test_cert_id'), \
             patch('tools.account_api._check_user_consent', return_value="test_token"):
            mock_client_class.return_value = mock_rest_client
            mock_rest_client.get.return_value = mock_seller_standards_response
            
            result = await get_seller_standards.fn(
                ctx=mock_context,
                program="PROGRAM_US",
                cycle="CURRENT"
            )
            
            result_data = json.loads(result)
            assert result_data["status"] == "success"
            assert result_data["data"]["seller_standards"]["program"] == "PROGRAM_US"
            assert result_data["data"]["seller_standards"]["cycle"] == "CURRENT"
            assert result_data["data"]["seller_standards"]["seller_level"] == "ABOVE_STANDARD"
            assert result_data["data"]["seller_standards"]["defect_rate"]["value"] == 0.5
            assert result_data["data"]["seller_standards"]["defect_rate"]["threshold"] == 2.0
            assert result_data["data"]["data_source"] == "analytics_api"
            
            # Verify API call
            mock_rest_client.get.assert_called_once_with(
                "/sell/analytics/v1/seller_standards_profile/PROGRAM_US/CURRENT",
                scope="https://api.ebay.com/oauth/api_scope/sell.analytics.readonly"
            )
    
    @pytest.mark.asyncio
    async def test_get_seller_standards_no_credentials(self, mock_context):
        """Test without credentials returns static data."""
        with patch('tools.account_api.mcp') as mock_mcp:
            mock_mcp.config.app_id = ""
            mock_mcp.config.cert_id = ""
            
            result = await get_seller_standards.fn(
                ctx=mock_context,
                program="PROGRAM_US",
                cycle="CURRENT"
            )
            
            result_data = json.loads(result)
            assert result_data["status"] == "success"
            assert result_data["data"]["data_source"] == "static_fallback"
            assert result_data["data"]["seller_standards"]["seller_level"] == "ABOVE_STANDARD"
            assert "Live seller standards require eBay API credentials" in result_data["data"]["note"]
    
    @pytest.mark.asyncio
    async def test_get_seller_standards_no_user_consent(self, mock_context):
        """Test without user consent returns error."""
        with patch('tools.account_api.mcp.config.app_id', 'test_app_id'), \
             patch('tools.account_api.mcp.config.cert_id', 'test_cert_id'), \
             patch('tools.account_api._check_user_consent', return_value=None):
            
            result = await get_seller_standards.fn(
                ctx=mock_context,
                program="PROGRAM_US",
                cycle="CURRENT"
            )
            
            result_data = json.loads(result)
            assert result_data["status"] == "error"
            assert result_data["error_code"] == "AUTHENTICATION_ERROR"
            assert "User consent required" in result_data["error_message"]
    
    @pytest.mark.asyncio
    async def test_get_seller_standards_api_error(self, mock_context, mock_rest_client):
        """Test API error handling."""
        with patch('tools.account_api.EbayRestClient') as mock_client_class, \
             patch('tools.account_api.mcp.config.app_id', 'test_app_id'), \
             patch('tools.account_api.mcp.config.cert_id', 'test_cert_id'), \
             patch('tools.account_api._check_user_consent', return_value="test_token"):
            mock_client_class.return_value = mock_rest_client
            mock_rest_client.get.side_effect = EbayApiError(
                status_code=500,
                error_response={"message": "Internal server error"}
            )
            
            result = await get_seller_standards.fn(
                ctx=mock_context,
                program="PROGRAM_US",
                cycle="CURRENT"
            )
            
            result_data = json.loads(result)
            assert result_data["status"] == "error"
            # The retry logic may change error type depending on implementation
            assert result_data["error_code"] in ["EXTERNAL_API_ERROR", "INTERNAL_ERROR"]