"""
Marketplace and Insights Models for eBay APIs

This module contains pydantic models for marketplace insights, trending items,
and merchandising functionality.
"""

from typing import Optional, List
from pydantic import BaseModel, Field, field_validator, ConfigDict
from enum import Enum
from .enums import MarketplaceIdEnum


class BuyingOption(Enum):
    """eBay buying options."""
    AUCTION = "AUCTION"
    FIXED_PRICE = "FIXED_PRICE"
    BEST_OFFER = "BEST_OFFER"
    
    @classmethod
    def get_all(cls):
        """Get all buying option values."""
        return [option.value for option in cls]


class DeliveryOption(Enum):
    """Delivery options for items."""
    SHIP_TO_HOME = "SHIP_TO_HOME"
    LOCAL_PICKUP = "LOCAL_PICKUP"
    
    @classmethod
    def get_all(cls):
        """Get all delivery option values."""
        return [option.value for option in cls]


class PriceCurrency(Enum):
    """Supported currencies for price filters."""
    USD = "USD"
    CAD = "CAD"
    GBP = "GBP"
    EUR = "EUR"
    AUD = "AUD"


class SellerAccountType(Enum):
    """Seller account types."""
    BUSINESS = "BUSINESS"
    INDIVIDUAL = "INDIVIDUAL"


class ItemLocationRegion(Enum):
    """Item location regions."""
    US = "US"
    NORTH_AMERICA = "NORTH_AMERICA"
    EUROPE = "EUROPE"
    ASIA = "ASIA"
    WORLDWIDE = "WORLDWIDE"


class QualifiedProgram(Enum):
    """eBay qualified programs."""
    EBAY_PLUS = "EBAY_PLUS"
    TOP_RATED_PLUS = "TOP_RATED_PLUS"
    AUTHENTICITY_GUARANTEE = "AUTHENTICITY_GUARANTEE"
    AUTHENTICITY_VERIFICATION = "AUTHENTICITY_VERIFICATION"


class ItemSalesSearchInput(BaseModel):
    """Input validation for item sales search requests."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    # REQUIRED FIELDS
    epid: Optional[str] = Field(None, description="eBay Product ID")
    gtin: Optional[str] = Field(None, description="Global Trade Item Number")
    
    # OPTIONAL SEARCH FILTERS
    conditionIds: Optional[List[str]] = Field(None, description="Item condition IDs")
    buyingOptions: Optional[List[BuyingOption]] = Field(None, description="Buying options filter")
    deliveryOptions: Optional[List[DeliveryOption]] = Field(None, description="Delivery options filter")
    itemLocationRegion: Optional[ItemLocationRegion] = Field(None, description="Item location region")
    priceLowerLimit: Optional[str] = Field(None, description="Minimum price with currency (e.g., '10.00|USD')")
    priceUpperLimit: Optional[str] = Field(None, description="Maximum price with currency (e.g., '100.00|USD')")
    sellerAccountTypes: Optional[List[SellerAccountType]] = Field(None, description="Seller account types")
    qualifiedPrograms: Optional[List[QualifiedProgram]] = Field(None, description="eBay qualified programs")
    
    # PAGINATION
    limit: int = Field(default=100, ge=1, le=200, description="Maximum results to return")
    offset: int = Field(default=0, ge=0, description="Result offset for pagination")
    
    @field_validator('priceLowerLimit', 'priceUpperLimit')
    @classmethod
    def validate_price_format(cls, v):
        """Validate price format includes currency."""
        if v and '|' not in v:
            raise ValueError("Price must include currency in format 'amount|currency' (e.g., '10.00|USD')")
        return v
    
    def model_post_init(self, __context):
        """Validate that at least one identifier is provided."""
        if not self.epid and not self.gtin:
            raise ValueError("Either epid or gtin must be provided")


class TrendingItemsInput(BaseModel):
    """
    Input validation for trending items requests.
    
    Used for finding trending and popular items using strategic Browse API searches.
    """
    model_config = ConfigDict(str_strip_whitespace=True)
    
    categoryId: Optional[str] = Field(None, description="eBay category ID to filter by")
    maxResults: int = Field(20, ge=1, le=100, description="Maximum number of items to return")
    marketplaceId: MarketplaceIdEnum = Field(MarketplaceIdEnum.EBAY_US, description="eBay marketplace ID")
    
    @field_validator('categoryId')
    @classmethod
    def validate_category_id(cls, v):
        """Validate category ID is not empty if provided."""
        if v is not None and (not v or not v.strip()):
            raise ValueError("Category ID cannot be empty if provided")
        return v.strip() if v else None