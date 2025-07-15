"""Tests for eBay API client."""
import asyncio
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from ebaysdk.exception import ConnectionError
from config import EbayConfig
from api.ebay_client import EbayApiClient
from data_types import ErrorCode


@pytest.fixture
def mock_config():
    """Create mock eBay configuration."""
    config = MagicMock(spec=EbayConfig)
    config.app_id = "test-app-id"
    config.cert_id = "test-cert-id"
    config.dev_id = "test-dev-id"
    config.sandbox_mode = True
    config.site_id = "EBAY-US"
    config.domain = "sandbox.ebay.com"
    config.max_retries = 3
    config.cache_ttl = 300
    config.max_pages = 10
    return config


@pytest.fixture
def mock_logger():
    """Create mock logger."""
    logger = MagicMock()
    logger.api_cache_hit = MagicMock()
    logger.external_api_called = MagicMock()
    logger.external_api_failed = MagicMock()
    logger.info = MagicMock()
    return logger


@pytest.fixture
def ebay_client(mock_config, mock_logger):
    """Create eBay API client with mocks."""
    return EbayApiClient(mock_config, mock_logger)


def test_api_connections_lazy_initialization(ebay_client):
    """Test that API connections are created lazily."""
    # Initially, connections should not exist
    assert ebay_client._finding_api is None
    assert ebay_client._trading_api is None
    assert ebay_client._shopping_api is None
    assert ebay_client._merchandising_api is None
    
    # Access properties to trigger initialization
    with patch("api.ebay_client.Finding") as MockFinding:
        finding = ebay_client.finding
        MockFinding.assert_called_once()
        assert finding is not None
    
    with patch("api.ebay_client.Trading") as MockTrading:
        trading = ebay_client.trading
        MockTrading.assert_called_once()
        assert trading is not None


def test_trading_api_requires_credentials(ebay_client):
    """Test that Trading API requires dev_id and cert_id."""
    # Remove required credentials
    ebay_client.config.dev_id = None
    
    with pytest.raises(ValueError, match="Trading API requires dev_id and cert_id"):
        _ = ebay_client.trading


@pytest.mark.asyncio
async def test_execute_with_retry_success(ebay_client):
    """Test successful API execution."""
    # Mock API response
    mock_response = MagicMock()
    mock_response.dict.return_value = {"result": "success"}
    
    # Mock API execute method
    mock_api = MagicMock()
    mock_api.execute = MagicMock(return_value=mock_response)
    
    # Mock the private attribute instead of the property
    ebay_client._finding_api = mock_api
    
    result = await ebay_client.execute_with_retry(
        "finding",
        "findItemsAdvanced",
        {"keywords": "test"}
    )
    
    assert result == {"result": "success"}
    mock_api.execute.assert_called_once_with("findItemsAdvanced", {"keywords": "test"})
    ebay_client.logger.external_api_called.assert_called_once()


@pytest.mark.asyncio
async def test_execute_with_retry_cache_hit(ebay_client):
    """Test cache hit on repeated calls."""
    # Mock API response
    mock_response = MagicMock()
    mock_response.dict.return_value = {"result": "cached"}
    
    # Mock API execute method
    mock_api = MagicMock()
    mock_api.execute = MagicMock(return_value=mock_response)
    
    # Mock the private attribute instead of the property
    ebay_client._finding_api = mock_api
    
    # First call - should hit API
    result1 = await ebay_client.execute_with_retry(
        "finding",
        "findItemsAdvanced",
        {"keywords": "test"},
        use_cache=True
    )
    
    # Second call - should hit cache
    result2 = await ebay_client.execute_with_retry(
        "finding",
        "findItemsAdvanced",
        {"keywords": "test"},
        use_cache=True
    )
    
    assert result1 == result2
    # API should only be called once
    mock_api.execute.assert_called_once()
    # Cache hit should be logged
    ebay_client.logger.api_cache_hit.assert_called_once_with("finding", "findItemsAdvanced")


