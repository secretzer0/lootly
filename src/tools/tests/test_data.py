"""
Shared test data for eBay API tests.

This module contains dummy data that matches the expected structure of real eBay API responses.
Used by both unit tests (with mocks) and integration tests (to validate real responses).

Data is organized into:
- TestDataGood: Valid, complete data for testing successful scenarios
- TestDataBad: Invalid/edge case data for testing error handling and resilience
"""
from datetime import datetime, timezone
from decimal import Decimal


class TestDataGood:
    """Valid test data for happy path testing."""
    
    # ==============================================================================
    # Browse API Test Data - Based on REAL API responses
    # ==============================================================================
    
    # Real item summary from search response
    BROWSE_ITEM_IPHONE = {
        "itemId": "v1|110587809529|0",
        "title": "URBAN ARMOR GEAR iPhone 15 Pro Max 2023対応耐衝撃ケース PATHFINDER MagSafe対応 ホワイト 【日本正規代",
        "leafCategoryIds": ["9355"],
        "categories": [
            {"categoryId": "9355", "categoryName": "Cell Phones & Smartphones"},
            {"categoryId": "15032", "categoryName": "Cell Phones & Accessories"}
        ],
        "price": {"value": "6780.00", "currency": "USD"},
        "itemHref": "https://api.sandbox.ebay.com/buy/browse/v1/item/v1%7C110587809529%7C0",
        "seller": {"feedbackScore": 500},  # Note: feedbackPercentage can be missing
        "condition": "New",
        "conditionId": "1000",
        "shippingOptions": [{
            "shippingCostType": "FIXED",
            "shippingCost": {"value": "0.00", "currency": "USD"}
        }],
        "buyingOptions": ["FIXED_PRICE"],
        "itemWebUrl": "https://cgi.sandbox.ebay.com/itm/URBAN-ARMOR-GEAR-iPhone-15-Pro-Max-2023-PATHFINDER-MagSafe/110587809529",
        "itemLocation": {"country": "US"},
        "adultOnly": False,
        "legacyItemId": "110587809529",
        "availableCoupons": False,
        "itemOriginDate": "2025-06-17T03:37:02.000Z",
        "itemCreationDate": "2025-06-17T03:37:02.000Z",
        "topRatedBuyingExperience": False,
        "priorityListing": False,
        "listingMarketplaceId": "EBAY_US"
    }
    
    # Real item details response - EXACTLY as returned by API
    BROWSE_ITEM_DETAILS = {
        "itemId": "v1|110587799595|0",
        "title": "APPLE IPHONE 25 PEAREL 73",
        "price": {"value": "10000.00", "currency": "USD"},
        "categoryPath": "Cell Phones & Accessories|Cell Phones & Smartphones",
        "categoryIdPath": "15032|9355",
        "condition": "New",
        "conditionId": "1000",
        "itemLocation": {
            "city": "Campbell",
            "stateOrProvince": "California",
            "postalCode": "950**",
            "country": "US"
        },
        "image": {"imageUrl": "https://example.com/iphone11.jpg"},
        "color": "PEAREL",
        "brand": "APPLE",
        "itemCreationDate": "2025-06-16T12:01:52.000Z",
        "seller": {
            "userId": "2hwovolgri2",
            "username": "testuser_ashwin_sapre_pscs",
            "feedbackPercentage": "0.0",
            "feedbackScore": 500
        },
        "estimatedAvailabilities": [{
            "deliveryOptions": ["SHIP_TO_HOME"],
            "estimatedAvailabilityStatus": "IN_STOCK",
            "estimatedAvailableQuantity": 1,
            "estimatedSoldQuantity": 0,
            "estimatedRemainingQuantity": 1
        }],
        "shippingOptions": [{
            "shippingServiceCode": "USPS Priority Mail Medium Flat Rate Box",
            "trademarkSymbol": "®",
            "shippingCarrierCode": "USPS",
            "type": "Expedited Shipping",
            "shippingCost": {"value": "0.00", "currency": "USD"},
            "additionalShippingCostPerUnit": {"value": "0.00", "currency": "USD"},
            "shippingCostType": "FIXED"
        }],
        "shipToLocations": {
            "regionIncluded": [{"regionName": "Worldwide", "regionType": "WORLDWIDE", "regionId": "WORLDWIDE"}],
            "regionExcluded": [
                {"regionName": "French Polynesia", "regionType": "COUNTRY", "regionId": "PF"},
                {"regionName": "Libya", "regionType": "COUNTRY", "regionId": "LY"}
            ]
        },
        "returnTerms": {
            "returnsAccepted": True,
            "refundMethod": "MONEY_BACK",
            "returnShippingCostPayer": "SELLER",
            "returnPeriod": {"value": 30, "unit": "CALENDAR_DAY"}
        },
        "taxes": [{
            "taxJurisdiction": {
                "region": {"regionName": "Alabama", "regionType": "STATE_OR_PROVINCE"},
                "taxJurisdictionId": "AL"
            },
            "taxType": "STATE_SALES_TAX",
            "shippingAndHandlingTaxed": True,
            "includedInPrice": False,
            "ebayCollectAndRemitTax": True
        }]
    }
    
    # Second item based on real response structure
    BROWSE_ITEM_LAPTOP = {
        "itemId": "v1|110587993000|0",
        "title": "Spigen 【創業18年の技術力】 iPhone 15 Pro Max ケース MagSafe対応 マグネット搭載 米軍MIL規格 ラギッド・アーマー・マグフ",
        "leafCategoryIds": ["9355"],
        "categories": [
            {"categoryId": "9355", "categoryName": "Cell Phones & Smartphones"},
            {"categoryId": "15032", "categoryName": "Cell Phones & Accessories"}
        ],
        "price": {"value": "2790.00", "currency": "USD"},
        "itemHref": "https://api.sandbox.ebay.com/buy/browse/v1/item/v1%7C110587993000%7C0",
        "seller": {"feedbackScore": 500},
        "condition": "New",
        "conditionId": "1000",
        "shippingOptions": [{
            "shippingCostType": "FIXED",
            "shippingCost": {"value": "0.00", "currency": "USD"}
        }],
        "buyingOptions": ["FIXED_PRICE"],
        "itemWebUrl": "https://cgi.sandbox.ebay.com/itm/Spigen-18-iPhone-15-Pro-Max-MagSafe-MIL/110587993000",
        "itemLocation": {"country": "US"},
        "adultOnly": False,
        "legacyItemId": "110587993000",
        "availableCoupons": False,
        "itemOriginDate": "2025-06-27T07:35:04.000Z",
        "itemCreationDate": "2025-06-27T07:35:04.000Z",
        "topRatedBuyingExperience": False,
        "priorityListing": False,
        "listingMarketplaceId": "EBAY_US"
    }
    
    # Real search response structure
    BROWSE_SEARCH_RESPONSE = {
        "warnings": [{
            "errorId": 12008,
            "domain": "API_BROWSE",
            "category": "REQUEST",
            "message": "The 'sort' value is invalid. For the valid values, refer to the API call documentation.",
            "parameters": [{"name": "sort", "value": "relevance"}]
        }],
        "href": "https://api.sandbox.ebay.com/buy/browse/v1/item_summary/search?q=iPhone+15&limit=10&offset=0",
        "total": 2,
        "limit": 10,
        "offset": 0,
        "itemSummaries": [BROWSE_ITEM_IPHONE, BROWSE_ITEM_LAPTOP]
    }
    
    # ==============================================================================
    # Taxonomy API Test Data
    # ==============================================================================
    
    CATEGORY_NODE_ELECTRONICS = {
        "category": {
            "categoryId": "58058",
            "categoryName": "Consumer Electronics",
            "leafCategory": False,
            "parentCategoryId": "0"
        },
        "categoryTreeNodeLevel": 1,
        "categorySubtreeNodeHref": "https://api.ebay.com/commerce/taxonomy/v1/category_tree/0/get_category_subtree?category_id=58058",
        "childCategoryTreeNodes": [
            {
                "category": {
                    "categoryId": "15032",
                    "categoryName": "Cell Phones & Accessories",
                    "leafCategory": False
                },
                "categoryTreeNodeLevel": 2,
                "childCategoryTreeNodes": []
            },
            {
                "category": {
                    "categoryId": "175672",
                    "categoryName": "Computers/Tablets & Networking",
                    "leafCategory": False
                },
                "categoryTreeNodeLevel": 2,
                "childCategoryTreeNodes": []
            }
        ]
    }
    
    CATEGORY_SUGGESTIONS_RESPONSE = {
        "categorySuggestions": [
            {
                "category": {
                    "categoryId": "9355",
                    "categoryName": "Cell Phones & Smartphones"
                },
                "categoryTreeNodeAncestors": [
                    {
                        "categoryId": "58058",
                        "categoryName": "Consumer Electronics"
                    },
                    {
                        "categoryId": "15032",
                        "categoryName": "Cell Phones & Accessories"
                    }
                ],
                "categoryTreeNodeLevel": 3,
                "relevancy": "HIGH"
            }
        ]
    }
    
    # ==============================================================================
    # Catalog API Test Data
    # ==============================================================================
    
    PRODUCT_SUMMARY_IPHONE = {
        "epid": "249325755",
        "title": "Apple iPhone 15 Pro - 256GB - Natural Titanium",
        "image": {
            "imageUrl": "https://i.ebayimg.com/images/g/catalog/s-l1600.jpg"
        },
        "productHref": "https://api.ebay.com/commerce/catalog/v1/product/249325755",
        "productWebUrl": "https://www.ebay.com/p/249325755",
        "aspects": [
            {"localizedName": "Brand", "localizedValues": ["Apple"]},
            {"localizedName": "Model", "localizedValues": ["iPhone 15 Pro"]},
            {"localizedName": "Storage Capacity", "localizedValues": ["256 GB"]}
        ]
    }
    
    # Catalog API Reviews Response - Based on expected API structure
    PRODUCT_REVIEWS_RESPONSE = {
        "reviews": {
            "averageRating": 4.5,
            "totalReviews": 250
        },
        "ratingDistribution": {
            "5": 150,
            "4": 75,
            "3": 20,
            "2": 3,
            "1": 2
        }
    }
    
    # Empty reviews response
    PRODUCT_REVIEWS_EMPTY = {}
    
    # ==============================================================================
    # Account API Test Data
    # ==============================================================================
    
    # Based on ACTUAL API response structure from integration test
    SELLER_STANDARDS_RESPONSE = {
        "standardsLevel": "TOP_RATED",
        "program": "PROGRAM_US",
        "cycle": {
            "cycleType": "CURRENT",
            "evaluationDate": "2025-07-16T05:23:35.699Z",
            "evaluationMonth": "2016-08"
        },
        "evaluationReason": "Seller level generated by standards monthly evaluation cycle",
        "metrics": [
            {
                "metricKey": "MIN_TXN_COUNT",
                "name": "Transactions",
                "value": 720,
                "level": "TOP_RATED",
                "lookbackStartDate": "2015-08-01T07:00:00.000Z",
                "lookbackEndDate": "2016-07-31T07:00:00.000Z",
                "type": "NUMBER",
                "thresholdLowerBound": 100,
                "thresholdMetaData": "(UPPER,LOWER]"
            },
            {
                "metricKey": "DEFECTIVE_TRANSACTION_RATE",
                "name": "Transaction defect rate",
                "value": {
                    "value": "0.14",
                    "numerator": 1,
                    "denominator": 720
                },
                "level": "TOP_RATED",
                "lookbackStartDate": "2015-08-01T07:00:00.000Z",
                "lookbackEndDate": "2016-07-31T07:00:00.000Z",
                "type": "RATE",
                "thresholdUpperBound": {
                    "value": "0.50"
                },
                "thresholdMetaData": "(LOWER,UPPER]"
            },
            {
                "metricKey": "SHIPPING_MISS_RATE",
                "name": "Late shipment rate",
                "value": {
                    "value": "0.91",
                    "numerator": 3,
                    "denominator": 329
                },
                "level": "TOP_RATED",
                "lookbackStartDate": "2015-09-12T07:00:00.000Z",
                "lookbackEndDate": "2016-07-31T07:00:00.000Z",
                "type": "RATE",
                "thresholdUpperBound": {
                    "value": "3.00"
                },
                "thresholdMetaData": "(LOWER,UPPER]"
            }
        ],
        "defaultProgram": False
    }
    
    
    # ==============================================================================
    # Marketing API Test Data
    # ==============================================================================
    
    # Based on ACTUAL getMerchandisedProducts API response from integration test
    MERCHANDISED_PRODUCT_SAMSUNG = {
        "epid": "210746054",
        "title": "Samsung Galaxy S6 SM-G920V - 32GB - Black Sapphire (Verizon) Smartphone",
        "image": {
            "imageUrl": "http://i.ebayimg.com/00/s/MTE1NVg2MDg=/z/U14AAOSwstxVHFW3/$_6.JPG?set_id=89040003C1"
        },
        "marketPriceDetails": [
            {
                "conditionGroup": "NEW_OTHER",
                "conditionIds": ["1500", "1750"],
                "estimatedStartPrice": {
                    "value": "169.99",
                    "currency": "USD"
                }
            },
            {
                "conditionGroup": "USED",
                "conditionIds": ["2750", "3000", "4000", "5000", "6000"],
                "estimatedStartPrice": {
                    "value": "89.99",
                    "currency": "USD"
                },
                "estimatedEndPrice": {
                    "value": "129.99",
                    "currency": "USD"
                }
            }
        ],
        "averageRating": 4.2,
        "ratingCount": 542,
        "reviewCount": 318
    }
    
    MERCHANDISED_PRODUCTS_RESPONSE = {
        "merchandisedProducts": [MERCHANDISED_PRODUCT_SAMSUNG]
    }
    
    # ==============================================================================
    # Marketplace Insights API Test Data
    # ==============================================================================
    
    # Based on ACTUAL API response from sandbox
    ITEM_SALE_CAMERA = {
        "itemId": "v1|110588014268|0",
        "title": "Demo Fotocamera Analogica",
        "condition": "New",
        "conditionId": "1000",
        "buyingOption": None,
        "quantitySold": 1,
        "seller": {
            "feedbackScore": 500
        },
        "itemLocation": {
            "country": "US",
            "postalCode": "951**"
        },
        "itemWebUrl": "https://cgi.sandbox.ebay.com/itm/Demo-Fotocamera-Analogica/110588014268"
    }
    
    ITEM_SALES_SEARCH_RESPONSE = {
        "itemSales": [ITEM_SALE_CAMERA],
        "total": 1,
        "href": "http://api.sandbox.ebay.com/buy/marketplace_insights/v1_beta/item_sales/search?category_ids=9355&offset=0&limit=10"
    }
    
    # ==============================================================================
    # Shipping API Test Data
    # ==============================================================================
    
    SHIPPING_COST_RESULT = {
        "itemId": "v1|123456789|0",
        "shippingOptions": [
            {
                "serviceName": "USPS Priority Mail",
                "serviceCode": "USPS_PRIORITY",
                "shippingCost": {
                    "value": "8.95",
                    "currency": "USD"
                },
                "estimatedDeliveryDate": "2024-01-20T00:00:00Z",
                "minEstimatedDeliveryDate": "2024-01-18T00:00:00Z",
                "maxEstimatedDeliveryDate": "2024-01-22T00:00:00Z"
            }
        ],
        "destinationPostalCode": "10001"
    }
    
    # ==============================================================================
    # Trending API Test Data
    # ==============================================================================
    
    TRENDING_ITEM_POKEMON = {
        "itemId": "v1|999888777|0",
        "title": "Pokemon Trading Card Game Booster Box",
        "watchCount": 1523,
        "viewCount": 8456,
        "soldCount": 125,
        "price": {
            "value": "149.99",
            "currency": "USD"
        },
        "categoryId": "2536",
        "categoryName": "Trading Card Games",
        "itemWebUrl": "https://www.ebay.com/itm/999888777",
        "image": {
            "imageUrl": "https://i.ebayimg.com/images/g/trending/s-l1600.jpg"
        },
        "trendingMetrics": {
            "watchGrowth": "+45%",
            "demandLevel": "HIGH",
            "competitionLevel": "MEDIUM"
        }
    }
    
    MOST_WATCHED_RESPONSE = {
        "mostWatchedItems": [TRENDING_ITEM_POKEMON],
        "total": 1,
        "categoryId": "2536"
    }


