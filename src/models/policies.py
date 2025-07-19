"""
Policy-related Pydantic models for eBay business policies.

This module consolidates all models related to eBay seller business policies:
- Fulfillment (shipping) policies
- Return policies  
- Payment policies

All models follow the Pydantic-First Development methodology with strong typing
and validation through Pydantic models only.
"""
from typing import Optional, Dict, Any, List
from decimal import Decimal
from pydantic import BaseModel, Field, model_validator, ConfigDict

from .enums import (
    MarketplaceIdEnum,
    CategoryTypeEnum,
    ShippingCostTypeEnum,
    ShippingOptionTypeEnum,
    TimeDurationUnitEnum,
    CurrencyCodeEnum,
    PaymentInstrumentBrandEnum,
    PaymentMethodTypeEnum,
    RecipientAccountReferenceTypeEnum,
    RefundMethodEnum,
    ReturnMethodEnum,
    ReturnShippingCostPayerEnum
)
from .common import Amount, CategoryType, TimeDuration, Region, RegionSet


# =============================================================================
# PAYMENT POLICY MODELS
# =============================================================================

class PaymentMethod(BaseModel):
    """Offline payment method configuration."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    payment_method_type: PaymentMethodTypeEnum = Field(..., description="Type of offline payment method")
    
    # Recipient account only for certain types
    recipient_account_reference: Optional[Dict[str, str]] = Field(
        None, 
        description="Recipient account info for certain payment types"
    )
    
    @model_validator(mode='after')
    def validate_recipient_account(self):
        """Validate recipient account requirements."""
        # PayPal and other electronic methods may require recipient account
        # For now, no strict validation as requirements vary by marketplace
        return self


class DepositDueIn(BaseModel):
    """When deposit payment is due for motor vehicles."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    value: int = Field(..., description="Number of hours (24, 48, or 72)")
    unit: TimeDurationUnitEnum = Field(default=TimeDurationUnitEnum.HOUR, description="Time unit (must be HOUR)")
    
    @model_validator(mode='after')
    def validate_deposit_due_in(self):
        """Validate deposit due_in requirements per eBay API."""
        if self.unit != TimeDurationUnitEnum.HOUR:
            raise ValueError("Deposit due_in unit must be HOUR")
        if self.value not in [24, 48, 72]:
            raise ValueError("Deposit due_in value must be 24, 48, or 72 hours")
        return self


class Deposit(BaseModel):
    """Deposit configuration for motor vehicle listings."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    # Required fields
    due_in: DepositDueIn = Field(..., description="When deposit payment is due (24, 48, or 72 hours)")
    amount: Decimal = Field(..., ge=0, decimal_places=2, description="Deposit amount")
    
    # Optional payment methods for deposit
    payment_methods: Optional[List[PaymentMethod]] = Field(
        None,
        description="Accepted payment methods for deposit"
    )
    
    @model_validator(mode='after')
    def validate_deposit_amount(self):
        """Ensure deposit amount is reasonable."""
        if self.amount > Decimal('50000'):
            raise ValueError("Deposit amount seems unreasonably high")
        return self


class FullPaymentDueIn(BaseModel):
    """Full payment due configuration."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    value: int = Field(..., ge=0, le=999, description="Number of time units")
    unit: TimeDurationUnitEnum = Field(..., description="Time unit")