@pytest.mark.asyncio
async def test_execute_with_retry_failure(ebay_client):
    """Test retry logic on API failure."""
    # Mock API to fail
    mock_api = MagicMock()
    mock_api.execute = MagicMock(side_effect=ConnectionError("Network error"))
    
    # Mock the private attribute instead of the property
    ebay_client._finding_api = mock_api
    
    with pytest.raises(ConnectionError):
        await ebay_client.execute_with_retry(
            "finding",
            "findItemsAdvanced",
            {"keywords": "test"}
        )
    
    # Should retry max_retries times
    assert mock_api.execute.call_count == ebay_client.config.max_retries
    # Each failure should be logged
    assert ebay_client.logger.external_api_failed.call_count == ebay_client.config.max_retries


@pytest.mark.asyncio
async def test_execute_with_retry_eventual_success(ebay_client):
    """Test retry succeeds after initial failures."""
    mock_response = MagicMock()
    mock_response.dict.return_value = {"result": "success"}
    
    # Mock API to fail twice, then succeed
    mock_api = MagicMock()
    mock_api.execute = MagicMock(
        side_effect=[
            ConnectionError("Network error"),
            ConnectionError("Network error"),
            mock_response
        ]
    )
    
    # Mock the private attribute instead of the property
    ebay_client._finding_api = mock_api
    
    with patch("asyncio.sleep", new_callable=AsyncMock):  # Skip sleep in tests
        result = await ebay_client.execute_with_retry(
            "finding",
            "findItemsAdvanced",
            {"keywords": "test"}
        )
    
    assert result == {"result": "success"}
    assert mock_api.execute.call_count == 3
    assert ebay_client.logger.external_api_failed.call_count == 2
    assert ebay_client.logger.external_api_called.call_count == 1


def test_cache_operations(ebay_client):
    """Test cache get/set operations."""
    # Test empty cache
    assert ebay_client._get_cached("test_key") is None
    
    # Set cache
    test_data = {"test": "data"}
    ebay_client._set_cached("test_key", test_data)
    
    # Get from cache
    cached = ebay_client._get_cached("test_key")
    assert cached == test_data
    
    # Clear cache
    ebay_client.clear_cache()
    assert ebay_client._get_cached("test_key") is None
    ebay_client.logger.info.assert_called_with("Cache cleared")


def test_cache_expiration(ebay_client):
    """Test cache expiration."""
    import time
    
    # Set cache
    test_data = {"test": "data"}
    
    # Mock time for consistent testing
    current_time = time.time()
    with patch("api.ebay_client.time.time") as mock_time:
        # Set initial time for cache set
        mock_time.return_value = current_time
        ebay_client._set_cached("test_key", test_data)
        
        # Current time - should still be cached
        mock_time.return_value = current_time
        assert ebay_client._get_cached("test_key") == test_data
        
        # Jump forward past TTL
        mock_time.return_value = current_time + ebay_client.config.cache_ttl + 1
        assert ebay_client._get_cached("test_key") is None


def test_validate_pagination(ebay_client):
    """Test pagination validation."""
    # Valid page numbers
    ebay_client.validate_pagination(1)
    ebay_client.validate_pagination(5)
    ebay_client.validate_pagination(10)
    
    # Invalid page numbers
    with pytest.raises(ValueError, match="Page number must be >= 1"):
        ebay_client.validate_pagination(0)
    
    with pytest.raises(ValueError, match="Page number must be >= 1"):
        ebay_client.validate_pagination(-1)
    
    with pytest.raises(ValueError, match="Page number exceeds maximum"):
        ebay_client.validate_pagination(11)


def test_format_error_response(ebay_client):
    """Test error response formatting."""
    error = ValueError("Test error")
    response = ebay_client.format_error_response(error, ErrorCode.VALIDATION_ERROR)
    
    assert response == {
        "success": False,
        "error": {
            "code": "VALIDATION_ERROR",
            "message": "Test error",
            "type": "ValueError"
        }
    }