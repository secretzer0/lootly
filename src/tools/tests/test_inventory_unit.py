"""Unit tests for Inventory API tools."""
import pytest
from unittest.mock import Mock, patch, AsyncMock
import json
from datetime import datetime
from fastmcp import Context

from tools.inventory_api import (
    create_inventory_item,
    get_inventory_items,
    create_offer,
    publish_offer,
    _convert_inventory_item,
    _convert_offer,
    InventoryItemInput,
    OfferInput,
    InventorySearchInput
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
    client.put = AsyncMock()
    client.post = AsyncMock()
    client.close = AsyncMock()
    return client


@pytest.fixture(autouse=True)
def mock_global_mcp():
    """Mock the global mcp instance."""
    with patch('tools.inventory_api.mcp') as mock_mcp:
        mock_mcp.config.app_id = "test_app_id"
        mock_mcp.config.cert_id = "test_cert_id"
        mock_mcp.config.sandbox_mode = True
        mock_mcp.config.rate_limit_per_day = 5000
        mock_mcp.cache_manager = Mock()
        mock_mcp.cache_manager.set = AsyncMock()
        mock_mcp.cache_manager.delete = AsyncMock()
        mock_mcp.logger = Mock()
        yield mock_mcp


@pytest.fixture
def mock_inventory_item_response():
    """Mock inventory item response."""
    return {
        "sku": "TEST-SKU-001",
        "availability": {
            "shipToLocationAvailability": {
                "quantity": 10
            }
        },
        "condition": "NEW",
        "conditionDescription": "Brand new item",
        "product": {
            "title": "Test Product",
            "description": "Test product description",
            "brand": "Test Brand",
            "mpn": "TEST-MPN",
            "upc": "123456789012",
            "categoryId": "166",
            "imageUrls": ["https://example.com/image.jpg"],
            "aspects": {
                "Color": "Blue",
                "Size": "Medium"
            }
        },
        "pricing": {
            "price": {
                "value": "29.99",
                "currency": "USD"
            }
        },
        "status": "ACTIVE",
        "createdDate": "2024-01-01T00:00:00Z",
        "lastModifiedDate": "2024-01-01T00:00:00Z"
    }


@pytest.fixture
def mock_inventory_items_response():
    """Mock inventory items list response."""
    return {
        "inventoryItems": [
            {
                "sku": "TEST-SKU-001",
                "availability": {"shipToLocationAvailability": {"quantity": 10}},
                "condition": "NEW",
                "product": {
                    "title": "Test Product 1",
                    "description": "Test product 1 description",
                    "categoryId": "166"
                },
                "pricing": {"price": {"value": "29.99", "currency": "USD"}},
                "status": "ACTIVE"
            },
            {
                "sku": "TEST-SKU-002",
                "availability": {"shipToLocationAvailability": {"quantity": 5}},
                "condition": "USED_GOOD",
                "product": {
                    "title": "Test Product 2",
                    "description": "Test product 2 description",
                    "categoryId": "166"
                },
                "pricing": {"price": {"value": "19.99", "currency": "USD"}},
                "status": "ACTIVE"
            }
        ],
        "total": 2
    }


@pytest.fixture
def mock_offer_response():
    """Mock offer response."""
    return {
        "offerId": "12345678901234567890",
        "sku": "TEST-SKU-001",
        "marketplaceId": "EBAY_US",
        "format": "FIXED_PRICE",
        "categoryId": "166",
        "listing": {
            "duration": "GTC",
            "listingId": None,
            "listingStatus": "DRAFT"
        },
        "quantitySold": 0,
        "availableQuantity": 10,
        "pricingSummary": {
            "price": {
                "value": "29.99",
                "currency": "USD"
            }
        },
        "status": "UNPUBLISHED",
        "createdDate": "2024-01-01T00:00:00Z",
        "lastModifiedDate": "2024-01-01T00:00:00Z"
    }


@pytest.fixture
def mock_publish_response():
    """Mock publish offer response."""
    return {
        "listingId": "110123456789"
    }


class TestInputValidation:
    """Test input validation models."""
    
    def test_inventory_item_input_valid(self):
        """Test valid inventory item input."""
        input_data = InventoryItemInput(
            sku="TEST-SKU-001",
            title="Test Product",
            description="Test product description",
            category_id="166",
            price=29.99,
            quantity=10,
            condition="NEW"
        )
        
        assert input_data.sku == "TEST-SKU-001"
        assert input_data.title == "Test Product"
        assert input_data.description == "Test product description"
        assert input_data.category_id == "166"
        assert input_data.price == 29.99
        assert input_data.quantity == 10
        assert input_data.condition == "NEW"
        assert input_data.currency == "USD"
    
    def test_inventory_item_input_invalid_sku(self):
        """Test invalid SKU validation."""
        with pytest.raises(ValueError, match="SKU must contain only alphanumeric characters"):
            InventoryItemInput(
                sku="INVALID@SKU",
                title="Test Product",
                description="Test description",
                category_id="166",
                price=29.99,
                quantity=10
            )
    
    def test_inventory_item_input_invalid_condition(self):
        """Test invalid condition validation."""
        with pytest.raises(ValueError, match="Condition must be one of"):
            InventoryItemInput(
                sku="TEST-SKU-001",
                title="Test Product",
                description="Test description",
                category_id="166",
                price=29.99,
                quantity=10,
                condition="INVALID_CONDITION"
            )
    
    def test_inventory_item_input_invalid_price(self):
        """Test invalid price validation."""
        with pytest.raises(ValueError):
            InventoryItemInput(
                sku="TEST-SKU-001",
                title="Test Product",
                description="Test description",
                category_id="166",
                price=-10.00,  # Negative price
                quantity=10
            )
    
    def test_offer_input_valid(self):
        """Test valid offer input."""
        input_data = OfferInput(
            sku="TEST-SKU-001",
            marketplace_id="EBAY_US",
            format="FIXED_PRICE",
            duration="GTC",
            category_id="166"
        )
        
        assert input_data.sku == "TEST-SKU-001"
        assert input_data.marketplace_id == "EBAY_US"
        assert input_data.format == "FIXED_PRICE"
        assert input_data.duration == "GTC"
        assert input_data.category_id == "166"
    
    def test_offer_input_invalid_format(self):
        """Test invalid format validation."""
        with pytest.raises(ValueError, match="Format must be one of"):
            OfferInput(
                sku="TEST-SKU-001",
                marketplace_id="EBAY_US",
                format="INVALID_FORMAT",
                category_id="166"
            )
    
    def test_inventory_search_input_valid(self):
        """Test valid inventory search input."""
        input_data = InventorySearchInput(
            sku="TEST-SKU-001",
            title="Test Product",
            limit=50,
            offset=0
        )
        
        assert input_data.sku == "TEST-SKU-001"
        assert input_data.title == "Test Product"
        assert input_data.limit == 50
        assert input_data.offset == 0


class TestDataConversion:
    """Test data conversion functions."""
    
    def test_convert_inventory_item_complete(self):
        """Test conversion with complete inventory item."""
        item = {
            "sku": "TEST-SKU-001",
            "availability": {
                "shipToLocationAvailability": {
                    "quantity": 10
                }
            },
            "condition": "NEW",
            "conditionDescription": "Brand new item",
            "product": {
                "title": "Test Product",
                "description": "Test product description",
                "brand": "Test Brand",
                "mpn": "TEST-MPN",
                "upc": "123456789012",
                "categoryId": "166",
                "imageUrls": ["https://example.com/image.jpg"],
                "aspects": {
                    "Color": "Blue",
                    "Size": "Medium"
                }
            },
            "pricing": {
                "price": {
                    "value": "29.99",
                    "currency": "USD"
                }
            },
            "status": "ACTIVE",
            "createdDate": "2024-01-01T00:00:00Z",
            "lastModifiedDate": "2024-01-01T00:00:00Z"
        }
        
        result = _convert_inventory_item(item)
        
        assert result["sku"] == "TEST-SKU-001"
        assert result["title"] == "Test Product"
        assert result["description"] == "Test product description"
        assert result["brand"] == "Test Brand"
        assert result["mpn"] == "TEST-MPN"
        assert result["upc"] == "123456789012"
        assert result["condition"] == "NEW"
        assert result["condition_description"] == "Brand new item"
        assert result["category_id"] == "166"
        assert result["price"] == "29.99"
        assert result["currency"] == "USD"
        assert result["quantity"] == 10
        assert len(result["images"]) == 1
        assert result["aspects"]["Color"] == "Blue"
        assert result["aspects"]["Size"] == "Medium"
        assert result["status"] == "ACTIVE"
        assert result["created_date"] == "2024-01-01T00:00:00Z"
        assert result["last_modified_date"] == "2024-01-01T00:00:00Z"
    
    def test_convert_inventory_item_minimal(self):
        """Test conversion with minimal inventory item."""
        item = {
            "sku": "TEST-SKU-001",
            "condition": "NEW"
        }
        
        result = _convert_inventory_item(item)
        
        assert result["sku"] == "TEST-SKU-001"
        assert result["condition"] == "NEW"
        assert result["title"] is None
        assert result["quantity"] == 0
        assert result["images"] == []
        assert result["aspects"] == {}
        assert result["status"] == "ACTIVE"
    
    def test_convert_offer_complete(self):
        """Test conversion with complete offer."""
        offer = {
            "offerId": "12345678901234567890",
            "sku": "TEST-SKU-001",
            "marketplaceId": "EBAY_US",
            "format": "FIXED_PRICE",
            "categoryId": "166",
            "listing": {
                "duration": "GTC",
                "listingId": "110123456789",
                "listingStatus": "ACTIVE"
            },
            "quantitySold": 2,
            "availableQuantity": 8,
            "pricingSummary": {
                "price": {
                    "value": "29.99",
                    "currency": "USD"
                }
            },
            "status": "PUBLISHED",
            "createdDate": "2024-01-01T00:00:00Z",
            "lastModifiedDate": "2024-01-01T00:00:00Z"
        }
        
        result = _convert_offer(offer)
        
        assert result["offer_id"] == "12345678901234567890"
        assert result["sku"] == "TEST-SKU-001"
        assert result["marketplace_id"] == "EBAY_US"
        assert result["format"] == "FIXED_PRICE"
        assert result["duration"] == "GTC"
        assert result["category_id"] == "166"
        assert result["listing_id"] == "110123456789"
        assert result["listing_status"] == "ACTIVE"
        assert result["quantity_sold"] == 2
        assert result["available_quantity"] == 8
        assert result["price"] == "29.99"
        assert result["currency"] == "USD"
        assert result["status"] == "PUBLISHED"
        assert result["created_date"] == "2024-01-01T00:00:00Z"
        assert result["last_modified_date"] == "2024-01-01T00:00:00Z"


class TestCreateInventoryItem:
    """Test the create_inventory_item tool."""
    
    @pytest.mark.asyncio
    async def test_create_inventory_item_success(self, mock_context, mock_rest_client, mock_inventory_item_response):
        """Test successful inventory item creation."""
        with patch('tools.inventory_api.EbayRestClient') as mock_client_class:
            mock_client_class.return_value = mock_rest_client
            mock_rest_client.put.return_value = {}
            mock_rest_client.get.return_value = mock_inventory_item_response
            
            result = await create_inventory_item.fn(
                ctx=mock_context,
                sku="TEST-SKU-001",
                title="Test Product",
                description="Test product description",
                category_id="166",
                price=29.99,
                quantity=10,
                condition="NEW"
            )
            
            result_data = json.loads(result)
            assert result_data["status"] == "success"
            assert result_data["data"]["inventory_item"]["sku"] == "TEST-SKU-001"
            assert result_data["data"]["inventory_item"]["title"] == "Test Product"
            assert result_data["data"]["inventory_item"]["price"] == "29.99"
            assert result_data["data"]["inventory_item"]["quantity"] == 10
            assert result_data["data"]["data_source"] == "live_api"
            
            # Verify API calls
            mock_rest_client.put.assert_called_once()
            mock_rest_client.get.assert_called_once_with(
                "/sell/inventory/v1/inventory_item/TEST-SKU-001",
                scope="https://api.ebay.com/oauth/api_scope/sell.inventory"
            )
    
    @pytest.mark.asyncio
    async def test_create_inventory_item_no_credentials(self, mock_context):
        """Test without credentials returns static data."""
        with patch('tools.inventory_api.mcp') as mock_mcp:
            mock_mcp.config.app_id = ""
            mock_mcp.config.cert_id = ""
            
            result = await create_inventory_item.fn(
                ctx=mock_context,
                sku="TEST-SKU-001",
                title="Test Product",
                description="Test product description",
                category_id="166",
                price=29.99,
                quantity=10
            )
            
            result_data = json.loads(result)
            assert result_data["status"] == "success"
            assert result_data["data"]["data_source"] == "static_fallback"
            assert result_data["data"]["inventory_item"]["sku"] == "TEST-SKU-001"
            assert "Live inventory management requires eBay API credentials" in result_data["data"]["note"]
    
    @pytest.mark.asyncio
    async def test_create_inventory_item_validation_error(self, mock_context):
        """Test validation error handling."""
        result = await create_inventory_item.fn(
            ctx=mock_context,
            sku="INVALID@SKU",
            title="Test Product",
            description="Test description",
            category_id="166",
            price=29.99,
            quantity=10
        )
        
        result_data = json.loads(result)
        assert result_data["status"] == "error"
        assert result_data["error_code"] == "VALIDATION_ERROR"
    
    @pytest.mark.asyncio
    async def test_create_inventory_item_api_error(self, mock_context, mock_rest_client):
        """Test API error handling."""
        with patch('tools.inventory_api.EbayRestClient') as mock_client_class:
            mock_client_class.return_value = mock_rest_client
            mock_rest_client.put.side_effect = EbayApiError(
                status_code=400,
                error_response={"message": "Invalid category ID"}
            )
            
            result = await create_inventory_item.fn(
                ctx=mock_context,
                sku="TEST-SKU-001",
                title="Test Product",
                description="Test description",
                category_id="999999",  # Invalid category
                price=29.99,
                quantity=10
            )
            
            result_data = json.loads(result)
            assert result_data["status"] == "error"
            assert result_data["error_code"] == "EXTERNAL_API_ERROR"


class TestGetInventoryItems:
    """Test the get_inventory_items tool."""
    
    @pytest.mark.asyncio
    async def test_get_inventory_items_success(self, mock_context, mock_rest_client, mock_inventory_items_response):
        """Test successful inventory items retrieval."""
        with patch('tools.inventory_api.EbayRestClient') as mock_client_class:
            mock_client_class.return_value = mock_rest_client
            mock_rest_client.get.return_value = mock_inventory_items_response
            
            result = await get_inventory_items.fn(
                ctx=mock_context,
                limit=25,
                offset=0
            )
            
            result_data = json.loads(result)
            assert result_data["status"] == "success"
            assert len(result_data["data"]["inventory_items"]) == 2
            assert result_data["data"]["total_items"] == 2
            assert result_data["data"]["inventory_items"][0]["sku"] == "TEST-SKU-001"
            assert result_data["data"]["inventory_items"][1]["sku"] == "TEST-SKU-002"
            assert result_data["data"]["data_source"] == "live_api"
            
            # Verify API call
            mock_rest_client.get.assert_called_once_with(
                "/sell/inventory/v1/inventory_item",
                params={"limit": 25, "offset": 0},
                scope="https://api.ebay.com/oauth/api_scope/sell.inventory"
            )
    
    @pytest.mark.asyncio
    async def test_get_inventory_items_with_sku_filter(self, mock_context, mock_rest_client, mock_inventory_items_response):
        """Test inventory items retrieval with SKU filter."""
        with patch('tools.inventory_api.EbayRestClient') as mock_client_class:
            mock_client_class.return_value = mock_rest_client
            mock_rest_client.get.return_value = mock_inventory_items_response
            
            result = await get_inventory_items.fn(
                ctx=mock_context,
                sku="TEST-SKU-001",
                limit=25,
                offset=0
            )
            
            result_data = json.loads(result)
            assert result_data["status"] == "success"
            
            # Verify API call with SKU parameter
            mock_rest_client.get.assert_called_once_with(
                "/sell/inventory/v1/inventory_item",
                params={"sku": "TEST-SKU-001", "limit": 25, "offset": 0},
                scope="https://api.ebay.com/oauth/api_scope/sell.inventory"
            )
    
    @pytest.mark.asyncio
    async def test_get_inventory_items_no_credentials(self, mock_context):
        """Test without credentials returns static data."""
        with patch('tools.inventory_api.mcp') as mock_mcp:
            mock_mcp.config.app_id = ""
            mock_mcp.config.cert_id = ""
            
            result = await get_inventory_items.fn(
                ctx=mock_context,
                limit=25,
                offset=0
            )
            
            result_data = json.loads(result)
            assert result_data["status"] == "success"
            assert result_data["data"]["data_source"] == "static_fallback"
            assert len(result_data["data"]["inventory_items"]) == 1
            assert "Live inventory data requires eBay API credentials" in result_data["data"]["note"]


class TestCreateOffer:
    """Test the create_offer tool."""
    
    @pytest.mark.asyncio
    async def test_create_offer_success(self, mock_context, mock_rest_client, mock_offer_response):
        """Test successful offer creation."""
        with patch('tools.inventory_api.EbayRestClient') as mock_client_class:
            mock_client_class.return_value = mock_rest_client
            mock_rest_client.post.return_value = mock_offer_response
            
            result = await create_offer.fn(
                ctx=mock_context,
                sku="TEST-SKU-001",
                category_id="166",
                marketplace_id="EBAY_US",
                format="FIXED_PRICE",
                duration="GTC"
            )
            
            result_data = json.loads(result)
            assert result_data["status"] == "success"
            assert result_data["data"]["offer"]["offer_id"] == "12345678901234567890"
            assert result_data["data"]["offer"]["sku"] == "TEST-SKU-001"
            assert result_data["data"]["offer"]["marketplace_id"] == "EBAY_US"
            assert result_data["data"]["offer"]["format"] == "FIXED_PRICE"
            assert result_data["data"]["data_source"] == "live_api"
            
            # Verify API call
            mock_rest_client.post.assert_called_once_with(
                "/sell/inventory/v1/offer",
                json={
                    "sku": "TEST-SKU-001",
                    "marketplaceId": "EBAY_US",
                    "format": "FIXED_PRICE",
                    "categoryId": "166",
                    "listingDuration": "GTC",
                    "listingPolicies": {}
                },
                scope="https://api.ebay.com/oauth/api_scope/sell.inventory"
            )
    
    @pytest.mark.asyncio
    async def test_create_offer_with_policies(self, mock_context, mock_rest_client, mock_offer_response):
        """Test offer creation with business policies."""
        with patch('tools.inventory_api.EbayRestClient') as mock_client_class:
            mock_client_class.return_value = mock_rest_client
            mock_rest_client.post.return_value = mock_offer_response
            
            result = await create_offer.fn(
                ctx=mock_context,
                sku="TEST-SKU-001",
                category_id="166",
                payment_policy_id="payment_123",
                shipping_policy_id="shipping_456",
                return_policy_id="return_789"
            )
            
            result_data = json.loads(result)
            assert result_data["status"] == "success"
            
            # Verify API call includes policies
            call_args = mock_rest_client.post.call_args
            assert call_args[1]["json"]["listingPolicies"]["paymentPolicyId"] == "payment_123"
            assert call_args[1]["json"]["listingPolicies"]["shippingPolicyId"] == "shipping_456"
            assert call_args[1]["json"]["listingPolicies"]["returnPolicyId"] == "return_789"
    
    @pytest.mark.asyncio
    async def test_create_offer_no_credentials(self, mock_context):
        """Test without credentials returns static data."""
        with patch('tools.inventory_api.mcp') as mock_mcp:
            mock_mcp.config.app_id = ""
            mock_mcp.config.cert_id = ""
            
            result = await create_offer.fn(
                ctx=mock_context,
                sku="TEST-SKU-001",
                category_id="166"
            )
            
            result_data = json.loads(result)
            assert result_data["status"] == "success"
            assert result_data["data"]["data_source"] == "static_fallback"
            assert result_data["data"]["offer"]["sku"] == "TEST-SKU-001"
            assert "Live offer management requires eBay API credentials" in result_data["data"]["note"]


class TestPublishOffer:
    """Test the publish_offer tool."""
    
    @pytest.mark.asyncio
    async def test_publish_offer_success(self, mock_context, mock_rest_client, mock_publish_response):
        """Test successful offer publication."""
        with patch('tools.inventory_api.EbayRestClient') as mock_client_class:
            mock_client_class.return_value = mock_rest_client
            mock_rest_client.post.return_value = mock_publish_response
            
            result = await publish_offer.fn(
                ctx=mock_context,
                offer_id="12345678901234567890"
            )
            
            result_data = json.loads(result)
            assert result_data["status"] == "success"
            assert result_data["data"]["offer_id"] == "12345678901234567890"
            assert result_data["data"]["listing_id"] == "110123456789"
            assert result_data["data"]["status"] == "PUBLISHED"
            assert result_data["data"]["data_source"] == "live_api"
            
            # Verify API call
            mock_rest_client.post.assert_called_once_with(
                "/sell/inventory/v1/offer/12345678901234567890/publish",
                scope="https://api.ebay.com/oauth/api_scope/sell.inventory"
            )
    
    @pytest.mark.asyncio
    async def test_publish_offer_no_credentials(self, mock_context):
        """Test without credentials returns static data."""
        with patch('tools.inventory_api.mcp') as mock_mcp:
            mock_mcp.config.app_id = ""
            mock_mcp.config.cert_id = ""
            
            result = await publish_offer.fn(
                ctx=mock_context,
                offer_id="12345678901234567890"
            )
            
            result_data = json.loads(result)
            assert result_data["status"] == "success"
            assert result_data["data"]["data_source"] == "static_fallback"
            assert result_data["data"]["offer_id"] == "12345678901234567890"
            assert "Live offer publishing requires eBay API credentials" in result_data["data"]["note"]
    
    @pytest.mark.asyncio
    async def test_publish_offer_api_error(self, mock_context, mock_rest_client):
        """Test API error handling."""
        with patch('tools.inventory_api.EbayRestClient') as mock_client_class:
            mock_client_class.return_value = mock_rest_client
            mock_rest_client.post.side_effect = EbayApiError(
                status_code=400,
                error_response={"message": "Offer not ready for publication"}
            )
            
            result = await publish_offer.fn(
                ctx=mock_context,
                offer_id="12345678901234567890"
            )
            
            result_data = json.loads(result)
            assert result_data["status"] == "error"
            assert result_data["error_code"] == "EXTERNAL_API_ERROR"