"""
Tests for Payment Policy API endpoints.

This module tests all 6 payment policy endpoints with both unit tests (using mocks)
and integration tests (using real eBay sandbox API).

Run modes:
- Unit tests: pytest test_payment_policy_api.py
- Integration tests: pytest test_payment_policy_api.py -v -s --test-mode=integration

CRITICAL: Integration tests require valid eBay credentials AND user consent.
Use check_user_consent_status and initiate_user_consent tools first.

TEST METHODOLOGY:
1. Infrastructure validation first (proves connectivity)
2. READ operations before WRITE operations
3. Test error cases with proper classification
4. Use diagnostic approach to distinguish real problems from expected failures

Professional implementation - no emojis, professional output only.
"""
import json
import pytest
import os
from decimal import Decimal
from unittest.mock import AsyncMock, patch
import logging
import sys

from tools.tests.base_test import TestMode
from lootly_server import mcp

from tools.payment_policy_api import (
    create_payment_policy,
    get_payment_policies,
    get_payment_policy,
    get_payment_policy_by_name,
    update_payment_policy,
    delete_payment_policy,
    PaymentPolicyInput,
    UpdatePaymentPolicyInput,
    CategoryType,
    PaymentMethod,
    Deposit,
    FullPaymentDueIn
)
from api.ebay_enums import (
    MarketplaceIdEnum,
    CategoryTypeEnum,
    PaymentMethodTypeEnum,
    TimeDurationUnitEnum,
    PaymentInstrumentBrandEnum
)
from api.errors import EbayApiError
from api.oauth import ConsentRequiredException
from tools.tests.test_data import (
    TestDataPaymentPolicy,
    TestDataError
)


