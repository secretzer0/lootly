"""Tests for eBay Trading API tools."""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from fastmcp import Context

from tools.trading_api import (
    create_listing,
    revise_listing,
    end_listing,
    get_my_ebay_selling,
    get_user_info,
    CreateListingInput,
    ReviseListingInput
)
from data_types import ErrorCode, ResponseStatus
import json


@pytest.fixture
def mock_context():
    """Create a mock MCP context."""
    ctx = Mock(spec=Context)
    ctx.info = AsyncMock()
    ctx.error = AsyncMock()
    ctx.warning = AsyncMock()
    ctx.debug = AsyncMock()
    ctx.report_progress = AsyncMock()
    
    # Mock server with config and logger
    ctx.server = Mock()
    ctx.server.config = Mock()
    ctx.server.config.domain = "sandbox.ebay.com"
    ctx.server.logger = Mock()
    ctx.server.logger.tool_failed = Mock()
    
    return ctx


@pytest.fixture
def mock_ebay_client():
    """Create a mock eBay API client."""
    with patch('tools.trading_api.EbayApiClient') as mock_client_class:
        mock_client = Mock()
        mock_client.execute_with_retry = AsyncMock()
        mock_client.validate_pagination = Mock()
        mock_client_class.return_value = mock_client
        yield mock_client


class TestCreateListing:
    """Tests for create_listing tool."""
    
    @pytest.mark.asyncio
    async def test_create_listing_success(self, mock_context, mock_ebay_client):
        """Test successful listing creation."""
        # Mock API response
        mock_ebay_client.execute_with_retry.return_value = {
            "ItemID": ["123456789"],
            "Fees": {
                "Fee": [
                    {"Name": "InsertionFee", "Fee": {"value": "0.35"}},
                    {"Name": "FinalValueFee", "Fee": {"value": "0.00"}}
                ]
            }
        }
        
        # Execute
        result = await create_listing.fn(
            title="Test Item",
            description="This is a test item description",
            category_id="12345",
            start_price=19.99,
            condition_id="1000",
            shipping_service="USPSPriority",
            shipping_cost=5.99,
            ctx=mock_context
        )
        
        # Parse result
        response = json.loads(result)
        
        # Assertions
        assert response["status"] == ResponseStatus.SUCCESS.value
        assert response["data"]["item_id"] == "123456789"
        assert response["data"]["title"] == "Test Item"
        assert response["data"]["fees"]["total"] == 0.35
        assert len(response["data"]["fees"]["details"]) == 1
        assert "listing_url" in response["data"]
        
        # Verify API call
        mock_ebay_client.execute_with_retry.assert_called_once()
        call_args = mock_ebay_client.execute_with_retry.call_args
        assert call_args[0][0] == "trading"
        assert call_args[0][1] == "AddItem"
        assert call_args[0][2]["Item"]["Title"] == "Test Item"
        
        # Verify context calls
        mock_context.info.assert_called()
        mock_context.report_progress.assert_called()
    
    @pytest.mark.asyncio
    async def test_create_listing_with_buy_it_now(self, mock_context, mock_ebay_client):
        """Test creating listing with Buy It Now price."""
        mock_ebay_client.execute_with_retry.return_value = {
            "ItemID": ["123456789"],
            "Fees": {"Fee": []}
        }
        
        result = await create_listing.fn(
            title="Test Item",
            description="Description",
            category_id="12345",
            start_price=9.99,
            buy_it_now_price=29.99,
            condition_id="1000",
            shipping_service="USPSPriority",
            shipping_cost=0,
            ctx=mock_context
        )
        
        # Verify BIN price was included
        call_args = mock_ebay_client.execute_with_retry.call_args
        item_data = call_args[0][2]["Item"]
        assert item_data["BuyItNowPrice"] == "29.99"
        assert item_data["ListingType"] == "Chinese"
    
    @pytest.mark.asyncio
    async def test_create_listing_with_pictures(self, mock_context, mock_ebay_client):
        """Test creating listing with pictures."""
        mock_ebay_client.execute_with_retry.return_value = {
            "ItemID": ["123456789"],
            "Fees": {"Fee": []}
        }
        
        picture_urls = [
            "https://example.com/pic1.jpg",
            "https://example.com/pic2.jpg"
        ]
        
        result = await create_listing.fn(
            title="Test Item",
            description="Description",
            category_id="12345",
            start_price=19.99,
            condition_id="1000",
            shipping_service="USPSPriority",
            shipping_cost=5.99,
            picture_urls=picture_urls,
            ctx=mock_context
        )
        
        # Verify pictures were included
        call_args = mock_ebay_client.execute_with_retry.call_args
        item_data = call_args[0][2]["Item"]
        assert item_data["PictureDetails"]["PictureURL"] == picture_urls
    
    @pytest.mark.asyncio
    async def test_create_listing_validation_error(self, mock_context, mock_ebay_client):
        """Test listing creation with invalid parameters."""
        result = await create_listing.fn(
            title="",  # Empty title
            description="Description",
            category_id="12345",
            start_price=19.99,
            condition_id="1000",
            shipping_service="USPSPriority",
            shipping_cost=5.99,
            ctx=mock_context
        )
        
        response = json.loads(result)
        assert response["status"] == ResponseStatus.ERROR.value
        assert response["error_code"] == ErrorCode.VALIDATION_ERROR.value
        mock_context.error.assert_called()
    
    @pytest.mark.asyncio
    async def test_create_listing_api_error(self, mock_context, mock_ebay_client):
        """Test listing creation with API error."""
        mock_ebay_client.execute_with_retry.side_effect = Exception("API Error")
        
        result = await create_listing.fn(
            title="Test Item",
            description="Description",
            category_id="12345",
            start_price=19.99,
            condition_id="1000",
            shipping_service="USPSPriority",
            shipping_cost=5.99,
            ctx=mock_context
        )
        
        response = json.loads(result)
        assert response["status"] == ResponseStatus.ERROR.value
        assert response["error_code"] == ErrorCode.INTERNAL_ERROR.value
        assert "API Error" in response["error_message"]
        mock_context.server.logger.tool_failed.assert_called()


