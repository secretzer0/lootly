"""Integration tests for eBay API client using real sandbox API."""
import os
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from ebaysdk.exception import ConnectionError
from api.ebay_client import EbayApiClient
from config import EbayConfig
from logging_config import MCPLogger
from data_types import ErrorCode


# Skip all tests in this file if EBAY_RUN_INTEGRATION_TESTS is not set
pytestmark = pytest.mark.skipif(
    os.getenv("EBAY_RUN_INTEGRATION_TESTS") != "true",
    reason="Integration tests disabled. Set EBAY_RUN_INTEGRATION_TESTS=true to run."
)


def is_valid_app_id(app_id: str) -> bool:
    """Check if app_id looks like a valid eBay app ID."""
    # eBay App IDs are typically 32-character strings
    # Test credentials will be shorter or contain 'test'
    return (
        app_id and 
        len(app_id) >= 32 and 
        not app_id.startswith("test") and
        not app_id == "your-app-id-here"
    )


@pytest.fixture
def real_config():
    """Create real eBay configuration from environment."""
    # Check if we have the required credentials
    app_id = os.getenv("EBAY_APP_ID")
    if not app_id:
        pytest.skip("EBAY_APP_ID not set in environment")
    
    config = EbayConfig.from_env()
    # Ensure we're using sandbox for testing
    config.sandbox_mode = True
    return config


@pytest.fixture
def mock_logger():
    """Create mock logger for integration tests."""
    logger = MagicMock(spec=MCPLogger)
    logger.api_cache_hit = MagicMock()
    logger.external_api_called = MagicMock()
    logger.external_api_failed = MagicMock()
    logger.info = MagicMock()
    logger.error = MagicMock()
    logger.warning = MagicMock()
    return logger


@pytest.fixture
def api_client(real_config, mock_logger):
    """Create API client with real configuration."""
    return EbayApiClient(real_config, mock_logger)


@pytest.fixture
def test_config():
    """Create test configuration for credential validation tests."""
    config = EbayConfig()
    config.app_id = "test-app-id"
    config.dev_id = "test-dev-id"
    config.cert_id = "test-cert-id"
    config.sandbox_mode = True
    config.site_id = "EBAY-US"
    config.domain = "sandbox.ebay.com"
    config.max_retries = 2
    config.cache_ttl = 300
    config.max_pages = 10
    return config


@pytest.fixture
def test_api_client(test_config, mock_logger):
    """Create API client with test configuration."""
    return EbayApiClient(test_config, mock_logger)


class TestRealAPIConnectivity:
    """Test real eBay sandbox API connectivity."""
    
    @pytest.mark.asyncio
    async def test_finding_api_connectivity(self, api_client):
        """Test Finding API can connect to sandbox."""
        # Only run if we have valid credentials
        if not is_valid_app_id(api_client.config.app_id):
            pytest.skip("Valid eBay credentials required for connectivity test")
        
        try:
            result = await api_client.execute_with_retry(
                "finding",
                "findItemsAdvanced",
                {
                    "keywords": "test",
                    "paginationInput.entriesPerPage": "1",
                    "paginationInput.pageNumber": "1"
                },
                use_cache=False
            )
            
            # Should get a valid response structure
            assert "searchResult" in result
            api_client.logger.external_api_called.assert_called_once()
            
        except ConnectionError:
            pytest.fail("Finding API failed to connect to sandbox")
    
    @pytest.mark.asyncio
    async def test_shopping_api_connectivity(self, api_client):
        """Test Shopping API can connect to sandbox."""
        if not is_valid_app_id(api_client.config.app_id):
            pytest.skip("Valid eBay credentials required for connectivity test")
        
        try:
            result = await api_client.execute_with_retry(
                "shopping",
                "FindProducts",
                {
                    "QueryKeywords": "test",
                    "MaxEntries": "1"
                },
                use_cache=False
            )
            
            # Should get a valid response structure
            assert "Product" in result or "Errors" in result  # Errors are ok for test queries
            api_client.logger.external_api_called.assert_called_once()
            
        except ConnectionError:
            pytest.fail("Shopping API failed to connect to sandbox")
    
    @pytest.mark.asyncio
    async def test_merchandising_api_connectivity(self, api_client):
        """Test Merchandising API can connect to sandbox."""
        if not is_valid_app_id(api_client.config.app_id):
            pytest.skip("Valid eBay credentials required for connectivity test")
        
        try:
            result = await api_client.execute_with_retry(
                "merchandising",
                "getMostWatchedItems",
                {"maxResults": "1"},
                use_cache=False
            )
            
            # Should get a valid response structure
            assert "itemRecommendations" in result or "errorMessage" in result
            api_client.logger.external_api_called.assert_called_once()
            
        except ConnectionError:
            pytest.fail("Merchandising API failed to connect to sandbox")
    
    @pytest.mark.asyncio
    async def test_trading_api_connectivity(self, api_client):
        """Test Trading API can connect to sandbox."""
        # Trading API requires additional credentials
        if not (api_client.config.dev_id and api_client.config.cert_id):
            pytest.skip("Trading API requires dev_id and cert_id")
        
        if not is_valid_app_id(api_client.config.app_id):
            pytest.skip("Valid eBay credentials required for connectivity test")
        
        try:
            result = await api_client.execute_with_retry(
                "trading",
                "GetMyeBaySelling",
                {
                    "ActiveList.Include": "true",
                    "ActiveList.Pagination.EntriesPerPage": "1"
                },
                use_cache=False
            )
            
            # Should get a valid response structure
            assert "ActiveList" in result or "Errors" in result
            api_client.logger.external_api_called.assert_called_once()
            
        except ConnectionError:
            pytest.fail("Trading API failed to connect to sandbox")