class PaymentPolicyInput(BaseModel):
    """
    Complete input validation for payment policy operations.
    
    Maps ALL fields from eBay API createPaymentPolicy Request Fields exactly.
    """
    model_config = ConfigDict(str_strip_whitespace=True)
    
    # REQUIRED FIELDS
    name: str = Field(..., min_length=1, max_length=64, description="Policy name")
    marketplace_id: MarketplaceIdEnum = Field(..., description="eBay marketplace ID")
    category_types: List[CategoryType] = Field(..., description="Category types this policy applies to")
    
    # OPTIONAL FIELDS
    description: Optional[str] = Field(None, max_length=250, description="Internal policy description")
    
    # Immediate payment flag
    immediate_pay: Optional[bool] = Field(
        False, 
        description="Whether immediate payment is required"
    )
    
    # Payment methods - typically managed by eBay
    payment_methods: Optional[List[PaymentMethod]] = Field(
        None,
        description="Offline payment methods accepted"
    )
    
    # Motor vehicle specific fields
    deposit: Optional[Deposit] = Field(
        None,
        description="Deposit requirements for motor vehicles"
    )
    
    full_payment_due_in: Optional[FullPaymentDueIn] = Field(
        None,
        description="When full payment is due for motor vehicles"
    )
    
    # Accepted payment instruments (cards)
    payment_instrument_brands: Optional[List[PaymentInstrumentBrandEnum]] = Field(
        None,
        description="Credit card brands accepted"
    )
    
    @model_validator(mode='after')
    def validate_motor_vehicle_requirements(self):
        """Validate motor vehicle category requirements."""
        has_motors_category = any(
            ct.name == CategoryTypeEnum.MOTORS_VEHICLES 
            for ct in self.category_types
        )
        
        # If motor vehicles category and has deposit, validate full payment due
        if has_motors_category and self.deposit and not self.full_payment_due_in:
            raise ValueError(
                "full_payment_due_in is required when deposit is specified for motor vehicle listings"
            )
        
        # Validate immediate pay restrictions
        if has_motors_category and self.immediate_pay:
            raise ValueError(
                "immediate_pay cannot be true for motor vehicle listings"
            )
        
        return self
    
    @model_validator(mode='after')
    def validate_payment_methods(self):
        """Validate payment method configurations."""
        # If payment methods specified, ensure they're appropriate
        if self.payment_methods:
            # Check for duplicate payment method types
            method_types = [m.payment_method_type for m in self.payment_methods]
            if len(method_types) != len(set(method_types)):
                raise ValueError("Duplicate payment method types are not allowed")
        
        return self


# Alias for update operations
UpdatePaymentPolicyInput = PaymentPolicyInput


# =============================================================================
# RETURN POLICY MODELS
# =============================================================================

class InternationalReturnOverride(BaseModel):
    """International return policy override settings."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    returns_accepted: bool = Field(..., description="Whether international returns are accepted")
    return_period: Optional[TimeDuration] = Field(None, description="Return period for international buyers")
    return_shipping_cost_payer: Optional[ReturnShippingCostPayerEnum] = Field(None, description="Who pays international return shipping")
    return_method: Optional[ReturnMethodEnum] = Field(None, description="Return method for international buyers")
    
    @model_validator(mode='after')
    def validate_conditional_fields(self):
        """Validate conditional requirements for international returns."""
        if self.returns_accepted:
            if not self.return_period:
                raise ValueError("return_period is required when returns_accepted is true for international override")
            if not self.return_shipping_cost_payer:
                raise ValueError("return_shipping_cost_payer is required when returns_accepted is true for international override")
        return self


class ReturnPolicyInput(BaseModel):
    """
    Complete input validation for return policy operations.
    
    Maps ALL fields from eBay API createReturnPolicy Request Fields exactly.
    """
    model_config = ConfigDict(str_strip_whitespace=True)
    
    # REQUIRED FIELDS
    name: str = Field(..., min_length=1, max_length=64, description="Policy name")
    marketplace_id: MarketplaceIdEnum = Field(..., description="eBay marketplace ID")
    category_types: List[CategoryType] = Field(..., description="Category types this policy applies to")
    returns_accepted: bool = Field(..., description="Whether returns are accepted")
    
    # CONDITIONAL FIELDS (required when returns_accepted=true)
    return_period: Optional[TimeDuration] = Field(None, description="Return window duration")
    return_shipping_cost_payer: Optional[ReturnShippingCostPayerEnum] = Field(None, description="Who pays return shipping")
    
    # OPTIONAL FIELDS
    description: Optional[str] = Field(None, max_length=250, description="Internal policy description")
    refund_method: Optional[RefundMethodEnum] = Field(RefundMethodEnum.MONEY_BACK, description="Type of refund offered")
    return_method: Optional[ReturnMethodEnum] = Field(None, description="Return method offered")
    return_instructions: Optional[str] = Field(None, max_length=5000, description="Instructions for buyers on how to return items")
    international_override: Optional[InternationalReturnOverride] = Field(None, description="International return policy override")
    
    # DEPRECATED FIELDS (still included per PRP requirements)
    extended_holiday_returns_offered: Optional[bool] = Field(None, description="Deprecated - no longer supported")
    restocking_fee_percentage: Optional[str] = Field(None, description="Deprecated - no longer supported")
    
    @model_validator(mode='after')
    def validate_conditional_fields(self):
        """Validate conditional requirements based on returns_accepted."""
        if self.returns_accepted:
            if not self.return_period:
                raise ValueError("return_period is required when returns_accepted is true")
            if not self.return_shipping_cost_payer:
                raise ValueError("return_shipping_cost_payer is required when returns_accepted is true")
        return self


# Alias for update operations
UpdateReturnPolicyInput = ReturnPolicyInput


# =============================================================================
# FULFILLMENT POLICY MODELS  
# =============================================================================

class ShippingService(BaseModel):
    """Individual shipping service configuration."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    # Required fields
    shipping_service_code: str = Field(..., description="eBay shipping service code")
    shipping_cost: Amount = Field(..., description="Cost for this shipping service")
    
    # Optional fields
    additional_shipping_cost: Optional[Amount] = Field(None, description="Additional shipping cost for extra items")
    shipping_carrier_code: Optional[str] = Field(None, description="Carrier code (USPS, UPS, etc.)")
    free_shipping: Optional[bool] = Field(False, description="Whether shipping is free")
    
    @model_validator(mode='after')
    def validate_free_shipping_cost(self):
        """Validate that free shipping has zero cost."""
        if self.free_shipping and self.shipping_cost.value > 0:
            raise ValueError("Free shipping must have zero shipping cost")
        return self


