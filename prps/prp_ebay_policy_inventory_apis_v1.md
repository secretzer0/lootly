# Project Requirements Plan: eBay Policy and Inventory APIs Implementation
**Version**: 1.0  
**Date**: 2025-01-16  
**Author**: Claude  
**Status**: Draft  

## Executive Summary

This PRP outlines a phased implementation approach for adding 4 new eBay APIs to the Lootly MCP server:
- Fulfillment Policy API (shipping/delivery management)
- Payment Policy API (payment method management)
- Return Policy API (return handling management)
- Inventory Item API (product inventory management)

Additionally, a comprehensive enum file will be created to provide strongly-typed parameters across all APIs.

### Key Benefits of Phased Approach:
1. **Risk Mitigation**: Implement and test incrementally
2. **Pattern Validation**: Establish patterns with simpler APIs first
3. **Early Feedback**: Discover API quirks before complex implementations
4. **Maintainability**: Each phase builds on proven patterns

## Documentation Reference

All implementation will be based on the following eBay API documentation:

### Fulfillment Policy API:
- **Overview**: https://developer.ebay.com/api-docs/sell/account/resources/methods#s0-1-30-4-7-5-6-2[1]-h2-fulfillment_policy
- **Endpoints**:
  - create_fulfillment_policy: https://developer.ebay.com/api-docs/sell/account/resources/fulfillment_policy/methods/createFulfillmentPolicy
  - delete_fulfillment_policy: https://developer.ebay.com/api-docs/sell/account/resources/fulfillment_policy/methods/deleteFulfillmentPolicy
  - get_fulfillment_policies: https://developer.ebay.com/api-docs/sell/account/resources/fulfillment_policy/methods/getFulfillmentPolicies
  - get_fulfillment_policy: https://developer.ebay.com/api-docs/sell/account/resources/fulfillment_policy/methods/getFulfillmentPolicy
  - get_fulfillment_policy_by_name: https://developer.ebay.com/api-docs/sell/account/resources/fulfillment_policy/methods/getFulfillmentPolicyByName
  - update_fulfillment_policy: https://developer.ebay.com/api-docs/sell/account/resources/fulfillment_policy/methods/updateFulfillmentPolicy

### Payment Policy API:
- **Overview**: https://developer.ebay.com/api-docs/sell/account/resources/methods#s0-1-30-4-7-5-6-2[2]-h2-payment_policy
- **Endpoints**:
  - create_payment_policy: https://developer.ebay.com/api-docs/sell/account/resources/payment_policy/methods/createPaymentPolicy
  - delete_payment_policy: https://developer.ebay.com/api-docs/sell/account/resources/payment_policy/methods/deletePaymentPolicy
  - get_payment_policies: https://developer.ebay.com/api-docs/sell/account/resources/payment_policy/methods/getPaymentPolicies
  - get_payment_policy: https://developer.ebay.com/api-docs/sell/account/resources/payment_policy/methods/getPaymentPolicy
  - get_payment_policy_by_name: https://developer.ebay.com/api-docs/sell/account/resources/payment_policy/methods/getPaymentPolicyByName
  - update_payment_policy: https://developer.ebay.com/api-docs/sell/account/resources/payment_policy/methods/updatePaymentPolicy

### Return Policy API:
- **Overview**: https://developer.ebay.com/api-docs/sell/account/resources/methods#s0-1-30-4-7-5-6-2[7]-h2-return_policy
- **Endpoints**:
  - create_return_policy: https://developer.ebay.com/api-docs/sell/account/resources/return_policy/methods/createReturnPolicy
  - delete_return_policy: https://developer.ebay.com/api-docs/sell/account/resources/return_policy/methods/deleteReturnPolicy
  - get_return_policies: https://developer.ebay.com/api-docs/sell/account/resources/return_policy/methods/getReturnPolicies
  - get_return_policy: https://developer.ebay.com/api-docs/sell/account/resources/return_policy/methods/getReturnPolicy
  - get_return_policy_by_name: https://developer.ebay.com/api-docs/sell/account/resources/return_policy/methods/getReturnPolicyByName
  - update_return_policy: https://developer.ebay.com/api-docs/sell/account/resources/return_policy/methods/updateReturnPolicy

### Inventory Item API:
- **Overview**: https://developer.ebay.com/api-docs/sell/inventory/resources/methods
- **Endpoints**:
  - bulk_create_or_replace_inventory_item: https://developer.ebay.com/api-docs/sell/inventory/resources/inventory_item/methods/bulkCreateOrReplaceInventoryItem
  - bulk_get_inventory_item: https://developer.ebay.com/api-docs/sell/inventory/resources/inventory_item/methods/bulkGetInventoryItem
  - bulk_update_price_quantity: https://developer.ebay.com/api-docs/sell/inventory/resources/inventory_item/methods/bulkUpdatePriceQuantity
  - add_inventory_item: https://developer.ebay.com/api-docs/sell/inventory/resources/inventory_item/methods/createOrReplaceInventoryItem
  - delete_inventory_item: https://developer.ebay.com/api-docs/sell/inventory/resources/inventory_item/methods/deleteInventoryItem
  - get_inventory_item: https://developer.ebay.com/api-docs/sell/inventory/resources/inventory_item/methods/getInventoryItem
  - get_inventory_items: https://developer.ebay.com/api-docs/sell/inventory/resources/inventory_item/methods/getInventoryItems

### Enum Documentation:
- AvailabilityTypeEnum: https://developer.ebay.com/api-docs/sell/inventory/types/slr:AvailabilityTypeEnum
- CategoryTypeEnum: https://developer.ebay.com/api-docs/sell/account/types/api:CategoryTypeEnum
- ConditionEnum: https://developer.ebay.com/api-docs/sell/inventory/types/slr:ConditionEnum
- CurrencyCodeEnum: https://developer.ebay.com/api-docs/sell/account/types/ba:CurrencyCodeEnum
- LocaleEnum: https://developer.ebay.com/api-docs/sell/inventory/types/slr:LocaleEnum
- LengthUnitOfMeasureEnum: https://developer.ebay.com/api-docs/sell/inventory/types/slr:LengthUnitOfMeasureEnum
- MarketplaceIdEnum: https://developer.ebay.com/api-docs/sell/account/types/ba:MarketplaceIdEnum
- PackageTypeEnum: https://developer.ebay.com/api-docs/sell/inventory/types/slr:PackageTypeEnum
- PaymentInstrumentBrandEnum: https://developer.ebay.com/api-docs/sell/account/types/api:PaymentInstrumentBrandEnum
- PaymentMethodTypeEnum: https://developer.ebay.com/api-docs/sell/account/types/api:PaymentMethodTypeEnum
- RecipientAccountReferenceTypeEnum: https://developer.ebay.com/api-docs/sell/account/types/api:RecipientAccountReferenceTypeEnum
- RefundMethodEnum: https://developer.ebay.com/api-docs/sell/account/types/api:RefundMethodEnum
- ReturnMethodEnum: https://developer.ebay.com/api-docs/sell/account/types/api:ReturnMethodEnum
- ReturnShippingCostPayerEnum: https://developer.ebay.com/api-docs/sell/account/types/api:ReturnShippingCostPayerEnum
- RegionTypeEnum: https://developer.ebay.com/api-docs/sell/account/types/ba:RegionTypeEnum
- ShippingCostTypeEnum: https://developer.ebay.com/api-docs/sell/account/types/api:ShippingCostTypeEnum
- ShippingOptionTypeEnum: https://developer.ebay.com/api-docs/sell/account/types/api:ShippingOptionTypeEnum
- TimeDurationUnitEnum: https://developer.ebay.com/api-docs/sell/inventory/types/slr:TimeDurationUnitEnum
- WeightUnitOfMeasureEnum: https://developer.ebay.com/api-docs/sell/inventory/types/slr:WeightUnitOfMeasureEnum

