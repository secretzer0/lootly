"""
eBay REST API Pydantic Models.

Comprehensive data models for all eBay REST API operations with
validation and serialization support.
"""
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from decimal import Decimal
from enum import Enum
from pydantic import BaseModel, Field, HttpUrl, field_validator, ConfigDict


# ==================== Common Models ====================

class Currency(str, Enum):
    """ISO 4217 currency codes."""
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    CAD = "CAD"
    AUD = "AUD"
    JPY = "JPY"
    CNY = "CNY"
    # Add more as needed


class Money(BaseModel):
    """Monetary amount with currency."""
    value: Decimal = Field(..., description="Amount value")
    currency: Currency = Field(..., description="Currency code")
    
    @field_validator('value')
    @classmethod
    def validate_value(cls, v):
        if v < 0:
            raise ValueError("Money value cannot be negative")
        return v
    
    def __str__(self) -> str:
        """Format as currency string."""
        if self.currency == Currency.JPY:
            return f"¥{self.value:,.0f}"
        elif self.currency == Currency.EUR:
            return f"€{self.value:,.2f}"
        elif self.currency == Currency.GBP:
            return f"£{self.value:,.2f}"
        else:
            return f"{self.currency} {self.value:,.2f}"


class MarketplaceId(str, Enum):
    """eBay marketplace identifiers."""
    EBAY_US = "EBAY_US"
    EBAY_GB = "EBAY_GB"
    EBAY_DE = "EBAY_DE"
    EBAY_AU = "EBAY_AU"
    EBAY_CA = "EBAY_CA"
    EBAY_FR = "EBAY_FR"
    EBAY_IT = "EBAY_IT"
    EBAY_ES = "EBAY_ES"


class ConditionId(str, Enum):
    """Item condition IDs."""
    NEW = "1000"
    NEW_OTHER = "1500"
    NEW_WITH_DEFECTS = "1750"
    CERTIFIED_REFURBISHED = "2000"
    EXCELLENT_REFURBISHED = "2010"
    VERY_GOOD_REFURBISHED = "2020"
    GOOD_REFURBISHED = "2030"
    USED_EXCELLENT = "3000"
    USED_VERY_GOOD = "4000"
    USED_GOOD = "5000"
    USED_ACCEPTABLE = "6000"
    FOR_PARTS = "7000"


class ListingStatus(str, Enum):
    """Listing status values."""
    ACTIVE = "ACTIVE"
    ENDED = "ENDED"
    SOLD = "SOLD"
    UNSOLD = "UNSOLD"


class Location(BaseModel):
    """Geographic location."""
    country: str = Field(..., description="ISO 3166-1 alpha-2 country code")
    city: Optional[str] = Field(None, description="City name")
    state_or_province: Optional[str] = Field(None, description="State or province")
    postal_code: Optional[str] = Field(None, description="Postal/ZIP code")
    
    @field_validator('country')
    @classmethod
    def validate_country(cls, v):
        if len(v) != 2:
            raise ValueError("Country must be 2-letter ISO code")
        return v.upper()


class TimePeriod(BaseModel):
    """Time period for date ranges."""
    start_date: datetime = Field(..., description="Start date/time")
    end_date: datetime = Field(..., description="End date/time")
    
    @field_validator('end_date')
    @classmethod
    def validate_dates(cls, v, info):
        if 'start_date' in info.data and v <= info.data['start_date']:
            raise ValueError("End date must be after start date")
        return v


class Dimension(BaseModel):
    """Physical dimensions."""
    length: Decimal = Field(..., gt=0, description="Length")
    width: Decimal = Field(..., gt=0, description="Width")
    height: Decimal = Field(..., gt=0, description="Height")
    unit: str = Field(..., description="Unit of measurement (in, cm, etc)")


class Weight(BaseModel):
    """Weight measurement."""
    value: Decimal = Field(..., gt=0, description="Weight value")
    unit: str = Field(..., description="Unit (lb, kg, oz, g)")


