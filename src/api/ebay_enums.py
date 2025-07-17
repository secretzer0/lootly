"""
eBay API Enumerations for strongly-typed parameters.

This module contains all enum types used across eBay's Sell APIs including
Account and Inventory APIs. These enums provide type safety and validation
for API parameters.

Documentation references:
- https://developer.ebay.com/api-docs/sell/account/types/
- https://developer.ebay.com/api-docs/sell/inventory/types/
"""
from enum import Enum
from typing import Optional, Dict, List


class BaseEbayEnum(Enum):
    """Base class for eBay enumerations with helper methods."""
    
    @classmethod
    def get_description(cls, value: str) -> Optional[str]:
        """Get human-readable description for enum value."""
        return cls._get_descriptions().get(value)
    
    @classmethod
    def _get_descriptions(cls) -> Dict[str, str]:
        """Override in subclasses to provide descriptions."""
        return {}
    
    @classmethod
    def from_string(cls, value: str) -> Optional['BaseEbayEnum']:
        """Convert string to enum value, case-insensitive."""
        if not value:
            return None
        value_upper = value.upper()
        for member in cls:
            if member.value.upper() == value_upper:
                return member
        return None
    
    @classmethod
    def get_all_values(cls) -> List[str]:
        """Get all possible enum values."""
        return [member.value for member in cls]
    
    @classmethod
    def is_valid(cls, value: str) -> bool:
        """Check if a value is valid for this enum."""
        return value in cls.get_all_values()


class AvailabilityTypeEnum(BaseEbayEnum):
    """
    Type of availability for an inventory item.
    Docs: https://developer.ebay.com/api-docs/sell/inventory/types/slr:AvailabilityTypeEnum
    """
    SHIP_TO_HOME = "SHIP_TO_HOME"
    PICKUP = "PICKUP"
    NOT_AVAILABLE = "NOT_AVAILABLE"
    
    @classmethod
    def _get_descriptions(cls) -> Dict[str, str]:
        return {
            "SHIP_TO_HOME": "Item is available for shipping to buyer's location",
            "PICKUP": "Item is available for local pickup only",
            "NOT_AVAILABLE": "Item is not currently available"
        }


class CategoryTypeEnum(BaseEbayEnum):
    """
    Category type for business policies.
    Docs: https://developer.ebay.com/api-docs/sell/account/types/api:CategoryTypeEnum
    """
    MOTORS_VEHICLES = "MOTORS_VEHICLES"
    ALL_EXCLUDING_MOTORS_VEHICLES = "ALL_EXCLUDING_MOTORS_VEHICLES"
    
    @classmethod
    def _get_descriptions(cls) -> Dict[str, str]:
        return {
            "MOTORS_VEHICLES": "Business policy applies to motor vehicle listings",
            "ALL_EXCLUDING_MOTORS_VEHICLES": "Business policy applies to all listings except motor vehicles"
        }


class ConditionEnum(BaseEbayEnum):
    """
    Item condition enumeration for inventory items.
    Docs: https://developer.ebay.com/api-docs/sell/inventory/types/slr:ConditionEnum
    """
    NEW = "NEW"
    LIKE_NEW = "LIKE_NEW"
    NEW_OTHER = "NEW_OTHER"
    NEW_WITH_DEFECTS = "NEW_WITH_DEFECTS"
    CERTIFIED_REFURBISHED = "CERTIFIED_REFURBISHED"
    EXCELLENT_REFURBISHED = "EXCELLENT_REFURBISHED"
    VERY_GOOD_REFURBISHED = "VERY_GOOD_REFURBISHED"
    GOOD_REFURBISHED = "GOOD_REFURBISHED"
    SELLER_REFURBISHED = "SELLER_REFURBISHED"
    USED_EXCELLENT = "USED_EXCELLENT"
    USED_VERY_GOOD = "USED_VERY_GOOD"
    USED_GOOD = "USED_GOOD"
    USED_ACCEPTABLE = "USED_ACCEPTABLE"
    FOR_PARTS_OR_NOT_WORKING = "FOR_PARTS_OR_NOT_WORKING"
    PRE_OWNED_EXCELLENT = "PRE_OWNED_EXCELLENT"
    PRE_OWNED_FAIR = "PRE_OWNED_FAIR"
    
    @classmethod
    def _get_descriptions(cls) -> Dict[str, str]:
        return {
            "NEW": "Brand-new, unopened item in its original packaging",
            "LIKE_NEW": "In 'like-new' condition. Opened but very lightly used",
            "NEW_OTHER": "New, unused item possibly missing original packaging",
            "NEW_WITH_DEFECTS": "New, unused item with defects like scuffs or hanging threads",
            "CERTIFIED_REFURBISHED": "Pristine, like-new condition inspected and refurbished by manufacturer",
            "EXCELLENT_REFURBISHED": "Like new condition, inspected and cleaned by manufacturer",
            "VERY_GOOD_REFURBISHED": "Minimal wear, inspected and refurbished by manufacturer",
            "GOOD_REFURBISHED": "Moderate wear, inspected and refurbished by manufacturer",
            "SELLER_REFURBISHED": "Restored to working order by seller, in excellent condition",
            "USED_EXCELLENT": "Used but in excellent condition",
            "USED_VERY_GOOD": "Used but in very good condition",
            "USED_GOOD": "Used but in good condition",
            "USED_ACCEPTABLE": "In acceptable condition",
            "FOR_PARTS_OR_NOT_WORKING": "Not fully functioning, suitable for parts",
            "PRE_OWNED_EXCELLENT": "Previously owned, in excellent condition",
            "PRE_OWNED_FAIR": "Previously owned, in fair condition with significant wear"
        }


