"""Integration tests for Inventory API tools."""
import pytest
from unittest.mock import patch, AsyncMock
import json
from fastmcp import Context

from tools.inventory_api import (
    get_inventory_item,
    update_inventory_item,
    delete_inventory_item,
    bulk_update_inventory,
    get_offer,
    update_offer,
    delete_offer,
    withdraw_offer
)


@pytest.fixture
def mock_context():
    """Create a mock FastMCP context."""
    ctx = AsyncMock(spec=Context)
    ctx.info = AsyncMock()
    ctx.error = AsyncMock()
    ctx.debug = AsyncMock()
    ctx.report_progress = AsyncMock()
    return ctx


class TestInventoryManagementIntegration:
    """Integration tests for new inventory management functions."""
    
    @pytest.mark.asyncio
    async def test_get_inventory_item_without_credentials(self, mock_context):
        """Test get_inventory_item returns static fallback without credentials."""
        # Temporarily clear credentials to force static fallback
        with patch('tools.inventory_api.mcp') as mock_mcp:
            mock_mcp.config.app_id = ""
            mock_mcp.config.cert_id = ""
            
            result = await get_inventory_item.fn(
                ctx=mock_context,
                sku="TEST-SKU-001"
            )
            
            result_data = json.loads(result)
            assert result_data["status"] == "success"
            assert result_data["data"]["data_source"] == "static_fallback"
            assert "Live inventory data requires eBay API credentials" in result_data["data"]["note"]
    
    @pytest.mark.asyncio
    async def test_update_inventory_item_static_fallback(self, mock_context):
        """Test update_inventory_item returns static fallback without credentials."""
        # Temporarily clear credentials to force static fallback
        with patch('tools.inventory_api.mcp') as mock_mcp:
            mock_mcp.config.app_id = ""
            mock_mcp.config.cert_id = ""
            
            result = await update_inventory_item.fn(
                ctx=mock_context,
                sku="TEST-SKU-001",
                title="Updated Title"  # Provide at least one field
            )
            
            result_data = json.loads(result)
            assert result_data["status"] == "success"
            assert result_data["data"]["data_source"] == "static_fallback"
            assert "Live inventory updates require eBay API credentials" in result_data["data"]["note"]
    
    @pytest.mark.asyncio
    async def test_update_inventory_item_requires_user_consent(self, mock_context):
        """Test update_inventory_item requires user consent with credentials."""
        # This will fail user consent check and return authentication error
        result = await update_inventory_item.fn(
            ctx=mock_context,
            sku="TEST-SKU-001",
            title="Updated Title"
        )
        
        result_data = json.loads(result)
        assert result_data["status"] == "error"
        assert result_data["error_code"] == "AUTHENTICATION_ERROR"
        assert "User consent required" in result_data["error_message"]
    
    @pytest.mark.asyncio
    async def test_delete_inventory_item_requires_user_consent(self, mock_context):
        """Test delete_inventory_item requires user consent."""
        result = await delete_inventory_item.fn(
            ctx=mock_context,
            sku="TEST-SKU-001"
        )
        
        result_data = json.loads(result)
        assert result_data["status"] == "error"
        assert result_data["error_code"] == "AUTHENTICATION_ERROR"
        assert "User consent required" in result_data["error_message"]
    
    @pytest.mark.asyncio
    async def test_bulk_update_inventory_validation_error(self, mock_context):
        """Test bulk_update_inventory validates input structure."""
        # Invalid updates - missing required sku field
        updates = [
            {"title": "Missing SKU"}
        ]
        
        result = await bulk_update_inventory.fn(
            ctx=mock_context,
            updates=updates,
            currency="USD"
        )
        
        result_data = json.loads(result)
        assert result_data["status"] == "error"
        assert result_data["error_code"] == "VALIDATION_ERROR"


