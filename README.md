# Lootly - eBay MCP Server

**AI-powered eBay integration for Claude and other LLMs**

Lootly provides comprehensive eBay marketplace intelligence through the Model Context Protocol (MCP). Search items, analyze markets, optimize listings, and discover deals - all directly from your AI assistant.

## ✨ Key Features

- **🔍 Comprehensive** - All eBay APIs (Finding, Shopping, Trading, Merchandising)
- **📊 Market Intelligence** - Real-time trends, seasonal insights, pricing analysis
- **🚀 Easy Integration** - Simple installation and Claude Desktop setup

## 🚀 Quick Start

### 1. Get eBay API Keys
1. Sign up at [eBay Developer Portal](https://developer.ebay.com/)
2. Create an application to get your **App ID** (required)
3. Get **Dev ID** and **Cert ID** for seller features (optional)

### 2. Install Lootly
```bash
git clone https://github.com/secretzer0/lootly
cd lootly
uv sync
```

### 3. Test Installation
```bash
# Verify setup
uv run python -c "from lootly_server import create_lootly_server; print('Installation successful')"
```

### 4. Configure Environment
Create `.env` file with your credentials:
```env
# Required for all features
EBAY_APP_ID=your-app-id-here

# Required only for seller features (Trading API)
EBAY_CERT_ID=your-cert-id-here
EBAY_DEV_ID=your-dev-id-here

# Environment settings
EBAY_SANDBOX_MODE=true
```

### 5. Add to Claude

#### Claude Desktop
Add to your `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "lootly": {
      "command": "uv",
      "args": ["run", "lootly"],
      "cwd": "/path/to/lootly",
      "env": {
        "EBAY_APP_ID": "your-app-id-here",
        "EBAY_CERT_ID": "your-cert-id-here",
        "EBAY_DEV_ID": "your-dev-id-here",
        "EBAY_SANDBOX_MODE": "true"
      }
    }
  }
}
```

#### Claude CLI (Claude Code)
```bash
# Add local server (STDIO transport)
claude mcp add lootly uv run lootly --cwd /path/to/lootly

# Or add SSE server for web integration
LOOTLY_TRANSPORT=sse LOOTLY_PORT=8000 uv run lootly &
claude mcp add --transport sse lootly http://localhost:8000

# Set environment variables
claude mcp env lootly EBAY_APP_ID=your-app-id-here
claude mcp env lootly EBAY_SANDBOX_MODE=true
```

### 6. Start Using
Restart Claude Desktop and try:
```
Search eBay for "vintage camera" under $200

What are current market trends on eBay?

Show my active eBay listings
```

## 💡 Usage Examples

### Search & Discovery
```
Search eBay for "vintage camera" under $200

Find most watched items in Electronics

Get similar items to this eBay listing: 123456789
```

### Market Intelligence  
```
What are the trending categories on eBay right now?

Show me seasonal market opportunities

Analyze pricing trends for smartphones
```

### Seller Tools (Requires API Keys)
```
Show my active eBay listings

Help me optimize this listing title: "Old Camera"

What are the recommended return policies?
```

## 🎯 What You Can Do

| Feature | Description | Credentials Needed |
|---------|-------------|-------------------|
| **Search Items** | Find eBay items with advanced filters | App ID only |
| **Get Item Details** | Detailed item information and status | App ID only |
| **Browse Categories** | eBay category hierarchy and data | None (coming soon) |
| **Market Trends** | Seasonal insights and opportunities | None (coming soon) |
| **Shipping Rates** | Cost estimates and service options | None (coming soon) |
| **Manage Listings** | Create, update, and end listings | App ID + Dev ID + Cert ID |
| **Policy Templates** | Seller policy best practices | None (coming soon) |

## 🔧 Advanced Configuration

### Transport Modes

Lootly supports three transport modes for different use cases:

#### STDIO (Default)
**Best for**: Claude Desktop integration, CLI usage
```bash
uv run lootly
# or explicitly:
LOOTLY_TRANSPORT=stdio uv run lootly
```
- Direct process communication
- Lowest latency and overhead
- Recommended for desktop AI assistants

#### SSE (Server-Sent Events)
**Best for**: Web applications, browser integration
```bash
LOOTLY_TRANSPORT=sse LOOTLY_PORT=8000 uv run lootly
```
- Real-time web streaming
- Browser-compatible event stream
- Perfect for web dashboard integration

#### HTTP
**Best for**: REST API access, microservice architecture
```bash
LOOTLY_TRANSPORT=streamable-http LOOTLY_PORT=8000 uv run lootly
```
- Standard HTTP request/response
- Easy integration with existing systems
- Ideal for server-to-server communication

### Docker Deployment
```bash
# Quick start
./scripts/docker-run.sh build
./scripts/docker-run.sh prod

# Web server
./scripts/docker-run.sh sse --port 8000
```

## 📚 Documentation

- **[Getting Started Guide](docs/getting-started.md)** - Detailed setup and configuration
- **[API Reference](docs/api-reference.md)** - Complete tools, resources, and prompts
- **[Usage Examples](docs/usage-examples.md)** - Real-world scenarios and workflows  
- **[Developer Guide](docs/developer-guide.md)** - Architecture, testing, and contributing
- **[MCP Integration](docs/mcp-integration.md)** - Understanding MCP components
- **[Docker Deployment](docs/docker-deployment.md)** - Container setup and operations

## 🧪 Testing

```bash
# Run all tests
uv run pytest

# Run integration tests (requires API keys)
EBAY_RUN_INTEGRATION_TESTS=true uv run pytest

# Docker tests
./scripts/docker-run.sh test
```

## 🤝 Contributing

We welcome contributions! See our [Developer Guide](docs/developer-guide.md) for:
- Project architecture
- Adding new features  
- Testing guidelines
- Code standards

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🔗 Links

- [eBay Developer Portal](https://developer.ebay.com/) - Get your API keys
- [Claude Desktop](https://claude.ai/desktop) - AI assistant with MCP support
- [Model Context Protocol](https://github.com/modelcontextprotocol/protocol) - Learn about MCP

---

**Ready to supercharge your eBay experience with AI?** Start with the [Getting Started Guide](docs/getting-started.md) 🚀