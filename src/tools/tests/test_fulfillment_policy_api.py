"""
Test Fulfillment Policy API in both unit and integration modes.

FOLLOWS: DUAL-MODE TESTING METHODOLOGY from PRP
- Unit Mode: Complete mocking, validates interface contracts and Pydantic models
- Integration Mode: Real API calls, validates actual responses and OAuth handling

Run unit tests: pytest src/tools/tests/test_fulfillment_policy_api.py --test-mode=unit
Run integration tests: pytest src/tools/tests/test_fulfillment_policy_api.py --test-mode=integration
"""

import pytest
import json
from unittest.mock import AsyncMock, patch
from pydantic import ValidationError

from tools.tests.base_test import BaseApiTest
from tools.tests.test_data import TestDataFulfillmentPolicy
from tools.fulfillment_policy_api import (
    create_fulfillment_policy,
    get_fulfillment_policies,
    get_fulfillment_policy,
    get_fulfillment_policy_by_name,
    update_fulfillment_policy,
    delete_fulfillment_policy,
    FulfillmentPolicyInput,
    CategoryType,
    TimeDuration,
    ShippingOption,
    ShippingService,
    ShippingCost,
    RegionSet
)
from api.ebay_enums import (
    MarketplaceIdEnum,
    CategoryTypeEnum,
    ShippingCostTypeEnum,
    ShippingOptionTypeEnum,
    TimeDurationUnitEnum,
    CurrencyCodeEnum
)
from api.errors import EbayApiError