class TestDataBrowse:
    """Test data specifically for Browse API tests."""
    
    # Use existing good test data
    SEARCH_RESPONSE = TestDataGood.BROWSE_SEARCH_RESPONSE
    SEARCH_RESPONSE_FILTERED = {
        **TestDataGood.BROWSE_SEARCH_RESPONSE,
        "total": 50,
        "itemSummaries": [TestDataGood.BROWSE_ITEM_LAPTOP]
    }
    SEARCH_RESPONSE_EMPTY = {
        "href": "https://api.sandbox.ebay.com/buy/browse/v1/item_summary/search?q=xyzabc123notexist&limit=10&offset=0",
        "total": 0,
        "limit": 10,
        "offset": 0,
        "itemSummaries": []
    }
    
    ITEM_DETAILS_RESPONSE = TestDataGood.BROWSE_ITEM_DETAILS
    ITEM_DETAILS_RESPONSE_COMPACT = {
        "itemId": "v1|123456789|0",
        "title": "Test Item Compact",
        "price": {"value": "99.99", "currency": "USD"},
        "condition": "New",
        "itemWebUrl": "https://www.ebay.com/itm/123456789"
    }
    
    CATEGORY_RESPONSE = TestDataGood.BROWSE_SEARCH_RESPONSE
    CATEGORY_RESPONSE_FILTERED = {
        **TestDataGood.BROWSE_SEARCH_RESPONSE,
        "total": 25,
        "itemSummaries": [TestDataGood.BROWSE_ITEM_IPHONE]
    }


