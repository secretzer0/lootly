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
    # Inventory API Test Data
    # ==============================================================================
    
    INVENTORY_ITEM_IPHONE = {
        "sku": "IPHONE-15-PRO-256-TITANIUM",
        "product": {
            "title": "Apple iPhone 15 Pro - 256GB - Natural Titanium",
            "description": "Brand new iPhone 15 Pro with advanced camera system",
            "brand": "Apple",
            "mpn": "MTQA3LL/A",
            "epid": "249325755",
            "imageUrls": [
                "https://i.ebayimg.com/images/g/123/s-l1600.jpg"
            ],
            "aspects": {
                "Brand": ["Apple"],
                "Model": ["iPhone 15 Pro"],
                "Storage Capacity": ["256 GB"],
                "Color": ["Natural Titanium"]
            }
        },
        "condition": "NEW",
        "availability": {
            "shipToLocationAvailability": {
                "quantity": 10
            }
        },
        "location": {
            "address": {
                "city": "San Jose",
                "stateOrProvince": "CA",
                "postalCode": "95110",
                "country": "US"
            }
        },
        "pricing": {
            "price": {
                "value": "999.99",
                "currency": "USD"
            }
        }
    }
    
    OFFER_FIXED_PRICE = {
        "offerId": "5123456789",
        "sku": "IPHONE-15-PRO-256-TITANIUM",
        "marketplaceId": "EBAY_US",
        "format": "FIXED_PRICE",
        "pricingSummary": {
            "price": {
                "value": "999.99",
                "currency": "USD"
            }
        },
        "listingDescription": "Brand new iPhone 15 Pro with advanced camera system",
        "categoryId": "9355",
        "merchantLocationKey": "warehouse-1",
        "listingDuration": "GTC",
        "status": "PUBLISHED",
        "listingPolicies": {
            "paymentPolicyId": "payment_policy_1",
            "fulfillmentPolicyId": "shipping_policy_1",
            "returnPolicyId": "return_policy_1"
        }
    }
    
    # ==============================================================================
    # Marketing API Test Data
    # ==============================================================================
    
    MARKETING_PRODUCT_IPHONE = {
        "productId": "EPID249325755",
        "title": "Apple iPhone 15 Pro - 256GB",
        "priceRange": {
            "minPrice": {
                "value": "899.99",
                "currency": "USD"
            },
            "maxPrice": {
                "value": "1099.99",
                "currency": "USD"
            }
        },
        "reviewCount": 1250,
        "averageRating": 4.8,
        "imageUrl": "https://i.ebayimg.com/images/g/marketing/s-l1600.jpg",
        "productUrl": "https://www.ebay.com/itm/marketing/123456789",
        "categoryId": "9355",
        "salesRank": 1,
        "availableQuantity": 500
    }
    
    MERCHANDISED_PRODUCTS_RESPONSE = {
        "merchandisedProducts": [MARKETING_PRODUCT_IPHONE],
        "marketplaceId": "EBAY_US",
        "metricType": "BEST_SELLING",
        "categoryId": "9355",
        "total": 1
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
    # Inventory API Bad Data
    # ==============================================================================
    
    INVENTORY_ITEM_IPHONE = {
        "sku": "",  # Empty SKU
        "product": {
            "title": "",  # Empty title
            "imageUrls": ["not-a-url"],
            "aspects": []  # Empty aspects
        },
        "condition": "INVALID",
        "availability": {
            "shipToLocationAvailability": {
                "quantity": -10  # Negative quantity
            }
        }
    }
    
    OFFER_FIXED_PRICE = {
        "offerId": "",
        "sku": "INVALID@SKU!",  # Invalid characters
        "format": "INVALID_FORMAT",
        "pricingSummary": {
            "price": {
                "value": "0.00",  # Zero price
                "currency": "XXX"  # Invalid currency
            }
        },
        "categoryId": "",  # Empty category
        "status": "INVALID_STATUS"
    }
    
    # ==============================================================================
    # Marketing API Bad Data
    # ==============================================================================
    
    MARKETING_PRODUCT_IPHONE = {
        "productId": "",  # Empty ID
        "title": "",  # Empty title
        "priceRange": {
            "minPrice": {
                "value": "-100",  # Negative price
                "currency": "XXX"  # Invalid currency
            },
            "maxPrice": {
                "value": "not-a-number",  # Invalid number
                "currency": "USD"
            }
        },
        "reviewCount": -50,  # Negative count
        "averageRating": 10.5,  # Rating > 5
        "imageUrl": "not-a-url",
        "productUrl": "",
        "categoryId": "invalid-category"
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
    
    @staticmethod
    def get_inventory_response(items=None, use_bad_data=False):
        """Generate an inventory response with given items."""
        if use_bad_data:
            return {
                "href": "/sell/inventory/v1/inventory_item",
                "inventoryItems": "not-an-array"  # Bad data
            }
            
        if items is None:
            items = [TestDataGood.INVENTORY_ITEM_IPHONE]
        return {
            "href": "/sell/inventory/v1/inventory_item",
            "total": len(items),
            "size": len(items),
            "inventoryItems": items
        }