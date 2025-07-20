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
from lootly_server import mcp
from tools.tests.test_data import TestDataFulfillmentPolicy
from tools.fulfillment_policy_api import (
    create_fulfillment_policy,
    get_fulfillment_policies,
    get_fulfillment_policy,
    get_fulfillment_policy_by_name,
    update_fulfillment_policy,
    delete_fulfillment_policy
)
from models.policies import (
    FulfillmentPolicyInput,
    ShippingOption,
    ShippingService
)
from models.common import (
    CategoryType,
    TimeDuration,
    Amount
)
from models.enums import (
    MarketplaceIdEnum,
    CategoryTypeEnum,
    ShippingCostTypeEnum,
    ShippingOptionTypeEnum,
    TimeDurationUnitEnum,
    CurrencyCodeEnum,
)
from models.shipping_enums import DomesticShippingServiceEnum, InternationalShippingServiceEnum
from api.errors import EbayApiError

class TestFulfillmentPolicyPydanticModels:
    """Test Pydantic models validation (runs in both modes)."""
    
    def test_valid_simple_policy_creation(self):
        """Test complete valid policy with required fields only."""
        policy = FulfillmentPolicyInput(
            name="Test Fulfillment Policy",
            marketplaceId=MarketplaceIdEnum.EBAY_US,
            categoryTypes=[CategoryType(name=CategoryTypeEnum.ALL_EXCLUDING_MOTORS_VEHICLES)]
        )
        assert policy.name == "Test Fulfillment Policy"
        assert policy.marketplaceId == MarketplaceIdEnum.EBAY_US
        assert len(policy.categoryTypes) == 1
        assert policy.categoryTypes[0].name == CategoryTypeEnum.ALL_EXCLUDING_MOTORS_VEHICLES
        assert policy.handlingTime is None
        assert policy.shippingOptions is None
    
    def test_valid_policy_with_handlingTime(self):
        """Test policy with handling time configured."""
        policy = FulfillmentPolicyInput(
            name="Fast Handling Policy",
            marketplaceId=MarketplaceIdEnum.EBAY_US,
            categoryTypes=[CategoryType(name=CategoryTypeEnum.ALL_EXCLUDING_MOTORS_VEHICLES)],
            handlingTime=TimeDuration(value=1, unit=TimeDurationUnitEnum.DAY)
        )
        assert policy.handlingTime is not None
        assert policy.handlingTime.value == 1
        assert policy.handlingTime.unit == TimeDurationUnitEnum.DAY
    
    def test_valid_complex_policy_with_shipping_options(self):
        """Test complex policy with shipping services."""
        domestic_service = ShippingService(
            shippingServiceCode=DomesticShippingServiceEnum.USPSPriority,
            shippingCarrierCode=DomesticShippingServiceEnum.USPSPriority,
            shippingCost=Amount(currency=CurrencyCodeEnum.USD, value="5.99"),
            additionalShippingCost=Amount(currency=CurrencyCodeEnum.USD, value="2.99"),
            freeShipping=False,
            sortOrder=1
        )
        
        domestic_option = ShippingOption(
            costType=ShippingCostTypeEnum.FLAT_RATE,
            optionType=ShippingOptionTypeEnum.DOMESTIC,
            shippingServices=[domestic_service]
        )
        
        policy = FulfillmentPolicyInput(
            name="Complex Shipping Policy",
            marketplaceId=MarketplaceIdEnum.EBAY_US,
            categoryTypes=[CategoryType(name=CategoryTypeEnum.ALL_EXCLUDING_MOTORS_VEHICLES)],
            handlingTime=TimeDuration(value=2, unit=TimeDurationUnitEnum.DAY),
            shippingOptions=[domestic_option],
            localPickup=True,
            globalShipping=True
        )
        
        assert policy.shippingOptions is not None
        assert len(policy.shippingOptions) == 1
        assert policy.shippingOptions[0].optionType == ShippingOptionTypeEnum.DOMESTIC
        assert policy.shippingOptions[0].shippingServices is not None
        assert len(policy.shippingOptions[0].shippingServices) == 1
        assert policy.shippingOptions[0].shippingServices[0].shippingServiceCode == DomesticShippingServiceEnum.USPSPriority
        assert policy.localPickup is True
        assert policy.globalShipping is True
    
    def test_local_pickup_only_policy(self):
        """Test policy with only local pickup enabled."""
        policy = FulfillmentPolicyInput(
            name="Local Pickup Only",
            marketplaceId=MarketplaceIdEnum.EBAY_US,
            categoryTypes=[CategoryType(name=CategoryTypeEnum.ALL_EXCLUDING_MOTORS_VEHICLES)],
            localPickup=True,
            pickupDropOff=False
        )
        assert policy.localPickup is True
        assert policy.pickupDropOff == False
        assert policy.handlingTime is None
        assert policy.shippingOptions is None
    
    def test_conditional_validation_handlingTime_required_with_shipping(self):
        """Test that shipping services can be defined without handlingTime (optional requirement)."""
        service = ShippingService(shippingServiceCode=DomesticShippingServiceEnum.USPSPriority)
        option = ShippingOption(
            costType=ShippingCostTypeEnum.FLAT_RATE,
            optionType=ShippingOptionTypeEnum.DOMESTIC,
            shippingServices=[service]
        )
        
        # This should be allowed - handlingTime is optional even with shipping services
        policy = FulfillmentPolicyInput(
            name="Valid Policy",
            marketplaceId=MarketplaceIdEnum.EBAY_US,
            categoryTypes=[CategoryType(name=CategoryTypeEnum.ALL_EXCLUDING_MOTORS_VEHICLES)],
            shippingOptions=[option]
            # handlingTime is optional
        )
        
        assert policy.name == "Valid Policy"
        assert policy.handlingTime is None
    
    def test_shipping_service_limits_domestic(self):
        """Test domestic shipping service limit validation (max 4)."""
        services = [
            ShippingService(shippingServiceCode=DomesticShippingServiceEnum.USPSPriority) 
            for i in range(5)  # Too many!
        ]
        
        with pytest.raises(ValidationError) as exc:
            ShippingOption(
                costType=ShippingCostTypeEnum.FLAT_RATE,
                optionType=ShippingOptionTypeEnum.DOMESTIC,
                shippingServices=services
            )
        
        error_str = str(exc.value)
        assert "Maximum 4 shipping services allowed for DOMESTIC" in error_str
    
    def test_shipping_service_limits_international(self):
        """Test international shipping service limit validation (max 5)."""
        services = [
            ShippingService(shippingServiceCode=DomesticShippingServiceEnum.USPSPriority) 
            for i in range(6)  # Too many!
        ]
        
        with pytest.raises(ValidationError) as exc:
            ShippingOption(
                costType=ShippingCostTypeEnum.FLAT_RATE,
                optionType=ShippingOptionTypeEnum.INTERNATIONAL,
                shippingServices=services
            )
        
        error_str = str(exc.value)
        assert "Maximum 5 shipping services allowed for INTERNATIONAL" in error_str
    
    def test_validation_errors_show_enum_options(self):
        """Test that enum validation errors show all valid options."""
        with pytest.raises(ValidationError) as exc:
            FulfillmentPolicyInput(
                name="Test",
                marketplaceId="INVALID_MARKETPLACE",  # Wrong type
                categoryTypes=[CategoryType(name=CategoryTypeEnum.ALL_EXCLUDING_MOTORS_VEHICLES)]
            )
        # Error should show all valid marketplace options
        error_str = str(exc.value)
        assert "EBAY_US" in error_str
        assert "EBAY_UK" in error_str  # Updated to match actual enum value
    
    def test_handlingTime_value_limits(self):
        """Test handling time value validation (max 30 days)."""
        # Test through FulfillmentPolicyInput where the validation occurs
        with pytest.raises(ValidationError) as exc:
            FulfillmentPolicyInput(
                name="Test Policy",
                marketplaceId=MarketplaceIdEnum.EBAY_US,
                categoryTypes=[CategoryType(name=CategoryTypeEnum.ALL_EXCLUDING_MOTORS_VEHICLES)],
                handlingTime=TimeDuration(value=31, unit=TimeDurationUnitEnum.DAY)  # Too many days
            )
        assert "Handling time cannot exceed 30 days" in str(exc.value)
        
        # Zero not allowed (TimeDuration has gt=0 constraint)
        with pytest.raises(ValidationError):
            TimeDuration(value=0, unit=TimeDurationUnitEnum.DAY)
        
        # Valid values should work
        policy = FulfillmentPolicyInput(
            name="Test Policy",
            marketplaceId=MarketplaceIdEnum.EBAY_US,
            categoryTypes=[CategoryType(name=CategoryTypeEnum.ALL_EXCLUDING_MOTORS_VEHICLES)],
            handlingTime=TimeDuration(value=30, unit=TimeDurationUnitEnum.DAY)
        )
        assert policy.handlingTime.value == 30


