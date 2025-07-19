"""Unit tests for eBay enum types."""
from models.enums import (
    AvailabilityTypeEnum,
    CategoryTypeEnum,
    ConditionEnum,
    CurrencyCodeEnum,
    LocaleEnum,
    LengthUnitOfMeasureEnum,
    MarketplaceIdEnum,
    PackageTypeEnum,
    PaymentInstrumentBrandEnum,
    PaymentMethodTypeEnum,
    RecipientAccountReferenceTypeEnum,
    RefundMethodEnum,
    ReturnMethodEnum,
    ReturnShippingCostPayerEnum,
    RegionTypeEnum,
    ShippingCostTypeEnum,
    ShippingOptionTypeEnum,
    TimeDurationUnitEnum,
    WeightUnitOfMeasureEnum,
    validate_enum_value,
    get_enum_from_string,
    get_all_enum_values,
    get_enum_description
)


class TestBaseEnumFunctionality:
    """Test base enum helper methods."""
    
    def test_get_description(self):
        """Test getting enum descriptions."""
        assert CategoryTypeEnum.get_description("MOTORS_VEHICLES") == "Business policy applies to motor vehicle listings"
        assert CategoryTypeEnum.get_description("INVALID") is None
        
    def test_from_string_case_insensitive(self):
        """Test case-insensitive string conversion."""
        assert CategoryTypeEnum.from_string("motors_vehicles") == CategoryTypeEnum.MOTORS_VEHICLES
        assert CategoryTypeEnum.from_string("MOTORS_VEHICLES") == CategoryTypeEnum.MOTORS_VEHICLES
        assert CategoryTypeEnum.from_string("Motors_Vehicles") == CategoryTypeEnum.MOTORS_VEHICLES
        assert CategoryTypeEnum.from_string("invalid") is None
        assert CategoryTypeEnum.from_string("") is None
        
    def test_get_all_values(self):
        """Test getting all enum values."""
        values = CategoryTypeEnum.get_all_values()
        assert len(values) == 2
        assert "MOTORS_VEHICLES" in values
        assert "ALL_EXCLUDING_MOTORS_VEHICLES" in values
        
    def test_is_valid(self):
        """Test enum value validation."""
        assert CategoryTypeEnum.is_valid("MOTORS_VEHICLES") is True
        assert CategoryTypeEnum.is_valid("ALL_EXCLUDING_MOTORS_VEHICLES") is True
        assert CategoryTypeEnum.is_valid("INVALID") is False


class TestCategoryTypeEnum:
    """Test CategoryTypeEnum specifics."""
    
    def test_enum_values(self):
        """Test all CategoryTypeEnum values exist."""
        assert CategoryTypeEnum.MOTORS_VEHICLES.value == "MOTORS_VEHICLES"
        assert CategoryTypeEnum.ALL_EXCLUDING_MOTORS_VEHICLES.value == "ALL_EXCLUDING_MOTORS_VEHICLES"
        
    def test_descriptions(self):
        """Test CategoryTypeEnum descriptions."""
        descriptions = CategoryTypeEnum._get_descriptions()
        assert len(descriptions) == 2
        assert "motor vehicle" in descriptions["MOTORS_VEHICLES"]


class TestConditionEnum:
    """Test ConditionEnum specifics."""
    
    def test_enum_values_count(self):
        """Test that all condition values are present."""
        values = ConditionEnum.get_all_values()
        assert len(values) == 16  # Should have 16 condition types
        
    def test_key_condition_values(self):
        """Test key condition values."""
        assert ConditionEnum.NEW.value == "NEW"
        assert ConditionEnum.USED_EXCELLENT.value == "USED_EXCELLENT"
        assert ConditionEnum.FOR_PARTS_OR_NOT_WORKING.value == "FOR_PARTS_OR_NOT_WORKING"
        
    def test_condition_descriptions(self):
        """Test condition descriptions."""
        assert "Brand-new" in ConditionEnum.get_description("NEW")
        assert "parts" in ConditionEnum.get_description("FOR_PARTS_OR_NOT_WORKING")