class TestReviseListing:
    """Tests for revise_listing tool."""
    
    @pytest.mark.asyncio
    async def test_revise_listing_success(self, mock_context, mock_ebay_client):
        """Test successful listing revision."""
        mock_ebay_client.execute_with_retry.return_value = {}
        
        result = await revise_listing.fn(
            item_id="123456789",
            title="Updated Title",
            price=24.99,
            ctx=mock_context
        )
        
        response = json.loads(result)
        assert response["status"] == ResponseStatus.SUCCESS.value
        assert response["data"]["item_id"] == "123456789"
        assert "title" in response["data"]["revised_fields"]
        assert "price" in response["data"]["revised_fields"]
        
        # Verify API call
        call_args = mock_ebay_client.execute_with_retry.call_args
        assert call_args[0][0] == "trading"
        assert call_args[0][1] == "ReviseItem"
        revision_data = call_args[0][2]["Item"]
        assert revision_data["ItemID"] == "123456789"
        assert revision_data["Title"] == "Updated Title"
        assert revision_data["StartPrice"] == "24.99"
    
    @pytest.mark.asyncio
    async def test_revise_listing_no_fields(self, mock_context, mock_ebay_client):
        """Test revision with no fields to update."""
        result = await revise_listing.fn(
            item_id="123456789",
            ctx=mock_context
        )
        
        response = json.loads(result)
        assert response["status"] == ResponseStatus.ERROR.value
        assert response["error_code"] == ErrorCode.VALIDATION_ERROR.value
        assert "at least one field" in response["error_message"].lower()
    
    @pytest.mark.asyncio
    async def test_revise_listing_all_fields(self, mock_context, mock_ebay_client):
        """Test revision with all fields."""
        mock_ebay_client.execute_with_retry.return_value = {}
        
        result = await revise_listing.fn(
            item_id="123456789",
            title="New Title",
            description="New Description",
            price=29.99,
            quantity=10,
            shipping_cost=7.99,
            picture_urls=["https://example.com/new.jpg"],
            ctx=mock_context
        )
        
        response = json.loads(result)
        assert response["status"] == ResponseStatus.SUCCESS.value
        assert len(response["data"]["revised_fields"]) == 6


