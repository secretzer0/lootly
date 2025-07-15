# Understanding MCP Components

This guide explains how Lootly implements the Model Context Protocol (MCP) and how its components work together to provide AI assistants with eBay marketplace intelligence.

## What is MCP?

The Model Context Protocol (MCP) is a standardized way for AI assistants to access external tools and data. It defines three main component types:

- **Tools**: Functions the AI can call to perform actions
- **Resources**: Read-only data the AI can access via URIs  
- **Prompts**: Conversation templates that guide workflows

## Lootly's MCP Architecture

### Component Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│     Tools       │    │   Resources     │    │    Prompts      │
│   (Actions)     │    │  (Read-only)    │    │  (Templates)    │
├─────────────────┤    ├─────────────────┤    ├─────────────────┤
│ • search_items  │    │ • Categories    │    │ • Search Guide  │
│ • get_item_info │    │ • Shipping      │    │ • List Optimizer│
│ • create_listing│    │ • Policies      │    │ • Deal Finder   │
│ • analyze_market│    │ • Trends        │    │ • Market Research│
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │  FastMCP Server │
                    │   (Lootly)      │
                    └─────────────────┘
                             │
                    ┌─────────────────┐
                    │   AI Assistant  │
                    │    (Claude)     │
                    └─────────────────┘
```

### Data Flow

1. **AI Request**: Claude asks for eBay data or action
2. **MCP Routing**: FastMCP routes to appropriate component
3. **Component Execution**: Tool/Resource/Prompt processes request
4. **eBay API**: External API calls (when credentials available)
5. **Response**: Standardized JSON response to AI

## Tools Deep Dive

Tools are functions that LLMs can call to perform actions. They're the "verbs" of the MCP interface.

### Implementation Pattern

```python
from fastmcp import Context
from lootly_server import mcp

@mcp.tool()
async def search_items(
    keywords: str,
    min_price: float = None,
    max_price: float = None,
    ctx: Context = None
) -> str:
    """Search eBay items with keywords and filters."""
    try:
        # Input validation
        if not keywords or len(keywords.strip()) < 2:
            return error_response(
                ErrorCode.VALIDATION_ERROR,
                "Keywords must be at least 2 characters"
            ).to_json_string()
        
        # Progress reporting
        await ctx.info(f"Searching eBay for: {keywords}")
        
        # API interaction
        client = EbayApiClient(config, logger)
        results = await client.execute_with_retry(
            "finding",
            "findItemsAdvanced",
            {"keywords": keywords, "priceFilter": {...}}
        )
        
        # Response formatting
        return success_response(
            data=parse_search_results(results),
            message=f"Found {len(results)} items"
        ).to_json_string()
        
    except Exception as e:
        # Error handling
        await ctx.error(f"Search failed: {str(e)}")
        return error_response(
            ErrorCode.EXTERNAL_API_ERROR,
            str(e)
        ).to_json_string()
```

### Key Features

**Async Support**: All tools are async for non-blocking operation
**Context Integration**: Access to MCP context for logging and progress
**Error Handling**: Standardized error responses with clear codes
**Input Validation**: Pydantic-style validation for parameters
**Progress Reporting**: Real-time feedback to the AI assistant

### Tool Categories

1. **Search Tools** (`finding_api.py`)
   - Item discovery and filtering
   - Keyword optimization
   - Category browsing

2. **Information Tools** (`shopping_api.py`)
   - Item details and status
   - Shipping calculations
   - Seller information

3. **Seller Tools** (`trading_api.py`)
   - Listing management
   - Account information
   - Sales analytics

4. **Discovery Tools** (`merchandising_api.py`)
   - Trending items
   - Similar products
   - Market opportunities

## Resources Deep Dive

Resources provide read-only data accessible via URI patterns. They're the "nouns" of the MCP interface.

### Implementation Pattern

```python
@mcp.resource("ebay://categories/{category_id}")
async def ebay_category_details_resource(category_id: str, ctx: Context) -> str:
    """Get details for a specific eBay category."""
    try:
        # URI parameter validation
        if not category_id or not category_id.isdigit():
            return MCPResourceData(
                error="Invalid category ID format",
                metadata={"category_id": category_id}
            ).to_json_string()
        
        # Data retrieval (API + fallback)
        api_data = await get_categories_from_api(category_id)
        
        if api_data:
            # Live API data
            category_info = api_data
            data_source = "live_api"
        else:
            # Static fallback data
            category_info = STATIC_CATEGORIES.get(category_id)
            data_source = "static_cache"
        
        # Response with metadata
        return MCPResourceData(
            data={
                "category": category_info,
                "subcategories": get_subcategories(category_id),
                "search_tips": get_search_tips(category_id),
                "data_source": data_source
            },
            metadata={
                "cache_ttl": 3600,
                "last_updated": datetime.now()
            }
        ).to_json_string()
        
    except Exception as e:
        return MCPResourceData(
            error=str(e),
            metadata={"error_type": type(e).__name__}
        ).to_json_string()
```

### URI Patterns

Resources use hierarchical URI schemes:

```
ebay://categories                     # All categories
ebay://categories/11233               # Specific category
ebay://categories/11233/children      # Subcategories
ebay://categories/popular             # Popular categories

ebay://shipping/rates                 # All shipping info
ebay://shipping/rates/domestic        # US domestic only
ebay://shipping/rates/carrier/ups     # UPS-specific

