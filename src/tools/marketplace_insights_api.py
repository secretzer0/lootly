"""
eBay Marketplace Insights API tool for sales data analysis.

Provides access to eBay's Buy Marketplace Insights API to retrieve
historical sales data and market trends for specific items.
"""
from typing import Dict, Any, Optional, List, Union, Literal
from fastmcp import Context
from pydantic import BaseModel, Field, field_validator, ConfigDict
import json
from datetime import datetime, timedelta
from enum import Enum
from urllib.parse import quote

from api.oauth import OAuthManager, OAuthConfig, OAuthScopes
from api.rest_client import EbayRestClient, RestConfig
from api.errors import EbayApiError, ValidationError as ApiValidationError
from data_types import success_response, error_response, ErrorCode
from lootly_server import mcp


class ConditionID(Enum):
    """eBay condition IDs with human-readable names."""
    NEW = ("1000", "New")
    NEW_OTHER = ("1500", "New other (see details)")
    NEW_WITH_DEFECTS = ("1750", "New with defects")
    MANUFACTURER_REFURBISHED = ("2000", "Manufacturer refurbished")
    SELLER_REFURBISHED = ("2500", "Seller refurbished")
    USED_LIKE_NEW = ("2750", "Used - Like New / Open Box")
    USED = ("3000", "Used")
    VERY_GOOD = ("4000", "Very Good")
    GOOD = ("5000", "Good")
    ACCEPTABLE = ("6000", "Acceptable")
    FOR_PARTS_NOT_WORKING = ("7000", "For parts or not working")
    
    def __init__(self, id_value: str, description: str):
        self.id = id_value
        self.description = description
    
    @classmethod
    def get_id(cls, name: str) -> Optional[str]:
        """Get condition ID by name."""
        try:
            return cls[name.upper().replace(" ", "_").replace("-", "_")].id
        except KeyError:
            return None
    
    @classmethod
    def get_description(cls, condition_id: str) -> Optional[str]:
        """Get human-readable description for a condition ID."""
        for condition in cls:
            if condition.id == condition_id:
                return condition.description
        return None
    
    @classmethod
    def get_all_ids(cls) -> List[str]:
        """Get all valid condition IDs."""
        return [condition.id for condition in cls]
    
    @classmethod
    def get_mapping(cls) -> Dict[str, str]:
        """Get mapping of condition IDs to descriptions."""
        return {condition.id: condition.description for condition in cls}


class BuyingOption(Enum):
    """eBay buying options."""
    FIXED_PRICE = "FIXED_PRICE"
    AUCTION = "AUCTION"
    BEST_OFFER = "BEST_OFFER"
    CLASSIFIED_AD = "CLASSIFIED_AD"
    
    @classmethod
    def get_all(cls) -> List[str]:
        """Get all buying option values."""
        return [option.value for option in cls]




class DeliveryOption(Enum):
    """Delivery/shipping options."""
    SELLER_ARRANGED_LOCAL_PICKUP = "SELLER_ARRANGED_LOCAL_PICKUP"
    
    @classmethod
    def get_all(cls) -> List[str]:
        """Get all delivery option values."""
        return [option.value for option in cls]


class PriceCurrency(Enum):
    """Common ISO 4217 currency codes."""
    USD = "USD"  # US Dollar
    EUR = "EUR"  # Euro
    GBP = "GBP"  # British Pound
    CAD = "CAD"  # Canadian Dollar
    AUD = "AUD"  # Australian Dollar
    JPY = "JPY"  # Japanese Yen
    CNY = "CNY"  # Chinese Yuan
    INR = "INR"  # Indian Rupee
    MXN = "MXN"  # Mexican Peso
    BRL = "BRL"  # Brazilian Real
    CHF = "CHF"  # Swiss Franc
    SEK = "SEK"  # Swedish Krona
    NOK = "NOK"  # Norwegian Krone
    DKK = "DKK"  # Danish Krone
    PLN = "PLN"  # Polish Zloty
    SGD = "SGD"  # Singapore Dollar
    HKD = "HKD"  # Hong Kong Dollar
    NZD = "NZD"  # New Zealand Dollar
    ZAR = "ZAR"  # South African Rand
    RUB = "RUB"  # Russian Ruble
    
    @classmethod
    def get_all(cls) -> List[str]:
        """Get all currency values."""
        return [currency.value for currency in cls]


