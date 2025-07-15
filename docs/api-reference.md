# API Reference

Complete reference for all Lootly tools, resources, and prompts available through the MCP interface.

## Tools (Actions)

Tools are functions that LLMs can call to perform actions. All tools return standardized JSON responses and handle errors gracefully.

### Finding API Tools

Search and discover eBay items with advanced filtering capabilities.

#### `search_items`
Search eBay items with keywords and filters.

**Parameters:**
- `keywords` (string): Search terms
- `category_id` (string, optional): eBay category ID  
- `min_price` (float, optional): Minimum price
- `max_price` (float, optional): Maximum price
- `condition` (string, optional): Item condition ("new", "used", "refurbished")
- `sort_order` (string, optional): Sort results ("BestMatch", "PricePlusShipping", "EndTimeSoonest")
- `max_results` (int, optional): Number of results (1-100, default: 20)

**Example:**
```json
{
  "keywords": "vintage camera",
  "min_price": 50,
  "max_price": 200,
  "condition": "used",
  "max_results": 10
}
```

#### `get_search_keywords`
Get keyword suggestions for search optimization.

**Parameters:**
- `query` (string): Base search term

#### `find_items_by_category`
Browse items within a specific category.

**Parameters:**
- `category_id` (string): eBay category ID
- `max_results` (int, optional): Number of results (default: 20)
- `sort_order` (string, optional): Sort method

#### `find_items_advanced`
Advanced search with multiple filter criteria.

**Parameters:**
- `keywords` (string): Search terms
- `filters` (object): Advanced filter criteria
- `max_results` (int, optional): Number of results

### Shopping API Tools

Access public eBay data for items and sellers.

#### `get_single_item`
Get detailed information for a specific item.

**Parameters:**
- `item_id` (string): eBay item ID
- `include_selector` (string, optional): Additional data to include

#### `get_item_status`
Check current status, pricing, and availability.

**Parameters:**
- `item_id` (string): eBay item ID

#### `get_shipping_costs`
Calculate shipping costs for an item.

**Parameters:**
- `item_id` (string): eBay item ID
- `country_code` (string, optional): Destination country (default: "US")
- `postal_code` (string, optional): Destination postal code

#### `get_multiple_items`
Get information for multiple items at once.

**Parameters:**
- `item_ids` (array): List of eBay item IDs (max 20)

#### `find_products`
Search eBay product catalog.

**Parameters:**
- `query` (string): Search query
- `max_results` (int, optional): Number of results

### Trading API Tools

Manage eBay listings and seller account (requires Trading API credentials).

#### `get_my_ebay_selling`
View your active, sold, and unsold listings.

**Parameters:**
- `listing_type` (string): Type of listings ("active", "sold", "unsold")
- `max_results` (int, optional): Number of results

#### `create_listing`
Create a new eBay listing.

**Parameters:**
- `title` (string): Listing title
- `description` (string): Item description
- `category_id` (string): eBay category ID
- `start_price` (float): Starting price
- `buy_it_now_price` (float, optional): Buy It Now price
- `duration` (string): Listing duration ("Days_3", "Days_5", "Days_7", "Days_10")
- `condition` (string): Item condition
- `pictures` (array, optional): Picture URLs

#### `revise_listing`
Update an existing listing.

**Parameters:**
- `item_id` (string): eBay item ID
- `title` (string, optional): New title
- `description` (string, optional): New description
- `price` (float, optional): New price

#### `end_listing`
End a listing early.

**Parameters:**
- `item_id` (string): eBay item ID
- `reason` (string): Reason for ending ("NotAvailable", "LostOrBroken", "Incorrect", "OtherListingError")

#### `get_user_info`
Get user account information.

**Parameters:**
- `user_id` (string, optional): User ID to look up (defaults to authenticated user)

### Merchandising API Tools

Discover trending and related items.

#### `get_most_watched_items`
Find the most watched items by category.

**Parameters:**
- `category_id` (string, optional): Category to search in
- `max_results` (int, optional): Number of results (1-100, default: 20)

#### `get_similar_items`
Find items similar to a given item.

**Parameters:**
- `item_id` (string): Reference item ID
- `max_results` (int, optional): Number of results

#### `get_related_category_items`
Get items from related categories.

**Parameters:**
- `category_id` (string): Base category ID
- `max_results` (int, optional): Number of results

#### `get_top_selling_products`
Browse top selling products by category.

**Parameters:**
- `category_id` (string, optional): Category to search in
- `max_results` (int, optional): Number of results

## Resources (Read-only Data)

Resources provide structured data accessible via URIs. They work without API credentials using curated static data.

