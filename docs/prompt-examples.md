# eBay MCP Prompt Examples

This guide provides detailed examples of how to use each MCP Prompt in Lootly. Prompts are conversation templates that guide complex eBay workflows.

## Search Assistant Prompt

The Search Assistant helps users find exactly what they're looking for on eBay through an interactive, guided process.

### Basic Usage
```
Use the eBay search assistant to help me find a laptop
```

### Example Conversation Flow
**Assistant**: I'll help you find the perfect laptop on eBay! Let me ask you a few questions to narrow down your search:

1. **Budget Range**: What's your price range? (e.g., $300-$800)
2. **Primary Use**: What will you mainly use it for?
   - General use (web, documents)
   - Gaming
   - Professional/Creative work
   - School/Student
3. **Preferences**:
   - New or Used/Refurbished acceptable?
   - Screen size preference?
   - Any specific brands?

**User**: I need a laptop for college, budget $500-$700, refurbished is fine, prefer 14-15" screen

**Assistant**: Great! Based on your requirements, I'll search for:
- Price: $500-$700
- Condition: Used/Refurbished
- Screen: 14-15"
- Keywords: "laptop college student"

*[Searches eBay and presents results with analysis]*

Here are the best matches I found:
1. **Dell Latitude 5480** - $599 (Refurbished)
   - Intel i5, 8GB RAM, 256GB SSD
   - 14" screen, great for students
   - Seller has 99.8% feedback

2. **Lenovo ThinkPad T470** - $649 (Certified Refurbished)
   - Intel i5, 16GB RAM, 512GB SSD
   - 14" screen, excellent keyboard
   - 1-year warranty included

Would you like me to check shipping costs or find similar options?

### Advanced Search Assistant Features
- Suggests related searches based on initial results
- Warns about potential issues (e.g., older models, missing accessories)
- Compares prices with current market values
- Identifies best value options

## Listing Optimizer Prompt

The Listing Optimizer helps sellers improve their eBay listings for better visibility and sales.

### Basic Usage
```
Use the listing optimizer to improve my vintage watch listing
```

### Example Optimization Session
**Assistant**: I'll help optimize your vintage watch listing! First, let me analyze what makes successful vintage watch listings on eBay.

**Current Listing Analysis**:
Please share your current title and I'll suggest improvements.

**User**: "Old Rolex Watch Mens Working"

**Assistant**: I can significantly improve this listing! Here's my optimization:

**Optimized Title** (80 characters):
"Vintage Rolex Oyster Perpetual Date Mens Watch 1970s Ref 1500 Working Original"

**Key Improvements**:
1. ✅ Added "Vintage" - crucial keyword for collectors
2. ✅ Specified model (Oyster Perpetual Date)
3. ✅ Added era (1970s) - helps with search filters
4. ✅ Included reference number - collectors search by this
5. ✅ "Original" - indicates authenticity

**Additional Optimization Tips**:
- **Photos**: Need 12+ images including:
  - Movement shot
  - Serial/reference numbers
  - Case back
  - All angles of wear
  - Papers/box if available
  
- **Description Structure**:
  ```
  AUTHENTICITY: [Details about originality]
  CONDITION: [Honest assessment with close-ups]
  SPECIFICATIONS: [Size, movement, reference]
  SERVICE HISTORY: [When last serviced]
  WHAT'S INCLUDED: [Watch, papers, box, etc.]
  ```

- **Search Keywords**: vintage, collectible, automatic, Swiss made
- **Category**: Jewelry & Watches > Watches > Wristwatches > Men's
- **Item Specifics**: Fill ALL fields (brand, model, year, etc.)

Would you like help with pricing strategy or shipping recommendations?

## Deal Finder Prompt

The Deal Finder helps buyers discover underpriced items and arbitrage opportunities.

### Basic Usage
```
Use the deal finder to find underpriced items in collectibles
```

### Example Deal Finding Session
**Assistant**: I'll help you find underpriced collectibles on eBay! Let me search for the best opportunities.

**Search Strategy**:
1. Checking newly listed items (less competition)
2. Looking for misspellings and poor listings
3. Analyzing auction endings at off-peak times
4. Comparing with completed sales data

**Found Opportunities**:

🔥 **HOT DEAL**: Pokémon Card Lot - Misspelled Listing
- Listed as: "Pokeman cards vintage lot"
- Current bid: $45 (2 watchers)
- Market value: $150-$200 based on visible cards
- Ends: 3 AM EST (low competition time)
- Risk: Medium (need to verify authenticity)

💎 **HIDDEN GEM**: Sterling Silver Coins Collection
- Poor photos but description mentions key dates
- Buy It Now: $280
- Potential value: $400-$500 if dates are correct
- Seller: New (only 3 feedback)
- Action: Ask for better photos of dates