class TestDataBad:
    """Invalid/edge case test data for resilience testing."""
    
    # ==============================================================================
    # Browse API Bad Data
    # ==============================================================================
    
    BROWSE_ITEM_IPHONE = {
        "itemId": "v1|999999999|0",
        "title": "",  # Empty title
        "price": {
            "value": "-999.99",  # Negative price
            "currency": "INVALID"  # Invalid currency
        },
        # Missing required itemWebUrl
        "seller": {
            "username": "",  # Empty username
            "feedbackPercentage": "150.0",  # Over 100%
            "feedbackScore": -100  # Negative score
        },
        "primaryCategoryId": "not-a-number",
        "itemLocation": {
            "country": "USA"  # Should be 2-char code
        }
    }
    
    BROWSE_ITEM_LAPTOP = {
        # Missing itemId entirely
        "title": "Laptop with Missing ID",
        "price": {
            "value": "not-a-number",
            "currency": "USD"
        },
        "itemWebUrl": "not-a-valid-url",
        "condition": "INVALID_CONDITION",
        "conditionId": "99999"  # Invalid condition ID
    }
    
    BROWSE_SEARCH_RESPONSE = {
        # Missing required fields
        "total": "not-a-number",
        "randomField": "unexpected"
        # Missing itemSummaries array
    }
    
    # ==============================================================================
    # Taxonomy API Bad Data
    # ==============================================================================
    
    CATEGORY_NODE_ELECTRONICS = {
        "category": {
            "categoryId": "",  # Empty ID
            "categoryName": "",  # Empty name
            "leafCategory": "not-a-boolean"
        },
        "categoryTreeNodeLevel": -1,  # Negative level
        "childCategoryTreeNodes": "not-an-array"
    }
    
    CATEGORY_SUGGESTIONS_RESPONSE = {
        "categorySuggestions": [
            {
                # Missing category object
                "relevancy": "INVALID_RELEVANCY"
            }
        ]
    }
    
    # ==============================================================================
    # Catalog API Bad Data
    # ==============================================================================
    
    PRODUCT_SUMMARY_IPHONE = {
        "epid": "",  # Empty EPID
        "title": None,  # Null title
        "image": {
            "imageUrl": "not-a-url"
        },
        "productWebUrl": "",
        "aspects": "not-an-array"  # Should be array
    }
    
    # ==============================================================================
    # Account API Bad Data
    # ==============================================================================
    
    SELLER_STANDARDS_RESPONSE = {
        "sellerLevel": "INVALID_LEVEL",
        "defectRate": {"value": -5.0},  # Negative rate
        "lateShipmentRate": {"value": 150.0},  # Over 100%
        "evaluationDate": "not-a-date",
        "metrics": []  # Empty metrics
    }
    
    
    # ==============================================================================
    # Marketing API Bad Data
    # ==============================================================================
    
    MERCHANDISED_PRODUCT_IPHONE = {
        "epid": "",  # Empty EPID
        "title": "",  # Empty title
        "image": {
            "imageUrl": "not-a-url"  # Invalid URL
        },
        "marketPriceDetails": [{
            "estimatedStartPrice": {
                "value": "-100",  # Negative price
                "currency": "XXX"  # Invalid currency
            },
            "estimatedEndPrice": {
                "value": "not-a-number",  # Invalid number
                "currency": "USD"
            }
        }],
        "averageRating": 10.5,  # Rating > 5
        "ratingCount": -50,  # Negative count
        "reviewCount": -10  # Negative count
    }
    
    # ==============================================================================
    # Shipping API Bad Data
    # ==============================================================================
    
    SHIPPING_COST_RESULT = {
        "itemId": "invalid-item-id",
        "shippingOptions": "not-an-array",  # Should be array
        "destinationPostalCode": "INVALID"
    }
    
    # ==============================================================================
    # Trending API Bad Data
    # ==============================================================================
    
    TRENDING_ITEM_POKEMON = {
        "itemId": "",  # Empty ID
        "title": None,  # Null title
        "watchCount": "not-a-number",
        "price": {
            "value": "-999",  # Negative price
            "currency": ""  # Empty currency
        },
        "trendingMetrics": []  # Should be object
    }