---

## CRITICAL IMPLEMENTATION REQUIREMENTS

**MANDATORY READING**: When implementing ANY endpoint, you MUST follow these requirements exactly:

### 1. THOROUGHLY READ the Endpoint Documentation

- Navigate to the EXACT endpoint URL provided in this PRP
- Study the Request Payload JSON structure 
- Read EVERY field in the Request Fields section
- Note which fields are arrays vs single values

### 2. VERIFY OAuth Scope Requirements

**MANDATORY STEP**: Every eBay API endpoint documentation contains an "OAuth Scope" section that specifies the exact OAuth scope required.

**OAuth Scope Validation Process:**
1. **Find "OAuth Scope" section** in the endpoint documentation
2. **Note the exact scope string** (e.g., `https://api.ebay.com/oauth/api_scope/sell.account`)
3. **Verify scope exists in `src/api/oauth.py`** under `OAuthScopes` class
4. **Use correct scope constant** in your implementation
5. **Document authentication type** for testing expectations

**Example OAuth Scopes:**
- `api_scope` (basic) → App-only authentication (Taxonomy, Browse)
- `sell.account` → User consent required (Return Policy, Payment Policy)
- `sell.fulfillment` → User consent required (Fulfillment Policy)
- `sell.inventory` → User consent required (Inventory APIs)

### 3. PAY SPECIAL ATTENTION to Request Fields Section

The Request Fields section lists EVERY field name with its type next to it. This is your source of truth for implementation.

### 4. CRITICAL GOTCHA: OAuth Scope Usage in REST Client

**IMPORTANT**: When making REST API calls with the EbayRestClient, DO NOT pass a `scope` parameter to the client methods when using user tokens:

**WRONG Pattern** ❌:
```python
# DO NOT do this when user tokens are present
response = await rest_client.get(
    "/sell/account/v1/return_policy",
    params=params,
    scope=OAuthScopes.SELL_ACCOUNT  # WRONG - don't pass scope with user tokens
)
```

**CORRECT Pattern** ✅:
```python
# The correct pattern - no scope parameter needed
response = await rest_client.get(
    "/sell/account/v1/return_policy",
    params=params
)
```

**Why this matters**:
- When using OAuth user tokens (obtained via user consent flow), the token already contains the granted scopes
- The `scope` parameter in rest_client is ONLY used for client credentials flow (app-only auth)
- Passing a scope when user tokens are present is meaningless and may cause confusion
- The rest_client automatically uses the user token when available (see rest_client.py line 167-172)

**Implementation Checklist**:
- [ ] Check if API requires user consent (sell.account, sell.inventory, etc.)
- [ ] If yes, obtain user token via OAuth consent flow
- [ ] Pass user token to OAuthConfig during client initialization
- [ ] DO NOT pass scope parameter to rest_client methods
- [ ] Let the client handle token selection automatically

### 4a. CORRECT OAuth Initialization Pattern

**MANDATORY**: When initializing OAuth and REST clients in ALL API implementations, use this exact pattern:

```python
# Initialize API clients
oauth_config = OAuthConfig(
    client_id=mcp.config.app_id,
    client_secret=mcp.config.cert_id,
    sandbox=mcp.config.sandbox_mode
)
oauth_manager = OAuthManager(oauth_config)

rest_config = RestConfig(
    sandbox=mcp.config.sandbox_mode,
    rate_limit_per_day=mcp.config.rate_limit_per_day
)
rest_client = EbayRestClient(oauth_manager, rest_config)
```

**DO NOT**:
- Add `or ""` fallback for cert_id
- Include extra parameters like `timeout` or `max_retries` in RestConfig
- Pass any scope parameter to rest_client method calls

**ALWAYS**:
- Use exactly the pattern shown above
- Close the rest_client in a finally block: `await rest_client.close()`
- Let the OAuth manager handle token selection automatically

### 5. Field Mapping Process

Example from createReturnPolicy:
```
Field Name                    Type
--------------------------------------------
returnShippingCostPayer      ReturnShippingCostPayerEnum
marketplaceId                MarketplaceIdEnum  
name                         string
value                        integer
description                  string
categoryTypes                array of CategoryType
```

**CRITICAL**: The type column tells you EXACTLY which Python type to use!

### 4. Complete Type Mapping Rules

**eBay API Type → Python Type Mapping:**
```
string                → str
integer               → int
number                → float
decimal               → Decimal (from decimal import Decimal)
boolean               → bool
array of X            → List[X]
XEnum (any enum)      → XEnum (from ebay_enums.py)
ComplexType           → ComplexType (Pydantic model)
```

**Examples:**
```
Request Fields Type:              Python Parameter:
string                         → param: str
integer                        → param: int
decimal                        → param: Decimal
boolean                        → param: bool
MarketplaceIdEnum             → marketplace_id: MarketplaceIdEnum
array of CategoryType         → category_types: List[CategoryType]
TimeDuration                  → time_duration: TimeDuration
```

### 5. Field Mapping Process

1. Find field name in Request Fields (e.g., `returnShippingCostPayer`)
2. Look at the Type column (e.g., `ReturnShippingCostPayerEnum`)
3. Map to Python parameter:
   - API field: `returnShippingCostPayer` (Type: `ReturnShippingCostPayerEnum`)
   - Python param: `return_shipping_cost_payer: ReturnShippingCostPayerEnum`
4. Add `Optional[]` wrapper if field is optional
5. NEVER use generic types - be specific!

### 6. Use Strongly-Typed Parameters ALWAYS

- NEVER use `Any` or untyped parameters
- NEVER use `str` when Request Fields shows an enum type
- ALWAYS use the exact type shown in Request Fields
- For money/price fields showing `decimal`, use `Decimal` not `float`
- This allows MCP/LLM to see all valid values automatically

### 7. Include ALL Fields from Request Fields Section

- Go through EVERY row in the Request Fields table
- Every field MUST appear in your function signature
- Required fields as required parameters
- Optional fields with `Optional[Type] = None`
- DO NOT skip any fields!

### 8. Common Type Patterns

```python
# Primitive types
name: str                                    # for "string"
limit: int                                   # for "integer"
percentage: float                            # for "number"
price: Decimal                               # for "decimal"
is_active: bool                              # for "boolean"

# Enum types (NEVER use str!)
marketplace_id: MarketplaceIdEnum            # for "MarketplaceIdEnum"
return_shipping_cost_payer: ReturnShippingCostPayerEnum  # for "ReturnShippingCostPayerEnum"

# Complex types
return_period: TimeDuration                  # for "TimeDuration"

# Arrays
category_types: List[CategoryType]           # for "array of CategoryType"
tags: List[str]                             # for "array of string"
```

