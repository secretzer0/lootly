# Developer Guide

This guide covers the technical architecture, development workflow, and contribution guidelines for Lootly.

## Project Architecture

### Directory Structure

```
lootly/
├── src/                           # Source code
│   ├── main.py                   # Application entry point
│   ├── lootly_server.py          # MCP server configuration
│   ├── config.py                 # Environment configuration
│   ├── data_types.py             # Standardized response types
│   ├── logging_config.py         # Centralized logging
│   │
│   ├── api/                      # eBay API integration layer
│   │   ├── ebay_client.py        # Unified API client
│   │   └── tests/                # API integration tests
│   │
│   ├── tools/                    # MCP Tools (LLM actions)
│   │   ├── finding_api.py        # Item search and discovery
│   │   ├── shopping_api.py       # Public item data
│   │   ├── trading_api.py        # Listing management
│   │   ├── merchandising_api.py  # Trending items
│   │   └── tests/                # Tool tests (unit + integration)
│   │
│   ├── resources/                # MCP Resources (read-only data)
│   │   ├── categories.py         # Category hierarchy
│   │   ├── shipping.py           # Shipping rates/policies
│   │   ├── policies.py           # Seller policy templates
│   │   ├── trends.py             # Market intelligence
│   │   └── tests/                # Resource tests
│   │
│   └── prompts/                  # MCP Prompts (guided workflows)
│       ├── search_assistant.py   # Search optimization
│       ├── listing_optimizer.py  # Listing improvement
│       ├── deal_finder.py        # Bargain hunting
│       ├── market_researcher.py  # Market analysis
│       └── tests/                # Prompt tests
│
├── docs/                         # Documentation
├── scripts/                      # Development scripts
├── Dockerfile                    # Container configuration
├── docker-compose.yml           # Multi-container setup
├── pyproject.toml               # Python project config
└── .env.example                 # Configuration template
```

### Design Principles

1. **Vertical Slice Architecture**: Each API (Finding, Shopping, etc.) is self-contained
2. **Progressive Enhancement**: Features work without credentials, improve with API access
3. **Standardized Responses**: All components use consistent JSON response formats
4. **Comprehensive Testing**: Unit, integration, and import tests for reliability
5. **MCP Native**: Built specifically for Model Context Protocol integration

### Technology Stack

- **Runtime**: Python 3.12+
- **Framework**: FastMCP 2.10+
- **API Client**: ebaysdk 2.2+
- **Testing**: pytest + pytest-asyncio
- **Validation**: Pydantic
- **Containerization**: Docker + Docker Compose
- **Package Management**: uv

## Development Workflow

### Environment Setup

1. **Clone and Install**
```bash
git clone https://github.com/yourusername/lootly
cd lootly
uv sync
```

2. **Environment Configuration**
```bash
cp .env.example .env
# Edit .env with your eBay API credentials
```

3. **Verify Installation**
```bash
# Test imports
uv run python -c "from lootly_server import create_lootly_server; print('✅ Setup complete')"

# Run tests
uv run pytest
```

### Testing Strategy

#### Test Types

1. **Import Tests** (`test_*_imports.py`)
   - Verify module imports work
   - Check FastMCP decorator registration
   - Validate MCP server integration

2. **Unit Tests** (`test_*_unit.py`)
   - Test individual functions with mocked dependencies
   - Validate input/output processing
   - Check error handling

3. **Integration Tests** (`test_*_integration.py`)
   - Test real eBay API interactions
   - Require valid credentials
   - Validate end-to-end workflows

#### Running Tests

```bash
# All tests (no credentials needed for most)
uv run pytest -v

# Specific test categories
uv run pytest src/tools/tests/ -v          # Tool tests
uv run pytest src/resources/tests/ -v      # Resource tests
uv run pytest src/prompts/tests/ -v        # Prompt tests

# Integration tests (requires API credentials)
EBAY_RUN_INTEGRATION_TESTS=true uv run pytest src/api/tests/test_api_integration.py -v

# Docker tests
./scripts/docker-run.sh test
```

#### Test Configuration

Tests use environment variables for configuration:

```bash
# Enable integration tests
EBAY_RUN_INTEGRATION_TESTS=true

# Test with specific credentials
EBAY_APP_ID=your-app-id-here
EBAY_SANDBOX_MODE=true

# Reduce noise during testing
LOOTLY_LOG_LEVEL=ERROR
```

### Adding New Features

#### Adding a New Tool

1. **Create Tool Function**
```python
# src/tools/your_new_api.py
from fastmcp import Context
from lootly_server import mcp
from data_types import success_response, error_response, ErrorCode

@mcp.tool()
async def your_new_tool(
    param1: str,
    param2: int = 10,
    ctx: Context = None
) -> str:
    """Description of what this tool does."""
    try:
        # Input validation
        if not param1:
            return error_response(
                ErrorCode.VALIDATION_ERROR,
                "param1 is required"
            ).to_json_string()
        
        # Progress reporting
        await ctx.info(f"Processing {param1}...")
        
        # Business logic
        result = await process_request(param1, param2)
        
        # Success response
        return success_response(
            data=result,
            message="Operation completed successfully"
        ).to_json_string()
        
    except Exception as e:
        await ctx.error(f"Tool failed: {str(e)}")
        return error_response(
            ErrorCode.INTERNAL_ERROR,
            str(e)
        ).to_json_string()
```