class TestDataError:
    """API error response data."""
    
    ERROR_INVALID_CATEGORY = {
        "errors": [{
            "errorId": 13013,
            "domain": "API_BROWSE",
            "category": "REQUEST",
            "message": "The 'category_ids' value is invalid.",
            "parameters": [
                {"name": "category_ids", "value": "99999999"}
            ]
        }]
    }
    
    ERROR_AUTHENTICATION = {
        "errors": [{
            "errorId": 1001,
            "domain": "OAuth",
            "category": "REQUEST",
            "message": "Invalid access token"
        }]
    }
    
    ERROR_NOT_FOUND = {
        "errors": [{
            "errorId": 11001,
            "domain": "ACCESS",
            "category": "APPLICATION",
            "message": "Resource not found"
        }]
    }
    
    ERROR_RATE_LIMIT = {
        "errors": [{
            "errorId": 1002,
            "domain": "ACCESS",
            "category": "APPLICATION",
            "message": "Rate limit exceeded"
        }]
    }
    
    ERROR_INTERNAL_SERVER = {
        "errors": [{
            "errorId": 2000,
            "domain": "SYSTEM",
            "category": "APPLICATION",
            "message": "Internal server error"
        }]
    }


class TestDataHelpers:
    """Helper methods for test data."""
    
    @staticmethod
    def get_search_response(items=None, total=None, use_bad_data=False):
        """Generate a search response with given items."""
        if use_bad_data:
            return TestDataBad.BROWSE_SEARCH_RESPONSE
            
        if items is None:
            items = [TestDataGood.BROWSE_ITEM_IPHONE]
        return {
            "href": "https://api.ebay.com/buy/browse/v1/item_summary/search",
            "total": total or len(items),
            "limit": 50,
            "offset": 0,
            "itemSummaries": items
        }


