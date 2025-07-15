"""
Integration tests for OAuth enhancements.

Tests the real OAuth functionality against eBay's OAuth endpoints
to ensure our enhancements work correctly.
"""
import pytest
from datetime import datetime, timedelta
import json

from api.oauth import OAuthManager, OAuthConfig, CachedToken, OAuthScopes


class TestOAuthIntegration:
    """Integration tests for OAuth functionality."""
    
    def test_oauth_config_enhancements(self):
        """Test OAuth configuration enhancements."""
        config = OAuthConfig(
            client_id="test_client_id",
            client_secret="test_client_secret",
            max_retries=5,
            retry_delay=0.5,
            request_timeout=60
        )
        
        assert config.max_retries == 5
        assert config.retry_delay == 0.5
        assert config.request_timeout == 60
        assert config.token_url == "https://api.sandbox.ebay.com/identity/v1/oauth2/token"
    
    def test_token_expiry_enhancements(self):
        """Test token expiry utility methods."""
        expires_at = datetime.utcnow() + timedelta(minutes=30)
        token = CachedToken(
            access_token="test_token",
            expires_at=expires_at
        )
        
        # Test configurable buffer
        assert not token.is_expired(buffer_minutes=5)
        assert token.is_expired(buffer_minutes=35)
        
        # Test near expiry detection
        assert not token.is_near_expiry(buffer_minutes=5)
        assert token.is_near_expiry(buffer_minutes=35)
        
        # Test time until expiry
        time_until = token.time_until_expiry()
        assert time_until.total_seconds() > 0
    
    def test_oauth_manager_enhancements(self):
        """Test OAuth manager enhancements."""
        config = OAuthConfig(
            client_id="test_client_id",
            client_secret="test_client_secret"
        )
        manager = OAuthManager(config)
        
        # Test metrics initialization
        metrics = manager.get_metrics()
        assert metrics['token_requests'] == 0
        assert metrics['token_cache_hits'] == 0
        assert metrics['token_cache_misses'] == 0
        assert metrics['token_errors'] == 0
        
        # Test cache status
        status = manager.get_cache_status()
        assert status['total_cached_tokens'] == 0
        assert status['tokens'] == []
        
        # Test metrics reset
        manager.reset_metrics()
        metrics = manager.get_metrics()
        assert all(count == 0 for count in metrics.values())
    
    def test_oauth_error_parsing(self):
        """Test OAuth error parsing functionality."""
        config = OAuthConfig(
            client_id="test_client_id",
            client_secret="test_client_secret"
        )
        manager = OAuthManager(config)
        
        # Test invalid client error
        invalid_client_response = json.dumps({
            "error": "invalid_client",
            "error_description": "Client authentication failed"
        })
        error_msg = manager._parse_oauth_error(400, invalid_client_response)
        assert "Invalid client credentials" in error_msg
        
        # Test invalid scope error
        invalid_scope_response = json.dumps({
            "error": "invalid_scope",
            "error_description": "Requested scope is invalid"
        })
        error_msg = manager._parse_oauth_error(400, invalid_scope_response)
        assert "Invalid or unauthorized scope" in error_msg
        
        # Test rate limit error
        rate_limit_response = json.dumps({
            "error": "rate_limit_exceeded",
            "error_description": "Too many requests"
        })
        error_msg = manager._parse_oauth_error(429, rate_limit_response)
        assert "Rate limit exceeded" in error_msg
        
        # Test generic error
        generic_response = "Internal server error"
        error_msg = manager._parse_oauth_error(500, generic_response)
        assert error_msg == "Internal server error"
    
    def test_scope_validation_enhancements(self):
        """Test OAuth scope validation enhancements."""
        # Test valid single scope
        assert OAuthScopes.validate_scope(OAuthScopes.BUY_BROWSE)
        
        # Test valid multiple scopes
        combined_scope = f"{OAuthScopes.BUY_BROWSE} {OAuthScopes.SELL_INVENTORY}"
        assert OAuthScopes.validate_scope(combined_scope)
        
        # Test invalid scope
        assert not OAuthScopes.validate_scope("invalid_scope")
        
        # Test scope descriptions
        description = OAuthScopes.get_scope_description(OAuthScopes.BUY_BROWSE)
        assert "Browse items" in description
        
        unknown_description = OAuthScopes.get_scope_description("unknown_scope")
        assert unknown_description == "Unknown scope"
        
        # Test combined scope constants
        assert OAuthScopes.BUY_BROWSE in OAuthScopes.ALL_BUY
        assert OAuthScopes.SELL_INVENTORY in OAuthScopes.ALL_SELL
        assert OAuthScopes.COMMERCE_CATALOG in OAuthScopes.ALL_COMMERCE
    
    def test_cache_management_enhancements(self):
        """Test cache management enhancements."""
        config = OAuthConfig(
            client_id="test_client_id",
            client_secret="test_client_secret"
        )
        manager = OAuthManager(config)
        
        # Add a test token to cache
        expires_at = datetime.utcnow() + timedelta(hours=1)
        test_token = CachedToken(
            access_token="test_token",
            expires_at=expires_at,
            scope="test_scope"
        )
        
        cache_key = "client_credentials:test_scope"
        manager._token_cache[cache_key] = test_token
        
        # Test cache status
        status = manager.get_cache_status()
        assert status['total_cached_tokens'] == 1
        assert len(status['tokens']) == 1
        
        token_info = status['tokens'][0]
        assert token_info['cache_key'] == cache_key
        assert token_info['scope'] == "test_scope"
        assert not token_info['is_expired']
        assert not token_info['is_near_expiry']
        
        # Test cache clearing
        manager.clear_cache()
        status = manager.get_cache_status()
        assert status['total_cached_tokens'] == 0
    
    def test_configuration_validation(self):
        """Test configuration validation."""
        # Test minimum required fields
        config = OAuthConfig(
            client_id="test_client_id",
            client_secret="test_client_secret"
        )
        assert config.client_id == "test_client_id"
        assert config.client_secret == "test_client_secret"
        
        # Test environment-specific URLs
        sandbox_config = OAuthConfig(
            client_id="test_id",
            client_secret="test_secret",
            sandbox=True
        )
        assert "sandbox.ebay.com" in sandbox_config.token_url
        
        prod_config = OAuthConfig(
            client_id="test_id",
            client_secret="test_secret",
            sandbox=False
        )
        assert "api.ebay.com" in prod_config.token_url
        assert "sandbox" not in prod_config.token_url
        
        # Test auth header generation
        auth_header = config.auth_header
        assert auth_header.startswith("Basic ")
        assert len(auth_header) > 10  # Should be base64 encoded