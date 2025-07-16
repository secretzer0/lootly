# eBay API Testing Scripts

These scripts help test the eBay API integration with real credentials and tokens.
The system now uses **inline policies** instead of Business Policies for easier setup.

## Prerequisites

1. Set up your `.env` file with eBay API credentials:
   ```bash
   EBAY_APP_ID=your-app-id
   EBAY_CERT_ID=your-cert-id
   EBAY_DEV_ID=your-dev-id
   EBAY_SANDBOX_MODE=true  # or false for production
   ```

2. Make sure you have the project dependencies installed:
   ```bash
   uv sync
   ```

## OAuth Consent Flow

For APIs that require user consent (Account, Inventory), use the MCP tools directly:

### Step 1: Use the MCP OAuth Tools

The OAuth consent flow is now integrated into the main MCP tools:

1. **Check consent status**: Use `check_user_consent_status` tool
2. **Initiate consent**: Use `initiate_user_consent` tool (opens browser automatically if running locally)
3. **Complete consent**: Use `complete_user_consent` tool with callback URL

### Step 2: Complete Authorization

1. The `initiate_user_consent` tool will open your browser automatically (if running locally)
2. Log in to your eBay sandbox account
3. Grant the requested permissions
4. You'll be redirected to localhost (the page won't load, that's normal)
5. Copy the ENTIRE URL from your browser's address bar
6. Use `complete_user_consent` with the callback URL

## Testing APIs

### Test All APIs

```bash
# Test all APIs (including OAuth consent)
uv run python scripts/test_all_apis_real.py

# Test specific API category
uv run python scripts/test_all_apis_real.py --category=oauth      # OAuth consent flow
uv run python scripts/test_all_apis_real.py --category=browse    # Browse API
uv run python scripts/test_all_apis_real.py --category=account   # Account API
uv run python scripts/test_all_apis_real.py --category=inventory # Inventory API (with inline policies)
uv run python scripts/test_all_apis_real.py --category=taxonomy  # Taxonomy API
```

### Example: Create Listing Without Business Policies

```bash
# Shows how to create listings with inline policies
uv run python scripts/create_listing_no_policies.py
```

## Results

Test results are saved to `scripts/test_results.json` with:
- Summary of passed/failed tests
- Detailed error messages
- API response data
- Timestamps

## Troubleshooting

### "No valid token found"
Use the MCP `initiate_user_consent` and `complete_user_consent` tools to get user consent.

### "eBay credentials not found"
Make sure your `.env` file has the required credentials.

### "Access denied" errors
- Check if you're using sandbox or production mode correctly
- Verify your app has the required API access
- For sandbox, use sandbox test accounts

### Token expiration
Tokens expire after a certain time. Use the MCP OAuth tools to refresh consent.

### "Business Policy not found" errors
This system now uses **inline policies** instead of Business Policies. No need to set up Business Policies in eBay Seller Hub.

## Notes

- These scripts use **REAL API calls and REAL OAuth tokens** - no mocking!
- Sandbox environment is recommended for testing
- Uses **inline policies** for listings (payment, shipping, return terms)
- Rate limits apply to real API calls
- OAuth consent flow automatically opens browser when running locally