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
    