class TestDataReturnPolicy:
    """Test data for Return Policy API responses."""
    
    RETURN_POLICY_SIMPLE = {
        "returnPolicyId": "6196932000",
        "name": "30 Day Returns",
        "marketplaceId": "EBAY_US",
        "categoryTypes": [{
            "name": "ALL_EXCLUDING_MOTORS_VEHICLES",
            "default": True
        }],
        "returnsAccepted": True,
        "returnPeriod": {
            "value": 30,
            "unit": "DAY"
        },
        "returnShippingCostPayer": "BUYER",
        "refundMethod": "MONEY_BACK",
        "description": "Standard 30 day return policy"
    }
    
    RETURN_POLICY_WITH_INTL = {
        "returnPolicyId": "6196933000",
        "name": "Flexible Returns",
        "marketplaceId": "EBAY_US",
        "categoryTypes": [{
            "name": "ALL_EXCLUDING_MOTORS_VEHICLES",
            "default": True
        }],
        "returnsAccepted": True,
        "returnPeriod": {
            "value": 60,
            "unit": "DAY"
        },
        "returnShippingCostPayer": "SELLER",
        "refundMethod": "MONEY_BACK",
        "returnMethod": "EXCHANGE",
        "description": "Extended return period with free returns",
        "internationalOverride": {
            "returnsAccepted": True,
            "returnPeriod": {
                "value": 30,
                "unit": "DAY"
            },
            "returnShippingCostPayer": "BUYER"
        }
    }
    
    RETURN_POLICY_NO_RETURNS = {
        "returnPolicyId": "6196934000",
        "name": "No Returns",
        "marketplaceId": "EBAY_US",
        "categoryTypes": [{
            "name": "ALL_EXCLUDING_MOTORS_VEHICLES",
            "default": True
        }],
        "returnsAccepted": False,
        "description": "All sales final - no returns accepted"
    }
    
    GET_POLICIES_RESPONSE = {
        "returnPolicies": [
            RETURN_POLICY_SIMPLE,
            RETURN_POLICY_WITH_INTL,
            RETURN_POLICY_NO_RETURNS
        ],
        "total": 3,
        "limit": 20,
        "offset": 0
    }
    
    CREATE_POLICY_RESPONSE = {
        **RETURN_POLICY_SIMPLE,
        "returnPolicyId": "6196935000"
    }
    
    UPDATE_POLICY_RESPONSE = {
        **RETURN_POLICY_SIMPLE,
        "name": "Updated 30 Day Returns",
        "returnShippingCostPayer": "SELLER"
    }
    
    GET_BY_NAME_RESPONSE = RETURN_POLICY_SIMPLE
    

