"""
eBay OAuth 2.0 Manager for REST API Authentication.

Handles client credentials flow for application-level access to eBay APIs.
Includes token caching and automatic refresh functionality.
"""
import base64
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict
import aiohttp
from pydantic import BaseModel, Field
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


class CachedToken(BaseModel):
    """Cached OAuth token with expiration tracking."""
    access_token: str
    token_type: str = "Bearer"
    expires_at: datetime
    scope: Optional[str] = None
    
    def is_expired(self, buffer_minutes: int = 5) -> bool:
        """Check if token is expired with configurable buffer."""
        return datetime.utcnow() >= self.expires_at - timedelta(minutes=buffer_minutes)
    
    def time_until_expiry(self) -> timedelta:
        """Get time remaining until token expires."""
        return self.expires_at - datetime.utcnow()
    
    def is_near_expiry(self, buffer_minutes: int = 10) -> bool:
        """Check if token is near expiry (within buffer time)."""
        return datetime.utcnow() >= self.expires_at - timedelta(minutes=buffer_minutes)


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
        logger.debug(f"Using endpoint: {self.config.token_url}")
        
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
                    expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
                    
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
    """Common eBay OAuth scopes for different API access levels."""
    
    # Buy API scopes
    BUY_BROWSE = "https://api.ebay.com/oauth/api_scope"  # Basic scope for Browse API
    BUY_OFFER = "https://api.ebay.com/oauth/api_scope/buy.offer"
    BUY_ORDER = "https://api.ebay.com/oauth/api_scope/buy.order"
    BUY_MARKETING = "https://api.ebay.com/oauth/api_scope/buy.marketing"
    BUY_INSIGHTS = "https://api.ebay.com/oauth/api_scope/buy.marketplace.insights"
    
    # Sell API scopes
    SELL_INVENTORY = "https://api.ebay.com/oauth/api_scope/sell.inventory"
    SELL_INVENTORY_READONLY = "https://api.ebay.com/oauth/api_scope/sell.inventory.readonly"
    SELL_MARKETING = "https://api.ebay.com/oauth/api_scope/sell.marketing"
    SELL_ACCOUNT = "https://api.ebay.com/oauth/api_scope/sell.account"
    SELL_ACCOUNT_READONLY = "https://api.ebay.com/oauth/api_scope/sell.account.readonly"
    SELL_FULFILLMENT = "https://api.ebay.com/oauth/api_scope/sell.fulfillment"
    SELL_ANALYTICS = "https://api.ebay.com/oauth/api_scope/sell.analytics.readonly"
    SELL_FINANCES = "https://api.ebay.com/oauth/api_scope/sell.finances"
    
    # Commerce API scopes
    COMMERCE_CATALOG = "https://api.ebay.com/oauth/api_scope/commerce.catalog.readonly"
    COMMERCE_TAXONOMY = "https://api.ebay.com/oauth/api_scope/commerce.taxonomy.readonly"
    COMMERCE_IDENTITY = "https://api.ebay.com/oauth/api_scope/commerce.identity.readonly"
    
    # Combined scopes for common use cases
    ALL_BUY = " ".join([BUY_BROWSE, BUY_OFFER, BUY_ORDER, BUY_MARKETING, BUY_INSIGHTS])
    ALL_SELL = " ".join([SELL_INVENTORY, SELL_MARKETING, SELL_ACCOUNT, SELL_FULFILLMENT])
    ALL_COMMERCE = " ".join([COMMERCE_CATALOG, COMMERCE_TAXONOMY, COMMERCE_IDENTITY])
    
    # User consent scopes (require user authorization)
    USER_CONSENT_SCOPES = " ".join([SELL_ACCOUNT, SELL_INVENTORY])
    
    # Basic API access (default)
    API_SCOPE = "https://api.ebay.com/oauth/api_scope"
    
    @classmethod
    def get_scope_description(cls, scope: str) -> str:
        """Get human-readable description of OAuth scope."""
        scope_descriptions = {
            cls.BUY_BROWSE: "Browse items and search eBay marketplace",
            cls.BUY_OFFER: "Make offers on eBay items",
            cls.BUY_ORDER: "Manage purchase orders",
            cls.BUY_MARKETING: "Access marketing and promotional data",
            cls.BUY_INSIGHTS: "Access marketplace insights and analytics",
            cls.SELL_INVENTORY: "Manage inventory items and listings",
            cls.SELL_INVENTORY_READONLY: "Read-only access to inventory items",
            cls.SELL_MARKETING: "Manage marketing campaigns and promotions",
            cls.SELL_ACCOUNT: "Manage seller account settings and policies",
            cls.SELL_ACCOUNT_READONLY: "Read-only access to seller account data",
            cls.SELL_FULFILLMENT: "Manage order fulfillment and shipping",
            cls.SELL_ANALYTICS: "Access seller analytics and performance data",
            cls.SELL_FINANCES: "Access financial data and reports",
            cls.COMMERCE_CATALOG: "Access product catalog data",
            cls.COMMERCE_TAXONOMY: "Access category and taxonomy data",
            cls.COMMERCE_IDENTITY: "Access identity and profile data",
            cls.API_SCOPE: "Basic API access"
        }
        return scope_descriptions.get(scope, "Unknown scope")
    
    @classmethod
    def validate_scope(cls, scope: str) -> bool:
        """Validate that scope is a known eBay OAuth scope."""
        known_scopes = [
            cls.BUY_BROWSE, cls.BUY_OFFER, cls.BUY_ORDER, cls.BUY_MARKETING, cls.BUY_INSIGHTS,
            cls.SELL_INVENTORY, cls.SELL_INVENTORY_READONLY, cls.SELL_MARKETING, 
            cls.SELL_ACCOUNT, cls.SELL_ACCOUNT_READONLY, cls.SELL_FULFILLMENT,
            cls.SELL_ANALYTICS, cls.SELL_FINANCES,
            cls.COMMERCE_CATALOG, cls.COMMERCE_TAXONOMY, cls.COMMERCE_IDENTITY,
            cls.API_SCOPE
        ]
        
        # Check if scope is a single known scope or multiple space-separated scopes
        scopes = scope.split()
        return all(s in known_scopes for s in scopes)