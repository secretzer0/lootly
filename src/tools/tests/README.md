# eBay MCP API Test Suite

This directory contains comprehensive tests for the eBay MCP API tools that can run in two modes:
- **Unit mode**: Fast tests with mocked dependencies
- **Integration mode**: Real API tests that validate against live eBay APIs

## Quick Start

### Run All Tests (Unit Mode - Default)
```bash
uv run python -m pytest src/tools/tests/
```

### Run Integration Tests (Requires eBay API Credentials)
```bash
uv run python -m pytest src/tools/tests/ --test-mode=integration
```

### Run Specific API Tests
```bash
# Test just the Browse API
uv run python -m pytest src/tools/tests/test_browse_api.py

# Test with verbose output
uv run python -m pytest src/tools/tests/test_inventory_api.py -v

# Test a specific function in an API
uv run python -m pytest src/tools/tests/test_taxonomy_api.py::TestTaxonomyApi::test_get_category_tree_full -v

# Test specific function in integration mode
uv run python -m pytest src/tools/tests/test_taxonomy_api.py::TestTaxonomyApi::test_get_category_tree_full -v --test-mode=integration
```

## Test Modes

### Unit Mode (Default)
- Uses mocked API responses
- Fast execution (all 103 tests run in ~4 seconds)
- No external dependencies or credentials required
- Tests code logic, data conversion, and error handling

### Integration Mode
- Makes real calls to eBay's sandbox/production APIs
- Validates actual API responses and contracts
- Requires valid eBay API credentials
- Tests end-to-end functionality

## Environment Setup

### Unit Tests (No Setup Required)
Unit tests run out of the box with no configuration.

### Integration Tests (Requires eBay API Credentials)
Set these environment variables:
```bash
export EBAY_APP_ID="your-ebay-app-id"
export EBAY_CERT_ID="your-ebay-cert-id"  
export EBAY_DEV_ID="your-ebay-dev-id"    # Optional
```

Or use a `.env` file in the project root:
```
EBAY_APP_ID=your-ebay-app-id
EBAY_CERT_ID=your-ebay-cert-id
EBAY_DEV_ID=your-ebay-dev-id
```

## Test Structure

### Available Test Files
- `test_browse_api.py` - Search and browse eBay items (12 tests)
- `test_inventory_api.py` - Seller inventory management (12 tests)
- `test_account_api.py` - Seller account and standards (10 tests)
- `test_marketplace_insights_api.py` - Sales trends and insights (10 tests)
- `test_marketing_api.py` - Promotions and campaigns (10 tests)
- `test_shipping_api.py` - Shipping and fulfillment (8 tests)
- `test_taxonomy_api.py` - Category and aspect metadata (16 tests)
- `test_trending_api.py` - Market trends and popular items (9 tests)

### Test Categories

#### Data Conversion Tests (Unit Only)
Test internal data transformation functions:
```python
@TestMode.skip_in_integration("Data conversion is unit test only")
def test_convert_browse_item(self):
    """Test converting API response to internal format."""
```

#### Input Validation Tests (Unit Only)
Test request parameter validation:
```python
@TestMode.skip_in_integration("Input validation is unit test only")
def test_search_input_validation(self):
    """Test search parameter validation."""
```

#### API Function Tests (Both Modes)
Test actual API endpoints in both unit and integration modes:
```python
async def test_search_items_basic(self, mock_context, mock_credentials):
    """Test basic item search in both modes."""
    if self.is_integration_mode:
        # Real API call
        result = await search_items.fn(ctx=mock_context, query="iPhone")
    else:
        # Mocked API call
        with patch('tools.browse_api.EbayRestClient') as MockClient:
            # Setup mocks and test
```

## Test Commands Reference

### Basic Testing
```bash
# All tests in unit mode (default)
uv run python -m pytest src/tools/tests/

# All tests in integration mode
uv run python -m pytest src/tools/tests/ --test-mode=integration

# Specific test file
uv run python -m pytest src/tools/tests/test_browse_api.py

# Specific test method
uv run python -m pytest src/tools/tests/test_browse_api.py::TestBrowseApi::test_search_items_basic
```