class CurrencyCodeEnum(BaseEbayEnum):
    """
    ISO 4217 currency codes.
    Docs: https://developer.ebay.com/api-docs/sell/account/types/ba:CurrencyCodeEnum
    """
    # Major currencies
    USD = "USD"  # US Dollar
    EUR = "EUR"  # Euro
    GBP = "GBP"  # British Pound Sterling
    JPY = "JPY"  # Japanese Yen
    CHF = "CHF"  # Swiss Franc
    CAD = "CAD"  # Canadian Dollar
    AUD = "AUD"  # Australian Dollar
    NZD = "NZD"  # New Zealand Dollar
    
    # Asian currencies
    CNY = "CNY"  # Chinese Yuan Renminbi
    HKD = "HKD"  # Hong Kong Dollar
    SGD = "SGD"  # Singapore Dollar
    TWD = "TWD"  # Taiwan Dollar
    KRW = "KRW"  # South Korean Won
    THB = "THB"  # Thai Baht
    MYR = "MYR"  # Malaysian Ringgit
    IDR = "IDR"  # Indonesian Rupiah
    PHP = "PHP"  # Philippine Peso
    VND = "VND"  # Vietnamese Dong
    INR = "INR"  # Indian Rupee
    PKR = "PKR"  # Pakistani Rupee
    BDT = "BDT"  # Bangladeshi Taka
    LKR = "LKR"  # Sri Lankan Rupee
    
    # European currencies (non-Euro)
    SEK = "SEK"  # Swedish Krona
    NOK = "NOK"  # Norwegian Krone
    DKK = "DKK"  # Danish Krone
    PLN = "PLN"  # Polish Zloty
    CZK = "CZK"  # Czech Koruna
    HUF = "HUF"  # Hungarian Forint
    RON = "RON"  # Romanian Leu
    BGN = "BGN"  # Bulgarian Lev
    HRK = "HRK"  # Croatian Kuna
    RUB = "RUB"  # Russian Ruble
    UAH = "UAH"  # Ukrainian Hryvnia
    TRY = "TRY"  # Turkish Lira
    
    # Middle Eastern currencies
    AED = "AED"  # UAE Dirham
    SAR = "SAR"  # Saudi Riyal
    QAR = "QAR"  # Qatari Riyal
    KWD = "KWD"  # Kuwaiti Dinar
    BHD = "BHD"  # Bahraini Dinar
    OMR = "OMR"  # Omani Rial
    JOD = "JOD"  # Jordanian Dinar
    ILS = "ILS"  # Israeli Shekel
    
    # African currencies
    ZAR = "ZAR"  # South African Rand
    NGN = "NGN"  # Nigerian Naira
    EGP = "EGP"  # Egyptian Pound
    KES = "KES"  # Kenyan Shilling
    GHS = "GHS"  # Ghanaian Cedi
    MAD = "MAD"  # Moroccan Dirham
    
    # Latin American currencies
    MXN = "MXN"  # Mexican Peso
    BRL = "BRL"  # Brazilian Real
    ARS = "ARS"  # Argentine Peso
    CLP = "CLP"  # Chilean Peso
    COP = "COP"  # Colombian Peso
    PEN = "PEN"  # Peruvian Sol
    UYU = "UYU"  # Uruguayan Peso
    VEF = "VEF"  # Venezuelan Bolivar
    
    # Caribbean currencies
    JMD = "JMD"  # Jamaican Dollar
    BBD = "BBD"  # Barbadian Dollar
    TTD = "TTD"  # Trinidad and Tobago Dollar
    
    # Pacific currencies
    FJD = "FJD"  # Fijian Dollar
    PGK = "PGK"  # Papua New Guinean Kina
    
    # Other currencies
    ISK = "ISK"  # Icelandic Krona
    BAM = "BAM"  # Bosnia-Herzegovina Convertible Mark
    MKD = "MKD"  # Macedonian Denar
    ALL = "ALL"  # Albanian Lek
    RSD = "RSD"  # Serbian Dinar
    BYN = "BYN"  # Belarusian Ruble
    GEL = "GEL"  # Georgian Lari
    AZN = "AZN"  # Azerbaijani Manat
    KZT = "KZT"  # Kazakhstani Tenge
    UZS = "UZS"  # Uzbekistani Som
    
    @classmethod
    def _get_descriptions(cls) -> Dict[str, str]:
        """Return currency names for common currencies."""
        return {
            "USD": "United States Dollar",
            "EUR": "Euro",
            "GBP": "British Pound Sterling",
            "JPY": "Japanese Yen",
            "CHF": "Swiss Franc",
            "CAD": "Canadian Dollar",
            "AUD": "Australian Dollar",
            "CNY": "Chinese Yuan Renminbi",
            "HKD": "Hong Kong Dollar",
            "SGD": "Singapore Dollar",
            "INR": "Indian Rupee",
            "KRW": "South Korean Won",
            "MXN": "Mexican Peso",
            "BRL": "Brazilian Real",
            "ZAR": "South African Rand",
            "AED": "UAE Dirham",
            "SAR": "Saudi Riyal",
            "SEK": "Swedish Krona",
            "NOK": "Norwegian Krone",
            "DKK": "Danish Krone",
            "PLN": "Polish Zloty",
            "RUB": "Russian Ruble",
            "TRY": "Turkish Lira",
            "NZD": "New Zealand Dollar"
        }


