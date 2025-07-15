"""
eBay REST API Error Handling Framework.

Provides comprehensive error handling with structured exceptions
for different API error scenarios.
"""
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from enum import Enum


class ErrorSeverity(str, Enum):
    """Error severity levels."""
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ErrorCategory(str, Enum):
    """Error categories for classification."""
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    VALIDATION = "validation"
    RATE_LIMIT = "rate_limit"
    NOT_FOUND = "not_found"
    BUSINESS_LOGIC = "business_logic"
    SERVER_ERROR = "server_error"
    NETWORK = "network"
    UNKNOWN = "unknown"


class ErrorDetail(BaseModel):
    """Detailed error information from eBay API."""
    error_id: Optional[int] = Field(None, description="eBay error ID")
    domain: Optional[str] = Field(None, description="Error domain")
    subdomain: Optional[str] = Field(None, description="Error subdomain")
    category: Optional[str] = Field(None, description="eBay error category")
    message: str = Field(..., description="Error message")
    long_message: Optional[str] = Field(None, description="Detailed error message")
    input_ref_ids: Optional[List[str]] = Field(None, description="Input fields that caused error")
    output_ref_ids: Optional[List[str]] = Field(None, description="Output fields affected")
    parameters: Optional[List[Dict[str, Any]]] = Field(None, description="Error parameters")


class EbayApiException(Exception):
    """Base exception for all eBay API errors."""
    
    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.category = category
        self.severity = severity
        self.details = details or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for logging/response."""
        return {
            "error": {
                "type": self.__class__.__name__,
                "message": self.message,
                "category": self.category.value,
                "severity": self.severity.value,
                "details": self.details
            }
        }


class EbayApiError(EbayApiException):
    """
    eBay API HTTP error response.
    
    Used for errors returned by the eBay REST API with HTTP status codes.
    """
    
    def __init__(
        self,
        status_code: int,
        error_response: Dict[str, Any],
        request_id: Optional[str] = None
    ):
        # Parse eBay error response structure
        errors = error_response.get("errors", [])
        if not errors and "message" in error_response:
            # Simple error format
            errors = [{
                "message": error_response["message"],
                "error_id": error_response.get("error_id"),
                "domain": error_response.get("domain")
            }]
        
        # Get primary error message
        primary_error = errors[0] if errors else {}
        message = primary_error.get("message", f"HTTP {status_code} error")
        
        # Determine category based on status code and error details
        category = self._determine_category(status_code, primary_error)
        severity = self._determine_severity(status_code)
        
        # Build details
        details = {
            "status_code": status_code,
            "request_id": request_id,
            "errors": [ErrorDetail(**err).dict(exclude_none=True) for err in errors if isinstance(err, dict)]
        }
        
        super().__init__(message, category, severity, details)
        self.status_code = status_code
        self.request_id = request_id
        self.errors = [ErrorDetail(**err) for err in errors if isinstance(err, dict)]
    
    def _determine_category(self, status_code: int, error: Dict[str, Any]) -> ErrorCategory:
        """Determine error category from status code and error details."""
        # Check error domain first
        domain = error.get("domain", "") or ""
        domain = domain.lower()
        if "auth" in domain:
            return ErrorCategory.AUTHENTICATION if status_code == 401 else ErrorCategory.AUTHORIZATION
        
        # Map by status code
        status_map = {
            400: ErrorCategory.VALIDATION,
            401: ErrorCategory.AUTHENTICATION,
            403: ErrorCategory.AUTHORIZATION,
            404: ErrorCategory.NOT_FOUND,
            429: ErrorCategory.RATE_LIMIT,
            500: ErrorCategory.SERVER_ERROR,
            502: ErrorCategory.SERVER_ERROR,
            503: ErrorCategory.SERVER_ERROR,
            504: ErrorCategory.SERVER_ERROR
        }
        
        return status_map.get(status_code, ErrorCategory.UNKNOWN)
    
    def _determine_severity(self, status_code: int) -> ErrorSeverity:
        """Determine error severity from status code."""
        if status_code >= 500:
            return ErrorSeverity.CRITICAL
        elif status_code >= 400:
            return ErrorSeverity.ERROR
        else:
            return ErrorSeverity.WARNING
    
    def is_retryable(self) -> bool:
        """Check if error is retryable."""
        # Server errors and rate limits are retryable
        return self.category in [
            ErrorCategory.SERVER_ERROR,
            ErrorCategory.RATE_LIMIT,
            ErrorCategory.NETWORK
        ] or self.status_code in [408, 409, 502, 503, 504]
    
    def get_retry_after(self) -> Optional[int]:
        """Get retry-after seconds if available."""
        for error in self.errors:
            for param in error.parameters or []:
                if param.get("name") == "retry_after":
                    return int(param.get("value", 60))
        return None


class AuthenticationError(EbayApiException):
    """OAuth authentication failures."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message,
            ErrorCategory.AUTHENTICATION,
            ErrorSeverity.ERROR,
            details
        )