class SellerAccountType(Enum):
    """Seller account types."""
    INDIVIDUAL = "INDIVIDUAL"
    BUSINESS = "BUSINESS"
    
    @classmethod
    def get_all(cls) -> List[str]:
        """Get all account type values."""
        return [account_type.value for account_type in cls]


class ItemLocationRegion(Enum):
    """Item location regions (from eBay docs)."""
    WORLDWIDE = "WORLDWIDE"
    NORTH_AMERICA = "NORTH_AMERICA"
    ASIA = "ASIA"
    CONTINENTAL_EUROPE = "CONTINENTAL_EUROPE"
    EUROPEAN_UNION = "EUROPEAN_UNION"
    UK_AND_IRELAND = "UK_AND_IRELAND"
    BORDER_COUNTRIES = "BORDER_COUNTRIES"
    
    @classmethod
    def get_all(cls) -> List[str]:
        """Get all region values."""
        return [region.value for region in cls]


class QualifiedProgram(Enum):
    """eBay qualified programs."""
    EBAY_PLUS = "EBAY_PLUS"
    AUTHENTICITY_GUARANTEE = "AUTHENTICITY_GUARANTEE"
    AUTHENTICITY_VERIFICATION = "AUTHENTICITY_VERIFICATION"
    
    @classmethod
    def get_all(cls) -> List[str]:
        """Get all program values."""
        return [program.value for program in cls]