### 9. Remove ALL String Validation

When using enum types, DELETE code like:
```python
# DELETE THIS - enums provide their own validation:
if not validate_enum_value(MarketplaceIdEnum, marketplace_id):
    raise ValueError(...)
```

The type system handles validation automatically.

### 10. Pydantic Models Are The Source of Truth

- Create Pydantic models BEFORE writing MCP tools
- Every API structure needs a corresponding Pydantic model
- Use Pydantic models in function signatures when possible
- For complex inputs, pass the Pydantic model directly

### 11. Validation Errors Are Documentation

When Pydantic validation fails, it provides:
- Exact field that failed
- Why it failed
- For enums: ALL valid values
- For conditionals: Clear messages

Example error:
```
marketplace_id
  Input should be 'EBAY_US', 'EBAY_CA', 'EBAY_MX'... [type=enum]
```

The LLM sees all valid options and can self-correct!

---

## PYDANTIC-FIRST DEVELOPMENT METHODOLOGY

**FUNDAMENTAL PRINCIPLE**: Pydantic models ARE your validation, documentation, and type safety. 

### The Pydantic-First Workflow:

1. **API Documentation → Pydantic Models → MCP Tools**
   - Read API docs to understand structure
   - Create Pydantic models that mirror the API exactly
   - MCP tool parameters use these Pydantic types directly
   - Validation errors become self-documenting

2. **Validation Philosophy**:
   - **NEVER write manual validation code**
   - **NEVER use string validation with enum checks**
   - Let Pydantic handle ALL validation
   - Trust validation errors - they contain the solution

3. **Benefits for LLMs**:
   ```python
   # BAD - Manual validation
   if marketplace_id not in ["EBAY_US", "EBAY_GB", ...]:
       raise ValueError("Invalid marketplace")
   
   # GOOD - Pydantic with enums
   marketplace_id: MarketplaceIdEnum  # Validation automatic!
   # Error shows ALL valid values: 'EBAY_US', 'EBAY_CA', 'EBAY_MX'...
   ```

### Pydantic Model Structure Pattern:

```python
# 1. Define nested structures first
class CategoryType(BaseModel):
    name: CategoryTypeEnum
    default: bool = False

class TimeDuration(BaseModel):
    value: int = Field(..., gt=0, le=365)
    unit: TimeDurationUnitEnum

# 2. Define main input model with ALL fields from API docs
class PolicyInput(BaseModel):
    # Required fields
    name: str = Field(..., max_length=64)
    marketplace_id: MarketplaceIdEnum
    
    # Conditional validation
    @model_validator(mode='after')
    def validate_conditional(self):
        if self.some_condition:
            if not self.required_field:
                raise ValueError("Clear message for LLM")
        return self
```

### Testing with Pydantic:

```python
def test_policy_validation():
    # Test data
    data = {...}
    
    try:
        policy = PolicyInput(**data)
        # If we get here, data is valid!
    except ValidationError as e:
        # Error tells us EXACTLY what's wrong
        # AND shows valid options for enums
        print(e)  # LLM can parse and fix
```

---

## WORKFLOW AND APPROVAL PROCESS

### 1. Enhanced Implementation Phase

#### Before Writing Any API Code:
- **Identify OAuth scope requirements** from eBay API documentation
- **Determine if API requires user consent** or app-only auth
- **Plan test strategy** based on scope type (infrastructure validation vs direct testing)

#### Implementation Order:
1. **Write Pydantic models first** with comprehensive validation
2. **Write unit tests** with complete mocking
3. **Write infrastructure validation test** (if API requires user consent)
4. **Write OAuth scope enforcement test** (for restricted APIs)
5. **Write main API functionality tests** with proper error classification

#### OAuth Scope Validation (MANDATORY)
**For EVERY endpoint implementation, you MUST:**

1. **Navigate to the endpoint documentation** (e.g., createReturnPolicy)
2. **Find the "OAuth Scope" section** in the eBay API documentation
3. **Note the exact scope string** (e.g., `https://api.ebay.com/oauth/api_scope/sell.account`)
4. **Validate the scope exists in `src/api/oauth.py`** under `OAuthScopes` class
5. **Use the correct scope constant** in your API implementation
6. **Plan appropriate test strategy** based on scope type

**OAuth Scope Validation Checklist:**
- [ ] Located "OAuth Scope" section in eBay endpoint documentation
- [ ] Identified exact scope string required
- [ ] Verified scope exists in `src/api/oauth.py` as a constant
- [ ] Used correct `OAuthScopes.CONSTANT` in implementation
- [ ] Planned test strategy (direct testing vs infrastructure validation)

**Integration Test Strategy by Scope Type:**

**App-Only Scopes** (basic `api_scope`):
- Examples: Taxonomy, Browse APIs
- Integration tests should **SUCCEED** with real data validation
- Use for infrastructure validation tests
- Timing: 2-5 seconds

**User Consent Scopes** (`sell.account`, `sell.fulfillment`, etc.):
- Examples: Account, Inventory, Fulfillment APIs
- Integration tests should **FAIL with auth error** (expected behavior)
- MUST be preceded by infrastructure validation test
- Timing: <1 second (fast failure)

### 2. Review Phase
- Present completed work
- Wait for user approval
- DO NOT mark tasks complete until approved

### 3. Completion Phase
- Only after explicit user approval: "the work you have done is good"
- Update todo lists to mark phase complete
- Update PRP task lists to show completion status
- Proceed to next phase

---

## Phase 1: Foundation - Shared Enums File
**Duration**: 1 day  
**Priority**: Critical (blocks all other phases)

### Objectives:
1. Create comprehensive enum file with all 19 enum types
2. Establish pattern for enum implementation
3. Provide type safety foundation for all APIs

### Implementation Tasks:
1. Create `src/api/ebay_enums.py`
2. Implement all 19 enum classes with proper values and descriptions
3. Add helper methods for validation and conversion
4. Create unit tests for enum functionality

### Required Documentation for Phase 1:
**ULTRATHINK Required**: Read each enum documentation page completely to understand:
- All possible values for each enum
- Description/meaning of each value
- Usage context in the APIs