class LocaleEnum(BaseEbayEnum):
    """
    Locale values for specifying language and country.
    Docs: https://developer.ebay.com/api-docs/sell/inventory/types/slr:LocaleEnum
    """
    en_US = "en_US"
    en_GB = "en_GB"
    en_AU = "en_AU"
    en_CA = "en_CA"
    fr_FR = "fr_FR"
    de_DE = "de_DE"
    it_IT = "it_IT"
    es_ES = "es_ES"
    zh_CN = "zh_CN"
    zh_HK = "zh_HK"
    ja_JP = "ja_JP"
    ko_KR = "ko_KR"
    pt_BR = "pt_BR"
    ru_RU = "ru_RU"
    nl_NL = "nl_NL"
    pl_PL = "pl_PL"
    
    @classmethod
    def _get_descriptions(cls) -> Dict[str, str]:
        return {
            "en_US": "English (United States)",
            "en_GB": "English (United Kingdom)",
            "en_AU": "English (Australia)",
            "en_CA": "English (Canada)",
            "fr_FR": "French (France)",
            "de_DE": "German (Germany)",
            "it_IT": "Italian (Italy)",
            "es_ES": "Spanish (Spain)",
            "zh_CN": "Chinese (Simplified, China)",
            "zh_HK": "Chinese (Traditional, Hong Kong)",
            "ja_JP": "Japanese (Japan)",
            "ko_KR": "Korean (South Korea)",
            "pt_BR": "Portuguese (Brazil)",
            "ru_RU": "Russian (Russia)",
            "nl_NL": "Dutch (Netherlands)",
            "pl_PL": "Polish (Poland)"
        }


class LengthUnitOfMeasureEnum(BaseEbayEnum):
    """
    Units for measuring length/dimensions.
    Docs: https://developer.ebay.com/api-docs/sell/inventory/types/slr:LengthUnitOfMeasureEnum
    """
    INCH = "INCH"
    FEET = "FEET"
    CENTIMETER = "CENTIMETER"
    METER = "METER"
    
    @classmethod
    def _get_descriptions(cls) -> Dict[str, str]:
        return {
            "INCH": "Inches",
            "FEET": "Feet",
            "CENTIMETER": "Centimeters",
            "METER": "Meters"
        }


