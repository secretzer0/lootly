"""
Browse API enumerations for eBay search and filtering.

This module provides strongly-typed enumerations for all Browse API parameters
to ensure type safety and provide clear documentation for LLMs and developers.

All enums follow the Pydantic-First Development methodology.
"""
from enum import Enum


class SortField(str, Enum):
    """
    Sort options for Browse API search results.
    
    The sort parameter determines the order in which search results are returned.
    Price sorting considers the total cost (item price + shipping).
    """
    BEST_MATCH = "BestMatch"  # Default - eBay's relevance algorithm
    PRICE_ASC = "price"       # Lowest total price first (item + shipping)
    PRICE_DESC = "-price"     # Highest total price first
    NEWLY_LISTED = "newlyListed"  # Most recently listed items first
    ENDING_SOONEST = "endingSoonest"  # Auctions ending soonest first
    DISTANCE = "distance"     # Nearest items first (requires pickup filters)


class FilterField(str, Enum):
    """
    Available filter fields for Browse API search.
    
    These fields can be used to construct filter strings for the search endpoint.
    Multiple filters can be combined with commas.
    """
    PRICE = "price"                          # Price range filtering
    SELLERS = "sellers"                      # Filter by seller usernames
    BUYING_OPTIONS = "buyingOptions"         # Filter by listing format
    CONDITIONS = "conditions"                # Filter by item condition
    DELIVERY_COUNTRY = "deliveryCountry"     # Filter by delivery location
    PICKUP_COUNTRY = "pickupCountry"         # Filter by pickup country
    PICKUP_POSTAL_CODE = "pickupPostalCode"  # Filter by pickup postal code
    CHARITY_ONLY = "charityOnly"             # Show only charity listings
    GUARANTEED_DELIVERY = "guaranteedDelivery"  # Filter by guaranteed delivery
    ITEM_LOCATION_COUNTRY = "itemLocationCountry"  # Filter by item location
    BID_COUNT = "bidCount"                   # Filter by number of bids
    CONDITIONIDS = "conditionIds"            # Legacy condition ID filtering


class BuyingOption(str, Enum):
    """
    Buying format options for the buyingOptions filter.
    
    These values can be combined using pipe (|) separator in the filter string.
    Example: buyingOptions:{FIXED_PRICE|BEST_OFFER}
    """
    FIXED_PRICE = "FIXED_PRICE"      # Buy It Now listings
    AUCTION = "AUCTION"              # Auction format listings
    BEST_OFFER = "BEST_OFFER"        # Listings accepting offers
    CLASSIFIED_AD = "CLASSIFIED_AD"  # Classified ad format


class ItemCondition(str, Enum):
    """
    Item condition values for the conditions filter.
    
    These values can be combined using pipe (|) separator in the filter string.
    Example: conditions:{NEW|LIKE_NEW}
    """
    NEW = "NEW"                                          # Brand new items
    LIKE_NEW = "LIKE_NEW"                                # Nearly new condition
    VERY_GOOD = "VERY_GOOD"                              # Very good condition
    GOOD = "GOOD"                                        # Good condition
    ACCEPTABLE = "ACCEPTABLE"                            # Acceptable condition
    FOR_PARTS_OR_NOT_WORKING = "FOR_PARTS_OR_NOT_WORKING"  # Parts/repair only
    CERTIFIED_REFURBISHED = "CERTIFIED_REFURBISHED"      # Certified refurbished
    EXCELLENT_REFURBISHED = "EXCELLENT_REFURBISHED"      # Excellent refurbished
    VERY_GOOD_REFURBISHED = "VERY_GOOD_REFURBISHED"     # Very good refurbished
    GOOD_REFURBISHED = "GOOD_REFURBISHED"                # Good refurbished
    SELLER_REFURBISHED = "SELLER_REFURBISHED"            # Seller refurbished
    USED = "USED"                                        # General used condition


class ConditionId(int, Enum):
    """
    Legacy numeric condition IDs for conditionIds filter.
    
    These numeric IDs are used with the conditionIds filter for backward compatibility.
    Example: conditionIds:{1000|1500}
    """
    NEW = 1000
    NEW_OTHER = 1500
    NEW_WITH_DEFECTS = 1750
    CERTIFIED_REFURBISHED = 2000
    EXCELLENT_REFURBISHED = 2010
    VERY_GOOD_REFURBISHED = 2020
    GOOD_REFURBISHED = 2030
    SELLER_REFURBISHED = 2500
    LIKE_NEW = 2750
    USED = 3000
    VERY_GOOD = 4000
    GOOD = 5000
    ACCEPTABLE = 6000
    FOR_PARTS_NOT_WORKING = 7000


class DeliveryOption(str, Enum):
    """
    Delivery options for advanced filtering.
    
    Used with delivery-related filters to specify shipping preferences.
    """
    SHIP_TO_HOME = "SHIP_TO_HOME"
    SELLER_ARRANGED = "SELLER_ARRANGED"
    PICKUP_DROP_OFF = "PICKUP_DROP_OFF"
    LOCKER_PICKUP = "LOCKER_PICKUP"


class MarketplaceId(str, Enum):
    """
    eBay marketplace identifiers for the Browse API.
    
    Each marketplace represents a different eBay site/country.
    """
    EBAY_US = "EBAY_US"              # United States (ebay.com)
    EBAY_CA = "EBAY_CA"              # Canada (ebay.ca)
    EBAY_GB = "EBAY_GB"              # United Kingdom (ebay.co.uk)
    EBAY_AU = "EBAY_AU"              # Australia (ebay.com.au)
    EBAY_DE = "EBAY_DE"              # Germany (ebay.de)
    EBAY_FR = "EBAY_FR"              # France (ebay.fr)
    EBAY_IT = "EBAY_IT"              # Italy (ebay.it)
    EBAY_ES = "EBAY_ES"              # Spain (ebay.es)
    EBAY_CH = "EBAY_CH"              # Switzerland (ebay.ch)
    EBAY_NL = "EBAY_NL"              # Netherlands (ebay.nl)
    EBAY_BE = "EBAY_BE"              # Belgium (ebay.be)
    EBAY_AT = "EBAY_AT"              # Austria (ebay.at)
    EBAY_IE = "EBAY_IE"              # Ireland (ebay.ie)
    EBAY_PL = "EBAY_PL"              # Poland (ebay.pl)
    EBAY_SG = "EBAY_SG"              # Singapore (ebay.com.sg)
    EBAY_MY = "EBAY_MY"              # Malaysia (ebay.com.my)
    EBAY_PH = "EBAY_PH"              # Philippines (ebay.ph)
    EBAY_HK = "EBAY_HK"              # Hong Kong (ebay.com.hk)
    EBAY_IN = "EBAY_IN"              # India (ebay.in)
    EBAY_CN = "EBAY_CN"              # China (ebay.cn)
    EBAY_JP = "EBAY_JP"              # Japan (ebay.co.jp)
    EBAY_RU = "EBAY_RU"              # Russia (ebay.ru)
    EBAY_MOTOR = "EBAY_MOTOR"        # eBay Motors (motors.ebay.com)