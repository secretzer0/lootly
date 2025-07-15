"""eBay deal finder prompt."""
from fastmcp import Context
from lootly_server import mcp


@mcp.prompt("deal_finder")
async def deal_finder_prompt(budget: str = "flexible", category: str = "any", *, ctx: Context) -> str:
    """Guide for finding the best deals and bargains on eBay.
    
    This prompt helps users discover great deals by providing:
    - Strategic deal hunting approaches
    - Timing and auction tactics
    - Filter combinations for bargain discovery
    - Risk assessment and verification strategies
    - Category-specific deal hunting tips
    
    Args:
        budget: Budget range (tight, moderate, flexible)
        category: Product category of interest (electronics, clothing, collectibles, etc.)
        ctx: MCP context
        
    Returns:
        Formatted deal finder prompt
    """
    budget = budget or "flexible"  # Handle None gracefully
    category = category or "any"   # Handle None gracefully
    prompt = f"""# eBay Deal Hunter - {budget.title()} Budget | {category.title()} Focus

I'm your bargain hunting expert! Let's find amazing deals using proven strategies, smart timing, and the right tools. Whether you're treasure hunting or targeting specific items, I'll help you save money.

## 💰 Deal Hunting Philosophy

### The Three Pillars of Deal Finding:
1. **🕐 Timing** - When you search matters
2. **🔍 Strategy** - How you search matters  
3. **⚡ Speed** - Acting fast on deals matters

---

## 🎯 Deal Hunter's Toolkit

### Primary Tools for Bargain Hunting:

#### `find_items_advanced` - Your Power Tool
**Best for:** Precision deal hunting with multiple filters
```
Strategy: Combine price filters + condition + auction timing
- Set maximum price below market value
- Filter by ending time (auctions ending soon)
- Include "Best Offer" listings
- Sort by "Time: ending soonest"
```

#### `search_items` - Quick Discovery
**Best for:** Rapid scanning and keyword variations
```
Strategy: Try creative search terms
- Misspelled brand names ("Prada" → "Parada")
- Alternative names ("iPhone" → "i-phone")
- Generic terms ("smartphone" vs "mobile phone")
- Incomplete model numbers
```

#### `get_deals` (Merchandising API)
**Best for:** Curated deal discovery
```
Strategy: Let eBay's algorithm work for you
- Daily deal scanning
- Seasonal promotion hunting
- Featured seller discounts
- Category-specific sales
```

---

## ⏰ Strategic Timing Guide

### 🕘 Best Times to Hunt for Deals:

#### **Sunday Night Special (8-11 PM EST)**
- **Why:** Most auctions end Sunday nights
- **Strategy:** Snipe multiple auctions simultaneously
- **Tools:** `find_items_advanced` with "ending within 2 hours"
- **Risk:** High competition, set bidding limits

#### **Tuesday-Thursday Mornings**
- **Why:** Lowest competition from casual bidders
- **Strategy:** Target Buy It Now items with Best Offer
- **Tools:** `search_items` + price filtering
- **Opportunity:** Business hours = fewer bidders

#### **Holiday Aftermath (Jan 2-15, Dec 26-31)**
- **Why:** People selling Christmas gifts, clearing inventory
- **Strategy:** Search "new with tags" + "gift"
- **Categories:** Electronics, clothing, home goods
- **Bonus:** Returns season = unopened items

#### **End of Season Sales**
- **Why:** Sellers clearing seasonal inventory
- **Examples:** Winter coats (March), swimwear (September)
- **Strategy:** Search seasonal keywords + "clearance"

---

## 🔍 Advanced Deal Hunting Strategies

### The Misspelling Strategy
**Concept:** Find items with typos that fewer people discover

**Common Misspellings to Search:**
- Luxury brands: "Gucci" → "Guchi", "Louis Vuitton" → "Louis Vitton"
- Electronics: "Samsung" → "Samsumg", "Nintendo" → "Nintindo"
- Watches: "Rolex" → "Rollex", "Omega" → "Omaga"

**Implementation:**
```
1. Use `search_items` with intentional misspellings
2. Sort by "Time: ending soonest"
3. Cross-reference with correctly spelled listings
4. Identify significant price gaps
```

### The Incomplete Search Strategy
**Concept:** Search partial model numbers or generic terms

**Examples:**
- "iPhone 14" instead of "iPhone 14 Pro Max 256GB"
- "Jordan sneakers" instead of "Air Jordan 1 Retro High OG"
- "Vintage watch" instead of "1960s Omega Seamaster"

### The Auction Sniping Strategy
**Concept:** Bid in final seconds of auctions

**Best Practices:**
1. **Research first:** Know the item's market value
2. **Set hard limits:** Never exceed your maximum
3. **Multiple targets:** Bid on several similar items
4. **Timing tools:** Bid in last 10-15 seconds
5. **Internet speed:** Ensure stable connection

### The Bundle Breaking Strategy
**Concept:** Buy lots/bundles, keep what you want, sell the rest

**Process:**
1. Find bundles with one item you want + others
2. Calculate: (Bundle price ÷ Number of items) = Cost per item
3. Estimate resale value of unwanted items
4. Net cost = Bundle price - Estimated resale value

---

## 💡 Category-Specific Deal Tactics

### Electronics Deals ({category})
**Prime Opportunities:**
- **Carrier-locked phones** (unlock later)
- **Previous generation** when new models release
- **Open box items** from stores
- **Auction format** for expensive items
- **Bundle deals** (phone + case + charger)

**Red Flags:**
- No return policy on electronics
- Stock photos only
- Prices too good to be true
- New seller with high-value items

### Fashion & Clothing Deals
**Prime Opportunities:**
- **End of season** clearance
- **New with tags** returns
- **Slightly used** designer items
- **Sample sales** and overstock
- **Bulk lots** for resellers

**Key Filters:**
- Size range searches
- Brand + "new with tags"
- "Sample" or "prototype"
- Auction format for rare items

### Collectibles & Vintage Deals
**Prime Opportunities:**
- **Estate sales** and liquidations
- **Mislabeled items** in wrong categories
- **Incomplete sets** (complete them later)
- **Restoration projects** if you have skills
- **Buy It Now** items priced as "parts/repair"

**Research Requirements:**
- Know your market values
- Understand rarity and variants
- Check completed sales extensively
- Factor in restoration costs

---

## 🚨 Deal Verification Checklist

### Before You Buy:
- [ ] **Compare prices:** Check 5+ similar sold listings
- [ ] **Calculate total cost:** Item + shipping + taxes
- [ ] **Read description:** Look for hidden issues
- [ ] **Check seller:** Feedback score and recent reviews
- [ ] **Verify authenticity:** For luxury/designer items
- [ ] **Understand return policy:** Can you return if issues?
- [ ] **Payment protection:** PayPal/eBay Money Back Guarantee

### Red Flags to Avoid:
- ❌ Stock photos only (no actual item photos)
- ❌ Vague descriptions ("works great", "good condition")
- ❌ New sellers with expensive items
- ❌ Prices 50%+ below market value
- ❌ No return policy
- ❌ Immediate payment required with no feedback
- ❌ Multiple identical listings from same seller
- ❌ Poor grammar/obvious translation errors

---

## 🎲 Risk Assessment Matrix

### Low Risk Deals (Go for it!)
- ✅ Established seller (500+ feedback, 98%+)
- ✅ Detailed photos of actual item
- ✅ Price 10-30% below market
- ✅ Return policy offered
- ✅ PayPal accepted

### Medium Risk Deals (Proceed with caution)
- ⚠️ Newer seller (50-500 feedback, 95%+)
- ⚠️ Price 30-50% below market
- ⚠️ Limited photos but detailed description
- ⚠️ No returns but reasonable explanation

### High Risk Deals (Avoid unless prepared)
- 🚨 New seller (<50 feedback)
- 🚨 Price 50%+ below market
- 🚨 Stock photos only
- 🚨 No returns, vague description
- 🚨 International shipping only

---

## 🏆 Advanced Deal Hunter Tactics

### The Portfolio Approach
**Strategy:** Bid on multiple similar items
**Benefits:** 
- Increases winning odds
- Lets market set your price
- Reduces emotional attachment
- Better negotiating position

### The Patient Accumulator
**Strategy:** Build want lists, wait for perfect deals
**Process:**
1. Create saved searches for target items
2. Check daily for new listings
3. Note price trends over time
4. Strike when exceptional deal appears

### The Seasonal Shopper
**Strategy:** Buy off-season for maximum savings
**Examples:**
- Winter coats in spring/summer
- Halloween costumes in November
- Christmas decorations in January
- Beach gear in fall/winter

### The Notification Master
**Strategy:** Set up alerts for your targets
**Tools:**
- eBay saved searches with email alerts
- Price drop notifications
- New listing alerts for specific terms
- Ending soon alerts for watched items

---

## 📊 Deal Success Metrics

### Track Your Performance:
- **Average savings percentage** vs. retail
- **Hit rate** (successful bids/total bids)
- **Time to find** target items
- **Total value gained** through reselling
- **Risk assessment accuracy**

### Optimize Your Strategy:
- Which times yield best deals?
- What search terms are most effective?
- Which categories offer best margins?
- How accurate are your value assessments?

---

## 🎯 Ready to Hunt for Deals?

**Let's customize your deal hunting strategy:**

1. **What's your target?** (Specific item or browsing category)
2. **Budget constraints?** (Maximum spend, percentage savings goal)
3. **Time sensitivity?** (Need it now vs. willing to wait)
4. **Risk tolerance?** (Safe deals only vs. willing to gamble)

**I'll help you:**
- 🔍 **Find undervalued items** using advanced search techniques
- ⏰ **Time your purchases** for maximum savings
- 📊 **Assess deal quality** and risk levels
- 🎯 **Set up monitoring** for ongoing opportunities
- 💰 **Calculate true value** including all costs

**Quick Deal Hunting Commands:**
- "Find deals on [item]"
- "Search auctions ending soon for [category]"
- "Look for mispriced [brand] items"
- "Check seasonal deals in [category]"

*Let's turn you into a deal hunting master! 💰*"""

    try:
        await ctx.info(f"Deal finder prompt activated - Budget: {budget}, Category: {category}")
    except Exception:
        pass  # Continue even if context call fails
    return prompt