# ==================== Browse API Models ====================

class Image(BaseModel):
    """Item image."""
    url: HttpUrl = Field(..., description="Image URL")
    height: Optional[int] = Field(None, description="Image height in pixels")
    width: Optional[int] = Field(None, description="Image width in pixels")


class Category(BaseModel):
    """eBay category."""
    category_id: str = Field(..., description="Category ID")
    category_name: str = Field(..., description="Category name")
    category_path: Optional[str] = Field(None, description="Full category path")
    parent_category_id: Optional[str] = Field(None, description="Parent category ID")


class Seller(BaseModel):
    """Seller information."""
    username: str = Field(..., description="Seller username")
    feedback_percentage: Optional[float] = Field(None, ge=0, le=100, description="Positive feedback percentage")
    feedback_score: Optional[int] = Field(None, ge=0, description="Total feedback score")
    seller_level: Optional[str] = Field(None, description="Seller level (Top Rated, etc)")


class ShippingOption(BaseModel):
    """Shipping service option."""
    service_type: str = Field(..., description="Shipping service name")
    shipping_cost: Optional[Money] = Field(None, description="Shipping cost")
    estimated_delivery_date: Optional[datetime] = Field(None, description="Estimated delivery")
    expedited: bool = Field(default=False, description="Is expedited shipping")
    global_shipping: bool = Field(default=False, description="Ships internationally")


class Item(BaseModel):
    """eBay item/listing details."""
    item_id: str = Field(..., description="Unique item ID")
    title: str = Field(..., description="Item title")
    subtitle: Optional[str] = Field(None, description="Item subtitle")
    description: Optional[str] = Field(None, description="Full description")
    
    # Categorization
    primary_category: Category = Field(..., description="Primary category")
    secondary_category: Optional[Category] = Field(None, description="Secondary category")
    
    # Pricing
    price: Money = Field(..., description="Current price")
    original_price: Optional[Money] = Field(None, description="Original/MSRP price")
    discount_percentage: Optional[float] = Field(None, ge=0, le=100, description="Discount percentage")
    
    # Condition
    condition_id: Optional[ConditionId] = Field(None, description="Condition ID")
    condition_description: Optional[str] = Field(None, description="Condition description")
    
    # Images
    images: List[Image] = Field(default_factory=list, description="Item images")
    primary_image: Optional[Image] = Field(None, description="Primary image")
    
    # Seller
    seller: Seller = Field(..., description="Seller information")
    
    # Location
    item_location: Location = Field(..., description="Item location")
    
    # Shipping
    shipping_options: List[ShippingOption] = Field(default_factory=list, description="Shipping options")
    free_shipping: bool = Field(default=False, description="Free shipping available")
    
    # Listing details
    listing_status: ListingStatus = Field(..., description="Listing status")
    quantity_available: Optional[int] = Field(None, ge=0, description="Available quantity")
    quantity_sold: Optional[int] = Field(None, ge=0, description="Quantity sold")
    
    # Engagement metrics
    watch_count: Optional[int] = Field(None, ge=0, description="Number of watchers")
    view_count: Optional[int] = Field(None, ge=0, description="Number of views")
    
    # URLs
    item_url: HttpUrl = Field(..., description="Item page URL")
    view_item_url: Optional[HttpUrl] = Field(None, description="Mobile-friendly URL")
    
    # Timestamps
    listing_start_date: datetime = Field(..., description="Listing start date")
    listing_end_date: Optional[datetime] = Field(None, description="Listing end date")
    
    # Additional details
    product_id: Optional[str] = Field(None, description="Product ID (UPC, EAN, etc)")
    brand: Optional[str] = Field(None, description="Brand name")
    mpn: Optional[str] = Field(None, description="Manufacturer part number")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Decimal: lambda v: float(v)
        }