class TestEndListing:
    """Tests for end_listing tool."""
    
    @pytest.mark.asyncio
    async def test_end_listing_success(self, mock_context, mock_ebay_client):
        """Test successful listing ending."""
        end_time = datetime.now().isoformat()
        mock_ebay_client.execute_with_retry.return_value = {
            "EndTime": [end_time]
        }
        
        result = await end_listing.fn(
            item_id="123456789",
            reason="NotAvailable",
            ctx=mock_context
        )
        
        response = json.loads(result)
        assert response["status"] == ResponseStatus.SUCCESS.value
        assert response["data"]["item_id"] == "123456789"
        assert response["data"]["reason"] == "NotAvailable"
        assert response["data"]["end_time"] == end_time
        
        # Verify API call
        call_args = mock_ebay_client.execute_with_retry.call_args
        assert call_args[0][0] == "trading"
        assert call_args[0][1] == "EndItem"
        assert call_args[0][2]["ItemID"] == "123456789"
        assert call_args[0][2]["EndingReason"] == "NotAvailable"
    
    @pytest.mark.asyncio
    async def test_end_listing_invalid_reason(self, mock_context, mock_ebay_client):
        """Test ending listing with invalid reason."""
        result = await end_listing.fn(
            item_id="123456789",
            reason="InvalidReason",
            ctx=mock_context
        )
        
        response = json.loads(result)
        assert response["status"] == ResponseStatus.ERROR.value
        assert response["error_code"] == ErrorCode.VALIDATION_ERROR.value
        assert "Invalid reason" in response["error_message"]


class TestGetMyEbaySelling:
    """Tests for get_my_ebay_selling tool."""
    
    @pytest.mark.asyncio
    async def test_get_active_listings_success(self, mock_context, mock_ebay_client):
        """Test getting active listings."""
        mock_ebay_client.execute_with_retry.return_value = {
            "ActiveList": {
                "ItemArray": {
                    "Item": [
                        {
                            "ItemID": "123456789",
                            "Title": "Test Item 1",
                            "Quantity": "5",
                            "SellingStatus": {
                                "CurrentPrice": {"value": "19.99", "_currencyId": "USD"},
                                "QuantitySold": "2"
                            },
                            "ListingType": "FixedPriceItem",
                            "TimeLeft": "P2DT3H15M",
                            "WatchCount": "10",
                            "HitCount": "50",
                            "ListingDetails": {
                                "ViewItemURL": "https://www.ebay.com/itm/123456789",
                                "StartTime": "2024-01-01T00:00:00.000Z",
                                "EndTime": "2024-01-08T00:00:00.000Z"
                            }
                        }
                    ]
                },
                "PaginationResult": {
                    "TotalNumberOfPages": "1",
                    "TotalNumberOfEntries": "1"
                }
            }
        }
        
        result = await get_my_ebay_selling.fn(
            listing_type="Active",
            page_number=1,
            page_size=50,
            ctx=mock_context
        )
        
        response = json.loads(result)
        assert response["status"] == ResponseStatus.SUCCESS.value
        assert len(response["data"]["listings"]) == 1
        
        listing = response["data"]["listings"][0]
        assert listing["item_id"] == "123456789"
        assert listing["title"] == "Test Item 1"
        assert listing["current_price"] == 19.99
        assert listing["quantity"]["available"] == 3
        assert listing["quantity"]["sold"] == 2
        assert listing["watchers"] == 10
        
        assert response["data"]["summary"]["total_listings"] == 1
        assert response["data"]["summary"]["total_value"] == 59.97  # 3 * 19.99
    
    @pytest.mark.asyncio
    async def test_get_sold_listings_success(self, mock_context, mock_ebay_client):
        """Test getting sold listings."""
        mock_ebay_client.execute_with_retry.return_value = {
            "SoldList": {
                "ItemArray": {
                    "Item": {  # Single item (not array)
                        "ItemID": "987654321",
                        "Title": "Sold Item",
                        "Quantity": "1",
                        "SellingStatus": {
                            "CurrentPrice": {"value": "29.99"},
                            "QuantitySold": "1",
                            "HighBidder": {"UserID": "buyer123"}
                        }
                    }
                },
                "PaginationResult": {
                    "TotalNumberOfPages": "1",
                    "TotalNumberOfEntries": "1"
                }
            }
        }
        
        result = await get_my_ebay_selling.fn(
            listing_type="Sold",
            ctx=mock_context
        )
        
        response = json.loads(result)
        assert response["status"] == ResponseStatus.SUCCESS.value
        assert len(response["data"]["listings"]) == 1
        assert response["data"]["listings"][0]["buyer_id"] == "buyer123"
        assert response["data"]["summary"]["total_value"] == 29.99
    
    @pytest.mark.asyncio
    async def test_get_my_ebay_selling_invalid_type(self, mock_context, mock_ebay_client):
        """Test with invalid listing type."""
        result = await get_my_ebay_selling.fn(
            listing_type="InvalidType",
            ctx=mock_context
        )
        
        response = json.loads(result)
        assert response["status"] == ResponseStatus.ERROR.value
        assert response["error_code"] == ErrorCode.VALIDATION_ERROR.value


