"""Unit tests for inline policies Pydantic models."""
import pytest
from unittest.mock import Mock
from pydantic import ValidationError

from api.inline_policies import (
    Money,
    TimeDuration,
    TimeDurationUnit,
    PaymentAccountReference,
    PaymentMethod,
    PaymentMethodType,
    ReferenceType,
    ShippingOption,
    ShippingServiceType,
    InlinePaymentPolicy,
    InlineShippingPolicy,
    InlineReturnPolicy,
    ShippingCostPayer,
    ReturnMethod
)


class TestMoneyModelUnit:
    """Unit tests for the Money model."""
    
    def test_money_valid_values(self):
        """Test Money model with valid values."""
        money = Money(value="29.99", currency="USD")
        assert money.value == "29.99"
        assert money.currency == "USD"
    
    def test_money_default_currency(self):
        """Test Money model uses USD as default currency."""
        money = Money(value="19.99")
        assert money.currency == "USD"
    
    def test_money_validation_error(self):
        """Test Money model validates numeric strings."""
        with pytest.raises(ValidationError):
            Money(value="not_a_number")


class TestTimeDurationModelUnit:
    """Unit tests for the TimeDuration model."""
    
    def test_time_duration_valid(self):
        """Test TimeDuration with valid values."""
        duration = TimeDuration(unit=TimeDurationUnit.DAY, value=30)
        assert duration.unit == TimeDurationUnit.DAY
        assert duration.value == 30
    
    def test_time_duration_validation_error(self):
        """Test TimeDuration validates positive values."""
        with pytest.raises(ValidationError):
            TimeDuration(unit=TimeDurationUnit.DAY, value=0)


class TestPaymentAccountReferenceModelUnit:
    """Unit tests for the PaymentAccountReference model."""
    
    def test_payment_account_reference_valid(self):
        """Test PaymentAccountReference with valid values."""
        ref = PaymentAccountReference(
            reference_type=ReferenceType.PAYPAL_EMAIL,
            reference_value="seller@example.com"
        )
        assert ref.reference_type == ReferenceType.PAYPAL_EMAIL
        assert ref.reference_value == "seller@example.com"


class TestPaymentMethodModelUnit:
    """Unit tests for the PaymentMethod model."""
    
    def test_payment_method_with_account_reference(self):
        """Test PaymentMethod with account reference."""
        method = PaymentMethod(
            payment_method_type=PaymentMethodType.PAYPAL,
            recipient_account_reference=PaymentAccountReference(
                reference_type=ReferenceType.PAYPAL_EMAIL,
                reference_value="seller@example.com"
            )
        )
        assert method.payment_method_type == PaymentMethodType.PAYPAL
        assert method.recipient_account_reference.reference_value == "seller@example.com"
    
    def test_payment_method_without_account_reference(self):
        """Test PaymentMethod without account reference."""
        method = PaymentMethod(payment_method_type=PaymentMethodType.CREDIT_CARD)
        assert method.payment_method_type == PaymentMethodType.CREDIT_CARD
        assert method.recipient_account_reference is None


class TestShippingOptionModelUnit:
    """Unit tests for the ShippingOption model."""
    
    def test_shipping_option_flat_rate(self):
        """Test ShippingOption for flat rate shipping."""
        option = ShippingOption(
            option_type=ShippingServiceType.FLAT_RATE,
            cost=Money(value="5.99", currency="USD")
        )
        assert option.option_type == ShippingServiceType.FLAT_RATE
        assert option.cost.value == "5.99"
    
    def test_shipping_option_calculated(self):
        """Test ShippingOption for calculated shipping."""
        option = ShippingOption(
            option_type=ShippingServiceType.CALCULATED,
            package_weight="1.5",
            package_length="10",
            package_width="8",
            package_depth="6"
        )
        assert option.option_type == ShippingServiceType.CALCULATED
        assert option.package_weight == "1.5"
        assert option.cost is None


class TestInlinePaymentPolicyModelUnit:
    """Unit tests for the InlinePaymentPolicy model."""
    
    def test_payment_policy_basic(self):
        """Test basic payment policy creation."""
        policy = InlinePaymentPolicy(
            payment_methods=[
                PaymentMethod(payment_method_type=PaymentMethodType.PAYPAL)
            ],
            immediate_payment_required=False
        )
        assert len(policy.payment_methods) == 1
        assert policy.immediate_payment_required is False
    
    def test_payment_policy_create_paypal_policy(self):
        """Test PayPal policy creation helper."""
        policy = InlinePaymentPolicy.create_paypal_policy(
            paypal_email="seller@example.com",
            immediate_payment=True
        )
        assert len(policy.payment_methods) == 1
        assert policy.payment_methods[0].payment_method_type == PaymentMethodType.PAYPAL
        assert policy.immediate_payment_required is True
        assert "seller@example.com" in policy.payment_instructions
    
    def test_payment_policy_create_mixed_policy(self):
        """Test mixed payment policy creation helper."""
        policy = InlinePaymentPolicy.create_mixed_policy(
            paypal_email="seller@example.com",
            accept_cards=True
        )
        assert len(policy.payment_methods) == 2
        method_types = [method.payment_method_type for method in policy.payment_methods]
        assert PaymentMethodType.PAYPAL in method_types
        assert PaymentMethodType.CREDIT_CARD in method_types
    
    def test_payment_policy_validation_error(self):
        """Test payment policy validation with empty methods."""
        with pytest.raises(ValidationError):
            InlinePaymentPolicy(payment_methods=[])


