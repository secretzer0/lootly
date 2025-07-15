"""eBay listing optimizer prompt."""
from fastmcp import Context
from lootly_server import mcp


@mcp.prompt("listing_optimizer")
async def listing_optimizer_prompt(item_type: str = "product", *, ctx: Context) -> str:
    """Guide for creating optimized eBay listings that sell.
    
    This prompt helps users create high-performing eBay listings by providing:
    - Title optimization strategies
    - Description best practices
    - Pricing and format recommendations
    - Photo and presentation tips
    - Category and shipping optimization
    
    Args:
        item_type: Type of item being listed (electronics, clothing, collectibles, etc.)
        ctx: MCP context
        
    Returns:
        Formatted listing optimization prompt
    """
    item_type = item_type or "product"  # Handle None gracefully
    prompt = f"""# eBay Listing Optimizer - {item_type.title()} Edition

I'll help you create a high-performing eBay listing that attracts buyers and sells quickly! Let's optimize every element for maximum visibility and conversion.

## 🎯 Listing Optimization Checklist

### ✅ **Title Optimization (80-character limit)**
- [ ] Include primary keyword first
- [ ] Add brand name and model number
- [ ] Use power words (NEW, RARE, VINTAGE, etc.)
- [ ] Include key specifications
- [ ] Add condition if relevant
- [ ] Use ALL CAPS sparingly for emphasis

### ✅ **Category Selection**
- [ ] Choose most specific category possible
- [ ] Use secondary category if beneficial
- [ ] Check competitors' category choices
- [ ] Consider seasonal category shifts

### ✅ **Pricing Strategy**
- [ ] Research completed sales (not just current listings)
- [ ] Factor in eBay and PayPal fees (~13%)
- [ ] Consider Buy It Now vs Auction format
- [ ] Plan for Best Offer if appropriate

### ✅ **Photos & Presentation**
- [ ] 12 high-quality photos (eBay's max)
- [ ] Good lighting and clear focus
- [ ] Multiple angles and close-ups
- [ ] Show any flaws honestly
- [ ] Include size references where helpful

### ✅ **Description & Details**
- [ ] Complete all item specifics
- [ ] Write detailed, honest description
- [ ] Use bullet points for key features
- [ ] Include keywords naturally
- [ ] Address common buyer questions

---

## 📝 Title Optimization Strategies

### The Perfect Title Formula:
**[BRAND] [MODEL] [KEY FEATURE] [CONDITION] [POWER WORD]**

### Title Strategies by Category:

#### Electronics ({item_type})
```
✅ GOOD: "Apple iPhone 14 Pro 256GB Unlocked Space Black NEW"
❌ POOR: "Nice phone for sale iPhone"

Key elements:
- Brand first: Apple, Samsung, Sony
- Exact model: iPhone 14 Pro, Galaxy S23
- Capacity/specs: 256GB, 8GB RAM
- Carrier status: Unlocked, Verizon
- Condition: New, Refurbished, Used
```

#### Clothing & Fashion
```
✅ GOOD: "Nike Air Jordan 1 Retro High OG Chicago Size 10 NEW"
❌ POOR: "Red and black sneakers size 10"

Key elements:
- Brand + model: Nike Air Jordan 1
- Style details: Retro High OG
- Colorway: Chicago, Bred, Royal
- Size clearly stated
- Condition
```

#### Collectibles & Vintage
```
✅ GOOD: "Vintage 1960s Omega Seamaster Automatic Watch RARE"
❌ POOR: "Old watch from estate sale"

Key elements:
- Era: 1960s, Mid-Century, Victorian
- Brand recognition: Omega, Rolex
- Specific model: Seamaster
- Rarity indicators: RARE, HTCA, Limited
```

### Power Words That Sell:
- **Urgency:** RARE, LIMITED, LAST ONE, DISCONTINUED
- **Condition:** NEW, MINT, PRISTINE, PERFECT
- **Value:** DEAL, SALE, REDUCED, BARGAIN
- **Quality:** PREMIUM, PROFESSIONAL, AUTHENTIC, GENUINE

---

## 💰 Strategic Pricing Guide

### Research Phase:
1. **Check completed listings** (sold items, not current)
2. **Analyze price ranges** (low, average, high)
3. **Factor in condition differences**
4. **Consider seasonal trends**
5. **Account for all fees** (~13% total)

### Pricing Strategies:

#### **Buy It Now (Fixed Price)**
**Best for:**
- Items with consistent market value
- When you need quick sale
- Professional/business sellers
- Items with low competition

**Pricing tips:**
- Price at market rate or slightly below
- Enable "Best Offer" for negotiation
- Consider free shipping (build into price)

#### **Auction Format**
**Best for:**
- Rare or unique items
- Testing market demand
- Creating urgency and competition
- When unsure of value

**Starting strategies:**
- Start at $0.99 for maximum exposure
- Start at 70% of market value for safer approach
- 7-day auctions for maximum visibility
- End on Sunday evening for best results

#### **Hybrid Approach**
- Auction with Buy It Now option
- Gives buyers choice
- Can sell immediately or create bidding war

---

## 📸 Photo Optimization Secrets

### The 12-Photo Strategy:
1. **Main photo:** Clean, bright, full item view
2. **Detail shots:** Close-ups of key features
3. **Condition documentation:** Any wear or flaws
4. **Packaging:** What's included
5. **Scale reference:** Size comparison
6. **Multiple angles:** Front, back, sides, top
7. **In-use photos:** Item being worn/used
8. **Accessories:** All included items
9. **Labels/tags:** Brand, model, size tags
10. **Comparison:** With similar items if helpful
11. **Lifestyle context:** Item in appropriate setting
12. **Bonus feature:** Special details buyers care about

### Photo Quality Tips:
- **Natural lighting** is best (near window)
- **Clean, neutral background** (white/light colored)
- **Sharp focus** on important details
- **Consistent lighting** across all photos
- **High resolution** (eBay optimizes automatically)

---

## ✍️ Description Optimization

### Structure That Converts:

#### Opening Hook (First 2 Lines)
```
🔥 RARE 1985 Apple IIe Computer - Complete Setup! 🔥
Perfect working condition with original manuals and software!
```

#### Key Features (Bullet Points)
```
✅ What you get:
• Original Apple IIe computer
• Monitor, keyboard, mouse
• Original manuals and documentation
• 10+ software disks included
• All cables and power supplies

✅ Condition details:
• Powers on immediately
• All keys responsive
• Screen clear and bright
• Minor cosmetic wear (shown in photos)
• Non-smoking household
```

#### Detailed Description
- Tell the item's story
- Explain why you're selling
- Address common concerns
- Use keywords naturally
- Be completely honest about condition

#### Call to Action
```
💫 Ready to own a piece of computing history? 
⚡ Buy now or make an offer!
📨 Questions? Message me anytime!
```

---

## 🎨 Category-Specific Optimization

### Electronics Optimization:
- **Specs in title:** Storage, RAM, screen size
- **Compatibility:** Works with X, compatible with Y
- **Accessories:** All original boxes, chargers
- **Warranty status:** Remaining warranty info
- **Unlock status:** Carrier locked/unlocked

### Fashion Optimization:
- **Measurements:** Exact dimensions when possible
- **Material details:** 100% cotton, leather type
- **Care instructions:** Washing, storage
- **Styling suggestions:** Outfit ideas
- **Authenticity:** Authentication details if luxury

### Collectibles Optimization:
- **Provenance:** Where/when acquired
- **Rarity indicators:** Production numbers, variants
- **Grading:** Professional grades if applicable
- **Storage:** How item was kept
- **Research links:** Reference materials

---

## 🚚 Shipping & Handling Strategy

### Shipping Optimization:
- **Free shipping** increases visibility (build cost into price)
- **Fast handling time** (same/next day) improves metrics
- **Multiple options** (economy vs expedited)
- **International shipping** expands market
- **Calculated shipping** for large/heavy items

### Handling Best Practices:
- State handling time clearly
- Ship faster than promised when possible
- Use eBay labels for discounts
- Package securely with tracking
- Communicate shipping updates

---

## 📊 Performance Optimization

### After Listing:
- **Monitor views and watchers**
- **Adjust price if low interest**
- **Answer questions quickly**
- **Add more photos if requested**
- **Promote listings** for increased visibility

### Success Metrics:
- **Views per day:** Good listing gets steady views
- **Watchers:** Shows buyer interest
- **Questions:** Engagement indicates interest
- **Best Offers:** Market testing your price

---

## 🏆 Advanced Listing Tactics

### SEO Optimization:
- **Research keywords** buyers actually use
- **Include synonyms** (laptop/notebook, phone/smartphone)
- **Long-tail keywords** for specific searches
- **Seasonal terms** when relevant

### Psychological Triggers:
- **Scarcity:** "Only one available"
- **Social proof:** "Popular item with 50+ watchers"
- **Authority:** "From smoke-free home"
- **Urgency:** "Priced to sell quickly"

### Competition Analysis:
- **Study successful listings** for similar items
- **Note their titles, prices, photos**
- **Identify gaps** you can fill
- **Differentiate** your listing

---

## 🎯 Ready to Create Your Winning Listing?

**Let's optimize your {item_type} listing step by step:**

1. **What exactly are you selling?** (Brand, model, condition)
2. **What's your timeline?** (Quick sale vs. maximum profit)
3. **Do you have all the item details?** (Specs, measurements, accessories)
4. **What's your competition doing?** (Check similar sold listings)

**I'll help you craft:**
- ✨ **Perfect title** with high-impact keywords
- 💰 **Strategic pricing** based on market research
- 📝 **Converting description** that addresses buyer needs
- 📸 **Photo plan** for maximum appeal
- 🚚 **Shipping strategy** for competitive advantage

*Let's make your listing irresistible to buyers! 🎯*"""

    try:
        await ctx.info(f"Listing optimizer prompt activated for {item_type}")
    except Exception:
        pass  # Continue even if context call fails
    return prompt