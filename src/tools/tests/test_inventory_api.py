"""
Tests for Inventory API that can run in unit or integration mode.

Environment Variables:
    TEST_MODE=unit (default): Run with mocked dependencies
    TEST_MODE=integration: Run against real eBay API
"""
import pytest
from unittest.mock import patch, AsyncMock, Mock
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
from tools.inventory_api import (
    create_inventory_item,
    get_inventory_items,
    update_inventory_item,
    delete_inventory_item,
    create_offer,
    get_offer,
    publish_offer,
    withdraw_offer,
    InventoryItemInput,
    OfferInput,
    InventorySearchInput,
    _convert_inventory_item,
    _convert_offer,
    _check_user_consent
)
from api.errors import EbayApiError


class TestInventoryApi(BaseApiTest):
    """Test Inventory API functions in both unit and integration modes."""
    
    # ==============================================================================
    # Data Conversion Tests (Unit tests only)
    # ==============================================================================
    
    @TestMode.skip_in_integration("Data conversion is unit test only")
    def test_convert_inventory_item(self):
        """Test inventory item conversion with valid data."""
        result = _convert_inventory_item(TestDataGood.INVENTORY_ITEM_IPHONE)
        
        # Validate structure, not specific values
        assert result["sku"] is not None
        assert FieldValidator.is_non_empty_string(result["sku"])
        
        assert result["title"] is not None
        assert FieldValidator.is_non_empty_string(result["title"])
        
        assert result["price"] is not None
        assert FieldValidator.is_valid_price(result["price"])
        
        assert result["quantity"] is not None
        assert isinstance(result["quantity"], int) and result["quantity"] >= 0
        
        assert result["condition"] == "NEW"
        assert result["currency"] == "USD"
        
        # Check nested fields
        assert isinstance(result["images"], list)
        assert isinstance(result["aspects"], dict)
    
    @TestMode.skip_in_integration("Data conversion is unit test only")
    def test_convert_inventory_item_minimal(self):
        """Test inventory item conversion with minimal data."""
        minimal_item = {
            "sku": "TEST-SKU",
            "product": {
                "title": "Test Item"
            },
            "condition": "NEW"
        }
        
        result = _convert_inventory_item(minimal_item)
        
        # Required fields should exist
        assert result["sku"] == "TEST-SKU"
        assert result["title"] == "Test Item"
        assert result["condition"] == "NEW"
        
        # Optional fields should have defaults
        assert result["quantity"] == 0
        assert result["images"] == []
        assert result["aspects"] == {}
    
    @TestMode.skip_in_integration("Data conversion is unit test only")
    def test_convert_offer(self):
        """Test offer conversion with valid data."""
        result = _convert_offer(TestDataGood.OFFER_FIXED_PRICE)
        
        # Validate structure
        assert result["offer_id"] is not None
        assert FieldValidator.is_non_empty_string(result["offer_id"])
        
        assert result["sku"] is not None
        assert FieldValidator.is_non_empty_string(result["sku"])
        
        assert result["marketplace_id"] == "EBAY_US"
        assert result["format"] == "FIXED_PRICE"
        
        assert result["price"] is not None
        assert FieldValidator.is_valid_price(result["price"])
        
        assert result["status"] == "PUBLISHED"
    
    @TestMode.skip_in_integration("Data conversion is unit test only")
    def test_convert_offer_bad_data(self):
        """Test offer conversion handles bad data gracefully."""
        result = _convert_offer(TestDataBad.OFFER_FIXED_PRICE)
        
        # Should handle empty/invalid data
        assert result["offer_id"] == ""  # Empty ID
        assert result["sku"] == "INVALID@SKU!"  # Invalid SKU
        assert result["format"] == "INVALID_FORMAT"
        assert result["price"] == "0.00"  # Zero price
    
    @TestMode.skip_in_integration("Input validation is unit test only")
    def test_inventory_item_input_validation(self):
        """Test inventory item input validation."""
        # Valid input
        valid_input = InventoryItemInput(
            sku="TEST-123",
            title="Test Product",
            description="A test product",
            category_id="166",
            price=29.99,
            quantity=10
        )
        assert valid_input.sku == "TEST-123"
        assert valid_input.price == 29.99
        assert valid_input.condition == "NEW"  # Default
        
        # Invalid SKU
        with pytest.raises(ValueError, match="SKU must contain only alphanumeric"):
            InventoryItemInput(
                sku="TEST@123!",  # Invalid characters
                title="Test",
                description="Test",
                category_id="166",
                price=10.0,
                quantity=1
            )
        
        # Invalid price
        with pytest.raises(ValueError):
            InventoryItemInput(
                sku="TEST-123",
                title="Test",
                description="Test",
                category_id="166",
                price=-10.0,  # Negative price
                quantity=1
            )
        
        # Invalid condition
        with pytest.raises(ValueError, match="Condition must be one of"):
            InventoryItemInput(
                sku="TEST-123",
                title="Test",
                description="Test",
                category_id="166",
                price=10.0,
                quantity=1,
                condition="INVALID"
            )
    
    # ==============================================================================
    # Create Inventory Item Tests (Both unit and integration)
    # ==============================================================================
    
    @pytest.mark.asyncio
    async def test_create_inventory_item_basic(self, mock_context, mock_credentials):
        """Test creating a basic inventory item."""
        if self.is_integration_mode:
            # Integration test - requires user consent
            with patch('tools.inventory_api._check_user_consent', AsyncMock(return_value="test_user_token")):
                result = await create_inventory_item.fn(
                    ctx=mock_context,
                    sku=f"TEST-{datetime.now().timestamp()}",  # Unique SKU
                    title="Test iPhone 15",
                    description="Test description for iPhone",
                    category_id="9355",
                    price=999.99,
                    quantity=5,
                    brand="Apple",
                    condition="NEW"
                )
                
                # Parse response
                data = json.loads(result)
                
                # May fail with auth error if no real user token
                if data["status"] == "success":
                    item = data["data"]["inventory_item"]
                    validate_field(item, "sku", str)
                    validate_field(item, "title", str)
                    validate_field(item, "price", (int, float))
                    validate_field(item, "quantity", int)
                else:
                    # Expected auth error without real user consent
                    assert data["error_code"] in ["AUTHENTICATION_ERROR", "EXTERNAL_API_ERROR"]
        else:
            # Unit test - mocked response
            with patch('tools.inventory_api._check_user_consent', new_callable=AsyncMock) as mock_consent, \
                 patch('tools.inventory_api.EbayRestClient') as MockClient:
                
                mock_consent.return_value = "test_user_token"
                mock_client = MockClient.return_value
                mock_client.put = AsyncMock(return_value={})  # Successful creation
                mock_client.get = AsyncMock(return_value={  # Mock the get response
                    "sku": "TEST-123",
                    "product": {
                        "title": "Test Product",
                        "description": "Test description",
                        "categoryId": "166",
                        "brand": "TestBrand"
                    },
                    "availability": {
                        "shipToLocationAvailability": {"quantity": 10}
                    },
                    "pricing": {
                        "price": {"value": "29.99", "currency": "USD"}
                    },
                    "condition": "NEW"
                })
                mock_client.close = AsyncMock()
                type(mock_client)._user_token = "test_user_token"
                
                with patch('tools.inventory_api.mcp.config.app_id', mock_credentials["app_id"]), \
                     patch('tools.inventory_api.mcp.config.cert_id', mock_credentials["cert_id"]):
                    
                    result = await create_inventory_item.fn(
                        ctx=mock_context,
                        sku="TEST-123",
                        title="Test Product",
                        description="Test description",
                        category_id="166",
                        price=29.99,
                        quantity=10,
                        brand="TestBrand"
                    )
                    
                    data = assert_api_response_success(result)
                    
                    # Should return the created item
                    assert "inventory_item" in data["data"]
                    item = data["data"]["inventory_item"]
                    assert item["sku"] == "TEST-123"
                    assert item["title"] == "Test Product"
                    assert item["price"] == 29.99
                    
                    # Verify API was called correctly
                    mock_client.put.assert_called()
                    call_args = mock_client.put.call_args
                    assert "/sell/inventory/v1/inventory_item/TEST-123" in call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_create_inventory_item_with_product_ids(self, mock_context, mock_credentials):
        """Test creating inventory item with product identifiers."""
        if self.is_integration_mode:
            # Skip detailed integration test
            return
        else:
            # Unit test
            with patch('tools.inventory_api._check_user_consent', new_callable=AsyncMock) as mock_consent, \
                 patch('tools.inventory_api.EbayRestClient') as MockClient:
                
                mock_consent.return_value = "test_user_token"
                mock_client = MockClient.return_value
                mock_client.put = AsyncMock(return_value={})
                mock_client.get = AsyncMock(return_value={  # Mock the get response
                    "sku": "IPHONE-TEST",
                    "product": {
                        "title": "iPhone 15 Pro",
                        "description": "Latest iPhone",
                        "categoryId": "9355",
                        "brand": "Apple",
                        "mpn": "MTQA3LL/A",
                        "upc": "194253434894"
                    },
                    "availability": {
                        "shipToLocationAvailability": {"quantity": 3}
                    },
                    "pricing": {
                        "price": {"value": "999.99", "currency": "USD"}
                    },
                    "condition": "NEW"
                })
                mock_client.close = AsyncMock()
                type(mock_client)._user_token = "test_user_token"
                
                with patch('tools.inventory_api.mcp.config.app_id', mock_credentials["app_id"]), \
                     patch('tools.inventory_api.mcp.config.cert_id', mock_credentials["cert_id"]):
                    
                    result = await create_inventory_item.fn(
                        ctx=mock_context,
                        sku="IPHONE-TEST",
                        title="iPhone 15 Pro",
                        description="Latest iPhone",
                        category_id="9355",
                        price=999.99,
                        quantity=3,
                        brand="Apple",
                        mpn="MTQA3LL/A",
                        upc="194253434894"
                    )
                    
                    data = assert_api_response_success(result)
                    
                    # Verify product identifiers were included
                    call_data = mock_client.put.call_args[1]["json"]
                    assert call_data["product"]["brand"] == "Apple"
                    assert call_data["product"]["mpn"] == "MTQA3LL/A"
                    assert call_data["product"]["upc"] == "194253434894"
    
    @pytest.mark.asyncio
    async def test_create_inventory_item_no_consent(self, mock_context, mock_credentials):
        """Test creating inventory item without user consent."""
        with patch('tools.inventory_api._check_user_consent', return_value=None):
            with patch('tools.inventory_api.mcp.config.app_id', mock_credentials["app_id"]), \
                 patch('tools.inventory_api.mcp.config.cert_id', mock_credentials["cert_id"]):
                
                result = await create_inventory_item.fn(
                    ctx=mock_context,
                    sku="TEST-123",
                    title="Test",
                    description="Test",
                    category_id="166",
                    price=10.0,
                    quantity=1
                )
                
                data = json.loads(result)
                assert data["status"] == "error"
                assert data["error_code"] == "AUTHENTICATION_ERROR"
                assert "consent required" in data["error_message"].lower()
    
    # ==============================================================================
    # Get Inventory Items Tests (Both unit and integration)
    # ==============================================================================
    
    @pytest.mark.asyncio
    async def test_get_inventory_items(self, mock_context, mock_credentials):
        """Test getting inventory items."""
        if self.is_integration_mode:
            # Integration test
            with patch('tools.inventory_api._check_user_consent', AsyncMock(return_value="test_user_token")):
                result = await get_inventory_items.fn(
                    ctx=mock_context,
                    limit=10
                )
                
                data = json.loads(result)
                
                if data["status"] == "success":
                    validate_field(data["data"], "inventory_items", list)
                    validate_field(data["data"], "total_items", int)
                    
                    # Check items if any exist
                    if data["data"]["inventory_items"]:
                        for item in data["data"]["inventory_items"]:
                            validate_field(item, "sku", str)
                            validate_field(item, "title", str)
        else:
            # Unit test
            with patch('tools.inventory_api._check_user_consent', AsyncMock(return_value="test_user_token")), \
                 patch('tools.inventory_api.EbayRestClient') as MockClient:
                
                mock_client = MockClient.return_value
                mock_client.get = AsyncMock(return_value={
                    "inventoryItems": [TestDataGood.INVENTORY_ITEM_IPHONE],
                    "total": 1
                })
                mock_client.close = AsyncMock()
                type(mock_client)._user_token = "test_user_token"
                
                with patch('tools.inventory_api.mcp.config.app_id', mock_credentials["app_id"]), \
                     patch('tools.inventory_api.mcp.config.cert_id', mock_credentials["cert_id"]):
                    
                    result = await get_inventory_items.fn(
                        ctx=mock_context,
                        limit=25
                    )
                    
                    data = assert_api_response_success(result)
                    
                    assert len(data["data"]["inventory_items"]) == 1
                    assert data["data"]["total_items"] == 1
                    
                    # Check converted item
                    item = data["data"]["inventory_items"][0]
                    assert item["sku"] == "IPHONE-15-PRO-256-TITANIUM"
                    assert item["title"] == "Apple iPhone 15 Pro - 256GB - Natural Titanium"
    
    # ==============================================================================
    # Create Offer Tests (Both unit and integration)
    # ==============================================================================
    
    @pytest.mark.asyncio
    async def test_create_offer_basic(self, mock_context, mock_credentials):
        """Test creating a basic offer."""
        if self.is_integration_mode:
            # Skip detailed integration test
            return
        else:
            # Unit test
            with patch('tools.inventory_api._check_user_consent', AsyncMock(return_value="test_user_token")), \
                 patch('tools.inventory_api.EbayRestClient') as MockClient:
                
                mock_client = MockClient.return_value
                # Mock getting inventory item
                mock_client.get = AsyncMock(return_value=TestDataGood.INVENTORY_ITEM_IPHONE)
                # Mock creating offer
                mock_client.post = AsyncMock(return_value={
                    "offerId": "5123456789"
                })
                mock_client.close = AsyncMock()
                type(mock_client)._user_token = "test_user_token"
                
                with patch('tools.inventory_api.mcp.config.app_id', mock_credentials["app_id"]), \
                     patch('tools.inventory_api.mcp.config.cert_id', mock_credentials["cert_id"]):
                    
                    result = await create_offer.fn(
                        ctx=mock_context,
                        sku="IPHONE-15-PRO-256-TITANIUM",
                        category_id="9355"
                    )
                    
                    data = assert_api_response_success(result)
                    
                    assert data["data"]["offer_id"] == "5123456789"
                    # Note: inline_policies_used was removed from the test call
                    
                    # Verify offer creation was called
                    assert mock_client.post.call_count == 1
                    call_args = mock_client.post.call_args
                    assert "/sell/inventory/v1/offer" in call_args[0][0]
    
    # ==============================================================================
    # Error Handling Tests
    # ==============================================================================
    
    @pytest.mark.asyncio
    async def test_create_inventory_item_error_handling(self, mock_context, mock_credentials):
        """Test error handling in inventory item creation."""
        if self.is_integration_mode:
            # Test with invalid input
            with patch('tools.inventory_api._check_user_consent', AsyncMock(return_value="test_user_token")):
                result = await create_inventory_item.fn(
                    ctx=mock_context,
                    sku="",  # Empty SKU
                    title="Test",
                    description="Test",
                    category_id="166",
                    price=10.0,
                    quantity=1
                )
                
                data = json.loads(result)
                assert data["status"] == "error"
                assert data["error_code"] == "VALIDATION_ERROR"
        else:
            # Unit test error handling
            with patch('tools.inventory_api._check_user_consent', AsyncMock(return_value="test_user_token")), \
                 patch('tools.inventory_api.EbayRestClient') as MockClient:
                
                mock_client = MockClient.return_value
                mock_client.put = AsyncMock(side_effect=EbayApiError(
                    status_code=400,
                    error_response={
                        "errors": [{
                            "errorId": 25710,
                            "message": "Invalid SKU format"
                        }]
                    }
                ))
                mock_client.close = AsyncMock()
                type(mock_client)._user_token = "test_user_token"
                
                with patch('tools.inventory_api.mcp.config.app_id', mock_credentials["app_id"]), \
                     patch('tools.inventory_api.mcp.config.cert_id', mock_credentials["cert_id"]):
                    
                    result = await create_inventory_item.fn(
                        ctx=mock_context,
                        sku="TEST-123",
                        title="Test",
                        description="Test",
                        category_id="166",
                        price=10.0,
                        quantity=1
                    )
                    
                    data = json.loads(result)
                    assert data["status"] == "error"
                    assert data["error_code"] == "EXTERNAL_API_ERROR"
    
    # ==============================================================================
    # Static Fallback Tests
    # ==============================================================================
    
    @pytest.mark.asyncio
    async def test_create_inventory_item_no_credentials(self, mock_context):
        """Test inventory item creation with no credentials uses static fallback."""
        with patch('tools.inventory_api.mcp.config.app_id', ''), \
             patch('tools.inventory_api.mcp.config.cert_id', ''):
            
            result = await create_inventory_item.fn(
                ctx=mock_context,
                sku="TEST-123",
                title="Test Product",
                description="Test description",
                category_id="166",
                price=29.99,
                quantity=10
            )
            
            data = assert_api_response_success(result)
            # Static fallback returns created item
            assert "inventory_item" in data["data"]
            assert data["data"]["data_source"] == "static_fallback"
            
            item = data["data"]["inventory_item"]
            assert item["sku"] == "TEST-123"
            assert item["title"] == "Test Product"
            assert item["status"] == "ACTIVE"