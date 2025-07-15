# eBay API Limitations and Known Issues

This document describes the current limitations and known issues with the eBay APIs as implemented in the Lootly MCP server.

## Working APIs

### Finding API ✅
- **Status**: Fully functional
- **Authentication**: App ID only
- **Endpoints**: All Finding API endpoints work correctly
- **Supported Operations**:
  - `search_items` - Search for items with filters
  - `get_search_keywords` - Get keyword suggestions
  - `find_items_by_category` - Browse items by category
  - `find_items_advanced` - Advanced search with multiple filters

## APIs with Limitations

### Shopping API ⚠️
- **Status**: Authentication issues
- **Issue**: The Shopping API now requires OAuth 2.0 token authentication instead of just App ID
- **Error**: "Token not available in request"
- **Impact**: All Shopping API operations are currently non-functional
- **Affected Operations**:
  - `get_single_item`
  - `get_item_status`
  - `get_shipping_costs`
  - `get_multiple_items`
  - `find_products`

### Merchandising API ⚠️
- **Status**: Not available in sandbox, authentication issues in production
- **Issues**:
  - Sandbox returns 404 Not Found for all operations
  - Production requires CONSUMER-ID which may differ from App ID
- **Impact**: All Merchandising API operations are currently non-functional
- **Affected Operations**:
  - `get_most_watched_items`
  - `get_related_category_items`
  - `get_similar_items`
  - `get_top_selling_products`

### Trading API ⚠️
- **Status**: Requires full authentication (App ID, Cert ID, Dev ID, and User Token)
- **Issue**: Trading API requires OAuth user tokens for operations
- **Impact**: Limited to basic operations without user-specific data
- **Note**: This is by design as Trading API deals with user-specific data

## Recommendations

1. **For Item Search and Discovery**: Use the Finding API which is fully functional
2. **For Item Details**: The Shopping API limitations mean you cannot get detailed item information
3. **For Market Analysis**: The Merchandising API limitations prevent trend analysis
4. **For Selling Operations**: Trading API requires full OAuth implementation

## Future Improvements

To fully support all eBay APIs, the following would be needed:

1. **OAuth 2.0 Implementation**: Add OAuth flow for user authentication
2. **Token Management**: Implement token storage and refresh logic
3. **API Migration**: Consider migrating to eBay's newer REST APIs which have better documentation and support

## Testing

When running integration tests:
- Finding API tests should pass
- Shopping API tests will fail with authentication errors
- Merchandising API tests will fail with 404 or authentication errors
- Trading API tests require valid user tokens