"""Integration tests for Trading API tools with the MCP server."""
import pytest
from unittest.mock import patch, Mock, MagicMock
import os

# Set required environment variables for testing
os.environ["EBAY_APP_ID"] = "test_app_id"
os.environ["EBAY_CERT_ID"] = "test_cert_id"
os.environ["EBAY_DEV_ID"] = "test_dev_id"


class TestTradingAPIIntegration:
    """Test Trading API tools integration with MCP server."""
    
    def test_trading_api_tools_exist(self):
        """Test that all Trading API tools can be imported."""
        from tools.trading_api import (
            create_listing,
            revise_listing,
            end_listing,
            get_my_ebay_selling,
            get_user_info
        )
        
        # Check tools are FunctionTool objects (decorated with @mcp.tool)
        from fastmcp.tools.tool import FunctionTool
        assert isinstance(create_listing, FunctionTool)
        assert isinstance(revise_listing, FunctionTool)
        assert isinstance(end_listing, FunctionTool)
        assert isinstance(get_my_ebay_selling, FunctionTool)
        assert isinstance(get_user_info, FunctionTool)
        
        # Check underlying functions are callable
        assert callable(create_listing.fn)
        assert callable(revise_listing.fn)
        assert callable(end_listing.fn)
        assert callable(get_my_ebay_selling.fn)
        assert callable(get_user_info.fn)
        
        # Check docstrings exist
        assert create_listing.fn.__doc__ is not None
        assert "Create a new eBay listing" in create_listing.fn.__doc__
        assert revise_listing.fn.__doc__ is not None
        assert "Update an existing eBay listing" in revise_listing.fn.__doc__
    
    @pytest.mark.asyncio
    async def test_trading_api_in_server_imports(self):
        """Test that Trading API tools are registered with MCP server."""
        from lootly_server import create_lootly_server
        
        # Create server to register all tools
        server = create_lootly_server()
        
        # Check the tools are registered with the server
        tools = await server.get_tools()
        tool_names = set(tools.keys())
        expected_tools = {'create_listing', 'revise_listing', 'end_listing', 'get_my_ebay_selling', 'get_user_info'}
        
        for tool_name in expected_tools:
            assert tool_name in tool_names, f"Tool {tool_name} not registered with server"
    
    def test_config_supports_trading_api(self):
        """Test that EbayConfig includes Trading API fields."""
        from config import EbayConfig
        
        # Create config with Trading API credentials
        config = EbayConfig(
            app_id="test_app_id",
            cert_id="test_cert_id",
            dev_id="test_dev_id"
        )
        
        # Verify Trading API specific fields
        assert config.cert_id == "test_cert_id"
        assert config.dev_id == "test_dev_id"
        
        # Test from_env method includes Trading API fields
        config_from_env = EbayConfig.from_env()
        assert config_from_env.cert_id == "test_cert_id"
        assert config_from_env.dev_id == "test_dev_id"
    
    def test_ebay_client_supports_trading_api(self):
        """Test that EbayApiClient has Trading API support."""
        from api.ebay_client import EbayApiClient
        from config import EbayConfig
        from logging_config import MCPLogger
        
        config = EbayConfig(
            app_id="test_app_id",
            cert_id="test_cert_id",
            dev_id="test_dev_id"
        )
        logger = Mock(spec=MCPLogger)
        
        client = EbayApiClient(config, logger)
        
        # Test that trading property exists and works
        with patch('api.ebay_client.Trading') as mock_trading:
            mock_trading_instance = Mock()
            mock_trading.return_value = mock_trading_instance
            
            # Access trading property
            trading_api = client.trading
            
            # Verify Trading was initialized with correct parameters
            mock_trading.assert_called_once_with(
                appid="test_app_id",
                devid="test_dev_id",
                certid="test_cert_id",
                config_file=None,
                siteid="EBAY-US",
                domain="api.sandbox.ebay.com"
            )
            
            # Verify instance is cached
            trading_api2 = client.trading
            assert trading_api is trading_api2