class TestFulfillmentPolicyPydanticModels:
    """Test Pydantic models validation (runs in both modes)."""
    
    def test_valid_simple_policy_creation(self):
        """Test complete valid policy with required fields only."""
        policy = FulfillmentPolicyInput(
            name="Test Fulfillment Policy",
            marketplace_id=MarketplaceIdEnum.EBAY_US,
            category_types=[CategoryType(name=CategoryTypeEnum.ALL_EXCLUDING_MOTORS_VEHICLES)]
        )
        assert policy.name == "Test Fulfillment Policy"
        assert policy.marketplace_id == MarketplaceIdEnum.EBAY_US
        assert len(policy.category_types) == 1
        assert policy.category_types[0].name == CategoryTypeEnum.ALL_EXCLUDING_MOTORS_VEHICLES
        assert policy.handling_time is None
        assert policy.shipping_options is None
    
    def test_valid_policy_with_handling_time(self):
        """Test policy with handling time configured."""
        policy = FulfillmentPolicyInput(
            name="Fast Handling Policy",
            marketplace_id=MarketplaceIdEnum.EBAY_US,
            category_types=[CategoryType(name=CategoryTypeEnum.ALL_EXCLUDING_MOTORS_VEHICLES)],
            handling_time=TimeDuration(value=1, unit=TimeDurationUnitEnum.DAY)
        )
        assert policy.handling_time is not None
        assert policy.handling_time.value == 1
        assert policy.handling_time.unit == TimeDurationUnitEnum.DAY
    
    def test_valid_complex_policy_with_shipping_options(self):
        """Test complex policy with shipping services."""
        domestic_service = ShippingService(
            shipping_service_code="StandardShipping",
            shipping_carrier_code="USPS",
            shipping_cost=ShippingCost(currency=CurrencyCodeEnum.USD, value="5.99"),
            additional_shipping_cost=ShippingCost(currency=CurrencyCodeEnum.USD, value="2.99"),
            free_shipping=False,
            sort_order=1
        )
        
        domestic_option = ShippingOption(
            cost_type=ShippingCostTypeEnum.FLAT_RATE,
            option_type=ShippingOptionTypeEnum.DOMESTIC,
            shipping_services=[domestic_service]
        )
        
        policy = FulfillmentPolicyInput(
            name="Complex Shipping Policy",
            marketplace_id=MarketplaceIdEnum.EBAY_US,
            category_types=[CategoryType(name=CategoryTypeEnum.ALL_EXCLUDING_MOTORS_VEHICLES)],
            handling_time=TimeDuration(value=2, unit=TimeDurationUnitEnum.DAY),
            shipping_options=[domestic_option],
            local_pickup=True,
            global_shipping=True
        )
        
        assert policy.shipping_options is not None
        assert len(policy.shipping_options) == 1
        assert policy.shipping_options[0].option_type == ShippingOptionTypeEnum.DOMESTIC
        assert policy.shipping_options[0].shipping_services is not None
        assert len(policy.shipping_options[0].shipping_services) == 1
        assert policy.shipping_options[0].shipping_services[0].shipping_service_code == "StandardShipping"
        assert policy.local_pickup is True
        assert policy.global_shipping is True
    
    def test_local_pickup_only_policy(self):
        """Test policy with only local pickup enabled."""
        policy = FulfillmentPolicyInput(
            name="Local Pickup Only",
            marketplace_id=MarketplaceIdEnum.EBAY_US,
            category_types=[CategoryType(name=CategoryTypeEnum.ALL_EXCLUDING_MOTORS_VEHICLES)],
            local_pickup=True,
            pickup_drop_off=True
        )
        assert policy.local_pickup is True
        assert policy.pickup_drop_off is True
        assert policy.handling_time is None
        assert policy.shipping_options is None
    
    def test_conditional_validation_handling_time_required_with_shipping(self):
        """Test that handling_time is required when shipping services are defined."""
        service = ShippingService(shipping_service_code="StandardShipping")
        option = ShippingOption(
            cost_type=ShippingCostTypeEnum.FLAT_RATE,
            option_type=ShippingOptionTypeEnum.DOMESTIC,
            shipping_services=[service]
        )
        
        with pytest.raises(ValidationError) as exc:
            FulfillmentPolicyInput(
                name="Invalid Policy",
                marketplace_id=MarketplaceIdEnum.EBAY_US,
                category_types=[CategoryType(name=CategoryTypeEnum.ALL_EXCLUDING_MOTORS_VEHICLES)],
                shipping_options=[option]
                # Missing handling_time!
            )
        
        error_str = str(exc.value)
        assert "handling_time is required when shipping services are defined" in error_str
    
    def test_shipping_service_limits_domestic(self):
        """Test domestic shipping service limit validation (max 4)."""
        services = [
            ShippingService(shipping_service_code=f"Service{i}") 
            for i in range(5)  # Too many!
        ]
        
        with pytest.raises(ValidationError) as exc:
            ShippingOption(
                cost_type=ShippingCostTypeEnum.FLAT_RATE,
                option_type=ShippingOptionTypeEnum.DOMESTIC,
                shipping_services=services
            )
        
        error_str = str(exc.value)
        assert "Maximum 4 domestic shipping services allowed" in error_str
    
    def test_shipping_service_limits_international(self):
        """Test international shipping service limit validation (max 5)."""
        services = [
            ShippingService(shipping_service_code=f"Service{i}") 
            for i in range(6)  # Too many!
        ]
        
        with pytest.raises(ValidationError) as exc:
            ShippingOption(
                cost_type=ShippingCostTypeEnum.FLAT_RATE,
                option_type=ShippingOptionTypeEnum.INTERNATIONAL,
                shipping_services=services
            )
        
        error_str = str(exc.value)
        assert "Maximum 5 international shipping services allowed" in error_str
    
    def test_validation_errors_show_enum_options(self):
        """Test that enum validation errors show all valid options."""
        with pytest.raises(ValidationError) as exc:
            FulfillmentPolicyInput(
                name="Test",
                marketplace_id="INVALID_MARKETPLACE",  # Wrong type
                category_types=[CategoryType(name=CategoryTypeEnum.ALL_EXCLUDING_MOTORS_VEHICLES)]
            )
        # Error should show all valid marketplace options
        error_str = str(exc.value)
        assert "EBAY_US" in error_str
        assert "EBAY_GB" in error_str
    
    def test_handling_time_value_limits(self):
        """Test handling time value validation (max 30 days)."""
        with pytest.raises(ValidationError):
            TimeDuration(value=31, unit=TimeDurationUnitEnum.DAY)  # Too many days
        
        with pytest.raises(ValidationError):
            TimeDuration(value=0, unit=TimeDurationUnitEnum.DAY)  # Zero not allowed
        
        # Valid values should work
        duration = TimeDuration(value=30, unit=TimeDurationUnitEnum.DAY)
        assert duration.value == 30


