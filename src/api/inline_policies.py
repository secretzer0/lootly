"""
Pydantic models for eBay inline policies.

Provides structured models for payment, shipping, and return policies
that can be embedded directly in offers without requiring separate
Business Policy IDs. This follows the modern eBay REST API patterns.
"""
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field, field_validator
from enum import Enum
from decimal import Decimal


class PaymentMethodType(str, Enum):
    """Supported payment method types."""
    PAYPAL = "PAYPAL"
    CREDIT_CARD = "CREDIT_CARD"
    BANK_TRANSFER = "BANK_TRANSFER"
    APPLE_PAY = "APPLE_PAY"
    GOOGLE_PAY = "GOOGLE_PAY"


class ReferenceType(str, Enum):
    """Reference types for payment accounts."""
    PAYPAL_EMAIL = "PAYPAL_EMAIL"
    MERCHANT_ID = "MERCHANT_ID"


class TimeDurationUnit(str, Enum):
    """Time duration units."""
    DAY = "DAY"
    BUSINESS_DAY = "BUSINESS_DAY"
    HOUR = "HOUR"
    CALENDAR_DAY = "CALENDAR_DAY"


class ShippingCostPayer(str, Enum):
    """Who pays for shipping costs."""
    BUYER = "BUYER"
    SELLER = "SELLER"


class ReturnMethod(str, Enum):
    """Return method options."""
    EXCHANGE = "EXCHANGE"
    MONEY_BACK = "MONEY_BACK"


class ShippingServiceType(str, Enum):
    """Shipping service types."""
    CALCULATED = "CALCULATED"
    FLAT_RATE = "FLAT_RATE"
    FREIGHT = "FREIGHT"


class Money(BaseModel):
    """Money value with currency."""
    value: str = Field(..., description="Monetary value as string")
    currency: str = Field(default="USD", description="Currency code")
    
    @field_validator('value')
    @classmethod
    def validate_value(cls, v):
        try:
            float(v)
            return v
        except ValueError:
            raise ValueError("Value must be a valid number")


class TimeDuration(BaseModel):
    """Time duration specification."""
    unit: TimeDurationUnit = Field(..., description="Time unit")
    value: int = Field(..., ge=1, description="Duration value")


class PaymentAccountReference(BaseModel):
    """Payment account reference details."""
    reference_type: ReferenceType = Field(..., description="Type of reference")
    reference_value: str = Field(..., description="Reference value (email, ID, etc.)")


class PaymentMethod(BaseModel):
    """Payment method configuration."""
    payment_method_type: PaymentMethodType = Field(..., description="Payment method type")
    recipient_account_reference: Optional[PaymentAccountReference] = Field(None, description="Account reference")


class ShippingOption(BaseModel):
    """Shipping option details."""
    option_type: ShippingServiceType = Field(..., description="Shipping service type")
    cost: Optional[Money] = Field(None, description="Shipping cost (for flat rate)")
    additional_shipping_cost: Optional[Money] = Field(None, description="Additional item shipping cost")
    
    # Calculated shipping fields
    package_depth: Optional[str] = Field(None, description="Package depth for calculated shipping")
    package_length: Optional[str] = Field(None, description="Package length for calculated shipping")
    package_width: Optional[str] = Field(None, description="Package width for calculated shipping")
    package_weight: Optional[str] = Field(None, description="Package weight for calculated shipping")


class InlinePaymentPolicy(BaseModel):
    """Inline payment policy for offers."""
    payment_methods: List[PaymentMethod] = Field(..., description="Accepted payment methods")
    payment_instructions: Optional[str] = Field(None, description="Payment instructions")
    immediate_payment_required: bool = Field(default=False, description="Require immediate payment")
    
    @classmethod
    def create_paypal_policy(cls, paypal_email: str, immediate_payment: bool = False) -> "InlinePaymentPolicy":
        """Create a standard PayPal payment policy."""
        return cls(
            payment_methods=[
                PaymentMethod(
                    payment_method_type=PaymentMethodType.PAYPAL,
                    recipient_account_reference=PaymentAccountReference(
                        reference_type=ReferenceType.PAYPAL_EMAIL,
                        reference_value=paypal_email
                    )
                )
            ],
            immediate_payment_required=immediate_payment,
            payment_instructions=f"Pay via PayPal to {paypal_email}. Fast and secure payment processing."
        )
    
    @classmethod
    def create_mixed_policy(cls, paypal_email: str, accept_cards: bool = True) -> "InlinePaymentPolicy":
        """Create a policy accepting multiple payment methods."""
        methods = [
            PaymentMethod(
                payment_method_type=PaymentMethodType.PAYPAL,
                recipient_account_reference=PaymentAccountReference(
                    reference_type=ReferenceType.PAYPAL_EMAIL,
                    reference_value=paypal_email
                )
            )
        ]
        
        if accept_cards:
            methods.append(
                PaymentMethod(payment_method_type=PaymentMethodType.CREDIT_CARD)
            )
        
        return cls(
            payment_methods=methods,
            payment_instructions="We accept PayPal and major credit cards for your convenience."
        )


