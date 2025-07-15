"""Tests for eBay Shopping API tools."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from data_types import ErrorCode
import json

from tools.shopping_api import (
    get_single_item,
    get_item_status,
    get_shipping_costs,
    get_multiple_items,
    find_products,
    get_user_profile,
    get_category_info
)


@pytest.fixture
def mock_context():
    """Create mock MCP context."""
    ctx = AsyncMock()
    ctx.info = AsyncMock()
    ctx.error = AsyncMock()
    ctx.debug = AsyncMock()
    ctx.warning = AsyncMock()
    ctx.report_progress = AsyncMock()
    
    # Mock server with config and logger
    ctx.server = MagicMock()
    ctx.server.config = MagicMock()
    ctx.server.logger = MagicMock()
    
    return ctx


@pytest.fixture
def mock_client(monkeypatch):
    """Mock EbayApiClient."""
    mock = MagicMock()
    mock.execute_with_retry = AsyncMock()
    mock.validate_pagination = MagicMock()
    
    def mock_init(*args, **kwargs):
        return mock
    
    monkeypatch.setattr("tools.shopping_api.EbayApiClient", mock_init)
    return mock


class TestGetSingleItem:
    """Tests for get_single_item tool."""
    
    @pytest.mark.asyncio
    async def test_get_single_item_basic(self, mock_context, mock_client):
        """Test basic item retrieval."""
        # Setup mock response
        mock_client.execute_with_retry.return_value = {
            "Item": {
                "ItemID": "123456789012",
                "Title": "Test Item",
                "CurrentPrice": {"value": "99.99", "_currencyID": "USD"},
                "ConditionID": "1000",
                "ConditionDisplayName": "New",
                "Quantity": 10,
                "QuantitySold": 2,
                "Seller": {
                    "UserID": "test_seller",
                    "FeedbackScore": "100",
                    "PositiveFeedbackPercent": "99.5",
                    "TopRatedSeller": True
                },
                "Location": "Los Angeles, CA",
                "Country": "US",
                "PostalCode": "90001",
                "ListingType": "FixedPriceItem",
                "ListingStatus": "Active",
                "StartTime": "2024-01-01T00:00:00.000Z",
                "EndTime": "2024-12-31T23:59:59.000Z",
                "ViewItemURLForNaturalSearch": "https://www.ebay.com/itm/123456789012",
                "GalleryURL": "https://i.ebayimg.com/images/test.jpg",
                "PictureURL": ["https://i.ebayimg.com/images/test1.jpg", "https://i.ebayimg.com/images/test2.jpg"],
                "PaymentMethods": ["PayPal", "CreditCard"],
                "ReturnPolicy": {
                    "ReturnsAccepted": "ReturnsAccepted",
                    "ReturnsWithin": "30 Days",
                    "ShippingCostPaidBy": "Buyer"
                }
            }
        }
        
        result = await get_single_item.fn("123456789012", ctx=mock_context)
        response = json.loads(result)
        
        assert response["status"] == "success"
        assert response["data"]["item_id"] == "123456789012"
        assert response["data"]["title"] == "Test Item"
        assert response["data"]["price"]["value"] == 99.99
        assert response["data"]["seller"]["top_rated"] is True
        assert response["data"]["quantity"]["available"] == 10
        assert response["data"]["quantity"]["sold"] == 2
        
        mock_context.info.assert_called()
        mock_context.report_progress.assert_called()
        mock_client.execute_with_retry.assert_called_once_with(
            "shopping",
            "GetSingleItem",
            {"ItemID": "123456789012"}
        )
    
    @pytest.mark.asyncio
    async def test_get_single_item_with_selector(self, mock_context, mock_client):
        """Test item retrieval with include selector."""
        mock_client.execute_with_retry.return_value = {
            "Item": {
                "ItemID": "123456789012",
                "Title": "Test Item",
                "CurrentPrice": {"value": "99.99", "_currencyID": "USD"},
                "Description": "<p>Full HTML description</p>",
                "ItemSpecifics": {
                    "NameValueList": [
                        {"Name": "Brand", "Value": ["TestBrand"]},
                        {"Name": "Model", "Value": ["TestModel"]}
                    ]
                }
            }
        }
        
        result = await get_single_item.fn(
            "123456789012",
            include_selector="Description,ItemSpecifics",
            ctx=mock_context
        )
        response = json.loads(result)
        
        assert response["status"] == "success"
        assert "description" in response["data"]
        assert "item_specifics" in response["data"]
        
        mock_client.execute_with_retry.assert_called_once_with(
            "shopping",
            "GetSingleItem",
            {"ItemID": "123456789012", "IncludeSelector": "Description,ItemSpecifics"}
        )
    
    @pytest.mark.asyncio
    async def test_get_single_item_error(self, mock_context, mock_client):
        """Test error handling."""
        mock_client.execute_with_retry.side_effect = Exception("API Error")
        
        result = await get_single_item.fn("123456789012", ctx=mock_context)
        response = json.loads(result)
        
        assert response["status"] == "error"
        assert response["error_code"] == ErrorCode.INTERNAL_ERROR.value
        mock_context.error.assert_called()


class TestGetItemStatus:
    """Tests for get_item_status tool."""
    
    @pytest.mark.asyncio
    async def test_get_item_status_available(self, mock_context, mock_client):
        """Test status check for available item."""
        mock_client.execute_with_retry.return_value = {
            "Item": {
                "ItemID": "123456789012",
                "Title": "Test Item",
                "ListingStatus": "Active",
                "Quantity": 10,
                "QuantitySold": 3,
                "CurrentPrice": {"value": "49.99", "_currencyID": "USD"},
                "EndTime": "2024-12-31T23:59:59.000Z",
                "BidCount": 0,
                "WatchCount": 15
            }
        }
        
        result = await get_item_status.fn("123456789012", ctx=mock_context)
        response = json.loads(result)
        
        assert response["status"] == "success"
        assert response["data"]["listing_status"] == "Active"
        assert response["data"]["quantity_available"] == 7
        assert response["data"]["is_available"] is True
        assert response["message"] == "Item is available"
    
    @pytest.mark.asyncio
    async def test_get_item_status_sold_out(self, mock_context, mock_client):
        """Test status check for sold out item."""
        mock_client.execute_with_retry.return_value = {
            "Item": {
                "ItemID": "123456789012",
                "Title": "Test Item",
                "ListingStatus": "Active",
                "Quantity": 10,
                "QuantitySold": 10,
                "CurrentPrice": {"value": "49.99", "_currencyID": "USD"}
            }
        }
        
        result = await get_item_status.fn("123456789012", ctx=mock_context)
        response = json.loads(result)
        
        assert response["status"] == "success"
        assert response["data"]["quantity_available"] == 0
        assert response["data"]["is_available"] is False
        assert response["message"] == "Item is not available"


class TestGetShippingCosts:
    """Tests for get_shipping_costs tool."""
    
    @pytest.mark.asyncio
    async def test_get_shipping_costs_domestic(self, mock_context, mock_client):
        """Test shipping cost calculation for domestic destination."""
        mock_client.execute_with_retry.return_value = {
            "ShippingDetails": {
                "ShippingServiceOptions": [
                    {
                        "ShippingServiceName": "USPS Priority Mail",
                        "ShippingServiceCost": {"value": "8.99", "_currencyID": "USD"},
                        "ShippingServicePriority": 1,
                        "EstimatedDeliveryTime": "2-3 business days"
                    },
                    {
                        "ShippingServiceName": "USPS Ground",
                        "ShippingServiceCost": {"value": "5.99", "_currencyID": "USD"},
                        "ShippingServicePriority": 2,
                        "EstimatedDeliveryTime": "5-7 business days"
                    }
                ],
                "InsuranceOption": "Optional",
                "InsuranceCost": {"value": "2.50", "_currencyID": "USD"}
            },
            "ShippingCostSummary": {
                "ShippingType": "Flat",
                "ListedShippingServiceCost": {"_currencyID": "USD"}
            }
        }
        
        result = await get_shipping_costs.fn(
            "123456789012",
            destination_country_code="US",
            destination_postal_code="90210",
            quantity=2,
            ctx=mock_context
        )
        response = json.loads(result)
        
        assert response["status"] == "success"
        assert len(response["data"]["domestic_shipping"]) == 2
        assert response["data"]["domestic_shipping"][0]["service_name"] == "USPS Priority Mail"
        assert response["data"]["domestic_shipping"][0]["cost"]["value"] == 8.99
        assert response["data"]["insurance_available"] is True
        assert response["data"]["insurance_cost"] == 2.5
    
    @pytest.mark.asyncio
    async def test_get_shipping_costs_international(self, mock_context, mock_client):
        """Test shipping cost calculation for international destination."""
        mock_client.execute_with_retry.return_value = {
            "ShippingDetails": {
                "InternationalShippingServiceOptions": [
                    {
                        "ShippingServiceName": "USPS Priority Mail International",
                        "ShippingServiceCost": {"value": "35.99", "_currencyID": "USD"},
                        "ShippingServicePriority": 1,
                        "ShipToLocation": ["GB", "DE", "FR"]
                    }
                ]
            },
            "ShippingCostSummary": {
                "ShippingType": "Calculated"
            }
        }
        
        result = await get_shipping_costs.fn(
            "123456789012",
            destination_country_code="GB",
            ctx=mock_context
        )
        response = json.loads(result)
        
        assert response["status"] == "success"
        assert len(response["data"]["international_shipping"]) == 1
        assert response["data"]["shipping_type"] == "Calculated"


class TestGetMultipleItems:
    """Tests for get_multiple_items tool."""
    
    @pytest.mark.asyncio
    async def test_get_multiple_items_success(self, mock_context, mock_client):
        """Test retrieving multiple items."""
        mock_client.execute_with_retry.return_value = {
            "Item": [
                {
                    "ItemID": "123456789012",
                    "Title": "Item 1",
                    "CurrentPrice": {"value": "99.99", "_currencyID": "USD"},
                    "Quantity": 10,
                    "QuantitySold": 2,
                    "ListingStatus": "Active"
                },
                {
                    "ItemID": "123456789013",
                    "Title": "Item 2",
                    "CurrentPrice": {"value": "149.99", "_currencyID": "USD"},
                    "Quantity": 5,
                    "QuantitySold": 5,
                    "ListingStatus": "Ended"
                }
            ]
        }
        
        result = await get_multiple_items.fn(
            ["123456789012", "123456789013", "123456789014"],
            ctx=mock_context
        )
        response = json.loads(result)
        
        assert response["status"] == "success"
        assert len(response["data"]["items"]) == 2
        assert response["data"]["summary"]["requested"] == 3
        assert response["data"]["summary"]["found"] == 2
        assert "123456789014" in response["data"]["summary"]["not_found"]
    
    @pytest.mark.asyncio
    async def test_get_multiple_items_validation_error(self, mock_context, mock_client):
        """Test validation error for too many items."""
        item_ids = [str(i) for i in range(25)]  # 25 items, exceeds limit
        
        result = await get_multiple_items.fn(item_ids, ctx=mock_context)
        response = json.loads(result)
        
        assert response["status"] == "error"
        assert response["error_code"] == ErrorCode.VALIDATION_ERROR.value
        assert "Maximum 20 items" in response["error_message"]


class TestFindProducts:
    """Tests for find_products tool."""
    
    @pytest.mark.asyncio
    async def test_find_products_by_keywords(self, mock_context, mock_client):
        """Test product search by keywords."""
        mock_client.execute_with_retry.return_value = {
            "Product": [
                {
                    "ProductID": {"Value": "EPID123456"},
                    "Title": "iPhone 15 Pro",
                    "DetailsURL": "https://www.ebay.com/p/EPID123456",
                    "StockPhotoURL": "https://i.ebayimg.com/images/stock.jpg",
                    "DisplayStockPhotos": True,
                    "ReviewCount": 150,
                    "ReviewDetails": {"AverageRating": "4.5"},
                    "MinPrice": {"value": "999.00", "_currencyID": "USD"},
                    "ItemCount": 250,
                    "ItemSpecifics": {
                        "NameValueList": [
                            {"Name": "Brand", "Value": ["Apple"]},
                            {"Name": "Storage", "Value": ["128GB", "256GB", "512GB"]}
                        ]
                    }
                }
            ],
            "TotalProducts": 5
        }
        
        result = await find_products.fn(
            query_keywords="iPhone 15 Pro",
            ctx=mock_context
        )
        response = json.loads(result)
        
        assert response["status"] == "success"
        assert len(response["data"]["products"]) == 1
        assert response["data"]["products"][0]["product_id"] == "EPID123456"
        assert response["data"]["products"][0]["review_info"]["count"] == 150
        assert response["data"]["products"][0]["item_specifics"]["Brand"] == ["Apple"]
        assert response["data"]["summary"]["total_products"] == 5
    
    @pytest.mark.asyncio
    async def test_find_products_validation_error(self, mock_context, mock_client):
        """Test validation error when no search criteria provided."""
        result = await find_products.fn(ctx=mock_context)
        response = json.loads(result)
        
        assert response["status"] == "error"
        assert response["error_code"] == ErrorCode.VALIDATION_ERROR.value


class TestDeprecatedFunctions:
    """Tests for deprecated functions."""
    
    @pytest.mark.asyncio
    async def test_get_user_profile_deprecated(self, mock_context):
        """Test deprecated get_user_profile function."""
        result = await get_user_profile.fn(ctx=mock_context)
        response = json.loads(result)
        
        assert response["status"] == "error"
        assert response["error_code"] == ErrorCode.NOT_IMPLEMENTED.value
        assert "deprecated" in response["error_message"]
    
    @pytest.mark.asyncio
    async def test_get_category_info_deprecated(self, mock_context):
        """Test deprecated get_category_info function."""
        result = await get_category_info.fn(ctx=mock_context)
        response = json.loads(result)
        
        assert response["status"] == "error"
        assert response["error_code"] == ErrorCode.NOT_IMPLEMENTED.value
        assert "deprecated" in response["error_message"]