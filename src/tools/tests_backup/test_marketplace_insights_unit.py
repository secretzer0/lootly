"""Unit tests for Marketplace Insights API tools."""
import pytest
from unittest.mock import patch

from tools.marketplace_insights_api import (
    _has_marketplace_insights_access,
    _convert_sales_data
)




class TestMarketplaceInsightsAccess:
    """Test access control for Marketplace Insights API."""
    
    def test_has_marketplace_insights_access_enabled(self):
        """Test access when enabled in config."""
        with patch('tools.marketplace_insights_api.mcp') as mock_mcp:
            mock_mcp.config.marketplace_insights_enabled = True
            assert _has_marketplace_insights_access() == True
    
    def test_has_marketplace_insights_access_disabled(self):
        """Test access when disabled in config."""
        with patch('tools.marketplace_insights_api.mcp') as mock_mcp:
            mock_mcp.config.marketplace_insights_enabled = False
            assert _has_marketplace_insights_access() == False
    
    def test_has_marketplace_insights_access_not_configured(self):
        """Test access when not configured."""
        with patch('tools.marketplace_insights_api.mcp') as mock_mcp:
            # No marketplace_insights_enabled attribute
            del mock_mcp.config.marketplace_insights_enabled
            assert _has_marketplace_insights_access() == False


class TestDataConversion:
    """Test data conversion functions."""
    
    def test_convert_sales_data_complete(self):
        """Test conversion with complete sales data."""
        sales_data = {
            "itemId": "v1|123456789|0",
            "title": "Test Item",
            "categoryId": "12345",
            "categoryName": "Test Category",
            "lastSoldDate": "2024-01-15T12:30:00.000Z",
            "lastSoldPrice": {
                "value": "99.99",
                "currency": "USD"
            },
            "totalSoldQuantity": 10,
            "condition": "NEW",
            "itemWebUrl": "https://ebay.com/itm/123456789",
            "image": {
                "imageUrl": "https://example.com/image.jpg"
            }
        }
        
        result = _convert_sales_data(sales_data)
        
        assert result["item_id"] == "v1|123456789|0"
        assert result["title"] == "Test Item"
        assert result["category_id"] == "12345"
        assert result["category_name"] == "Test Category"
        assert result["last_sold_date"] == "2024-01-15T12:30:00+00:00"
        assert result["last_sold_price"]["value"] == 99.99
        assert result["last_sold_price"]["currency"] == "USD"
        assert result["total_sold_quantity"] == 10
        assert result["condition"] == "NEW"
        assert result["listing_url"] == "https://ebay.com/itm/123456789"
        assert result["image_url"] == "https://example.com/image.jpg"
    
    def test_convert_sales_data_minimal(self):
        """Test conversion with minimal sales data."""
        sales_data = {
            "itemId": "v1|123456789|0",
            "title": "Test Item"
        }
        
        result = _convert_sales_data(sales_data)
        
        assert result["item_id"] == "v1|123456789|0"
        assert result["title"] == "Test Item"
        assert result["last_sold_date"] is None
        assert result["last_sold_price"]["value"] == 0.0
        assert result["last_sold_price"]["currency"] == "USD"
        assert result["total_sold_quantity"] == 0