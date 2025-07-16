# Lootly - eBay MCP Server

**AI-powered eBay integration for Claude and other LLMs**

Lootly provides comprehensive eBay marketplace intelligence through the Model Context Protocol (MCP). Search items, analyze markets, and discover deals - all directly from your AI assistant.

## ✨ Key Features

- **🔍 Modern REST APIs** - Browse, Taxonomy, and Marketplace Insights
- **📊 Market Intelligence** - Real-time trends, seasonal insights, pricing analysis  
- **🏪 Seller Tools** - Business policies and account management
- **🔐 Secure OAuth** - Built-in user consent flow for account access
- **🚀 Easy Integration** - Simple installation and Claude Desktop setup

## 🎯 Current API Status

**✅ Fully Functional REST APIs:**
- **Browse API** - Search and browse eBay listings with advanced filters
- **Taxonomy API** - Dynamic category hierarchy and item aspects
- **Marketplace Insights API** - Market trends and seasonal data
- **Account API** - Business policies and seller account management (requires user OAuth)


**⚠️ Legacy APIs (Limited Support):**
- **Finding API** - Basic search functionality (being phased out)
- **Shopping API** - Item details (requires OAuth)
- **Trading API** - Legacy seller operations (requires OAuth)

**🔐 Security Features:**
- MCP-native OAuth consent flow (no web redirects needed)
- Secure token storage in user's home directory
- Automatic token refresh and validation
- Graceful degradation when credentials are missing

## 🚀 Quick Start

### 1. Get Your Own eBay API Credentials

**🔐 Security Note**: Each user must provide their own eBay developer credentials. Never share these with others or include them in version control.

