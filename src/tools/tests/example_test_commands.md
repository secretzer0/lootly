# Example Test Commands

## Unit Tests (Default Mode)

```bash
# Run all tests in unit mode (with mocks)
uv run pytest

# Run specific test file
uv run pytest src/tools/tests/test_browse_api.py

# Run specific test by name pattern
uv run pytest -k "test_search_items"

# Run only conversion/validation tests (unit-only)
uv run pytest -k "test_convert or test_validation"

# Verbose output
uv run pytest -vv

# With coverage
uv run pytest --cov=tools
```

## Integration Tests (Real API Calls)

```bash
# First set credentials
export EBAY_APP_ID="your-app-id"
export EBAY_CERT_ID="your-cert-id"

# Run all tests in integration mode
uv run pytest --test-mode=integration

# Run specific file in integration mode
uv run pytest src/tools/tests/test_browse_api.py --test-mode=integration

# Run specific test
uv run pytest src/tools/tests/test_browse_api.py::TestBrowseApi::test_search_items_basic --test-mode=integration

# Skip unit-only tests
uv run pytest --test-mode=integration -m "not unit"
```

## Mixed Testing

```bash
# Run all unit tests (quick)
uv run pytest -m unit

# Run all integration tests (slower)
uv run pytest -m integration --test-mode=integration

# Exclude integration tests (unit only)
uv run pytest -m "not integration"
```

## Debugging

```bash
# Show print statements
uv run pytest -s

# Stop on first failure
uv run pytest -x

# Run last failed tests
uv run pytest --lf

# Run specific test with full traceback
uv run pytest src/tools/tests/test_browse_api.py::TestBrowseApi::test_search_items_basic -vv --tb=long
```