2. **Add Tests**
```python
# src/tools/tests/test_your_new_api.py
import pytest
import json
from unittest.mock import AsyncMock, MagicMock
from tools.your_new_api import your_new_tool

@pytest.mark.asyncio
async def test_your_new_tool_success():
    """Test successful operation."""
    ctx = AsyncMock()
    
    result_json = await your_new_tool.fn(
        param1="test",
        param2=5,
        ctx=ctx
    )
    
    result = json.loads(result_json)
    assert result["status"] == "success"
    ctx.info.assert_called_once()
```

3. **Register with Server**
```python
# src/lootly_server.py - already imports all tool modules
# Your tool will be automatically registered via the @mcp.tool() decorator
```

#### Adding a New Resource

1. **Create Resource Function**
```python
# src/resources/your_resource.py
from fastmcp import Context
from lootly_server import mcp
from data_types import MCPResourceData

@mcp.resource("ebay://your-resource/{resource_id}")
async def your_resource_function(resource_id: str, ctx: Context) -> str:
    """Provide resource data with static fallback."""
    try:
        # API data (if available)
        api_data = await get_live_data(resource_id)
        
        if api_data:
            data_source = "live_api"
            resource_data = api_data
        else:
            # Static fallback
            data_source = "static_cache"
            resource_data = STATIC_DATA.get(resource_id, {})
        
        return MCPResourceData(
            data={
                "resource": resource_data,
                "data_source": data_source
            },
            metadata={
                "cache_ttl": 3600,
                "resource_id": resource_id
            }
        ).to_json_string()
        
    except Exception as e:
        return MCPResourceData(
            error=str(e),
            metadata={"error_type": type(e).__name__}
        ).to_json_string()
```

2. **Add Static Data**
```python
# Static fallback data
STATIC_DATA = {
    "example": {
        "name": "Example Resource",
        "description": "Example description"
    }
}
```

#### Adding a New Prompt

1. **Create Prompt Function**
```python
# src/prompts/your_prompt.py
from fastmcp import Context
from lootly_server import mcp

@mcp.prompt("your_workflow")
async def your_workflow_prompt(
    user_goal: str = "general assistance",
    ctx: Context = None
) -> str:
    """Guide users through your specific workflow."""
    try:
        await ctx.info("Workflow prompt activated")
        
        return f"""# 🎯 Your Workflow Assistant

I'll help you achieve: {user_goal}

## Available Tools:
• `your_new_tool` - Description of what it does
• `search_items` - Find relevant items

## Available Resources:
• `ebay://your-resource/{{id}}` - Get resource data

## Workflow Steps:
1. **Step 1**: Explanation
2. **Step 2**: Explanation  
3. **Step 3**: Explanation