ebay://market/trends                  # All trends
ebay://market/trends/seasonal         # Current season
ebay://market/trends/pricing          # Price movements
```

### Fallback Strategy

Resources implement a progressive enhancement model:

1. **Static Data**: Always available, no API required
2. **API Enhancement**: Richer data when credentials available
3. **Intelligent Caching**: Balance freshness with rate limits
4. **Graceful Degradation**: Fallback when API unavailable

## Prompts Deep Dive

Prompts are conversation templates that guide users through complex workflows.

### Implementation Pattern

```python
@mcp.prompt("search_assistant")
async def item_search_assistant_prompt(
    name: str = "there",
    ctx: Context = None
) -> str:
    """Helps users find the right items with guided search optimization."""
    try:
        await ctx.info("Search assistant prompt activated")
        
        return f"""# 🔍 eBay Search Assistant for {name}

I'm your eBay search expert! I'll help you find exactly what you're looking for.

## What I Can Help With:
• **Smart Search** - Optimize keywords for better results
• **Filter Guidance** - Set price, condition, and category filters  
• **Trend Insights** - Find popular and trending items
• **Deal Discovery** - Locate bargains and auctions

## Available Tools:
• `search_items` - Search with advanced filters
• `get_search_keywords` - Get keyword suggestions
• `find_items_by_category` - Browse by category
• `get_most_watched_items` - Find trending items

## Let's Start:
What are you looking for? I'll help you craft the perfect search!

Examples:
- "I want a vintage camera under $200"
- "Help me find gaming laptops with good graphics"
- "Show me trending items in collectibles"
"""
    
    except Exception as e:
        await ctx.error(f"Prompt generation failed: {str(e)}")
        return "Error generating search assistant prompt"
```

### Prompt Features

**Dynamic Content**: Adapts based on parameters and context
**Tool Integration**: References available tools and resources
**Workflow Guidance**: Step-by-step instructions for complex tasks
**Examples**: Concrete usage examples for users

### Prompt Categories

1. **Search Assistant**: Guided item discovery
2. **Listing Optimizer**: Improve listing quality
3. **Deal Finder**: Bargain hunting strategies
4. **Market Researcher**: Competitive analysis

## Server Architecture

### FastMCP Integration

```python
# Server setup
mcp = FastMCP("Lootly - eBay Integration Server", version="0.1.0")

# Component registration happens via decorators
# Tools: @mcp.tool()
# Resources: @mcp.resource()  
# Prompts: @mcp.prompt()

# Server creation
def create_lootly_server():
    # Import modules to register decorators
    import tools.finding_api      # Registers @mcp.tool functions
    import resources.categories   # Registers @mcp.resource functions
    import prompts.search_assistant # Registers @mcp.prompt functions
    
    return mcp
```

### Configuration Management

```python
# Environment-based configuration
config = EbayConfig.from_env()

# Attached to server for component access
mcp.config = config
mcp.logger = logger

# Components access via context
async def some_tool(ctx: Context):
    config = ctx.server.config
    logger = ctx.server.logger
```

### Transport Support

Lootly supports multiple MCP transports:

- **stdio**: Claude Desktop integration
- **sse**: Server-Sent Events for web apps
- **streamable-http**: Modern HTTP with streaming

## Best Practices

### Tool Design

1. **Single Responsibility**: Each tool does one thing well
2. **Input Validation**: Validate all parameters
3. **Error Handling**: Graceful failure with clear messages
4. **Progress Reporting**: Keep users informed of long operations
5. **Caching**: Respect rate limits with intelligent caching

### Resource Design

1. **Static Fallbacks**: Always provide data, even without API
2. **URI Hierarchies**: Logical, predictable URI patterns
3. **Metadata**: Include cache hints and data source info
4. **Performance**: Optimize for common access patterns

### Prompt Design

1. **Clear Structure**: Well-organized with headers and sections
2. **Tool References**: Guide users to relevant tools
3. **Examples**: Concrete usage examples
4. **Contextual**: Adapt content based on parameters

## Testing Strategy

### Component Testing

```python
# Tool testing
@pytest.mark.asyncio
async def test_search_items_success():
    result = await search_items.fn(
        keywords="test",
        ctx=mock_context
    )
    response = json.loads(result)
    assert response["status"] == "success"

# Resource testing  
def test_category_resource_structure():
    from resources.categories import ebay_all_categories_resource
    assert isinstance(ebay_all_categories_resource, FunctionResource)

# Prompt testing
@pytest.mark.asyncio
async def test_search_assistant_prompt():
    result = await item_search_assistant_prompt.fn(ctx=mock_context)
    assert "eBay Search Assistant" in result
```

### Integration Testing

```python
# Real API testing (requires credentials)
@pytest.mark.skipif(
    os.getenv("EBAY_RUN_INTEGRATION_TESTS") != "true",
    reason="Integration tests disabled"
)
@pytest.mark.asyncio
async def test_real_api_search():
    # Test with real eBay sandbox
    pass
```

## Extending Lootly

### Adding New Tools

1. Create function in appropriate module
2. Add `@mcp.tool()` decorator
3. Implement validation and error handling
4. Add comprehensive tests
5. Update documentation

### Adding New Resources

1. Define URI pattern
2. Create resource function with `@mcp.resource()`
3. Implement static fallback data
4. Add API enhancement when available
5. Test with and without credentials

### Adding New Prompts

1. Design workflow and user experience
2. Create prompt function with `@mcp.prompt()`
3. Reference relevant tools and resources
4. Test with various parameters
5. Document usage patterns

This architecture provides a robust, scalable foundation for eBay marketplace intelligence while maintaining the flexibility to add new features and integrate with different AI assistants.