🎯 **ARBITRAGE OPP**: LEGO Star Wars Set
- Incomplete set (missing 10 pieces)
- Current price: $120
- Complete set value: $350
- Replacement pieces cost: ~$30 on BrickLink
- Profit potential: $200

**Quick Flip Strategy**:
- Search terms that often hide deals:
  - "estate sale lot"
  - "barn find"
  - "as-is untested"
  - Common misspellings

Would you like me to set up saved searches for these opportunities?

## Market Researcher Prompt

The Market Researcher provides in-depth analysis of eBay market segments and trends.

### Basic Usage
```
Use the market researcher to analyze the smartphone market
```

### Example Market Research Report
**Assistant**: I'll conduct a comprehensive analysis of the eBay smartphone market for you.

## 📊 Smartphone Market Analysis - eBay

### Market Overview
- **Total Active Listings**: ~2.4M smartphones
- **Daily Sales Volume**: ~45,000 units
- **Average Selling Price**: $312
- **YoY Growth**: +18%

### Top Performers by Brand
1. **Apple iPhone** (42% market share)
   - iPhone 13: $650-$750 (high demand)
   - iPhone 12: $450-$550 (best value)
   - iPhone 11: $300-$400 (budget favorite)

2. **Samsung Galaxy** (28% market share)
   - S23 Series: $700-$900
   - S22 Series: $500-$650
   - A-Series: $150-$300 (volume seller)

3. **Google Pixel** (8% market share)
   - Growing segment (+35% YoY)
   - Pixel 7: $400-$500
   - Strong in refurbished market

### Seasonal Trends
- **Peak Seasons**: 
  - September-October (new iPhone launch)
  - November-December (holiday shopping)
  - January (New Year upgrades)
  
- **Low Season**: 
  - May-July (good time to buy)

### Profitable Niches
1. **Unlocked International Models** 
   - 20-30% markup potential
   - Dual-SIM models in demand

2. **Vintage/Rare Models**
   - Original iPhone: $500-$2000
   - Limited editions command premiums

3. **Bulk Lots for Parts**
   - Broken phone lots
   - $50-$200 investment
   - 3-5x return fixing/parting out

### Seller Strategies
**High-Volume Approach**:
- Focus on 1-2 generation old flagships
- Quick turnover (3-5 days)
- 15-20% margins

**Premium Approach**:
- Latest models, mint condition
- Original accessories included
- 25-30% margins but slower turnover

### Risk Factors
⚠️ **Watch Out For**:
- Carrier lock issues
- Hidden damage (especially water)
- Fake/clone devices (verify IMEI)
- Rapid depreciation on Android

**Recommendation**: Start with iPhone 11/12 series - stable demand, good margins, lower risk.

Would you like detailed sourcing strategies or competitive pricing analysis?

## Using Multiple Prompts Together

Prompts can work together for comprehensive workflows:

### Example: Complete Seller Workflow
1. **Market Researcher**: "Analyze the vintage camera market"
2. **Search Assistant**: "Help me find undervalued vintage cameras to resell"
3. **Deal Finder**: "Find vintage camera lots with profit potential"
4. **Listing Optimizer**: "Optimize my listing for this Leica camera I bought"

### Example: Smart Buyer Journey
1. **Market Researcher**: "What's the best time to buy winter sports equipment?"
2. **Search Assistant**: "Help me find ski equipment for beginners"
3. **Deal Finder**: "Find the best deals on the ski equipment we discussed"

## Pro Tips for Using Prompts

1. **Be Specific**: The more details you provide, the better the results
   - ❌ "Find me a good deal"
   - ✅ "Find underpriced vintage video games from the 1990s"

2. **Iterate**: Use follow-up questions to refine results
   - "Show me more options under $50"
   - "Focus only on items with free shipping"
   - "Exclude anything from sellers with less than 98% feedback"

3. **Combine with Resources**: Prompts automatically use Resources
   - Categories data helps with navigation
   - Shipping rates inform cost calculations
   - Market trends guide timing decisions

4. **Save Successful Searches**: When a prompt finds great results
   - Save the search on eBay
   - Set up alerts for new listings
   - Note the keywords that worked

5. **Trust the Guardrails**: Prompts include built-in protections
   - Shipping cost warnings
   - Authenticity red flags
   - Seller reputation checks
   - Market value validations

## Customizing Prompts

Each prompt accepts parameters for customization:

### Search Assistant Parameters
- `name`: Specify searcher name for personalization

### Listing Optimizer Parameters  
- `item_type`: Customize for specific product categories

### Deal Finder Parameters
- `budget`: Set maximum investment amount
- `category`: Focus on specific categories

### Market Researcher Parameters
- `research_type`: Choose analysis depth (quick/comprehensive)
- `market_focus`: Specify market segment

Example with parameters:
```
Use the deal finder with budget=$100 and category=electronics
```

This will constrain the search to electronics deals under $100, perfect for beginners or testing strategies.