class TestInlineShippingPolicyModelUnit:
    """Unit tests for the InlineShippingPolicy model."""
    
    def test_shipping_policy_basic(self):
        """Test basic shipping policy creation."""
        policy = InlineShippingPolicy(
            shipping_options=[
                ShippingOption(
                    option_type=ShippingServiceType.FLAT_RATE,
                    cost=Money(value="5.99")
                )
            ]
        )
        assert len(policy.shipping_options) == 1
        assert policy.global_shipping is True  # Default value
    
    def test_shipping_policy_create_flat_rate(self):
        """Test flat rate shipping policy helper."""
        policy = InlineShippingPolicy.create_flat_rate_policy(
            shipping_cost=4.99,
            currency="USD"
        )
        assert len(policy.shipping_options) == 1
        option = policy.shipping_options[0]
        assert option.option_type == ShippingServiceType.FLAT_RATE
        assert option.cost.value == "4.99"
        assert option.cost.currency == "USD"
    
    def test_shipping_policy_create_calculated(self):
        """Test calculated shipping policy helper."""
        dimensions = {
            "length": "12",
            "width": "8", 
            "depth": "6",
            "weight": "2.5"
        }
        policy = InlineShippingPolicy.create_calculated_policy(dimensions)
        assert len(policy.shipping_options) == 1
        option = policy.shipping_options[0]
        assert option.option_type == ShippingServiceType.CALCULATED
        assert option.package_length == "12"
        assert option.package_weight == "2.5"
    
    def test_shipping_policy_create_free_shipping(self):
        """Test free shipping policy helper."""
        policy = InlineShippingPolicy.create_free_shipping_policy()
        assert len(policy.shipping_options) == 1
        option = policy.shipping_options[0]
        assert option.option_type == ShippingServiceType.FLAT_RATE
        assert option.cost.value == "0.00"
    
    def test_shipping_policy_validation_error(self):
        """Test shipping policy validation with empty options."""
        with pytest.raises(ValidationError):
            InlineShippingPolicy(shipping_options=[])


class TestInlineReturnPolicyModelUnit:
    """Unit tests for the InlineReturnPolicy model."""
    
    def test_return_policy_basic(self):
        """Test basic return policy creation."""
        policy = InlineReturnPolicy(
            returns_accepted=True,
            return_period=TimeDuration(unit=TimeDurationUnit.DAY, value=30),
            return_shipping_cost_payer=ShippingCostPayer.BUYER,
            return_method=ReturnMethod.MONEY_BACK
        )
        assert policy.returns_accepted is True
        assert policy.return_period.value == 30
        assert policy.return_shipping_cost_payer == ShippingCostPayer.BUYER
    
    def test_return_policy_create_standard(self):
        """Test standard return policy helper."""
        policy = InlineReturnPolicy.create_standard_policy(
            return_days=30,
            buyer_pays_return=True
        )
        assert policy.returns_accepted is True
        assert policy.return_period.value == 30
        assert policy.return_shipping_cost_payer == ShippingCostPayer.BUYER
        assert "30-day returns" in policy.return_policy_description
    
    def test_return_policy_create_no_returns(self):
        """Test no returns policy helper."""
        policy = InlineReturnPolicy.create_no_returns_policy()
        assert policy.returns_accepted is False
        assert "No returns accepted" in policy.return_policy_description
    
    def test_return_policy_create_exchange_only(self):
        """Test exchange only policy helper."""
        policy = InlineReturnPolicy.create_exchange_only_policy(return_days=14)
        assert policy.returns_accepted is True
        assert policy.return_method == ReturnMethod.EXCHANGE
        assert policy.return_period.value == 14
        assert "Exchanges only" in policy.return_policy_description
    
    def test_return_policy_restocking_fee_validation(self):
        """Test restocking fee validation."""
        # Valid restocking fee
        policy = InlineReturnPolicy(
            returns_accepted=True,
            restocking_fee_percentage=10.0
        )
        assert policy.restocking_fee_percentage == 10.0
        
        # Invalid restocking fee (over 100%)
        with pytest.raises(ValidationError):
            InlineReturnPolicy(
                returns_accepted=True,
                restocking_fee_percentage=150.0
            )
        
        # Invalid restocking fee (negative)
        with pytest.raises(ValidationError):
            InlineReturnPolicy(
                returns_accepted=True,
                restocking_fee_percentage=-5.0
            )