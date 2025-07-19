"""
Browse and search-related Pydantic models for eBay APIs.

This module consolidates all models related to:
- Item searching and browsing
- Category navigation
- Item details retrieval
- Search filtering and sorting

All models follow the Pydantic-First Development methodology with strong typing
and validation through Pydantic models only.
"""
from typing import Optional, List
from decimal import Decimal
from pydantic import BaseModel, Field, field_validator, ConfigDict


# =============================================================================
# BROWSE API MODELS
# =============================================================================

class BrowseSearchInput(BaseModel):
    """Complete input validation for Browse API search operations."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    # REQUIRED FIELDS
    query: str = Field(..., min_length=1, max_length=350, description="Search keywords")
    
    # FILTERING FIELDS
    category_ids: Optional[str] = Field(None, description="Comma-separated category IDs")
    price_min: Optional[Decimal] = Field(None, ge=0, description="Minimum price filter")
    price_max: Optional[Decimal] = Field(None, ge=0, description="Maximum price filter")
    conditions: Optional[str] = Field(None, description="Item conditions (New,Used,etc)")
    sellers: Optional[str] = Field(None, description="Specific seller usernames")
    
    # SORTING AND PAGINATION
    sort: str = Field(default="BestMatch", description="Sort order")
    limit: int = Field(default=50, ge=1, le=200, description="Number of results to return")
    offset: int = Field(default=0, ge=0, description="Number of results to skip")
    
    @field_validator('price_max')
    @classmethod
    def validate_price_range(cls, v, info):
        """Validate price range logic."""
        if v is not None and 'price_min' in info.data:
            price_min = info.data.get('price_min')
            if price_min is not None and v <= price_min:
                raise ValueError("price_max must be greater than price_min")
        return v


class ItemDetailsInput(BaseModel):
    """Input validation for item details retrieval."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    # REQUIRED FIELDS
    item_id: str = Field(..., min_length=1, description="eBay item ID")
    
    # OPTIONAL FIELDS
    fieldgroups: Optional[str] = Field(
        "SUMMARY,DETAILS,PRIMARY_PHOTO,ADDITIONAL_PHOTOS", 
        description="Comma-separated list of field groups to include"
    )
    
    @field_validator('item_id')
    @classmethod
    def validate_item_id_format(cls, v):
        """Basic validation for eBay item ID format."""
        if not v.isdigit() or len(v) < 10:
            raise ValueError("Item ID must be a numeric string with at least 10 digits")
        return v


class CategoryBrowseInput(BaseModel):
    """Input validation for category browsing operations."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    # REQUIRED FIELDS
    category_id: str = Field(..., min_length=1, description="eBay category ID")
    
    # OPTIONAL FIELDS
    sort: str = Field(default="BestMatch", description="Sort order for category items")
    limit: int = Field(default=50, ge=1, le=200, description="Number of items to return")
    offset: int = Field(default=0, ge=0, description="Number of items to skip")
    filter: Optional[str] = Field(None, description="Additional filters for category browsing")
    
    @field_validator('category_id')
    @classmethod
    def validate_category_id(cls, v):
        """Validate category ID format."""
        if not v.isdigit():
            raise ValueError("Category ID must be numeric")
        return v


# =============================================================================
# MARKETPLACE INSIGHTS MODELS
# =============================================================================

class ItemSalesSearchInput(BaseModel):
    """Input validation for marketplace insights sales search."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    # REQUIRED FIELDS
    q: str = Field(..., min_length=1, max_length=350, description="Search query")
    
    # OPTIONAL FIELDS
    category_ids: Optional[str] = Field(None, description="Comma-separated category IDs")
    filter: Optional[str] = Field(None, description="Advanced filter string")
    sort: Optional[str] = Field(None, description="Sort criteria")
    limit: int = Field(default=50, ge=1, le=200, description="Number of results")
    offset: int = Field(default=0, ge=0, description="Results offset for pagination")
    
    @field_validator('limit')
    @classmethod
    def validate_limit_range(cls, v):
        """Validate limit is within API constraints."""
        if v > 200:
            raise ValueError("Limit cannot exceed 200")
        return v


# =============================================================================
# TAXONOMY MODELS
# =============================================================================

class GetDefaultCategoryTreeIdInput(BaseModel):
    """Input for getting default category tree ID."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    marketplace_id: str = Field(..., description="eBay marketplace ID")


class GetCategoryTreeInput(BaseModel):
    """Input for retrieving complete category tree."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    category_tree_id: str = Field(..., description="Category tree ID")


class GetCategorySubtreeInput(BaseModel):
    """Input for retrieving category subtree."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    category_tree_id: str = Field(..., description="Category tree ID")
    category_id: str = Field(..., description="Root category ID for subtree")


class GetCategorySuggestionsInput(BaseModel):
    """Input for category suggestions based on query."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    category_tree_id: str = Field(..., description="Category tree ID")
    q: str = Field(..., min_length=1, description="Query string for category suggestions")


class GetExpiredCategoriesInput(BaseModel):
    """Input for retrieving expired categories."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    category_tree_id: str = Field(..., description="Category tree ID")


# =============================================================================
# MARKETING MODELS
# =============================================================================

class MerchandisedProductsInput(BaseModel):
    """Input for merchandised products request."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    # OPTIONAL FIELDS
    category_id: Optional[str] = Field(None, description="Category ID for merchandised products")
    metric_name: Optional[str] = Field(None, description="Metric for product ranking")
    limit: int = Field(default=8, ge=1, le=100, description="Number of products to return")
    aspect_filter: Optional[str] = Field(None, description="Aspect-based filtering")
    
    @field_validator('limit')
    @classmethod
    def validate_merchandised_limit(cls, v):
        """Validate limit for merchandised products."""
        if v > 100:
            raise ValueError("Merchandised products limit cannot exceed 100")
        return v