class TestGetUserInfo:
    """Tests for get_user_info tool."""
    
    @pytest.mark.asyncio
    async def test_get_user_info_authenticated(self, mock_context, mock_ebay_client):
        """Test getting authenticated user info."""
        mock_ebay_client.execute_with_retry.return_value = {
            "User": {
                "UserID": "testuser123",
                "Email": "test@example.com",
                "RegistrationDate": "2020-01-01T00:00:00.000Z",
                "Status": "Confirmed",
                "Site": "US",
                "FeedbackScore": "150",
                "PositiveFeedbackPercent": "99.5",
                "FeedbackRatingStar": "Yellow",
                "UniquePositiveFeedbackCount": "145",
                "UniqueNegativeFeedbackCount": "1",
                "UserIDVerified": True,
                "PayPalAccountStatus": "Verified",
                "SellerInfo": {
                    "CheckoutEnabled": True,
                    "StoreOwner": True,
                    "StoreURL": "https://stores.ebay.com/teststore",
                    "SellerLevel": "PowerSeller",
                    "TopRatedSeller": True
                }
            }
        }
        
        result = await get_user_info.fn(ctx=mock_context)
        
        response = json.loads(result)
        assert response["status"] == ResponseStatus.SUCCESS.value
        
        user_data = response["data"]
        assert user_data["user_id"] == "testuser123"
        assert user_data["email"] == "test@example.com"
        assert user_data["feedback"]["score"] == 150
        assert user_data["feedback"]["positive_percentage"] == 99.5
        assert user_data["seller_info"]["top_rated_seller"] is True
        assert user_data["verified"]["paypal"] is True
        
        # Verify API call
        call_args = mock_ebay_client.execute_with_retry.call_args
        assert call_args[0][0] == "trading"
        assert call_args[0][1] == "GetUser"
        assert "UserID" not in call_args[0][2]  # No user ID for authenticated user
    
    @pytest.mark.asyncio
    async def test_get_user_info_specific_user(self, mock_context, mock_ebay_client):
        """Test getting specific user info."""
        mock_ebay_client.execute_with_retry.return_value = {
            "User": {
                "UserID": "otheruser456",
                "FeedbackScore": "50",
                "SellerInfo": {}
            }
        }
        
        result = await get_user_info.fn(user_id="otheruser456", ctx=mock_context)
        
        response = json.loads(result)
        assert response["status"] == ResponseStatus.SUCCESS.value
        assert response["data"]["user_id"] == "otheruser456"
        
        # Verify API call included user ID
        call_args = mock_ebay_client.execute_with_retry.call_args
        assert call_args[0][2]["UserID"] == "otheruser456"