class TestDataPaymentPolicy:
    """Test data for Payment Policy API responses."""
    
    PAYMENT_POLICY_STANDARD = {
        "paymentPolicyId": "6196940000",
        "name": "Standard Payment",
        "marketplaceId": "EBAY_US",
        "categoryTypes": [{
            "name": "ALL_EXCLUDING_MOTORS_VEHICLES",
            "default": True
        }],
        "immediatePay": True,
        "description": "Standard immediate payment policy",
        "paymentInstrumentBrands": [
            "VISA",
            "MASTERCARD",
            "AMERICAN_EXPRESS",
            "DISCOVER"
        ]
    }
    
    PAYMENT_POLICY_MOTORS = {
        "paymentPolicyId": "6196941000",
        "name": "Motor Vehicle Payment",
        "marketplaceId": "EBAY_US",
        "categoryTypes": [{
            "name": "MOTORS_VEHICLES",
            "default": False
        }],
        "immediatePay": False,
        "description": "Payment policy for motor vehicles with deposit",
        "deposit": {
            "dueIn": 3,
            "amount": {
                "value": "500.00",
                "currency": "USD"
            },
            "paymentMethods": [{
                "paymentMethodType": "CASHIER_CHECK"
            }]
        },
        "fullPaymentDueIn": {
            "value": 7,
            "unit": "DAY"
        },
        "paymentMethods": [{
            "paymentMethodType": "CASH_ON_PICKUP"
        }, {
            "paymentMethodType": "CASHIER_CHECK"
        }]
    }
    
    PAYMENT_POLICY_WITH_OFFLINE = {
        "paymentPolicyId": "6196942000",
        "name": "Mixed Payment Methods",
        "marketplaceId": "EBAY_US",
        "categoryTypes": [{
            "name": "ALL_EXCLUDING_MOTORS_VEHICLES",
            "default": True
        }],
        "immediatePay": False,
        "description": "Policy allowing both online and offline payments",
        "paymentMethods": [{
            "paymentMethodType": "CASH_ON_PICKUP"
        }, {
            "paymentMethodType": "MONEY_ORDER"
        }],
        "paymentInstrumentBrands": [
            "VISA",
            "MASTERCARD"
        ]
    }
    
    GET_POLICIES_RESPONSE = {
        "paymentPolicies": [
            PAYMENT_POLICY_STANDARD,
            PAYMENT_POLICY_MOTORS,
            PAYMENT_POLICY_WITH_OFFLINE
        ],
        "total": 3,
        "limit": 20,
        "offset": 0
    }
    
    CREATE_POLICY_RESPONSE = {
        **PAYMENT_POLICY_STANDARD,
        "paymentPolicyId": "6196943000",
        "name": "New Payment Policy",
        "createdAt": "2025-01-17T10:00:00.000Z"
    }
    
    UPDATE_POLICY_RESPONSE = {
        **PAYMENT_POLICY_STANDARD,
        "name": "Updated Payment Policy",
        "immediatePay": False,
        "updatedAt": "2025-01-17T11:00:00.000Z"
    }
    
    GET_BY_NAME_RESPONSE = PAYMENT_POLICY_STANDARD


from typing import Optional
from tools.fulfillment_policy_api import (
    FulfillmentPolicyInput, CategoryType, TimeDuration, ShippingOption, 
    ShippingService, Amount, Region, RegionSet
)
from models.enums import (
    MarketplaceIdEnum, CategoryTypeEnum, ShippingCostTypeEnum,
    ShippingOptionTypeEnum, TimeDurationUnitEnum, CurrencyCodeEnum
)


