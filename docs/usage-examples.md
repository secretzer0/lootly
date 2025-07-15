# Usage Examples

Real-world scenarios and workflows showing how to use Lootly's eBay integration effectively.

## Search & Discovery Workflows

### Finding Specific Items

**Scenario**: Looking for a specific vintage camera model within budget

```
User: I'm looking for a vintage Nikon F camera under $300

Claude (using Lootly):
search_items("vintage Nikon F camera", max_price=300, condition="used")

Results: Found 15 vintage Nikon F cameras under $300
- 1972 Nikon F with 50mm lens - $275 (Good condition)
- 1971 Nikon F body only - $220 (Excellent condition)  
- 1973 Nikon F with case - $290 (Very good condition)
```

**Follow-up Search Optimization**:
```
User: Can you suggest better keywords for this search?

Claude: get_search_keywords("vintage Nikon F camera")

Suggestions: "Nikon F body", "Nikon F SLR", "vintage Nikon camera", "Nikon F film camera"
```

### Category Exploration

**Scenario**: Browsing a category to understand what's available

```
User: What's available in the Electronics category on eBay?

Claude: Let me show you the Electronics category structure:

Resource: ebay://categories/293

Electronics Category (293):
- Computers/Tablets & Networking (58058)
- Consumer Electronics (293)
- Video Games & Consoles (131090)
- Cell Phones & Accessories (9355)

Popular subcategories:
- Gaming laptops are trending
- Vintage electronics showing high interest
- Smart home devices growing rapidly
```

### Trending Item Discovery

**Scenario**: Finding what's popular right now

```
User: What items are most watched in Electronics?

Claude: get_most_watched_items(category_id="293", max_results=10)

Most Watched Electronics:
1. iPhone 15 Pro Max - 1,247 watchers
2. PlayStation 5 Console - 892 watchers
3. MacBook Air M2 - 734 watchers
4. Nintendo Switch OLED - 623 watchers
5. Samsung Galaxy S24 Ultra - 567 watchers
```

## Market Intelligence Workflows

### Seasonal Market Analysis

**Scenario**: Understanding current market opportunities

```
User: What are the best selling opportunities right now?

Claude: Let me analyze current market trends:

Resource: ebay://market/trends/seasonal

Current Season: Winter (December-February)
Market Phase: Post-Holiday

Top Opportunities:
🔥 Winter Sports Equipment (+45% demand)
📱 Refurbished Electronics (+30% as people upgrade holiday gifts)
🏠 Home Organization (+25% New Year decluttering)
🎮 Gaming Accessories (+20% holiday gift money spending)
💎 Vintage Collectibles (+15% investment mindset)

Seasonal Insights:
- Electronics see price dips in January
- Outdoor gear preparing for spring activities
- Home improvement projects increase
```

### Category Growth Analysis

**Scenario**: Identifying growing market segments

```
User: Which eBay categories are growing fastest?

Claude: Resource: ebay://market/trends/categories

Fastest Growing Categories (6-month trend):
1. **Collectible Card Games** (+78%)
   - Pokémon cards leading growth
   - Vintage sports cards strong
   
2. **Sustainable Fashion** (+65%)
   - Vintage clothing revival
   - Eco-friendly brands popular
   
3. **Home Automation** (+52%)
   - Smart security systems
   - Energy efficiency products
   
4. **Electric Vehicle Accessories** (+48%)
   - Charging equipment
   - EV maintenance tools
```

### Pricing Analysis

**Scenario**: Understanding price trends for investment decisions

```
User: How have smartphone prices changed recently?

Claude: Resource: ebay://market/trends/pricing

Smartphone Price Trends (Last 3 months):

📱 **iPhone Models**:
- iPhone 14: -12% (New model release effect)
- iPhone 13: -8% (Stable demand)
- iPhone 12: -15% (Moving to budget tier)

📱 **Android Flagship**:
- Samsung Galaxy S23: -10%
- Google Pixel 7: -18%
- OnePlus devices: -22%

📊 **Market Insights**:
- Best buying time: January-February (post-holiday dips)
- Price recovery: March-April (spring refresh)
- New release impact: 10-20% price drops on previous models
```

## Seller Optimization Workflows

### Listing Optimization

**Scenario**: Improving a poorly performing listing