class ShippingOption(BaseModel):
    """Shipping option configuration for fulfillment policy."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    # Required fields
    option_type: ShippingOptionTypeEnum = Field(..., description="Type of shipping option")
    cost_type: ShippingCostTypeEnum = Field(..., description="How shipping cost is calculated")
    shipping_services: List[ShippingService] = Field(..., description="Available shipping services")
    
    # Optional fields  
    package_handling_cost: Optional[Amount] = Field(None, description="Handling cost for packaging")
    shipping_discount: Optional[Dict[str, Any]] = Field(None, description="Shipping discount configuration")
    
    @model_validator(mode='after')
    def validate_shipping_services(self):
        """Validate shipping services list."""
        if not self.shipping_services:
            raise ValueError("At least one shipping service is required")
        if len(self.shipping_services) > 4:
            raise ValueError("Maximum 4 shipping services allowed")
        return self


class FulfillmentPolicyInput(BaseModel):
    """
    Complete input validation for fulfillment policy operations.
    
    Maps ALL fields from eBay API createFulfillmentPolicy Request Fields exactly.
    """
    model_config = ConfigDict(str_strip_whitespace=True)
    
    # REQUIRED FIELDS
    name: str = Field(..., min_length=1, max_length=64, description="Policy name")
    marketplace_id: MarketplaceIdEnum = Field(..., description="eBay marketplace ID")
    category_types: List[CategoryType] = Field(..., description="Category types this policy applies to")
    handling_time: TimeDuration = Field(..., description="Handling time before shipment")
    shipping_options: List[ShippingOption] = Field(..., description="Available shipping options")
    
    # OPTIONAL FIELDS
    description: Optional[str] = Field(None, max_length=250, description="Internal policy description")
    local_pickup: Optional[bool] = Field(False, description="Whether local pickup is offered")
    freight_shipping: Optional[bool] = Field(False, description="Whether freight shipping is offered")
    ship_to_locations: Optional[RegionSet] = Field(None, description="Regions where items can be shipped")
    
    @model_validator(mode='after')
    def validate_shipping_options(self):
        """Validate shipping options configuration."""
        if not self.shipping_options:
            raise ValueError("At least one shipping option is required")
        if len(self.shipping_options) > 2:  # Typically domestic + international
            raise ValueError("Maximum 2 shipping options allowed (domestic + international)")
        return self
    
    @model_validator(mode='after')
    def validate_handling_time(self):
        """Validate handling time constraints."""
        if self.handling_time.unit not in [TimeDurationUnitEnum.DAY, TimeDurationUnitEnum.BUSINESS_DAY]:
            raise ValueError("Handling time unit must be DAY or BUSINESS_DAY")
        if self.handling_time.value > 30:
            raise ValueError("Handling time cannot exceed 30 days")
        return self


class FulfillmentPolicyResponse(FulfillmentPolicyInput):
    """
    Response model for fulfillment policy operations.
    
    Extends the input model with additional response fields.
    """
    fulfillment_policy_id: Optional[str] = Field(None, description="eBay fulfillment policy ID")
    warnings: Optional[List[Dict[str, Any]]] = Field(None, description="API warnings")