class TestFulfillmentPolicyApi(BaseApiTest):
    """Test Fulfillment Policy API in both unit and integration modes."""
    
    @pytest.mark.asyncio
    async def test_infrastructure_validation(self, mock_context):
        """CRITICAL: Validates integration infrastructure works before testing restricted APIs."""
        if not self.is_integration_mode:
            pytest.skip("Infrastructure validation only runs in integration mode")
        
        # Use Browse API to prove connectivity  
        from tools.browse_api import search_items, BrowseSearchInput
        print("Testing integration infrastructure with Browse API...")
        print("This API uses basic scope (no user consent required)")
        
        search_input = BrowseSearchInput(q="iPhone", limit=1)
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
        
        print("Integration infrastructure is working correctly")
        print("Network, credentials, and basic API calls are functional")
        assert "data" in response
        items = response["data"].get("items", [])
        print(f"Retrieved {len(items)} items from eBay")
    
    @pytest.mark.asyncio
    async def test_create_fulfillment_policy_simple(self, mock_context, mock_credentials):
        """Test successful fulfillment policy creation."""
        # Create valid input using Pydantic test data factory
        policy_input = TestDataFulfillmentPolicy.create_simple_policy(
            name="Test Fulfillment Policy"
        )
        
        if self.is_integration_mode:
            # Integration test - real API call
            
            # Test restricted API
            result = await create_fulfillment_policy.fn(
                ctx=mock_context,
                policy_input=policy_input
            )
            response = json.loads(result)
            
            if response["status"] == "error":
                error_code = response["error_code"]
                error_msg = response["error_message"]
                response.get("details", {}).get("status_code")
                errors = response.get("details", {}).get("errors", [])
                
                # Check if we're in sandbox mode
                is_sandbox = mcp.config.sandbox_mode
                
                # Only skip for known sandbox limitations when actually in sandbox mode
                if is_sandbox:
                    # Business Policy Eligibility Issues
                    if any(e.get("error_id") in [20403, 20001] for e in errors):
                        # Check error message and parameters for Business Policy eligibility
                        if ("not eligible for Business Policy" in error_msg or 
                            "not opted in to business policies" in error_msg or
                            "not BP opted in" in error_msg or
                            "seller profile ID is not valid" in error_msg):
                            pytest.skip(f"Known eBay sandbox limitation: Business Policy eligibility - {error_msg}")
                    # Policy already exists
                    elif any(e.get("error_id") == 20400 for e in errors):
                        pytest.skip(f"Known eBay sandbox limitation: Policy already exists - {error_msg}")
                
                # For production or unexpected sandbox errors - fail the test
                if error_code == "CONFIGURATION_ERROR":
                    pytest.fail(f"CREDENTIALS PROBLEM: {error_msg} - {response}")
                elif error_code == "EXTERNAL_API_ERROR":
                    pytest.fail(f"eBay API CONNECTIVITY ISSUE: {error_msg} - {response}")
                else:
                    pytest.fail(f"UNEXPECTED INFRASTRUCTURE ISSUE: {error_code} - {error_msg} - {response}")
            
            assert response["status"] == "success"
            
            # Store the created policy ID in runtime data for later tests
            if "data" in response and response["data"].get("fulfillmentPolicyId"):
                TestDataFulfillmentPolicy.store_policy_id(
                    policy_input.name,
                    response["data"]["fulfillmentPolicyId"]
                )

        else:
            # Unit test - mocked dependencies
            with patch('tools.fulfillment_policy_api.EbayRestClient') as MockClient, \
                 patch('tools.fulfillment_policy_api.OAuthManager'), \
                 patch('tools.fulfillment_policy_api.mcp.config') as MockConfig:
                
                # Setup all mocks
                mock_client = MockClient.return_value
                # Convert Pydantic model to expected API response
                expected_response = TestDataFulfillmentPolicy.policy_to_api_response(
                    policy_input, 
                    policy_id="6197962000"
                )
                # Mock the post method to return body and headers
                mock_client.post = AsyncMock(return_value={
                    "body": expected_response,
                    "headers": {
                        "Location": "/sell/account/v1/fulfillment_policy/6197962000",
                        "X-EBAY-C-REQUEST-ID": "test-request-id"
                    }
                })
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
                if response["status"] == "error":
                    print(f"Error response: {response}")
                assert response["status"] == "success"
                assert "data" in response
                assert response["data"]["fulfillmentPolicyId"] == "6197962000"
                assert response["data"]["name"] == policy_input.name
                assert "metadata" in response
                assert response["metadata"]["location_url"] == "/sell/account/v1/fulfillment_policy/6197962000"
                mock_client.post.assert_called_once()
                mock_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_fulfillment_policy_complex(self, mock_context, mock_credentials):
        """Test successful fulfillment policy creation."""
        # Create valid input using Pydantic test data factory
        policy_input = TestDataFulfillmentPolicy.create_complex_policy(
            name="Test Complex Fulfillment Policy"
        )
        
        if self.is_integration_mode:
            # Integration test - real API call
            
            # Test restricted API
            result = await create_fulfillment_policy.fn(
                ctx=mock_context,
                policy_input=policy_input
            )
            response = json.loads(result)
            
            if response["status"] == "error":
                error_code = response["error_code"]
                error_msg = response["error_message"]
                response.get("details", {}).get("status_code")
                errors = response.get("details", {}).get("errors", [])
                
                # Check if we're in sandbox mode
                is_sandbox = mcp.config.sandbox_mode
                
                # Only skip for known sandbox limitations when actually in sandbox mode
                if is_sandbox:
                    # Business Policy Eligibility Issues
                    if any(e.get("error_id") in [20403, 20001] for e in errors):
                        # Check error message and parameters for Business Policy eligibility
                        if ("not eligible for Business Policy" in error_msg or 
                            "not opted in to business policies" in error_msg or
                            "not BP opted in" in error_msg or
                            "seller profile ID is not valid" in error_msg):
                            pytest.skip(f"Known eBay sandbox limitation: Business Policy eligibility - {error_msg}")
                    # Policy already exists
                    elif any(e.get("error_id") == 20400 for e in errors):
                        pytest.skip(f"Known eBay sandbox limitation: Policy already exists - {error_msg}")
                
                # For production or unexpected sandbox errors - fail the test
                if error_code == "CONFIGURATION_ERROR":
                    pytest.fail(f"CREDENTIALS PROBLEM: {error_msg} - {response}")
                elif error_code == "EXTERNAL_API_ERROR":
                    pytest.fail(f"eBay API CONNECTIVITY ISSUE: {error_msg} - {response}")
                else:
                    pytest.fail(f"UNEXPECTED INFRASTRUCTURE ISSUE: {error_code} - {error_msg} - {response}")
            
            assert response["status"] == "success"
            
            # Store the created policy ID in runtime data for later tests
            if "data" in response and response["data"].get("fulfillmentPolicyId"):
                TestDataFulfillmentPolicy.store_policy_id(
                    policy_input.name,
                    response["data"]["fulfillmentPolicyId"]
                )

        else:
            # Unit test - mocked dependencies
            with patch('tools.fulfillment_policy_api.EbayRestClient') as MockClient, \
                 patch('tools.fulfillment_policy_api.OAuthManager'), \
                 patch('tools.fulfillment_policy_api.mcp.config') as MockConfig:
                
                # Setup all mocks
                mock_client = MockClient.return_value
                # Convert Pydantic model to expected API response
                expected_response = TestDataFulfillmentPolicy.policy_to_api_response(
                    policy_input, 
                    policy_id="6197962000"
                )
                # Mock the post method to return body and headers
                mock_client.post = AsyncMock(return_value={
                    "body": expected_response,
                    "headers": {
                        "Location": "/sell/account/v1/fulfillment_policy/6197962000",
                        "X-EBAY-C-REQUEST-ID": "test-request-id"
                    }
                })
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
                if response["status"] == "error":
                    print(f"Error response: {response}")
                assert response["status"] == "success"
                assert "data" in response
                assert response["data"]["fulfillmentPolicyId"] == "6197962000"
                assert response["data"]["name"] == policy_input.name
                assert "metadata" in response
                assert response["metadata"]["location_url"] == "/sell/account/v1/fulfillment_policy/6197962000"
                mock_client.post.assert_called_once()
                mock_client.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_fulfillment_policies_success(self, mock_context, mock_credentials):
        """Test successful retrieval of fulfillment policies."""
        
        if self.is_integration_mode:
            
            result = await get_fulfillment_policies.fn(
                ctx=mock_context,
                marketplaceId=MarketplaceIdEnum.EBAY_US
            )
            response = json.loads(result)

            if response["status"] == "error":
                error_code = response["error_code"]
                error_msg = response["error_message"]
                response.get("details", {}).get("status_code")
                errors = response.get("details", {}).get("errors", [])
                
                # Check if we're in sandbox mode
                is_sandbox = mcp.config.sandbox_mode
                
                # Only skip for known sandbox limitations when actually in sandbox mode
                if is_sandbox:
                    # Business Policy Eligibility Issues
                    if any(e.get("error_id") in [20403, 20001] for e in errors):
                        # Check error message and parameters for Business Policy eligibility
                        if ("not eligible for Business Policy" in error_msg or 
                            "not opted in to business policies" in error_msg or
                            "not BP opted in" in error_msg or
                            "seller profile ID is not valid" in error_msg):
                            pytest.skip(f"Known eBay sandbox limitation: Business Policy eligibility - {error_msg}")
                
                # For production or unexpected sandbox errors - fail the test
                if error_code == "CONFIGURATION_ERROR":
                    pytest.fail(f"CREDENTIALS PROBLEM: {error_msg} - {response}")
                elif error_code == "EXTERNAL_API_ERROR":
                    pytest.fail(f"eBay API CONNECTIVITY ISSUE: {error_msg} - {response}")
                else:
                    pytest.fail(f"UNEXPECTED INFRASTRUCTURE ISSUE: {error_code} - {error_msg} - {response}")

            assert response["status"] == "success"

        else:
            # Unit test - mocked dependencies
            with patch('tools.fulfillment_policy_api.EbayRestClient') as MockClient, \
                 patch('tools.fulfillment_policy_api.OAuthManager'), \
                 patch('tools.fulfillment_policy_api.mcp.config') as MockConfig:
                
                # Setup mocks with Pydantic-based test data
                mock_client = MockClient.return_value
                # Create multiple policies using factory
                policies = [
                    TestDataFulfillmentPolicy.policy_to_api_response(
                        TestDataFulfillmentPolicy.create_simple_policy(),
                        policy_id="6197932000"
                    ),
                    TestDataFulfillmentPolicy.policy_to_api_response(
                        TestDataFulfillmentPolicy.create_complex_policy(),
                        policy_id="6197942000"
                    ),
                    TestDataFulfillmentPolicy.policy_to_api_response(
                        TestDataFulfillmentPolicy.create_local_pickup_policy(),
                        policy_id="6197952000"
                    )
                ]
                mock_response = {
                    "fulfillmentPolicies": policies,
                    "total": len(policies),
                    "limit": 10,
                    "offset": 0
                }
                mock_client.get = AsyncMock(return_value={
                    "body": mock_response,
                    "headers": {}
                })
                mock_client.close = AsyncMock()
                MockConfig.app_id = "test_app"
                MockConfig.cert_id = "test_cert"
                MockConfig.sandbox_mode = True
                MockConfig.rate_limit_per_day = 5000
                
                result = await get_fulfillment_policies.fn(
                    ctx=mock_context,
                    marketplaceId=MarketplaceIdEnum.EBAY_US,
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
    async def test_get_fulfillment_policy_by_name_success(self, mock_context, mock_credentials):
        """Test successful retrieval of fulfillment policy by name."""
        marketplaceId = MarketplaceIdEnum.EBAY_US
        policyName = "Test Fulfillment Policy"
        
        if self.is_integration_mode:

            result = await get_fulfillment_policy_by_name.fn(
                ctx=mock_context,
                marketplaceId=marketplaceId,
                name=policyName
            )
            response = json.loads(result)
            
            if response["status"] == "error":
                error_code = response["error_code"]
                error_msg = response["error_message"]
                response.get("details", {}).get("status_code")
                errors = response.get("details", {}).get("errors", [])
                
                # Check if we're in sandbox mode
                is_sandbox = mcp.config.sandbox_mode
                
                # Only skip for known sandbox limitations when actually in sandbox mode
                if is_sandbox:
                    # Business Policy Eligibility Issues
                    if any(e.get("error_id") in [20403, 20001] for e in errors):
                        # Check error message and parameters for Business Policy eligibility
                        if ("not eligible for Business Policy" in error_msg or 
                            "not opted in to business policies" in error_msg or
                            "not BP opted in" in error_msg or
                            "seller profile ID is not valid" in error_msg):
                            pytest.skip(f"Known eBay sandbox limitation: Business Policy eligibility - {error_msg}")
                
                # For production or unexpected sandbox errors - fail the test
                if error_code == "CONFIGURATION_ERROR":
                    pytest.fail(f"CREDENTIALS PROBLEM: {error_msg} - {response}")
                elif error_code == "EXTERNAL_API_ERROR":
                    pytest.fail(f"eBay API CONNECTIVITY ISSUE: {error_msg} - {response}")
                else:
                    pytest.fail(f"UNEXPECTED INFRASTRUCTURE ISSUE: {error_code} - {error_msg} - {response}")

            assert response["status"] == "success"
            
        else:
            # Unit test - mocked dependencies
            with patch('tools.fulfillment_policy_api.EbayRestClient') as MockClient, \
                 patch('tools.fulfillment_policy_api.OAuthManager'), \
                 patch('tools.fulfillment_policy_api.mcp.config') as MockConfig:
                
                # Setup mocks
                mock_client = MockClient.return_value
                # Create test policy and convert to response
                test_policy = TestDataFulfillmentPolicy.create_simple_policy(name=policyName)
                expected_response = TestDataFulfillmentPolicy.policy_to_api_response(
                    test_policy,
                    policy_id="6197932000"
                )
                mock_client.get = AsyncMock(return_value={
                    "body": expected_response,
                    "headers": {}
                })
                mock_client.close = AsyncMock()
                MockConfig.app_id = "test_app"
                MockConfig.cert_id = "test_cert"
                MockConfig.sandbox_mode = True
                MockConfig.rate_limit_per_day = 5000
                
                result = await get_fulfillment_policy_by_name.fn(
                    ctx=mock_context,
                    marketplaceId=marketplaceId,
                    name=policyName
                )
                
                response = json.loads(result)
                assert response["status"] == "success"
                assert "data" in response
                assert response["data"]["name"] == policyName
                
                # Verify correct parameters were passed
                expected_params = {
                    "marketplaceId": "EBAY_US",
                    "name": policyName
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
        # Create initial policy, then modify it for update
        policy_input = TestDataFulfillmentPolicy.create_simple_policy()
        policy_input.name = "Updated Fulfillment Policy"
        policy_input.description = "Updated description"
        
        if self.is_integration_mode:
            # Try to get the policy ID from runtime data first
            stored_policy_id = TestDataFulfillmentPolicy.get_policy_id("Test Fulfillment Policy")
            if stored_policy_id:
                policy_id = stored_policy_id
            else:
                # If not found in runtime data, try to retrieve it via API
                marketplace_id = MarketplaceIdEnum.EBAY_US
                policy_name = "Test Fulfillment Policy"
            
                result = await get_fulfillment_policy_by_name.fn(
                    ctx=mock_context,
                    marketplaceId=marketplace_id,
                    name=policy_name
                )
                response = json.loads(result)

                # Check if we got a successful response with policy data
                if response["status"] == "success":
                    # Extract the policy_id from the formatted response
                    retrieved_policy_id = response["data"].get("fulfillmentPolicyId")
                    if retrieved_policy_id:
                        policy_id = retrieved_policy_id
            
            result = await update_fulfillment_policy.fn(
                ctx=mock_context,
                policyId=policy_id,
                policy_input=policy_input
            )
            response = json.loads(result)
            
            if response["status"] == "error":
                error_code = response["error_code"]
                error_msg = response["error_message"]
                response.get("details", {}).get("status_code")
                errors = response.get("details", {}).get("errors", [])
                
                # Check if we're in sandbox mode
                is_sandbox = mcp.config.sandbox_mode
                
                # Only skip for known sandbox limitations when actually in sandbox mode
                if is_sandbox:
                    # Business Policy Eligibility Issues
                    if any(e.get("error_id") in [20403, 20001] for e in errors):
                        # Check error message and parameters for Business Policy eligibility
                        if ("not eligible for Business Policy" in error_msg or 
                            "not opted in to business policies" in error_msg or
                            "not BP opted in" in error_msg or
                            "seller profile ID is not valid" in error_msg):
                            pytest.skip(f"Known eBay sandbox limitation: Business Policy eligibility - {error_msg}")
                
                # For production or unexpected sandbox errors - fail the test
                if error_code == "CONFIGURATION_ERROR":
                    pytest.fail(f"CREDENTIALS PROBLEM: {error_msg} - {response}")
                elif error_code == "EXTERNAL_API_ERROR":
                    pytest.fail(f"eBay API CONNECTIVITY ISSUE: {error_msg} - {response}")
                else:
                    pytest.fail(f"UNEXPECTED INFRASTRUCTURE ISSUE: {error_code} - {error_msg} - {response}")

            assert response["status"] == "success"
            
        else:
            # Unit test - mocked dependencies
            with patch('tools.fulfillment_policy_api.EbayRestClient') as MockClient, \
                 patch('tools.fulfillment_policy_api.OAuthManager'), \
                 patch('tools.fulfillment_policy_api.mcp.config') as MockConfig:
                
                # Setup mocks
                mock_client = MockClient.return_value
                # Convert updated policy to expected response
                expected_response = TestDataFulfillmentPolicy.policy_to_api_response(
                    policy_input,
                    policy_id=policy_id
                )
                mock_client.put = AsyncMock(return_value={
                    "body": expected_response,
                    "headers": {}
                })
                mock_client.close = AsyncMock()
                MockConfig.app_id = "test_app"
                MockConfig.cert_id = "test_cert"
                MockConfig.sandbox_mode = True
                MockConfig.rate_limit_per_day = 5000
                
                result = await update_fulfillment_policy.fn(
                    ctx=mock_context,
                    policyId=policy_id,
                    policy_input=policy_input
                )
                
                response = json.loads(result)
                assert response["status"] == "success"
                assert "data" in response
                assert response["data"]["name"] == policy_input.name
                assert response["data"]["description"] == policy_input.description
                mock_client.put.assert_called_once()
                mock_client.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_fulfillment_policy_success(self, mock_context, mock_credentials):
        """Test successful fulfillment policy deletion."""
        policy_id = "6197932000"
        
        if self.is_integration_mode:

            result = await delete_fulfillment_policy.fn(
                ctx=mock_context,
                policyId=policy_id
            )
            response = json.loads(result)
            
            if response["status"] == "error":
                error_code = response["error_code"]
                error_msg = response["error_message"]
                response.get("details", {}).get("status_code")
                errors = response.get("details", {}).get("errors", [])
                
                # Check if we're in sandbox mode
                is_sandbox = mcp.config.sandbox_mode
                
                # Only skip for known sandbox limitations when actually in sandbox mode
                if is_sandbox:
                    # Policy not found (sandbox limitation)
                    if any(e.get("error_id") == 20404 for e in errors):
                        pytest.skip(f"Known eBay sandbox limitation: Policy not found - {error_msg}")
                    # General policy not found error
                    elif "policyID not found" in error_msg:
                        pytest.skip(f"Known eBay sandbox limitation: Policy not found - {error_msg}")
                
                # For production or unexpected sandbox errors - fail the test
                pytest.fail(f"API call failed - {error_code}: {error_msg}")
            
            assert response["status"] == "success"
            
        else:
            # Unit test - mocked dependencies
            with patch('tools.fulfillment_policy_api.EbayRestClient') as MockClient, \
                 patch('tools.fulfillment_policy_api.OAuthManager'), \
                 patch('tools.fulfillment_policy_api.mcp.config') as MockConfig:
                
                # Setup mocks
                mock_client = MockClient.return_value
                mock_client.delete = AsyncMock(return_value={
                    "body": None,
                    "headers": {}
                })  # Delete returns no content
                mock_client.close = AsyncMock()
                MockConfig.app_id = "test_app"
                MockConfig.cert_id = "test_cert"
                MockConfig.sandbox_mode = True
                MockConfig.rate_limit_per_day = 5000
                
                result = await delete_fulfillment_policy.fn(
                    ctx=mock_context,
                    policyId=policy_id
                )
                
                response = json.loads(result)
                assert response["status"] == "success"
                assert "data" in response
                assert response["data"]["policyId"] == policy_id
                assert response["data"]["deleted"] is True
                mock_client.delete.assert_called_once_with(f"/sell/account/v1/fulfillment_policy/{policy_id}")
                mock_client.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_validation_errors(self, mock_context, mock_credentials):
        """Test validation error handling."""
        # Test empty policy_id
        result = await get_fulfillment_policy.fn(
            ctx=mock_context,
            policyId=""
        )
        response = json.loads(result)
        assert response["status"] == "error"
        assert response["error_code"] == "VALIDATION_ERROR"
        assert "policyId is required" in response["error_message"]
        
        # Test empty name
        result = await get_fulfillment_policy_by_name.fn(
            ctx=mock_context,
            marketplaceId=MarketplaceIdEnum.EBAY_US,
            name=""
        )
        response = json.loads(result)
        assert response["status"] == "error"
        assert response["error_code"] == "VALIDATION_ERROR"
        assert "name is required" in response["error_message"]
    
    @pytest.mark.asyncio
    async def test_ebay_api_errors(self, mock_context, mock_credentials):
        """Test eBay API error handling in unit mode."""
        if self.is_integration_mode:
            pytest.skip("eBay API error simulation only in unit mode")
        
        with patch('tools.fulfillment_policy_api.EbayRestClient') as MockClient, \
             patch('tools.fulfillment_policy_api.OAuthManager'), \
             patch('tools.fulfillment_policy_api.mcp.config') as MockConfig:
            
            # Setup mocks with API error
            mock_client = MockClient.return_value
            mock_client.get.side_effect = EbayApiError(
                status_code=404,
                error_response={"message": "Policy not found"}
            )
            mock_client.close = AsyncMock()
            MockConfig.app_id = "test_app"
            MockConfig.cert_id = "test_cert"
            MockConfig.sandbox_mode = True
            MockConfig.rate_limit_per_day = 5000
            
            result = await get_fulfillment_policy.fn(
                ctx=mock_context,
                policyId="nonexistent"
            )
            
            response = json.loads(result)
            assert response["status"] == "error"
            assert response["error_code"] == "EXTERNAL_API_ERROR"
            assert "Policy not found" in response["error_message"]
            assert response["details"]["status_code"] == 404
            mock_client.close.assert_called_once()