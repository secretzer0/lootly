# Docker Deployment Guide

Complete guide for deploying Lootly using Docker containers in development, testing, and production environments.

## Overview

Lootly provides Docker support for:
- **Development**: Hot reloading and debugging
- **Production**: Optimized runtime containers
- **Testing**: Isolated test environments
- **Web Integration**: SSE and HTTP transports

## Quick Start

### 1. Clone and Build

```bash
git clone https://github.com/yourusername/lootly
cd lootly

# Build the image
./scripts/docker-run.sh build
```

### 2. Environment Setup

```bash
# Copy environment template
cp .env.example .env

# Edit with your eBay API credentials
nano .env
```

### 3. Run Production Server

```bash
# STDIO transport (default)
./scripts/docker-run.sh prod

# SSE transport for web integration
./scripts/docker-run.sh sse --port 8000
```

## Docker Services

### Production Server (`lootly-server`)

**Purpose**: Production-ready STDIO transport for Claude Desktop integration

```bash
# Start production server
docker compose up lootly-server

# Or with helper script
./scripts/docker-run.sh prod
```

**Configuration**:
- Transport: STDIO
- Environment: Production optimized
- Logging: INFO level
- Restart: Unless stopped

### SSE Server (`lootly-server-sse`)

**Purpose**: Server-Sent Events transport for web applications

```bash
# Start SSE server
docker compose up lootly-server-sse

# Custom port
./scripts/docker-run.sh sse --port 8080
```

**Configuration**:
- Transport: SSE
- Port: 8000 (configurable)
- Host: 0.0.0.0
- Web accessible endpoint

### Development Server (`lootly-server-dev`)

**Purpose**: Development with hot reloading and debug features

```bash
# Start development server
docker compose --profile development up lootly-server-dev

# Or with helper script
./scripts/docker-run.sh dev
```

**Features**:
- Source code mounted for hot reloading
- Debug logging enabled
- Development dependencies included
- Interactive debugging support

### Test Server (`lootly-server-test`)

**Purpose**: Isolated testing environment

```bash
# Run tests
docker compose --profile testing run --rm lootly-server-test

# Or with helper script
./scripts/docker-run.sh test
```

**Features**:
- Clean test environment
- All test dependencies
- Configurable test credentials
- Integration test support

## Configuration

### Environment Variables

Configure services using environment variables:

```bash
# Core eBay API Configuration
EBAY_APP_ID=your-app-id-here
EBAY_DEV_ID=your-dev-id-here
EBAY_CERT_ID=your-cert-id-here
EBAY_SANDBOX_MODE=true
EBAY_SITE_ID=EBAY-US

# Lootly Server Configuration
LOOTLY_TRANSPORT=stdio          # stdio, sse, streamable-http
LOOTLY_HOST=127.0.0.1          # Host for network transports
LOOTLY_PORT=8000               # Port for network transports
LOOTLY_LOG_LEVEL=INFO          # DEBUG, INFO, WARNING, ERROR
LOOTLY_DEBUG_MODE=false        # Enable debug features

# API Performance Settings  
EBAY_CACHE_TTL=300             # Cache TTL in seconds
EBAY_MAX_RETRIES=3             # Maximum API retry attempts
EBAY_TIMEOUT=30                # API request timeout
EBAY_MAX_PAGES=10              # Maximum pagination pages

# Testing Configuration
EBAY_RUN_INTEGRATION_TESTS=false  # Enable integration tests
```

### Docker Compose Override

Create `docker-compose.override.yml` for custom configurations:

```yaml
# docker-compose.override.yml
services:
  lootly-server:
    environment:
      # Custom environment variables
      - EBAY_APP_ID=${CUSTOM_APP_ID}
      - LOOTLY_LOG_LEVEL=DEBUG
    ports:
      # Expose additional ports if needed
      - "9000:9000"
    volumes:
      # Additional volume mounts
      - ./custom-data:/app/data
```

### Production Environment File

For production, create `.env.production`:

```bash
# .env.production
EBAY_APP_ID=prod-app-id-here
EBAY_DEV_ID=prod-dev-id-here  
EBAY_CERT_ID=prod-cert-id-here
EBAY_SANDBOX_MODE=false
LOOTLY_LOG_LEVEL=WARNING
EBAY_CACHE_TTL=600
```

Use with Docker Compose:

```bash
docker compose --env-file .env.production up lootly-server
```

## Deployment Scenarios

### Claude Desktop Integration

**Scenario**: Local development with Claude Desktop

```bash
# 1. Build and start server
./scripts/docker-run.sh build
./scripts/docker-run.sh prod --detach

# 2. Configure Claude Desktop
# Add to claude_desktop_config.json:
{
  "mcpServers": {
    "lootly": {
      "command": "docker",
      "args": ["exec", "lootly-server", "python", "src/main.py"],
      "env": {
        "EBAY_APP_ID": "your-app-id"
      }
    }
  }
}

# 3. Restart Claude Desktop
```

### Web Application Integration

**Scenario**: Integrate with web application using SSE

```bash
# 1. Start SSE server
./scripts/docker-run.sh sse --port 8000

# 2. Connect from web application
const eventSource = new EventSource('http://localhost:8000/sse');
eventSource.onmessage = function(event) {
    const data = JSON.parse(event.data);
    console.log('MCP Response:', data);
};
```

### Production Server Deployment

**Scenario**: Production deployment with monitoring

```yaml
# docker-compose.production.yml
services:
  lootly-server:
    image: lootly:latest
    restart: always
    environment:
      - EBAY_SANDBOX_MODE=false
      - LOOTLY_LOG_LEVEL=WARNING
    volumes:
      - ./logs:/app/logs
      - ./data:/app/data:ro
    healthcheck:
      test: ["CMD", "python", "-c", "import sys; sys.exit(0)"]
      interval: 30s
      timeout: 10s
      retries: 3
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '0.5'
        reservations:
          memory: 256M
          cpus: '0.25'

  # Add monitoring
  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml

  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
```

### Multi-Environment Setup

**Scenario**: Development, staging, and production environments

```bash
# Directory structure
environments/
├── development/
│   ├── docker-compose.yml
│   └── .env
├── staging/
│   ├── docker-compose.yml  
│   └── .env
└── production/
    ├── docker-compose.yml
    └── .env

# Deploy to specific environment
cd environments/production
docker compose up -d
```

## Advanced Configuration

### Custom Dockerfile

For specialized deployments, extend the base Dockerfile:

```dockerfile
# Dockerfile.custom
FROM lootly:latest

# Add custom dependencies
COPY requirements-custom.txt /app/
RUN pip install -r requirements-custom.txt

# Add custom configuration
COPY custom-config/ /app/config/

# Override entrypoint if needed
COPY custom-entrypoint.sh /app/
ENTRYPOINT ["/app/custom-entrypoint.sh"]
```

### Volume Mounts

**Persistent Data**:
```yaml
volumes:
  # Configuration files
  - ./config:/app/config:ro
  
  # Log files
  - ./logs:/app/logs
  
  # Cache data
  - lootly-cache:/app/cache
  
  # Credentials (secure)
  - ./secrets/.env:/app/.env:ro
```

**Development Hot Reloading**:
```yaml
volumes:
  # Source code for development
  - ./src:/app/src
  - ./docs:/app/docs
  - ./tests:/app/tests
```

### Networking

**Custom Networks**:
```yaml
networks:
  lootly-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16

services:
  lootly-server:
    networks:
      lootly-network:
        ipv4_address: 172.20.0.10
```

**External Network Integration**:
```yaml
networks:
  external-network:
    external: true

services:
  lootly-server:
    networks:
      - external-network
```

## Management Scripts

### Helper Script Usage

The `scripts/docker-run.sh` script provides convenient management:

```bash
# Build operations
./scripts/docker-run.sh build               # Build images
./scripts/docker-run.sh build --no-cache    # Build without cache

# Run operations  
./scripts/docker-run.sh prod               # Production server
./scripts/docker-run.sh dev                # Development server
./scripts/docker-run.sh sse --port 8080    # SSE server on port 8080
./scripts/docker-run.sh test               # Run tests

# Management operations
./scripts/docker-run.sh status             # Show container status
./scripts/docker-run.sh logs               # Show logs
./scripts/docker-run.sh logs dev           # Show dev server logs
./scripts/docker-run.sh shell              # Get shell access
./scripts/docker-run.sh clean              # Cleanup resources
```

### Custom Scripts

Create custom deployment scripts:

```bash
#!/bin/bash
# deploy.sh - Custom deployment script

set -e

echo "🚀 Deploying Lootly..."

# Build latest image
./scripts/docker-run.sh build

# Run tests
./scripts/docker-run.sh test

# Deploy to production
docker compose -f docker-compose.production.yml up -d

# Verify deployment
sleep 10
if docker compose -f docker-compose.production.yml ps | grep -q "Up"; then
    echo "✅ Deployment successful"
else
    echo "❌ Deployment failed"
    exit 1
fi
```

## Monitoring and Logging

### Health Checks

Configure health checks for reliability:

```yaml
healthcheck:
  test: ["CMD", "python", "-c", "from lootly_server import create_lootly_server; create_lootly_server()"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s
```

### Log Management

**Structured Logging**:
```yaml
services:
  lootly-server:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

**External Log Aggregation**:
```yaml
services:
  lootly-server:
    logging:
      driver: syslog
      options:
        syslog-address: "tcp://loghost:514"
        tag: "lootly-server"
```

### Metrics Collection

```yaml
# Add metrics endpoint
services:
  lootly-server:
    environment:
      - ENABLE_METRICS=true
      - METRICS_PORT=9090
    ports:
      - "9090:9090"
```

## Security Considerations

### Credential Management

**Docker Secrets**:
```yaml
secrets:
  ebay_credentials:
    file: ./secrets/ebay.env

services:
  lootly-server:
    secrets:
      - ebay_credentials
    environment:
      - EBAY_CREDENTIALS_FILE=/run/secrets/ebay_credentials
```

**Environment File Security**:
```bash
# Secure permissions
chmod 600 .env
chown root:root .env

# Use separate credentials file
echo "EBAY_APP_ID=secret" > /secure/path/ebay.env
chmod 400 /secure/path/ebay.env
```

### Network Security

**Firewall Rules**:
```bash
# Only allow necessary ports
ufw allow 8000/tcp  # SSE transport
ufw deny 22/tcp     # SSH if not needed
```

**TLS/SSL Configuration**:
```yaml
services:
  nginx:
    image: nginx
    ports:
      - "443:443"
    volumes:
      - ./ssl:/etc/nginx/ssl
      - ./nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - lootly-server
```

## Troubleshooting

### Common Issues

**Container Won't Start**:
```bash
# Check logs
docker compose logs lootly-server

# Check configuration
docker compose config

# Verify image
docker images | grep lootly
```

**API Connection Issues**:
```bash
# Test API connectivity from container
docker compose exec lootly-server python -c "
import os
print('App ID:', os.getenv('EBAY_APP_ID', 'Not set'))
print('Sandbox:', os.getenv('EBAY_SANDBOX_MODE', 'Not set'))
"
```

**Performance Issues**:
```bash
# Check resource usage
docker stats lootly-server

# Check container limits
docker inspect lootly-server | grep -A 10 "Memory\|Cpu"
```

**Integration Test Failures**:
```bash
# Run integration tests with debug
EBAY_RUN_INTEGRATION_TESTS=true \
LOOTLY_LOG_LEVEL=DEBUG \
./scripts/docker-run.sh test
```

### Debug Mode

Enable debug mode for troubleshooting:

```bash
# Development debug mode
LOOTLY_DEBUG_MODE=true \
LOOTLY_LOG_LEVEL=DEBUG \
./scripts/docker-run.sh dev

# Get shell access for debugging
./scripts/docker-run.sh shell dev
```

This deployment guide covers all aspects of running Lootly in containerized environments, from local development to production deployment with proper monitoring and security considerations.