1. **Create eBay Developer Account**
   - Go to [eBay Developer Portal](https://developer.ebay.com/)
   - Sign up for a free developer account
   - Verify your email address

2. **Create an Application**
   - Go to [My Applications](https://developer.ebay.com/my/keys)
   - Click "Create Application"
   - Fill in application details:
     - **Application Name**: Something descriptive (e.g., "My eBay MCP Integration")
     - **Application Type**: "Personal" or "Business"
     - **Application Use**: Select appropriate use case

3. **Get Your Credentials**
   - **App ID (Client ID)**: Required for all API access ✅
   - **Dev ID**: Required for some legacy APIs ⚠️
   - **Cert ID (Client Secret)**: Required for user APIs and OAuth 🔐

   **⚠️ IMPORTANT**: The Cert ID is like a password - keep it secure!

### 2. Install Lootly
```bash
git clone https://github.com/secretzer0/lootly
cd lootly
uv sync
```

### 3. Configure Your Credentials

1. **Copy the template file**:
   ```bash
   cp .env.template .env
   ```

2. **Edit `.env` with your credentials**:
   ```env
   # eBay Application Credentials
   EBAY_APP_ID=your-app-id-here
   EBAY_DEV_ID=your-dev-id-here
   EBAY_CERT_ID=your-cert-id-here
   
   # Environment settings
   EBAY_SANDBOX_MODE=true
   EBAY_SITE_ID=EBAY-US
   ```

3. **Verify your setup**:
   ```bash
   uv run python -c "from config import EbayConfig; config = EbayConfig.from_env(); print('✅ Configuration loaded successfully')"
   ```

### 4. Test Installation
```bash
# Test the server
uv run lootly-server --help

# Quick functionality test
uv run python -c "from lootly_server import create_lootly_server; server = create_lootly_server(); print('✅ Server created successfully')"
```

### 5. Add to Claude

#### Claude Desktop
Add to your `claude_desktop_config.json`:

**Option 1: Using .env file (Recommended)**
```json
{
  "mcpServers": {
    "lootly": {
      "command": "uv",
      "args": ["run", "lootly"],
      "cwd": "/path/to/lootly"
    }
  }
}
```

**Option 2: Environment variables in config**
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
# Add local server (STDIO transport) - uses .env file
claude mcp add lootly uv run lootly --cwd /path/to/lootly

# Or add with environment variables
claude mcp add lootly uv run lootly --cwd /path/to/lootly --env EBAY_APP_ID=your-app-id-here

# For web integration with SSE
LOOTLY_TRANSPORT=sse LOOTLY_PORT=8000 uv run lootly &
claude mcp add --transport sse lootly http://localhost:8000
```

### 6. Start Using
Restart Claude Desktop and try:
```
Search eBay for "vintage camera" under $200

What are current market trends on eBay?

Get category suggestions for "smartphone accessories"
```

### 7. OAuth Setup for Account API

For APIs that require user permissions (Account), you'll need to complete OAuth authorization:

1. **Check your consent status**:
   ```
   Check my eBay OAuth consent status
   ```

2. **If consent is needed, start the flow**:
   ```
   I need to authorize eBay account access
   ```

3. **Follow the provided instructions** to complete authorization

4. **Verify access**:
   ```
   Get my eBay business policies
   ```

## 🔐 Security & Best Practices

### Credential Security

**✅ DO:**
- Keep your `.env` file secure and never commit it to version control
- Use your own eBay developer credentials (never share with others)
- Set appropriate file permissions: `chmod 600 .env`
- Regularly rotate your Certificate ID if you suspect compromise
- Use sandbox mode for testing and development

**❌ DON'T:**
- Include credentials in your source code or configuration files
- Share your Certificate ID with anyone (it's like a password)
- Commit your `.env` file to Git repositories
- Use production credentials for testing

### Token Storage

- User OAuth tokens are stored securely in `~/.ebay/oauth_tokens.json`
- File permissions are automatically set to 600 (readable only by owner)
- Tokens are automatically refreshed when needed
- You can revoke consent at any time through the OAuth tools

### Data Privacy

- Lootly only accesses data you explicitly authorize
- No data is sent to third parties
- All API calls are made directly to eBay's servers
- User consent is required for accessing account-specific data

### API Rate Limits

- Lootly respects eBay's API rate limits
- Built-in rate limiting prevents quota exceeded errors
- Automatic backoff and retry for transient failures
- Monitor your API usage through eBay's developer dashboard

## 💡 Usage Examples

### Search & Discovery (Browse API)
```
Search eBay for "vintage camera" under $200

Find iPhone 15 Pro listings with Buy It Now format

Get detailed information for eBay item 123456789012

Search for electronics in category 293 with local pickup
```


### Category Management (Taxonomy API)
```
Get category suggestions for "smartphone accessories"

Show me the category tree for electronics

Get item aspects for category 9355 (Cell Phones)

Find the default category tree ID for EBAY_US
```

### Market Intelligence (Marketplace Insights API)
```
What are the trending categories on eBay right now?

Show me seasonal market opportunities

Get marketplace insights for the Electronics category

Analyze market trends for the past 30 days
```

### Account Management (Requires OAuth)
```
Check my eBay OAuth consent status

Get my eBay business policies

Show me my payment policies

Get my shipping rate tables

Check my seller standards profile
```

## 🎯 What You Can Do

| Feature | Description | Credentials Needed |
|---------|-------------|-------------------|
| **Browse Items** | Search eBay with advanced filters and sorting | App ID only |
| **Item Details** | Get detailed item information and status | App ID only |
| **Category Management** | Dynamic categories, suggestions, item aspects | App ID only |
| **Market Intelligence** | Trending categories, seasonal insights, analytics | App ID only |
| **Account Policies** | Business policies, rate tables, seller standards | App ID + Cert ID + OAuth |
| **OAuth Flow** | MCP-native user consent and token management | App ID + Cert ID |
| **Legacy APIs** | Shopping, Trading, Finding (limited support) | App ID + Cert ID |

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

## 🔧 Troubleshooting

### Common Credential Issues

**❌ "EBAY_APP_ID environment variable is required"**
- Solution: Copy `.env.template` to `.env` and add your App ID
- Get credentials at: https://developer.ebay.com/my/keys

**❌ "EBAY_CERT_ID environment variable is required"**
- Solution: Add your Certificate ID to the `.env` file
- Required for Account API and OAuth
- Keep this value secure!

**❌ "User consent required for Account API"**
- Solution: Run the OAuth consent flow:
  ```
  Check my eBay OAuth consent status
  I need to authorize eBay account access
  ```

**❌ "Invalid client credentials"**
- Check that your App ID and Cert ID are correct
- Verify you're using the right environment (sandbox vs production)
- Make sure credentials are for the same eBay application

**❌ "Configuration loaded successfully" but features don't work**
- Verify your `.env` file is in the correct directory
- Check that `EBAY_SANDBOX_MODE` is set to `true` for testing
- Ensure your eBay application has the required permissions

### API-Specific Issues

**Browse API not working:**
- Only requires App ID
- Check your rate limits on eBay developer dashboard
- Verify network connectivity

**Account API not working:**
- Requires OAuth user consent
- Use the built-in OAuth flow to authorize access
- Check that your tokens haven't expired

**Legacy APIs (Shopping, Trading) not working:**
- These APIs have limited support
- Some features may require production credentials
- Consider using the modern REST APIs instead

### Getting Help

1. Check the [eBay Developer Portal](https://developer.ebay.com/) for API status
2. Review your application settings and permissions
3. Check the server logs for detailed error messages
4. Verify your API quotas and rate limits

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