"""Import and configuration tests for Shopping API."""
import pytest
from unittest.mock import patch, Mock, MagicMock
import os

# Set required environment variables for testing
os.environ["EBAY_APP_ID"] = "test_app_id"


class TestShoppingAPIImports:
    """Test Shopping API tools imports and configuration."""
    
    def test_shopping_api_tools_exist(self):
        """Test that all Shopping API tools can be imported."""
        from tools.shopping_api import (
            get_single_item,
            get_item_status,
            get_shipping_costs,
            get_multiple_items,
            find_products,
            get_user_profile,
            get_category_info
        )
        
        # Check tools are FunctionTool objects (decorated with @mcp.tool)
        from fastmcp.tools.tool import FunctionTool
        assert isinstance(get_single_item, FunctionTool)
        assert isinstance(get_item_status, FunctionTool)
        assert isinstance(get_shipping_costs, FunctionTool)
        assert isinstance(get_multiple_items, FunctionTool)
        assert isinstance(find_products, FunctionTool)
        assert isinstance(get_user_profile, FunctionTool)  # Deprecated but still exists
        assert isinstance(get_category_info, FunctionTool)  # Deprecated but still exists
        
        # Check underlying functions are callable
        assert callable(get_single_item.fn)
        assert callable(get_item_status.fn)
        assert callable(get_shipping_costs.fn)
        assert callable(get_multiple_items.fn)
        assert callable(find_products.fn)
        assert callable(get_user_profile.fn)
        assert callable(get_category_info.fn)
        
        # Check docstrings exist
        assert get_single_item.fn.__doc__ is not None
        assert "detailed public information" in get_single_item.fn.__doc__
        assert get_item_status.fn.__doc__ is not None
        assert "item availability" in get_item_status.fn.__doc__
    
    @pytest.mark.asyncio
    async def test_shopping_api_in_server_imports(self):
        """Test that Shopping API tools are registered with MCP server."""
        from lootly_server import create_lootly_server
        
        # Create server to register all tools
        server = create_lootly_server()
        
        # Check the tools are registered with the server
        tools = await server.get_tools()
        tool_names = set(tools.keys())
        expected_tools = {'get_single_item', 'get_item_status', 'get_shipping_costs', 'get_multiple_items', 'find_products', 'get_user_profile', 'get_category_info'}
        
        for tool_name in expected_tools:
            assert tool_name in tool_names, f"Tool {tool_name} not registered with server"
    
    def test_config_supports_shopping_api(self):
        """Test that EbayConfig includes Shopping API fields."""
        from config import EbayConfig
        
        # Create config with Shopping API credentials
        config = EbayConfig(app_id="test_app_id")
        
        # Verify Shopping API uses app_id
        assert config.app_id == "test_app_id"
        assert config.site_id == "EBAY-US"  # Default
        
        # Shopping API doesn't require cert_id or dev_id
        assert hasattr(config, 'app_id')
    
    def test_ebay_client_supports_shopping_api(self):
        """Test that EbayApiClient has Shopping API support."""
        from api.ebay_client import EbayApiClient
        from config import EbayConfig
        from logging_config import MCPLogger
        
        config = EbayConfig(app_id="test_app_id")
        logger = Mock(spec=MCPLogger)
        
        client = EbayApiClient(config, logger)
        
        # Test that shopping property exists and works
        with patch('api.ebay_client.Shopping') as mock_shopping:
            mock_shopping_instance = Mock()
            mock_shopping.return_value = mock_shopping_instance
            
            # Access shopping property
            shopping_api = client.shopping
            
            # Verify Shopping was initialized with correct parameters
            mock_shopping.assert_called_once_with(
                appid="test_app_id",
                config_file=None,
                siteid="EBAY-US",
                domain="open.api.sandbox.ebay.com"
            )
            
            # Verify instance is cached
            shopping_api2 = client.shopping
            assert shopping_api is shopping_api2
    
    def test_shopping_api_tool_count(self):
        """Verify Shopping API has the expected number of tools."""
        from tools import shopping_api
        
        # List of known tool names for Shopping API
        expected_tools = {
            'get_single_item',
            'get_item_status',
            'get_shipping_costs',
            'get_multiple_items',
            'find_products',
            'get_user_profile',  # Deprecated but still exists
            'get_category_info'  # Deprecated but still exists
        }
        
        # Get all FunctionTool objects
        from fastmcp.tools.tool import FunctionTool
        actual_tools = {
            attr for attr in dir(shopping_api)
            if not attr.startswith('_') and 
            isinstance(getattr(shopping_api, attr), FunctionTool) and
            attr in expected_tools
        }
        
        # Verify all expected tools exist
        assert actual_tools == expected_tools, f"Tool mismatch. Expected: {expected_tools}, Found: {actual_tools}"
