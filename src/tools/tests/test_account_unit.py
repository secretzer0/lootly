"""Unit tests for Account API tools."""
import pytest
from unittest.mock import Mock, patch, AsyncMock
import json
from datetime import datetime
from fastmcp import Context

from tools.account_api import (
    get_business_policies,
    get_rate_tables,
    get_seller_standards,
    _convert_policy,
    _convert_rate_table,
    PolicySearchInput,
    RateTableInput
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
    with patch('tools.account_api.mcp') as mock_mcp:
        mock_mcp.config.app_id = "test_app_id"
        mock_mcp.config.cert_id = "test_cert_id"
        mock_mcp.config.sandbox_mode = True
        mock_mcp.config.rate_limit_per_day = 5000
        mock_mcp.logger = Mock()
        yield mock_mcp


@pytest.fixture
def mock_payment_policies_response():
    """Mock payment policies response."""
    return {
        "paymentPolicies": [
            {
                "paymentPolicyId": "12345",
                "name": "Standard Payment Policy",
                "description": "Accept PayPal and credit cards",
                "marketplaceId": "EBAY_US",
                "categoryTypes": [{"name": "ALL_EXCLUDING_MOTORS_VEHICLES"}],
                "paymentMethods": [
                    {"paymentMethodType": "PAYPAL", "brands": ["PAYPAL"]},
                    {"paymentMethodType": "CREDIT_CARD", "brands": ["VISA", "MASTERCARD"]}
                ],
                "immediatePayRequired": False,
                "createdDate": "2024-01-01T00:00:00Z",
                "lastModifiedDate": "2024-01-01T00:00:00Z"
            }
        ]
    }


@pytest.fixture
def mock_rate_tables_response():
    """Mock rate tables response."""
    return {
        "rateTables": [
            {
                "rateTableId": "67890",
                "name": "Standard US Shipping",
                "description": "Standard shipping rates for US",
                "countryCode": "US",
                "locality": "DOMESTIC",
                "rateTableType": "SHIPPING",
                "shippingServices": [
                    {
                        "shippingServiceCode": "USPSGround",
                        "shippingCarrierCode": "USPS",
                        "baseShippingCost": {"value": "8.95", "currency": "USD"}
                    }
                ],
                "createdDate": "2024-01-01T00:00:00Z",
                "lastModifiedDate": "2024-01-01T00:00:00Z"
            }
        ]
    }


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


class TestInputValidation:
    """Test input validation models."""
    
    def test_policy_search_input_valid(self):
        """Test valid policy search input."""
        input_data = PolicySearchInput(
            policy_type="PAYMENT",
            marketplace_id="EBAY_US"
        )
        
        assert input_data.policy_type == "PAYMENT"
        assert input_data.marketplace_id == "EBAY_US"
    
    def test_policy_search_input_invalid_type(self):
        """Test invalid policy type."""
        with pytest.raises(ValueError, match="Policy type must be one of"):
            PolicySearchInput(
                policy_type="INVALID",
                marketplace_id="EBAY_US"
            )
    
    def test_rate_table_input_valid(self):
        """Test valid rate table input."""
        input_data = RateTableInput(country_code="US")
        
        assert input_data.country_code == "US"
    
    def test_rate_table_input_invalid_code(self):
        """Test invalid country code."""
        with pytest.raises(ValueError, match="Country code must be 2 characters"):
            RateTableInput(country_code="USA")
    
    def test_rate_table_input_lowercase_conversion(self):
        """Test country code uppercase conversion."""
        input_data = RateTableInput(country_code="gb")
        
        assert input_data.country_code == "GB"


class TestDataConversion:
    """Test data conversion functions."""
    
    def test_convert_policy_payment(self):
        """Test payment policy conversion."""
        policy = {
            "paymentPolicyId": "12345",
            "name": "Standard Payment Policy",
            "description": "Accept PayPal and credit cards",
            "marketplaceId": "EBAY_US",
            "categoryTypes": [{"name": "ALL_EXCLUDING_MOTORS_VEHICLES"}],
            "createdDate": "2024-01-01T00:00:00Z",
            "lastModifiedDate": "2024-01-01T00:00:00Z"
        }
        
        result = _convert_policy(policy)
        
        assert result["policy_id"] == "12345"
        assert result["name"] == "Standard Payment Policy"
        assert result["description"] == "Accept PayPal and credit cards"
        assert result["marketplace_id"] == "EBAY_US"
        assert result["category_types"] == [{"name": "ALL_EXCLUDING_MOTORS_VEHICLES"}]
        assert result["created_date"] == "2024-01-01T00:00:00Z"
        assert result["last_modified_date"] == "2024-01-01T00:00:00Z"
    
    def test_convert_policy_shipping(self):
        """Test shipping policy conversion."""
        policy = {
            "shippingPolicyId": "54321",
            "name": "Standard Shipping Policy",
            "description": "Standard shipping rates",
            "marketplaceId": "EBAY_US"
        }
        
        result = _convert_policy(policy)
        
        assert result["policy_id"] == "54321"
        assert result["name"] == "Standard Shipping Policy"
    
    def test_convert_rate_table(self):
        """Test rate table conversion."""
        rate_table = {
            "rateTableId": "67890",
            "name": "Standard US Shipping",
            "description": "Standard shipping rates for US",
            "countryCode": "US",
            "locality": "DOMESTIC",
            "rateTableType": "SHIPPING",
            "shippingServices": [
                {
                    "shippingServiceCode": "USPSGround",
                    "shippingCarrierCode": "USPS"
                }
            ],
            "createdDate": "2024-01-01T00:00:00Z",
            "lastModifiedDate": "2024-01-01T00:00:00Z"
        }
        
        result = _convert_rate_table(rate_table)
        
        assert result["rate_table_id"] == "67890"
        assert result["name"] == "Standard US Shipping"
        assert result["description"] == "Standard shipping rates for US"
        assert result["country_code"] == "US"
        assert result["locality"] == "DOMESTIC"
        assert result["rate_table_type"] == "SHIPPING"
        assert len(result["shipping_services"]) == 1
        assert result["created_date"] == "2024-01-01T00:00:00Z"
        assert result["last_modified_date"] == "2024-01-01T00:00:00Z"


class TestGetBusinessPolicies:
    """Test the get_business_policies tool."""
    
    @pytest.mark.asyncio
    async def test_get_business_policies_payment_success(self, mock_context, mock_rest_client, mock_payment_policies_response):
        """Test successful payment policies retrieval."""
        with patch('tools.account_api.EbayRestClient') as mock_client_class:
            mock_client_class.return_value = mock_rest_client
            mock_rest_client.get.return_value = mock_payment_policies_response
            
            result = await get_business_policies.fn(
                ctx=mock_context,
                policy_type="PAYMENT",
                marketplace_id="EBAY_US"
            )
            
            result_data = json.loads(result)
            assert result_data["status"] == "success"
            assert len(result_data["data"]["policies"]) == 1
            assert result_data["data"]["policies"][0]["policy_id"] == "12345"
            assert result_data["data"]["policy_type"] == "PAYMENT"
            assert result_data["data"]["marketplace_id"] == "EBAY_US"
            assert result_data["data"]["data_source"] == "live_api"
            
            # Verify API call
            mock_rest_client.get.assert_called_once_with(
                "/sell/account/v1/payment_policy",
                params={"marketplace_id": "EBAY_US"},
                scope="https://api.ebay.com/oauth/api_scope/sell.account"
            )
    
    @pytest.mark.asyncio
    async def test_get_business_policies_no_credentials(self, mock_context):
        """Test without credentials returns static data."""
        with patch('tools.account_api.mcp') as mock_mcp:
            mock_mcp.config.app_id = ""
            mock_mcp.config.cert_id = ""
            
            result = await get_business_policies.fn(
                ctx=mock_context,
                policy_type="PAYMENT",
                marketplace_id="EBAY_US"
            )
            
            result_data = json.loads(result)
            assert result_data["status"] == "success"
            assert result_data["data"]["data_source"] == "static_fallback"
            assert len(result_data["data"]["policies"]) == 1
            assert "Live policy data requires eBay API credentials" in result_data["data"]["note"]
    
    @pytest.mark.asyncio
    async def test_get_business_policies_validation_error(self, mock_context):
        """Test validation error handling."""
        result = await get_business_policies.fn(
            ctx=mock_context,
            policy_type="INVALID_TYPE",
            marketplace_id="EBAY_US"
        )
        
        result_data = json.loads(result)
        assert result_data["status"] == "error"
        assert result_data["error_code"] == "VALIDATION_ERROR"
    
    @pytest.mark.asyncio
    async def test_get_business_policies_api_error(self, mock_context, mock_rest_client):
        """Test API error handling."""
        with patch('tools.account_api.EbayRestClient') as mock_client_class:
            mock_client_class.return_value = mock_rest_client
            mock_rest_client.get.side_effect = EbayApiError(
                status_code=403,
                error_response={"message": "Access denied"}
            )
            
            result = await get_business_policies.fn(
                ctx=mock_context,
                policy_type="PAYMENT",
                marketplace_id="EBAY_US"
            )
            
            result_data = json.loads(result)
            assert result_data["status"] == "error"
            assert result_data["error_code"] == "EXTERNAL_API_ERROR"


class TestGetRateTables:
    """Test the get_rate_tables tool."""
    
    @pytest.mark.asyncio
    async def test_get_rate_tables_success(self, mock_context, mock_rest_client, mock_rate_tables_response):
        """Test successful rate tables retrieval."""
        with patch('tools.account_api.EbayRestClient') as mock_client_class:
            mock_client_class.return_value = mock_rest_client
            mock_rest_client.get.return_value = mock_rate_tables_response
            
            result = await get_rate_tables.fn(
                ctx=mock_context,
                country_code="US"
            )
            
            result_data = json.loads(result)
            assert result_data["status"] == "success"
            assert len(result_data["data"]["rate_tables"]) == 1
            assert result_data["data"]["rate_tables"][0]["rate_table_id"] == "67890"
            assert result_data["data"]["country_code"] == "US"
            assert result_data["data"]["data_source"] == "live_api"
            
            # Verify API call
            mock_rest_client.get.assert_called_once_with(
                "/sell/account/v1/rate_table",
                params={"country_code": "US"},
                scope="https://api.ebay.com/oauth/api_scope/sell.account"
            )
    
    @pytest.mark.asyncio
    async def test_get_rate_tables_no_credentials(self, mock_context):
        """Test without credentials returns static data."""
        with patch('tools.account_api.mcp') as mock_mcp:
            mock_mcp.config.app_id = ""
            mock_mcp.config.cert_id = ""
            
            result = await get_rate_tables.fn(
                ctx=mock_context,
                country_code="US"
            )
            
            result_data = json.loads(result)
            assert result_data["status"] == "success"
            assert result_data["data"]["data_source"] == "static_fallback"
            assert len(result_data["data"]["rate_tables"]) == 1
            assert "Live rate table data requires eBay API credentials" in result_data["data"]["note"]
    
    @pytest.mark.asyncio
    async def test_get_rate_tables_validation_error(self, mock_context):
        """Test validation error handling."""
        result = await get_rate_tables.fn(
            ctx=mock_context,
            country_code="USA"  # Invalid - too long
        )
        
        result_data = json.loads(result)
        assert result_data["status"] == "error"
        assert result_data["error_code"] == "VALIDATION_ERROR"


class TestGetSellerStandards:
    """Test the get_seller_standards tool."""
    
    @pytest.mark.asyncio
    async def test_get_seller_standards_success(self, mock_context, mock_rest_client, mock_seller_standards_response):
        """Test successful seller standards retrieval."""
        with patch('tools.account_api.EbayRestClient') as mock_client_class:
            mock_client_class.return_value = mock_rest_client
            mock_rest_client.get.return_value = mock_seller_standards_response
            
            result = await get_seller_standards.fn(
                ctx=mock_context,
                marketplace_id="EBAY_US"
            )
            
            result_data = json.loads(result)
            assert result_data["status"] == "success"
            assert result_data["data"]["seller_standards"]["marketplace_id"] == "EBAY_US"
            assert result_data["data"]["seller_standards"]["seller_level"] == "ABOVE_STANDARD"
            assert result_data["data"]["seller_standards"]["defect_rate"]["value"] == 0.5
            assert result_data["data"]["seller_standards"]["defect_rate"]["threshold"] == 2.0
            assert result_data["data"]["seller_standards"]["data_source"] == "live_api"
            
            # Verify API call
            mock_rest_client.get.assert_called_once_with(
                "/sell/account/v1/seller_standards_profile",
                params={"marketplace_id": "EBAY_US"},
                scope="https://api.ebay.com/oauth/api_scope/sell.account"
            )
    
    @pytest.mark.asyncio
    async def test_get_seller_standards_no_credentials(self, mock_context):
        """Test without credentials returns static data."""
        with patch('tools.account_api.mcp') as mock_mcp:
            mock_mcp.config.app_id = ""
            mock_mcp.config.cert_id = ""
            
            result = await get_seller_standards.fn(
                ctx=mock_context,
                marketplace_id="EBAY_US"
            )
            
            result_data = json.loads(result)
            assert result_data["status"] == "success"
            assert result_data["data"]["data_source"] == "static_fallback"
            assert result_data["data"]["seller_standards"]["seller_level"] == "ABOVE_STANDARD"
            assert "Live seller standards require eBay API credentials" in result_data["data"]["note"]
    
    @pytest.mark.asyncio
    async def test_get_seller_standards_api_error(self, mock_context, mock_rest_client):
        """Test API error handling."""
        with patch('tools.account_api.EbayRestClient') as mock_client_class:
            mock_client_class.return_value = mock_rest_client
            mock_rest_client.get.side_effect = EbayApiError(
                status_code=500,
                error_response={"message": "Internal server error"}
            )
            
            result = await get_seller_standards.fn(
                ctx=mock_context,
                marketplace_id="EBAY_US"
            )
            
            result_data = json.loads(result)
            assert result_data["status"] == "error"
            assert result_data["error_code"] == "EXTERNAL_API_ERROR"