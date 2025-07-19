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
    PaymentInstrumentBrandEnum,
    PaymentMethodTypeEnum,
    RefundMethodEnum,
    ReturnMethodEnum,
    ReturnShippingCostPayerEnum
)
from .common import Amount, CategoryType, TimeDuration, RegionSet


# =============================================================================
# PAYMENT POLICY MODELS
# =============================================================================

class PaymentMethod(BaseModel):
    """Offline payment method configuration."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    payment_method_type: PaymentMethodTypeEnum = Field(..., description="Type of offline payment method")
    
    # Payment instrument brands (for credit cards, etc)
    brands: Optional[List[PaymentInstrumentBrandEnum]] = Field(
        None,
        description="Accepted payment instrument brands"
    )
    
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
    marketplaceId: MarketplaceIdEnum = Field(..., description="eBay marketplace ID")
    categoryTypes: List[CategoryType] = Field(..., description="Category types this policy applies to")
    
    # OPTIONAL FIELDS
    description: Optional[str] = Field(None, max_length=250, description="Internal policy description")
    
    # Immediate payment flag
    immediatePay: Optional[bool] = Field(
        False, 
        description="Whether immediate payment is required"
    )
    
    # Payment methods - typically managed by eBay
    paymentMethods: Optional[List[PaymentMethod]] = Field(
        None,
        description="Offline payment methods accepted"
    )
    
    # Motor vehicle specific fields
    deposit: Optional[Deposit] = Field(
        None,
        description="Deposit requirements for motor vehicles"
    )
    
    fullPaymentDueIn: Optional[FullPaymentDueIn] = Field(
        None,
        description="When full payment is due for motor vehicles"
    )
    
    # Accepted payment instruments (cards)
    paymentInstrumentBrands: Optional[List[PaymentInstrumentBrandEnum]] = Field(
        None,
        description="Credit card brands accepted"
    )
    
    @model_validator(mode='after')
    def validate_motor_vehicle_requirements(self):
        """Validate motor vehicle category requirements."""
        has_motors_category = any(
            ct.name == CategoryTypeEnum.MOTORS_VEHICLES 
            for ct in self.categoryTypes
        )
        
        # If motor vehicles category and has deposit, validate full payment due
        if has_motors_category and self.deposit and not self.fullPaymentDueIn:
            raise ValueError(
                "fullPaymentDueIn is required when deposit is specified for motor vehicle listings"
            )
        
        # Validate immediate pay restrictions
        if has_motors_category and self.immediatePay:
            raise ValueError(
                "immediatePay cannot be true for motor vehicle listings"
            )
        
        return self
    
    @model_validator(mode='after')
    def validate_payment_methods(self):
        """Validate payment method configurations."""
        # If payment methods specified, ensure they're appropriate
        if self.paymentMethods:
            # Check for duplicate payment method types
            method_types = [m.paymentMethodType for m in self.paymentMethods]
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
        """Validate conditional requirements based on returnsAccepted."""
        if self.returnsAccepted:
            if not self.returnPeriod:
                raise ValueError("returnPeriod is required when returnsAccepted is true")
            if not self.returnShippingCostPayer:
                raise ValueError("returnShippingCostPayer is required when returnsAccepted is true")
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
    shippingServiceCode: str = Field(..., description="eBay shipping service code")
    
    # Optional fields - conditionally required based on cost type
    additionalShippingCost: Optional[Amount] = Field(None, description="Additional shipping cost for extra items")
    buyerResponsibleForPickup: Optional[bool] = Field(None, description="Buyer responsible for pickup (motor vehicles)")
    buyerResponsibleForShipping: Optional[bool] = Field(None, description="Buyer responsible for shipping (motor vehicles)")
    freeShipping: Optional[bool] = Field(None, description="Whether shipping is free")
    shippingCarrierCode: Optional[str] = Field(None, description="Carrier code (USPS, UPS, etc.)")
    shippingCost: Optional[Amount] = Field(None, description="Cost for this shipping service")
    shipToLocations: Optional[RegionSet] = Field(None, description="Geographical shipping regions")
    sortOrder: Optional[int] = Field(None, ge=1, le=5, description="Display order of shipping options")


class ShippingOption(BaseModel):
    """Shipping option configuration for fulfillment policy."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    # Required fields
    costType: ShippingCostTypeEnum = Field(..., description="How shipping cost is calculated")
    optionType: ShippingOptionTypeEnum = Field(..., description="Type of shipping option")
    
    # Optional fields
    packageHandlingCost: Optional[Amount] = Field(None, description="Handling cost for packaging")
    rateTableId: Optional[str] = Field(None, description="Shipping rate table ID")
    shippingServices: Optional[List[ShippingService]] = Field(None, description="Available shipping services")
    shippingDiscountProfileId: Optional[str] = Field(None, description="Shipping discount profile ID")
    shippingPromotionOffered: Optional[bool] = Field(None, description="Promotional shipping discount available")
    
    @model_validator(mode='after')
    def validate_shipping_services(self):
        """Validate shipping services list."""
        if self.shippingServices:
            max_services = 4 if self.optionType == ShippingOptionTypeEnum.DOMESTIC else 5
            if len(self.shippingServices) > max_services:
                raise ValueError(f"Maximum {max_services} shipping services allowed for {self.optionType.value}")
        return self


class FulfillmentPolicyInput(BaseModel):
    """
    Complete input validation for fulfillment policy operations.
    
    Maps ALL fields from eBay API createFulfillmentPolicy Request Fields exactly.
    """
    model_config = ConfigDict(str_strip_whitespace=True)
    
    # REQUIRED FIELDS
    name: str = Field(..., min_length=1, max_length=64, description="Policy name")
    marketplaceId: MarketplaceIdEnum = Field(..., description="eBay marketplace ID")
    categoryTypes: List[CategoryType] = Field(..., description="Category types this policy applies to")
    
    # OPTIONAL FIELDS
    description: Optional[str] = Field(None, max_length=250, description="Internal policy description")
    freightShipping: Optional[bool] = Field(None, description="Whether freight shipping is offered")
    globalShipping: Optional[bool] = Field(None, description="Whether eBay Global Shipping is used")
    handlingTime: Optional[TimeDuration] = Field(None, description="Handling time before shipment")
    localPickup: Optional[bool] = Field(None, description="Whether local pickup is offered")
    pickupDropOff: Optional[List[str]] = Field(None, description="Pickup drop-off options")
    shipToLocations: Optional[RegionSet] = Field(None, description="Regions where items can be shipped")
    shippingOptions: Optional[List[ShippingOption]] = Field(None, description="Available shipping options")
    
    @model_validator(mode='after')
    def validate_conditional_requirements(self):
        """Validate conditional requirements based on policy type."""
        # Validate handling time if provided
        if self.handlingTime:
            if self.handlingTime.unit not in [TimeDurationUnitEnum.DAY, TimeDurationUnitEnum.BUSINESS_DAY]:
                raise ValueError("Handling time unit must be DAY or BUSINESS_DAY")
            if self.handlingTime.value > 30:
                raise ValueError("Handling time cannot exceed 30 days")
        
        # Validate shipping options
        if self.shippingOptions and len(self.shippingOptions) > 2:
            raise ValueError("Maximum 2 shipping options allowed (domestic + international)")
        
        return self


class FulfillmentPolicyResponse(FulfillmentPolicyInput):
    """
    Response model for fulfillment policy operations.
    
    Extends the input model with additional response fields.
    """
    fulfillmentPolicyId: Optional[str] = Field(None, description="eBay fulfillment policy ID")
    warnings: Optional[List[Dict[str, Any]]] = Field(None, description="API warnings")