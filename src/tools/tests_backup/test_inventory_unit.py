"""Unit tests for Inventory API tools."""
import pytest
from datetime import datetime

from tools.inventory_api import (
    _convert_inventory_item,
    _convert_offer,
    InventoryItemInput,
    OfferInput,
    InventorySearchInput
)




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




