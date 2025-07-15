"""Import and configuration tests for Merchandising API."""
import pytest
from unittest.mock import patch, Mock, MagicMock
import os

# Set required environment variables for testing
os.environ["EBAY_APP_ID"] = "test_app_id"


class TestMerchandisingAPIImports:
    """Test Merchandising API tools imports and configuration."""
    
    def test_merchandising_api_tools_exist(self):
        """Test that all Merchandising API tools can be imported."""
        from tools.merchandising_api import (
            get_most_watched_items,
            get_related_category_items,
            get_similar_items,
            get_top_selling_products
        )
        
        # Check tools are FunctionTool objects (decorated with @mcp.tool)
        from fastmcp.tools.tool import FunctionTool
        assert isinstance(get_most_watched_items, FunctionTool)
        assert isinstance(get_related_category_items, FunctionTool)
        assert isinstance(get_similar_items, FunctionTool)
        assert isinstance(get_top_selling_products, FunctionTool)
        
        # Check underlying functions are callable
        assert callable(get_most_watched_items.fn)
        assert callable(get_related_category_items.fn)
        assert callable(get_similar_items.fn)
        assert callable(get_top_selling_products.fn)
        
        # Check docstrings exist
        assert get_most_watched_items.fn.__doc__ is not None
        assert "most watched items" in get_most_watched_items.fn.__doc__
        assert get_top_selling_products.fn.__doc__ is not None
        assert "top selling products" in get_top_selling_products.fn.__doc__
    
    @pytest.mark.asyncio
    async def test_merchandising_api_in_server_imports(self):
        """Test that Merchandising API tools are registered with MCP server."""
        from lootly_server import create_lootly_server
        
        # Create server to register all tools
        server = create_lootly_server()
        
        # Check the tools are registered with the server
        tools = await server.get_tools()
        tool_names = set(tools.keys())
        expected_tools = {'get_most_watched_items', 'get_related_category_items', 'get_similar_items', 'get_top_selling_products'}
        
        for tool_name in expected_tools:
            assert tool_name in tool_names, f"Tool {tool_name} not registered with server"
    
    def test_config_supports_merchandising_api(self):
        """Test that EbayConfig includes Merchandising API fields."""
        from config import EbayConfig
        
        # Create config with Merchandising API credentials
        config = EbayConfig(app_id="test_app_id")
        
        # Verify Merchandising API uses app_id
        assert config.app_id == "test_app_id"
        assert config.site_id == "EBAY-US"  # Default
        
        # Merchandising API only requires app_id
        assert hasattr(config, 'app_id')
    
    def test_ebay_client_supports_merchandising_api(self):
        """Test that EbayApiClient has Merchandising API support."""
        from api.ebay_client import EbayApiClient
        from config import EbayConfig
        from logging_config import MCPLogger
        
        config = EbayConfig(app_id="test_app_id")
        logger = Mock(spec=MCPLogger)
        
        client = EbayApiClient(config, logger)
        
        # Test that merchandising property exists and works
        with patch('api.ebay_client.Merchandising') as mock_merchandising:
            mock_merchandising_instance = Mock()
            mock_merchandising.return_value = mock_merchandising_instance
            
            # Access merchandising property
            merchandising_api = client.merchandising
            
            # Verify Merchandising was initialized with correct parameters
            mock_merchandising.assert_called_once_with(
                appid="test_app_id",
                config_file=None,
                siteid="EBAY-US",
                domain="svcs.sandbox.ebay.com"
            )
            
            # Verify instance is cached
            merchandising_api2 = client.merchandising
            assert merchandising_api is merchandising_api2
    
    def test_merchandising_api_tool_count(self):
        """Verify Merchandising API has the expected number of tools."""
        from tools import merchandising_api
        
        # List of known tool names for Merchandising API
        expected_tools = {
            'get_most_watched_items',
            'get_related_category_items',
            'get_similar_items',
            'get_top_selling_products'
        }
        
        # Get all FunctionTool objects
        from fastmcp.tools.tool import FunctionTool
        actual_tools = {
            attr for attr in dir(merchandising_api)
            if not attr.startswith('_') and 
            isinstance(getattr(merchandising_api, attr), FunctionTool) and
            attr in expected_tools
        }
        
        # Verify all expected tools exist
        assert actual_tools == expected_tools, f"Tool mismatch. Expected: {expected_tools}, Found: {actual_tools}"
