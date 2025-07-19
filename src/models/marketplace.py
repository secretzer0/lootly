"""
Marketplace and Insights Models for eBay APIs

This module contains pydantic models for marketplace insights, trending items,
and merchandising functionality.
"""

from typing import Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict
from .enums import MarketplaceIdEnum


class TrendingItemsInput(BaseModel):
    """
    Input validation for trending items requests.
    
    Used for finding trending and popular items using strategic Browse API searches.
    """
    model_config = ConfigDict(str_strip_whitespace=True)
    
    category_id: Optional[str] = Field(None, description="eBay category ID to filter by")
    max_results: int = Field(20, ge=1, le=100, description="Maximum number of items to return")
    marketplace_id: MarketplaceIdEnum = Field(MarketplaceIdEnum.EBAY_US, description="eBay marketplace ID")
    
    @field_validator('category_id')
    @classmethod
    def validate_category_id(cls, v):
        """Validate category ID is not empty if provided."""
        if v is not None and (not v or not v.strip()):
            raise ValueError("Category ID cannot be empty if provided")
        return v.strip() if v else None