class MarketplaceIdEnum(BaseEbayEnum):
    """
    eBay marketplace identifiers.
    Docs: https://developer.ebay.com/api-docs/sell/account/types/ba:MarketplaceIdEnum
    """
    # Americas
    EBAY_US = "EBAY_US"  # United States
    EBAY_CA = "EBAY_CA"  # Canada
    EBAY_MX = "EBAY_MX"  # Mexico
    EBAY_BR = "EBAY_BR"  # Brazil
    
    # Europe
    EBAY_GB = "EBAY_GB"  # United Kingdom
    EBAY_DE = "EBAY_DE"  # Germany
    EBAY_FR = "EBAY_FR"  # France
    EBAY_IT = "EBAY_IT"  # Italy
    EBAY_ES = "EBAY_ES"  # Spain
    EBAY_NL = "EBAY_NL"  # Netherlands
    EBAY_BE = "EBAY_BE"  # Belgium
    EBAY_AT = "EBAY_AT"  # Austria
    EBAY_CH = "EBAY_CH"  # Switzerland
    EBAY_IE = "EBAY_IE"  # Ireland
    EBAY_PL = "EBAY_PL"  # Poland
    EBAY_SE = "EBAY_SE"  # Sweden
    EBAY_FI = "EBAY_FI"  # Finland
    EBAY_DK = "EBAY_DK"  # Denmark
    EBAY_NO = "EBAY_NO"  # Norway
    EBAY_CZ = "EBAY_CZ"  # Czech Republic
    EBAY_RU = "EBAY_RU"  # Russia
    EBAY_TR = "EBAY_TR"  # Turkey
    
    # Asia Pacific
    EBAY_AU = "EBAY_AU"  # Australia
    EBAY_CN = "EBAY_CN"  # China
    EBAY_HK = "EBAY_HK"  # Hong Kong
    EBAY_IN = "EBAY_IN"  # India
    EBAY_MY = "EBAY_MY"  # Malaysia
    EBAY_PH = "EBAY_PH"  # Philippines
    EBAY_SG = "EBAY_SG"  # Singapore
    EBAY_TH = "EBAY_TH"  # Thailand
    EBAY_TW = "EBAY_TW"  # Taiwan
    EBAY_VN = "EBAY_VN"  # Vietnam
    EBAY_JP = "EBAY_JP"  # Japan
    EBAY_ID = "EBAY_ID"  # Indonesia
    
    # Middle East & Africa
    EBAY_IL = "EBAY_IL"  # Israel
    EBAY_ZA = "EBAY_ZA"  # South Africa
    
    # Motors
    EBAY_MOTORS_US = "EBAY_MOTORS_US"  # eBay Motors US
    
    @classmethod
    def _get_descriptions(cls) -> Dict[str, str]:
        return {
            "EBAY_US": "eBay United States (ebay.com)",
            "EBAY_CA": "eBay Canada (ebay.ca)",
            "EBAY_GB": "eBay United Kingdom (ebay.co.uk)",
            "EBAY_AU": "eBay Australia (ebay.com.au)",
            "EBAY_DE": "eBay Germany (ebay.de)",
            "EBAY_FR": "eBay France (ebay.fr)",
            "EBAY_IT": "eBay Italy (ebay.it)",
            "EBAY_ES": "eBay Spain (ebay.es)",
            "EBAY_CN": "eBay China",
            "EBAY_HK": "eBay Hong Kong",
            "EBAY_IN": "eBay India (ebay.in)",
            "EBAY_JP": "eBay Japan",
            "EBAY_MOTORS_US": "eBay Motors United States"
        }


class PackageTypeEnum(BaseEbayEnum):
    """
    Package types for shipping.
    Docs: https://developer.ebay.com/api-docs/sell/inventory/types/slr:PackageTypeEnum
    """
    LETTER = "LETTER"
    LARGE_ENVELOPE = "LARGE_ENVELOPE"
    PACKAGE_THICK_ENVELOPE = "PACKAGE_THICK_ENVELOPE"
    PARCEL = "PARCEL"
    FLAT_RATE_ENVELOPE = "FLAT_RATE_ENVELOPE"
    FLAT_RATE_BOX = "FLAT_RATE_BOX"
    LARGE_PACKAGE = "LARGE_PACKAGE"
    EXTRA_LARGE_PACKAGE = "EXTRA_LARGE_PACKAGE"
    
    @classmethod
    def _get_descriptions(cls) -> Dict[str, str]:
        return {
            "LETTER": "Standard letter envelope",
            "LARGE_ENVELOPE": "Large envelope or flat",
            "PACKAGE_THICK_ENVELOPE": "Thick envelope or small package",
            "PARCEL": "Standard parcel or box",
            "FLAT_RATE_ENVELOPE": "USPS flat rate envelope",
            "FLAT_RATE_BOX": "USPS flat rate box",
            "LARGE_PACKAGE": "Large package",
            "EXTRA_LARGE_PACKAGE": "Extra large or oversized package"
        }