class InlineShippingPolicy(BaseModel):
    """Inline shipping policy for offers."""
    shipping_options: List[ShippingOption] = Field(..., description="Available shipping options")
    domestic_shipping_discount: bool = Field(default=False, description="Offer domestic shipping discount")
    international_shipping_discount: bool = Field(default=False, description="Offer international shipping discount")
    global_shipping: bool = Field(default=True, description="Use eBay Global Shipping Program")
    
    @classmethod
    def create_flat_rate_policy(cls, shipping_cost: float, currency: str = "USD") -> "InlineShippingPolicy":
        """Create a simple flat rate shipping policy."""
        return cls(
            shipping_options=[
                ShippingOption(
                    option_type=ShippingServiceType.FLAT_RATE,
                    cost=Money(value=str(shipping_cost), currency=currency)
                )
            ],
            global_shipping=True
        )
    
    @classmethod
    def create_calculated_policy(cls, package_dimensions: Dict[str, str]) -> "InlineShippingPolicy":
        """Create a calculated shipping policy."""
        return cls(
            shipping_options=[
                ShippingOption(
                    option_type=ShippingServiceType.CALCULATED,
                    package_depth=package_dimensions.get("depth"),
                    package_length=package_dimensions.get("length"),
                    package_width=package_dimensions.get("width"),
                    package_weight=package_dimensions.get("weight")
                )
            ],
            global_shipping=True
        )
    
    @classmethod
    def create_free_shipping_policy(cls) -> "InlineShippingPolicy":
        """Create a free shipping policy."""
        return cls(
            shipping_options=[
                ShippingOption(
                    option_type=ShippingServiceType.FLAT_RATE,
                    cost=Money(value="0.00", currency="USD")
                )
            ],
            global_shipping=True
        )


class InlineReturnPolicy(BaseModel):
    """Inline return policy for offers."""
    returns_accepted: bool = Field(default=True, description="Whether returns are accepted")
    return_period: Optional[TimeDuration] = Field(None, description="Return period")
    return_shipping_cost_payer: ShippingCostPayer = Field(default=ShippingCostPayer.BUYER, description="Who pays return shipping")
    return_method: ReturnMethod = Field(default=ReturnMethod.MONEY_BACK, description="Return method")
    return_policy_description: Optional[str] = Field(None, description="Return policy description")
    restocking_fee_percentage: Optional[float] = Field(None, ge=0, le=100, description="Restocking fee percentage")
    
    @classmethod
    def create_standard_policy(cls, return_days: int = 30, buyer_pays_return: bool = True) -> "InlineReturnPolicy":
        """Create a standard return policy."""
        return cls(
            returns_accepted=True,
            return_period=TimeDuration(unit=TimeDurationUnit.DAY, value=return_days),
            return_shipping_cost_payer=ShippingCostPayer.BUYER if buyer_pays_return else ShippingCostPayer.SELLER,
            return_method=ReturnMethod.MONEY_BACK,
            return_policy_description=f"{return_days}-day returns accepted. {'Buyer' if buyer_pays_return else 'Seller'} pays return shipping."
        )
    
    @classmethod
    def create_no_returns_policy(cls) -> "InlineReturnPolicy":
        """Create a no returns policy."""
        return cls(
            returns_accepted=False,
            return_policy_description="No returns accepted. All sales final."
        )
    
    @classmethod
    def create_exchange_only_policy(cls, return_days: int = 14) -> "InlineReturnPolicy":
        """Create an exchange-only return policy."""
        return cls(
            returns_accepted=True,
            return_period=TimeDuration(unit=TimeDurationUnit.DAY, value=return_days),
            return_shipping_cost_payer=ShippingCostPayer.BUYER,
            return_method=ReturnMethod.EXCHANGE,
            return_policy_description=f"Exchanges only within {return_days} days. Buyer pays return shipping."
        )