class SearchResult(BaseModel):
    """Search results container."""
    total: int = Field(..., ge=0, description="Total number of results")
    offset: int = Field(default=0, ge=0, description="Result offset")
    limit: int = Field(default=50, ge=1, le=200, description="Results per page")
    items: List[Item] = Field(default_factory=list, description="Search results")
    refinements: Optional[Dict[str, List[str]]] = Field(None, description="Search refinements")
    
    @property
    def has_more(self) -> bool:
        """Check if more results available."""
        return self.offset + len(self.items) < self.total


# ==================== Marketplace Insights Models ====================

class TrendingKeyword(BaseModel):
    """Trending search keyword."""
    keyword: str = Field(..., description="Search keyword")
    search_volume: int = Field(..., ge=0, description="Search volume")
    trend_direction: str = Field(..., description="Trend direction (up/down/stable)")
    percentage_change: float = Field(..., description="Percentage change")
    category: Optional[Category] = Field(None, description="Associated category")
    
    class Config:
        schema_extra = {
            "example": {
                "keyword": "vintage camera",
                "search_volume": 15000,
                "trend_direction": "up",
                "percentage_change": 25.5,
                "category": {"category_id": "625", "category_name": "Cameras & Photo"}
            }
        }


class CategoryInsight(BaseModel):
    """Category market insights."""
    category: Category = Field(..., description="Category information")
    average_price: Money = Field(..., description="Average selling price")
    median_price: Money = Field(..., description="Median selling price")
    total_listings: int = Field(..., ge=0, description="Total active listings")
    sell_through_rate: float = Field(..., ge=0, le=100, description="Sell-through rate percentage")
    average_days_on_market: float = Field(..., ge=0, description="Average listing duration")
    top_sellers: List[Seller] = Field(default_factory=list, description="Top sellers in category")
    price_range: Dict[str, Money] = Field(..., description="Price range (min/max)")


class SeasonalTrend(BaseModel):
    """Seasonal trend data."""
    period: str = Field(..., description="Season/period name")
    categories: List[Category] = Field(..., description="Trending categories")
    keywords: List[str] = Field(..., description="Popular keywords")
    demand_increase: float = Field(..., description="Demand increase percentage")
    optimal_listing_time: str = Field(..., description="Best time to list")
    
    class Config:
        schema_extra = {
            "example": {
                "period": "Back to School",
                "categories": [{"category_id": "617", "category_name": "Books"}],
                "keywords": ["textbooks", "backpacks", "calculators"],
                "demand_increase": 45.2,
                "optimal_listing_time": "July 15 - August 15"
            }
        }


# ==================== Inventory API Models ====================

class InventoryItem(BaseModel):
    """Inventory item for sellers."""
    sku: str = Field(..., description="Stock keeping unit")
    product: Dict[str, Any] = Field(..., description="Product details")
    condition: ConditionId = Field(..., description="Item condition")
    condition_description: Optional[str] = Field(None, description="Condition details")
    availability: Dict[str, Any] = Field(..., description="Availability details")
    package_weight_and_size: Optional[Dict[str, Any]] = Field(None, description="Package details")
    
    class Config:
        schema_extra = {
            "example": {
                "sku": "CAMERA-001",
                "product": {
                    "title": "Vintage Canon AE-1",
                    "description": "Classic 35mm film camera",
                    "brand": "Canon",
                    "mpn": "AE-1"
                },
                "condition": "USED_EXCELLENT",
                "availability": {
                    "quantity": 1,
                    "warehouse_location": "Shelf A-5"
                }
            }
        }


class Offer(BaseModel):
    """Listing offer details."""
    offer_id: Optional[str] = Field(None, description="Offer ID")
    sku: str = Field(..., description="Inventory SKU")
    marketplace_id: MarketplaceId = Field(..., description="Target marketplace")
    format: str = Field(..., description="Listing format (FIXED_PRICE, AUCTION)")
    listing_description: str = Field(..., description="Listing description")
    listing_duration: str = Field(..., description="Duration (GTC, DAYS_7, etc)")
    listing_start_date: Optional[datetime] = Field(None, description="Start date")
    pricing_summary: Dict[str, Any] = Field(..., description="Pricing details")
    listing_policies: Dict[str, str] = Field(..., description="Policy IDs")
    category_id: str = Field(..., description="eBay category ID")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# ==================== Response Models ====================