class PaymentInstrumentBrandEnum(BaseEbayEnum):
    """
    Payment instrument brands.
    Docs: https://developer.ebay.com/api-docs/sell/account/types/api:PaymentInstrumentBrandEnum
    """
    VISA = "VISA"
    MASTERCARD = "MASTERCARD"
    AMERICAN_EXPRESS = "AMERICAN_EXPRESS"
    DISCOVER = "DISCOVER"
    JCB = "JCB"
    DINERS_CLUB = "DINERS_CLUB"
    CREDIT_CARD = "CREDIT_CARD"
    PAYPAL = "PAYPAL"
    
    @classmethod
    def _get_descriptions(cls) -> Dict[str, str]:
        return {
            "VISA": "Visa credit/debit card",
            "MASTERCARD": "Mastercard credit/debit card",
            "AMERICAN_EXPRESS": "American Express card",
            "DISCOVER": "Discover card",
            "JCB": "Japan Credit Bureau card",
            "DINERS_CLUB": "Diners Club card",
            "CREDIT_CARD": "Generic credit card",
            "PAYPAL": "PayPal payment"
        }


class PaymentMethodTypeEnum(BaseEbayEnum):
    """
    Payment method types for offline payments.
    Docs: https://developer.ebay.com/api-docs/sell/account/types/api:PaymentMethodTypeEnum
    """
    CASH_IN_PERSON = "CASH_IN_PERSON"
    CASH_ON_DELIVERY = "CASH_ON_DELIVERY"
    CASH_ON_PICKUP = "CASH_ON_PICKUP"
    PERSONAL_CHECK = "PERSONAL_CHECK"
    MONEY_ORDER = "MONEY_ORDER"
    CASHIER_CHECK = "CASHIER_CHECK"
    
    @classmethod
    def _get_descriptions(cls) -> Dict[str, str]:
        return {
            "CASH_IN_PERSON": "Cash payment in person",
            "CASH_ON_DELIVERY": "Cash on delivery (COD)",
            "CASH_ON_PICKUP": "Cash when item is picked up",
            "PERSONAL_CHECK": "Personal check payment",
            "MONEY_ORDER": "Money order payment",
            "CASHIER_CHECK": "Cashier's check payment"
        }


class RecipientAccountReferenceTypeEnum(BaseEbayEnum):
    """
    Recipient account reference types.
    Docs: https://developer.ebay.com/api-docs/sell/account/types/api:RecipientAccountReferenceTypeEnum
    """
    PAYPAL_EMAIL = "PAYPAL_EMAIL"
    
    @classmethod
    def _get_descriptions(cls) -> Dict[str, str]:
        return {
            "PAYPAL_EMAIL": "PayPal email address"
        }


class RefundMethodEnum(BaseEbayEnum):
    """
    Refund methods for return policies.
    Docs: https://developer.ebay.com/api-docs/sell/account/types/api:RefundMethodEnum
    """
    MONEY_BACK = "MONEY_BACK"
    MERCHANDISE_CREDIT = "MERCHANDISE_CREDIT"
    
    @classmethod
    def _get_descriptions(cls) -> Dict[str, str]:
        return {
            "MONEY_BACK": "Full monetary refund",
            "MERCHANDISE_CREDIT": "Store credit or merchandise credit"
        }


class ReturnMethodEnum(BaseEbayEnum):
    """
    Return methods for return policies.
    Docs: https://developer.ebay.com/api-docs/sell/account/types/api:ReturnMethodEnum
    """
    EXCHANGE = "EXCHANGE"
    REPLACEMENT = "REPLACEMENT"
    
    @classmethod
    def _get_descriptions(cls) -> Dict[str, str]:
        return {
            "EXCHANGE": "Exchange for different item",
            "REPLACEMENT": "Replace with same item"
        }