Let's get started! What would you like to do first?
"""
        
    except Exception as e:
        await ctx.error(f"Prompt generation failed: {str(e)}")
        return "Error generating workflow prompt"
```

### Code Standards

#### Python Style

- Follow PEP 8 style guidelines
- Use type hints for all function parameters and returns
- Docstrings for all public functions using Google style
- Maximum line length: 88 characters (Black formatter)

#### Function Naming

- Tools: `verb_noun` (e.g., `search_items`, `get_user_info`)
- Resources: `ebay_noun_resource` (e.g., `ebay_categories_resource`)
- Prompts: `noun_prompt` (e.g., `search_assistant_prompt`)

#### Error Handling

```python
# Always use standardized error responses
try:
    # Operation
    result = await operation()
    return success_response(data=result)
except ValidationError as e:
    return error_response(ErrorCode.VALIDATION_ERROR, str(e))
except APIError as e:
    return error_response(ErrorCode.EXTERNAL_API_ERROR, str(e))
except Exception as e:
    await ctx.error(f"Unexpected error: {str(e)}")
    return error_response(ErrorCode.INTERNAL_ERROR, str(e))
```

#### Async Patterns

```python
# All MCP functions should be async
@mcp.tool()
async def my_tool(ctx: Context) -> str:
    # Use async/await for all I/O operations
    result = await api_client.fetch_data()
    await ctx.info("Operation completed")
    return response
```

### Configuration Management

#### Environment Variables

All configuration uses environment variables with fallbacks:

```python
# config.py pattern
class Config(BaseModel):
    app_id: str = Field(description="eBay Application ID")
    sandbox_mode: bool = Field(True, description="Use sandbox environment")
    
    @classmethod
    def from_env(cls):
        return cls(
            app_id=os.environ.get("EBAY_APP_ID", ""),
            sandbox_mode=os.environ.get("EBAY_SANDBOX_MODE", "true").lower() == "true"
        )
```

#### Configuration Access

```python
# Tools access config via context
async def my_tool(ctx: Context):
    config = ctx.server.config
    logger = ctx.server.logger
```

### API Integration Patterns

#### Client Usage

```python
# Use the unified API client
from api.ebay_client import EbayApiClient

async def make_api_call(ctx: Context):
    config = ctx.server.config
    logger = ctx.server.logger
    
    client = EbayApiClient(config, logger)
    
    result = await client.execute_with_retry(
        api_name="finding",
        operation="findItemsAdvanced",
        params={"keywords": "test"},
        use_cache=True
    )
    
    return result
```

#### Error Handling

```python
# Handle API errors gracefully
try:
    result = await client.execute_with_retry(...)
except ConnectionError as e:
    return error_response(
        ErrorCode.EXTERNAL_API_ERROR,
        f"eBay API connection failed: {str(e)}"
    )
```

### Documentation Standards

#### Code Documentation

```python
def search_items(
    keywords: str,
    min_price: float = None,
    max_price: float = None,
    ctx: Context = None
) -> str:
    """Search eBay items with keywords and filters.
    
    Args:
        keywords: Search terms to find items
        min_price: Minimum price filter (optional)
        max_price: Maximum price filter (optional)
        ctx: MCP context for logging and progress
        
    Returns:
        JSON string with search results or error
        
    Example:
        >>> result = await search_items("vintage camera", min_price=50.0)
        >>> data = json.loads(result)
        >>> print(data["status"])
        "success"
    """
```

#### API Documentation

Update relevant documentation files when adding features:

- `docs/api-reference.md` - Tool/Resource/Prompt definitions
- `docs/usage-examples.md` - Real-world usage scenarios
- `README.md` - Update feature lists and examples

### Performance Guidelines

#### Caching Strategy

```python
# Use built-in caching for API calls
result = await client.execute_with_retry(
    "finding",
    "findItemsAdvanced", 
    params,
    use_cache=True  # Enable caching
)
```

#### Rate Limiting

- Respect eBay API rate limits (5,000 calls/day for most APIs)
- Use caching to minimize API calls
- Implement exponential backoff for retries
- Provide fallback data when rate limits exceeded

#### Memory Usage

- Stream large responses instead of loading fully into memory
- Use pagination for large result sets
- Clean up resources in finally blocks

### Security Considerations

#### Credential Handling

```python
# Never log sensitive credentials
logger.info(f"API call with app_id={config.app_id[:8]}...")  # Truncate

# Validate credentials before use
if not config.app_id:
    raise ValueError("EBAY_APP_ID is required")
```

#### Input Validation

```python
# Validate all user inputs
if not keywords or len(keywords.strip()) < 2:
    return error_response(
        ErrorCode.VALIDATION_ERROR,
        "Keywords must be at least 2 characters"
    )

# Sanitize inputs for API calls
safe_keywords = keywords.strip()[:100]  # Limit length
```

### Docker Development

#### Local Development

```bash
# Development container with hot reloading
./scripts/docker-run.sh dev

# Run tests in container
./scripts/docker-run.sh test

# Get shell access
./scripts/docker-run.sh shell dev
```

#### Building Images

```bash
# Build production image
./scripts/docker-run.sh build

# Build with no cache
./scripts/docker-run.sh build --no-cache
```

### Contributing Guidelines

#### Pull Request Process

1. **Fork and Branch**
```bash
git checkout -b feature/your-feature-name
```

2. **Implement Changes**
   - Follow code standards
   - Add comprehensive tests
   - Update documentation

3. **Test Thoroughly**
```bash
# Run all tests
uv run pytest -v

# Test Docker build
./scripts/docker-run.sh build
./scripts/docker-run.sh test

# Integration tests (if you have credentials)
EBAY_RUN_INTEGRATION_TESTS=true uv run pytest src/api/tests/ -v
```

4. **Submit Pull Request**
   - Clear description of changes
   - Link to relevant issues
   - Include test results

#### Code Review Checklist

- [ ] All tests pass
- [ ] Documentation updated
- [ ] Error handling implemented
- [ ] Type hints added
- [ ] Security considerations addressed
- [ ] Performance impact considered

### Debugging

#### Logging

```python
# Use structured logging
await ctx.info("Operation starting", extra={"operation": "search"})
await ctx.error("Operation failed", extra={"error": str(e)})
```

#### Debug Mode

```bash
# Enable debug logging
LOOTLY_LOG_LEVEL=DEBUG uv run python src/main.py
```

#### Common Issues

1. **Import Errors**: Ensure using `uv run` for proper path resolution
2. **API Errors**: Check credentials and sandbox mode settings
3. **MCP Connection**: Verify Claude Desktop configuration and restart

This developer guide provides the foundation for contributing to Lootly. For specific implementation details, refer to the existing code and test patterns throughout the project.