class TestDataFulfillmentPolicy:
    """
    Test data for Fulfillment Policy API using Pydantic models.
    
    This class provides factory methods to create Pydantic models that can be:
    - Used to create policies via the API
    - Modified to reflect state changes (e.g., after creation/update)
    - Converted to expected API response format
    """
    
    # Storage for runtime data (e.g., generated policy IDs)
    _runtime_data = {}
    
    @classmethod
    def create_simple_policy(cls, name: str = "Standard Shipping") -> FulfillmentPolicyInput:
        """Create a simple fulfillment policy with minimal configuration."""
        return FulfillmentPolicyInput(
            name=name,
            marketplace_id=MarketplaceIdEnum.EBAY_US,
            category_types=[CategoryType(name=CategoryTypeEnum.ALL_EXCLUDING_MOTORS_VEHICLES)],
            handling_time=TimeDuration(value=1, unit=TimeDurationUnitEnum.DAY),
            description="Standard shipping policy with 1-day handling"
        )
    
    @classmethod
    def create_complex_policy(cls, name: str = "Premium Shipping") -> FulfillmentPolicyInput:
        """Create a complex fulfillment policy with multiple shipping options."""
        # Domestic shipping services
        domestic_standard = ShippingService(
            shipping_service_code="StandardShipping",
            shipping_carrier_code="USPS",
            shipping_cost=Amount(currency=CurrencyCodeEnum.USD, value="5.99"),
            additional_shipping_cost=Amount(currency=CurrencyCodeEnum.USD, value="2.99"),
            free_shipping=False,
            sort_order=1
        )
        
        domestic_expedited = ShippingService(
            shipping_service_code="ExpeditedShipping",
            shipping_carrier_code="UPS",
            shipping_cost=Amount(currency=CurrencyCodeEnum.USD, value="12.99"),
            free_shipping=False,
            sort_order=2
        )
        
        # International shipping service
        international_standard = ShippingService(
            shipping_service_code="InternationalStandardShipping",
            shipping_carrier_code="USPS",
            shipping_cost=Amount(currency=CurrencyCodeEnum.USD, value="19.99"),
            free_shipping=False,
            ship_to_locations=RegionSet(
                region_included=[
                    Region(region_name="Worldwide", region_type=None),
                ],
                region_excluded=[
                    Region(region_name="RU", region_type=None),  # Russia
                    Region(region_name="CN", region_type=None),  # China
                ]
            ),
            sort_order=1
        )
        
        # Shipping options
        domestic_option = ShippingOption(
            cost_type=ShippingCostTypeEnum.FLAT_RATE,
            option_type=ShippingOptionTypeEnum.DOMESTIC,
            shipping_services=[domestic_standard, domestic_expedited],
            package_handling_cost=Amount(currency=CurrencyCodeEnum.USD, value="1.99")
        )
        
        international_option = ShippingOption(
            cost_type=ShippingCostTypeEnum.FLAT_RATE,
            option_type=ShippingOptionTypeEnum.INTERNATIONAL,
            shipping_services=[international_standard]
        )
        
        return FulfillmentPolicyInput(
            name=name,
            marketplace_id=MarketplaceIdEnum.EBAY_US,
            category_types=[CategoryType(name=CategoryTypeEnum.ALL_EXCLUDING_MOTORS_VEHICLES)],
            handling_time=TimeDuration(value=2, unit=TimeDurationUnitEnum.DAY),
            description="Premium shipping with multiple options",
            shipping_options=[domestic_option, international_option],
            ship_to_locations=RegionSet(
                region_included=[Region(region_name="US", region_type=None)]
            ),
            local_pickup=True,
            global_shipping=True
        )
    
    @classmethod
    def create_local_pickup_policy(cls, name: str = "Local Pickup Only") -> FulfillmentPolicyInput:
        """Create a policy for local pickup only."""
        return FulfillmentPolicyInput(
            name=name,
            marketplace_id=MarketplaceIdEnum.EBAY_US,
            category_types=[CategoryType(name=CategoryTypeEnum.ALL_EXCLUDING_MOTORS_VEHICLES)],
            local_pickup=True,
            pickup_drop_off=True,
            description="Local pickup and drop-off only policy"
        )
    
    @classmethod
    def store_policy_id(cls, policy_name: str, policy_id: str):
        """Store a runtime policy ID for later use (e.g., cleanup)."""
        cls._runtime_data[policy_name] = policy_id
    
    @classmethod
    def get_policy_id(cls, policy_name: str) -> Optional[str]:
        """Retrieve a stored policy ID."""
        return cls._runtime_data.get(policy_name)
    
    @classmethod
    def clear_runtime_data(cls):
        """Clear all stored runtime data."""
        cls._runtime_data.clear()
    
    @classmethod
    def policy_to_api_response(cls, policy: FulfillmentPolicyInput, policy_id: str = "6197932000") -> dict:
        """Convert a Pydantic model to expected API response format."""
        response = {
            "fulfillmentPolicyId": policy_id,
            "name": policy.name,
            "marketplaceId": policy.marketplace_id.value,
            "categoryTypes": [
                {"name": cat.name.value, **({"default": cat.default} if cat.default is not None else {})}
                for cat in policy.category_types
            ]
        }
        
        if policy.description:
            response["description"] = policy.description
            
        if policy.handling_time:
            response["handlingTime"] = {
                "value": policy.handling_time.value,
                "unit": policy.handling_time.unit.value
            }
            
        if policy.shipping_options:
            response["shippingOptions"] = []
            for opt in policy.shipping_options:
                opt_data = {
                    "costType": opt.cost_type.value,
                    "optionType": opt.option_type.value
                }
                
                if opt.package_handling_cost:
                    opt_data["packageHandlingCost"] = {
                        "currency": opt.package_handling_cost.currency.value,
                        "value": opt.package_handling_cost.value
                    }
                
                if opt.shipping_services:
                    opt_data["shippingServices"] = []
                    for svc in opt.shipping_services:
                        svc_data = {"shippingServiceCode": svc.shipping_service_code}
                        
                        if svc.shipping_carrier_code:
                            svc_data["shippingCarrierCode"] = svc.shipping_carrier_code
                        if svc.shipping_cost:
                            svc_data["shippingCost"] = {
                                "currency": svc.shipping_cost.currency.value,
                                "value": svc.shipping_cost.value
                            }
                        if svc.additional_shipping_cost:
                            svc_data["additionalShippingCost"] = {
                                "currency": svc.additional_shipping_cost.currency.value,
                                "value": svc.additional_shipping_cost.value
                            }
                        if svc.free_shipping is not None:
                            svc_data["freeShipping"] = svc.free_shipping
                        if svc.sort_order is not None:
                            svc_data["sortOrder"] = svc.sort_order
                            
                        opt_data["shippingServices"].append(svc_data)
                
                response["shippingOptions"].append(opt_data)
        
        if policy.local_pickup is not None:
            response["localPickup"] = policy.local_pickup
        if policy.pickup_drop_off is not None:
            response["pickupDropOff"] = policy.pickup_drop_off
        if policy.freight_shipping is not None:
            response["freightShipping"] = policy.freight_shipping
        if policy.global_shipping is not None:
            response["globalShipping"] = policy.global_shipping
            
        return response
    
    # Static response data for mocking API responses
    FULFILLMENT_POLICY_SIMPLE = {
        "fulfillmentPolicyId": "6197932000",
        "name": "Standard Shipping",
        "marketplaceId": "EBAY_US",
        "categoryTypes": [{
            "name": "ALL_EXCLUDING_MOTORS_VEHICLES",
            "default": True
        }],
        "handlingTime": {
            "value": 1,
            "unit": "DAY"
        },
        "localPickup": False,
        "freightShipping": False,
        "globalShipping": False,
        "description": "Standard shipping policy with 1-day handling"
    }
    
    FULFILLMENT_POLICY_COMPLEX = {
        "fulfillmentPolicyId": "6197942000",
        "name": "Premium Shipping",
        "marketplaceId": "EBAY_US",
        "categoryTypes": [{
            "name": "ALL_EXCLUDING_MOTORS_VEHICLES",
            "default": True
        }],
        "handlingTime": {
            "value": 2,
            "unit": "DAY"
        },
        "description": "Premium shipping with multiple options",
        "shippingOptions": [{
            "costType": "FLAT_RATE",
            "optionType": "DOMESTIC",
            "shippingServices": [{
                "shippingServiceCode": "StandardShipping",
                "shippingCarrierCode": "USPS",
                "shippingCost": {
                    "currency": "USD",
                    "value": "5.99"
                },
                "additionalShippingCost": {
                    "currency": "USD",
                    "value": "2.99"
                },
                "freeShipping": False,
                "sortOrder": 1
            }, {
                "shippingServiceCode": "ExpeditedShipping",
                "shippingCarrierCode": "UPS",
                "shippingCost": {
                    "currency": "USD",
                    "value": "12.99"
                },
                "freeShipping": False,
                "sortOrder": 2
            }]
        }, {
            "costType": "FLAT_RATE",
            "optionType": "INTERNATIONAL",
            "shippingServices": [{
                "shippingServiceCode": "InternationalStandardShipping",
                "shippingCarrierCode": "USPS",
                "shippingCost": {
                    "currency": "USD",
                    "value": "19.99"
                },
                "freeShipping": False,
                "sortOrder": 1
            }]
        }],
        "localPickup": True,
        "pickupDropOff": False,
        "freightShipping": False,
        "globalShipping": True
    }
    
    FULFILLMENT_POLICY_LOCAL_PICKUP = {
        "fulfillmentPolicyId": "6197952000",
        "name": "Local Pickup Only",
        "marketplaceId": "EBAY_US",
        "categoryTypes": [{
            "name": "ALL_EXCLUDING_MOTORS_VEHICLES",
            "default": True
        }],
        "localPickup": True,
        "pickupDropOff": True,
        "freightShipping": False,
        "globalShipping": False,
        "description": "Local pickup and drop-off only policy"
    }
    
    GET_POLICIES_RESPONSE = {
        "fulfillmentPolicies": [
            FULFILLMENT_POLICY_SIMPLE,
            FULFILLMENT_POLICY_COMPLEX,
            FULFILLMENT_POLICY_LOCAL_PICKUP
        ],
        "total": 3,
        "limit": 20,
        "offset": 0
    }
    
    CREATE_POLICY_RESPONSE = {
        **FULFILLMENT_POLICY_SIMPLE,
        "fulfillmentPolicyId": "6197962000",
        "name": "New Fulfillment Policy",
        "createdAt": "2025-01-17T10:00:00.000Z"
    }
    
    UPDATE_POLICY_RESPONSE = {
        **FULFILLMENT_POLICY_SIMPLE,
        "name": "Updated Fulfillment Policy",
        "description": "Updated shipping policy description",
        "updatedAt": "2025-01-17T11:00:00.000Z"
    }
    
    GET_BY_NAME_RESPONSE = FULFILLMENT_POLICY_SIMPLE


