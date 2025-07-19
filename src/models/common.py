"""
Common Pydantic Models for eBay APIs

This module contains shared models used across multiple eBay API tools,
eliminating duplication and providing consistent validation.
"""

from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
from .enums import (
    CurrencyCodeEnum,
    CategoryTypeEnum, 
    TimeDurationUnitEnum,
    RegionTypeEnum
)


class Amount(BaseModel):
    """
    Monetary amount with currency.
    
    Used for all monetary values across eBay APIs (prices, fees, limits, etc).
    Consolidates the duplicate Amount models from various tool files.
    """
    model_config = ConfigDict(str_strip_whitespace=True)
    
    currency: CurrencyCodeEnum = Field(..., description="3-letter ISO 4217 currency code")
    value: str = Field(..., description="Monetary amount as decimal string")


class CategoryType(BaseModel):
    """
    Category type for business policies.
    
    Defines which category types a business policy applies to.
    Consolidates the duplicate CategoryType models from policy APIs.
    """
    model_config = ConfigDict(str_strip_whitespace=True)
    
    name: CategoryTypeEnum = Field(..., description="Category type name")
    default: Optional[bool] = Field(None, description="Whether this is the default category type")


class TimeDuration(BaseModel):
    """
    Time duration with configurable validation limits.
    
    Used for various time-based fields across eBay APIs with different
    maximum values depending on context (handling time, return periods, etc).
    Consolidates the duplicate TimeDuration models from various APIs.
    """
    model_config = ConfigDict(str_strip_whitespace=True)
    
    value: int = Field(..., gt=0, description="Number of time units")
    unit: TimeDurationUnitEnum = Field(..., description="Time unit")
    
    @classmethod 
    def for_handling_time(cls):
        """Create TimeDuration with handling time constraints (max 30 days)."""
        class HandlingTimeDuration(cls):
            value: int = Field(..., gt=0, le=30, description="Number of time units (max 30 days)")
        return HandlingTimeDuration
    
    @classmethod
    def for_return_period(cls):
        """Create TimeDuration with return period constraints (max 365 days)."""
        class ReturnPeriodDuration(cls):
            value: int = Field(..., gt=0, le=365, description="Number of time units (max 365 days)")
        return ReturnPeriodDuration
    
    @classmethod
    def for_payment_terms(cls):
        """Create TimeDuration with payment term constraints (max 999 units)."""
        class PaymentTermDuration(cls):
            value: int = Field(..., gt=0, le=999, description="Number of time units (max 999)")
        return PaymentTermDuration


class Region(BaseModel):
    """
    Geographic region for shipping locations.
    
    Can represent world regions, countries, states/provinces, or special domestic regions.
    Used in shipping policy configurations.
    """
    model_config = ConfigDict(str_strip_whitespace=True)
    
    region_name: str = Field(..., description="Name of region as defined by eBay (e.g., 'US', 'Asia', 'CA')")
    region_type: Optional[RegionTypeEnum] = Field(None, description="Type of region")


class RegionSet(BaseModel):
    """Shipping regions configuration for included and excluded locations."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    region_included: Optional[list[Region]] = Field(None, description="List of regions where shipping is offered")
    region_excluded: Optional[list[Region]] = Field(None, description="List of regions excluded from shipping")