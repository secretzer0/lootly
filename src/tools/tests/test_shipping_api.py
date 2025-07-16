"""
Tests for Shipping API that can run in unit or integration mode.

Environment Variables:
    TEST_MODE=unit (default): Run with mocked dependencies
    TEST_MODE=integration: Run against real eBay API
"""
import pytest
from unittest.mock import patch, AsyncMock
import json
from datetime import datetime, timezone

from tools.tests.base_test import BaseApiTest, TestMode
from tools.tests.test_data import TestDataGood, TestDataBad, TestDataError
from tools.tests.test_helpers import (
    FieldValidator,
    validate_field,
    validate_list_field,
    validate_money_field,
    assert_api_response_success
)
from tools.shipping_api import (
    calculate_shipping_costs,
    compare_shipping_strategies,
    ShippingCalculationInput,
    _generate_pricing_recommendations,
    _should_offer_free_shipping,
    _estimate_conversion_impact
)
from api.errors import EbayApiError


class TestShippingApi(BaseApiTest):
    """Test Shipping API functions in both unit and integration modes."""
    
    # ==============================================================================
    # Helper Function Tests (Unit tests only)
    # ==============================================================================
    
    @TestMode.skip_in_integration("Helper function is unit test only")
    def test_generate_pricing_recommendations(self):
        """Test pricing recommendations generation."""
        # Test with low shipping cost
        shipping_options = [{"service_name": "Standard", "shipping_cost": {"value": 3.99}}]
        recommendations = _generate_pricing_recommendations(shipping_options, 3.99)
        
        assert recommendations["include_shipping_in_price"] is True  # Low cost, include it
        assert recommendations["recommended_handling_fee"] == 0.0
        assert recommendations["total_shipping_cost"] == 3.99
        assert recommendations["competitiveness"] == "high"
        
        # Test with high shipping cost
        high_options = [{"service_name": "Express", "shipping_cost": {"value": 25.00}}]
        high_recommendations = _generate_pricing_recommendations(high_options, 25.00)
        
        assert high_recommendations["include_shipping_in_price"] is False  # High cost, show separately
        assert high_recommendations["recommended_handling_fee"] == 0.99
        assert high_recommendations["competitiveness"] == "low"
    
    @TestMode.skip_in_integration("Helper function is unit test only")
    def test_should_offer_free_shipping(self):
        """Test free shipping logic."""
        # Should offer free shipping if item price is high relative to shipping
        assert _should_offer_free_shipping(100.0, 10.0) is True  # 100 > 10*5
        assert _should_offer_free_shipping(40.0, 10.0) is False  # 40 < 10*5
        assert _should_offer_free_shipping(50.0, 5.0) is True  # 50 > 5*5
    
    @TestMode.skip_in_integration("Input validation is unit test only")
    def test_shipping_calculation_input_validation(self):
        """Test shipping calculation input validation."""
        # Valid input
        valid_input = ShippingCalculationInput(
            item_id="v1|123456789|0",
            destination_country="US",
            destination_postal_code="10001",
            quantity=1
        )
        assert valid_input.item_id == "v1|123456789|0"
        assert valid_input.destination_country == "US"
        
        # Empty item ID
        with pytest.raises(ValueError, match="Item ID cannot be empty"):
            ShippingCalculationInput(
                item_id="",
                destination_postal_code="10001"
            )
        
        # Invalid country code
        with pytest.raises(ValueError, match="Country code must be 2 characters"):
            ShippingCalculationInput(
                item_id="123",
                destination_country="USA",  # Should be "US"
                destination_postal_code="10001"
            )
        
        # Empty postal code
        with pytest.raises(ValueError, match="Postal code cannot be empty"):
            ShippingCalculationInput(
                item_id="123",
                destination_postal_code=""
            )
    
    # ==============================================================================
    # Calculate Shipping Costs Tests (Both unit and integration)
    # ==============================================================================
    
    @pytest.mark.asyncio
    async def test_calculate_shipping_costs_basic(self, mock_context, mock_credentials):
        """Test basic shipping cost calculation."""
        if self.is_integration_mode:
            # Integration test - real API call
            # Note: Requires a valid item ID
            result = await calculate_shipping_costs.fn(
                ctx=mock_context,
                item_id="v1|123456789|0",  # May need real item ID
                destination_postal_code="10001",
                destination_country="US",
                quantity=1
            )
            
            # Parse response
            data = json.loads(result)
            
            # Shopping API might not work in sandbox or without special setup
            if data["status"] == "success":
                validate_field(data["data"], "item_id", str)
                validate_field(data["data"], "destination", str)
                validate_list_field(data["data"], "shipping_options")
                validate_field(data["data"], "pricing_recommendations", dict)
                
                # Check shipping options
                if data["data"]["shipping_options"]:
                    for option in data["data"]["shipping_options"]:
                        validate_field(option, "service_name", str)
                        validate_field(option, "shipping_cost", dict)
                        validate_field(option["shipping_cost"], "value", (int, float))
        else:
            # Unit test - mocked response
            with patch('tools.shipping_api.EbayRestClient') as MockClient:
                mock_client = MockClient.return_value
                mock_client.get = AsyncMock(return_value={
                    "ShippingCostSummary": {
                        "ShippingServiceCost": {
                            "value": "8.95",
                            "currencyID": "USD"
                        },
                        "ShippingServiceName": "USPS Priority Mail",
                        "ExpeditedShipping": {
                            "value": "24.95"
                        }
                    }
                })
                mock_client.close = AsyncMock()
                
                with patch('tools.shipping_api.mcp.config.app_id', mock_credentials["app_id"]), \
                     patch('tools.shipping_api.mcp.config.cert_id', mock_credentials["cert_id"]):
                    
                    result = await calculate_shipping_costs.fn(
                        ctx=mock_context,
                        item_id="v1|123456789|0",
                        destination_postal_code="10001",
                        quantity=1
                    )
                    
                    data = assert_api_response_success(result)
                    
                    # Validate response structure
                    assert data["data"]["item_id"] == "v1|123456789|0"
                    assert data["data"]["destination"] == "10001, US"
                    assert len(data["data"]["shipping_options"]) == 2  # Standard + Expedited
                    
                    # Check standard shipping
                    standard = data["data"]["shipping_options"][0]
                    assert standard["service_name"] == "Standard Shipping"
                    assert standard["shipping_cost"]["value"] == 8.95
                    assert standard["shipping_cost"]["currency"] == "USD"
                    
                    # Check recommendations
                    recommendations = data["data"]["pricing_recommendations"]
                    assert recommendations["total_shipping_cost"] == 8.95
                    assert recommendations["competitiveness"] == "medium"
                    
                    # Verify API was called correctly
                    mock_client.get.assert_called_once()
                    call_args = mock_client.get.call_args
                    assert call_args[1]["params"]["ItemID"] == "v1|123456789|0"
                    assert call_args[1]["params"]["DestinationPostalCode"] == "10001"
    
    @pytest.mark.asyncio
    async def test_calculate_shipping_costs_multiple_quantity(self, mock_context, mock_credentials):
        """Test shipping calculation with multiple quantities."""
        if self.is_integration_mode:
            # Skip detailed integration test
            return
        else:
            # Unit test
            with patch('tools.shipping_api.EbayRestClient') as MockClient:
                mock_client = MockClient.return_value
                mock_client.get = AsyncMock(return_value={
                    "ShippingCostSummary": {
                        "ShippingServiceCost": {
                            "value": "15.95",  # Higher for multiple items
                            "currencyID": "USD"
                        }
                    }
                })
                mock_client.close = AsyncMock()
                
                with patch('tools.shipping_api.mcp.config.app_id', mock_credentials["app_id"]), \
                     patch('tools.shipping_api.mcp.config.cert_id', mock_credentials["cert_id"]):
                    
                    result = await calculate_shipping_costs.fn(
                        ctx=mock_context,
                        item_id="v1|123456789|0",
                        destination_postal_code="90210",
                        quantity=5
                    )
                    
                    data = assert_api_response_success(result)
                    
                    assert data["data"]["quantity"] == 5
                    assert data["data"]["shipping_options"][0]["shipping_cost"]["value"] == 15.95
                    
                    # Verify quantity was passed
                    call_params = mock_client.get.call_args[1]["params"]
                    assert call_params["QuantitySold"] == 5
    
    # ==============================================================================
    # Compare Shipping Strategies Tests
    # ==============================================================================
    
    @pytest.mark.asyncio
    async def test_compare_shipping_strategies_basic(self, mock_context, mock_credentials):
        """Test shipping strategy comparison."""
        if self.is_integration_mode:
            # Integration test
            result = await compare_shipping_strategies.fn(
                ctx=mock_context,
                item_price=50.0,
                item_id="v1|123456789|0"
            )
            
            data = json.loads(result)
            
            if data["status"] == "success":
                validate_field(data["data"], "item_price", (int, float))
                validate_field(data["data"], "strategy_analysis", dict)
                validate_field(data["data"]["strategy_analysis"], "recommended_strategy", str)
        else:
            # Unit test
            with patch('tools.shipping_api.calculate_shipping_costs.fn') as mock_calc:
                # Mock shipping calculations for different destinations
                mock_calc.side_effect = [
                    json.dumps({
                        "status": "success",
                        "data": {
                            "shipping_options": [{
                                "shipping_cost": {"value": 5.99, "currency": "USD"}
                            }]
                        }
                    }),
                    json.dumps({
                        "status": "success",
                        "data": {
                            "shipping_options": [{
                                "shipping_cost": {"value": 8.99, "currency": "USD"}
                            }]
                        }
                    }),
                    json.dumps({
                        "status": "success",
                        "data": {
                            "shipping_options": [{
                                "shipping_cost": {"value": 12.99, "currency": "USD"}
                            }]
                        }
                    })
                ]
                
                with patch('tools.shipping_api.mcp.config.app_id', mock_credentials["app_id"]), \
                     patch('tools.shipping_api.mcp.config.cert_id', mock_credentials["cert_id"]):
                    
                    result = await compare_shipping_strategies.fn(
                        ctx=mock_context,
                        item_price=50.0,
                        item_id="v1|123456789|0"
                    )
                    
                    data = assert_api_response_success(result)
                    
                    assert data["data"]["item_price"] == 50.0
                    assert "strategy_analysis" in data["data"]
                    assert "recommended_strategy" in data["data"]["strategy_analysis"]
                    
                    # Should have tested multiple destinations
                    assert mock_calc.call_count >= 3
    
    # ==============================================================================
    # Error Handling Tests
    # ==============================================================================
    
    @pytest.mark.asyncio
    async def test_calculate_shipping_costs_error_handling(self, mock_context, mock_credentials):
        """Test error handling in shipping calculation."""
        if self.is_integration_mode:
            # Test with invalid input
            result = await calculate_shipping_costs.fn(
                ctx=mock_context,
                item_id="",  # Empty ID
                destination_postal_code="10001"
            )
            
            data = json.loads(result)
            assert data["status"] == "error"
            assert data["error_code"] == "VALIDATION_ERROR"
        else:
            # Unit test error handling
            with patch('tools.shipping_api.EbayRestClient') as MockClient:
                mock_client = MockClient.return_value
                mock_client.get = AsyncMock(side_effect=EbayApiError(
                    status_code=404,
                    error_response=TestDataError.ERROR_NOT_FOUND
                ))
                mock_client.close = AsyncMock()
                
                with patch('tools.shipping_api.mcp.config.app_id', mock_credentials["app_id"]), \
                     patch('tools.shipping_api.mcp.config.cert_id', mock_credentials["cert_id"]):
                    
                    result = await calculate_shipping_costs.fn(
                        ctx=mock_context,
                        item_id="invalid-item",
                        destination_postal_code="10001"
                    )
                    
                    data = json.loads(result)
                    assert data["status"] == "error"
                    assert data["error_code"] == "EXTERNAL_API_ERROR"
    
    # ==============================================================================
    # Static Fallback Tests
    # ==============================================================================
    
    @pytest.mark.asyncio
    async def test_calculate_shipping_costs_no_credentials(self, mock_context):
        """Test shipping calculation with no credentials uses static estimate."""
        with patch('tools.shipping_api.mcp.config.app_id', ''), \
             patch('tools.shipping_api.mcp.config.cert_id', ''):
            
            result = await calculate_shipping_costs.fn(
                ctx=mock_context,
                item_id="v1|123456789|0",
                destination_postal_code="10001"
            )
            
            data = assert_api_response_success(result)
            # Static fallback returns estimate
            assert data["data"]["data_source"] == "static_estimate"
            assert len(data["data"]["shipping_options"]) == 1
            
            # Check static shipping option
            static_option = data["data"]["shipping_options"][0]
            assert static_option["service_name"] == "Standard Shipping"
            assert static_option["shipping_cost"]["value"] == 4.99
            assert "note" in data["data"]