class TestInputValidation:
    """Tests for input validation models."""
    
    def test_create_listing_input_validation(self):
        """Test CreateListingInput validation."""
        # Valid input
        valid_input = CreateListingInput(
            title="Test Item",
            description="Test description",
            category_id="12345",
            start_price=19.99,
            condition_id="1000",
            shipping_service="USPSPriority",
            shipping_cost=5.99
        )
        assert valid_input.title == "Test Item"
        
        # Invalid duration
        with pytest.raises(ValueError) as exc_info:
            CreateListingInput(
                title="Test",
                description="Description",
                category_id="12345",
                start_price=19.99,
                condition_id="1000",
                shipping_service="USPSPriority",
                shipping_cost=5.99,
                duration="InvalidDuration"
            )
        assert "Duration must be one of" in str(exc_info.value)
        
        # Too many pictures
        with pytest.raises(ValueError) as exc_info:
            CreateListingInput(
                title="Test",
                description="Description",
                category_id="12345",
                start_price=19.99,
                condition_id="1000",
                shipping_service="USPSPriority",
                shipping_cost=5.99,
                picture_urls=[f"pic{i}.jpg" for i in range(13)]
            )
        assert "Maximum 12 pictures" in str(exc_info.value)
    
    def test_revise_listing_input_validation(self):
        """Test ReviseListingInput validation."""
        # Valid input with some fields
        valid_input = ReviseListingInput(
            item_id="123456789",
            title="New Title",
            price=29.99
        )
        assert valid_input.item_id == "123456789"
        assert valid_input.title == "New Title"
        assert valid_input.description is None
        
        # All fields
        full_input = ReviseListingInput(
            item_id="123456789",
            title="New Title",
            description="New Description",
            price=29.99,
            quantity=10,
            shipping_cost=7.99,
            picture_urls=["pic1.jpg"]
        )
        assert full_input.quantity == 10


@pytest.mark.asyncio
async def test_integration_flow(mock_context, mock_ebay_client):
    """Test a complete flow: create, revise, and end listing."""
    # Step 1: Create listing
    mock_ebay_client.execute_with_retry.return_value = {
        "ItemID": ["123456789"],
        "Fees": {"Fee": []}
    }
    
    create_result = await create_listing.fn(
        title="Integration Test Item",
        description="Testing complete flow",
        category_id="12345",
        start_price=19.99,
        condition_id="1000",
        shipping_service="USPSPriority",
        shipping_cost=5.99,
        ctx=mock_context
    )
    
    create_response = json.loads(create_result)
    assert create_response["status"] == ResponseStatus.SUCCESS.value
    item_id = create_response["data"]["item_id"]
    
    # Step 2: Revise listing
    mock_ebay_client.execute_with_retry.return_value = {}
    
    revise_result = await revise_listing.fn(
        item_id=item_id,
        price=24.99,
        ctx=mock_context
    )
    
    revise_response = json.loads(revise_result)
    assert revise_response["status"] == ResponseStatus.SUCCESS.value
    
    # Step 3: End listing
    mock_ebay_client.execute_with_retry.return_value = {
        "EndTime": [datetime.now().isoformat()]
    }
    
    end_result = await end_listing.fn(
        item_id=item_id,
        reason="NotAvailable",
        ctx=mock_context
    )
    
    end_response = json.loads(end_result)
    assert end_response["status"] == ResponseStatus.SUCCESS.value
    assert end_response["data"]["item_id"] == item_id