Key enums to implement:
- **CategoryTypeEnum** (https://developer.ebay.com/api-docs/sell/account/types/api:CategoryTypeEnum)
  - MOTORS_VEHICLES
  - ALL_EXCLUDING_MOTORS_VEHICLES
  
- **MarketplaceIdEnum** (https://developer.ebay.com/api-docs/sell/account/types/ba:MarketplaceIdEnum)
  - All marketplace IDs (EBAY_US, EBAY_GB, EBAY_DE, etc.)
  
- **CurrencyCodeEnum** (https://developer.ebay.com/api-docs/sell/account/types/ba:CurrencyCodeEnum)
  - All ISO 4217 currency codes
  
- **ConditionEnum** (https://developer.ebay.com/api-docs/sell/inventory/types/slr:ConditionEnum)
  - NEW, LIKE_NEW, NEW_OTHER, NEW_WITH_DEFECTS, etc.

### Pydantic Model Requirements:

1. Base enum class with validation helpers
2. All 19 enum types with proper values
3. Descriptions for common values
4. Type-safe conversion methods
5. Integration with Pydantic validation

### Success Criteria:
- [x] All 19 enum classes implemented
- [x] Each enum has proper value/description mappings
- [x] Helper methods for string/enum conversion
- [x] 100% unit test coverage
- [x] Type hints working correctly in IDE
- [x] Pydantic models validate using these enums
- [x] Zero manual validation code

**Status**:  IN PROGRESS

### Sample Implementation Pattern:
```python
from enum import Enum
from typing import Optional, Dict, List

class CategoryTypeEnum(Enum):
    """eBay category type enumeration."""
    MOTORS_VEHICLES = "MOTORS_VEHICLES"
    ALL_EXCLUDING_MOTORS_VEHICLES = "ALL_EXCLUDING_MOTORS_VEHICLES"
    
    @classmethod
    def get_description(cls, value: str) -> Optional[str]:
        """Get human-readable description for enum value."""
        descriptions = {
            "MOTORS_VEHICLES": "Business policy applies to motor vehicle listings",
            "ALL_EXCLUDING_MOTORS_VEHICLES": "Business policy applies to all listings except motor vehicles"
        }
        return descriptions.get(value)
```

---

## Phase 2: Return Policy API - Simplest Implementation
**Duration**: 2 days  
**Priority**: High (establishes patterns)

### Objectives:
1. Implement the simplest policy API first
2. Establish patterns for policy CRUD operations
3. Validate OAuth integration with Account API
4. Set testing patterns for remaining APIs

### Required Documentation for Phase 2:
**ULTRATHINK Required**: Deep dive into return policy structure:
- **Return Policy Overview** (https://developer.ebay.com/api-docs/sell/account/resources/methods#s0-1-30-4-7-5-6-2[7]-h2-return_policy)
- **Create endpoint** (https://developer.ebay.com/api-docs/sell/account/resources/return_policy/methods/createReturnPolicy)
  - Understand conditional requirements: if `returnsAccepted` is true, then `returnPeriod` and `returnShippingCostPayer` are required
  - Note the `internationalOverride` option for different international policies

### Implementation Tasks:
1. Create `src/tools/return_policy_api.py`
2. Implement all 6 endpoints with proper Pydantic models
3. Handle conditional field validation
4. Add comprehensive docstrings for MCP
5. Create test file with unit/integration tests

### Field Mapping Requirements:
**IMPORTANT**: Follow the CRITICAL IMPLEMENTATION REQUIREMENTS section above to properly map fields.
Navigate to the createReturnPolicy documentation linked above and study the Request Fields section to identify ALL fields with their correct types.

### Pydantic Model Requirements:

1. Create `ReturnPolicyInput` model with ALL fields from API docs
2. Create nested models: `CategoryType`, `TimeDuration`, `InternationalOverride`
3. Use enums for ALL enumerated fields (marketplace, payer, method, etc.)
4. Add conditional validation using @model_validator
5. Test the models with valid/invalid data before writing MCP tools

Example structure:
```python
class ReturnPolicyInput(BaseModel):
    name: str = Field(..., max_length=64)
    marketplace_id: MarketplaceIdEnum
    category_types: List[CategoryType]
    returns_accepted: bool
    # ... all other fields with proper types
    
    @model_validator(mode='after')
    def validate_conditional(self):
        if self.returns_accepted and not self.return_period:
            raise ValueError("return_period is required when returns_accepted is true")
        return self
```

### Success Criteria:
- [x] All 6 endpoints designed (2 implemented, 4 remaining)
- [x] Conditional validation working correctly
- [x] OAuth integration validated
- [x] Pydantic models created for ALL API structures
- [x] All enums properly typed (no string validation)
- [x] Conditional validation in Pydantic models
- [x] Tests validate using Pydantic models only
- [x] MCP tools use Pydantic types in signatures
- [x] Zero manual validation code
- [x] Integration tests calling real sandbox API with diagnostic methodology
- [x] Pattern established for remaining policy APIs
- [x] Enhanced testing methodology implemented and documented

**Status**: 🟡 **PARTIALLY COMPLETED** - Testing methodology complete, 4 endpoints remaining

---

## Phase 3: Payment Policy API
**Duration**: 2 days  
**Priority**: High

### Objectives:
1. Build on patterns from Phase 2
2. Add payment method complexity
3. Handle motor vehicle special cases
4. Implement immediate payment options

### Required Documentation for Phase 3:
**ULTRATHINK Required**: Payment policy specifics:
- **Payment Policy Overview** (https://developer.ebay.com/api-docs/sell/account/resources/methods#s0-1-30-4-7-5-6-2[2]-h2-payment_policy)
- **Create endpoint** (https://developer.ebay.com/api-docs/sell/account/resources/payment_policy/methods/createPaymentPolicy)
  - Special handling for motor vehicle deposits
  - Offline payment methods enumeration
  - Immediate payment configuration

### Implementation Tasks:
1. Create `src/tools/payment_policy_api.py`
2. Implement all 6 endpoints
3. Handle motor vehicle special cases
4. Support offline payment methods
5. Add deposit configuration support

### Field Mapping Requirements:
**IMPORTANT**: Follow the CRITICAL IMPLEMENTATION REQUIREMENTS section above to properly map fields.
Navigate to the createPaymentPolicy documentation linked above and study the Request Fields section to identify ALL fields with their correct types.
Pay special attention to motor vehicle-specific conditional fields.

### Pydantic Model Requirements:

1. Create `PaymentPolicyInput` model with ALL fields from API docs
2. Handle motor vehicle category special logic
3. Create nested models for deposit and payment terms
4. Use enums for ALL payment-related fields
5. Complex conditional validation for category-based requirements

### Success Criteria:
- [ ] All endpoints working with sandbox
- [ ] Motor vehicle logic implemented
- [ ] Payment method validation
- [ ] Deposit handling tested
- [ ] Integration with existing patterns
- [ ] Pydantic models for ALL payment structures
- [ ] Zero manual validation code
- [ ] Tests use Pydantic validation only

---

## Phase 4: Fulfillment Policy API - Most Complex
**Duration**: 3 days  
**Priority**: Medium

### Objectives:
1. Implement most complex policy API
2. Handle shipping service configurations
3. Manage regional/international shipping
4. Support freight and local pickup options

### Required Documentation for Phase 4:
**ULTRATHINK Required**: Complex shipping structures:
- **Fulfillment Policy Overview** (https://developer.ebay.com/api-docs/sell/account/resources/methods#s0-1-30-4-7-5-6-2[1]-h2-fulfillment_policy)
- **Create endpoint** (https://developer.ebay.com/api-docs/sell/account/resources/fulfillment_policy/methods/createFulfillmentPolicy)
  - Shipping options structure (domestic vs international)
  - Cost type handling (FLAT_RATE vs CALCULATED)
  - Region sets for shipping destinations
  - Up to 4 domestic and 5 international services

### Implementation Tasks:
1. Create `src/tools/fulfillment_policy_api.py`
2. Implement complex shipping option structures
3. Handle region/location configurations
4. Support multiple shipping services
5. Add freight shipping support

### Field Mapping Requirements:
**IMPORTANT**: Follow the CRITICAL IMPLEMENTATION REQUIREMENTS section above to properly map fields.
Navigate to the createFulfillmentPolicy documentation linked above and study the Request Fields section to identify ALL fields with their correct types.

### Pydantic Model Requirements:

1. Create `FulfillmentPolicyInput` model with complex nested structures
2. Create models for: `ShippingOption`, `ShippingService`, `RegionSet`
3. Handle domestic vs international shipping logic
4. Use enums for cost types, option types, service codes
5. Validate shipping service limits (4 domestic, 5 international)

### Complex Nested Structure for Fulfillment:
```
FulfillmentPolicy
├── shippingOptions[]
│   ├── optionType (DOMESTIC/INTERNATIONAL)
│   ├── costType (FLAT_RATE/CALCULATED)
│   └── shippingServices[]
│       ├── shippingServiceCode
│       ├── shippingCost
│       ├── additionalShippingCost
│       └── shipToLocations (RegionSet)
├── localPickup (boolean)
├── freightShipping (boolean)
└── globalShipping (boolean)
```

### Success Criteria:
- [ ] Complex shipping structures working
- [ ] Region validation implemented
- [ ] Cost calculations validated
- [ ] All shipping options tested
- [ ] Edge cases handled
- [ ] Pydantic models handle nested complexity
- [ ] Validation for service limits
- [ ] Zero manual validation code

---

## Phase 5: Inventory Item API
**Duration**: 3 days  
**Priority**: Medium

### Objectives:
1. Implement inventory management endpoints
2. Handle bulk operations efficiently
3. SKU-based item management
4. Product data structure handling

### Required Documentation for Phase 5:
**ULTRATHINK Required**: Inventory complexity:
- **Inventory Overview** (https://developer.ebay.com/api-docs/sell/inventory/resources/methods)
- **Create/Replace Item** (https://developer.ebay.com/api-docs/sell/inventory/resources/inventory_item/methods/createOrReplaceInventoryItem)
  - SKU requirements and validation
  - Product structure with identifiers
  - Availability configurations
  - Bulk operation handling

### Implementation Tasks:
1. Create `src/tools/inventory_item_api.py`
2. Implement single-item CRUD operations
3. Add bulk operation endpoints
4. Handle product identifiers (UPC, EAN, ISBN)
5. Manage availability and pricing

### Field Mapping Requirements:
**IMPORTANT**: Follow the CRITICAL IMPLEMENTATION REQUIREMENTS section above to properly map fields.
Navigate to the createOrReplaceInventoryItem documentation linked above and study the Request Fields section to identify ALL fields with their correct types.

### Pydantic Model Requirements:

1. Create `InventoryItemInput` model with product structure
2. Create models for: `Product`, `Availability`, `PackageWeightAndSize`
3. Handle SKU validation and formatting
4. Use enums for condition, availability type, units
5. Validate product identifiers (UPC, EAN, ISBN formats)

### Inventory Item Structure:
```
InventoryItem
├── SKU (URI parameter)
├── availability
│   ├── shipToLocationAvailability
│   │   └── quantity
│   └── pickupAtLocationAvailability
├── condition (ConditionEnum)
├── product
│   ├── title
│   ├── description
│   ├── imageUrls[]
│   ├── aspects
│   └── identifiers (brand, mpn, upc, etc.)
└── packageWeightAndSize
```

### Bulk Operations:
- **bulk_create_or_replace**: Up to 25 items
- **bulk_get**: Up to 25 SKUs
- **bulk_update_price_quantity**: Efficient price/quantity updates

### Success Criteria:
- [ ] All 7 endpoints implemented
- [ ] SKU validation working
- [ ] Bulk operations efficient
- [ ] Product data validated
- [ ] Quantity management tested
- [ ] Pydantic models for inventory structures
- [ ] Bulk operation models validate arrays
- [ ] Zero manual validation code

---

## Phase 6: Integration and Polish
**Duration**: 2 days  
**Priority**: High

### Objectives:
1. End-to-end testing of all APIs
2. Documentation updates
3. Performance optimization
4. Error handling improvements

### Tasks:
1. Update `lootly_server.py` to register all APIs
2. Comprehensive integration testing
3. Update README with new capabilities
4. Performance testing for bulk operations
5. Error message improvements for MCP

### Final Validation:
- [ ] All APIs working in sandbox mode
- [ ] Test coverage > 80%
- [ ] Documentation complete
- [ ] MCP tool descriptions optimized
- [ ] Error handling comprehensive

---

## Risk Management

### Technical Risks:
1. **OAuth Complexity**: Mitigated by using existing oauth_consent implementation
2. **Conditional Fields**: Extensive testing and clear documentation
3. **Bulk Operations**: Start with small batches, optimize if needed
4. **API Rate Limits**: Implement proper throttling

### Mitigation Strategies:
1. Test each phase thoroughly before proceeding
2. Maintain detailed logs of API responses
3. Create rollback procedures for each phase
4. Document all discovered quirks

---

## DUAL-MODE TESTING METHODOLOGY

**FUNDAMENTAL PRINCIPLE**: Every test must support both unit mode (mocked) and integration mode (real API calls) to ensure comprehensive validation.

### Testing Architecture

#### 1. **BaseApiTest Pattern**
All test classes inherit from `BaseApiTest` which provides:
- `self.is_integration_mode` property to detect test mode
- Command-line flag `--test-mode=integration` enables real API testing
- Command-line flag `--test-mode=unit` enables only Mock unit API testing
- Automatic credential validation for integration tests
- Mock setup utilities for unit tests

#### 2. **Dual Execution Paths**
Each test method implements two complete execution paths:

**Integration Path (Real API):**
```python
if self.is_integration_mode:
    # Real API call - no mocking whatsoever
    result = await create_return_policy.fn(
        ctx=mock_context,
        policy_input=valid_policy_input
    )
    
    # Validate actual API response structure
    response = json.loads(result)
            
    if response["status"] == "error":
        error_code = response["error_code"]
        error_msg = response["error_message"]
        
        if error_code == "CONFIGURATION_ERROR":
            pytest.fail(f"CREDENTIALS PROBLEM: {error_msg} - {response}")
        elif error_code == "EXTERNAL_API_ERROR":
            pytest.fail(f"eBay API CONNECTIVITY ISSUE: {error_msg} - {response}")
        else:
            pytest.fail(f"UNEXPECTED INFRASTRUCTURE ISSUE: {error_code} - {error_msg} - {response}")

    assert response["status"] == "success"
```

**Unit Path (Mocked):**
```python
else:
    # Unit test with completely mocked dependencies
    with patch('tools.return_policy_api.EbayRestClient') as MockClient, \
         patch('tools.return_policy_api.OAuthManager') as MockOAuth, \
         patch('tools.return_policy_api.mcp.config') as MockConfig:
        
        # Setup all mocks
        mock_client = MockClient.return_value
        mock_client.post.return_value = TestData.CREATE_POLICY_RESPONSE
        MockConfig.app_id = "test_app"
        MockConfig.cert_id = "test_cert"
        
        # Test interface contracts and Pydantic validation
        result = await create_return_policy.fn(
            ctx=mock_context,
            policy_input=valid_policy_input
        )
        
        # Verify mocked response processing
        data = assert_api_response_success(result)
        mock_client.post.assert_called_once()
```

#### 3. **Integration Test Requirements**

**Real API Calls:**
- Must call actual eBay sandbox APIs
- No mocking of HTTP clients or API responses
- Use real OAuth flow with proper scope validation
- Handle graceful degradation based on OAuth scope type

**OAuth Scope-Based Integration Test Behavior:**

**App-Only APIs** (Taxonomy, Browse):
- Use basic `api_scope` - no user consent required
- Integration tests should **SUCCEED** and validate real response data
- Example: `assert data["data"]["category_tree_id"] == "0"`

**User Consent APIs** (Account, Inventory, Fulfillment):
- Use `sell.account`, `sell.fulfillment` scopes - require user authorization
- Integration tests should **FAIL with auth error** (this is CORRECT)
- Auth error proves real API attempt was made
- Example: `assert response["error_code"] == "AUTHENTICATION_ERROR"`

**Response Validation:**
```python
if self.is_integration_mode:
    # Test may succeed or fail gracefully
    response = json.loads(result)
    if response["status"] == "success":
        # Validate successful response structure
        validate_field(response["data"], "policy_id", str)
        validate_field(response["data"], "name", str)
    else:
        # If error, ensure it's a reasonable error (auth, permissions, etc.)
        assert response["status"] == "error"
        assert response["error_code"] in ["AUTHENTICATION_ERROR", "EXTERNAL_API_ERROR"]
        print("✅ Integration test structure validated (user consent required)")
```

#### 4. **Unit Test Requirements**

**Complete Mocking:**
- Mock ALL external dependencies (`EbayRestClient`, `OAuthManager`, `mcp.config`)
- Use predefined test data from `TestDataReturnPolicy`
- Never make real network calls
- Test all code paths including error conditions

**Pydantic Model Testing:**
```python
class TestPydanticModels:
    def test_valid_policy_creation(self):
        """Test complete valid policy with all fields."""
        policy = ReturnPolicyInput(
            name="Test Policy",
            marketplace_id=MarketplaceIdEnum.EBAY_US,
            category_types=[CategoryType(name=CategoryTypeEnum.ALL_EXCLUDING_MOTORS_VEHICLES)],
            returns_accepted=True,
            return_period=TimeDuration(value=30, unit=TimeDurationUnitEnum.DAY),
            return_shipping_cost_payer=ReturnShippingCostPayerEnum.BUYER
        )
        assert policy.name == "Test Policy"
        
    def test_validation_errors_show_enum_options(self):
        """Test that enum validation errors show all valid options."""
        with pytest.raises(ValidationError) as exc:
            ReturnPolicyInput(
                name="Test",
                marketplace_id="INVALID_MARKETPLACE",  # Wrong type
                category_types=[CategoryType(name=CategoryTypeEnum.ALL_EXCLUDING_MOTORS_VEHICLES)],
                returns_accepted=False
            )
        # Error should show all valid marketplace options
        error_str = str(exc.value)
        assert "EBAY_US" in error_str
        assert "EBAY_GB" in error_str
```

#### 5. **Test Class Structure Pattern**

```python
class TestReturnPolicyApi(BaseApiTest):
    """Test Return Policy API in both unit and integration modes."""
    
    @pytest.mark.asyncio
    async def test_create_return_policy_success(self, mock_context, mock_credentials):
        """Test successful policy creation."""
        # Create valid input using Pydantic model
        policy_input = ReturnPolicyInput(
            name="Test Policy",
            marketplace_id=MarketplaceIdEnum.EBAY_US,
            category_types=[CategoryType(name=CategoryTypeEnum.ALL_EXCLUDING_MOTORS_VEHICLES)],
            returns_accepted=True,
            return_period=TimeDuration(value=30, unit=TimeDurationUnitEnum.DAY),
            return_shipping_cost_payer=ReturnShippingCostPayerEnum.BUYER
        )
        
        if self.is_integration_mode:
            # Integration test - real API call
            result = await create_return_policy.fn(
                ctx=mock_context,
                policy_input=policy_input
            )
            # Handle real response...
        else:
            # Unit test - mocked dependencies
            with patch('tools.return_policy_api.EbayRestClient') as MockClient:
                # Setup mocks and test...
```

#### 6. **Benefits of Dual-Mode Testing**

**Pydantic-First Validation:**
- Same Pydantic validation works in both modes
- If Pydantic model accepts data, real API will too
- Integration tests prove models match actual API structure
- Unit tests validate all edge cases and error conditions

**Comprehensive Coverage:**
- Unit tests: Fast, reliable, test all code paths
- Integration tests: Prove real API compatibility
- Combined: Complete confidence in implementation

**Development Workflow:**
1. Create Pydantic models first
2. Test models with unit tests
3. Implement MCP tool using models
4. Validate with integration tests
5. Refine based on real API behavior

#### 7. **Test Data Requirements**

Each API needs comprehensive test data in `test_data.py`:
- Success responses for all endpoints (unit tests)
- Error responses for common failures (unit tests)
- Edge cases (empty lists, missing fields) (unit tests)
- Bulk operation responses (unit tests)
- Invalid data to test Pydantic validation (unit tests)
- Integration tests use real API responses (no test data needed)

#### 8. **Running Tests**

**Unit Mode (Default):**
```bash
uv run pytest src/tools/tests/test_return_policy_api.py --test-mode=unit
```

**Integration Mode:**
```bash
uv run pytest src/tools/tests/test_return_policy_api.py --test-mode=integration
```

#### 9. **Error Handling Patterns**

**Integration Test Error Handling:**
```python
if self.is_integration_mode:
    try:
        result = await api_function.fn(ctx=ctx, **params)
        response = json.loads(result)
        if response["status"] != "success":
            # Expected for auth/permission issues in sandbox
            assert "error_code" in response
            print("✅ Integration structure validated (auth required)")
            return
        # Test successful response...
    except Exception as e:
        # Even exceptions validate structure
        print(f"✅ Integration test caught expected exception: {e}")
```

**Unit Test Error Handling:**
```python
else:
    # Test specific error conditions with mocks
    mock_client.post.side_effect = EbayApiError("Rate limit exceeded", 429)
    result = await api_function.fn(ctx=ctx, **params)
    response = json.loads(result)
    assert response["status"] == "error"
    assert response["error_code"] == "EXTERNAL_API_ERROR"
```

### Test Data Requirements:
Each API needs comprehensive test data in `test_data.py`:
- Success responses for all endpoints
- Error responses for common failures
- Edge cases (empty lists, missing fields)
- Bulk operation responses
- Invalid data to test Pydantic validation

---

## CRITICAL: NO "SUCCESSFUL FAILURES" IN TESTS

**⚠️ ABSOLUTELY CRITICAL REQUIREMENT ⚠️**

**THIS IS NON-NEGOTIABLE**: Tests MUST fail when things go wrong. There is NO SUCH THING as a "successful failure" in testing.

### The Anti-Pattern That Must Be Eliminated

**NEVER DO THIS:**
```python
# TERRIBLE ANTI-PATTERN - This hides real problems!
if response["status"] == "error":
    print("Test completed successfully with expected error")
    return  # NO! This is lying to yourself and the system!
```

**ALWAYS DO THIS:**
```python
# CORRECT PATTERN - Fail fast and loud on real problems
if response["status"] == "error":
    error_code = response.get("error_code")
    error_msg = response.get("error_message", "")
    details = response.get("details", {})
    pytest.fail(f"API call failed - {error_code}: {error_msg}\nDetails: {details}")
```

### Why This Matters

1. **Tests Are Your Safety Net**: If tests don't fail on real problems, you have NO safety net
2. **Hidden Problems Compound**: A "successful failure" today becomes a production outage tomorrow
3. **Debugging Nightmares**: When tests hide failures, debugging becomes impossible
4. **False Confidence**: Green tests that hide failures give dangerous false confidence

### The Only Acceptable Exception

The ONLY time an error is acceptable in integration tests is when testing OAuth scope enforcement for APIs that require user consent:

```python
# ONLY acceptable for OAuth validation tests
if response["error_code"] == "AUTHENTICATION_ERROR" and "User consent required" in response["error_message"]:
    print("Expected: User consent required for sell.account scope")
    return  # This is the ONLY acceptable case
```

But even then, you MUST first validate infrastructure works with a different API!

---

## DIAGNOSTIC TEST METHODOLOGY

**FUNDAMENTAL PRINCIPLE**: Tests must distinguish real problems from expected behavior and provide actionable diagnostic information.

### Core Problem: "Successfully Failing" Tests

Traditional integration tests for user consent APIs always fail with auth errors, making them useless for distinguishing:
- Expected behavior (user consent required)
- Real problems (bad config, network issues, API errors)

### Required Test Categories

#### 1. **Infrastructure Validation Tests**
**Purpose**: Prove that only OAuth scope is blocking restricted APIs

**Requirements**:
- MUST use APIs that don't require user consent (Browse, Taxonomy, Catalog)
- MUST make real API calls in integration mode (2-5 second timing)
- MUST fail hard (pytest.fail()) on configuration, network, or credential issues
- MUST succeed and return real data from eBay

**Example**:
```python
@pytest.mark.asyncio
async def test_infrastructure_validation(self, mock_context):
    """CRITICAL: Validates integration infrastructure works before testing restricted APIs."""
    if not self.is_integration_mode:
        pytest.skip("Infrastructure validation only runs in integration mode")
    
    # Use Browse API to prove connectivity
    from tools.browse_api import search_items
    print("Testing integration infrastructure with Browse API...")
    print("This API uses basic scope (no user consent required)")
    
    result = await search_items.fn(ctx=mock_context, query="iPhone", limit=1)
    response = json.loads(result)
    
    if response["status"] == "error":
        error_code = response["error_code"]
        error_msg = response["error_message"]
        
        if error_code == "CONFIGURATION_ERROR":
            pytest.fail(f"CREDENTIALS PROBLEM: {error_msg}")
        elif error_code == "EXTERNAL_API_ERROR":
            pytest.fail(f"eBay API CONNECTIVITY ISSUE: {error_msg}")
        else:
            pytest.fail(f"UNEXPECTED INFRASTRUCTURE ISSUE: {error_code} - {error_msg}")
    
    print("Integration infrastructure is working correctly")
    print("Network, credentials, and basic API calls are functional")
    assert "data" in response
    items = response["data"].get("items", [])
    print(f"Retrieved {len(items)} items from eBay")
```

#### 2. **OAuth Scope Enforcement Tests**
**Purpose**: Prove OAuth validation is working correctly

**Requirements**:
- MUST first validate infrastructure works
- MUST test the actual restricted API
- MUST fail hard on anything other than expected auth errors
- MUST only pass on "User consent required" errors

**Example**:
```python
@pytest.mark.asyncio 
async def test_oauth_scope_enforcement(self, mock_context):
    """Tests OAuth scope enforcement - MUST fail only with expected auth error."""
    if not self.is_integration_mode:
        pytest.skip("OAuth scope test only runs in integration mode")
        
    # First ensure infrastructure works
    print("Step 1: Verify infrastructure is functional...")
    from tools.browse_api import search_items
    browse_result = await search_items.fn(ctx=mock_context, query="test", limit=1)
    browse_response = json.loads(browse_result)
    
    if browse_response["status"] != "success":
        pytest.fail("Infrastructure check failed - fix basic connectivity before testing OAuth")
    
    print("Infrastructure confirmed working")
    print("Step 2: Test OAuth scope enforcement...")
    
    # Test restricted API
    policy_input = ReturnPolicyInput(...)
    result = await create_return_policy.fn(ctx=mock_context, policy_input=policy_input)
    response = json.loads(result)
    
    # This SHOULD fail with auth error only
    if response["status"] != "error":
        pytest.fail("OAuth scope enforcement not working - API should require user consent")
    if response["error_code"] != "AUTHENTICATION_ERROR":
        pytest.fail(f"Unexpected error type: {response['error_code']} - expected AUTHENTICATION_ERROR")
    if "User consent required" not in response["error_message"]:
        pytest.fail(f"Wrong auth error: {response['error_message']} - should mention user consent")
    
    print("OAuth scope enforcement working correctly")
    print("sell.account scope properly requires user consent")
```

#### 3. **Enhanced Error Classification**
**Requirements**:
- Expected auth errors: AUTHENTICATION_ERROR with "User consent required"
- Real problems: CONFIGURATION_ERROR, network issues, unexpected API errors
- MUST fail hard (pytest.fail()) on real problems
- MUST only pass on expected behavior

**Error Classification Pattern**:
```python
if response["status"] == "error":
    if response["error_code"] == "AUTHENTICATION_ERROR" and "User consent required" in response["error_message"]:
        print("Expected: User consent required for sell.account scope")
        return  # This is correct behavior
    elif response["error_code"] == "CONFIGURATION_ERROR":
        pytest.fail(f"CONFIGURATION PROBLEM: {response['error_message']}")
    elif response["error_code"] == "EXTERNAL_API_ERROR":
        if "details" in response and "status_code" in response["details"]:
            status_code = response["details"]["status_code"]
            if status_code in [401, 403]:
                print(f"Expected: eBay returned {status_code} (auth required)")
                return
            else:
                pytest.fail(f"UNEXPECTED eBay API ERROR: Status {status_code}")
        else:
            pytest.fail(f"NETWORK OR API CONNECTION ISSUE: {response['error_message']}")
    else:
        pytest.fail(f"UNEXPECTED ERROR TYPE: {response['error_code']} - {response['error_message']}")
```

### Test Output Standards

#### Professional Output Requirements:
- **NO emoji characters** (🚫❌✅) - use plain text only
- Clear, actionable error messages
- Specific diagnostic information
- Professional tone suitable for enterprise environments

#### Good vs Bad Examples:
```python
# GOOD
pytest.fail("CONFIGURATION PROBLEM: Missing EBAY_APP_ID environment variable")
print("Infrastructure validated - connectivity and credentials working")
print("OAuth scope enforcement working correctly")

# BAD  
pytest.fail("❌ CONFIG ISSUE: Missing app ID 😞")
print("✅ Infra working! 🎉")
print("🔐 OAuth working! 🎯")
```

#### Diagnostic Requirements:
- Include timing information to distinguish real API calls from fast failures
- Classify errors into specific categories with next steps
- Provide clear indication of what component failed
- Surface actionable information for developers/LLMs

### Integration Test Timing Expectations

**App-Only APIs** (api_scope):
- Examples: Browse, Taxonomy, Catalog
- Integration tests MUST succeed with real API calls
- Timing: 2-5 seconds (proves real network activity)
- Use these for infrastructure validation

**User Consent APIs** (sell.account, sell.fulfillment, sell.inventory):
- Examples: Account, Return Policy, Fulfillment Policy
- Integration tests MUST fail with AUTHENTICATION_ERROR only
- Timing: <1 second (fast failure at auth check)
- MUST be preceded by infrastructure validation test

---

## Definition of Done

Each phase is complete when all quality gates are met:

### Unit Test Quality Gates:
- [ ] All Pydantic models validate correctly with comprehensive test coverage
- [ ] Enum validation errors show all valid options for LLM guidance  
- [ ] Complete mocking with zero real API calls in unit mode
- [ ] All error scenarios covered (credentials, user consent, API errors)
- [ ] Professional output with no emoji characters
- [ ] Clear, actionable error messages

### Integration Test Quality Gates:
- [ ] Infrastructure validation test passes (proves connectivity works)
- [ ] OAuth scope enforcement test passes (proves auth validation works)
- [ ] Clear timing distinction between real API calls (2-5s) and fast failures (<1s)
- [ ] All error messages are actionable and professional
- [ ] No "successfully failing" tests without diagnostic value
- [ ] Tests distinguish real problems from expected behavior

### Diagnostic Quality Gates:
- [ ] Tests provide actionable diagnostic information
- [ ] Error messages include specific next steps
- [ ] Output suitable for enterprise environments  
- [ ] Clear indication of component failure location
- [ ] Infrastructure vs auth vs configuration issues clearly separated

### Code Quality Gates:
- [ ] All code implemented and passing comprehensive tests
- [ ] Documentation updated with diagnostic methodology
- [ ] Integration tests provide meaningful diagnostics
- [ ] Code reviewed and refactored
- [ ] Test data comprehensive and professional
- [ ] MCP tools discoverable and well-documented
- [ ] Pydantic models validate ALL inputs
- [ ] Zero manual validation code
- [ ] Validation errors are self-documenting

---

## IMPLEMENTATION SUMMARY

### Key Success Factors

The enhanced testing methodology ensures:

1. **Meaningful Tests**: Every test provides diagnostic value and distinguishes real problems from expected behavior
2. **Professional Quality**: Clean, enterprise-suitable output without emoji clutter  
3. **Actionable Diagnostics**: Clear error classification with specific next steps
4. **Infrastructure Validation**: Proof that connectivity and credentials work before testing restricted APIs
5. **OAuth Verification**: Confirmation that auth requirements are correctly enforced

### Test Categories by API Type

**App-Only APIs** (Browse, Taxonomy, Catalog):
- Direct integration testing with real API calls
- Use for infrastructure validation
- Must succeed with timing 2-5 seconds

**User Consent APIs** (Account, Return Policy, Fulfillment):
- Infrastructure validation test (using app-only API)
- OAuth scope enforcement test (fast auth failure)
- Enhanced error classification for diagnostics

### Critical Success Metrics

**Unit Tests**: Fast, comprehensive mocking, all edge cases covered
**Integration Tests**: Clear diagnostic value, professional output, actionable errors
**Overall**: Tests guide developers/LLMs toward correct solutions

This methodology eliminates "successfully failing" tests and ensures every test provides meaningful diagnostic information for autonomous development.

---

## Appendix: Common Patterns

### Error Handling Pattern:
```python
try:
    response = await rest_client.post(endpoint, json=data)
    return success_response(data=response)
except EbayApiError as e:
    return error_response(
        ErrorCode.EXTERNAL_API_ERROR,
        str(e),
        {"status_code": e.status_code}
    )
```

### Conditional Validation Pattern (in Pydantic):
```python
class PolicyInput(BaseModel):
    returns_accepted: bool
    return_period: Optional[TimeDuration]
    
    @model_validator(mode='after')
    def validate_conditional(self):
        if self.returns_accepted and not self.return_period:
            raise ValueError("return_period is required when returns are accepted")
        return self
```

### MCP Tool Pattern:
```python
@mcp.tool
async def create_return_policy(
    ctx: Context,
    name: str,
    marketplace_id: MarketplaceIdEnum,  # Use enum!
    returns_accepted: bool,
    # ... other parameters with proper types
) -> str:
    """
    Create a new return policy for your eBay seller account.
    
    [Detailed description for LLM understanding]
    """
    # Build Pydantic model - validation automatic!
    policy = PolicyInput(
        name=name,
        marketplace_id=marketplace_id,
        returns_accepted=returns_accepted
    )
```

---

## COMMON PITFALLS TO AVOID

1. **Writing Manual Validation**
   ```python
   # NEVER DO THIS
   if not validate_enum_value(SomeEnum, value):
       raise ValueError("Invalid value")
   
   # ALWAYS DO THIS
   value: SomeEnum  # Automatic validation!
   ```

2. **Using Strings Instead of Enums**
   ```python
   # NEVER
   marketplace_id: str
   
   # ALWAYS
   marketplace_id: MarketplaceIdEnum
   ```

3. **Validating in MCP Tools**
   ```python
   # NEVER validate in the tool function
   @mcp.tool
   async def create_policy(marketplace_id: str):
       if marketplace_id not in VALID_MARKETS:  # NO!
   
   # ALWAYS use typed parameters
   @mcp.tool
   async def create_policy(marketplace_id: MarketplaceIdEnum):
       # Validation already done!
   ```

4. **Not Trusting Pydantic Errors**
   - Pydantic errors are meant for LLMs
   - They contain the solution
   - Don't wrap or hide them
   - Let them bubble up to the API/MCP layer

5. **Duplicating Validation**
   ```python
   # NEVER
   if len(name) > 64:
       raise ValueError("Name too long")
   
   # ALWAYS
   name: str = Field(..., max_length=64)
   ```

6. **Not Using Pydantic Models First**
   - Create Pydantic models BEFORE writing any code
   - Test the models with sample data
   - Only then write the MCP tools

---

## Next Steps

1. Review and approve this PRP
2. Begin Phase 1 implementation
3. Daily progress updates
4. Phase gate reviews before proceeding
5. Ensure Pydantic-first approach for all phases