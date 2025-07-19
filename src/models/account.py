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
from pydantic import BaseModel, Field, ConfigDict

from .enums import (
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
    
    # Account status - using eBay's exact camelCase field names
    sellerRegistrationCompleted: bool = Field(..., description="Whether seller registration is complete")
    
    # Selling limits - using eBay's exact camelCase field names
    sellingLimit: Optional[SellingLimit] = Field(None, description="Monthly selling limits")


# =============================================================================
# SELLER PROGRAMS MODELS
# =============================================================================

class Program(BaseModel):
    """Individual eBay seller program representation."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    programType: ProgramTypeEnum = Field(..., description="Type of seller program")


class ProgramsResponse(BaseModel):
    """Response for seller programs listing."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    programs: List[Program] = Field(default_factory=list, description="List of available programs")


class OptInOutInput(BaseModel):
    """Input for program opt-in/opt-out operations."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    programType: ProgramTypeEnum = Field(..., description="Program to opt in/out of")


