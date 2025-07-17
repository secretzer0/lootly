"""
eBay REST API Client with rate limiting and retry logic.

Provides a unified interface for making authenticated requests to eBay REST APIs
with built-in rate limiting, retry logic, and error handling.
"""
import asyncio
import time
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, Union
import aiohttp
from pydantic import BaseModel, Field
import logging
from contextlib import asynccontextmanager
import json as jsonpkg

from .oauth import OAuthManager, ConsentRequiredException

logger = logging.getLogger(__name__)


class RestConfig(BaseModel):
    """Configuration for REST API client."""
    sandbox: bool = Field(default=True, description="Use sandbox environment")
    rate_limit_per_day: int = Field(default=5000, description="API calls per day limit")
    max_retries: int = Field(default=3, description="Maximum retry attempts")
    timeout_seconds: int = Field(default=30, description="Request timeout in seconds")
    
    @property
    def base_url(self) -> str:
        """Get base API URL for the environment."""
        domain = "sandbox.ebay.com" if self.sandbox else "ebay.com"
        return f"https://api.{domain}"


class RateLimiter:
    """
    Token bucket rate limiter for API calls.
    
    Tracks daily API usage and enforces rate limits to prevent
    exceeding eBay's API quotas.
    """
    
    def __init__(self, calls_per_day: int = 5000):
        self.calls_per_day = calls_per_day
        self.window_start = datetime.now(timezone.utc)
        self.call_count = 0
        self._lock = asyncio.Lock()
        
    async def acquire(self) -> None:
        """
        Acquire permission to make an API call.
        
        Blocks if daily limit is reached until the next day.
        """
        async with self._lock:
            now = datetime.now(timezone.utc)
            
            # Reset counter if new day
            if now.date() > self.window_start.date():
                logger.info(f"Rate limiter reset. Previous day used {self.call_count}/{self.calls_per_day} calls")
                self.window_start = now
                self.call_count = 0
            
            # Check if limit reached
            if self.call_count >= self.calls_per_day:
                # Calculate wait time until next day
                tomorrow = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
                wait_seconds = (tomorrow - now).total_seconds()
                
                logger.warning(
                    f"Daily rate limit reached ({self.calls_per_day}). "
                    f"Waiting {wait_seconds:.0f} seconds until reset."
                )
                
                await asyncio.sleep(wait_seconds)
                
                # Reset after wait
                self.window_start = datetime.now(timezone.utc)
                self.call_count = 0
            
            self.call_count += 1
            
            if self.call_count % 100 == 0:
                logger.info(f"API calls today: {self.call_count}/{self.calls_per_day}")
    
    def get_usage(self) -> Dict[str, Any]:
        """Get current usage statistics."""
        return {
            "calls_today": self.call_count,
            "calls_limit": self.calls_per_day,
            "window_start": self.window_start.isoformat(),
            "percentage_used": (self.call_count / self.calls_per_day) * 100
        }