class TestFulfillmentPolicyApi(BaseApiTest):
    """Test Fulfillment Policy API in both unit and integration modes."""
    
    @pytest.mark.asyncio
    async def test_infrastructure_validation(self, mock_context):
        """CRITICAL: Validates integration infrastructure works before testing restricted APIs."""
        if not self.is_integration_mode:
            pytest.skip("Infrastructure validation only runs in integration mode")
        
        # Use Browse API to prove connectivity  
        from tools.browse_api import search_items
        print("Testing integration infrastructure with Browse API...")
        print("This API uses basic scope (no user consent required)")
        
        result = await search_items.fn(ctx=mock_context, query="iPhone", limit=1)
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
        
        print("Integration infrastructure is working correctly")
        print("Network, credentials, and basic API calls are functional")
        assert "data" in response
        items = response["data"].get("items", [])
        print(f"Retrieved {len(items)} items from eBay")
    
    @pytest.mark.asyncio
    async def test_create_fulfillment_policy_success(self, mock_context, mock_credentials):
        """Test successful fulfillment policy creation."""
        # Create valid input using Pydantic model
        policy_input = FulfillmentPolicyInput(
            name="Test Fulfillment Policy",
            marketplace_id=MarketplaceIdEnum.EBAY_US,
            category_types=[CategoryType(name=CategoryTypeEnum.ALL_EXCLUDING_MOTORS_VEHICLES)],
            handling_time=TimeDuration(value=1, unit=TimeDurationUnitEnum.DAY),
            description="Test fulfillment policy for unit/integration testing"
        )
        
        if self.is_integration_mode:
            # Integration test - real API call
            print("Step 1: Verify infrastructure is functional...")
            from tools.browse_api import search_items
            browse_result = await search_items.fn(ctx=mock_context, query="test", limit=1)
            browse_response = json.loads(browse_result)
            
            if browse_response["status"] != "success":
                pytest.fail("Infrastructure check failed - fix basic connectivity before testing OAuth")
            
            print("Infrastructure confirmed working")
            print("Step 2: Test OAuth scope enforcement...")
            
            # Test restricted API
            result = await create_fulfillment_policy.fn(
                ctx=mock_context,
                policy_input=policy_input
            )
            response = json.loads(result)
            
            # This SHOULD fail with auth error only
            if response["status"] != "error":
                pytest.fail("OAuth scope enforcement not working - API should require user consent")
            if response["error_code"] != "AUTHENTICATION_ERROR":
                pytest.fail(f"Unexpected error type: {response['error_code']} - expected AUTHENTICATION_ERROR")
            if "User consent required" not in response["error_message"]:
                pytest.fail(f"Wrong auth error: {response['error_message']} - should mention user consent")
            
            print("OAuth scope enforcement working correctly")
            print("sell.account scope properly requires user consent")
            
        else:
            # Unit test - mocked dependencies
            with patch('tools.fulfillment_policy_api.EbayRestClient') as MockClient, \
                 patch('tools.fulfillment_policy_api.OAuthManager') as MockOAuth, \
                 patch('tools.fulfillment_policy_api.mcp.config') as MockConfig:
                
                # Setup all mocks
                mock_client = MockClient.return_value
                mock_client.post.return_value = TestDataFulfillmentPolicy.CREATE_POLICY_RESPONSE
                mock_client.close = AsyncMock()
                MockConfig.app_id = "test_app"
                MockConfig.cert_id = "test_cert"
                MockConfig.sandbox_mode = True
                MockConfig.rate_limit_per_day = 5000
                
                # Test interface contracts and Pydantic validation
                result = await create_fulfillment_policy.fn(
                    ctx=mock_context,
                    policy_input=policy_input
                )
                
                # Verify mocked response processing
                response = json.loads(result)
                assert response["status"] == "success"
                assert "data" in response
                assert response["data"]["policy_id"] == "6197962000"
                assert response["data"]["name"] == "New Fulfillment Policy"
                mock_client.post.assert_called_once()
                mock_client.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_fulfillment_policies_success(self, mock_context, mock_credentials):
        """Test successful retrieval of fulfillment policies."""
        marketplace_id = MarketplaceIdEnum.EBAY_US
        
        if self.is_integration_mode:
            # Integration test - OAuth scope enforcement
            print("Testing OAuth scope enforcement for get_fulfillment_policies...")
            
            result = await get_fulfillment_policies.fn(
                ctx=mock_context,
                marketplace_id=marketplace_id,
                limit=10
            )
            response = json.loads(result)
            
            # Should fail with auth error
            if response["status"] != "error":
                pytest.fail("OAuth scope enforcement not working")
            if response["error_code"] != "AUTHENTICATION_ERROR":
                pytest.fail(f"Wrong error type: {response['error_code']}")
            
            print("OAuth scope enforcement confirmed for get_fulfillment_policies")
            
        else:
            # Unit test - mocked dependencies
            with patch('tools.fulfillment_policy_api.EbayRestClient') as MockClient, \
                 patch('tools.fulfillment_policy_api.OAuthManager') as MockOAuth, \
                 patch('tools.fulfillment_policy_api.mcp.config') as MockConfig:
                
                # Setup mocks
                mock_client = MockClient.return_value
                mock_client.get.return_value = TestDataFulfillmentPolicy.GET_POLICIES_RESPONSE
                mock_client.close = AsyncMock()
                MockConfig.app_id = "test_app"
                MockConfig.cert_id = "test_cert"
                MockConfig.sandbox_mode = True
                MockConfig.rate_limit_per_day = 5000
                
                result = await get_fulfillment_policies.fn(
                    ctx=mock_context,
                    marketplace_id=marketplace_id,
                    limit=10
                )
                
                response = json.loads(result)
                assert response["status"] == "success"
                assert "data" in response
                assert "policies" in response["data"]
                assert len(response["data"]["policies"]) == 3
                assert response["data"]["total"] == 3
                mock_client.get.assert_called_once()
                mock_client.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_fulfillment_policy_success(self, mock_context, mock_credentials):
        """Test successful retrieval of specific fulfillment policy."""
        policy_id = "6197932000"
        
        if self.is_integration_mode:
            # Integration test - OAuth scope enforcement
            result = await get_fulfillment_policy.fn(
                ctx=mock_context,
                policy_id=policy_id
            )
            response = json.loads(result)
            
            # Should fail with auth error
            assert response["status"] == "error"
            assert response["error_code"] == "AUTHENTICATION_ERROR"
            
        else:
            # Unit test - mocked dependencies
            with patch('tools.fulfillment_policy_api.EbayRestClient') as MockClient, \
                 patch('tools.fulfillment_policy_api.OAuthManager') as MockOAuth, \
                 patch('tools.fulfillment_policy_api.mcp.config') as MockConfig:
                
                # Setup mocks
                mock_client = MockClient.return_value
                mock_client.get.return_value = TestDataFulfillmentPolicy.FULFILLMENT_POLICY_SIMPLE
                mock_client.close = AsyncMock()
                MockConfig.app_id = "test_app"
                MockConfig.cert_id = "test_cert"
                MockConfig.sandbox_mode = True
                MockConfig.rate_limit_per_day = 5000
                
                result = await get_fulfillment_policy.fn(
                    ctx=mock_context,
                    policy_id=policy_id
                )
                
                response = json.loads(result)
                assert response["status"] == "success"
                assert "data" in response
                assert response["data"]["policy_id"] == "6197932000"
                assert response["data"]["name"] == "Standard Shipping"
                mock_client.get.assert_called_once_with(f"/sell/account/v1/fulfillment_policy/{policy_id}")
                mock_client.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_fulfillment_policy_by_name_success(self, mock_context, mock_credentials):
        """Test successful retrieval of fulfillment policy by name."""
        marketplace_id = MarketplaceIdEnum.EBAY_US
        policy_name = "Standard Shipping"
        
        if self.is_integration_mode:
            # Integration test - OAuth scope enforcement
            result = await get_fulfillment_policy_by_name.fn(
                ctx=mock_context,
                marketplace_id=marketplace_id,
                name=policy_name
            )
            response = json.loads(result)
            
            # Should fail with auth error
            assert response["status"] == "error"
            assert response["error_code"] == "AUTHENTICATION_ERROR"
            
        else:
            # Unit test - mocked dependencies
            with patch('tools.fulfillment_policy_api.EbayRestClient') as MockClient, \
                 patch('tools.fulfillment_policy_api.OAuthManager') as MockOAuth, \
                 patch('tools.fulfillment_policy_api.mcp.config') as MockConfig:
                
                # Setup mocks
                mock_client = MockClient.return_value
                mock_client.get.return_value = TestDataFulfillmentPolicy.GET_BY_NAME_RESPONSE
                mock_client.close = AsyncMock()
                MockConfig.app_id = "test_app"
                MockConfig.cert_id = "test_cert"
                MockConfig.sandbox_mode = True
                MockConfig.rate_limit_per_day = 5000
                
                result = await get_fulfillment_policy_by_name.fn(
                    ctx=mock_context,
                    marketplace_id=marketplace_id,
                    name=policy_name
                )
                
                response = json.loads(result)
                assert response["status"] == "success"
                assert "data" in response
                assert response["data"]["name"] == "Standard Shipping"
                
                # Verify correct parameters were passed
                expected_params = {
                    "marketplace_id": "EBAY_US",
                    "name": policy_name
                }
                mock_client.get.assert_called_once_with(
                    "/sell/account/v1/fulfillment_policy/get_by_policy_name",
                    params=expected_params
                )
                mock_client.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_fulfillment_policy_success(self, mock_context, mock_credentials):
        """Test successful fulfillment policy update."""
        policy_id = "6197932000"
        policy_input = FulfillmentPolicyInput(
            name="Updated Fulfillment Policy",
            marketplace_id=MarketplaceIdEnum.EBAY_US,
            category_types=[CategoryType(name=CategoryTypeEnum.ALL_EXCLUDING_MOTORS_VEHICLES)],
            description="Updated description"
        )
        
        if self.is_integration_mode:
            # Integration test - OAuth scope enforcement
            result = await update_fulfillment_policy.fn(
                ctx=mock_context,
                policy_id=policy_id,
                policy_input=policy_input
            )
            response = json.loads(result)
            
            # Should fail with auth error
            assert response["status"] == "error"
            assert response["error_code"] == "AUTHENTICATION_ERROR"
            
        else:
            # Unit test - mocked dependencies
            with patch('tools.fulfillment_policy_api.EbayRestClient') as MockClient, \
                 patch('tools.fulfillment_policy_api.OAuthManager') as MockOAuth, \
                 patch('tools.fulfillment_policy_api.mcp.config') as MockConfig:
                
                # Setup mocks
                mock_client = MockClient.return_value
                mock_client.put.return_value = TestDataFulfillmentPolicy.UPDATE_POLICY_RESPONSE
                mock_client.close = AsyncMock()
                MockConfig.app_id = "test_app"
                MockConfig.cert_id = "test_cert"
                MockConfig.sandbox_mode = True
                MockConfig.rate_limit_per_day = 5000
                
                result = await update_fulfillment_policy.fn(
                    ctx=mock_context,
                    policy_id=policy_id,
                    policy_input=policy_input
                )
                
                response = json.loads(result)
                assert response["status"] == "success"
                assert "data" in response
                assert response["data"]["name"] == "Updated Fulfillment Policy"
                mock_client.put.assert_called_once()
                mock_client.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_fulfillment_policy_success(self, mock_context, mock_credentials):
        """Test successful fulfillment policy deletion."""
        policy_id = "6197932000"
        
        if self.is_integration_mode:
            # Integration test - OAuth scope enforcement
            result = await delete_fulfillment_policy.fn(
                ctx=mock_context,
                policy_id=policy_id
            )
            response = json.loads(result)
            
            # Should fail with auth error
            assert response["status"] == "error"
            assert response["error_code"] == "AUTHENTICATION_ERROR"
            
        else:
            # Unit test - mocked dependencies
            with patch('tools.fulfillment_policy_api.EbayRestClient') as MockClient, \
                 patch('tools.fulfillment_policy_api.OAuthManager') as MockOAuth, \
                 patch('tools.fulfillment_policy_api.mcp.config') as MockConfig:
                
                # Setup mocks
                mock_client = MockClient.return_value
                mock_client.delete.return_value = None  # Delete returns no content
                mock_client.close = AsyncMock()
                MockConfig.app_id = "test_app"
                MockConfig.cert_id = "test_cert"
                MockConfig.sandbox_mode = True
                MockConfig.rate_limit_per_day = 5000
                
                result = await delete_fulfillment_policy.fn(
                    ctx=mock_context,
                    policy_id=policy_id
                )
                
                response = json.loads(result)
                assert response["status"] == "success"
                assert "data" in response
                assert response["data"]["policy_id"] == policy_id
                assert response["data"]["deleted"] is True
                mock_client.delete.assert_called_once_with(f"/sell/account/v1/fulfillment_policy/{policy_id}")
                mock_client.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_validation_errors(self, mock_context, mock_credentials):
        """Test validation error handling."""
        # Test empty policy_id
        result = await get_fulfillment_policy.fn(
            ctx=mock_context,
            policy_id=""
        )
        response = json.loads(result)
        assert response["status"] == "error"
        assert response["error_code"] == "VALIDATION_ERROR"
        assert "policy_id is required" in response["error_message"]
        
        # Test empty name
        result = await get_fulfillment_policy_by_name.fn(
            ctx=mock_context,
            marketplace_id=MarketplaceIdEnum.EBAY_US,
            name=""
        )
        response = json.loads(result)
        assert response["status"] == "error"
        assert response["error_code"] == "VALIDATION_ERROR"
        assert "name is required" in response["error_message"]
    
    @pytest.mark.asyncio
    async def test_configuration_errors(self, mock_context):
        """Test configuration error handling."""
        with patch('tools.fulfillment_policy_api.mcp.config') as MockConfig:
            MockConfig.app_id = None
            MockConfig.cert_id = None
            
            policy_input = FulfillmentPolicyInput(
                name="Test Policy",
                marketplace_id=MarketplaceIdEnum.EBAY_US,
                category_types=[CategoryType(name=CategoryTypeEnum.ALL_EXCLUDING_MOTORS_VEHICLES)]
            )
            
            result = await create_fulfillment_policy.fn(
                ctx=mock_context,
                policy_input=policy_input
            )
            
            response = json.loads(result)
            assert response["status"] == "error"
            assert response["error_code"] == "CONFIGURATION_ERROR"
            assert "eBay App ID and Cert ID must be configured" in response["error_message"]
    
    @pytest.mark.asyncio
    async def test_ebay_api_errors(self, mock_context, mock_credentials):
        """Test eBay API error handling in unit mode."""
        if self.is_integration_mode:
            pytest.skip("eBay API error simulation only in unit mode")
        
        with patch('tools.fulfillment_policy_api.EbayRestClient') as MockClient, \
             patch('tools.fulfillment_policy_api.OAuthManager') as MockOAuth, \
             patch('tools.fulfillment_policy_api.mcp.config') as MockConfig:
            
            # Setup mocks with API error
            mock_client = MockClient.return_value
            mock_client.get.side_effect = EbayApiError("Policy not found", 404)
            mock_client.close = AsyncMock()
            MockConfig.app_id = "test_app"
            MockConfig.cert_id = "test_cert"
            MockConfig.sandbox_mode = True
            MockConfig.rate_limit_per_day = 5000
            
            result = await get_fulfillment_policy.fn(
                ctx=mock_context,
                policy_id="nonexistent"
            )
            
            response = json.loads(result)
            assert response["status"] == "error"
            assert response["error_code"] == "EXTERNAL_API_ERROR"
            assert "Policy not found" in response["error_message"]
            assert response["details"]["status_code"] == 404
            mock_client.close.assert_called_once()