### Advanced Options
```bash
# Verbose output with test names
uv run python -m pytest src/tools/tests/ -v

# Show print statements and logging
uv run python -m pytest src/tools/tests/ -s

# Stop on first failure
uv run python -m pytest src/tools/tests/ -x

# Run tests in parallel (faster)
uv run python -m pytest src/tools/tests/ -n auto

# Show test coverage
uv run python -m pytest src/tools/tests/ --cov=tools --cov-report=html
```

### Filtering Tests
```bash
# Run only unit-only tests
uv run python -m pytest src/tools/tests/ -k "not integration_mode"

# Run only quick tests (exclude slow integration tests)
uv run python -m pytest src/tools/tests/ -m "not slow"

# Run tests matching a pattern
uv run python -m pytest src/tools/tests/ -k "search"
```

## Development Workflow

### During Development (Fast Feedback)
```bash
# Run unit tests while coding (fast)
uv run python -m pytest src/tools/tests/test_browse_api.py

# Test specific functionality
uv run python -m pytest src/tools/tests/ -k "search_items"
```

### Before Committing (Quality Check)
```bash
# Run all unit tests
uv run python -m pytest src/tools/tests/

# Run integration tests if you have credentials
uv run python -m pytest src/tools/tests/ --test-mode=integration
```

### CI/CD Pipeline
```bash
# Unit tests (always run)
uv run python -m pytest src/tools/tests/ --junitxml=unit-test-results.xml

# Integration tests (run if credentials available)
uv run python -m pytest src/tools/tests/ --test-mode=integration --junitxml=integration-test-results.xml
```

## Test Architecture

### Key Files
- `base_test.py` - Base class with mode detection and common fixtures
- `test_data.py` - Shared test data for consistent mocking
- `test_helpers.py` - Validation helpers for response checking

### Design Principles
1. **Dual Mode**: Every test runs in both unit and integration mode
2. **Consistent Data**: Same test data used for mocking and validation
3. **Fast Unit Tests**: Mocked tests run quickly for rapid development
4. **Real Validation**: Integration tests validate actual API behavior
5. **No Flaky Tests**: Robust mocking and error handling

## Troubleshooting

### Common Issues

#### "object MagicMock can't be used in 'await' expression"
- Async function mocking issue
- Use `AsyncMock` instead of `MagicMock` for async functions

#### "Required field 'X' not found"
- Response structure mismatch
- Check if API response format changed

#### "AUTHENTICATION_ERROR" in integration tests
- Missing or invalid eBay API credentials
- Verify `EBAY_APP_ID` and `EBAY_CERT_ID` are set correctly


#### Tests timeout in integration mode
- Real API calls can be slow
- Use `-x` flag to stop on first failure for debugging

### Debug Commands
```bash
# Run with maximum verbosity
uv run python -m pytest src/tools/tests/test_browse_api.py -vvv -s

# Debug specific test
uv run python -m pytest src/tools/tests/test_browse_api.py::TestBrowseApi::test_search_items_basic -vvv -s --pdb

# Check test collection
uv run python -m pytest src/tools/tests/ --collect-only
```

## Test Results

Current status: **✅ 103/103 tests passing** in both unit and integration modes.

## Adding New Tests

1. **Create test file** following the pattern `test_[api_name]_api.py`
2. **Inherit from BaseApiTest** for automatic mode detection
3. **Add test data** to `test_data.py` if needed
4. **Write dual-mode tests** that work in both unit and integration modes
5. **Use decorators** like `@TestMode.skip_in_integration()` for unit-only tests
6. **Validate responses** using helpers from `test_helpers.py`

Example new test:
```python
class TestNewApi(BaseApiTest):
    @pytest.mark.asyncio
    async def test_new_function(self, mock_context, mock_credentials):
        if self.is_integration_mode:
            # Real API test
            result = await new_function.fn(ctx=mock_context, param="value")
            data = assert_api_response_success(result)
        else:
            # Unit test with mocks
            with patch('tools.new_api.EbayRestClient') as MockClient:
                mock_client = MockClient.return_value
                mock_client.get = AsyncMock(return_value={"data": "test"})
                result = await new_function.fn(ctx=mock_context, param="value")
                data = assert_api_response_success(result)
```