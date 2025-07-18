# Project Requirements Plan: eBay Error Handling Enhancement Framework
**Version**: 1.0  
**Date**: 2025-01-18  
**Author**: Claude  
**Status**: Draft  

## Executive Summary

This PRP outlines a comprehensive enhancement to our error handling framework to align with eBay's official error handling guidance. The current implementation provides basic error capture but lacks the intelligent error analysis, actionable guidance, and sophisticated retry strategies that eBay's APIs require.

### Key Objectives:
1. **Implement eBay's Three-Category Error System** (APPLICATION, BUSINESS, REQUEST)
2. **Surface Actionable Error Guidance** to LLMs, MCPs, and developers
3. **Implement Intelligent Retry Strategies** based on error categories
4. **Add Warning Support System** for non-blocking issues
5. **Enhance Test Suite Error Classification** for better diagnostics

### Critical Problem Solved:
The recent deposit.dueIn bug exemplified how poor error handling masks real issues. Instead of hiding errors with "successful failures," this framework will provide specific, actionable guidance that leads to solutions.

### Business Value:
- **Reduced Development Time**: Clear error guidance eliminates guesswork
- **Improved API Reliability**: Intelligent retry strategies reduce transient failures
- **Better LLM Integration**: Actionable error messages enable autonomous problem-solving
- **Enhanced Debugging**: Precise error classification accelerates issue resolution

---

## eBay Error Handling Standards Analysis

### Official eBay Error Response Structure

