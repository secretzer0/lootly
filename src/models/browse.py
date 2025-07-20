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
from typing import Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict

from models.browse_enums import SortField


# =============================================================================
# BROWSE API MODELS
# =============================================================================

class BrowseSearchInput(BaseModel):
    """
    Complete input validation for Browse API search operations.
    
    This model supports advanced searching with filtering, sorting, and pagination.
    All parameters are validated according to eBay Browse API specifications.
    """
    model_config = ConfigDict(str_strip_whitespace=True)
    
    # REQUIRED FIELDS
    q: str = Field(
        ..., 
        min_length=1, 
        max_length=300,
        description=(
            "Search keywords - max 300 characters. "
            "Use 'term1 term2' for AND search, '(term1, term2)' for OR search, "
            "'\"exact phrase\"' for phrase search"
        )
    )
    
    # FILTERING FIELDS
    category_ids: Optional[str] = Field(
        None,
        pattern=r'^\d+$',
        description="Single eBay category ID (numeric). Use Browse API category methods to find IDs"
    )
    
    filter: Optional[str] = Field(
        None,
        description=(
            "Advanced filter string with specific syntax. "
            "Examples: 'price:[10..50]', 'conditions:{NEW|LIKE_NEW}', "
            "'sellers:{user1|user2}'. Multiple filters separated by commas"
        )
    )
    
    # SORTING AND PAGINATION
    sort: Optional[SortField] = Field(
        default=SortField.BEST_MATCH,
        description="Sort order for search results. Price sort includes shipping cost"
    )
    
    limit: int = Field(
        default=50, 
        ge=1, 
        le=200, 
        description="Number of results to return (1-200)"
    )
    
    offset: int = Field(
        default=0, 
        ge=0, 
        description="Number of results to skip for pagination"
    )
    
    @field_validator('category_ids')
    @classmethod
    def validate_single_category(cls, v):
        """Ensure only one category ID is provided."""
        if v and ',' in v:
            raise ValueError("Only one category ID allowed per search")
        return v


class ItemDetailsInput(BaseModel):
    """
    Input validation for item details retrieval.
    
    Supports both modern RESTful item IDs and legacy item IDs from older eBay APIs.
    The tool automatically detects which type of ID is provided.
    """
    model_config = ConfigDict(str_strip_whitespace=True)
    
    # REQUIRED FIELDS
    item_id: str = Field(
        ..., 
        min_length=1,
        description=(
            "Item identifier - accepts two formats:\n"
            "1. RESTful ID (v1|123456789|0): Returned by Browse API methods\n"
            "2. Legacy ID (123456789): From older eBay APIs (Shopping, Finding, Trading)"
        )
    )
    
    @field_validator('item_id')
    @classmethod
    def validate_item_id_format(cls, v):
        """
        Validate and determine item ID type.
        
        RESTful format: v1|{listing_id}|{transaction_id}
        Legacy format: Numeric string (10-19 digits)
        """
        # RESTful format: v1|...|...
        if v.startswith('v1|') and v.count('|') >= 2:
            parts = v.split('|')
            # Validate middle part is numeric
            if len(parts) >= 3 and parts[1].isdigit():
                return v
            else:
                raise ValueError(
                    "Invalid RESTful item ID format. "
                    "Expected: v1|{numeric_id}|{transaction_id}"
                )
        # Legacy format: numeric only
        elif v.isdigit() and 10 <= len(v) <= 19:
            return v
        else:
            raise ValueError(
                "Invalid item ID format. Use either:\n"
                "- RESTful: v1|123456789|0 (from Browse API)\n"
                "- Legacy: 123456789 (10-19 digit numeric)"
            )



# =============================================================================
# MARKETPLACE INSIGHTS MODELS
# =============================================================================

class ItemSalesSearchInput(BaseModel):
    """Input validation for marketplace insights sales search."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    # OPTIONAL FIELDS  
    q: Optional[str] = Field(None, min_length=1, max_length=100, description="Search query")
    
    # OPTIONAL FIELDS
    categoryIds: Optional[str] = Field(None, description="Comma-separated category IDs")
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
    
    def validate_search_criteria(self):
        """Validate that at least one search criterion is provided."""
        if not self.q and not self.categoryIds and not self.filter:
            raise ValueError("At least one search criterion is required (q, categoryIds, or filter)")


# =============================================================================
# TAXONOMY MODELS
# =============================================================================

class GetDefaultCategoryTreeIdInput(BaseModel):
    """Input for getting default category tree ID."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    marketplaceId: str = Field(..., description="eBay marketplace ID")


class GetCategoryTreeInput(BaseModel):
    """Input for retrieving complete category tree."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    categoryTreeId: str = Field(..., description="Category tree ID")


class GetCategorySubtreeInput(BaseModel):
    """Input for retrieving category subtree."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    categoryTreeId: str = Field(..., description="Category tree ID")
    categoryId: str = Field(..., description="Root category ID for subtree")


class GetCategorySuggestionsInput(BaseModel):
    """Input for category suggestions based on query."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    categoryTreeId: str = Field(..., description="Category tree ID")
    q: str = Field(..., min_length=1, description="Query string for category suggestions")


class GetExpiredCategoriesInput(BaseModel):
    """Input for retrieving expired categories."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    categoryTreeId: str = Field(..., description="Category tree ID")


# =============================================================================
# MARKETING MODELS
# =============================================================================

class MerchandisedProductsInput(BaseModel):
    """Input for merchandised products request."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    # OPTIONAL FIELDS
    categoryId: Optional[str] = Field(None, description="Category ID for merchandised products")
    metricName: Optional[str] = Field(None, description="Metric for product ranking")
    limit: int = Field(default=8, ge=1, le=100, description="Number of products to return")
    aspectFilter: Optional[str] = Field(None, description="Aspect-based filtering")
    
    @field_validator('categoryId')
    @classmethod
    def validate_category_id(cls, v):
        """Validate category ID format."""
        if v and not v.isdigit():
            raise ValueError("Category ID must be numeric")
        return v
    
    @field_validator('limit')
    @classmethod
    def validate_merchandised_limit(cls, v):
        """Validate limit for merchandised products."""
        if v > 100:
            raise ValueError("Merchandised products limit cannot exceed 100")
        return v