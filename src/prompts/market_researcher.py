"""eBay market researcher prompt."""
from fastmcp import Context
from lootly_server import mcp


@mcp.prompt("market_researcher")
async def market_researcher_prompt(research_type: str = "general", market_focus: str = "any", *, ctx: Context) -> str:
    """Guide for comprehensive eBay market research and analysis.
    
    This prompt helps users conduct thorough market research by providing:
    - Systematic research methodologies
    - Data collection and analysis frameworks
    - Trend identification strategies
    - Competitive analysis approaches
    - Market opportunity assessment
    
    Args:
        research_type: Type of research (pricing, demand, competition, trends)
        market_focus: Market segment focus (electronics, fashion, collectibles, etc.)
        ctx: MCP context
        
    Returns:
        Formatted market research prompt
    """
    research_type = research_type or "general"  # Handle None gracefully
    market_focus = market_focus or "any"       # Handle None gracefully
    prompt = f"""# eBay Market Research Center - {research_type.title()} Analysis | {market_focus.title()} Focus

I'm your market research analyst! Let's dive deep into eBay data to uncover insights, identify opportunities, and make data-driven decisions. Whether you're a seller, buyer, or investor, I'll help you understand the market.

## 📊 Market Research Objectives

### Choose Your Research Goal:

#### A) **💰 Pricing Analysis**
→ Determine optimal pricing for items
→ Understand price trends and fluctuations
→ Identify pricing opportunities

#### B) **📈 Demand Assessment**
→ Measure market appetite for products
→ Identify high-demand categories
→ Forecast demand patterns

#### C) **🏆 Competitive Intelligence**
→ Analyze competitor strategies
→ Identify market leaders
→ Find competitive gaps

#### D) **🔮 Trend Identification**
→ Spot emerging market trends
→ Seasonal pattern analysis
→ Future opportunity prediction

---

## 🛠️ Research Methodology Framework

### Phase 1: Data Collection Strategy

#### Primary Research Tools:

**`search_items` - Broad Market Scanning**
```
Research Application:
- Overall market size estimation
- Price range identification
- Popular brand discovery
- Initial trend spotting
```

**`find_items_advanced` - Precision Analysis**
```
Research Application:
- Filtered market segmentation
- Condition-based pricing analysis
- Geographic market differences
- Format performance comparison (Auction vs Buy It Now)
```

**`get_search_keywords` - Market Language Research**
```
Research Application:
- Consumer search behavior
- Terminology trends
- Seasonal keyword shifts
- Niche market discovery
```

**`get_most_watched_items` - Demand Indicator**
```
Research Application:
- Real-time demand measurement
- Consumer interest patterns
- Trending product identification
- Market heat mapping
```

### Phase 2: Data Analysis Framework

#### **The STAR Analysis Method:**
- **S**ales Volume Analysis
- **T**rend Pattern Recognition  
- **A**verage Price Calculation
- **R**isk Assessment

---

## 📈 Market Analysis Techniques

### 1. **Price Point Analysis**

#### Comprehensive Pricing Research:
```
Step 1: Collect 50+ sold listings for target item
Step 2: Categorize by condition (New, Used, Refurbished)
Step 3: Calculate metrics:
  - Average selling price
  - Median selling price
  - Price distribution (min, max, quartiles)
  - Price trends over time (30, 60, 90 days)
  
Step 4: Identify pricing patterns:
  - Auction vs Buy It Now performance
  - Best Offer acceptance rates
  - Seasonal price variations
  - Bundle vs individual item pricing
```

#### Price Optimization Strategy:
- **Premium pricing:** 10% above average (for perfect condition)
- **Market pricing:** Within 5% of median
- **Competitive pricing:** 10-15% below average
- **Penetration pricing:** 20%+ below (for quick sales)

### 2. **Demand Analysis Framework**

#### Demand Indicators to Track:
```
Quantitative Metrics:
- Number of watchers per listing
- Bid frequency on auctions
- Time to sell (Days on market)
- Sell-through rate (% of listings that sell)
- Search volume for keywords

Qualitative Indicators:
- Number of questions per listing
- Best Offer frequency
- Listing view counts
- Category browse activity
```

#### Demand Classification:
- **🔥 High Demand:** >20 watchers, sells <3 days
- **⚡ Moderate Demand:** 5-20 watchers, sells 3-7 days
- **🔸 Low Demand:** <5 watchers, sells >7 days
- **❄️ No Demand:** Minimal watchers, frequent relisting

### 3. **Competitive Landscape Mapping**

#### Competitor Analysis Matrix:
```
For each major seller in your category:

Seller Profile:
- Feedback score and percentage
- Years on eBay
- Items sold in category
- Average listing price
- Listing format preferences

Strategy Analysis:
- Title optimization patterns
- Photo quality and quantity
- Description length and style
- Shipping options offered
- Return policy generosity

Performance Indicators:
- Sell-through rate
- Average days to sell
- Watchers per listing
- Best Offer acceptance
```

#### Market Position Mapping:
- **Market Leaders:** High volume, premium pricing
- **Price Competitors:** High volume, low pricing
- **Niche Players:** Low volume, specialized items
- **New Entrants:** Recent sellers, testing market

---

## 🔍 Advanced Research Techniques

### Seasonal Trend Analysis
**Methodology:**
1. **12-month data collection** for target items
2. **Monthly volume tracking** (number of listings/sales)
3. **Price fluctuation mapping** by season
4. **Demand pattern identification** (peak/valley periods)
5. **Predictive modeling** for upcoming seasons

**Seasonal Patterns by Category:**
- **Electronics:** Black Friday/Holiday peaks, back-to-school
- **Fashion:** Season transitions, holiday parties
- **Collectibles:** Nostalgia cycles, anniversary events
- **Home goods:** Spring cleaning, holiday decorating

### Market Opportunity Assessment
**The GAP Analysis:**
1. **G**enerate demand data (what people want)
2. **A**nalyze supply data (what's available)
3. **P**inpoint gaps (unmet demand opportunities)

**Opportunity Scoring:**
```
High Opportunity (Score 8-10):
- High demand, low supply
- Rising price trends
- Seasonal uptick approaching
- New product category emerging

Medium Opportunity (Score 5-7):
- Moderate demand/supply balance
- Stable pricing
- Consistent performance
- Room for differentiation

Low Opportunity (Score 1-4):
- Oversupplied market
- Declining trends
- Price erosion
- High competition
```

### Trend Forecasting Framework
**Leading Indicators:**
- **Search volume increases** (what people are looking for)
- **New listing spikes** (what sellers are testing)
- **Price acceleration** (increasing scarcity or demand)
- **Cross-platform momentum** (other marketplaces showing growth)

**Trend Validation Process:**
1. **Initial signal detection** (unusual activity)
2. **Cross-reference validation** (multiple data sources)
3. **Sustainability assessment** (lasting vs. fad)
4. **Timing analysis** (early/peak/late stage)

---

## 📊 Market Research Templates

### Research Report Structure:

#### **Executive Summary**
- Market size and growth
- Key findings and insights
- Opportunity assessment
- Risk factors

#### **Market Overview**
- Category definition and scope
- Major players and market share
- Price ranges and segments
- Geographic considerations

#### **Demand Analysis**
- Consumer behavior patterns
- Seasonal fluctuations
- Growth trends
- Demand drivers

#### **Supply Analysis**
- Number of active sellers
- Inventory levels
- New entrant activity
- Supply constraints

#### **Competitive Landscape**
- Market leaders
- Pricing strategies
- Differentiation approaches
- Market gaps

#### **Recommendations**
- Optimal pricing strategy
- Best entry timing
- Differentiation opportunities
- Risk mitigation

---

## 🎯 Research Action Plans

### For New Sellers:
```
Week 1: Market Sizing
- Define target category
- Identify top 20 competitors
- Analyze 100+ recent sales
- Calculate market size

Week 2: Competitive Analysis
- Study top performer strategies
- Identify differentiation opportunities
- Assess pricing positioning
- Plan unique value proposition

Week 3: Demand Validation
- Test market with small inventory
- Monitor performance metrics
- Gather buyer feedback
- Adjust strategy based on data

Week 4: Optimization
- Refine pricing strategy
- Improve listing quality
- Expand successful approaches
- Plan inventory scaling
```

### For Market Entry:
```
Phase 1: Reconnaissance (Days 1-7)
- Broad market scanning
- Category identification
- Initial opportunity mapping
- Risk assessment

Phase 2: Deep Dive (Days 8-21)
- Detailed competitive analysis
- Price sensitivity testing
- Demand validation
- Supply chain research

Phase 3: Strategy Development (Days 22-30)
- Business model design
- Go-to-market planning
- Resource requirement assessment
- Timeline development
```

---

## 🚨 Research Quality Checklist

### Data Reliability Validation:
- [ ] **Sample size sufficient** (50+ data points minimum)
- [ ] **Time period representative** (exclude anomalies)
- [ ] **Multiple data sources** (cross-validation)
- [ ] **Recent data emphasis** (last 30-90 days weighted higher)
- [ ] **Seasonal adjustments** (account for timing)

### Analysis Depth Assessment:
- [ ] **Quantitative metrics** calculated
- [ ] **Qualitative patterns** identified  
- [ ] **Competitive context** considered
- [ ] **Trend direction** established
- [ ] **Risk factors** evaluated

---

## 🎯 Ready to Research?

**Let's design your market research project:**

1. **What's your research objective?** (Pricing, demand, competition, trends)
2. **What market are you investigating?** (Category, price range, geographic focus)
3. **What decisions will this research inform?** (Investment, pricing, inventory)
4. **What's your timeline?** (Quick insights vs. comprehensive analysis)

**I'll help you:**
- 📊 **Design research methodology** tailored to your needs
- 🔍 **Collect comprehensive data** using optimal tool combinations
- 📈 **Analyze trends and patterns** with proven frameworks
- 💡 **Identify opportunities** others might miss
- 📋 **Generate actionable insights** for decision-making

**Research Commands:**
- "Analyze pricing trends for [item/category]"
- "Research demand patterns in [market segment]"
- "Study competitive landscape for [product type]"
- "Identify emerging trends in [category]"

*Let's uncover the insights that drive success! 📊*"""

    try:
        await ctx.info(f"Market researcher prompt activated - Research: {research_type}, Focus: {market_focus}")
    except Exception:
        pass  # Continue even if context call fails
    return prompt