```
User: Help me optimize my vintage watch listing

Claude: I'll use the listing optimizer to help improve your listing.

Prompt: listing_optimizer_prompt(item_type="vintage watch")

# 🔧 eBay Listing Optimizer for Vintage Watches

Let's optimize your vintage watch listing for maximum visibility and sales!

## Current Listing Analysis Needed:
1. What's your current title?
2. Which category is it listed in?
3. What's your current price point?
4. How many photos do you have?

## Optimization Areas:

### Title Optimization:
✅ Include: Brand, Model, Year, Condition, Key Features
❌ Avoid: Generic terms, excessive capitalization, irrelevant keywords

### Category Selection:
Resource: ebay://categories/281 (Jewelry & Watches)
- Vintage watches: Category 281
- Luxury brands have specific subcategories
- Pocket watches: Separate category

### Pricing Strategy:
Tool: search_items("similar vintage watch model")
- Research completed sales
- Consider auction vs Buy It Now
- Factor in condition and rarity
```

### Market Positioning

**Scenario**: Pricing a collectible item competitively

```
User: I have a 1985 Transformer toy. How should I price it?

Claude: Let me analyze the market for 1985 Transformers:

search_items("1985 Transformer toy", condition="used")

Current Market (1985 Transformers):
- **Optimus Prime G1**: $150-$400 (condition dependent)
- **Megatron G1**: $120-$350  
- **Starscream**: $80-$200
- **Soundwave**: $100-$250

Pricing Factors:
✅ **Condition Impact**: Mint in package (+200-300%)
✅ **Completeness**: All accessories (+50-100%)
✅ **Packaging**: Original box (+75-150%)
✅ **Rarity**: Limited editions (+100-500%)

Recommendation:
1. Identify exact model and year
2. Check completeness (all parts/accessories)
3. Assess condition honestly
4. Research recent sold listings
5. Consider auction for rare items
```

## Deal Finding Workflows

### Bargain Hunting

**Scenario**: Finding underpriced items for resale

```
User: Help me find good deals in vintage electronics

Claude: I'll use the deal finder to help you locate bargains!

Prompt: deal_finder_prompt(interests="vintage electronics")

# 💰 eBay Deal Finder for Vintage Electronics

Let's hunt for underpriced vintage electronics with resale potential!

## Search Strategies:

### Misspelling Opportunities:
search_items("vintag electronic") // Common misspellings get fewer bids
search_items("electroincs vintage") // Transposed letters
search_items("retro electronic") // Alternative terms

### Auction Timing:
- Auctions ending during weekday work hours
- Holiday weekend endings (fewer bidders)
- Early morning or late night endings

### Category Crossovers:
- Electronics listed in wrong categories
- Vintage items in modern categories
- Lot sales with hidden gems
```

### Auction Sniping Opportunities

**Scenario**: Finding auctions ending soon with low bids

```
User: Show me auctions for vintage cameras ending soon

Claude: search_items("vintage camera", listing_type="auction", sort_order="EndTimeSoonest")

Auctions Ending Soon:
🕐 **2 hours left**: 1965 Leica M2 - Current bid: $85 (Est. value: $800-1200)
🕐 **4 hours left**: Nikon F Photomic - Current bid: $45 (Est. value: $200-350)  
🕐 **6 hours left**: Canon AE-1 kit - Current bid: $25 (Est. value: $150-250)

⚠️ **Sniping Tips**:
- Research sold listings for true value
- Set maximum bid based on resale potential
- Account for condition issues in photos
- Consider shipping costs in calculations
```

## Research & Analysis Workflows

### Competitive Analysis

**Scenario**: Analyzing competition for a product category

```
User: I want to sell handmade jewelry. What's the competition like?

Claude: Let me analyze the handmade jewelry market:

Prompt: market_researcher_prompt(market_focus="handmade jewelry")

# 📊 Market Research: Handmade Jewelry

## Market Overview:
search_items("handmade jewelry", max_results=100)

**Competition Analysis**:
- 45,000+ active listings
- Price range: $5-$500+ 
- Top categories: Necklaces (35%), Earrings (28%), Bracelets (22%)

**Successful Seller Patterns**:
✅ High-quality photography (professional lighting)
✅ Detailed descriptions (materials, dimensions, care)
✅ Story/craftsmanship focus
✅ Competitive pricing ($15-75 sweet spot)
✅ Fast shipping (1-2 business days)

**Market Gaps**:
🎯 Men's handmade jewelry (underserved)
🎯 Sustainable/recycled materials (growing trend)  
🎯 Custom/personalized pieces (premium pricing)
🎯 Minimalist modern designs (high demand)
```

### Trend Analysis