class ApiResponse(BaseModel):
    """Standard API response wrapper."""
    success: bool = Field(default=True, description="Operation success")
    data: Optional[Any] = Field(None, description="Response data")
    warnings: List[str] = Field(default_factory=list, description="Warning messages")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Response metadata")
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "data": {"item_id": "123456789"},
                "warnings": [],
                "metadata": {"api_version": "v1", "response_time": 0.123}
            }
        }


class PagedResponse(BaseModel):
    """Paginated response wrapper."""
    success: bool = Field(default=True)
    data: List[Any] = Field(default_factory=list, description="Page data")
    pagination: Dict[str, Any] = Field(..., description="Pagination info")
    total: int = Field(..., ge=0, description="Total results")
    
    @property
    def has_next(self) -> bool:
        """Check if next page exists."""
        offset = self.pagination.get("offset", 0)
        limit = self.pagination.get("limit", 50)
        return offset + limit < self.total
    
    @property
    def has_previous(self) -> bool:
        """Check if previous page exists."""
        return self.pagination.get("offset", 0) > 0


# ==================== Request Models ====================

class SearchRequest(BaseModel):
    """Item search request parameters."""
    query: str = Field(..., min_length=1, description="Search query")
    category_ids: Optional[List[str]] = Field(None, description="Category filters")
    condition_ids: Optional[List[ConditionId]] = Field(None, description="Condition filters")
    price_min: Optional[Decimal] = Field(None, ge=0, description="Minimum price")
    price_max: Optional[Decimal] = Field(None, ge=0, description="Maximum price")
    listing_type: Optional[str] = Field(None, description="Listing type filter")
    shipping_option: Optional[str] = Field(None, description="Shipping filter")
    item_location: Optional[Location] = Field(None, description="Item location filter")
    sort_order: Optional[str] = Field("BEST_MATCH", description="Sort order")
    limit: int = Field(default=50, ge=1, le=200, description="Results per page")
    offset: int = Field(default=0, ge=0, description="Result offset")
    
    @field_validator('price_max')
    @classmethod
    def validate_price_range(cls, v, info):
        if 'price_min' in info.data and v is not None and info.data.get('price_min') is not None:
            if v <= info.data['price_min']:
                raise ValueError("price_max must be greater than price_min")
        return v


class CreateListingRequest(BaseModel):
    """Create new listing request."""
    sku: str = Field(..., description="Inventory SKU")
    category_id: str = Field(..., description="eBay category ID")
    title: str = Field(..., min_length=1, max_length=80, description="Listing title")
    description: str = Field(..., min_length=1, description="Listing description")
    condition_id: ConditionId = Field(..., description="Item condition")
    price: Money = Field(..., description="Item price")
    quantity: int = Field(default=1, ge=1, description="Available quantity")
    listing_duration: str = Field(default="GTC", description="Listing duration")
    payment_policy_id: str = Field(..., description="Payment policy ID")
    return_policy_id: str = Field(..., description="Return policy ID")
    shipping_policy_id: str = Field(..., description="Shipping policy ID")
    images: List[HttpUrl] = Field(..., min_items=1, max_items=24, description="Image URLs")
    
    class Config:
        schema_extra = {
            "example": {
                "sku": "CAMERA-001",
                "category_id": "31388",
                "title": "Vintage Canon AE-1 35mm Film Camera - Excellent Condition",
                "description": "Classic camera in great working condition...",
                "condition_id": "3000",
                "price": {"value": 299.99, "currency": "USD"},
                "quantity": 1,
                "images": ["https://example.com/image1.jpg"]
            }
        }