class TestCurrencyCodeEnum:
    """Test CurrencyCodeEnum specifics."""
    
    def test_major_currencies(self):
        """Test major currency codes exist."""
        major_currencies = ["USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "CNY"]
        for currency in major_currencies:
            assert CurrencyCodeEnum.is_valid(currency)
            
    def test_currency_count(self):
        """Test we have a comprehensive list of currencies."""
        values = CurrencyCodeEnum.get_all_values()
        assert len(values) > 60  # Should have at least 60 currencies
        
    def test_currency_descriptions(self):
        """Test currency descriptions for common currencies."""
        assert CurrencyCodeEnum.get_description("USD") == "United States Dollar"
        assert CurrencyCodeEnum.get_description("EUR") == "Euro"
        assert CurrencyCodeEnum.get_description("GBP") == "British Pound Sterling"


class TestMarketplaceIdEnum:
    """Test MarketplaceIdEnum specifics."""
    
    def test_major_marketplaces(self):
        """Test major marketplace IDs exist."""
        major_markets = ["EBAY_US", "EBAY_GB", "EBAY_DE", "EBAY_AU", "EBAY_CA"]
        for market in major_markets:
            assert MarketplaceIdEnum.is_valid(market)
            
    def test_marketplace_descriptions(self):
        """Test marketplace descriptions."""
        assert "United States" in MarketplaceIdEnum.get_description("EBAY_US")
        assert "ebay.com" in MarketplaceIdEnum.get_description("EBAY_US")
        assert "United Kingdom" in MarketplaceIdEnum.get_description("EBAY_GB")
        assert "ebay.co.uk" in MarketplaceIdEnum.get_description("EBAY_GB")
        
    def test_motors_marketplace(self):
        """Test eBay Motors marketplace exists."""
        assert MarketplaceIdEnum.EBAY_MOTORS_US.value == "EBAY_MOTORS_US"


class TestPaymentMethodTypeEnum:
    """Test PaymentMethodTypeEnum specifics."""
    
    def test_payment_methods(self):
        """Test all offline payment methods."""
        expected_methods = [
            "CASH_IN_PERSON", "CASH_ON_DELIVERY", "CASH_ON_PICKUP",
            "PERSONAL_CHECK", "MONEY_ORDER", "CASHIER_CHECK"
        ]
        values = PaymentMethodTypeEnum.get_all_values()
        assert len(values) == 6
        for method in expected_methods:
            assert method in values


class TestReturnShippingCostPayerEnum:
    """Test ReturnShippingCostPayerEnum specifics."""
    
    def test_payer_options(self):
        """Test return shipping payer options."""
        assert ReturnShippingCostPayerEnum.BUYER.value == "BUYER"
        assert ReturnShippingCostPayerEnum.SELLER.value == "SELLER"
        assert len(ReturnShippingCostPayerEnum.get_all_values()) == 2


class TestShippingCostTypeEnum:
    """Test ShippingCostTypeEnum specifics."""
    
    def test_shipping_cost_types(self):
        """Test shipping cost calculation types."""
        assert ShippingCostTypeEnum.FLAT_RATE.value == "FLAT_RATE"
        assert ShippingCostTypeEnum.CALCULATED.value == "CALCULATED"
        assert len(ShippingCostTypeEnum.get_all_values()) == 2


class TestWeightUnitOfMeasureEnum:
    """Test WeightUnitOfMeasureEnum specifics."""
    
    def test_weight_units(self):
        """Test weight measurement units."""
        units = WeightUnitOfMeasureEnum.get_all_values()
        assert "POUND" in units
        assert "OUNCE" in units
        assert "KILOGRAM" in units
        assert "GRAM" in units
        assert len(units) == 4
        
    def test_weight_descriptions(self):
        """Test weight unit descriptions."""
        assert "lb" in WeightUnitOfMeasureEnum.get_description("POUND")
        assert "kg" in WeightUnitOfMeasureEnum.get_description("KILOGRAM")


class TestLengthUnitOfMeasureEnum:
    """Test LengthUnitOfMeasureEnum specifics."""
    
    def test_length_units(self):
        """Test length measurement units."""
        units = LengthUnitOfMeasureEnum.get_all_values()
        assert "INCH" in units
        assert "FEET" in units
        assert "CENTIMETER" in units
        assert "METER" in units
        assert len(units) == 4


class TestTimeDurationUnitEnum:
    """Test TimeDurationUnitEnum specifics."""
    
    def test_time_units(self):
        """Test time duration units."""
        units = TimeDurationUnitEnum.get_all_values()
        expected = ["YEAR", "MONTH", "DAY", "HOUR", "MINUTE", "SECOND", "MILLISECOND"]
        assert len(units) == 7
        for unit in expected:
            assert unit in units


class TestHelperFunctions:
    """Test module-level helper functions."""
    
    def test_validate_enum_value(self):
        """Test validate_enum_value helper."""
        assert validate_enum_value(CategoryTypeEnum, "MOTORS_VEHICLES") is True
        assert validate_enum_value(CategoryTypeEnum, "INVALID") is False
        
    def test_get_enum_from_string(self):
        """Test get_enum_from_string helper."""
        result = get_enum_from_string(ConditionEnum, "new")
        assert result == ConditionEnum.NEW
        
        result = get_enum_from_string(ConditionEnum, "INVALID")
        assert result is None
        
    def test_get_all_enum_values(self):
        """Test get_all_enum_values helper."""
        values = get_all_enum_values(RefundMethodEnum)
        assert len(values) == 2
        assert "MONEY_BACK" in values
        assert "MERCHANDISE_CREDIT" in values
        
    def test_get_enum_description(self):
        """Test get_enum_description helper."""
        desc = get_enum_description(ReturnMethodEnum, "EXCHANGE")
        assert "Exchange" in desc
        
        desc = get_enum_description(ReturnMethodEnum, "INVALID")
        assert desc is None


class TestEnumCompleteness:
    """Test that all required enums are implemented."""
    
    def test_all_enums_exist(self):
        """Test all 19 enum types are defined."""
        expected_enums = [
            AvailabilityTypeEnum,
            CategoryTypeEnum,
            ConditionEnum,
            CurrencyCodeEnum,
            LocaleEnum,
            LengthUnitOfMeasureEnum,
            MarketplaceIdEnum,
            PackageTypeEnum,
            PaymentInstrumentBrandEnum,
            PaymentMethodTypeEnum,
            RecipientAccountReferenceTypeEnum,
            RefundMethodEnum,
            ReturnMethodEnum,
            ReturnShippingCostPayerEnum,
            RegionTypeEnum,
            ShippingCostTypeEnum,
            ShippingOptionTypeEnum,
            TimeDurationUnitEnum,
            WeightUnitOfMeasureEnum
        ]
        
        # Verify each enum exists and has values
        for enum_class in expected_enums:
            assert len(enum_class.get_all_values()) > 0
            assert hasattr(enum_class, '_get_descriptions')
            assert hasattr(enum_class, 'from_string')
            assert hasattr(enum_class, 'is_valid')