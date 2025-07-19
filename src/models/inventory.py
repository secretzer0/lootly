"""
Inventory and product management Pydantic models for eBay APIs.

This module consolidates all models related to:
- Inventory item management
- Product information and details
- Bulk operations
- Availability and pricing

All models follow the Pydantic-First Development methodology with strong typing
and validation through Pydantic models only.
"""
from typing import Optional, Dict, List, Any
from decimal import Decimal
from pydantic import BaseModel, Field, model_validator, ConfigDict

from .enums import (
    ConditionEnum,
    AvailabilityTypeEnum,
    LocaleEnum,
    LengthUnitOfMeasureEnum,
    WeightUnitOfMeasureEnum,
    PackageTypeEnum
)


# =============================================================================
# PHYSICAL PROPERTIES MODELS
# =============================================================================

class Dimension(BaseModel):
    """Physical dimensions for items or packages."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    value: Decimal = Field(..., ge=0, description="Dimension value")
    unit: LengthUnitOfMeasureEnum = Field(..., description="Unit of measurement")


class Weight(BaseModel):
    """Weight specification for items or packages."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    value: Decimal = Field(..., ge=0, description="Weight value")
    unit: WeightUnitOfMeasureEnum = Field(..., description="Weight unit")


class PackageWeightAndSize(BaseModel):
    """Package specifications for shipping."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    # Weight specification
    weight: Weight = Field(..., description="Package weight")
    
    # Dimension specifications
    dimensions: Optional[Dict[str, Dimension]] = Field(
        None,
        description="Package dimensions (length, width, height)"
    )
    
    # Package type
    package_type: Optional[PackageTypeEnum] = Field(None, description="Type of package")


# =============================================================================
# AVAILABILITY MODELS
# =============================================================================

class PickupAtLocationAvailability(BaseModel):
    """Local pickup availability configuration."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    availability_type: AvailabilityTypeEnum = Field(..., description="Availability type")
    fulfillment_time: Optional[Dict[str, Any]] = Field(None, description="Fulfillment time specification")


class ShipToLocationAvailability(BaseModel):
    """Ship-to-home availability configuration."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    availability_type: AvailabilityTypeEnum = Field(..., description="Availability type")
    quantity: Optional[int] = Field(None, ge=0, description="Available quantity")


class Availability(BaseModel):
    """Complete availability configuration for inventory items."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    # Pickup availability
    pickup_at_location_availability: Optional[PickupAtLocationAvailability] = Field(
        None,
        description="Local pickup availability"
    )
    
    # Shipping availability
    ship_to_location_availability: Optional[ShipToLocationAvailability] = Field(
        None,
        description="Ship-to-home availability"
    )


# =============================================================================
# PRODUCT MODELS
# =============================================================================

class Product(BaseModel):
    """Product information and details."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    # REQUIRED FIELDS
    title: str = Field(..., min_length=1, max_length=80, description="Product title")
    
    # OPTIONAL FIELDS
    description: Optional[str] = Field(None, max_length=500000, description="Product description")
    aspects: Optional[Dict[str, List[str]]] = Field(None, description="Product aspects/attributes")
    brand: Optional[str] = Field(None, description="Product brand")
    mpn: Optional[str] = Field(None, description="Manufacturer part number")
    upc: Optional[List[str]] = Field(None, description="UPC codes")
    ean: Optional[List[str]] = Field(None, description="EAN codes")
    isbn: Optional[List[str]] = Field(None, description="ISBN codes")
    epid: Optional[str] = Field(None, description="eBay product ID")
    image_urls: Optional[List[str]] = Field(None, description="Product image URLs")
    
    @model_validator(mode='after')
    def validate_title_length(self):
        """Validate title meets eBay requirements."""
        if len(self.title.strip()) < 3:
            raise ValueError("Product title must be at least 3 characters long")
        return self
    
    @model_validator(mode='after')
    def validate_image_urls(self):
        """Validate image URL format and count."""
        if self.image_urls:
            if len(self.image_urls) > 12:
                raise ValueError("Maximum 12 image URLs allowed")
            
            for url in self.image_urls:
                if not url.startswith(('http://', 'https://')):
                    raise ValueError(f"Invalid image URL format: {url}")
        return self


# =============================================================================
# INVENTORY ITEM MODELS
# =============================================================================

class InventoryItemInput(BaseModel):
    """Complete input validation for inventory item operations."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    # REQUIRED FIELDS
    availability: Availability = Field(..., description="Item availability configuration")
    condition: ConditionEnum = Field(..., description="Item condition")
    product: Product = Field(..., description="Product information")
    
    # OPTIONAL FIELDS
    locale: Optional[LocaleEnum] = Field(None, description="Locale for the listing")
    package_weight_and_size: Optional[PackageWeightAndSize] = Field(
        None, 
        description="Package specifications"
    )
    
    @model_validator(mode='after')
    def validate_availability_completeness(self):
        """Ensure at least one availability type is specified."""
        if (not self.availability.pickup_at_location_availability and 
            not self.availability.ship_to_location_availability):
            raise ValueError("At least one availability type must be specified")
        return self


# =============================================================================
# BULK OPERATIONS MODELS
# =============================================================================

class BulkInventoryItemRequest(BaseModel):
    """Single inventory item request for bulk operations."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    sku: str = Field(..., min_length=1, max_length=50, description="SKU identifier")
    inventory_item: InventoryItemInput = Field(..., description="Inventory item data")


class BulkInventoryItemInput(BaseModel):
    """Input for bulk inventory item operations."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    requests: List[BulkInventoryItemRequest] = Field(
        ..., 
        min_items=1, 
        max_items=25,
        description="List of inventory item requests"
    )
    
    @model_validator(mode='after')
    def validate_unique_skus(self):
        """Ensure all SKUs in the bulk request are unique."""
        skus = [req.sku for req in self.requests]
        if len(skus) != len(set(skus)):
            raise ValueError("All SKUs in bulk request must be unique")
        return self


class PriceQuantity(BaseModel):
    """Price and quantity update specification."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    # Price fields
    price: Optional[Decimal] = Field(None, ge=0, description="Item price")
    
    # Quantity fields  
    quantity: Optional[int] = Field(None, ge=0, description="Available quantity")
    
    @model_validator(mode='after')
    def validate_at_least_one_field(self):
        """Ensure at least price or quantity is specified."""
        if self.price is None and self.quantity is None:
            raise ValueError("At least one of price or quantity must be specified")
        return self


class BulkPriceQuantityRequest(BaseModel):
    """Single price/quantity request for bulk operations."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    sku: str = Field(..., min_length=1, max_length=50, description="SKU identifier")
    price_quantity: PriceQuantity = Field(..., description="Price and/or quantity updates")


class BulkPriceQuantityInput(BaseModel):
    """Input for bulk price and quantity operations."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    requests: List[BulkPriceQuantityRequest] = Field(
        ...,
        min_items=1,
        max_items=25,
        description="List of price/quantity update requests"
    )
    
    @model_validator(mode='after')
    def validate_unique_skus(self):
        """Ensure all SKUs in the bulk request are unique."""
        skus = [req.sku for req in self.requests]
        if len(skus) != len(set(skus)):
            raise ValueError("All SKUs in bulk request must be unique")
        return self