"""
eBay OAuth 2.0 Manager for REST API Authentication.

Handles client credentials flow for application-level access to eBay APIs.
Includes token caching and automatic refresh functionality.
"""
import base64
import asyncio
import json
import os
import sys
import webbrowser
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, Dict, Any
import aiohttp
from pydantic import BaseModel, Field, ConfigDict
import logging
import time
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


class OAuthConfig(BaseModel):
    """Configuration for eBay OAuth 2.0."""
    client_id: str = Field(..., description="eBay application client ID")
    client_secret: str = Field(..., description="eBay application client secret")
    redirect_uri: str = Field(default="https://localhost", description="OAuth redirect URI")
    sandbox: bool = Field(default=True, description="Use sandbox environment")
    max_retries: int = Field(default=3, description="Maximum retry attempts for OAuth requests")
    retry_delay: float = Field(default=1.0, description="Base delay between retries in seconds")
    request_timeout: int = Field(default=30, description="Request timeout in seconds")
    
    @property
    def token_url(self) -> str:
        """Get the token endpoint URL based on environment."""
        domain = "sandbox.ebay.com" if self.sandbox else "ebay.com"
        return f"https://api.{domain}/identity/v1/oauth2/token"
    
    @property
    def auth_header(self) -> str:
        """Generate Basic Auth header for token requests."""
        credentials = f"{self.client_id}:{self.client_secret}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return f"Basic {encoded}"


