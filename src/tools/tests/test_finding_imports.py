"""Import and configuration tests for Finding API."""
import pytest
from unittest.mock import patch, Mock, MagicMock
import os

# Set required environment variables for testing
os.environ["EBAY_APP_ID"] = "test_app_id"


class TestFindingAPIImports:
    """Test Finding API tools imports and configuration."""
    
    def test_finding_api_tools_exist(self):
        """Test that all Finding API tools can be imported."""
        from tools.finding_api import (
            search_items,
            get_search_keywords,
            find_items_by_category,
            find_items_advanced
        )
        
        # Check tools are FunctionTool objects (decorated with @mcp.tool)
        from fastmcp.tools.tool import FunctionTool
        assert isinstance(search_items, FunctionTool)
        assert isinstance(get_search_keywords, FunctionTool)
        assert isinstance(find_items_by_category, FunctionTool)
        assert isinstance(find_items_advanced, FunctionTool)
        
        # Check underlying functions are callable
        assert callable(search_items.fn)
        assert callable(get_search_keywords.fn)
        assert callable(find_items_by_category.fn)
        assert callable(find_items_advanced.fn)
        
        # Check docstrings exist
        assert search_items.fn.__doc__ is not None
        assert "Search for items on eBay" in search_items.fn.__doc__
        assert get_search_keywords.fn.__doc__ is not None
        assert "Get keyword suggestions" in get_search_keywords.fn.__doc__
    
    @pytest.mark.asyncio
    async def test_finding_api_in_server_imports(self):
        """Test that Finding API tools are registered with MCP server."""
        from lootly_server import create_lootly_server
        
        # Create server to register all tools
        server = create_lootly_server()
        
        # Check the tools are registered with the server
        tools = await server.get_tools()
        tool_names = set(tools.keys())
        expected_tools = {'search_items', 'get_search_keywords', 'find_items_by_category', 'find_items_advanced'}
        
        for tool_name in expected_tools:
            assert tool_name in tool_names, f"Tool {tool_name} not registered with server"
    
    def test_config_supports_finding_api(self):
        """Test that EbayConfig includes Finding API fields."""
        from config import EbayConfig
        
        # Create config with Finding API credentials
        config = EbayConfig(app_id="test_app_id")
        
        # Verify Finding API specific fields
        assert config.app_id == "test_app_id"
        assert config.site_id == "EBAY-US"  # Default
        assert config.sandbox_mode is True  # Default
        
        # Test from_env method
        config_from_env = EbayConfig.from_env()
        assert config_from_env.app_id == "test_app_id"
    
    def test_ebay_client_supports_finding_api(self):
        """Test that EbayApiClient has Finding API support."""
        from api.ebay_client import EbayApiClient
        from config import EbayConfig
        from logging_config import MCPLogger
        
        config = EbayConfig(app_id="test_app_id")
        logger = Mock(spec=MCPLogger)
        
        client = EbayApiClient(config, logger)
        
        # Test that finding property exists and works
        with patch('api.ebay_client.Finding') as mock_finding:
            mock_finding_instance = Mock()
            mock_finding.return_value = mock_finding_instance
            
            # Access finding property
            finding_api = client.finding
            
            # Verify Finding was initialized with correct parameters
            mock_finding.assert_called_once_with(
                appid="test_app_id",
                config_file=None,
                siteid="EBAY-US",
                domain="svcs.sandbox.ebay.com"
            )
            
            # Verify instance is cached
            finding_api2 = client.finding
            assert finding_api is finding_api2
    
    def test_finding_api_tool_count(self):
        """Verify Finding API has the expected number of tools."""
        from tools import finding_api
        from fastmcp.tools.tool import FunctionTool
        
        # List of known tool names for Finding API
        expected_tools = {
            'search_items',
            'get_search_keywords', 
            'find_items_by_category',
            'find_items_advanced'
        }
        
        # Get all FunctionTool objects
        actual_tools = {
            attr for attr in dir(finding_api)
            if not attr.startswith('_') and 
            isinstance(getattr(finding_api, attr), FunctionTool) and
            attr in expected_tools
        }
        
        # Verify all expected tools exist
        assert actual_tools == expected_tools, f"Tool mismatch. Expected: {expected_tools}, Found: {actual_tools}"
