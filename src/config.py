"""Configuration for eBay MCP server."""
import os
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class EbayConfig(BaseModel):
    """Configuration for eBay API integration."""
    
    # Server identification
    server_name: str = Field("ebay-integration", description="Server name for logging")
    log_level: str = Field("INFO", description="Logging level")
    
    # Transport settings
    transport: str = Field("stdio", description="Transport type: stdio, sse, http")
    host: str = Field("127.0.0.1", description="Host for network transports")
    port: int = Field(8000, description="Port for network transports")
    
    # Required credentials
    app_id: str = Field(description="eBay Application ID")
    cert_id: Optional[str] = Field(None, description="Certificate ID (required for Trading API)")
    dev_id: Optional[str] = Field(None, description="Developer ID")
    
    # Environment settings
    sandbox_mode: bool = Field(True, description="Use sandbox environment")
    site_id: str = Field("EBAY-US", description="eBay site identifier")
    
    # API settings
    api_version: str = Field("1.13.0", description="API version")
    timeout: int = Field(30, description="API request timeout in seconds")
    max_retries: int = Field(3, description="Maximum retry attempts")
    
    # Cache settings
    cache_ttl: int = Field(300, description="Cache TTL in seconds (5 minutes)")
    redis_url: Optional[str] = Field(None, description="Redis URL for distributed caching")
    cache_memory_max_size: int = Field(1000, description="Maximum in-memory cache entries")
    
    # Rate limiting settings
    rate_limit_per_day: int = Field(5000, description="API calls per day limit")
    
    # Pagination settings
    page_size: int = Field(50, description="Default page size for listings")
    max_pages: int = Field(10, description="Maximum pages to fetch")
    
    @classmethod
    def from_env(cls) -> "EbayConfig":
        """Create config from environment variables."""
        return cls(
            app_id=os.environ.get("EBAY_APP_ID", ""),
            cert_id=os.environ.get("EBAY_CERT_ID"),
            dev_id=os.environ.get("EBAY_DEV_ID"),
            log_level=os.environ.get("LOOTLY_LOG_LEVEL", "INFO"),
            transport=os.environ.get("LOOTLY_TRANSPORT", "stdio"),
            host=os.environ.get("LOOTLY_HOST", "127.0.0.1"),
            port=int(os.environ.get("LOOTLY_PORT", "8000")),
            sandbox_mode=os.environ.get("EBAY_SANDBOX_MODE", "true").lower() == "true",
            site_id=os.environ.get("EBAY_SITE_ID", "EBAY-US"),
            api_version=os.environ.get("EBAY_API_VERSION", "1.13.0"),
            timeout=int(os.environ.get("EBAY_TIMEOUT", "30")),
            max_retries=int(os.environ.get("EBAY_MAX_RETRIES", "3")),
            cache_ttl=int(os.environ.get("EBAY_CACHE_TTL", "300")),
            redis_url=os.environ.get("REDIS_URL"),
            cache_memory_max_size=int(os.environ.get("CACHE_MEMORY_MAX_SIZE", "1000")),
            rate_limit_per_day=int(os.environ.get("EBAY_RATE_LIMIT_PER_DAY", "5000")),
            page_size=int(os.environ.get("EBAY_PAGE_SIZE", "50")),
            max_pages=int(os.environ.get("EBAY_MAX_PAGES", "10")),
        )
    
    @property
    def domain(self) -> str:
        """Get the API domain based on sandbox mode."""
        if self.sandbox_mode:
            return "sandbox.ebay.com"
        return "ebay.com"
    
    def validate_credentials(self) -> None:
        """Validate that required credentials are present."""
        if not self.app_id:
            raise ValueError(
                "EBAY_APP_ID environment variable is required.\n"
                "To get eBay developer credentials:\n"
                "1. Go to https://developer.ebay.com/my/keys\n"
                "2. Create a new application or select an existing one\n"
                "3. Copy the App ID from your application dashboard\n"
                "4. Set EBAY_APP_ID in your .env file or environment variables"
            )
        
        if not self.cert_id:
            raise ValueError(
                "EBAY_CERT_ID environment variable is required for full functionality.\n"
                "To get your Certificate ID:\n"
                "1. Go to https://developer.ebay.com/my/keys\n"
                "2. Select your application\n"
                "3. Copy the Certificate ID (Client Secret)\n"
                "4. Set EBAY_CERT_ID in your .env file\n"
                "WARNING: Keep this value secure - it's equivalent to a password!"
            )
    
    def check_credential_status(self) -> Dict[str, Any]:
        """Check credential status and provide helpful guidance."""
        status = {
            "app_id": bool(self.app_id),
            "cert_id": bool(self.cert_id),
            "dev_id": bool(self.dev_id),
            "ready_for_basic_apis": bool(self.app_id),
            "ready_for_user_apis": bool(self.app_id and self.cert_id),
            "fully_configured": bool(self.app_id and self.cert_id and self.dev_id)
        }
        
        # Generate helpful messages
        messages = []
        
        if not self.app_id:
            messages.append(
                "❌ EBAY_APP_ID missing - Required for all API access"
            )
        else:
            messages.append("✅ EBAY_APP_ID configured")
        
        if not self.cert_id:
            messages.append(
                "⚠️  EBAY_CERT_ID missing - Required for Account API and OAuth"
            )
        else:
            messages.append("✅ EBAY_CERT_ID configured")
        
        if not self.dev_id:
            messages.append(
                "⚠️  EBAY_DEV_ID missing - Required for some legacy APIs"
            )
        else:
            messages.append("✅ EBAY_DEV_ID configured")
        
        # Add functionality status
        if status["ready_for_basic_apis"]:
            messages.append("✅ Ready for: Browse, Catalog, Taxonomy APIs")
        
        if status["ready_for_user_apis"]:
            messages.append("✅ Ready for: Account API with OAuth")
        
        if not status["ready_for_basic_apis"]:
            messages.append(
                "🔗 Get credentials at: https://developer.ebay.com/my/keys"
            )
        
        status["messages"] = messages
        return status