### Category Resources

#### `ebay://categories`
Complete eBay category hierarchy.

**Response:** List of major categories with IDs, names, and child indicators.

#### `ebay://categories/popular`
Most active and trending categories.

**Response:** Popular categories with activity indicators and recommendations.

#### `ebay://categories/{category_id}`
Detailed information for a specific category.

**Parameters:**
- `category_id`: eBay category ID

**Response:** Category details, subcategories, and search tips.

#### `ebay://categories/{category_id}/children`
Subcategories for a given category.

**Parameters:**
- `category_id`: Parent category ID

#### `ebay://categories/{category_id}/search_tips`
Search optimization tips for a category.

**Parameters:**
- `category_id`: Category ID

### Shipping Resources

#### `ebay://shipping/rates`
Complete shipping service information and cost estimates.

**Response:** All shipping services with rates, delivery times, and warnings.

#### `ebay://shipping/rates/domestic`
US domestic shipping options.

**Response:** Domestic services with cost ranges and delivery estimates.

#### `ebay://shipping/rates/international`
International shipping services.

**Response:** International options with country restrictions and costs.

#### `ebay://shipping/rates/carrier/{carrier_name}`
Carrier-specific shipping information.

**Parameters:**
- `carrier_name`: Shipping carrier (ups, fedex, usps, dhl)

### Policy Resources

#### `ebay://policies`
All seller policy templates and best practices.

**Response:** Complete policy templates for returns, payments, and shipping.

#### `ebay://policies/return`
Return policy templates.

**Response:** Return policy options with legal compliance notes.

#### `ebay://policies/payment`
Payment policy templates.

**Response:** Payment terms and method recommendations.

#### `ebay://policies/shipping`
Shipping policy templates.

**Response:** Shipping policy examples with handling time guidelines.

### Market Trend Resources

#### `ebay://market/trends`
Comprehensive market analysis and insights.

**Response:** Market trends, seasonal patterns, and growth categories.

#### `ebay://market/trends/seasonal`
Current seasonal trends and opportunities.

**Response:** Season-specific trends based on current date.

#### `ebay://market/trends/categories`
Category growth trends and emerging markets.

**Response:** Growth categories and market opportunities.

#### `ebay://market/trends/pricing`
Pricing trends and competitive analysis.

**Response:** Price movement data and competitive insights.

#### `ebay://market/trends/opportunities`
Current market opportunities.

**Response:** Trending opportunities based on market phase and season.

## Prompts (Guided Workflows)

Prompts provide structured conversation templates for complex tasks.

### `item_search_assistant_prompt`
Helps users find the right items with guided search optimization.

**Parameters:**
- `name` (string, optional): User's name for personalization

**Use Case:** Guiding users through effective eBay searches with filters and keywords.

### `listing_optimizer_prompt`
Provides expert guidance for improving listing quality and visibility.

**Parameters:**
- `item_type` (string, optional): Type of item being listed

**Use Case:** Optimizing titles, descriptions, categories, and pricing for better sales.

### `deal_finder_prompt`
Assists in discovering underpriced items and market opportunities.

**Parameters:**
- `budget` (float, optional): User's budget
- `interests` (string, optional): Areas of interest

**Use Case:** Finding bargains, auctions ending soon, and mispriced items.

### `market_researcher_prompt`
Guides comprehensive market analysis and competitive research.

**Parameters:**
- `market_focus` (string, optional): Specific market or category to analyze

**Use Case:** Analyzing competition, pricing strategies, and market trends.

## Response Format

All tools return standardized JSON responses:

```json
{
  "status": "success|error|warning|partial",
  "data": { /* tool-specific data */ },
  "message": "Human-readable message",
  "metadata": {
    "timestamp": "2024-01-01T12:00:00Z",
    "cache_ttl": 300,
    "api_available": true
  }
}
```

## Error Handling

Common error codes and responses:

- **VALIDATION_ERROR**: Invalid input parameters
- **EXTERNAL_API_ERROR**: eBay API issues
- **PERMISSION_DENIED**: Insufficient credentials
- **RATE_LIMIT_EXCEEDED**: API rate limits hit
- **RESOURCE_NOT_FOUND**: Item or resource not found
- **CONFIGURATION_ERROR**: Server configuration issues

## Rate Limits

eBay API limits (per application per day):
- **Finding API**: 5,000 calls
- **Shopping API**: 5,000 calls  
- **Trading API**: 5,000 calls
- **Merchandising API**: 200,000 calls

Lootly implements intelligent caching to minimize API usage while providing fresh data.