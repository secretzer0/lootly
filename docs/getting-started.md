# Getting Started with Lootly

This guide walks you through setting up Lootly for different use cases, from basic Claude Desktop integration to advanced deployment scenarios.

## Prerequisites

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) package manager
- [Claude Desktop](https://claude.ai/desktop) (for AI integration)
- eBay Developer Account (optional, for full features)

## Installation Methods

### Method 1: Claude Desktop Integration (Recommended)

1. **Clone and Install**
```bash
git clone https://github.com/secretzer0/lootly
cd lootly
uv sync
```

2. **Configure Claude Desktop**
Edit your Claude Desktop configuration file:

**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`  
**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`  
**Linux:** `~/.config/claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "lootly": {
      "command": "uv",
      "args": ["run", "lootly"],
      "cwd": "/full/path/to/lootly",
      "env": {
        "EBAY_SANDBOX_MODE": "true"
      }
    }
  }
}
```

3. **Restart Claude Desktop**

4. **Test Basic Functionality**
Try these commands in Claude:
```
Show me eBay categories for Electronics
What are current eBay market trends?
Show me domestic shipping rates
```

### Method 2: Claude CLI Integration

1. **Install and Setup**
```bash
git clone https://github.com/secretzer0/lootly
cd lootly
uv sync
```

2. **Add to Claude CLI**
```bash
# Add local server (STDIO transport)
claude mcp add lootly uv run lootly --cwd /path/to/lootly

# Set environment variables
claude mcp env lootly EBAY_APP_ID=your-app-id-here
claude mcp env lootly EBAY_CERT_ID=your-cert-id-here
claude mcp env lootly EBAY_DEV_ID=your-dev-id-here
claude mcp env lootly EBAY_SANDBOX_MODE=true
```

3. **Test Integration**
```bash
# List configured servers
claude mcp list

# Test the connection
claude "Show me eBay categories for Electronics"
```

### Method 3: Docker Deployment

1. **Clone Repository**
```bash
git clone https://github.com/secretzer0/lootly
cd lootly
```

2. **Build and Run**
```bash
# Build the image
./scripts/docker-run.sh build

# Run production server
./scripts/docker-run.sh prod

# Or run SSE server for web integration
./scripts/docker-run.sh sse --port 8000
```

3. **Test Docker Setup**
```bash
./scripts/docker-run.sh status
```

## eBay API Credentials Setup

### Getting Your API Keys

1. **Sign up for eBay Developer Account**
   - Visit https://developer.ebay.com/
   - Create a free developer account
   - Verify your email address

2. **Create an Application**
   - Go to "My eBay" → "Application Keysets"
   - Click "Create Application Keyset"
   - Fill in application details:
     - **Name:** Lootly Integration
     - **Description:** AI-powered eBay marketplace intelligence
     - **Category:** Personal/Educational

3. **Get Your Credentials**
   - **App ID:** Required for all APIs
   - **Dev ID:** Required for Trading API
   - **Cert ID:** Required for Trading API

### Environment Configuration

Create a `.env` file in your project root:

```env
# Required for all features
EBAY_APP_ID=your-app-id-here

# Required for Trading API (seller features)
EBAY_DEV_ID=your-dev-id-here
EBAY_CERT_ID=your-cert-id-here

# Environment settings
EBAY_SANDBOX_MODE=true
EBAY_SITE_ID=EBAY-US

# Server configuration
LOOTLY_TRANSPORT=stdio
LOOTLY_LOG_LEVEL=INFO

# Performance tuning
EBAY_CACHE_TTL=300
EBAY_MAX_RETRIES=3
EBAY_MAX_PAGES=10
```

### Adding Credentials to Claude Desktop

Update your Claude Desktop configuration:

```json
{
  "mcpServers": {
    "lootly": {
      "command": "uv",
      "args": ["run", "lootly"],
      "cwd": "/full/path/to/lootly",
      "env": {
        "EBAY_APP_ID": "your-app-id-here",
        "EBAY_DEV_ID": "your-dev-id-here",
        "EBAY_CERT_ID": "your-cert-id-here",
        "EBAY_SANDBOX_MODE": "true",
        "EBAY_SITE_ID": "EBAY-US"
      }
    }
  }
}
```

## Transport Configuration

Lootly supports multiple transport protocols for different integration scenarios:

### stdio (Default)
Best for Claude Desktop and CLI tools:
```bash
uv run lootly
```

### Server-Sent Events (SSE)
For web applications that need real-time updates:
```bash
LOOTLY_TRANSPORT=sse LOOTLY_HOST=0.0.0.0 LOOTLY_PORT=8000 uv run lootly
```

### HTTP with Streaming
Modern web integration (recommended over SSE):
```bash
LOOTLY_TRANSPORT=streamable-http LOOTLY_HOST=0.0.0.0 LOOTLY_PORT=8000 uv run lootly
```

## Verification

### Test Installation

1. **Basic Functionality (No API Keys)**
```bash
# Test server starts
uv run python -c "from lootly_server import create_lootly_server; print('✅ Installation successful')"

# Run unit tests
uv run pytest -v
```

2. **API Integration (With Keys)**
```bash
# Test API connectivity
EBAY_RUN_INTEGRATION_TESTS=true uv run pytest src/api/tests/test_api_integration.py -v

# Test tools integration
EBAY_RUN_INTEGRATION_TESTS=true uv run pytest src/tools/tests/test_finding_integration.py -v
```

3. **Claude Desktop Integration**
   - Restart Claude Desktop
   - Look for "Lootly" in the MCP status
   - Try the example commands above

### Common Issues

**Import Errors**
```bash
# Make sure you're using uv run
uv run lootly              # ✅ Correct
python src/main.py         # ❌ May fail
```

**API Connection Issues**
- Verify credentials are correct
- Check you're using sandbox mode for testing
- Ensure network can reach eBay APIs

**Claude Desktop Not Detecting Server**
- Check the full path in `cwd` field
- Verify `uv` is in your PATH
- Restart Claude Desktop after config changes

## Next Steps

1. **Explore Features** - Try the examples in [Usage Examples](usage-examples.md)
2. **Learn MCP** - Understand the architecture in [MCP Integration](mcp-integration.md)
3. **API Reference** - See all available tools and resources in [API Reference](api-reference.md)
4. **Advanced Deployment** - Set up production environments with [Docker Deployment](docker-deployment.md)

## Getting Help

- **Issues:** Check the troubleshooting section in this guide
- **Features:** See the [API Reference](api-reference.md) for complete capabilities
- **Development:** Review the [Developer Guide](developer-guide.md) for contributing