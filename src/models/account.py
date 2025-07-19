"""
Account and seller management Pydantic models for eBay APIs.

This module consolidates all models related to:
- Account privileges and limits
- Seller programs and enrollment
- Account information and settings

All models follow the Pydantic-First Development methodology with strong typing
and validation through Pydantic models only.
"""
from typing import Optional, List
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict

from .enums import (
    CurrencyCodeEnum,
    ProgramTypeEnum
)
from .common import Amount


# =============================================================================
# ACCOUNT PRIVILEGES MODELS
# =============================================================================

class SellingLimit(BaseModel):
    """Monthly selling limits for seller account."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    amount: Amount = Field(..., description="Maximum monthly selling amount")
    quantity: int = Field(..., ge=0, description="Maximum number of items per month")


class PrivilegesResponse(BaseModel):
    """Account privileges and limits response."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    # Account status
    seller_registration_completed: bool = Field(..., description="Whether seller registration is complete")
    
    # Selling limits
    selling_limit: Optional[SellingLimit] = Field(None, description="Monthly selling limits")
    
    # Additional privileges
    qualified_for_fixed_price_on_auction: Optional[bool] = Field(
        None, 
        description="Can use Buy It Now on auction listings"
    )
    
    qualified_for_auction_only_selling: Optional[bool] = Field(
        None,
        description="Can create auction-only listings"
    )


# =============================================================================
# SELLER PROGRAMS MODELS
# =============================================================================

class Program(BaseModel):
    """Individual eBay seller program representation."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    program_type: ProgramTypeEnum = Field(..., description="Type of seller program")
    program_status: Optional[str] = Field(None, description="Current enrollment status")
    
    # Additional program details
    benefits: Optional[List[str]] = Field(None, description="Program benefits")
    requirements: Optional[List[str]] = Field(None, description="Program requirements")


class ProgramsResponse(BaseModel):
    """Response for seller programs listing."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    programs: List[Program] = Field(default_factory=list, description="List of available programs")


class OptInOutInput(BaseModel):
    """Input for program opt-in/opt-out operations."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    program_type: ProgramTypeEnum = Field(..., description="Program to opt in/out of")
    opt_in_status: bool = Field(..., description="True to opt in, False to opt out")


# =============================================================================
# ACCOUNT INFORMATION MODELS
# =============================================================================

class AccountInfo(BaseModel):
    """Basic account information."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    # Account identifiers
    user_id: Optional[str] = Field(None, description="eBay user ID")
    username: Optional[str] = Field(None, description="eBay username")
    
    # Account status
    registration_completed: bool = Field(default=False, description="Registration status")
    store_owner: Optional[bool] = Field(None, description="Whether user has an eBay Store")
    
    # Business information
    business_account: Optional[bool] = Field(None, description="Whether this is a business account")
    company_name: Optional[str] = Field(None, description="Company name for business accounts")
    
    # Location information
    primary_marketplace: Optional[str] = Field(None, description="Primary marketplace ID")
    supported_marketplaces: Optional[List[str]] = Field(None, description="List of supported marketplace IDs")