class CompletePolicySet(BaseModel):
    """Complete set of inline policies for an offer."""
    payment_policy: InlinePaymentPolicy = Field(..., description="Payment policy")
    shipping_policy: InlineShippingPolicy = Field(..., description="Shipping policy")
    return_policy: InlineReturnPolicy = Field(..., description="Return policy")
    
    @classmethod
    def create_standard_set(
        cls,
        paypal_email: str = "seller@example.com",
        shipping_cost: float = 4.99,
        return_days: int = 30,
        currency: str = "USD"
    ) -> "CompletePolicySet":
        """Create a standard policy set for most listings."""
        return cls(
            payment_policy=InlinePaymentPolicy.create_paypal_policy(paypal_email),
            shipping_policy=InlineShippingPolicy.create_flat_rate_policy(shipping_cost, currency),
            return_policy=InlineReturnPolicy.create_standard_policy(return_days)
        )
    
    @classmethod
    def create_premium_set(
        cls,
        paypal_email: str = "seller@example.com",
        return_days: int = 60,
        free_shipping: bool = True
    ) -> "CompletePolicySet":
        """Create a premium policy set with enhanced customer service."""
        return cls(
            payment_policy=InlinePaymentPolicy.create_mixed_policy(paypal_email, accept_cards=True),
            shipping_policy=InlineShippingPolicy.create_free_shipping_policy() if free_shipping else InlineShippingPolicy.create_flat_rate_policy(0.99),
            return_policy=InlineReturnPolicy.create_standard_policy(return_days, buyer_pays_return=not free_shipping)
        )
    
    def to_ebay_format(self) -> Dict[str, Any]:
        """Convert to eBay API format for offer creation."""
        # Convert payment policy
        payment_methods = []
        for method in self.payment_policy.payment_methods:
            ebay_method = {"paymentMethodType": method.payment_method_type.value}
            if method.recipient_account_reference:
                ebay_method["recipientAccountReference"] = {
                    "referenceType": method.recipient_account_reference.reference_type.value,
                    "referenceValue": method.recipient_account_reference.reference_value
                }
            payment_methods.append(ebay_method)
        
        # Convert shipping policy
        shipping_options = []
        for option in self.shipping_policy.shipping_options:
            ebay_option = {"optionType": option.option_type.value}
            if option.cost:
                ebay_option["cost"] = {"value": option.cost.value, "currency": option.cost.currency}
            if option.package_weight:
                ebay_option["packageWeight"] = option.package_weight
            # Add other package dimensions as needed
            shipping_options.append(ebay_option)
        
        # Convert return policy
        return_policy = {
            "returnsAccepted": self.return_policy.returns_accepted,
            "returnShippingCostPayer": self.return_policy.return_shipping_cost_payer.value,
            "returnMethod": self.return_policy.return_method.value
        }
        
        if self.return_policy.return_period:
            return_policy["returnPeriod"] = {
                "unit": self.return_policy.return_period.unit.value,
                "value": self.return_policy.return_period.value
            }
        
        if self.return_policy.return_policy_description:
            return_policy["description"] = self.return_policy.return_policy_description
        
        return {
            "paymentMethods": payment_methods,
            "shippingOptions": shipping_options,
            "returnPolicy": return_policy
        }


# Convenience functions for common policy patterns
def create_basic_policies(
    paypal_email: str = "seller@example.com",
    shipping_cost: float = 4.99,
    return_days: int = 30
) -> CompletePolicySet:
    """Create basic policies for simple listings."""
    return CompletePolicySet.create_standard_set(paypal_email, shipping_cost, return_days)


def create_premium_policies(
    paypal_email: str = "seller@example.com",
    free_shipping: bool = True,
    extended_returns: bool = True
) -> CompletePolicySet:
    """Create premium policies for high-value listings."""
    return CompletePolicySet.create_premium_set(
        paypal_email=paypal_email,
        return_days=60 if extended_returns else 30,
        free_shipping=free_shipping
    )


def create_auction_policies(
    paypal_email: str = "seller@example.com",
    shipping_cost: float = 9.99
) -> CompletePolicySet:
    """Create policies suitable for auction listings."""
    return CompletePolicySet(
        payment_policy=InlinePaymentPolicy.create_paypal_policy(paypal_email, immediate_payment=False),
        shipping_policy=InlineShippingPolicy.create_flat_rate_policy(shipping_cost),
        return_policy=InlineReturnPolicy.create_standard_policy(14)  # Shorter return period for auctions
    )


def create_no_returns_policies(
    paypal_email: str = "seller@example.com",
    shipping_cost: float = 6.99
) -> CompletePolicySet:
    """Create policies for items sold as-is with no returns."""
    return CompletePolicySet(
        payment_policy=InlinePaymentPolicy.create_paypal_policy(paypal_email, immediate_payment=True),
        shipping_policy=InlineShippingPolicy.create_flat_rate_policy(shipping_cost),
        return_policy=InlineReturnPolicy.create_no_returns_policy()
    )