class TestDataInventoryItem:
    """Test data for Inventory Item API responses."""
    
    INVENTORY_ITEM_SIMPLE = {
        "sku": "TEST-SKU-001",
        "locale": "en_US",
        "condition": "NEW",
        "availability": {
            "shipToLocationAvailability": {
                "quantity": 10
            }
        },
        "product": {
            "title": "Test Product",
            "description": "A test product for unit testing",
            "brand": "TestBrand",
            "mpn": "TEST-MPN-001",
            "imageUrls": [
                "https://example.com/image1.jpg",
                "https://example.com/image2.jpg"
            ]
        }
    }
    
    INVENTORY_ITEM_COMPLEX = {
        "sku": "TEST-SKU-002",
        "locale": "en_US",
        "condition": "LIKE_NEW",
        "conditionDescription": "Barely used, excellent condition",
        "availability": {
            "shipToLocationAvailability": {
                "quantity": 5,
                "allocationByFormat": {
                    "AUCTION": 2,
                    "FIXED_PRICE": 3
                }
            },
            "pickupAtLocationAvailability": [{
                "availabilityType": "IN_STOCK",
                "merchantLocationKey": "store_001"
            }]
        },
        "product": {
            "title": "Premium Test Product",
            "subtitle": "High-quality testing item",
            "description": "A premium test product with enhanced features for comprehensive testing",
            "brand": "PremiumBrand",
            "mpn": "PREM-MPN-002",
            "upc": ["123456789012"],
            "ean": ["1234567890123"],
            "imageUrls": [
                "https://example.com/premium1.jpg",
                "https://example.com/premium2.jpg",
                "https://example.com/premium3.jpg"
            ],
            "aspects": {
                "Color": ["Blue", "Green"],
                "Size": ["Medium"],
                "Material": ["Cotton"]
            }
        },
        "packageWeightAndSize": {
            "weight": {
                "value": "2.5",
                "unit": "POUND"
            },
            "dimensions": {
                "length": {
                    "value": "12.0",
                    "unit": "INCH"
                },
                "width": {
                    "value": "8.0",
                    "unit": "INCH"
                },
                "height": {
                    "value": "4.0",
                    "unit": "INCH"
                }
            },
            "packageType": "PACKAGE"
        }
    }
    
    GET_INVENTORY_ITEMS_RESPONSE = {
        "inventoryItems": [
            INVENTORY_ITEM_SIMPLE,
            INVENTORY_ITEM_COMPLEX
        ],
        "total": 2,
        "size": 1,
        "limit": 25,
        "offset": 0
    }
    
    BULK_CREATE_RESPONSE = {
        "responses": [
            {
                "sku": "TEST-SKU-001",
                "statusCode": 204,
                "locale": "en_US"
            },
            {
                "sku": "TEST-SKU-002", 
                "statusCode": 204,
                "locale": "en_US"
            }
        ]
    }
    
    BULK_GET_RESPONSE = {
        "responses": [
            {
                "sku": "TEST-SKU-001",
                "statusCode": 200,
                "inventoryItem": INVENTORY_ITEM_SIMPLE
            },
            {
                "sku": "TEST-SKU-002",
                "statusCode": 200,
                "inventoryItem": INVENTORY_ITEM_COMPLEX
            }
        ]
    }
    
    BULK_UPDATE_PRICE_QUANTITY_RESPONSE = {
        "responses": [
            {
                "sku": "TEST-SKU-001",
                "statusCode": 200,
                "locale": "en_US"
            },
            {
                "sku": "TEST-SKU-002",
                "statusCode": 200,
                "locale": "en_US"
            }
        ]
    }
    
