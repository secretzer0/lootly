#!/usr/bin/env python3
"""
Lootly MCP Server - Main entry point
"""
import os
from lootly_server import create_lootly_server

# Create server instance for mcp command
mcp = create_lootly_server()


def main():
    """Run the Lootly MCP server with configurable transport."""
    server = create_lootly_server()
    
    # Get transport configuration from environment
    transport = os.environ.get("LOOTLY_TRANSPORT", "stdio").lower()
    host = os.environ.get("LOOTLY_HOST", "127.0.0.1")
    port = int(os.environ.get("LOOTLY_PORT", "8000"))
    
    if transport == "stdio":
        # Default stdio transport for CLI/Claude Desktop
        server.run()
    elif transport == "sse":
        # Server-Sent Events for web integrations
        print(f"Starting Lootly SSE server on {host}:{port}")
        server.run(transport="sse")
    elif transport == "http" or transport == "streamable-http":
        # HTTP/Streamable HTTP (recommended for web)
        print(f"Starting Lootly HTTP server on {host}:{port}")
        server.run(transport="streamable-http")
    else:
        raise ValueError(f"Unknown transport type: {transport}. Supported: stdio, sse, streamable-http")


if __name__ == "__main__":
    main()
