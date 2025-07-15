"""
Temporary placeholder for eBay API client.

This module is being replaced with the new REST API implementation.
It provides a stub to prevent import errors during migration.
"""
from typing import Dict, Any, Optional
from unittest.mock import Mock
from config import EbayConfig
from logging_config import MCPLogger


# Mock classes for old SDK compatibility during migration
class Finding(Mock):
    """Mock Finding API class."""
    pass


class Trading(Mock):
    """Mock Trading API class."""
    pass


class Shopping(Mock):
    """Mock Shopping API class."""
    pass


class Merchandising(Mock):
    """Mock Merchandising API class."""
    pass


class EbayApiClient:
    """
    Temporary stub for eBay API client.
    
    This class is being replaced by the new REST API implementation
    using OAuth 2.0 and modern eBay REST APIs.
    """
    
    def __init__(self, config: EbayConfig, logger: MCPLogger):
        self.config = config
        self.logger = logger
        # Note: Using placeholder during REST API migration
        
        # Mock API connections for compatibility
        self._finding_api = None
        self._trading_api = None
        self._shopping_api = None
        self._merchandising_api = None
    
    @property
    def finding(self):
        """Mock Finding API connection."""
        if not self._finding_api:
            self._finding_api = Finding(
                appid=self.config.app_id,
                config_file=None,
                siteid=self.config.site_id,
                domain=f"svcs.{self.config.domain}"
            )
        return self._finding_api
    
    @property
    def trading(self):
        """Mock Trading API connection."""
        if not self._trading_api:
            self._trading_api = Trading(
                appid=self.config.app_id,
                devid=getattr(self.config, 'dev_id', None),
                certid=getattr(self.config, 'cert_id', None),
                config_file=None,
                siteid=self.config.site_id,
                domain=f"api.{self.config.domain}"
            )
        return self._trading_api
    
    @property
    def shopping(self):
        """Mock Shopping API connection."""
        if not self._shopping_api:
            self._shopping_api = Shopping(
                appid=self.config.app_id,
                config_file=None,
                siteid=self.config.site_id,
                domain=f"open.api.{self.config.domain}"
            )
        return self._shopping_api
    
    @property
    def merchandising(self):
        """Mock Merchandising API connection."""
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
        """Placeholder method that returns migration notice."""
        return {
            "success": False,
            "error": {
                "code": "MIGRATION_IN_PROGRESS",
                "message": f"The {api_name} API is being migrated to REST. This operation is temporarily unavailable.",
                "details": {
                    "api": api_name,
                    "operation": operation,
                    "migration_status": "in_progress"
                }
            }
        }
    
    def validate_pagination(self, page_number: int) -> None:
        """Validate pagination parameters."""
        if page_number < 1:
            raise ValueError("Page number must be >= 1")
        if page_number > 100:
            raise ValueError("Page number exceeds maximum of 100")
    
    def format_error_response(self, error: Exception, error_code: str) -> Dict[str, Any]:
        """Format error response for consistency."""
        return {
            "success": False,
            "error": {
                "code": error_code,
                "message": str(error),
                "type": type(error).__name__
            }
        }