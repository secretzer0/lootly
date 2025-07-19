"""
Enhanced tests for the eBay OAuth implementation.

Tests the eBay-specific enhancements including retry logic, error handling,
metrics tracking, and token lifecycle management.
"""
import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timedelta, timezone
import json

from api.oauth import OAuthManager, OAuthConfig, CachedToken, OAuthScopes


@pytest.fixture
def oauth_config():
    """Create OAuth configuration for testing."""
    return OAuthConfig(
        client_id="test_client_id",
        client_secret="test_client_secret",
        sandbox=True,
        max_retries=3,
        retry_delay=0.1,  # Short delay for testing
        request_timeout=10
    )


@pytest.fixture
def oauth_manager(oauth_config):
    """Create OAuth manager for testing."""
    return OAuthManager(oauth_config)


@pytest.fixture
def mock_token_response():
    """Mock successful token response from eBay."""
    return {
        "access_token": "test_access_token_123",
        "token_type": "Bearer",
        "expires_in": 7200,
        "scope": "https://api.ebay.com/oauth/api_scope"
    }


class TestOAuthEnhancements:
    """Test OAuth enhancements for eBay-specific requirements."""
    
    @pytest.mark.asyncio
    async def test_retry_logic_success_after_failure(self, oauth_manager, mock_token_response):
        """Test that retry logic works when first request fails."""
        with patch('api.oauth.aiohttp.ClientSession') as mock_session_class:
            # Mock session and its context manager behavior
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_session_class.return_value = mock_session
            
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value=json.dumps(mock_token_response))
            mock_response.json = AsyncMock(return_value=mock_token_response)
            
            # Create counter to track calls
            call_count = 0
            
            def mock_post(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    # First call fails
                    raise Exception("Network error")
                else:
                    # Second call succeeds
                    context = AsyncMock()
                    context.__aenter__ = AsyncMock(return_value=mock_response)
                    context.__aexit__ = AsyncMock(return_value=None)
                    return context
            
            mock_session.post = MagicMock(side_effect=mock_post)
            
            token = await oauth_manager.get_client_credentials_token()
            assert token == "test_access_token_123"
            
            # Verify retry was attempted
            assert call_count == 2
    
    @pytest.mark.asyncio
    async def test_retry_logic_max_retries_exceeded(self, oauth_manager):
        """Test that retry logic fails after max retries."""
        with patch('api.oauth.aiohttp.ClientSession') as mock_session_class:
            # Mock session and its context manager behavior
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_session_class.return_value = mock_session
            
            def mock_post(*args, **kwargs):
                raise Exception("Network error")
            
            mock_session.post = MagicMock(side_effect=mock_post)
            
            with pytest.raises(Exception, match="Network error"):
                await oauth_manager.get_client_credentials_token()
            
            # Verify all retries were attempted
            assert mock_session.post.call_count == 3
    
    @pytest.mark.asyncio
    async def test_exponential_backoff_delay(self, oauth_manager):
        """Test that exponential backoff is applied between retries."""
        with patch('api.oauth.aiohttp.ClientSession') as mock_session_class, \
             patch('api.oauth.asyncio.sleep') as mock_sleep:
            
            # Mock session and its context manager behavior
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_session_class.return_value = mock_session
            
            def mock_post(*args, **kwargs):
                raise Exception("Network error")
            
            mock_session.post = MagicMock(side_effect=mock_post)
            
            with pytest.raises(Exception):
                await oauth_manager.get_client_credentials_token()
            
            # Verify exponential backoff delays
            expected_delays = [0.1, 0.2]  # base_delay * (2^attempt)
            actual_delays = [call[0][0] for call in mock_sleep.call_args_list]
            assert actual_delays == expected_delays
    
    @pytest.mark.asyncio
    async def test_oauth_error_parsing(self, oauth_manager):
        """Test eBay-specific OAuth error parsing."""
        with patch('api.oauth.aiohttp.ClientSession') as mock_session_class:
            # Mock session and its context manager behavior
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_session_class.return_value = mock_session
            
            mock_response = AsyncMock()
            mock_response.status = 400
            mock_response.text = AsyncMock(return_value=json.dumps({
                "error": "invalid_client",
                "error_description": "Client authentication failed"
            }))
            
            # Create context manager for post method
            context = AsyncMock()
            context.__aenter__ = AsyncMock(return_value=mock_response)
            context.__aexit__ = AsyncMock(return_value=None)
            mock_session.post = MagicMock(return_value=context)
            
            with pytest.raises(Exception, match="Invalid client credentials"):
                await oauth_manager.get_client_credentials_token()
    
    @pytest.mark.asyncio
    async def test_timeout_handling(self, oauth_manager):
        """Test timeout handling for OAuth requests."""
        with patch('api.oauth.aiohttp.ClientSession') as mock_session_class:
            # Mock session and its context manager behavior
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_session_class.return_value = mock_session
            
            # Create context manager that raises TimeoutError on __aenter__
            context = AsyncMock()
            context.__aenter__ = AsyncMock(side_effect=asyncio.TimeoutError())
            context.__aexit__ = AsyncMock(return_value=None)
            mock_session.post = MagicMock(return_value=context)
            
            with pytest.raises(Exception, match="OAuth request timeout"):
                await oauth_manager.get_client_credentials_token()
    
    @pytest.mark.asyncio
    async def test_metrics_tracking(self, oauth_manager, mock_token_response):
        """Test that OAuth metrics are tracked correctly."""
        with patch('api.oauth.aiohttp.ClientSession') as mock_session_class:
            # Mock session and its context manager behavior
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_session_class.return_value = mock_session
            
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value=json.dumps(mock_token_response))
            mock_response.json = AsyncMock(return_value=mock_token_response)
            
            # Create context manager for post method
            context = AsyncMock()
            context.__aenter__ = AsyncMock(return_value=mock_response)
            context.__aexit__ = AsyncMock(return_value=None)
            mock_session.post = MagicMock(return_value=context)
            
            # First request (cache miss)
            await oauth_manager.get_client_credentials_token()
            
            # Second request (cache hit)
            await oauth_manager.get_client_credentials_token()
            
            metrics = oauth_manager.get_metrics()
            assert metrics['token_requests'] == 1
            assert metrics['token_cache_hits'] == 1
            assert metrics['token_cache_misses'] == 1
            assert metrics['token_errors'] == 0
    
    @pytest.mark.asyncio
    async def test_token_validation(self, oauth_manager, mock_token_response):
        """Test token response validation."""
        with patch('api.oauth.aiohttp.ClientSession') as mock_session_class:
            # Mock session and its context manager behavior
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_session_class.return_value = mock_session
            
            # Response missing access_token
            invalid_response = {"token_type": "Bearer", "expires_in": 7200}
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value=json.dumps(invalid_response))
            mock_response.json = AsyncMock(return_value=invalid_response)
            
            # Create context manager for post method
            context = AsyncMock()
            context.__aenter__ = AsyncMock(return_value=mock_response)
            context.__aexit__ = AsyncMock(return_value=None)
            mock_session.post = MagicMock(return_value=context)
            
            with pytest.raises(Exception, match="OAuth response missing access_token"):
                await oauth_manager.get_client_credentials_token()
    
    def test_token_expiry_methods(self):
        """Test token expiry utility methods."""
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)
        token = CachedToken(
            access_token="test_token",
            expires_at=expires_at
        )
        
        assert not token.is_expired()
        assert not token.is_expired(buffer_minutes=10)
        assert token.is_expired(buffer_minutes=35)
        assert token.is_near_expiry(buffer_minutes=35)
        assert not token.is_near_expiry(buffer_minutes=5)
        
        time_until = token.time_until_expiry()
        assert isinstance(time_until, timedelta)
        assert time_until.total_seconds() > 0
    
    def test_cache_status_reporting(self, oauth_manager):
        """Test cache status reporting functionality."""
        # Add some cached tokens
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        oauth_manager._token_cache["test_scope"] = CachedToken(
            access_token="test_token",
            expires_at=expires_at,
            scope="test_scope"
        )
        
        status = oauth_manager.get_cache_status()
        assert status['total_cached_tokens'] == 1
        assert len(status['tokens']) == 1
        assert status['tokens'][0]['scope'] == "test_scope"
        assert not status['tokens'][0]['is_expired']
    
    @pytest.mark.asyncio
    async def test_token_context_manager(self, oauth_manager, mock_token_response):
        """Test token context manager."""
        with patch('api.oauth.aiohttp.ClientSession') as mock_session_class:
            # Mock session and its context manager behavior
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_session_class.return_value = mock_session
            
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value=json.dumps(mock_token_response))
            mock_response.json = AsyncMock(return_value=mock_token_response)
            
            # Create context manager for post method
            context = AsyncMock()
            context.__aenter__ = AsyncMock(return_value=mock_response)
            context.__aexit__ = AsyncMock(return_value=None)
            mock_session.post = MagicMock(return_value=context)
            
            async with oauth_manager.token_context() as token:
                assert token == "test_access_token_123"