**Scenario**: Identifying emerging trends for investment

```
User: What collectibles are trending up right now?

Claude: Resource: ebay://market/trends/opportunities

🚀 **Emerging Collectible Trends**:

**Hot Right Now**:
1. **Pokémon 25th Anniversary** (+156% price increase)
   - Japanese exclusive cards
   - Graded PSA 10 condition premium
   
2. **90s Tech Nostalgia** (+89% interest)
   - Original Game Boys
   - Vintage Apple computers
   - Early gaming consoles

3. **Sustainable Collectibles** (+67% growth)
   - Eco-friendly vintage items
   - Upcycled furniture
   - Vintage outdoor gear

**Investment Signals**:
📈 Increasing search volume
📈 Rising completed sale prices  
📈 Celebrity/influencer mentions
📈 Anniversary/milestone years
```

## Advanced Integration Workflows

### Multi-Tool Research

**Scenario**: Comprehensive product research combining multiple tools

```
User: I'm considering selling vintage vinyl records. Give me a complete market analysis.

Claude: I'll conduct comprehensive vinyl record market research:

Step 1 - Category Analysis:
Resource: ebay://categories/306 (Music)
- Vinyl Records: Category 176985
- Rock, Jazz, Classical, Electronic subcategories

Step 2 - Current Market:
search_items("vintage vinyl records", max_results=50)
- Average price: $15-45 per record
- Premium items: $100-500+ (rare pressings)
- High volume: Classic rock, jazz standards

Step 3 - Trending Items:
get_most_watched_items(category_id="176985")
- The Beatles - Abbey Road (50th Anniversary): $89
- Pink Floyd - Dark Side of the Moon (Original): $156
- Miles Davis - Kind of Blue (Blue Note): $234

Step 4 - Market Insights:
Resource: ebay://market/trends/categories
- Vinyl market growing 23% annually
- Audiophile equipment driving demand
- Generation Z discovering analog music

Step 5 - Pricing Strategy:
- Research pressing variations (original vs reissue)
- Condition critical (Mint/NM commands premium)
- Rare labels (Blue Note, Prestige) valuable
- Test pressings and promo copies premium items
```

### Cross-Reference Validation

**Scenario**: Validating item authenticity and value

```
User: I found a "rare" 1952 Mickey Mantle rookie card. How do I verify its value?

Claude: Let me help you authenticate and value this card:

Step 1 - Market Research:
search_items("1952 Mickey Mantle rookie card")
Recent Sales:
- PSA 10: $12.6M (record sale)
- PSA 9: $5.2M  
- PSA 8: $2.88M
- PSA 7: $1.4M
- Ungraded: $50K-500K (condition dependent)

Step 2 - Authentication Resources:
Resource: ebay://policies/authentication
- eBay Authentication required for cards >$2,000
- Professional grading recommended (PSA, BGS, SGC)
- Look for: centering, corners, edges, surface quality

Step 3 - Red Flags:
⚠️ Too-good-to-be-true pricing
⚠️ Seller with limited feedback
⚠️ Poor quality photos
⚠️ No mention of reprints/reproductions
⚠️ Unusual card stock or printing

Recommendation: Given the card's extreme value, professional authentication is essential before any transaction.
```

## Shipping & Logistics

### Shipping Cost Analysis

**Scenario**: Understanding shipping implications for large items

```
User: I want to sell a vintage pinball machine. What should I know about shipping?

Claude: Resource: ebay://shipping/rates/large-items

**Large Item Shipping Analysis**:

📦 **Pinball Machine Shipping**:
- Weight: 250-300 lbs typically
- Dimensions: 6'×3'×6' average
- Freight shipping required

💰 **Cost Estimates**:
- Local delivery: $100-200
- Regional (500 miles): $300-500  
- Cross-country: $800-1,500
- White glove service: +$200-400

⚠️ **Important Considerations**:
- Buyer typically pays shipping
- Professional packaging required
- Insurance recommended (high value)
- Pickup/delivery coordination needed
- Some buyers prefer local pickup

**Listing Strategy**:
✅ Offer local pickup discount
✅ Partner with freight companies
✅ Provide detailed packaging process
✅ Include shipping calculator
✅ Set handling time realistically (5-7 days)
```

These examples demonstrate how Lootly's tools, resources, and prompts work together to provide comprehensive eBay marketplace intelligence. The AI assistant can seamlessly combine different components to deliver valuable insights and actionable recommendations for users at any experience level.