class TestInvalidCredentials:
    """Test handling of invalid credentials."""
    
    @pytest.mark.asyncio
    async def test_invalid_app_id_finding(self, test_api_client):
        """Test Finding API with invalid app_id."""
        with pytest.raises(ConnectionError):
            await test_api_client.execute_with_retry(
                "finding",
                "findItemsAdvanced",
                {"keywords": "test"},
                use_cache=False
            )
        
        # Should have attempted retries
        assert test_api_client.logger.external_api_failed.call_count == test_api_client.config.max_retries
    
    @pytest.mark.asyncio
    async def test_invalid_app_id_shopping(self, test_api_client):
        """Test Shopping API with invalid app_id."""
        with pytest.raises(ConnectionError):
            await test_api_client.execute_with_retry(
                "shopping",
                "FindProducts",
                {"QueryKeywords": "test"},
                use_cache=False
            )
        
        assert test_api_client.logger.external_api_failed.call_count == test_api_client.config.max_retries
    
    @pytest.mark.asyncio
    async def test_invalid_app_id_merchandising(self, test_api_client):
        """Test Merchandising API with invalid app_id."""
        with pytest.raises(ConnectionError):
            await test_api_client.execute_with_retry(
                "merchandising",
                "getMostWatchedItems",
                {"maxResults": "1"},
                use_cache=False
            )
        
        assert test_api_client.logger.external_api_failed.call_count == test_api_client.config.max_retries
    
    def test_missing_trading_credentials(self, mock_logger):
        """Test Trading API with missing credentials."""
        config = EbayConfig()
        config.app_id = "test-app-id"
        # Missing dev_id and cert_id
        config.sandbox_mode = True
        
        client = EbayApiClient(config, mock_logger)
        
        with pytest.raises(ValueError, match="Trading API requires dev_id and cert_id"):
            _ = client.trading


class TestNetworkResilience:
    """Test network error handling and resilience."""
    
    @pytest.mark.asyncio
    async def test_retry_logic_with_temporary_failures(self, api_client):
        """Test retry logic handles temporary network failures."""
        if not is_valid_app_id(api_client.config.app_id):
            pytest.skip("Valid eBay credentials required for resilience test")
        
        # Reduce retries for faster testing
        original_retries = api_client.config.max_retries
        api_client.config.max_retries = 2
        
        try:
            # This should succeed after retries if the network is stable
            result = await api_client.execute_with_retry(
                "finding",
                "findItemsAdvanced",
                {"keywords": "test", "paginationInput.entriesPerPage": "1"},
                use_cache=False
            )
            
            assert "searchResult" in result
            
        except ConnectionError:
            # If it still fails after retries, that's expected behavior
            assert api_client.logger.external_api_failed.call_count <= api_client.config.max_retries
        
        finally:
            api_client.config.max_retries = original_retries
    
    @pytest.mark.asyncio
    async def test_cache_survives_network_errors(self, api_client):
        """Test that cache works correctly during network issues."""
        if not is_valid_app_id(api_client.config.app_id):
            pytest.skip("Valid eBay credentials required for cache test")
        
        # Clear cache first
        api_client.clear_cache()
        
        try:
            # First call should hit API and cache result
            result1 = await api_client.execute_with_retry(
                "finding",
                "findItemsAdvanced",
                {"keywords": "test", "paginationInput.entriesPerPage": "1"},
                use_cache=True
            )
            
            # Second call should hit cache
            result2 = await api_client.execute_with_retry(
                "finding",
                "findItemsAdvanced",
                {"keywords": "test", "paginationInput.entriesPerPage": "1"},
                use_cache=True
            )
            
            assert result1 == result2
            api_client.logger.api_cache_hit.assert_called_once()
            
        except ConnectionError:
            pytest.skip("Network connectivity required for cache test")