class FilterBuilder:
    """Helper class to build eBay filter strings."""
    
    def __init__(self):
        self.filters = []
    
    def add_price_range(self, min_price: Optional[float] = None, max_price: Optional[float] = None, currency: str = "USD") -> "FilterBuilder":
        """Add price range filter."""
        if min_price is not None or max_price is not None:
            price_filter = "price:["
            if min_price is not None:
                price_filter += str(min_price)
            price_filter += ".."
            if max_price is not None:
                price_filter += str(max_price)
            price_filter += "]"
            self.filters.append(price_filter)
            self.filters.append(f"priceCurrency:{currency}")
        return self
    
    def add_condition_ids(self, condition_ids: Union[str, List[str]]) -> "FilterBuilder":
        """Add condition IDs filter."""
        if isinstance(condition_ids, str):
            condition_ids = [c.strip() for c in condition_ids.split(",")]
        if condition_ids:
            self.filters.append(f"conditionIds:{{{('|'.join(condition_ids))}}}")
        return self
    
    def add_conditions(self, conditions: List[str]) -> "FilterBuilder":
        """Add conditions filter (NEW, USED, UNSPECIFIED)."""
        if conditions:
            self.filters.append(f"conditions:{{{('|'.join(conditions))}}}")
        return self
    
    def add_delivery_options(self, options: List[str]) -> "FilterBuilder":
        """Add delivery options filter."""
        if options:
            self.filters.append(f"deliveryOptions:{{{('|'.join(options))}}}")
        return self
    
    def add_buying_options(self, options: List[str]) -> "FilterBuilder":
        """Add buying options filter."""
        if options:
            self.filters.append(f"buyingOptions:{{{('|'.join(options))}}}")
        return self
    
    def add_item_location_country(self, country: str) -> "FilterBuilder":
        """Add item location country filter."""
        if country:
            self.filters.append(f"itemLocationCountry:{country}")
        return self
    
    def add_sellers(self, sellers: List[str]) -> "FilterBuilder":
        """Add sellers filter."""
        if sellers and len(sellers) <= 250:  # eBay limit
            self.filters.append(f"sellers:{{{('|'.join(sellers))}}}")
        return self
    
    def add_seller_account_types(self, types: List[str]) -> "FilterBuilder":
        """Add seller account types filter."""
        if types:
            self.filters.append(f"sellerAccountTypes:{{{('|'.join(types))}}}")
        return self
    
    def add_delivery_country(self, country: str) -> "FilterBuilder":
        """Add delivery country filter."""
        if country:
            self.filters.append(f"deliveryCountry:{country}")
        return self
    
    def add_max_delivery_cost(self, cost: float) -> "FilterBuilder":
        """Add max delivery cost filter. Use 0 for free shipping."""
        if cost is not None:
            self.filters.append(f"maxDeliveryCost:{cost}")
        return self
    
    def add_returns_accepted(self, accepted: bool) -> "FilterBuilder":
        """Add returns accepted filter."""
        if accepted is not None:
            self.filters.append(f"returnsAccepted:{str(accepted).lower()}")
        return self
    
    def add_charity_only(self, charity_only: bool) -> "FilterBuilder":
        """Add charity only filter."""
        if charity_only:
            self.filters.append("charityOnly:true")
        return self
    
    def add_qualified_programs(self, programs: List[str]) -> "FilterBuilder":
        """Add qualified programs filter."""
        if programs:
            self.filters.append(f"qualifiedPrograms:{{{('|'.join(programs))}}}")
        return self
    
    def add_last_sold_date_range(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> "FilterBuilder":
        """Add last sold date range filter."""
        if start_date or end_date:
            date_filter = "lastSoldDate:["
            if start_date:
                date_filter += start_date
            date_filter += ".."
            if end_date:
                date_filter += end_date
            date_filter += "]"
            self.filters.append(date_filter)
        return self
    
    def build(self) -> Optional[str]:
        """Build the filter string."""
        if not self.filters:
            return None
        return ",".join(self.filters)
    
    def __str__(self) -> str:
        """String representation of the filter."""
        return self.build() or ""


class ItemSalesSearchInput(BaseModel):
    """Input validation for item sales search request."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    q: Optional[str] = Field(None, description="Keyword search query (max 100 chars)")
    category_ids: Optional[str] = Field(None, description="Comma-separated category IDs")
    filter: Optional[str] = Field(None, description="Complex filter string (price, condition, location, etc.)")
    sort: Optional[str] = Field(default=None, description="Sort order: 'price' (ascending) or '-price' (descending). If not specified, results are sorted by Best Match.")
    limit: int = Field(default=50, ge=1, le=200, description="Number of results to return")
    offset: int = Field(default=0, ge=0, description="Pagination offset")
    
    @field_validator('q')
    @classmethod
    def validate_query(cls, v):
        if v and len(v) > 100:
            raise ValueError("Query must be 100 characters or less")
        return v
    
    @field_validator('category_ids')
    @classmethod
    def validate_category_ids(cls, v):
        if v:
            cat_ids = v.split(",")
            for cat_id in cat_ids:
                if not cat_id.strip().isdigit():
                    raise ValueError(f"Invalid category ID: {cat_id}")
        return v
    
    @field_validator('sort')
    @classmethod
    def validate_sort(cls, v):
        if v is None:
            return v
        valid_sorts = ["price", "-price"]
        if v not in valid_sorts:
            raise ValueError(f"Invalid sort option. Must be one of: {', '.join(valid_sorts)}")
        return v
    
    def validate_search_criteria(self):
        """Ensure at least one search criterion is provided."""
        if not any([self.q, self.category_ids, self.filter]):
            raise ValueError("At least one search criterion is required (q, category_ids, or filter)")


def _convert_item_sale(sale: Dict[str, Any]) -> Dict[str, Any]:
    """Convert API sale response to our format."""
    # Extract basic info
    result = {
        "item_id": sale.get("itemId"),
        "title": sale.get("title"),
        "condition": sale.get("condition"),
        "condition_id": sale.get("conditionId"),
        "sold_date": sale.get("itemSoldDate"),
        "category_id": sale.get("categoryId"),
        "category_path": sale.get("categoryPath")
    }
    
    # Add human-readable condition name if we have condition ID
    if result["condition_id"]:
        condition_name = ConditionID.get_description(result["condition_id"])
        if condition_name:
            result["condition_name"] = condition_name
    
    # Extract price
    if sale.get("itemPrice"):
        result["price"] = {
            "value": float(sale["itemPrice"].get("value", 0)),
            "currency": sale["itemPrice"].get("currency", "USD")
        }
    
    # Extract seller info
    if sale.get("seller"):
        result["seller"] = {
            "username": sale["seller"].get("username"),
            "feedback_percentage": sale["seller"].get("feedbackPercentage"),
            "feedback_score": sale["seller"].get("feedbackScore")
        }
    
    # Extract buying option
    result["buying_option"] = sale.get("buyingOption")
    
    # Extract quantity sold
    result["quantity_sold"] = sale.get("quantitySold", 1)
    
    # Extract item location
    if sale.get("itemLocation"):
        result["item_location"] = {
            "city": sale["itemLocation"].get("city"),
            "state": sale["itemLocation"].get("stateOrProvince"),
            "country": sale["itemLocation"].get("country"),
            "postal_code": sale["itemLocation"].get("postalCode")
        }
    
    # Add item URL if available
    if sale.get("itemWebUrl"):
        result["item_url"] = sale["itemWebUrl"]
    
    # Extract EPID if available
    if sale.get("epid"):
        result["epid"] = sale["epid"]
    
    # Extract additional images if available
    if sale.get("additionalImages"):
        result["images"] = [img.get("imageUrl") for img in sale["additionalImages"] if img.get("imageUrl")]
    elif sale.get("image") and sale["image"].get("imageUrl"):
        result["images"] = [sale["image"]["imageUrl"]]
    
    return result




@mcp.tool
async def build_marketplace_filter(
    ctx: Context,
    price_min: Optional[float] = None,
    price_max: Optional[float] = None,
    price_currency: Optional[Union[PriceCurrency, str]] = None,
    conditions: Optional[List[Union[ConditionID, str]]] = None,
    buying_options: Optional[List[Union[BuyingOption, str]]] = None,
    delivery_options: Optional[List[Union[DeliveryOption, str]]] = None,
    item_location_country: Optional[str] = None,
    item_location_region: Optional[Union[ItemLocationRegion, str]] = None,
    delivery_country: Optional[str] = None,
    max_delivery_cost: Optional[float] = None,
    free_shipping: bool = False,
    sellers: Optional[List[str]] = None,
    seller_account_types: Optional[List[Union[SellerAccountType, str]]] = None,
    returns_accepted: Optional[bool] = None,
    charity_only: bool = False,
    authenticity_guarantee: bool = False,
    authenticity_verification: bool = False,
    ebay_plus: bool = False,
    last_sold_start_date: Optional[str] = None,
    last_sold_end_date: Optional[str] = None
) -> str:
    """
    Build a complex filter string for eBay Marketplace Insights API searches.
    
    This tool creates properly formatted filter strings that can be passed
    to the search_item_sales function's filter parameter.
    
    USAGE: Call this tool first to build a filter, then pass the result to search_item_sales:
    
    Step 1: filter_result = build_marketplace_filter(price_min=100, conditions=["New"])
    Step 2: search_item_sales(q="phone", filter=filter_result["data"]["filter"])
    
    Use this tool when you need:
    - Complex filters with many conditions
    - Filters that will be reused across multiple searches  
    - Better type safety with enum values
    
    Args:
        price_min: Minimum price
        price_max: Maximum price  
        price_currency: Currency code (ISO 4217). Use PriceCurrency enum or string:
            - PriceCurrency.USD, PriceCurrency.EUR, PriceCurrency.GBP, etc.
            - Or string values: "USD", "EUR", "GBP", "CAD", "AUD", "JPY", "CNY", "INR"
            - "MXN", "BRL", "CHF", "SEK", "NOK", "DKK", "PLN", "SGD"
            - "HKD", "NZD", "ZAR", "RUB"
        conditions: List of item conditions. Use ConditionID enum or string:
            - ConditionID.NEW, ConditionID.USED, ConditionID.VERY_GOOD, etc.
            - Or condition IDs: "1000", "3000", "4000", etc.
            - Or human-readable names: "New", "Used", "Very Good", etc.
        buying_options: List of buying options. Use BuyingOption enum or string:
            - BuyingOption.FIXED_PRICE - Buy It Now listings
            - BuyingOption.AUCTION - Auction listings
            - BuyingOption.BEST_OFFER - Listings with Make Offer
            - BuyingOption.CLASSIFIED_AD - Classified ad listings
        delivery_options: List of delivery options. Use DeliveryOption enum or string:
            - DeliveryOption.SELLER_ARRANGED_LOCAL_PICKUP - Local pickup available
        item_location_country: Item location country code (e.g., "US", "GB", "DE")
        item_location_region: Item location region. Use ItemLocationRegion enum or string:
            - ItemLocationRegion.WORLDWIDE - All regions
            - ItemLocationRegion.NORTH_AMERICA - US, Canada, Mexico
            - ItemLocationRegion.ASIA - Asian countries
            - ItemLocationRegion.CONTINENTAL_EUROPE - Continental European countries
            - ItemLocationRegion.EUROPEAN_UNION - EU member countries
            - ItemLocationRegion.UK_AND_IRELAND - United Kingdom and Ireland
            - ItemLocationRegion.BORDER_COUNTRIES - Countries bordering the buyer's country
        delivery_country: Delivery destination country code
        max_delivery_cost: Maximum delivery cost (use 0 for free shipping)
        free_shipping: Shortcut for max_delivery_cost=0
        sellers: List of seller usernames (max 250)
        seller_account_types: List of seller account types. Use SellerAccountType enum or string:
            - SellerAccountType.INDIVIDUAL - Individual sellers
            - SellerAccountType.BUSINESS - Business sellers
        returns_accepted: Filter by returns policy (true/false)
        charity_only: Only show charity listings
        authenticity_guarantee: Only items with authenticity guarantee
        authenticity_verification: Only items with authenticity verification
        ebay_plus: Only eBay Plus items
        last_sold_start_date: Start date (YYYY-MM-DD)
        last_sold_end_date: End date (YYYY-MM-DD)
        ctx: MCP context
    
    Returns:
        JSON response with the built filter string
    
    Examples:
        # Price and condition filter
        build_marketplace_filter(
            price_min=100,
            price_max=500,
            conditions=["New", "Used like new"]
        )
        Returns: "price:[100..500],priceCurrency:USD,conditionIds:{1000|2750}"
        
        # Location and shipping filter
        build_marketplace_filter(
            item_location_country="US",
            free_shipping=True,
            returns_accepted=True
        )
        Returns: "itemLocationCountry:US,maxDeliveryCost:0,returnsAccepted:true"
    """
    await ctx.info("🛠️ Building marketplace filter string...")
    
    fb = FilterBuilder()
    
    # Price filter
    if price_min is not None or price_max is not None:
        currency = price_currency.value if isinstance(price_currency, PriceCurrency) else (price_currency or "USD")
        fb.add_price_range(price_min, price_max, currency)
    
    # Condition filter
    if conditions:
        condition_ids = []
        for cond in conditions:
            if isinstance(cond, ConditionID):
                condition_ids.append(cond.id)
            elif cond in ConditionID.get_all_ids():
                # Direct condition ID
                condition_ids.append(cond)
            else:
                # Try to convert from human-readable name
                cid = ConditionID.get_id(cond)
                if cid:
                    condition_ids.append(cid)
                else:
                    await ctx.warning(f"Unknown condition: {cond}. Valid IDs: {', '.join(ConditionID.get_all_ids())}")
        
        if condition_ids:
            fb.add_condition_ids(condition_ids)
    
    # Buying options
    if buying_options:
        # Convert enum values to strings
        option_strings = []
        for opt in buying_options:
            if isinstance(opt, BuyingOption):
                option_strings.append(opt.value)
            else:
                option_strings.append(opt)
        
        # Validate buying options
        valid_options = BuyingOption.get_all()
        for opt in option_strings:
            if opt not in valid_options:
                await ctx.warning(f"Unknown buying option: {opt}. Valid: {', '.join(valid_options)}")
        fb.add_buying_options(option_strings)
    
    # Delivery options
    if delivery_options:
        # Convert enum values to strings
        option_strings = []
        for opt in delivery_options:
            if isinstance(opt, DeliveryOption):
                option_strings.append(opt.value)
            else:
                option_strings.append(opt)
        
        # Validate delivery options
        valid_options = DeliveryOption.get_all()
        for opt in option_strings:
            if opt not in valid_options:
                await ctx.warning(f"Unknown delivery option: {opt}. Valid: {', '.join(valid_options)}")
        fb.add_delivery_options(option_strings)
    
    # Location filters
    if item_location_country:
        fb.add_item_location_country(item_location_country)
    if item_location_region:
        region_value = item_location_region.value if isinstance(item_location_region, ItemLocationRegion) else item_location_region
        # Note: eBay API doesn't have a direct itemLocationRegion filter, but we can document this for future use
        await ctx.info(f"Note: item_location_region ({region_value}) is not directly supported by eBay API filters")
    if delivery_country:
        fb.add_delivery_country(delivery_country)
    
    # Shipping filter
    if free_shipping:
        fb.add_max_delivery_cost(0)
    elif max_delivery_cost is not None:
        fb.add_max_delivery_cost(max_delivery_cost)
    
    # Seller filters
    if sellers:
        if len(sellers) > 250:
            await ctx.warning("Seller list truncated to 250 (eBay limit)")
            sellers = sellers[:250]
        fb.add_sellers(sellers)
    
    if seller_account_types:
        # Convert enum values to strings
        type_strings = []
        for account_type in seller_account_types:
            if isinstance(account_type, SellerAccountType):
                type_strings.append(account_type.value)
            else:
                type_strings.append(account_type)
        
        # Validate seller account types
        valid_types = SellerAccountType.get_all()
        for account_type in type_strings:
            if account_type not in valid_types:
                await ctx.warning(f"Unknown seller account type: {account_type}. Valid: {', '.join(valid_types)}")
        fb.add_seller_account_types(type_strings)
    
    # Other filters
    if returns_accepted is not None:
        fb.add_returns_accepted(returns_accepted)
    if charity_only:
        fb.add_charity_only(charity_only)
    
    # Qualified programs
    programs = []
    if authenticity_guarantee:
        programs.append(QualifiedProgram.AUTHENTICITY_GUARANTEE.value)
    if authenticity_verification:
        programs.append(QualifiedProgram.AUTHENTICITY_VERIFICATION.value)
    if ebay_plus:
        programs.append(QualifiedProgram.EBAY_PLUS.value)
    if programs:
        fb.add_qualified_programs(programs)
    
    # Date range
    if last_sold_start_date or last_sold_end_date:
        fb.add_last_sold_date_range(last_sold_start_date, last_sold_end_date)
    
    filter_string = fb.build()
    
    if not filter_string:
        await ctx.info("No filters specified - empty filter string")
        return success_response(
            data={
                "filter": "",
                "filter_count": 0,
                "description": "No filters applied"
            },
            message="Empty filter string (no filters specified)"
        ).to_json_string()
    
    # Parse filter for description
    filter_parts = filter_string.split(",")
    
    await ctx.info(f"✅ Built filter with {len(filter_parts)} components")
    
    return success_response(
        data={
            "filter": filter_string,
            "filter_count": len(filter_parts),
            "components": filter_parts,
            "description": f"Filter with {len(filter_parts)} conditions"
        },
        message=f"Successfully built filter string"
    ).to_json_string()


@mcp.tool
async def search_item_sales(
    ctx: Context,
    q: Optional[str] = None,
    category_ids: Optional[str] = None,
    filter: Optional[str] = None,
    sort: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    # Helper parameters that build filter string:
    price_min: Optional[float] = None,
    price_max: Optional[float] = None,
    price_currency: str = "USD",
    condition: Optional[Union[str, List[str]]] = None,
    buying_options: Optional[List[str]] = None,
    free_shipping: bool = False,
    returns_accepted: Optional[bool] = None,
    sellers: Optional[List[str]] = None,
    item_location_country: Optional[str] = None,
    delivery_country: Optional[str] = None,
    charity_only: bool = False,
    authenticity_guarantee: bool = False
) -> str:
    """
    Search for historical sales data of items on eBay.
    
    Provides insights into sold items including prices, dates, and seller information.
    At least one search criterion (q, category_ids, or filter) must be provided.
    
    TWO WAYS TO USE THIS TOOL:
    
    SIMPLE: Use built-in helper parameters for basic filtering:
    search_item_sales(q="phone", price_min=100, condition=["New"])
    
    ADVANCED: Use build_marketplace_filter tool first for complex filters:
    1. filter_result = build_marketplace_filter(price_min=100, conditions=["New"], buying_options=["FIXED_PRICE"])
    2. search_item_sales(q="phone", filter=filter_result["data"]["filter"])
    
    Use ADVANCED approach when you need complex filters with many conditions or type safety.
    
    Args:
        q: Keyword search query (e.g., "iphone 15", "vintage camera"). Max 100 chars.
           - Space-separated words are treated as OR
           - Comma-separated words are treated as AND
        category_ids: Comma-separated category IDs (e.g., "9355,15032")
        filter: Complex filter string - use build_marketplace_filter tool to create this
        sort: Sort order - "price" (ascending) or "-price" (descending). Default: Best Match
        limit: Number of results (1-200, default: 50)
        offset: Pagination offset (default: 0)
        
        Helper parameters (these build the filter string for you):
        price_min: Minimum price filter
        price_max: Maximum price filter
        price_currency: Currency for price filter (default: "USD")
        condition: Condition filter - accepts names or IDs:
            - "New" or "1000"
            - "New other" or "1500"
            - "New with defects" or "1750"
            - "Manufacturer refurbished" or "2000"
            - "Used" or "3000"
            - "Used like new" or "2750"
            - "Very Good" or "4000"
            - "Good" or "5000"
            - "Acceptable" or "6000"
            - "For parts" or "7000"
        buying_options: List of buying options:
            - "FIXED_PRICE"
            - "AUCTION"
            - "BEST_OFFER"
            - "CLASSIFIED_AD"
        free_shipping: True to show only free shipping items
        returns_accepted: True/False to filter by returns policy
        sellers: List of seller usernames (max 250)
        item_location_country: Country code (e.g., "US", "GB", "DE")
        delivery_country: Delivery country filter
        charity_only: True to show only charity listings
        authenticity_guarantee: True to show only items with authenticity guarantee
        ctx: MCP context
    
    Returns:
        JSON response with sales data and statistics
        
    Note:
        This tool returns structured data for processing. Please analyze the sales data 
        and provide the user with useful insights (e.g., "Found 10 sales, average price $450")
        rather than showing them the raw JSON data.
    
    Examples:
        # Search for iPhone sales
        search_item_sales(q="iphone 15", category_ids="9355", price_min=500)
        
        # Search with complex filters
        search_item_sales(
            q="vintage camera",
            condition=["Used", "Very Good"],
            free_shipping=True,
            item_location_country="US"
        )
        
        # Method 1: Use build_marketplace_filter tool to create complex filters
        filter_result = build_marketplace_filter(
            price_min=300, price_max=1000,
            conditions=["Used", "Very Good"]
        )
        # Then use the filter:
        search_item_sales(
            q="laptop",
            filter=filter_result["data"]["filter"]
        )
        
        # Method 2: Use helper parameters directly (simpler for basic filters)
        search_item_sales(
            q="laptop",
            price_min=300,
            price_max=1000,
            condition=["Used", "Very Good"]
        )
    """
    await ctx.info(f"🔍 Searching item sales: q='{q}', categories={category_ids}")
    await ctx.report_progress(0.1, "🛠️ Building filters...")
    
    # Build filter string from helper parameters if not provided
    if not filter:
        fb = FilterBuilder()
        
        # Price filter
        if price_min is not None or price_max is not None:
            fb.add_price_range(price_min, price_max, price_currency)
        
        # Condition filter
        if condition:
            if isinstance(condition, str):
                condition = [condition]
            # Convert condition names to IDs
            condition_ids = []
            for c in condition:
                if c in ConditionID.get_all_ids():
                    condition_ids.append(c)
                else:
                    cid = ConditionID.get_id(c)
                    if cid:
                        condition_ids.append(cid)
                    else:
                        condition_ids.append(c)  # Keep original if not found
            fb.add_condition_ids(condition_ids)
        
        # Buying options
        if buying_options:
            fb.add_buying_options(buying_options)
        
        # Location filters
        if item_location_country:
            fb.add_item_location_country(item_location_country)
        if delivery_country:
            fb.add_delivery_country(delivery_country)
        
        # Shipping filter
        if free_shipping:
            fb.add_max_delivery_cost(0)
        
        # Other filters
        if returns_accepted is not None:
            fb.add_returns_accepted(returns_accepted)
        if charity_only:
            fb.add_charity_only(charity_only)
        if sellers:
            fb.add_sellers(sellers)
        
        # Special programs
        programs = []
        if authenticity_guarantee:
            programs.append(QualifiedProgram.AUTHENTICITY_GUARANTEE.value)
        if programs:
            fb.add_qualified_programs(programs)
        
        filter = fb.build()
    
    await ctx.report_progress(0.2, "Validating input...")
    
    # Validate input
    try:
        input_data = ItemSalesSearchInput(
            q=q,
            category_ids=category_ids,
            filter=filter,
            sort=sort,
            limit=limit,
            offset=offset
        )
        input_data.validate_search_criteria()
    except Exception as e:
        await ctx.error(f"Invalid input: {str(e)}")
        return error_response(
            ErrorCode.VALIDATION_ERROR,
            f"Invalid input: {str(e)}"
        ).to_json_string()
    
    # Check credentials
    if not mcp.config.app_id:
        await ctx.error("No eBay credentials configured")
        return error_response(
            ErrorCode.CONFIGURATION_ERROR,
            "eBay App ID not configured. Please set EBAY_APP_ID environment variable."
        ).to_json_string()
    
    # Initialize OAuth manager
    oauth_config = OAuthConfig(
        client_id=mcp.config.app_id,
        client_secret=mcp.config.cert_id or "",
        sandbox=mcp.config.sandbox_mode
    )
    oauth_manager = OAuthManager(oauth_config)
    
    # Initialize REST client
    rest_config = RestConfig(
        sandbox=mcp.config.sandbox_mode,
        timeout=mcp.config.timeout,
        max_retries=mcp.config.max_retries,
        rate_limit_per_day=mcp.config.rate_limit_per_day
    )
    rest_client = EbayRestClient(oauth_manager, rest_config)
    
    try:
        await ctx.report_progress(0.3, "🌐 Calling eBay Marketplace Insights API...")
        
        # Build query parameters
        params = {
            "limit": input_data.limit,
            "offset": input_data.offset
        }
        
        # Add main search criteria
        if input_data.q:
            params["q"] = input_data.q
        if input_data.category_ids:
            params["category_ids"] = input_data.category_ids
        if input_data.filter:
            params["filter"] = input_data.filter
        if input_data.sort is not None:
            params["sort"] = input_data.sort
        
        # Make API request
        response = await rest_client.get(
            "/buy/marketplace_insights/v1_beta/item_sales/search",
            params=params,
            scope=OAuthScopes.BUY_MARKETPLACE_INSIGHTS
        )
        
        await ctx.report_progress(0.8, "📊 Processing response...")
        
        # Extract sales data
        sales = response.get("itemSales", [])
        
        # Convert sales to our format
        converted_sales = [_convert_item_sale(sale) for sale in sales]
        
        # Calculate statistics if we have sales
        stats = {}
        if converted_sales:
            prices = [s["price"]["value"] for s in converted_sales if "price" in s]
            if prices:
                stats = {
                    "average_price": sum(prices) / len(prices),
                    "min_price": min(prices),
                    "max_price": max(prices),
                    "median_price": sorted(prices)[len(prices) // 2],
                    "total_items": len(converted_sales),
                    "price_currency": converted_sales[0]["price"]["currency"] if converted_sales[0].get("price") else "USD"
                }
        
        await ctx.report_progress(1.0, "✅ Complete")
        await ctx.info(f"📈 Retrieved {len(converted_sales)} item sales")
        
        return success_response(
            data={
                "item_sales": converted_sales,
                "total": response.get("total", len(converted_sales)),
                "limit": input_data.limit,
                "offset": input_data.offset,
                "statistics": stats,
                "search_criteria": {
                    "q": input_data.q,
                    "category_ids": input_data.category_ids,
                    "filter": input_data.filter,
                    "sort": input_data.sort
                },
                "href": response.get("href"),
                "next": response.get("next"),
                "prev": response.get("prev")
            },
            message=f"Retrieved {len(converted_sales)} item sales"
        ).to_json_string()
        
    except EbayApiError as e:
        await ctx.error(f"eBay API error: {str(e)}")
        
        # Handle specific errors
        if e.status_code == 400:
            error_msg = str(e)
            # Check for sandbox limitations
            if "9355" in error_msg and mcp.config.sandbox_mode:
                return error_response(
                    ErrorCode.VALIDATION_ERROR,
                    "In sandbox mode, try using category ID 9355 for testing"
                ).to_json_string()
            return error_response(
                ErrorCode.VALIDATION_ERROR,
                f"Invalid request: {error_msg}"
            ).to_json_string()
        elif e.status_code == 404:
            return error_response(
                ErrorCode.RESOURCE_NOT_FOUND,
                "No sales data found for the specified criteria"
            ).to_json_string()
        else:
            return error_response(
                ErrorCode.EXTERNAL_API_ERROR,
                f"eBay API error: {str(e)}"
            ).to_json_string()
            
    except Exception as e:
        await ctx.error(f"Unexpected error: {str(e)}")
        return error_response(
            ErrorCode.INTERNAL_ERROR,
            f"Failed to search item sales: {str(e)}"
        ).to_json_string()
        
    finally:
        # Clean up
        if 'rest_client' in locals():
            await rest_client.close()