class EbayRestClient:
    """
    eBay REST API client with authentication, rate limiting, and retry logic.
    
    Features:
    - Automatic OAuth token management
    - Rate limiting to prevent quota exceeded errors
    - Exponential backoff retry for transient failures
    - Comprehensive error handling
    - Request/response logging
    """
    
    def __init__(self, oauth_manager: OAuthManager, config: Optional[RestConfig] = None):
        """
        Initialize eBay REST API client.
        
        Args:
            oauth_manager: OAuth manager for token management
            config: REST API configuration
        """
        self.oauth = oauth_manager
        self.config = config or RestConfig()
        self.rate_limiter = RateLimiter(self.config.rate_limit_per_day)
        self._session: Optional[aiohttp.ClientSession] = None
        
    @asynccontextmanager
    async def _get_session(self):
        """Get or create aiohttp session with proper cleanup."""
        if self._session is None:
            timeout = aiohttp.ClientTimeout(total=self.config.timeout_seconds)
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                raise_for_status=False
            )
        try:
            yield self._session
        except Exception:
            # Don't close session on error, it can be reused
            raise
    
    async def close(self) -> None:
        """Close the HTTP session."""
        if self._session:
            await self._session.close()
            self._session = None
    
    async def request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        scope: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Make authenticated API request with retries.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint path (e.g., "/buy/browse/v1/item/{item_id}")
            params: Query parameters
            json: JSON body for POST/PUT requests
            headers: Additional headers
            scope: OAuth scope for the request (uses default if not specified)
            
        Returns:
            Response data as dictionary
            
        Raises:
            EbayApiError: API-specific errors
            aiohttp.ClientError: Network errors
        """
        # Acquire rate limit token
        await self.rate_limiter.acquire()
        
        # Get OAuth token from manager
        # For user-required APIs, use get_token() which returns user token or raises ConsentRequiredException
        # For client-only APIs, use get_client_credentials_token() with specific scope
        if scope:
            # Client credentials token with specific scope
            token = await self.oauth.get_client_credentials_token(scope)
            logger.debug("Using client credentials token for API request")
        else:
            # User token for user-authorized APIs
            token = await self.oauth.get_token()
            logger.debug("Using user access token for API request")
            logger.debug(f"Token first 50 chars: {token[:50]}...")
            logger.debug(f"Token length: {len(token)}")
        
        # Build headers
        default_headers = {
            "Authorization": f"Bearer {token}",
            "X-EBAY-C-MARKETPLACE-ID": "EBAY_US",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Content-Language": "en-US"
        }
        
        if headers:
            default_headers.update(headers)
        
        # Build full URL
        url = f"{self.config.base_url}{endpoint}"
        
        # Log request
        logger.debug(f"{method} {url} (params: {params})")
        
        # Retry logic with exponential backoff
        last_error = None
        
        for attempt in range(self.config.max_retries):
            try:
                async with self._get_session() as session:
                    start_time = time.time()
                    
                    async with session.request(
                        method,
                        url,
                        params=params,
                        json=json,
                        headers=default_headers
                    ) as response:
                        response_time = time.time() - start_time
                        response_text = await response.text()
                        
                        # Log response
                        logger.debug(
                            f"{method} {url} -> {response.status} "
                            f"({response_time:.2f}s)"
                        )
                        
                        # Handle successful response
                        if response.status in (200, 201, 204):
                            if response_text:
                                return await response.json()
                            return {}
                        
                        # Parse error response
                        try:
                            error_data = await response.json()
                        except:
                            error_data = {"message": response_text}
                        
                        # Debug log error response
                        logger.debug(f"Error response text: {response_text[:500]}")
                        logger.debug(f"Error response headers: {dict(response.headers)}")
                        
                        # Handle specific error cases
                        if response.status == 401:
                            # Token expired, clear cache and retry
                            logger.warning("Token expired, refreshing...")
                            self.oauth.clear_cache()
                            
                            if attempt < self.config.max_retries - 1:
                                continue
                        
                        elif response.status == 429:
                            # Rate limited by eBay
                            retry_after = int(response.headers.get("X-EBAY-C-LIMIT-RESET", 60))
                            logger.warning(f"Rate limited by eBay. Waiting {retry_after}s...")
                            
                            if attempt < self.config.max_retries - 1:
                                await asyncio.sleep(retry_after)
                                continue
                        
                        # Import here to avoid circular dependency
                        from .errors import EbayApiError
                        
                        # Raise API error for non-retryable errors
                        raise EbayApiError(
                            status_code=response.status,
                            error_response=error_data,
                            request_id=response.headers.get("X-EBAY-C-REQUEST-ID")
                        )
                        
            except aiohttp.ClientError as e:
                last_error = e
                logger.error(f"Network error on attempt {attempt + 1}: {str(e)}")
                
                if attempt < self.config.max_retries - 1:
                    # Exponential backoff
                    wait_time = 2 ** attempt
                    logger.info(f"Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    continue
                    
            except Exception as e:
                last_error = e
                logger.error(f"Unexpected error on attempt {attempt + 1}: {str(e)}")
                
                if attempt < self.config.max_retries - 1:
                    wait_time = 2 ** attempt
                    await asyncio.sleep(wait_time)
                    continue
        
        # All retries exhausted
        if last_error:
            raise last_error
        else:
            raise Exception("Request failed after all retries")
    
    # Convenience methods for common HTTP verbs
    
    async def get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Make GET request."""
        return await self.request("GET", endpoint, params=params, **kwargs)
    
    async def post(
        self,
        endpoint: str,
        json: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Make POST request."""
        return await self.request("POST", endpoint, json=json, **kwargs)
    
    async def put(
        self,
        endpoint: str,
        json: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Make PUT request."""
        return await self.request("PUT", endpoint, json=json, **kwargs)
    
    async def delete(
        self,
        endpoint: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Make DELETE request."""
        return await self.request("DELETE", endpoint, **kwargs)
    
    def get_rate_limit_status(self) -> Dict[str, Any]:
        """Get current rate limiting status."""
        return self.rate_limiter.get_usage()


class MockEbayRestClient:
    """
    Mock REST client for testing.
    
    Records all requests and returns pre-configured responses.
    """
    
    def __init__(self, responses: Optional[Dict[str, Any]] = None):
        self.responses = responses or {}
        self.call_history = []
        
    async def request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        scope: Optional[str] = None
    ) -> Dict[str, Any]:
        """Record request and return mock response."""
        # Record the call
        self.call_history.append({
            "method": method,
            "endpoint": endpoint,
            "params": params,
            "json": json,
            "headers": headers,
            "scope": scope,
            "timestamp": datetime.now(timezone.utc)
        })
        
        # Generate response key
        key = f"{method} {endpoint}"
        
        if key in self.responses:
            response = self.responses[key]
            
            # Support callable responses for dynamic behavior
            if callable(response):
                return response(method, endpoint, params, json)
            
            return response
        
        # Default 404 response
        from .errors import EbayApiError
        raise EbayApiError(
            status_code=404,
            error_response={"message": f"Mock: {key} not found"}
        )
    
    # Implement convenience methods
    async def get(self, endpoint: str, **kwargs) -> Dict[str, Any]:
        return await self.request("GET", endpoint, **kwargs)
    
    async def post(self, endpoint: str, **kwargs) -> Dict[str, Any]:
        return await self.request("POST", endpoint, **kwargs)
    
    async def put(self, endpoint: str, **kwargs) -> Dict[str, Any]:
        return await self.request("PUT", endpoint, **kwargs)
    
    async def delete(self, endpoint: str, **kwargs) -> Dict[str, Any]:
        return await self.request("DELETE", endpoint, **kwargs)
    
    def get_rate_limit_status(self) -> Dict[str, Any]:
        """Mock rate limit status."""
        return {
            "calls_today": len(self.call_history),
            "calls_limit": 5000,
            "window_start": datetime.now(timezone.utc).isoformat(),
            "percentage_used": (len(self.call_history) / 5000) * 100
        }
    
    async def close(self) -> None:
        """No-op for mock client."""
        pass