class TestPaymentPolicyAPI:
    """Test suite for Payment Policy API endpoints."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Determine test mode
        self.is_integration_mode = os.getenv("TEST_MODE") == "integration"
        
        # Test data
        self.marketplace_id = MarketplaceIdEnum.EBAY_US
        self.test_policy_id = "6196940000"
        self.test_policy_name = "Test Payment Policy"
    
    @pytest.fixture
    def mock_context(self):
        """Create mock MCP context."""
        context = AsyncMock()
        context.info = AsyncMock()
        context.error = AsyncMock()
        context.report_progress = AsyncMock()
        return context
    
    
    # ==============================================================================
    # CRITICAL INFRASTRUCTURE VALIDATION TEST
    # ==============================================================================
    
    @pytest.mark.asyncio
    async def test_infrastructure_validation(self, mock_context):
        """CRITICAL: Validates integration infrastructure works before testing restricted APIs."""
        if not self.is_integration_mode:
            pytest.skip("Infrastructure validation only runs in integration mode")
        
        from tools.browse_api import search_items, BrowseSearchInput
        print("Testing integration infrastructure with Browse API...")
        print("This API uses basic scope (no user consent required)")
        
        search_input = BrowseSearchInput(query="iPhone", limit=1)
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
    # CREATE PAYMENT POLICY TESTS
    # ==============================================================================
    
    @pytest.mark.asyncio
    async def test_create_payment_policy_standard(self, mock_context):
        """Test creating a standard payment policy."""
        # Prepare test data
        policy_input = PaymentPolicyInput(
            name="Standard Payment Policy",
            marketplace_id=self.marketplace_id,
            category_types=[
                CategoryType(name=CategoryTypeEnum.ALL_EXCLUDING_MOTORS_VEHICLES)
            ],
            immediate_pay=True,
            description="Test standard payment policy"
        )
        
        if self.is_integration_mode:
            # Integration test - real API call
            print(f"\nTesting real API call to eBay sandbox...")
            print(f"Policy name: {policy_input.name}")
            print(f"Marketplace: {policy_input.marketplace_id.value}")
            
            result = await create_payment_policy.fn(
                ctx=mock_context,
                policy_input=policy_input
            )
            response = json.loads(result)
            
            print(f"API Response status: {response['status']}")
            
            if response["status"] == "error":
                error_code = response.get("error_code")
                error_msg = response.get("error_message", "")
                details = response.get("details", {})
                status_code = details.get("status_code")
                errors = details.get("errors", [])
                
                # Check if we're in sandbox mode
                is_sandbox = mcp.config.sandbox_mode
                
                # Only skip for known sandbox limitations when actually in sandbox mode
                if is_sandbox:
                    # Business Policy Eligibility Issues
                    if any(e.get("error_id") in [20403, 20001] for e in errors):
                        if "not eligible for Business Policy" in error_msg or "not opted in to business policies" in error_msg:
                            pytest.skip(f"Known eBay sandbox limitation: Business Policy eligibility - {error_msg}")
                
                # For production or unexpected sandbox errors - fail the test
                pytest.fail(f"API call failed - {error_code}: {error_msg}\nDetails: {details}\nJSON: {result}")
            
            # Test succeeded - verify we got expected data
            assert response["status"] == "success"
            assert "policy_id" in response["data"]
            print(f"Successfully created policy with ID: {response['data']['policy_id']}")
            self.created_policy_id = response['data']['policy_id']
        
        else:
            # Unit test - mocked dependencies
            with patch('tools.payment_policy_api.EbayRestClient') as MockClient, \
                 patch('tools.payment_policy_api.OAuthManager') as MockOAuth, \
                 patch('tools.payment_policy_api.mcp.config') as MockConfig:
                
                # Setup all mocks
                mock_client = MockClient.return_value
                mock_client.post = AsyncMock(return_value={
                    "body": TestDataPaymentPolicy.CREATE_POLICY_RESPONSE,
                    "headers": {}
                })
                mock_client.close = AsyncMock()
                
                MockConfig.app_id = "test_app"
                MockConfig.cert_id = "test_cert"
                MockConfig.sandbox_mode = True
                MockConfig.rate_limit_per_day = 5000
                
                
                result = await create_payment_policy.fn(
                    ctx=mock_context,
                    policy_input=policy_input
                )
                
                response = json.loads(result)
                assert response["status"] == "success"
                assert response["data"]["policy_id"] == "6196943000"
                assert response["data"]["name"] == "New Payment Policy"
                
                # Verify API call
                mock_client.post.assert_called_once()
                call_args = mock_client.post.call_args
                assert call_args[0][0] == "/sell/account/v1/payment_policy"
    
    @pytest.mark.asyncio
    async def test_create_payment_policy_motors(self, mock_context):
        """Test creating a motor vehicle payment policy with deposit."""
        # Prepare test data
        policy_input = PaymentPolicyInput(
            name="Motor Vehicle Payment",
            marketplace_id=self.marketplace_id,
            category_types=[
                CategoryType(name=CategoryTypeEnum.MOTORS_VEHICLES)
            ],
            immediate_pay=False,
            deposit=Deposit(
                due_in=3,
                amount=Decimal("500.00"),
                payment_methods=[
                    PaymentMethod(payment_method_type=PaymentMethodTypeEnum.CASHIER_CHECK)
                ]
            ),
            full_payment_due_in=FullPaymentDueIn(
                value=7,
                unit=TimeDurationUnitEnum.DAY
            ),
            payment_methods=[
                PaymentMethod(payment_method_type=PaymentMethodTypeEnum.CASH_ON_PICKUP)
            ]
        )
        
        if self.is_integration_mode:
            # Integration test - real API call
            print(f"\nCreating motor vehicle payment policy: {policy_input.name}")
            
            result = await create_payment_policy.fn(
                ctx=mock_context,
                policy_input=policy_input
            )
            response = json.loads(result)
            
            print(f"API Response status: {response['status']}")
            
            if response["status"] == "error":
                error_code = response.get("error_code")
                error_msg = response.get("error_message", "")
                details = response.get("details", {})
                status_code = details.get("status_code")
                errors = details.get("errors", [])
                
                # Check if we're in sandbox mode
                is_sandbox = mcp.config.sandbox_mode
                
                # Only skip for known sandbox limitations when actually in sandbox mode
                if is_sandbox:
                    # Business Policy Eligibility Issues
                    if any(e.get("error_id") in [20403, 20001] for e in errors):
                        if "not eligible for Business Policy" in error_msg or "not opted in to business policies" in error_msg:
                            pytest.skip(f"Known eBay sandbox limitation: Business Policy eligibility - {error_msg}")
                    # API serialization error for deposit field
                    elif any(e.get("error_id") == 2004 for e in errors):
                        if "Could not serialize field" in error_msg:
                            pytest.skip(f"Known eBay sandbox limitation: API serialization error - {error_msg}")
                
                # For production or unexpected sandbox errors - fail the test
                pytest.fail(f"API call failed - {error_code}: {error_msg}\nDetails: {details}")
            
            # Test succeeded - verify we got expected data
            assert response["status"] == "success"
            print(f"Successfully created motor vehicle policy with deposit")
            assert response["data"]["deposit"] is not None
            assert response["data"]["full_payment_due_in"] is not None
        
        else:
            # Unit test - mocked dependencies
            with patch('tools.payment_policy_api.EbayRestClient') as MockClient, \
                 patch('tools.payment_policy_api.OAuthManager') as MockOAuth, \
                 patch('tools.payment_policy_api.mcp.config') as MockConfig:
                
                # Setup all mocks
                mock_client = MockClient.return_value
                mock_client.post = AsyncMock(return_value={
                    "body": TestDataPaymentPolicy.PAYMENT_POLICY_MOTORS,
                    "headers": {}
                })
                mock_client.close = AsyncMock()
                
                MockConfig.app_id = "test_app"
                MockConfig.cert_id = "test_cert"
                MockConfig.sandbox_mode = True
                MockConfig.rate_limit_per_day = 5000
                
                
                result = await create_payment_policy.fn(
                    ctx=mock_context,
                    policy_input=policy_input
                )
                
                response = json.loads(result)
                assert response["status"] == "success"
                assert response["data"]["deposit"] is not None
                assert response["data"]["full_payment_due_in"] is not None
    
    @pytest.mark.asyncio
    async def test_create_payment_policy_validation_errors(self):
        """Test validation errors for payment policy creation."""
        # Test 1: Motor vehicle with immediate_pay=True (invalid)
        with pytest.raises(ValueError) as exc_info:
            PaymentPolicyInput(
                name="Invalid Motor Policy",
                marketplace_id=self.marketplace_id,
                category_types=[
                    CategoryType(name=CategoryTypeEnum.MOTORS_VEHICLES)
                ],
                immediate_pay=True  # Invalid for motors
            )
        assert "immediate_pay cannot be true for motor vehicle listings" in str(exc_info.value)
        
        # Test 2: Motor vehicle with deposit but no full_payment_due_in
        with pytest.raises(ValueError) as exc_info:
            PaymentPolicyInput(
                name="Invalid Motor Policy 2",
                marketplace_id=self.marketplace_id,
                category_types=[
                    CategoryType(name=CategoryTypeEnum.MOTORS_VEHICLES)
                ],
                deposit=Deposit(
                    due_in=3,
                    amount=Decimal("500.00")
                )
                # Missing full_payment_due_in
            )
        assert "full_payment_due_in is required when deposit is specified" in str(exc_info.value)
    
    # ==============================================================================
    # GET PAYMENT POLICIES TESTS
    # ==============================================================================
    
    @pytest.mark.asyncio
    async def test_get_payment_policies(self, mock_context):
        """Test retrieving all payment policies."""
        if self.is_integration_mode:
            # Integration test - real API call
            print(f"\nRetrieving payment policies for {self.marketplace_id.value}")
            result = await get_payment_policies.fn(
                ctx=mock_context,
                marketplace_id=self.marketplace_id
            )
            response = json.loads(result)
            
            print(f"API Response status: {response['status']}")
            
            if response["status"] == "error":
                error_code = response.get("error_code")
                error_msg = response.get("error_message", "")
                details = response.get("details", {})
                status_code = details.get("status_code")
                errors = details.get("errors", [])
                
                # Check if we're in sandbox mode
                is_sandbox = mcp.config.sandbox_mode
                
                # Only skip for known sandbox limitations when actually in sandbox mode
                if is_sandbox:
                    # Business Policy Eligibility Issues
                    if any(e.get("error_id") in [20403, 20001] for e in errors):
                        if "not eligible for Business Policy" in error_msg or "not opted in to business policies" in error_msg:
                            pytest.skip(f"Known eBay sandbox limitation: Business Policy eligibility - {error_msg}")
                
                # For production or unexpected sandbox errors - fail the test
                pytest.fail(f"API call failed - {error_code}: {error_msg}\nDetails: {details}")
            
            # Test succeeded - verify we got expected data
            assert response["status"] == "success"
            print(f"Found {response['data']['total']} payment policies")
            for policy in response['data']['policies']:
                print(f"  - {policy['name']} (ID: {policy['policy_id']})")
        
        else:
            # Unit test - mocked dependencies
            with patch('tools.payment_policy_api.EbayRestClient') as MockClient, \
                 patch('tools.payment_policy_api.OAuthManager') as MockOAuth, \
                 patch('tools.payment_policy_api.mcp.config') as MockConfig:
                
                # Setup all mocks
                mock_client = MockClient.return_value
                mock_client.get = AsyncMock(return_value={
                    "body": TestDataPaymentPolicy.GET_POLICIES_RESPONSE,
                    "headers": {}
                })
                mock_client.close = AsyncMock()
                
                MockConfig.app_id = "test_app"
                MockConfig.cert_id = "test_cert"
                MockConfig.sandbox_mode = True
                MockConfig.rate_limit_per_day = 5000
                
                
                result = await get_payment_policies.fn(
                    ctx=mock_context,
                    marketplace_id=self.marketplace_id,
                    limit=20,
                    offset=0
                )
                
                response = json.loads(result)
                assert response["status"] == "success"
                assert len(response["data"]["policies"]) == 3
                assert response["data"]["total"] == 3
                
                # Verify API call
                mock_client.get.assert_called_once_with(
                    "/sell/account/v1/payment_policy",
                    params={
                        "marketplace_id": "EBAY_US",
                        "limit": 20,
                        "offset": 0
                    }
                )
    
    # ==============================================================================
    # GET SINGLE PAYMENT POLICY TESTS
    # ==============================================================================
    
    @pytest.mark.asyncio
    async def test_get_payment_policy(self, mock_context):
        """Test retrieving a single payment policy by ID."""
        if self.is_integration_mode:
            # Integration test - real API call
            result = await get_payment_policy.fn(
                ctx=mock_context,
                payment_policy_id=self.test_policy_id
            )
            response = json.loads(result)
            
            print(f"API Response status: {response['status']}")
            
            if response["status"] == "error":
                error_code = response.get("error_code")
                error_msg = response.get("error_message", "")
                details = response.get("details", {})
                status_code = details.get("status_code")
                errors = details.get("errors", [])
                
                # Check if we're in sandbox mode
                is_sandbox = mcp.config.sandbox_mode
                
                # Only skip for known sandbox limitations when actually in sandbox mode
                if is_sandbox:
                    # Business Policy Eligibility Issues
                    if any(e.get("error_id") in [20403, 20001] for e in errors):
                        if "not eligible for Business Policy" in error_msg or "not opted in to business policies" in error_msg:
                            pytest.skip(f"Known eBay sandbox limitation: Business Policy eligibility - {error_msg}")
                
                # For production or unexpected sandbox errors - fail the test
                pytest.fail(f"API call failed - {error_code}: {error_msg}\nDetails: {details}")
            
            # Test succeeded - verify we got expected data
            assert response["status"] == "success"
            assert response["data"]["policy_id"] == self.test_policy_id
        
        else:
            # Unit test - mocked dependencies
            with patch('tools.payment_policy_api.EbayRestClient') as MockClient, \
                 patch('tools.payment_policy_api.OAuthManager') as MockOAuth, \
                 patch('tools.payment_policy_api.mcp.config') as MockConfig:
                
                # Setup all mocks
                mock_client = MockClient.return_value
                mock_client.get = AsyncMock(return_value={
                    "body": TestDataPaymentPolicy.PAYMENT_POLICY_STANDARD,
                    "headers": {}
                })
                mock_client.close = AsyncMock()
                
                MockConfig.app_id = "test_app"
                MockConfig.cert_id = "test_cert"
                MockConfig.sandbox_mode = True
                MockConfig.rate_limit_per_day = 5000
                
                
                result = await get_payment_policy.fn(
                    ctx=mock_context,
                    payment_policy_id=self.test_policy_id
                )
                
                response = json.loads(result)
                assert response["status"] == "success"
                assert response["data"]["policy_id"] == self.test_policy_id
                
                # Verify API call
                mock_client.get.assert_called_once_with(
                    f"/sell/account/v1/payment_policy/{self.test_policy_id}"
                )
    
    @pytest.mark.asyncio
    async def test_get_payment_policy_not_found(self, mock_context):
        """Test retrieving non-existent payment policy."""
        if self.is_integration_mode:
            # Integration test - expect not found
            result = await get_payment_policy.fn(
                ctx=mock_context,
                payment_policy_id="NONEXISTENT_POLICY_12345"
            )
            response = json.loads(result)
            
            print(f"API Response status: {response['status']}")
            
            if response["status"] == "error":
                error_code = response.get("error_code")
                error_msg = response.get("error_message", "")
                details = response.get("details", {})
                status_code = details.get("status_code")
                errors = details.get("errors", [])
                
                # Check if we're in sandbox mode
                is_sandbox = mcp.config.sandbox_mode
                
                # Only skip for known sandbox limitations when actually in sandbox mode
                if is_sandbox:
                    # Business Policy Eligibility Issues (sandbox returns this instead of 404)
                    if any(e.get("error_id") in [20403, 20001] for e in errors):
                        if "not eligible for Business Policy" in error_msg or "Invalid paymentPolicyId" in error_msg:
                            pytest.skip(f"Known eBay sandbox limitation: Business Policy eligibility - {error_msg}")
                
                # For production or unexpected sandbox errors - fail the test
                # For a not found test, we might expect a 404 error
                # But if it's an auth error, that's a real problem
                if error_code == "AUTHENTICATION_ERROR":
                    pytest.fail(f"Authentication failed - {error_msg}")
                elif error_code == "EXTERNAL_API_ERROR" and "404" in str(response.get("details", {})):
                    print("Expected: Policy not found (404)")
                else:
                    pytest.fail(f"Unexpected error - {error_code}: {error_msg}")
        else:
            # Unit test - mocked dependencies
            with patch('tools.payment_policy_api.EbayRestClient') as MockClient, \
                 patch('tools.payment_policy_api.OAuthManager') as MockOAuth, \
                 patch('tools.payment_policy_api.mcp.config') as MockConfig:
                
                mock_client = MockClient.return_value
                mock_client.get = AsyncMock(side_effect=EbayApiError(404, TestDataError.ERROR_NOT_FOUND))
                mock_client.close = AsyncMock()
                
                MockConfig.app_id = "test_app"
                MockConfig.cert_id = "test_cert"
                MockConfig.sandbox_mode = True
                MockConfig.rate_limit_per_day = 5000
                
                
                result = await get_payment_policy.fn(
                    ctx=mock_context,
                    payment_policy_id="NONEXISTENT"
                )
                
                response = json.loads(result)
                assert response["status"] == "error"
                assert response["error_code"] == "EXTERNAL_API_ERROR"
    
    # ==============================================================================
    # GET PAYMENT POLICY BY NAME TESTS
    # ==============================================================================
    
    @pytest.mark.asyncio
    async def test_get_payment_policy_by_name(self, mock_context):
        """Test retrieving payment policy by name."""
        if self.is_integration_mode:
            # Integration test - real API call
            result = await get_payment_policy_by_name.fn(
                ctx=mock_context,
                marketplace_id=self.marketplace_id,
                name=self.test_policy_name
            )
            response = json.loads(result)
            
            print(f"API Response status: {response['status']}")
            
            if response["status"] == "error":
                error_code = response.get("error_code")
                error_msg = response.get("error_message", "")
                details = response.get("details", {})
                status_code = details.get("status_code")
                errors = details.get("errors", [])
                
                # Check if we're in sandbox mode
                is_sandbox = mcp.config.sandbox_mode
                
                # Only skip for known sandbox limitations when actually in sandbox mode
                if is_sandbox:
                    # Business Policy Eligibility Issues
                    if any(e.get("error_id") in [20403, 20001] for e in errors):
                        if "not eligible for Business Policy" in error_msg or "not opted in to business policies" in error_msg:
                            pytest.skip(f"Known eBay sandbox limitation: Business Policy eligibility - {error_msg}")
                
                # For production or unexpected sandbox errors - fail the test
                pytest.fail(f"API call failed - {error_code}: {error_msg}\nDetails: {details}")
            
            # Test succeeded - verify we got expected data
            assert response["status"] == "success"
            assert response["data"]["name"] == self.test_policy_name
        
        else:
            # Unit test mode
            with patch('tools.payment_policy_api.EbayRestClient') as MockClient, \
                 patch('tools.payment_policy_api.OAuthManager') as MockOAuth, \
                 patch('tools.payment_policy_api.mcp.config') as MockConfig:
                
                mock_client = MockClient.return_value
                mock_client.get = AsyncMock(return_value={
                    "body": TestDataPaymentPolicy.GET_BY_NAME_RESPONSE,
                    "headers": {}
                })
                mock_client.close = AsyncMock()
                
                MockConfig.app_id = "test_app"
                MockConfig.cert_id = "test_cert"
                MockConfig.sandbox_mode = True
                MockConfig.rate_limit_per_day = 5000
                
                
                result = await get_payment_policy_by_name.fn(
                    ctx=mock_context,
                    marketplace_id=self.marketplace_id,
                    name=self.test_policy_name
                )
                
                response = json.loads(result)
                if response["status"] == "error":
                    print(f"ERROR: {response['error_code']} - {response['error_message']}")
                assert response["status"] == "success"
                assert response["data"]["name"] == "Standard Payment"
                
                # Verify API call
                mock_client.get.assert_called_once_with(
                    "/sell/account/v1/payment_policy/get_by_policy_name",
                    params={
                        "marketplace_id": "EBAY_US",
                        "name": self.test_policy_name
                    }
                )
    
    @pytest.mark.asyncio
    async def test_get_payment_policy_by_name_not_found(self, mock_context):
        """Test retrieving non-existent payment policy by name."""
        # Unit test mode
        if not self.is_integration_mode:
            with patch('tools.payment_policy_api.EbayRestClient') as MockClient, \
                 patch('tools.payment_policy_api.OAuthManager') as MockOAuth, \
                 patch('tools.payment_policy_api.mcp.config') as MockConfig:
                
                mock_client = MockClient.return_value
                mock_client.get = AsyncMock(side_effect=EbayApiError(404, {"message": "Policy not found"}))
                mock_client.close = AsyncMock()
                
                MockConfig.app_id = "test_app"
                MockConfig.cert_id = "test_cert"
                MockConfig.sandbox_mode = True
                MockConfig.rate_limit_per_day = 5000
                
                
                result = await get_payment_policy_by_name.fn(
                    ctx=mock_context,
                    marketplace_id=self.marketplace_id,
                    name="Nonexistent Policy"
                )
                
                response = json.loads(result)
                assert response["status"] == "error"
                assert response["error_code"] == "RESOURCE_NOT_FOUND"
                assert "No payment policy found" in response["error_message"]
    
    # ==============================================================================
    # UPDATE PAYMENT POLICY TESTS
    # ==============================================================================
    
    @pytest.mark.asyncio
    async def test_update_payment_policy(self, mock_context):
        """Test updating an existing payment policy."""
        # Prepare update data
        update_input = UpdatePaymentPolicyInput(
            name="Updated Payment Policy",
            marketplace_id=self.marketplace_id,
            category_types=[
                CategoryType(name=CategoryTypeEnum.ALL_EXCLUDING_MOTORS_VEHICLES)
            ],
            immediate_pay=False,
            payment_instrument_brands=[
                PaymentInstrumentBrandEnum.VISA,
                PaymentInstrumentBrandEnum.MASTERCARD
            ]
        )
        
        if self.is_integration_mode:
            # Integration test - real API call
            print(f"\nUpdating payment policy {self.test_policy_id}")
            result = await update_payment_policy.fn(
                ctx=mock_context,
                payment_policy_id=self.test_policy_id,
                policy_input=update_input
            )
            response = json.loads(result)
            
            print(f"API Response status: {response['status']}")
            
            if response["status"] == "error":
                error_code = response.get("error_code")
                error_msg = response.get("error_message", "")
                details = response.get("details", {})
                status_code = details.get("status_code")
                errors = details.get("errors", [])
                
                # Check if we're in sandbox mode
                is_sandbox = mcp.config.sandbox_mode
                
                # Only skip for known sandbox limitations when actually in sandbox mode
                if is_sandbox:
                    # Business Policy Eligibility Issues
                    if any(e.get("error_id") in [20403, 20001] for e in errors):
                        if "not eligible for Business Policy" in error_msg or "not opted in to business policies" in error_msg:
                            pytest.skip(f"Known eBay sandbox limitation: Business Policy eligibility - {error_msg}")
                
                # For production or unexpected sandbox errors - fail the test
                pytest.fail(f"API call failed - {error_code}: {error_msg}\nDetails: {details}")
            
            # Test succeeded - verify we got expected data
            assert response["status"] == "success"
            assert response["data"]["name"] == update_input.name
        
        else:
            # Unit test mode
            with patch('tools.payment_policy_api.EbayRestClient') as MockClient, \
                 patch('tools.payment_policy_api.OAuthManager') as MockOAuth, \
                 patch('tools.payment_policy_api.mcp.config') as MockConfig:
                
                mock_client = MockClient.return_value
                mock_client.put = AsyncMock(return_value={
                    "body": TestDataPaymentPolicy.UPDATE_POLICY_RESPONSE,
                    "headers": {}
                })
                mock_client.close = AsyncMock()
                
                MockConfig.app_id = "test_app"
                MockConfig.cert_id = "test_cert"
                MockConfig.sandbox_mode = True
                MockConfig.rate_limit_per_day = 5000
                
                
                result = await update_payment_policy.fn(
                    ctx=mock_context,
                    payment_policy_id=self.test_policy_id,
                    policy_input=update_input
                )
                
                response = json.loads(result)
                assert response["status"] == "success"
                assert response["data"]["name"] == "Updated Payment Policy"
                assert response["data"]["immediate_pay"] is False
                
                # Verify API call
                mock_client.put.assert_called_once()
                call_args = mock_client.put.call_args
                assert call_args[0][0] == f"/sell/account/v1/payment_policy/{self.test_policy_id}"
    
    # ==============================================================================
    # DELETE PAYMENT POLICY TESTS
    # ==============================================================================
    
    @pytest.mark.asyncio
    async def test_delete_payment_policy(self, mock_context):
        """Test deleting a payment policy."""
        if self.is_integration_mode:
            # Integration test - real API call
            print(f"\nDeleting payment policy {self.test_policy_id}")
            result = await delete_payment_policy.fn(
                ctx=mock_context,
                payment_policy_id=self.test_policy_id
            )
            response = json.loads(result)
            
            print(f"API Response status: {response['status']}")
            
            if response["status"] == "error":
                error_code = response.get("error_code")
                error_msg = response.get("error_message", "")
                details = response.get("details", {})
                status_code = details.get("status_code")
                errors = details.get("errors", [])
                
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
                pytest.fail(f"API call failed - {error_code}: {error_msg}\nDetails: {details}")
            
            # Test succeeded - verify deletion
            assert response["status"] == "success"
            assert response["data"]["deleted"] is True
        
        else:
            # Unit test mode
            with patch('tools.payment_policy_api.EbayRestClient') as MockClient, \
                 patch('tools.payment_policy_api.OAuthManager') as MockOAuth, \
                 patch('tools.payment_policy_api.mcp.config') as MockConfig:
                
                mock_client = MockClient.return_value
                # DELETE typically returns 204 No Content (None)
                mock_client.delete = AsyncMock(return_value={
                    "body": None,
                    "headers": {}
                })
                mock_client.close = AsyncMock()
                
                MockConfig.app_id = "test_app"
                MockConfig.cert_id = "test_cert"
                MockConfig.sandbox_mode = True
                MockConfig.rate_limit_per_day = 5000
                
                
                result = await delete_payment_policy.fn(
                    ctx=mock_context,
                    payment_policy_id=self.test_policy_id
                )
                
                response = json.loads(result)
                assert response["status"] == "success"
                assert response["data"]["deleted"] is True
                assert response["data"]["policy_id"] == self.test_policy_id
                
                # Verify API call
                mock_client.delete.assert_called_once_with(
                    f"/sell/account/v1/payment_policy/{self.test_policy_id}"
                )
    
    @pytest.mark.asyncio
    async def test_delete_payment_policy_with_active_listings(self, mock_context):
        """Test deleting a policy that's associated with active listings."""
        if self.is_integration_mode:
            # Integration test - expect conflict error
            print(f"\nAttempting to delete policy with active listings")
            result = await delete_payment_policy.fn(
                ctx=mock_context,
                payment_policy_id=self.test_policy_id
            )
            response = json.loads(result)
            
            print(f"API Response status: {response['status']}")
            
            # This test expects an error (409 conflict)
            if response["status"] == "success":
                pytest.fail("Expected conflict error but got success")
            
            # Verify we got the expected conflict error
            assert response["status"] == "error"
            error_code = response.get("error_code")
            error_msg = response.get("error_message", "")
            details = response.get("details", {})
            status_code = details.get("status_code")
            errors = details.get("errors", [])
            
            # Check if we're in sandbox mode
            is_sandbox = mcp.config.sandbox_mode
            
            # Only skip for known sandbox limitations when actually in sandbox mode
            if is_sandbox:
                # Policy not found (sandbox limitation - might return 404 instead of 409)
                if any(e.get("error_id") == 20404 for e in errors):
                    pytest.skip(f"Known eBay sandbox limitation: Policy not found - {error_msg}")
                # General policy not found error  
                elif "policyID not found" in error_msg:
                    pytest.skip(f"Known eBay sandbox limitation: Policy not found - {error_msg}")
            
            # For production or unexpected sandbox errors - check for expected conflict
            if error_code != "PERMISSION_DENIED" and "409" not in str(response.get("details", {})):
                pytest.fail(f"Expected 409 conflict but got - {error_code}: {error_msg}")
        
        else:
            # Unit test mode
            with patch('tools.payment_policy_api.EbayRestClient') as MockClient, \
                 patch('tools.payment_policy_api.OAuthManager') as MockOAuth, \
                 patch('tools.payment_policy_api.mcp.config') as MockConfig:
                
                mock_client = MockClient.return_value
                mock_client.delete = AsyncMock(side_effect=EbayApiError(409, {"message": "Policy is in use"}))
                mock_client.close = AsyncMock()
                
                MockConfig.app_id = "test_app"
                MockConfig.cert_id = "test_cert"
                MockConfig.sandbox_mode = True
                MockConfig.rate_limit_per_day = 5000
                
                
                result = await delete_payment_policy.fn(
                    ctx=mock_context,
                    payment_policy_id=self.test_policy_id
                )
                
                response = json.loads(result)
                assert response["status"] == "error"
                assert response["error_code"] == "PERMISSION_DENIED"
                assert "associated with active listings" in response["error_message"]
    
    # ==============================================================================
    # ERROR HANDLING TESTS
    # ==============================================================================
    
    @pytest.mark.asyncio
    async def test_missing_credentials(self, mock_context):
        """Test handling missing credentials."""
        with patch('tools.payment_policy_api.mcp.config') as mock_cfg:
            mock_cfg.app_id = None
            mock_cfg.cert_id = None
            
            result = await get_payment_policies.fn(
                ctx=mock_context,
                marketplace_id=self.marketplace_id
            )
            
            response = json.loads(result)
            assert response["status"] == "error"
            assert response["error_code"] == "CONFIGURATION_ERROR"
            assert "eBay App ID and Cert ID must be configured" in response["error_message"]
    
    @pytest.mark.asyncio
    async def test_missing_user_consent(self, mock_context):
        """Test handling missing user consent - unit test only."""
        if self.is_integration_mode:
            pytest.skip("User consent test only runs in unit mode")
        
        with patch('tools.payment_policy_api.EbayRestClient') as MockClient, \
             patch('tools.payment_policy_api.OAuthManager') as MockOAuth, \
             patch('tools.payment_policy_api.mcp.config') as MockConfig:
            
            # Mock the REST client to raise ConsentRequiredException
            mock_client = MockClient.return_value
            mock_client.get = AsyncMock(side_effect=ConsentRequiredException("User consent required"))
            mock_client.close = AsyncMock()
            
            MockConfig.app_id = "test_app"
            MockConfig.cert_id = "test_cert"
            MockConfig.sandbox_mode = True
            MockConfig.rate_limit_per_day = 5000
            
            result = await get_payment_policies.fn(
                ctx=mock_context,
                marketplace_id=self.marketplace_id
            )
            
            response = json.loads(result)
            assert response["status"] == "error"
            assert response["error_code"] == "AUTHENTICATION_ERROR"
            assert "User consent required" in response["error_message"]
    
    @pytest.mark.asyncio
    async def test_rate_limit_error(self, mock_context):
        """Test handling rate limit errors."""
        if self.is_integration_mode:
            # Skip in integration mode - we don't want to trigger real rate limits
            pytest.skip("Rate limit testing skipped in integration mode")
        
        else:
            # Unit test mode
            with patch('tools.payment_policy_api.EbayRestClient') as MockClient, \
                 patch('tools.payment_policy_api.OAuthManager') as MockOAuth, \
                 patch('tools.payment_policy_api.mcp.config') as MockConfig:
                
                mock_client = MockClient.return_value
                mock_client.get = AsyncMock(side_effect=EbayApiError(429, TestDataError.ERROR_RATE_LIMIT))
                mock_client.close = AsyncMock()
                
                MockConfig.app_id = "test_app"
                MockConfig.cert_id = "test_cert"
                MockConfig.sandbox_mode = True
                MockConfig.rate_limit_per_day = 5000
                
                
                result = await get_payment_policies.fn(
                    ctx=mock_context,
                    marketplace_id=self.marketplace_id
                )
                
                response = json.loads(result)
                assert response["status"] == "error"
                assert response["error_code"] == "EXTERNAL_API_ERROR"
                assert response["details"]["status_code"] == 429
    
    # ==============================================================================
    # HELPER METHODS
    # ==============================================================================
    
    # REMOVED _classify_error_response - integration tests should FAIL on errors, not classify them
    
    def teardown_method(self):
        """Clean up after tests."""
        # Clean up any created policies in integration mode
        if hasattr(self, 'created_policy_id'):
            print(f"\nCleanup: Would delete policy {self.created_policy_id}")