class ReturnShippingCostPayerEnum(BaseEbayEnum):
    """
    Who pays for return shipping.
    Docs: https://developer.ebay.com/api-docs/sell/account/types/api:ReturnShippingCostPayerEnum
    """
    BUYER = "BUYER"
    SELLER = "SELLER"
    
    @classmethod
    def _get_descriptions(cls) -> Dict[str, str]:
        return {
            "BUYER": "Buyer pays return shipping",
            "SELLER": "Seller pays return shipping"
        }


class RegionTypeEnum(BaseEbayEnum):
    """
    Region types for shipping.
    Docs: https://developer.ebay.com/api-docs/sell/account/types/ba:RegionTypeEnum
    """
    COUNTRY = "COUNTRY"
    STATE_OR_PROVINCE = "STATE_OR_PROVINCE"
    POSTAL_CODE = "POSTAL_CODE"
    WORLDWIDE = "WORLDWIDE"
    
    @classmethod
    def _get_descriptions(cls) -> Dict[str, str]:
        return {
            "COUNTRY": "Country-level region",
            "STATE_OR_PROVINCE": "State or province level",
            "POSTAL_CODE": "Postal/ZIP code level",
            "WORLDWIDE": "Ships worldwide"
        }


class ShippingCostTypeEnum(BaseEbayEnum):
    """
    Shipping cost calculation types.
    Docs: https://developer.ebay.com/api-docs/sell/account/types/api:ShippingCostTypeEnum
    """
    FLAT_RATE = "FLAT_RATE"
    CALCULATED = "CALCULATED"
    
    @classmethod
    def _get_descriptions(cls) -> Dict[str, str]:
        return {
            "FLAT_RATE": "Fixed shipping cost",
            "CALCULATED": "Shipping cost calculated based on location"
        }


class ShippingOptionTypeEnum(BaseEbayEnum):
    """
    Shipping option types.
    Docs: https://developer.ebay.com/api-docs/sell/account/types/api:ShippingOptionTypeEnum
    """
    DOMESTIC = "DOMESTIC"
    INTERNATIONAL = "INTERNATIONAL"
    
    @classmethod
    def _get_descriptions(cls) -> Dict[str, str]:
        return {
            "DOMESTIC": "Domestic shipping within seller's country",
            "INTERNATIONAL": "International shipping to other countries"
        }


class TimeDurationUnitEnum(BaseEbayEnum):
    """
    Time duration units.
    Docs: https://developer.ebay.com/api-docs/sell/inventory/types/slr:TimeDurationUnitEnum
    """
    YEAR = "YEAR"
    MONTH = "MONTH"
    DAY = "DAY"
    HOUR = "HOUR"
    MINUTE = "MINUTE"
    SECOND = "SECOND"
    MILLISECOND = "MILLISECOND"
    
    @classmethod
    def _get_descriptions(cls) -> Dict[str, str]:
        return {
            "YEAR": "Years",
            "MONTH": "Months",
            "DAY": "Days",
            "HOUR": "Hours",
            "MINUTE": "Minutes",
            "SECOND": "Seconds",
            "MILLISECOND": "Milliseconds"
        }


class WeightUnitOfMeasureEnum(BaseEbayEnum):
    """
    Units for measuring weight.
    Docs: https://developer.ebay.com/api-docs/sell/inventory/types/slr:WeightUnitOfMeasureEnum
    """
    POUND = "POUND"
    OUNCE = "OUNCE"
    KILOGRAM = "KILOGRAM"
    GRAM = "GRAM"
    
    @classmethod
    def _get_descriptions(cls) -> Dict[str, str]:
        return {
            "POUND": "Pounds (lb)",
            "OUNCE": "Ounces (oz)",
            "KILOGRAM": "Kilograms (kg)",
            "GRAM": "Grams (g)"
        }


# Helper functions for enum usage
def validate_enum_value(enum_class: type[BaseEbayEnum], value: str) -> bool:
    """Validate if a value is valid for a given enum class."""
    return enum_class.is_valid(value)


def get_enum_from_string(enum_class: type[BaseEbayEnum], value: str) -> Optional[BaseEbayEnum]:
    """Convert string to enum value, with case-insensitive matching."""
    return enum_class.from_string(value)


def get_all_enum_values(enum_class: type[BaseEbayEnum]) -> List[str]:
    """Get all possible values for an enum class."""
    return enum_class.get_all_values()


def get_enum_description(enum_class: type[BaseEbayEnum], value: str) -> Optional[str]:
    """Get human-readable description for an enum value."""
    return enum_class.get_description(value)