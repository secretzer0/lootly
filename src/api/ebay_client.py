"""eBay API client wrapper for all eBay APIs."""
import asyncio
from typing import Dict, Any, Optional, List
from functools import lru_cache
import time
from ebaysdk.finding import Connection as Finding
from ebaysdk.trading import Connection as Trading
from ebaysdk.shopping import Connection as Shopping
from ebaysdk.merchandising import Connection as Merchandising
from ebaysdk.exception import ConnectionError
from config import EbayConfig
from logging_config import MCPLogger
from data_types import ErrorCode


class EbayApiClient:
    """Unified client for all eBay API connections."""
    
    def __init__(self, config: EbayConfig, logger: MCPLogger):
        self.config = config
        self.logger = logger
        self._cache: Dict[str, tuple[Any, float]] = {}
        
        # Initialize API connections
        self._finding_api = None
        self._trading_api = None
        self._shopping_api = None
        self._merchandising_api = None
    
    @property
    def finding(self) -> Finding:
        """Get or create Finding API connection."""
        if not self._finding_api:
            self._finding_api = Finding(
                appid=self.config.app_id,
                config_file=None,
                siteid=self.config.site_id,
                domain=f"svcs.{self.config.domain}"
            )
        return self._finding_api
    
    @property
    def trading(self) -> Trading:
        """Get or create Trading API connection."""
        if not self._trading_api:
            if not self.config.dev_id or not self.config.cert_id:
                raise ValueError("Trading API requires dev_id and cert_id")
            
            self._trading_api = Trading(
                appid=self.config.app_id,
                devid=self.config.dev_id,
                certid=self.config.cert_id,
                config_file=None,
                siteid=self.config.site_id,
                domain=f"api.{self.config.domain}"
            )
        return self._trading_api
    
    @property
    def shopping(self) -> Shopping:
        """Get or create Shopping API connection."""
        if not self._shopping_api:
            self._shopping_api = Shopping(
                appid=self.config.app_id,
                config_file=None,
                siteid=self.config.site_id,
                domain=f"open.api.{self.config.domain}"
            )
        return self._shopping_api
    
    @property
    def merchandising(self) -> Merchandising:
        """Get or create Merchandising API connection."""
        if not self._merchandising_api:
            self._merchandising_api = Merchandising(
                appid=self.config.app_id,
                config_file=None,
                siteid=self.config.site_id,
                domain=f"svcs.{self.config.domain}"
            )
        return self._merchandising_api
    
    async def execute_with_retry(
        self,
        api_name: str,
        operation: str,
        params: Dict[str, Any],
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """Execute an API call with retry logic and caching."""
        # Check cache first
        if use_cache:
            cache_key = f"{api_name}:{operation}:{str(params)}"
            cached = self._get_cached(cache_key)
            if cached:
                self.logger.api_cache_hit(api_name, operation)
                return cached
        
        # Get the appropriate API connection
        api = getattr(self, api_name)
        
        # Execute with retries
        last_error = None
        for attempt in range(self.config.max_retries):
            try:
                start_time = time.time()
                
                # Execute in thread pool since ebaysdk is synchronous
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    api.execute,
                    operation,
                    params
                )
                
                duration = time.time() - start_time
                self.logger.external_api_called(
                    api_name,
                    f"{operation}",
                    200,
                    duration
                )
                
                # Cache successful response
                if use_cache:
                    self._set_cached(cache_key, response.dict())
                
                return response.dict()
                
            except ConnectionError as e:
                last_error = e
                self.logger.external_api_failed(
                    api_name,
                    f"{operation}",
                    str(e),
                    attempt + 1
                )
                
                if attempt < self.config.max_retries - 1:
                    # Exponential backoff
                    await asyncio.sleep(2 ** attempt)
        
        # All retries failed
        raise last_error
    
    def _get_cached(self, key: str) -> Optional[Dict[str, Any]]:
        """Get cached data if not expired."""
        if key in self._cache:
            data, timestamp = self._cache[key]
            if time.time() - timestamp < self.config.cache_ttl:
                return data
            else:
                # Remove expired cache
                del self._cache[key]
        return None
    
    def _set_cached(self, key: str, data: Dict[str, Any]) -> None:
        """Set cache data with timestamp."""
        self._cache[key] = (data, time.time())
    
    def clear_cache(self) -> None:
        """Clear all cached data."""
        self._cache.clear()
        self.logger.info("Cache cleared")
    
    def validate_pagination(self, page_number: int) -> None:
        """Validate pagination parameters."""
        if page_number < 1:
            raise ValueError("Page number must be >= 1")
        if page_number > self.config.max_pages:
            raise ValueError(f"Page number exceeds maximum of {self.config.max_pages}")
    
    def format_error_response(self, error: Exception, error_code: ErrorCode) -> Dict[str, Any]:
        """Format error response for consistency."""
        return {
            "success": False,
            "error": {
                "code": error_code.value,
                "message": str(error),
                "type": type(error).__name__
            }
        }