class TestOAuthScopes:
    """Test OAuth scope validation and utility methods."""
    
    def test_scope_validation(self):
        """Test OAuth scope validation."""
        # Valid single scope
        assert OAuthScopes.validate_scope(OAuthScopes.BUY_BROWSE)
        
        # Valid multiple scopes
        combined_scope = f"{OAuthScopes.BUY_BROWSE} {OAuthScopes.BUY_ORDER}"
        assert OAuthScopes.validate_scope(combined_scope)
        
        # Invalid scope
        assert not OAuthScopes.validate_scope("invalid_scope")
        
        # Mixed valid and invalid
        mixed_scope = f"{OAuthScopes.BUY_BROWSE} invalid_scope"
        assert not OAuthScopes.validate_scope(mixed_scope)
    
    def test_scope_descriptions(self):
        """Test scope description functionality."""
        description = OAuthScopes.get_scope_description(OAuthScopes.BUY_BROWSE)
        assert "View public data from eBay" in description
        
        unknown_description = OAuthScopes.get_scope_description("unknown_scope")
        assert unknown_description == "Unknown scope"
    
    def test_combined_scopes(self):
        """Test combined scope constants."""
        # Check that combined scopes contain expected individual scopes
        assert OAuthScopes.BUY_BROWSE in OAuthScopes.ALL_BUY
        assert OAuthScopes.SELL_MARKETING in OAuthScopes.ALL_SELL
        
        # Validate combined scopes
        assert OAuthScopes.validate_scope(OAuthScopes.ALL_BUY)
        assert OAuthScopes.validate_scope(OAuthScopes.ALL_SELL)
        assert OAuthScopes.validate_scope(OAuthScopes.ALL_COMMERCE)