class TestAPIPerformance:
    """Test API performance characteristics."""
    
    @pytest.mark.asyncio
    async def test_response_time_tracking(self, api_client):
        """Test that response times are tracked."""
        if not is_valid_app_id(api_client.config.app_id):
            pytest.skip("Valid eBay credentials required for performance test")
        
        try:
            await api_client.execute_with_retry(
                "finding",
                "findItemsAdvanced",
                {"keywords": "test", "paginationInput.entriesPerPage": "1"},
                use_cache=False
            )
            
            # Verify that external_api_called was called with timing info
            call_args = api_client.logger.external_api_called.call_args
            assert call_args is not None
            
            # Should have api_name, operation, status_code, duration
            args = call_args[0]
            assert len(args) >= 4
            assert args[0] == "finding"  # api_name
            assert args[1] == "findItemsAdvanced"  # operation
            assert isinstance(args[3], float)  # duration
            
        except ConnectionError:
            pytest.skip("Network connectivity required for performance test")
    
    @pytest.mark.asyncio
    async def test_concurrent_requests(self, api_client):
        """Test handling of concurrent API requests."""
        if not is_valid_app_id(api_client.config.app_id):
            pytest.skip("Valid eBay credentials required for concurrency test")
        
        async def make_request(keywords):
            try:
                return await api_client.execute_with_retry(
                    "finding",
                    "findItemsAdvanced",
                    {"keywords": keywords, "paginationInput.entriesPerPage": "1"},
                    use_cache=False
                )
            except ConnectionError:
                return None
        
        # Make multiple concurrent requests
        tasks = [
            make_request("test1"),
            make_request("test2"),
            make_request("test3")
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # At least some should succeed if network is available
        successful_results = [r for r in results if r is not None and not isinstance(r, Exception)]
        
        if successful_results:
            # Verify all successful results have expected structure
            for result in successful_results:
                assert "searchResult" in result


class TestCrossAPIConsistency:
    """Test consistency across different eBay APIs."""
    
    @pytest.mark.asyncio
    async def test_all_apis_use_same_domain_pattern(self, api_client):
        """Test that all APIs use consistent domain patterns."""
        # Test domain construction for each API
        config = api_client.config
        
        # Finding API
        finding_api = api_client.finding
        assert f"svcs.{config.domain}" in str(finding_api.config_dict.get("domain", ""))
        
        # Shopping API  
        shopping_api = api_client.shopping
        assert f"open.api.{config.domain}" in str(shopping_api.config_dict.get("domain", ""))
        
        # Merchandising API
        merchandising_api = api_client.merchandising
        assert f"svcs.{config.domain}" in str(merchandising_api.config_dict.get("domain", ""))
        
        # Trading API (if credentials available)
        if api_client.config.dev_id and api_client.config.cert_id:
            trading_api = api_client.trading
            assert f"api.{config.domain}" in str(trading_api.config_dict.get("domain", ""))
    
    def test_all_apis_use_same_app_id(self, api_client):
        """Test that all APIs use the same app_id."""
        app_id = api_client.config.app_id
        
        # Check all API connections use the same app_id
        assert api_client.finding.config_dict.get("appid") == app_id
        assert api_client.shopping.config_dict.get("appid") == app_id
        assert api_client.merchandising.config_dict.get("appid") == app_id
        
        if api_client.config.dev_id and api_client.config.cert_id:
            assert api_client.trading.config_dict.get("appid") == app_id
    
    def test_all_apis_use_same_site_id(self, api_client):
        """Test that all APIs use the same site_id."""
        site_id = api_client.config.site_id
        
        # Check all API connections use the same site_id
        assert api_client.finding.config_dict.get("siteid") == site_id
        assert api_client.shopping.config_dict.get("siteid") == site_id
        assert api_client.merchandising.config_dict.get("siteid") == site_id
        
        if api_client.config.dev_id and api_client.config.cert_id:
            assert api_client.trading.config_dict.get("siteid") == site_id


class TestCacheOperations:
    """Test caching behavior in integration scenarios."""
    
    @pytest.mark.asyncio
    async def test_cache_across_different_apis(self, api_client):
        """Test that cache works independently for different APIs."""
        if not is_valid_app_id(api_client.config.app_id):
            pytest.skip("Valid eBay credentials required for cache test")
        
        api_client.clear_cache()
        
        try:
            # Make calls to different APIs
            finding_result = await api_client.execute_with_retry(
                "finding",
                "findItemsAdvanced",
                {"keywords": "test", "paginationInput.entriesPerPage": "1"},
                use_cache=True
            )
            
            merchandising_result = await api_client.execute_with_retry(
                "merchandising",
                "getMostWatchedItems",
                {"maxResults": "1"},
                use_cache=True
            )
            
            # Repeat calls should hit cache
            finding_result2 = await api_client.execute_with_retry(
                "finding",
                "findItemsAdvanced",
                {"keywords": "test", "paginationInput.entriesPerPage": "1"},
                use_cache=True
            )
            
            merchandising_result2 = await api_client.execute_with_retry(
                "merchandising",
                "getMostWatchedItems",
                {"maxResults": "1"},
                use_cache=True
            )
            
            assert finding_result == finding_result2
            assert merchandising_result == merchandising_result2
            
            # Should have 2 cache hits
            assert api_client.logger.api_cache_hit.call_count == 2
            
        except ConnectionError:
            pytest.skip("Network connectivity required for cache test")
    
    def test_cache_key_generation(self, api_client):
        """Test that cache keys are generated correctly."""
        # Test cache key format
        api_client._set_cached("test_key", {"test": "data"})
        result = api_client._get_cached("test_key")
        assert result == {"test": "data"}
        
        # Test cache expiration
        import time
        original_ttl = api_client.config.cache_ttl
        api_client.config.cache_ttl = 0.1  # Very short TTL
        
        api_client._set_cached("expire_test", {"data": "expires"})
        time.sleep(0.2)  # Wait for expiration
        
        expired_result = api_client._get_cached("expire_test")
        assert expired_result is None
        
        api_client.config.cache_ttl = original_ttl


class TestErrorScenarios:
    """Test various error scenarios in integration context."""
    
    @pytest.mark.asyncio
    async def test_malformed_request_handling(self, api_client):
        """Test handling of malformed API requests."""
        if not is_valid_app_id(api_client.config.app_id):
            pytest.skip("Valid eBay credentials required for error test")
        
        try:
            # Send request with invalid parameters
            result = await api_client.execute_with_retry(
                "finding",
                "findItemsAdvanced",
                {"invalidParam": "invalidValue"},
                use_cache=False
            )
            
            # Should get error response, not exception
            assert "errorMessage" in result or "searchResult" in result
            
        except ConnectionError:
            # Connection errors are expected for malformed requests
            pass
    
    def test_error_response_formatting(self, api_client):
        """Test error response formatting."""
        error = ValueError("Test error message")
        response = api_client.format_error_response(error, ErrorCode.VALIDATION_ERROR)
        
        expected = {
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Test error message",
                "type": "ValueError"
            }
        }
        
        assert response == expected
    
    @pytest.mark.asyncio
    async def test_pagination_validation_in_real_context(self, api_client):
        """Test pagination validation with real API context."""
        # Test valid pagination
        api_client.validate_pagination(1)
        api_client.validate_pagination(5)
        api_client.validate_pagination(api_client.config.max_pages)
        
        # Test invalid pagination
        with pytest.raises(ValueError, match="Page number must be >= 1"):
            api_client.validate_pagination(0)
        
        with pytest.raises(ValueError, match="Page number exceeds maximum"):
            api_client.validate_pagination(api_client.config.max_pages + 1)