class TestOfferManagementIntegration:
    """Integration tests for new offer management functions."""
    
    @pytest.mark.asyncio
    async def test_get_offer_without_credentials(self, mock_context):
        """Test get_offer returns static fallback without credentials."""
        # Temporarily clear credentials to force static fallback
        with patch('tools.inventory_api.mcp') as mock_mcp:
            mock_mcp.config.app_id = ""
            mock_mcp.config.cert_id = ""
            
            result = await get_offer.fn(
                ctx=mock_context,
                offer_id="12345678901234567890"
            )
            
            result_data = json.loads(result)
            assert result_data["status"] == "success"
            assert result_data["data"]["data_source"] == "static_fallback"
            assert "Live offer data requires eBay API credentials" in result_data["data"]["note"]
    
    @pytest.mark.asyncio
    async def test_update_offer_requires_user_consent(self, mock_context):
        """Test update_offer requires user consent."""
        result = await update_offer.fn(
            ctx=mock_context,
            offer_id="12345678901234567890",
            quantity=20
        )
        
        result_data = json.loads(result)
        assert result_data["status"] == "error"
        assert result_data["error_code"] == "AUTHENTICATION_ERROR"
        assert "User consent required" in result_data["error_message"]
    
    @pytest.mark.asyncio
    async def test_delete_offer_requires_user_consent(self, mock_context):
        """Test delete_offer requires user consent."""
        result = await delete_offer.fn(
            ctx=mock_context,
            offer_id="12345678901234567890"
        )
        
        result_data = json.loads(result)
        assert result_data["status"] == "error"
        assert result_data["error_code"] == "AUTHENTICATION_ERROR"
        assert "User consent required" in result_data["error_message"]
    
    @pytest.mark.asyncio
    async def test_withdraw_offer_requires_user_consent(self, mock_context):
        """Test withdraw_offer requires user consent."""
        result = await withdraw_offer.fn(
            ctx=mock_context,
            offer_id="12345678901234567890"
        )
        
        result_data = json.loads(result)
        assert result_data["status"] == "error"
        assert result_data["error_code"] == "AUTHENTICATION_ERROR"
        assert "User consent required" in result_data["error_message"]


class TestEnhancedResponseIntegration:
    """Integration tests for enhanced URLs and feedback features."""
    
    @pytest.mark.asyncio
    async def test_enhanced_response_structure_integration(self, mock_context):
        """Test that functions include enhanced response structure in real execution."""
        # Test with credentials present - should get enhanced URLs
        result = await get_inventory_item.fn(
            ctx=mock_context,
            sku="TEST-SKU-001"
        )
        
        result_data = json.loads(result)
        assert result_data["status"] == "success"
        
        # Should include enhanced response structure 
        data = result_data["data"]
        if data.get("data_source") == "live_api":
            # Live API should have enhanced structure
            assert "urls" in data
            assert "next_steps" in data
            assert "available_actions" in data
            
            # Check specific URLs are present
            urls = data["urls"]
            assert "seller_hub" in urls
            assert "edit_item" in urls
            assert "help_url" in urls
            
            # Check next steps are actionable
            next_steps = data["next_steps"]
            assert len(next_steps) >= 3
            assert any("retrieved" in step.lower() for step in next_steps)
            
        elif data.get("data_source") == "static_fallback":
            # Static fallback should have basic structure
            assert "inventory_item" in data
            assert "note" in data


class TestCreateInventoryItemIntegration:
    """Integration tests for create_inventory_item tool."""
    
    @pytest.mark.asyncio
    async def test_create_inventory_item_no_credentials_static_fallback(self, mock_context):
        """Test create_inventory_item returns static data without credentials."""
        from tools.inventory_api import create_inventory_item
        
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
    async def test_create_inventory_item_validation_error_integration(self, mock_context):
        """Test create_inventory_item validation error handling."""
        from tools.inventory_api import create_inventory_item
        
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


class TestGetInventoryItemsIntegration:
    """Integration tests for get_inventory_items tool."""
    
    @pytest.mark.asyncio
    async def test_get_inventory_items_no_credentials_static_fallback(self, mock_context):
        """Test get_inventory_items returns static data without credentials."""
        from tools.inventory_api import get_inventory_items
        
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


class TestCreateOfferIntegration:
    """Integration tests for create_offer tool."""
    
    @pytest.mark.asyncio
    async def test_create_offer_no_credentials_static_fallback(self, mock_context):
        """Test create_offer returns static data without credentials."""
        from tools.inventory_api import create_offer
        
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


class TestPublishOfferIntegration:
    """Integration tests for publish_offer tool."""
    
    @pytest.mark.asyncio
    async def test_publish_offer_no_credentials_static_fallback(self, mock_context):
        """Test publish_offer returns static data without credentials."""
        from tools.inventory_api import publish_offer
        
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