class TestOAuthConfig:
    """Test OAuth configuration enhancements."""
    
    def test_config_defaults(self):
        """Test OAuth configuration default values."""
        config = OAuthConfig(
            client_id="test_id",
            client_secret="test_secret"
        )
        
        assert config.max_retries == 3
        assert config.retry_delay == 1.0
        assert config.request_timeout == 30
        assert config.sandbox is True
    
    def test_config_customization(self):
        """Test OAuth configuration customization."""
        config = OAuthConfig(
            client_id="test_id",
            client_secret="test_secret",
            max_retries=5,
            retry_delay=0.5,
            request_timeout=60,
            sandbox=False
        )
        
        assert config.max_retries == 5
        assert config.retry_delay == 0.5
        assert config.request_timeout == 60
        assert config.sandbox is False
    
    def test_endpoint_urls(self):
        """Test environment-specific endpoint URLs."""
        # Sandbox config
        sandbox_config = OAuthConfig(
            client_id="test_id",
            client_secret="test_secret",
            sandbox=True
        )
        assert "sandbox.ebay.com" in sandbox_config.token_url
        
        # Production config
        prod_config = OAuthConfig(
            client_id="test_id",
            client_secret="test_secret",
            sandbox=False
        )
        assert "api.ebay.com" in prod_config.token_url
        assert "sandbox" not in prod_config.token_url