class AuthorizationError(EbayApiException):
    """Insufficient permissions or invalid scopes."""
    
    def __init__(self, message: str, required_scope: Optional[str] = None):
        details = {"required_scope": required_scope} if required_scope else {}
        super().__init__(
            message,
            ErrorCategory.AUTHORIZATION,
            ErrorSeverity.ERROR,
            details
        )


class ValidationError(EbayApiException):
    """Input validation failures."""
    
    def __init__(self, message: str, field_errors: Optional[Dict[str, str]] = None):
        details = {"field_errors": field_errors} if field_errors else {}
        super().__init__(
            message,
            ErrorCategory.VALIDATION,
            ErrorSeverity.ERROR,
            details
        )


class RateLimitError(EbayApiException):
    """API rate limit exceeded."""
    
    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[int] = None,
        limit: Optional[int] = None,
        remaining: Optional[int] = None
    ):
        details = {
            "retry_after": retry_after,
            "limit": limit,
            "remaining": remaining
        }
        super().__init__(
            message,
            ErrorCategory.RATE_LIMIT,
            ErrorSeverity.WARNING,
            details
        )
        self.retry_after = retry_after


class NotFoundError(EbayApiException):
    """Resource not found."""
    
    def __init__(self, resource_type: str, resource_id: str):
        message = f"{resource_type} '{resource_id}' not found"
        details = {
            "resource_type": resource_type,
            "resource_id": resource_id
        }
        super().__init__(
            message,
            ErrorCategory.NOT_FOUND,
            ErrorSeverity.ERROR,
            details
        )


class BusinessError(EbayApiException):
    """eBay business logic errors."""
    
    def __init__(self, message: str, error_code: Optional[str] = None):
        details = {"error_code": error_code} if error_code else {}
        super().__init__(
            message,
            ErrorCategory.BUSINESS_LOGIC,
            ErrorSeverity.ERROR,
            details
        )


class NetworkError(EbayApiException):
    """Network connectivity issues."""
    
    def __init__(self, message: str = "Network error occurred", original_error: Optional[Exception] = None):
        details = {
            "original_error": str(original_error) if original_error else None,
            "error_type": type(original_error).__name__ if original_error else None
        }
        super().__init__(
            message,
            ErrorCategory.NETWORK,
            ErrorSeverity.ERROR,
            details
        )


class ConfigurationError(EbayApiException):
    """Invalid configuration or missing credentials."""
    
    def __init__(self, message: str, missing_fields: Optional[List[str]] = None):
        details = {"missing_fields": missing_fields} if missing_fields else {}
        super().__init__(
            message,
            ErrorCategory.VALIDATION,
            ErrorSeverity.CRITICAL,
            details
        )


def handle_api_error(func):
    """
    Decorator to handle API errors consistently.
    
    Wraps async functions to catch and transform exceptions into
    structured error responses.
    """
    import functools
    
    @functools.wraps(func)
    async def wrapper(ctx, **kwargs):
        try:
            return await func(ctx, **kwargs)
        except EbayApiException:
            # Re-raise our exceptions as-is
            raise
        except Exception as e:
            # Wrap unexpected exceptions
            raise EbayApiException(
                message=f"Unexpected error: {str(e)}",
                category=ErrorCategory.UNKNOWN,
                severity=ErrorSeverity.ERROR,
                details={"original_error": str(e)}
            )
    
    return wrapper


class ErrorResponse(BaseModel):
    """Standard error response format."""
    success: bool = Field(default=False)
    error: Dict[str, Any] = Field(..., description="Error details")
    request_id: Optional[str] = Field(None, description="Request tracking ID")
    
    @classmethod
    def from_exception(cls, exception: EbayApiException, request_id: Optional[str] = None):
        """Create error response from exception."""
        return cls(
            success=False,
            error=exception.to_dict()["error"],
            request_id=request_id
        )