class UserTokenData(BaseModel):
    """User token storage model."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    access_token: str = Field(..., description="User access token")
    refresh_token: str = Field(..., description="User refresh token")
    token_type: str = Field(default="Bearer", description="Token type")
    expires_at: datetime = Field(..., description="Token expiration time")
    scope: str = Field(..., description="Granted scopes")
    user_id: Optional[str] = Field(None, description="eBay user ID")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Token creation time")


class TokenStorage:
    """Secure token storage manager."""
    
    def __init__(self, storage_path: Optional[str] = None):
        """Initialize token storage."""
        if storage_path:
            self.storage_path = Path(storage_path)
        else:
            # Default to ~/.ebay/oauth_tokens.json
            self.storage_path = Path.home() / ".ebay" / "oauth_tokens.json"
        
        # Ensure directory exists
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Set secure permissions (readable only by owner)
        if self.storage_path.exists():
            os.chmod(self.storage_path, 0o600)
    
    def store_user_token(self, token_data: UserTokenData, app_id: str) -> None:
        """Store user token securely."""
        # Load existing tokens
        tokens = self._load_tokens()
        
        # Store token under app_id key
        tokens[app_id] = {
            "access_token": token_data.access_token,
            "refresh_token": token_data.refresh_token,
            "token_type": token_data.token_type,
            "expires_at": token_data.expires_at.isoformat(),
            "scope": token_data.scope,
            "user_id": token_data.user_id,
            "created_at": token_data.created_at.isoformat()
        }
        
        # Save tokens
        self._save_tokens(tokens)
    
    def get_user_token(self, app_id: str) -> Optional[UserTokenData]:
        """Retrieve user token for app."""
        tokens = self._load_tokens()
        
        if app_id not in tokens:
            return None
        
        token_data = tokens[app_id]
        
        try:
            return UserTokenData(
                access_token=token_data["access_token"],
                refresh_token=token_data["refresh_token"],
                token_type=token_data.get("token_type", "Bearer"),
                expires_at=datetime.fromisoformat(token_data["expires_at"]),
                scope=token_data["scope"],
                user_id=token_data.get("user_id"),
                created_at=datetime.fromisoformat(token_data["created_at"])
            )
        except (KeyError, ValueError) as e:
            # Invalid token data, remove it
            del tokens[app_id]
            self._save_tokens(tokens)
            return None
    
    def delete_user_token(self, app_id: str) -> bool:
        """Delete user token for app."""
        tokens = self._load_tokens()
        
        if app_id in tokens:
            del tokens[app_id]
            self._save_tokens(tokens)
            return True
        
        return False
    
    def store_consent_state(self, app_id: str, state: str, redirect_uri: str) -> None:
        """Store consent state for OAuth flow."""
        tokens = self._load_tokens()
        
        # Store consent state under special key
        consent_key = f"{app_id}_consent"
        tokens[consent_key] = {
            "state": state,
            "redirect_uri": redirect_uri
        }
        
        self._save_tokens(tokens)
    
    def get_consent_state(self, app_id: str) -> Optional[Dict[str, str]]:
        """Get stored consent state."""
        tokens = self._load_tokens()
        consent_key = f"{app_id}_consent"
        
        if consent_key in tokens:
            return tokens[consent_key]
        
        return None
    
    def delete_consent_state(self, app_id: str) -> bool:
        """Delete consent state from storage."""
        tokens = self._load_tokens()
        consent_key = f"{app_id}_consent"
        
        if consent_key in tokens:
            del tokens[consent_key]
            self._save_tokens(tokens)
            return True
        
        return False
    
    def _load_tokens(self) -> Dict[str, Any]:
        """Load tokens from storage."""
        if not self.storage_path.exists():
            return {}
        
        try:
            with open(self.storage_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    
    def _save_tokens(self, tokens: Dict[str, Any]) -> None:
        """Save tokens to storage."""
        try:
            with open(self.storage_path, 'w') as f:
                json.dump(tokens, f, indent=2)
            
            # Ensure secure permissions
            os.chmod(self.storage_path, 0o600)
        except IOError as e:
            raise Exception(f"Failed to save tokens: {e}")


def _can_open_browser() -> bool:
    """Check if we can open a browser (running in stdio mode)."""
    # Check if we're running in a terminal/stdio environment
    # This is a simple heuristic - in practice, MCP servers running locally
    # through stdio can often open browsers
    return sys.stdin.isatty() and sys.stdout.isatty()


def _open_browser(url: str) -> bool:
    """Open URL in the default browser if possible."""
    if not _can_open_browser():
        return False
    
    try:
        return webbrowser.open(url)
    except Exception:
        return False


class ConsentRequiredException(Exception):
    """Exception raised when user consent is required but not available."""
    
    def __init__(self, message: str = "User consent required. Use initiate_user_consent tool to authorize eBay API access."):
        self.message = message
        super().__init__(self.message)


class CachedToken(BaseModel):
    """Cached OAuth token with expiration tracking."""
    access_token: str
    token_type: str = "Bearer"
    expires_at: datetime
    scope: Optional[str] = None
    
    def is_expired(self, buffer_minutes: int = 5) -> bool:
        """Check if token is expired with configurable buffer."""
        return datetime.now(timezone.utc) >= self.expires_at - timedelta(minutes=buffer_minutes)
    
    def time_until_expiry(self) -> timedelta:
        """Get time remaining until token expires."""
        return self.expires_at - datetime.now(timezone.utc)
    
    def is_near_expiry(self, buffer_minutes: int = 10) -> bool:
        """Check if token is near expiry (within buffer time)."""
        return datetime.now(timezone.utc) >= self.expires_at - timedelta(minutes=buffer_minutes)


class OAuthManager:
    """
    Manages OAuth 2.0 authentication for eBay REST APIs.
    
    Supports:
    - Client credentials flow for application access
    - Token caching and automatic refresh
    - Thread-safe token management
    - eBay-specific error handling and retry logic
    - Request metrics and monitoring
    """
    
    def __init__(self, config: OAuthConfig):
        self.config = config
        self._token_cache: Dict[str, CachedToken] = {}
        self._lock = asyncio.Lock()
        self._metrics = {
            'token_requests': 0,
            'token_cache_hits': 0,
            'token_cache_misses': 0,
            'token_errors': 0
        }
        self._token_storage = TokenStorage()
        
    async def get_client_credentials_token(self, scope: str = "https://api.ebay.com/oauth/api_scope") -> str:
        """
        Get access token using client credentials flow.
        
        Args:
            scope: OAuth scope(s) for the token. Default is basic API access.
                  Multiple scopes can be space-separated.
                  
        Returns:
            Access token string
            
        Raises:
            aiohttp.ClientError: Network errors
            Exception: OAuth errors from eBay
        """
        cache_key = f"client_credentials:{scope}"
        
        async with self._lock:
            # Check cache
            if cache_key in self._token_cache:
                cached = self._token_cache[cache_key]
                if not cached.is_expired():
                    logger.debug(f"Using cached token for scope: {scope} (expires in {cached.time_until_expiry()})")
                    self._metrics['token_cache_hits'] += 1
                    return cached.access_token
                else:
                    logger.debug(f"Cached token expired for scope: {scope}")
                    self._metrics['token_cache_misses'] += 1
            else:
                self._metrics['token_cache_misses'] += 1
            
            # Request new token with retry logic
            logger.info(f"Requesting new token for scope: {scope}")
            token = await self._request_token_with_retry(scope)
            
            # Cache the token
            self._token_cache[cache_key] = token
            
            return token.access_token
    
    async def _request_token_with_retry(self, scope: str) -> CachedToken:
        """Request token with eBay-specific retry logic."""
        last_exception = None
        
        for attempt in range(self.config.max_retries):
            try:
                return await self._request_token(scope)
            except Exception as e:
                last_exception = e
                self._metrics['token_errors'] += 1
                
                if attempt < self.config.max_retries - 1:
                    delay = self.config.retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.warning(f"OAuth request failed (attempt {attempt + 1}/{self.config.max_retries}): {e}. Retrying in {delay}s...")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"OAuth request failed after {self.config.max_retries} attempts: {e}")
        
        raise last_exception
    
    async def _request_token(self, scope: str) -> CachedToken:
        """
        Request a new token from eBay OAuth service.
        
        Args:
            scope: OAuth scope(s) for the token
            
        Returns:
            CachedToken with token details
            
        Raises:
            Exception: OAuth errors from eBay
        """
        headers = {
            "Authorization": self.config.auth_header,
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        # Validate scope before making request
        if not OAuthScopes.validate_scope(scope):
            logger.warning(f"Using unrecognized OAuth scope: {scope}")
        
        data = {
            "grant_type": "client_credentials",
            "scope": scope
        }
        
        logger.debug(f"Requesting OAuth token for scope: {OAuthScopes.get_scope_description(scope)}")
        logger.debug(f"Actual scope string: {scope}")
        logger.debug(f"Using endpoint: {self.config.token_url}")
        logger.debug(f"Request data: {data}")
        
        self._metrics['token_requests'] += 1
        
        timeout = aiohttp.ClientTimeout(total=self.config.request_timeout)
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            start_time = time.time()
            
            try:
                async with session.post(
                    self.config.token_url,
                    headers=headers,
                    data=data
                ) as response:
                    response_text = await response.text()
                    request_duration = time.time() - start_time
                    
                    logger.debug(f"OAuth request completed in {request_duration:.2f}s")
                    
                    if response.status != 200:
                        error_msg = self._parse_oauth_error(response.status, response_text)
                        logger.error(f"OAuth token request failed: {response.status} - {error_msg}")
                        raise Exception(f"OAuth token request failed: {error_msg}")
                    
                    token_data = await response.json()
                    
                    # Validate required fields
                    if "access_token" not in token_data:
                        raise Exception("OAuth response missing access_token")
                    
                    # Calculate expiration time
                    expires_in = token_data.get("expires_in", 7200)  # Default 2 hours
                    expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
                    
                    logger.info(f"OAuth token obtained successfully (expires in {expires_in}s)")
                    
                    return CachedToken(
                        access_token=token_data["access_token"],
                        token_type=token_data.get("token_type", "Bearer"),
                        expires_at=expires_at,
                        scope=token_data.get("scope", scope)
                    )
            except aiohttp.ClientError as e:
                logger.error(f"OAuth request network error: {e}")
                raise Exception(f"OAuth network error: {e}")
            except asyncio.TimeoutError:
                logger.error(f"OAuth request timeout after {self.config.request_timeout}s")
                raise Exception(f"OAuth request timeout after {self.config.request_timeout}s")
    
    async def exchange_code_for_tokens(self, auth_code: str, redirect_uri: str) -> dict:
        """
        Exchange authorization code for user access tokens.
        
        Args:
            auth_code: Authorization code from OAuth flow
            redirect_uri: OAuth redirect URI used in authorization request
            
        Returns:
            Dictionary containing access_token, refresh_token, expires_in, etc.
            
        Raises:
            Exception: OAuth errors from eBay
        """
        headers = {
            "Authorization": self.config.auth_header,
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        data = {
            "grant_type": "authorization_code",
            "code": auth_code,
            "redirect_uri": redirect_uri
        }
        
        logger.info(f"Exchanging authorization code for user tokens")
        logger.debug(f"Using redirect URI: {redirect_uri}")
        
        timeout = aiohttp.ClientTimeout(total=self.config.request_timeout)
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            try:
                async with session.post(
                    self.config.token_url,
                    headers=headers,
                    data=data
                ) as response:
                    response_text = await response.text()
                    
                    if response.status != 200:
                        error_msg = self._parse_oauth_error(response.status, response_text)
                        logger.error(f"Token exchange failed: {response.status} - {error_msg}")
                        raise Exception(f"Token exchange failed: {error_msg}")
                    
                    token_data = await response.json()
                    
                    # Validate required fields
                    if "access_token" not in token_data:
                        raise Exception("Token response missing access_token")
                    
                    expires_in = token_data.get("expires_in", 7200)
                    logger.info(f"User tokens obtained successfully (expires in {expires_in}s)")
                    
                    return token_data
                    
            except aiohttp.ClientError as e:
                logger.error(f"Token exchange network error: {e}")
                raise Exception(f"Token exchange network error: {e}")
            except asyncio.TimeoutError:
                logger.error(f"Token exchange timeout after {self.config.request_timeout}s")
                raise Exception(f"Token exchange timeout after {self.config.request_timeout}s")

    async def get_token(self) -> str:
        """
        Get appropriate token for API requests.
        
        Returns user token if available and valid, otherwise raises ConsentRequiredException.
        This method should be used by all APIs requiring user authorization.
        
        Returns:
            User access token string
            
        Raises:
            ConsentRequiredException: When user consent is required
        """
        # Check for valid user token
        user_token = self._token_storage.get_user_token(self.config.client_id)
        
        if not user_token:
            raise ConsentRequiredException("User consent required. Use initiate_user_consent tool to authorize eBay API access.")
        
        # Check if token is expired
        if user_token.expires_at <= datetime.now(timezone.utc):
            # TODO: Implement token refresh logic
            raise ConsentRequiredException("User consent expired. Use initiate_user_consent tool to re-authorize eBay API access.")
        
        return user_token.access_token
    
    async def initiate_consent_flow(self) -> Dict[str, Any]:
        """
        Initiate the user consent flow.
        
        Generates authorization URL and opens browser if possible.
        
        Returns:
            Dictionary with auth_url and browser_opened status
        """
        # Generate state parameter for security
        import uuid
        state = str(uuid.uuid4())
        
        # Build authorization URL
        base_url = "https://auth.sandbox.ebay.com/oauth2/authorize" if self.config.sandbox else "https://auth.ebay.com/oauth2/authorize"
        
        # Use redirect URI from environment or default to RuName
        redirect_uri = os.getenv("EBAY_REDIRECT_URI", "Travis_Melhiser-TravisMe-Lootly-menhqo")
        
        # URL encode parameters
        from urllib.parse import urlencode
        
        params = {
            "client_id": self.config.client_id,
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "scope": OAuthScopes.USER_CONSENT_SCOPES,
            "state": state,
            "consentGiven": False
        }
        
        auth_url = f"{base_url}?{urlencode(params)}"
        logger.debug(f'Auth URL: {auth_url}')
        
        # Try to open browser automatically
        browser_opened = _open_browser(auth_url)
        
        # Store state temporarily (in a real app, this would be more persistent)
        self._consent_state = state
        self._consent_redirect_uri = redirect_uri
        
        # Also store in token storage for persistence between OAuth manager instances
        self._token_storage.store_consent_state(self.config.client_id, state, redirect_uri)
        
        logger.debug(f"Stored consent state: {state}")
        logger.debug(f"Stored consent redirect URI: {redirect_uri}")
        
        return {
            "auth_url": auth_url,
            "browser_opened": browser_opened,
            "state": state,
            "redirect_uri": redirect_uri
        }
    
    async def complete_consent_flow(self, callback_url: str) -> Dict[str, Any]:
        """
        Complete the user consent flow using callback URL.
        
        Args:
            callback_url: The full callback URL from browser
            
        Returns:
            Dictionary with consent completion details
            
        Raises:
            Exception: On validation or token exchange errors
        """
        # Parse callback URL
        from urllib.parse import urlparse, parse_qs
        
        parsed_url = urlparse(callback_url)
        query_params = parse_qs(parsed_url.query)
        
        # Extract authorization code
        if 'code' not in query_params:
            raise Exception("Authorization code not found in callback URL")
        
        auth_code = query_params['code'][0]
        
        # Validate state parameter
        if 'state' in query_params:
            received_state = query_params['state'][0]
            
            # Get stored state from token storage (fallback to instance variable)
            stored_state = getattr(self, '_consent_state', None)
            stored_redirect_uri = getattr(self, '_consent_redirect_uri', None)
            
            # If not in instance, try to get from token storage
            if not stored_state:
                consent_info = self._token_storage.get_consent_state(self.config.client_id)
                if consent_info:
                    stored_state = consent_info['state']
                    stored_redirect_uri = consent_info['redirect_uri']
            
            if stored_state and received_state != stored_state:
                raise Exception("State parameter mismatch - possible CSRF attack")
        
        # Get redirect URI
        redirect_uri = stored_redirect_uri or self.config.redirect_uri
        logger.debug(f"Using redirect URI for token exchange: {redirect_uri}")
        logger.debug(f"Has _consent_redirect_uri: {hasattr(self, '_consent_redirect_uri')}")
        logger.debug(f"Stored redirect URI from storage: {stored_redirect_uri}")
        
        # Exchange authorization code for tokens
        token_data = await self.exchange_code_for_tokens(auth_code, redirect_uri)
        
        # Store user token
        user_token = UserTokenData(
            access_token=token_data["access_token"],
            refresh_token=token_data["refresh_token"],
            token_type=token_data.get("token_type", "Bearer"),
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=token_data.get("expires_in", 7200)),
            scope=token_data.get("scope", OAuthScopes.USER_CONSENT_SCOPES),
            user_id=token_data.get("user_id")
        )
        
        self._token_storage.store_user_token(user_token, self.config.client_id)
        
        # Clean up temporary state
        if hasattr(self, '_consent_state'):
            delattr(self, '_consent_state')
        if hasattr(self, '_consent_redirect_uri'):
            delattr(self, '_consent_redirect_uri')
        
        # Clean up from token storage
        self._token_storage.delete_consent_state(self.config.client_id)
        
        return {
            "expires_at": user_token.expires_at.isoformat(),
            "scopes": user_token.scope.split()
        }
    
    def get_user_token_info(self) -> Optional[UserTokenData]:
        """Get current user token information."""
        return self._token_storage.get_user_token(self.config.client_id)
    
    def delete_user_token(self) -> bool:
        """Delete stored user token."""
        return self._token_storage.delete_user_token(self.config.client_id)

    async def get_user_token(self, auth_code: str) -> str:
        """
        Exchange authorization code for user access token.
        
        Deprecated: Use exchange_code_for_tokens instead.
        
        Args:
            auth_code: Authorization code from OAuth flow
            
        Returns:
            User access token
            
        Raises:
            NotImplementedError: This flow is not yet implemented
        """
        raise NotImplementedError(
            "Use exchange_code_for_tokens method instead for full token exchange functionality."
        )
    
    async def refresh_user_token(self, refresh_token: str) -> str:
        """
        Refresh a user access token.
        
        This is for future implementation when user-specific operations are needed.
        
        Args:
            refresh_token: Refresh token from previous OAuth flow
            
        Returns:
            New user access token
            
        Raises:
            NotImplementedError: This flow is not yet implemented
        """
        raise NotImplementedError(
            "User token refresh not implemented. Current implementation supports "
            "only client credentials flow for application-level access."
        )
    
    def _parse_oauth_error(self, status_code: int, response_text: str) -> str:
        """Parse eBay OAuth error response for better error messages."""
        try:
            import json
            error_data = json.loads(response_text)
            
            # eBay OAuth specific error handling
            if isinstance(error_data, dict):
                error_description = error_data.get("error_description", "")
                error_code = error_data.get("error", "")
                
                # Common eBay OAuth errors
                if error_code == "invalid_client":
                    return "Invalid client credentials (check App ID and Cert ID)"
                elif error_code == "invalid_scope":
                    return f"Invalid or unauthorized scope requested: {error_description}"
                elif error_code == "unsupported_grant_type":
                    return "Unsupported grant type (should be client_credentials)"
                elif status_code == 429:
                    return "Rate limit exceeded for OAuth requests"
                elif error_description:
                    return f"{error_code}: {error_description}"
                
        except (json.JSONDecodeError, KeyError):
            pass
        
        return response_text or f"HTTP {status_code} error"
    
    def clear_cache(self) -> None:
        """Clear all cached tokens."""
        self._token_cache.clear()
        logger.info("OAuth token cache cleared")
    
    def get_cached_token(self, scope: str = "https://api.ebay.com/oauth/api_scope") -> Optional[CachedToken]:
        """
        Get cached token without making a request.
        
        Args:
            scope: OAuth scope to look up
            
        Returns:
            Cached token if available and not expired, None otherwise
        """
        cache_key = f"client_credentials:{scope}"
        cached = self._token_cache.get(cache_key)
        
        if cached and not cached.is_expired():
            return cached
        
        return None
    
    def get_metrics(self) -> Dict[str, int]:
        """Get OAuth request metrics."""
        return self._metrics.copy()
    
    def reset_metrics(self) -> None:
        """Reset OAuth request metrics."""
        self._metrics = {
            'token_requests': 0,
            'token_cache_hits': 0,
            'token_cache_misses': 0,
            'token_errors': 0
        }
    
    def get_cache_status(self) -> Dict[str, any]:
        """Get current cache status and token information."""
        status = {
            'total_cached_tokens': len(self._token_cache),
            'tokens': []
        }
        
        for cache_key, token in self._token_cache.items():
            status['tokens'].append({
                'cache_key': cache_key,
                'scope': token.scope,
                'expires_at': token.expires_at.isoformat(),
                'time_until_expiry': str(token.time_until_expiry()),
                'is_expired': token.is_expired(),
                'is_near_expiry': token.is_near_expiry()
            })
        
        return status
    
    @asynccontextmanager
    async def token_context(self, scope: str = "https://api.ebay.com/oauth/api_scope"):
        """Context manager for token lifecycle management."""
        token = await self.get_client_credentials_token(scope)
        try:
            yield token
        finally:
            # Token cleanup or logging could go here
            pass


# OAuth Scopes Reference
class OAuthScopes:
    """Complete eBay OAuth scopes for all API access levels."""

    # Basic API access (default)
    API_SCOPE = "https://api.ebay.com/oauth/api_scope"
    
    # Buy API scopes - User Authorization
    BUY_BROWSE = "https://api.ebay.com/oauth/api_scope"  # Basic scope for Browse API
    BUY_ORDER = "https://api.ebay.com/oauth/api_scope/buy.order"
    BUY_ORDER_READONLY = "https://api.ebay.com/oauth/api_scope/buy.order.readonly"
    BUY_GUEST_ORDER = "https://api.ebay.com/oauth/api_scope/buy.guest.order"
    BUY_SHOPPING_CART = "https://api.ebay.com/oauth/api_scope/buy.shopping.cart"
    BUY_OFFER = "https://api.ebay.com/oauth/api_scope/buy.offer"
    BUY_OFFER_AUCTION = "https://api.ebay.com/oauth/api_scope/buy.offer.auction"
    
    # Buy API scopes - Client Credentials
    BUY_MARKETING = "https://api.ebay.com/oauth/api_scope/buy.marketing"
    BUY_MARKETPLACE_INSIGHTS = "https://api.ebay.com/oauth/api_scope/buy.marketplace.insights"
    BUY_ITEM_FEED = "https://api.ebay.com/oauth/api_scope/buy.item.feed"
    BUY_PRODUCT_FEED = "https://api.ebay.com/oauth/api_scope/buy.product.feed"
    BUY_PROXY_GUEST_ORDER = "https://api.ebay.com/oauth/api_scope/buy.proxy.guest.order"
    BUY_ITEM_BULK = "https://api.ebay.com/oauth/api_scope/buy.item.bulk"
    BUY_DEAL = "https://api.ebay.com/oauth/api_scope/buy.deal"
    
    # Sell API scopes - Marketing
    SELL_MARKETING = "https://api.ebay.com/oauth/api_scope/sell.marketing"
    SELL_MARKETING_READONLY = "https://api.ebay.com/oauth/api_scope/sell.marketing.readonly"
    
    # Sell API scopes - Account
    SELL_ACCOUNT = "https://api.ebay.com/oauth/api_scope/sell.account"
    SELL_ACCOUNT_READONLY = "https://api.ebay.com/oauth/api_scope/sell.account.readonly"
    
    # Sell API scopes - Inventory
    SELL_INVENTORY = "https://api.ebay.com/oauth/api_scope/sell.inventory"
    SELL_INVENTORY_READONLY = "https://api.ebay.com/oauth/api_scope/sell.inventory.readonly"
    
    # Sell API scopes - Fulfillment
    SELL_FULFILLMENT = "https://api.ebay.com/oauth/api_scope/sell.fulfillment"
    SELL_FULFILLMENT_READONLY = "https://api.ebay.com/oauth/api_scope/sell.fulfillment.readonly"
    
    # Sell API scopes - Analytics & Insights
    SELL_ANALYTICS = "https://api.ebay.com/oauth/api_scope/sell.analytics.readonly"
    SELL_MARKETPLACE_INSIGHTS_READONLY = "https://api.ebay.com/oauth/api_scope/sell.marketplace.insights.readonly"
    
    # Sell API scopes - Finances & Payments
    SELL_FINANCES = "https://api.ebay.com/oauth/api_scope/sell.finances"
    SELL_PAYMENT_DISPUTE = "https://api.ebay.com/oauth/api_scope/sell.payment.dispute"
    
    # Sell API scopes - Items & Listings
    SELL_ITEM = "https://api.ebay.com/oauth/api_scope/sell.item"
    SELL_ITEM_DRAFT = "https://api.ebay.com/oauth/api_scope/sell.item.draft"
    
    # Sell API scopes - Reputation
    SELL_REPUTATION = "https://api.ebay.com/oauth/api_scope/sell.reputation"
    SELL_REPUTATION_READONLY = "https://api.ebay.com/oauth/api_scope/sell.reputation.readonly"
    
    # Sell API scopes - Stores
    SELL_STORES = "https://api.ebay.com/oauth/api_scope/sell.stores"
    SELL_STORES_READONLY = "https://api.ebay.com/oauth/api_scope/sell.stores.readonly"
    
    # Commerce API scopes - Catalog
    COMMERCE_CATALOG_READONLY = "https://api.ebay.com/oauth/api_scope/commerce.catalog.readonly"
    
    # Commerce API scopes - Identity
    COMMERCE_IDENTITY = "https://api.ebay.com/oauth/api_scope/commerce.identity.readonly"
    COMMERCE_IDENTITY_EMAIL_READONLY = "https://api.ebay.com/oauth/api_scope/commerce.identity.email.readonly"
    COMMERCE_IDENTITY_PHONE_READONLY = "https://api.ebay.com/oauth/api_scope/commerce.identity.phone.readonly"
    COMMERCE_IDENTITY_ADDRESS_READONLY = "https://api.ebay.com/oauth/api_scope/commerce.identity.address.readonly"
    COMMERCE_IDENTITY_NAME_READONLY = "https://api.ebay.com/oauth/api_scope/commerce.identity.name.readonly"
    COMMERCE_IDENTITY_STATUS_READONLY = "https://api.ebay.com/oauth/api_scope/commerce.identity.status.readonly"
    
    # Commerce API scopes - Notifications
    COMMERCE_NOTIFICATION_SUBSCRIPTION = "https://api.ebay.com/oauth/api_scope/commerce.notification.subscription"
    COMMERCE_NOTIFICATION_SUBSCRIPTION_READONLY = "https://api.ebay.com/oauth/api_scope/commerce.notification.subscription.readonly"
    
    # Commerce API scopes - VeRO (Verified Rights Owner)
    COMMERCE_VERO = "https://api.ebay.com/oauth/api_scope/commerce.vero"
    
    # Combined scopes for common use cases
    ALL_BUY = " ".join([
        API_SCOPE,
        BUY_BROWSE, BUY_ORDER, BUY_ORDER_READONLY, BUY_GUEST_ORDER, BUY_SHOPPING_CART,
        BUY_OFFER, BUY_OFFER_AUCTION, BUY_MARKETING, BUY_MARKETPLACE_INSIGHTS,
        BUY_ITEM_FEED, BUY_PRODUCT_FEED, BUY_PROXY_GUEST_ORDER, BUY_ITEM_BULK, BUY_DEAL
    ])
    
    ALL_SELL = " ".join([
        API_SCOPE,
        SELL_MARKETING, SELL_MARKETING_READONLY, SELL_ACCOUNT, SELL_ACCOUNT_READONLY,
        SELL_INVENTORY, SELL_INVENTORY_READONLY, SELL_FULFILLMENT, SELL_FULFILLMENT_READONLY,
        SELL_ANALYTICS, SELL_MARKETPLACE_INSIGHTS_READONLY, SELL_FINANCES, SELL_PAYMENT_DISPUTE,
        SELL_ITEM, SELL_ITEM_DRAFT, SELL_REPUTATION, SELL_REPUTATION_READONLY,
        SELL_STORES, SELL_STORES_READONLY
    ])
    
    ALL_COMMERCE = " ".join([
        API_SCOPE,
        COMMERCE_CATALOG_READONLY, COMMERCE_IDENTITY, COMMERCE_IDENTITY_EMAIL_READONLY,
        COMMERCE_IDENTITY_PHONE_READONLY, COMMERCE_IDENTITY_ADDRESS_READONLY,
        COMMERCE_IDENTITY_NAME_READONLY, COMMERCE_IDENTITY_STATUS_READONLY,
        COMMERCE_NOTIFICATION_SUBSCRIPTION, COMMERCE_NOTIFICATION_SUBSCRIPTION_READONLY,
        COMMERCE_VERO
    ])
    
    # All read-only scopes
    ALL_READONLY = " ".join([
        API_SCOPE,
        BUY_ORDER_READONLY, SELL_MARKETING_READONLY, SELL_ACCOUNT_READONLY,
        SELL_INVENTORY_READONLY, SELL_FULFILLMENT_READONLY, SELL_ANALYTICS,
        SELL_MARKETPLACE_INSIGHTS_READONLY, SELL_REPUTATION_READONLY, SELL_STORES_READONLY,
        COMMERCE_CATALOG_READONLY, COMMERCE_IDENTITY, COMMERCE_IDENTITY_EMAIL_READONLY,
        COMMERCE_IDENTITY_PHONE_READONLY, COMMERCE_IDENTITY_ADDRESS_READONLY,
        COMMERCE_IDENTITY_NAME_READONLY, COMMERCE_IDENTITY_STATUS_READONLY,
        COMMERCE_NOTIFICATION_SUBSCRIPTION_READONLY
    ])
    
    # All identity-related scopes
    ALL_IDENTITY = " ".join([
        API_SCOPE,
        COMMERCE_IDENTITY, COMMERCE_IDENTITY_EMAIL_READONLY, COMMERCE_IDENTITY_PHONE_READONLY,
        COMMERCE_IDENTITY_ADDRESS_READONLY, COMMERCE_IDENTITY_NAME_READONLY,
        COMMERCE_IDENTITY_STATUS_READONLY
    ])

    # All unique scopes (removing duplicates)
    ALL_SCOPES = " ".join(sorted(set(
        ALL_BUY.split() + 
        ALL_SELL.split() + 
        ALL_COMMERCE.split() +
        ALL_READONLY.split() +
        ALL_IDENTITY.split()
    )))
    
    # User consent scopes (require user authorization)
    # Note: Not all scopes require user consent - some work with client credentials
    USER_CONSENT_SCOPES = " ".join([
        API_SCOPE,
        SELL_ACCOUNT, SELL_ANALYTICS, SELL_FULFILLMENT, SELL_INVENTORY, SELL_MARKETING,
        SELL_ACCOUNT_READONLY, SELL_FULFILLMENT_READONLY, SELL_INVENTORY_READONLY,
        SELL_MARKETING_READONLY, SELL_MARKETPLACE_INSIGHTS_READONLY, SELL_FINANCES,
        SELL_PAYMENT_DISPUTE, SELL_ITEM, SELL_ITEM_DRAFT, SELL_REPUTATION,
        SELL_REPUTATION_READONLY, SELL_STORES, SELL_STORES_READONLY,
        BUY_GUEST_ORDER, BUY_ORDER_READONLY, BUY_SHOPPING_CART, BUY_OFFER_AUCTION,
        COMMERCE_IDENTITY, COMMERCE_IDENTITY_EMAIL_READONLY, COMMERCE_IDENTITY_PHONE_READONLY,
        COMMERCE_IDENTITY_ADDRESS_READONLY, COMMERCE_IDENTITY_NAME_READONLY,
        COMMERCE_IDENTITY_STATUS_READONLY, COMMERCE_NOTIFICATION_SUBSCRIPTION,
        COMMERCE_NOTIFICATION_SUBSCRIPTION_READONLY, COMMERCE_CATALOG_READONLY,
        COMMERCE_VERO
    ])
    
    # USER_CONSENT_SCOPES = " ".join([
    #     SELL_ACCOUNT, SELL_ANALYTICS, SELL_FULFILLMENT, SELL_INVENTORY, SELL_MARKETING
    # ])
    
    @classmethod
    def get_scope_description(cls, scope: str) -> str:
        """Get human-readable description of OAuth scope."""
        scope_descriptions = {
            # Basic scope
            cls.API_SCOPE: "View public data from eBay",
            
            # Buy API scopes
            cls.BUY_BROWSE: "View public data from eBay",
            cls.BUY_ORDER: "Manage purchase orders",
            cls.BUY_ORDER_READONLY: "View your order details",
            cls.BUY_GUEST_ORDER: "Purchase eBay items off eBay",
            cls.BUY_SHOPPING_CART: "Access shopping carts",
            cls.BUY_OFFER: "Make offers on eBay items",
            cls.BUY_OFFER_AUCTION: "View and manage bidding activities for auctions",
            cls.BUY_MARKETING: "Retrieve eBay product and listing data for use in marketing merchandise to buyers",
            cls.BUY_MARKETPLACE_INSIGHTS: "View historical sales data to help buyers make informed purchasing decisions",
            cls.BUY_ITEM_FEED: "View curated feeds of eBay items",
            cls.BUY_PRODUCT_FEED: "Access product feeds",
            cls.BUY_PROXY_GUEST_ORDER: "Purchase eBay items anywhere, using an external vault for PCI compliance",
            cls.BUY_ITEM_BULK: "Retrieve eBay items in bulk",
            cls.BUY_DEAL: "View eBay sale events and deals",
            
            # Sell API scopes
            cls.SELL_MARKETING: "View and manage your eBay marketing activities, such as ad campaigns and listing promotions",
            cls.SELL_MARKETING_READONLY: "View your eBay marketing activities, such as ad campaigns and listing promotions",
            cls.SELL_ACCOUNT: "View and manage your account settings",
            cls.SELL_ACCOUNT_READONLY: "View your account settings",
            cls.SELL_INVENTORY: "View and manage your inventory and offers",
            cls.SELL_INVENTORY_READONLY: "View your inventory and offers",
            cls.SELL_FULFILLMENT: "View and manage your order fulfillments",
            cls.SELL_FULFILLMENT_READONLY: "View your order fulfillments",
            cls.SELL_ANALYTICS: "View your selling analytics data, such as performance reports",
            cls.SELL_MARKETPLACE_INSIGHTS_READONLY: "Read only access to marketplace insights",
            cls.SELL_FINANCES: "View and manage your payment and order information to display this information to you and allow you to initiate refunds using the third party application",
            cls.SELL_PAYMENT_DISPUTE: "View and manage disputes and related details (including payment and order information)",
            cls.SELL_ITEM: "View and manage your item information",
            cls.SELL_ITEM_DRAFT: "View and manage your item drafts",
            cls.SELL_REPUTATION: "View and manage your reputation data, such as feedback",
            cls.SELL_REPUTATION_READONLY: "View your reputation data, such as feedback",
            cls.SELL_STORES: "View and manage eBay stores",
            cls.SELL_STORES_READONLY: "View eBay stores",
            
            # Commerce API scopes
            cls.COMMERCE_CATALOG_READONLY: "Read catalog data",
            cls.COMMERCE_IDENTITY: "View a user's basic information, such as username or business account details, from their eBay member account",
            cls.COMMERCE_IDENTITY_EMAIL_READONLY: "View a user's personal email information from their eBay member account",
            cls.COMMERCE_IDENTITY_PHONE_READONLY: "View a user's personal telephone information from their eBay member account",
            cls.COMMERCE_IDENTITY_ADDRESS_READONLY: "View a user's personal address information from their eBay member account",
            cls.COMMERCE_IDENTITY_NAME_READONLY: "View a user's first and last name from their eBay member account",
            cls.COMMERCE_IDENTITY_STATUS_READONLY: "View a user's eBay member account status",
            cls.COMMERCE_NOTIFICATION_SUBSCRIPTION: "View and manage your event notification subscriptions",
            cls.COMMERCE_NOTIFICATION_SUBSCRIPTION_READONLY: "View your event notification subscriptions",
            cls.COMMERCE_VERO: "Access to APIs that are related to eBay's Verified Rights Owner (VeRO) program"
        }
        return scope_descriptions.get(scope, "Unknown scope")
    
    @classmethod
    def validate_scope(cls, scope: str) -> bool:
        """Validate that scope is a known eBay OAuth scope."""
        known_scopes = [
            # Basic scope
            cls.API_SCOPE,
            
            # Buy API scopes
            cls.BUY_BROWSE, cls.BUY_ORDER, cls.BUY_ORDER_READONLY, cls.BUY_GUEST_ORDER,
            cls.BUY_SHOPPING_CART, cls.BUY_OFFER, cls.BUY_OFFER_AUCTION, cls.BUY_MARKETING,
            cls.BUY_MARKETPLACE_INSIGHTS, cls.BUY_ITEM_FEED, cls.BUY_PRODUCT_FEED,
            cls.BUY_PROXY_GUEST_ORDER, cls.BUY_ITEM_BULK, cls.BUY_DEAL,
            
            # Sell API scopes
            cls.SELL_MARKETING, cls.SELL_MARKETING_READONLY, cls.SELL_ACCOUNT,
            cls.SELL_ACCOUNT_READONLY, cls.SELL_INVENTORY, cls.SELL_INVENTORY_READONLY,
            cls.SELL_FULFILLMENT, cls.SELL_FULFILLMENT_READONLY, cls.SELL_ANALYTICS,
            cls.SELL_MARKETPLACE_INSIGHTS_READONLY, cls.SELL_FINANCES, cls.SELL_PAYMENT_DISPUTE,
            cls.SELL_ITEM, cls.SELL_ITEM_DRAFT, cls.SELL_REPUTATION, cls.SELL_REPUTATION_READONLY,
            cls.SELL_STORES, cls.SELL_STORES_READONLY,
            
            # Commerce API scopes
            cls.COMMERCE_CATALOG_READONLY, cls.COMMERCE_IDENTITY, cls.COMMERCE_IDENTITY_EMAIL_READONLY,
            cls.COMMERCE_IDENTITY_PHONE_READONLY, cls.COMMERCE_IDENTITY_ADDRESS_READONLY,
            cls.COMMERCE_IDENTITY_NAME_READONLY, cls.COMMERCE_IDENTITY_STATUS_READONLY,
            cls.COMMERCE_NOTIFICATION_SUBSCRIPTION, cls.COMMERCE_NOTIFICATION_SUBSCRIPTION_READONLY,
            cls.COMMERCE_VERO
        ]
        
        # Check if scope is a single known scope or multiple space-separated scopes
        scopes = scope.split()
        return all(s in known_scopes for s in scopes)