Based on [eBay's Error Handling Documentation](https://developer.ebay.com/api-docs/static/handling-error-messages.html):

```json
{
  "errors": [{
    "errorId": 15008,
    "domain": "API_ORDER",
    "subDomain": "string",
    "category": "REQUEST|APPLICATION|BUSINESS",
    "message": "Invalid Field: itemId",
    "longMessage": "The item ID is not valid for the specified marketplace",
    "inputRefIds": ["$.lineItemInputs[0].itemId"],
    "outputRefIds": ["$.errors[0]"],
    "parameters": [
      {"name": "itemId", "value": "2200077988|0"},
      {"name": "marketplace", "value": "EBAY_US"}
    ]
  }],
  "warnings": [{
    "warningId": 25001,
    "category": "BUSINESS",
    "message": "Inventory quantity adjusted",
    "longMessage": "Available quantity was reduced to match inventory",
    "parameters": [{"name": "adjustedQuantity", "value": "5"}]
  }]
}
```

### eBay's Three Error Categories

#### 1. **APPLICATION Category**
- **Definition**: Runtime exceptions, system failures, infrastructure issues
- **Characteristics**: Usually HTTP 500, temporary system problems
- **Action Required**: Contact eBay Developer Support
- **Retry Strategy**: Do not retry - these are system-level issues
- **Examples**: Database timeouts, service unavailable, internal server errors

#### 2. **BUSINESS Category** 
- **Definition**: Business rule violations, policy constraints
- **Characteristics**: HTTP 400, violates eBay business logic
- **Action Required**: Modify request to comply with business rules
- **Retry Strategy**: Do not retry without fixing the violation
- **Examples**: Item not eligible for category, shipping policy mismatch, seller restrictions

#### 3. **REQUEST Category**
- **Definition**: Syntax errors, authentication issues, malformed requests
- **Characteristics**: HTTP 400/401/403, correctable request issues
- **Action Required**: Fix request structure, authentication, or parameters
- **Retry Strategy**: Retry after correcting the request
- **Examples**: Invalid JSON, missing required fields, expired tokens

### Warning vs Error Distinction

**Errors:**
- Stop processing completely
- Return HTTP 4xx/5xx status codes
- Must be resolved before operation can succeed

**Warnings:**
- Allow processing to continue
- Return HTTP 200 with warning array
- Indicate potential issues or adjustments made
- Should be logged but don't block operation

---

## Current System Assessment

### Existing Error Handling Architecture

#### `src/api/errors.py` - Current Implementation
**Strengths:**
- Good foundation with `EbayApiError` class
- Captures most eBay error fields (errorId, domain, message, etc.)
- Basic retry logic with `is_retryable()` method
- Structured error responses

**Critical Gaps:**
1. **Category Mismatch**: Our categories don't align with eBay's three categories
2. **No Actionable Guidance**: Errors don't suggest specific actions
3. **Missing Warning Support**: No distinction between warnings and errors
4. **Limited LLM Integration**: Error messages aren't optimized for LLM consumption
5. **Basic Retry Logic**: Doesn't implement eBay's category-specific strategies
6. **No JSONPath Interpretation**: inputRefIds/outputRefIds aren't explained

#### Current Error Categories vs eBay Categories

**Our Current Categories:**
```python
class ErrorCategory(str, Enum):
    AUTHENTICATION = "authentication"      # → REQUEST
    AUTHORIZATION = "authorization"        # → REQUEST  
    VALIDATION = "validation"              # → REQUEST
    RATE_LIMIT = "rate_limit"             # → REQUEST
    NOT_FOUND = "not_found"               # → REQUEST
    BUSINESS_LOGIC = "business_logic"      # → BUSINESS
    SERVER_ERROR = "server_error"          # → APPLICATION
    NETWORK = "network"                    # → APPLICATION
    UNKNOWN = "unknown"                    # → APPLICATION
```

#### Integration Points Requiring Updates

1. **`src/data_types.py`**: MCPErrorResponse structure
2. **All API Tools**: Error handling patterns in return_policy_api.py, payment_policy_api.py, etc.
3. **Test Suites**: Error classification and expected behavior
4. **`src/api/rest_client.py`**: HTTP client error handling
5. **MCP Response Patterns**: Error surfacing to LLMs

---

## Enhanced Error Classification Framework

### New eBay-Aligned Error Categories

```python
class EbayErrorCategory(str, Enum):
    """eBay's official error categories with action guidance."""
    
    APPLICATION = "APPLICATION"
    BUSINESS = "BUSINESS" 
    REQUEST = "REQUEST"
    
    def get_action_guidance(self) -> str:
        """Get actionable guidance for this error category."""
        guidance = {
            "APPLICATION": "System error - contact eBay Developer Support. Do not retry.",
            "BUSINESS": "Business rule violation - modify request to comply with policies. Do not retry without changes.",
            "REQUEST": "Request error - fix syntax, authentication, or parameters. Safe to retry after correction."
        }
        return guidance[self.value]
    
    def is_retryable(self) -> bool:
        """Determine if errors in this category are retryable."""
        return self == EbayErrorCategory.REQUEST
    
    def get_retry_strategy(self) -> str:
        """Get recommended retry strategy."""
        strategies = {
            "APPLICATION": "none",
            "BUSINESS": "none", 
            "REQUEST": "exponential_backoff"
        }
        return strategies[self.value]
```

### Enhanced EbayApiError Class

```python
class EbayApiError(EbayApiException):
    """Enhanced eBay API error with actionable guidance."""
    
    def __init__(self, status_code: int, error_response: Dict[str, Any], request_id: Optional[str] = None):
        # ... existing initialization ...
        
        # New enhancements
        self.ebay_category = self._determine_ebay_category()
        self.action_guidance = self._generate_action_guidance()
        self.llm_guidance = self._generate_llm_guidance()
        self.retry_strategy = self._determine_retry_strategy()
        self.field_issues = self._analyze_field_issues()
    
    def _determine_ebay_category(self) -> EbayErrorCategory:
        """Determine eBay error category from error details."""
        for error in self.errors:
            if error.category:
                return EbayErrorCategory(error.category)
        
        # Fallback to status code mapping
        if self.status_code >= 500:
            return EbayErrorCategory.APPLICATION
        elif self.status_code in [400, 422]:
            return EbayErrorCategory.BUSINESS  # Most 400s are business rule violations
        elif self.status_code in [401, 403]:
            return EbayErrorCategory.REQUEST
        else:
            return EbayErrorCategory.APPLICATION
    
    def _generate_action_guidance(self) -> Dict[str, Any]:
        """Generate specific action guidance for this error."""
        return {
            "category": self.ebay_category.value,
            "guidance": self.ebay_category.get_action_guidance(),
            "retryable": self.ebay_category.is_retryable(),
            "retry_strategy": self.ebay_category.get_retry_strategy(),
            "next_steps": self._get_specific_next_steps()
        }
    
    def _generate_llm_guidance(self) -> str:
        """Generate LLM-specific guidance for this error."""
        guidance_parts = []
        
        # Start with category-specific guidance
        guidance_parts.append(f"eBay {self.ebay_category.value} Error:")
        guidance_parts.append(self.ebay_category.get_action_guidance())
        
        # Add field-specific issues
        if self.field_issues:
            guidance_parts.append("\nField Issues:")
            for field, issue in self.field_issues.items():
                guidance_parts.append(f"- {field}: {issue}")
        
        # Add specific error context
        for error in self.errors:
            if error.long_message and error.long_message != error.message:
                guidance_parts.append(f"\nDetailed Issue: {error.long_message}")
            
            if error.parameters:
                guidance_parts.append("\nError Parameters:")
                for param in error.parameters:
                    guidance_parts.append(f"- {param.get('name')}: {param.get('value')}")
        
        return "\n".join(guidance_parts)
    
    def _analyze_field_issues(self) -> Dict[str, str]:
        """Analyze inputRefIds to identify specific field issues."""
        field_issues = {}
        
        for error in self.errors:
            if error.input_ref_ids:
                for ref_id in error.input_ref_ids:
                    if ref_id:
                        field_name = self._interpret_json_path(ref_id)
                        field_issues[field_name] = self._get_field_specific_guidance(error, ref_id)
        
        return field_issues
    
    def _interpret_json_path(self, json_path: str) -> str:
        """Convert JSONPath reference to human-readable field name."""
        # Extract meaningful field names from JSONPath
        # Example: "$.lineItemInputs[0].itemId" → "itemId in line item 1"
        # Example: "$.deposit.dueIn" → "deposit.dueIn"
        
        if not json_path or json_path == "$":
            return "request_root"
        
        # Remove $ prefix and parse path
        path = json_path.replace("$.", "")
        
        # Handle array indices
        import re
        path = re.sub(r'\[(\d+)\]', r' (item \1)', path)
        
        return path.replace(".", " → ")
    
    def _get_field_specific_guidance(self, error: ErrorDetail, json_path: str) -> str:
        """Get specific guidance for a field error."""
        # Common field error patterns
        field_guidance = {
            "dueIn": "Must be TimeDuration object with unit='HOUR' and value in [24,48,72]",
            "marketplaceId": "Must be valid MarketplaceIdEnum value (e.g., 'EBAY_US')",
            "categoryTypes": "Must be array of CategoryType objects with valid CategoryTypeEnum values",
            "itemId": "Must be valid eBay item ID format",
        }
        
        # Extract field name from JSONPath
        field_name = json_path.split(".")[-1].replace("[0]", "")
        
        # Return specific guidance if available
        if field_name in field_guidance:
            return field_guidance[field_name]
        
        # Generic guidance based on error message
        return f"Check {field_name} value against API documentation"
```

### Warning Support System

```python
class EbayApiWarning(BaseModel):
    """eBay API warning structure."""
    warning_id: Optional[int] = Field(None, alias="warningId")
    category: Optional[str] = None
    message: str
    long_message: Optional[str] = Field(None, alias="longMessage")
    parameters: Optional[List[Dict[str, Any]]] = None
    
    model_config = ConfigDict(populate_by_name=True)

class EbayApiResponse(BaseModel):
    """Enhanced API response with warning support."""
    success: bool
    data: Optional[Any] = None
    errors: Optional[List[EbayApiError]] = None
    warnings: Optional[List[EbayApiWarning]] = None
    
    def has_warnings(self) -> bool:
        return bool(self.warnings)
    
    def has_errors(self) -> bool:
        return bool(self.errors)
    
    def should_continue_processing(self) -> bool:
        """Determine if processing should continue despite issues."""
        return not self.has_errors()  # Continue with warnings, stop on errors
```

---

## LLM/MCP Error Guidance System

### Actionable Error Message Generation

```python
class EbayErrorAnalyzer:
    """Intelligent analysis of eBay errors for actionable guidance."""
    
    def analyze_error(self, error: EbayApiError) -> ErrorActionGuidance:
        """Comprehensive error analysis with actionable guidance."""
        return ErrorActionGuidance(
            category=error.ebay_category,
            severity=self._determine_severity(error),
            action_required=self._get_action_required(error),
            specific_steps=self._get_specific_steps(error),
            code_fixes=self._suggest_code_fixes(error),
            retry_guidance=self._get_retry_guidance(error),
            escalation_path=self._get_escalation_path(error)
        )
    
    def generate_llm_response(self, error: EbayApiError) -> str:
        """Generate LLM-optimized error response."""
        response_parts = []
        
        # Error category and immediate action
        response_parts.append(f"❌ eBay {error.ebay_category.value} Error")
        response_parts.append(f"Action: {error.ebay_category.get_action_guidance()}")
        
        # Specific error details
        for err in error.errors:
            response_parts.append(f"\nError {err.error_id}: {err.message}")
            if err.long_message:
                response_parts.append(f"Details: {err.long_message}")
        
        # Field-specific issues with solutions
        if error.field_issues:
            response_parts.append("\n🔧 Field Issues & Solutions:")
            for field, guidance in error.field_issues.items():
                response_parts.append(f"• {field}: {guidance}")
        
        # Code fix suggestions
        code_fixes = self._suggest_code_fixes(error)
        if code_fixes:
            response_parts.append("\n💡 Suggested Fixes:")
            for fix in code_fixes:
                response_parts.append(f"• {fix}")
        
        # Retry guidance
        if error.ebay_category.is_retryable():
            response_parts.append(f"\n🔄 Retry: {error.ebay_category.get_retry_strategy()}")
        else:
            response_parts.append("\n🚫 Do not retry without fixing the underlying issue")
        
        return "\n".join(response_parts)
    
    def _suggest_code_fixes(self, error: EbayApiError) -> List[str]:
        """Suggest specific code fixes based on error analysis."""
        fixes = []
        
        # Common error patterns and their fixes
        for err in error.errors:
            error_id = err.error_id
            message = err.message.lower()
            
            # Specific error ID mappings
            if error_id == 2004 and "serialize" in message:
                fixes.append("Check data types - ensure TimeDuration objects use {unit, value} structure")
            elif error_id in [20403, 20001] and "business policy" in message:
                fixes.append("User not eligible for Business Policies - handle as sandbox limitation")
            elif error_id == 1001 and "access token" in message:
                fixes.append("Refresh OAuth token or re-initiate user consent flow")
            elif "invalid" in message and err.input_ref_ids:
                for ref_id in err.input_ref_ids:
                    field = self._extract_field_name(ref_id)
                    fixes.append(f"Validate {field} against API documentation and enum values")
        
        return fixes
    
    def _get_escalation_path(self, error: EbayApiError) -> Optional[str]:
        """Determine escalation path for unresolvable errors."""
        if error.ebay_category == EbayErrorCategory.APPLICATION:
            return "Contact eBay Developer Support with error details and request ID"
        elif error.status_code >= 500:
            return "Report infrastructure issue to eBay Developer Support"
        else:
            return None
```

### Context-Aware Error Responses

```python
class ContextAwareErrorResponse:
    """Generate context-aware error responses for different scenarios."""
    
    def for_test_suite(self, error: EbayApiError) -> str:
        """Generate test-specific error guidance."""
        if error.ebay_category == EbayErrorCategory.BUSINESS:
            return f"Known sandbox limitation: {error.llm_guidance}"
        elif error.ebay_category == EbayErrorCategory.REQUEST:
            return f"Test data issue: {error.llm_guidance}"
        else:
            return f"Infrastructure problem: {error.llm_guidance}"
    
    def for_development(self, error: EbayApiError) -> str:
        """Generate development-focused error guidance."""
        guidance_parts = []
        guidance_parts.append(f"Development Error - {error.ebay_category.value}")
        guidance_parts.append(error.llm_guidance)
        
        # Add debugging information
        guidance_parts.append(f"\nHTTP {error.status_code}")
        if error.request_id:
            guidance_parts.append(f"Request ID: {error.request_id}")
        
        return "\n".join(guidance_parts)
    
    def for_production(self, error: EbayApiError) -> str:
        """Generate production-safe error guidance."""
        # Sanitize sensitive information for production
        safe_guidance = error.ebay_category.get_action_guidance()
        
        if error.ebay_category == EbayErrorCategory.APPLICATION:
            return f"Service temporarily unavailable. {safe_guidance}"
        else:
            return f"Request error. {safe_guidance}"
```

---

## Intelligent Retry Strategy Framework

### Category-Based Retry Policies

```python
class RetryStrategy(ABC):
    """Base class for retry strategies."""
    
    @abstractmethod
    def should_retry(self, attempt: int, error: EbayApiError) -> bool:
        pass
    
    @abstractmethod
    def get_delay(self, attempt: int, error: EbayApiError) -> float:
        pass

class NoRetryStrategy(RetryStrategy):
    """No retry strategy for non-retryable errors."""
    
    def should_retry(self, attempt: int, error: EbayApiError) -> bool:
        return False
    
    def get_delay(self, attempt: int, error: EbayApiError) -> float:
        return 0.0

class ExponentialBackoffStrategy(RetryStrategy):
    """Exponential backoff with jitter for retryable errors."""
    
    def __init__(self, max_attempts: int = 3, base_delay: float = 1.0, max_delay: float = 60.0):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
    
    def should_retry(self, attempt: int, error: EbayApiError) -> bool:
        if attempt >= self.max_attempts:
            return False
        
        # Only retry REQUEST category errors
        if error.ebay_category != EbayErrorCategory.REQUEST:
            return False
        
        # Don't retry certain non-retryable request errors
        non_retryable_codes = [400, 401, 403]  # Validation, auth errors
        if error.status_code in non_retryable_codes:
            return False
        
        return True
    
    def get_delay(self, attempt: int, error: EbayApiError) -> float:
        # Check for retry-after header
        retry_after = error.get_retry_after()
        if retry_after:
            return retry_after
        
        # Exponential backoff with jitter
        delay = self.base_delay * (2 ** attempt)
        delay = min(delay, self.max_delay)
        
        # Add jitter (±25%)
        import random
        jitter = delay * 0.25 * (random.random() - 0.5)
        return delay + jitter

class RateLimitStrategy(RetryStrategy):
    """Specialized strategy for rate limit errors."""
    
    def should_retry(self, attempt: int, error: EbayApiError) -> bool:
        return attempt < 5 and error.status_code == 429
    
    def get_delay(self, attempt: int, error: EbayApiError) -> float:
        # Use retry-after header if available
        retry_after = error.get_retry_after()
        if retry_after:
            return retry_after
        
        # Default rate limit backoff
        return min(60.0, 5.0 * (2 ** attempt))

class RetryStrategyFactory:
    """Factory for creating appropriate retry strategies."""
    
    @staticmethod
    def create_strategy(error: EbayApiError) -> RetryStrategy:
        if error.status_code == 429:
            return RateLimitStrategy()
        elif error.ebay_category == EbayErrorCategory.REQUEST:
            return ExponentialBackoffStrategy()
        else:
            return NoRetryStrategy()
```

### Circuit Breaker Pattern

```python
class CircuitBreaker:
    """Circuit breaker for protecting against repeated failures."""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 60.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    def call(self, func, *args, **kwargs):
        if self.state == "OPEN":
            if self._should_attempt_reset():
                self.state = "HALF_OPEN"
            else:
                raise CircuitBreakerOpenError("Circuit breaker is OPEN")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except EbayApiError as e:
            self._on_failure(e)
            raise
    
    def _should_attempt_reset(self) -> bool:
        return (
            self.last_failure_time and
            time.time() - self.last_failure_time >= self.recovery_timeout
        )
    
    def _on_success(self):
        self.failure_count = 0
        self.state = "CLOSED"
    
    def _on_failure(self, error: EbayApiError):
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
```

---

## Implementation Phases

### Phase 1: Enhanced Error Classification (Days 1-2)

**Objectives:**
- Implement eBay-aligned error categories
- Enhance EbayApiError class with actionable guidance
- Add warning support system

**Tasks:**
1. **Create New Error Categories**
   - Add `EbayErrorCategory` enum with three categories
   - Map existing categories to eBay categories
   - Add action guidance methods

2. **Enhance EbayApiError Class**
   - Add `_determine_ebay_category()` method
   - Add `_generate_action_guidance()` method
   - Add `_analyze_field_issues()` method
   - Add JSONPath interpretation

3. **Add Warning Support**
   - Create `EbayApiWarning` model
   - Enhance response structures to handle warnings
   - Update API tools to process warnings

**Breaking Changes:**
- New fields in `EbayApiError` class (backward compatible)
- New response structure with warnings (backward compatible)

**Testing:**
- Unit tests for new error categorization
- Integration tests with real eBay errors
- Backward compatibility tests

### Phase 2: LLM/MCP Error Guidance System (Day 3)

**Objectives:**
- Implement `EbayErrorAnalyzer` class
- Create LLM-optimized error messages
- Add context-aware error responses

**Tasks:**
1. **Create Error Analyzer**
   - Implement `EbayErrorAnalyzer` class
   - Add LLM-specific message generation
   - Add code fix suggestions

2. **Update MCP Response Patterns**
   - Enhance error responses with actionable guidance
   - Add context-aware error formatting
   - Update all API tools to use new patterns

3. **Add Error Guidance Integration**
   - Integrate analyzer into existing error handling
   - Update `data_types.py` response patterns
   - Add guidance to test suite error handling

**Breaking Changes:**
- Enhanced error response format (backward compatible)
- New fields in MCPErrorResponse (backward compatible)

**Testing:**
- LLM error message format validation
- Context-aware response testing
- Integration tests with real scenarios

### Phase 3: Intelligent Retry Strategies (Day 4)

**Objectives:**
- Implement category-based retry strategies
- Add circuit breaker pattern
- Enhance rate limiting handling

**Tasks:**
1. **Create Retry Strategy Framework**
   - Implement base `RetryStrategy` class
   - Add category-specific strategies
   - Add `RetryStrategyFactory`

2. **Implement Circuit Breaker**
   - Add `CircuitBreaker` class
   - Integrate with API clients
   - Add monitoring and observability

3. **Enhance Rest Client**
   - Update `rest_client.py` with retry logic
   - Add circuit breaker integration
   - Add retry attempt logging

**Breaking Changes:**
- Enhanced `rest_client.py` behavior (backward compatible)
- New retry configuration options

**Testing:**
- Retry strategy unit tests
- Circuit breaker integration tests
- Performance testing with retries

### Phase 4: Test Suite Integration (Day 5)

**Objectives:**
- Update test suite error handling
- Add enhanced error classification
- Improve test failure diagnostics

**Tasks:**
1. **Update Test Error Handling**
   - Use new error categories in test assertions
   - Add actionable test failure messages
   - Enhance sandbox vs production error handling

2. **Add Error Analysis to Tests**
   - Use `EbayErrorAnalyzer` in test failures
   - Add context-aware test error reporting
   - Enhance diagnostic output

3. **Update Existing Tests**
   - Review all existing error handling tests
   - Update to use new error patterns
   - Add comprehensive error scenario tests

**Breaking Changes:**
- Test assertion patterns (needs manual update)
- Test error message formats

**Testing:**
- Test suite regression testing
- Error handling scenario validation
- Backward compatibility verification

---

## Breaking Change Analysis

### Critical Breaking Changes

#### 1. **Error Response Structure Changes**

**Impact:** Low - Backward Compatible
**Affected Files:**
- `src/api/errors.py` - Enhanced fields
- `src/data_types.py` - New response fields

**Mitigation:**
- New fields are optional and default to None
- Existing error handling continues to work
- Gradual migration path for adopting new features

#### 2. **Test Suite Error Assertions**

**Impact:** Medium - Requires Manual Updates
**Affected Files:**
- All test files with error assertions
- Test helper functions

**Migration Path:**
```python
# Old pattern
assert response["error_code"] == "EXTERNAL_API_ERROR"

# New pattern (enhanced)
assert response["error_code"] == "EXTERNAL_API_ERROR"
assert response["details"]["ebay_category"] == "BUSINESS"
assert "action_guidance" in response["details"]
```

**Mitigation:**
- Existing assertions continue to work
- New assertions optional but recommended
- Gradual migration over time

#### 3. **API Tool Error Handling Patterns**

**Impact:** Low - Backward Compatible
**Affected Files:**
- All API tool files (return_policy_api.py, etc.)

**Migration Path:**
```python
# Old pattern (still works)
except EbayApiError as e:
    return error_response(
        ErrorCode.EXTERNAL_API_ERROR,
        str(e)
    ).to_json_string()

# Enhanced pattern (recommended)
except EbayApiError as e:
    return error_response(
        ErrorCode.EXTERNAL_API_ERROR,
        e.get_comprehensive_message(),
        e.get_full_error_details()
    ).to_json_string()
```

**Mitigation:**
- Existing patterns continue to work
- Enhanced patterns provide better error information
- Can be updated incrementally

### Configuration Changes

#### 1. **New Configuration Options**

```python
# Optional retry configuration
EBAY_RETRY_MAX_ATTEMPTS = 3
EBAY_RETRY_BASE_DELAY = 1.0
EBAY_CIRCUIT_BREAKER_THRESHOLD = 5
EBAY_CIRCUIT_BREAKER_TIMEOUT = 60.0
```

**Impact:** None - All optional with sensible defaults

#### 2. **Logging Enhancements**

```python
# Enhanced error logging format
logger.error(
    "eBay API Error",
    extra={
        "error_category": error.ebay_category.value,
        "error_id": error.errors[0].error_id if error.errors else None,
        "action_guidance": error.action_guidance,
        "retryable": error.ebay_category.is_retryable()
    }
)
```

**Impact:** Low - Enhanced logging information

### Rollback Strategy

#### 1. **Feature Flags**
- Add feature flags for new error handling features
- Allow gradual rollout and quick rollback if needed

#### 2. **Fallback Mechanisms**
- Existing error handling remains as fallback
- New features enhance rather than replace

#### 3. **Monitoring**
- Add metrics for new error handling features
- Monitor error categorization accuracy
- Track retry strategy effectiveness

---

## Code Implementation Details

### Core Classes and Interfaces

#### 1. **Enhanced Error Classification**

```python
# src/api/errors.py additions

class ErrorActionGuidance(BaseModel):
    """Structured action guidance for errors."""
    category: EbayErrorCategory
    severity: ErrorSeverity
    action_required: str
    specific_steps: List[str]
    code_fixes: List[str]
    retry_guidance: str
    escalation_path: Optional[str]

class EbayApiError(EbayApiException):
    """Enhanced with eBay-specific guidance."""
    
    @property
    def ebay_category(self) -> EbayErrorCategory:
        """Get eBay error category."""
        return self._ebay_category
    
    @property
    def action_guidance(self) -> ErrorActionGuidance:
        """Get structured action guidance."""
        return self._action_guidance
    
    @property
    def llm_guidance(self) -> str:
        """Get LLM-optimized guidance."""
        return self._llm_guidance
    
    def get_field_issues(self) -> Dict[str, str]:
        """Get field-specific issues and solutions."""
        return self._field_issues
```

#### 2. **Retry Strategy Integration**

```python
# src/api/rest_client.py enhancements

class EbayRestClient:
    """Enhanced with intelligent retry strategies."""
    
    def __init__(self, oauth_manager, config, retry_config=None):
        self.oauth_manager = oauth_manager
        self.config = config
        self.retry_config = retry_config or RetryConfig()
        self.circuit_breaker = CircuitBreaker()
    
    async def _execute_with_retry(self, method, url, **kwargs):
        """Execute request with intelligent retry logic."""
        strategy = None
        
        for attempt in range(self.retry_config.max_attempts):
            try:
                return await self.circuit_breaker.call(
                    self._execute_request, method, url, **kwargs
                )
            except EbayApiError as e:
                if strategy is None:
                    strategy = RetryStrategyFactory.create_strategy(e)
                
                if not strategy.should_retry(attempt, e):
                    raise
                
                delay = strategy.get_delay(attempt, e)
                await asyncio.sleep(delay)
                
                # Log retry attempt
                logger.info(
                    f"Retrying eBay API call (attempt {attempt + 1})",
                    extra={
                        "url": url,
                        "error_category": e.ebay_category.value,
                        "delay": delay
                    }
                )
        
        # If we get here, all retries failed
        raise EbayApiError(...)
```

#### 3. **Enhanced MCP Response Format**

```python
# src/data_types.py enhancements

class EnhancedMCPErrorResponse(MCPErrorResponse):
    """Enhanced error response with eBay-specific guidance."""
    
    error_category: Optional[str] = None
    action_guidance: Optional[str] = None
    field_issues: Optional[Dict[str, str]] = None
    retry_guidance: Optional[str] = None
    escalation_path: Optional[str] = None
    
    @classmethod
    def from_ebay_error(cls, error: EbayApiError) -> "EnhancedMCPErrorResponse":
        """Create enhanced response from eBay error."""
        return cls(
            error_code=ErrorCode.EXTERNAL_API_ERROR,
            error_message=error.get_comprehensive_message(),
            error_category=error.ebay_category.value,
            action_guidance=error.action_guidance.action_required,
            field_issues=error.get_field_issues(),
            retry_guidance=error.action_guidance.retry_guidance,
            escalation_path=error.action_guidance.escalation_path,
            details=error.get_full_error_details()
        )
```

### Performance Considerations

#### 1. **Error Analysis Caching**
- Cache error analysis results for common error patterns
- Avoid recomputing guidance for identical errors

#### 2. **Retry Strategy Optimization**
- Implement adaptive retry strategies based on success rates
- Monitor and tune retry parameters based on performance metrics

#### 3. **Circuit Breaker Efficiency**
- Use lightweight state tracking
- Implement efficient failure rate calculations

### Monitoring and Observability

#### 1. **Error Metrics**
```python
# Error category distribution
error_category_counter = Counter(["APPLICATION", "BUSINESS", "REQUEST"])

# Retry success rates
retry_success_rate = Histogram("retry_success_rate")

# Circuit breaker state changes
circuit_breaker_state = Gauge("circuit_breaker_state")
```

#### 2. **Structured Logging**
```python
logger.error(
    "eBay API Error",
    extra={
        "error_category": error.ebay_category.value,
        "error_id": error.errors[0].error_id,
        "retryable": error.ebay_category.is_retryable(),
        "field_issues": len(error.get_field_issues()),
        "guidance_provided": bool(error.action_guidance)
    }
)
```

#### 3. **Health Checks**
- Monitor error categorization accuracy
- Track guidance effectiveness
- Alert on high error rates by category

---

## Testing Strategy

### Unit Testing Requirements

#### 1. **Error Classification Tests**
```python
def test_ebay_error_categorization():
    """Test eBay error category determination."""
    # APPLICATION error
    error = EbayApiError(500, {"errors": [{"category": "APPLICATION"}]})
    assert error.ebay_category == EbayErrorCategory.APPLICATION
    assert not error.ebay_category.is_retryable()
    
    # BUSINESS error
    error = EbayApiError(400, {"errors": [{"category": "BUSINESS"}]})
    assert error.ebay_category == EbayErrorCategory.BUSINESS
    assert not error.ebay_category.is_retryable()
    
    # REQUEST error
    error = EbayApiError(401, {"errors": [{"category": "REQUEST"}]})
    assert error.ebay_category == EbayErrorCategory.REQUEST
    assert error.ebay_category.is_retryable()
```

#### 2. **Action Guidance Tests**
```python
def test_action_guidance_generation():
    """Test action guidance generation."""
    error = create_test_error_with_field_issues()
    
    guidance = error.action_guidance
    assert guidance.category == EbayErrorCategory.BUSINESS
    assert "business rule" in guidance.action_required.lower()
    assert len(guidance.specific_steps) > 0
    assert len(guidance.code_fixes) > 0
```

#### 3. **Retry Strategy Tests**
```python
def test_retry_strategies():
    """Test retry strategy selection and behavior."""
    # APPLICATION error - no retry
    error = create_application_error()
    strategy = RetryStrategyFactory.create_strategy(error)
    assert isinstance(strategy, NoRetryStrategy)
    assert not strategy.should_retry(0, error)
    
    # REQUEST error - exponential backoff
    error = create_request_error()
    strategy = RetryStrategyFactory.create_strategy(error)
    assert isinstance(strategy, ExponentialBackoffStrategy)
    assert strategy.should_retry(0, error)
```

### Integration Testing Requirements

#### 1. **Real eBay Error Handling**
```python
@pytest.mark.integration
async def test_real_ebay_error_handling():
    """Test error handling with real eBay API responses."""
    # Create invalid request that will generate known error
    invalid_policy = create_invalid_policy_data()
    
    with pytest.raises(EbayApiError) as exc_info:
        await create_return_policy.fn(ctx=context, policy_input=invalid_policy)
    
    error = exc_info.value
    assert error.ebay_category in [EbayErrorCategory.BUSINESS, EbayErrorCategory.REQUEST]
    assert error.action_guidance is not None
    assert len(error.llm_guidance) > 0
```

#### 2. **Warning Processing Tests**
```python
@pytest.mark.integration
async def test_warning_processing():
    """Test processing API responses with warnings."""
    # Create request that generates warnings but succeeds
    result = await create_policy_with_warnings(context, policy_input)
    response = json.loads(result)
    
    assert response["status"] == "success"
    assert "warnings" in response
    assert len(response["warnings"]) > 0
```

### Performance Testing

#### 1. **Retry Strategy Performance**
- Test retry delays under various scenarios
- Verify circuit breaker behavior under load
- Measure error analysis overhead

#### 2. **Memory Usage**
- Test error object memory footprint
- Verify no memory leaks in retry logic
- Monitor cache performance

---

## Success Metrics

### Quantitative Metrics

1. **Error Resolution Time**
   - Target: 50% reduction in time to resolve eBay API errors
   - Measurement: Time from error occurrence to successful retry or fix

2. **LLM Problem-Solving Success Rate**
   - Target: 80% of errors resolved autonomously by LLM
   - Measurement: Percentage of errors that LLM can fix without human intervention

3. **Test Suite Diagnostic Quality**
   - Target: 90% of test failures provide actionable guidance
   - Measurement: Manual review of test failure messages

4. **Retry Strategy Effectiveness**
   - Target: 70% success rate for retryable errors
   - Measurement: Successful retries / total retry attempts

### Qualitative Metrics

1. **Developer Experience**
   - Clear, actionable error messages
   - Reduced debugging time
   - Faster problem resolution

2. **Code Maintenance**
   - Reduced error handling complexity
   - Standardized error patterns
   - Better error documentation

3. **Production Reliability**
   - Fewer manual interventions
   - Better error recovery
   - Improved system resilience

---

## Conclusion

This Enhanced eBay Error Handling Framework addresses the critical gap in our current error handling by implementing eBay's official guidance and providing intelligent, actionable error analysis. The framework transforms our approach from basic exception capture to a sophisticated system that guides developers, LLMs, and automated systems toward solutions.

### Key Benefits:

1. **Prevents Bug Masking**: Like the deposit.dueIn issue, this framework prevents hiding real bugs
2. **Enables Autonomous Problem-Solving**: LLMs receive actionable guidance for self-correction
3. **Improves Developer Productivity**: Clear error classification and retry strategies
4. **Enhances System Reliability**: Intelligent retry logic and circuit breaker protection

### Implementation Commitment:

- **5-day implementation timeline**
- **Backward compatibility maintained**
- **Gradual migration path**
- **Comprehensive testing strategy**

This framework establishes the foundation for robust, intelligent error handling that scales with our eBay API integration and serves as a model for other external API integrations.