"""
Tests for Marketplace Filter Builder tool.
"""
import pytest
import json
from unittest.mock import AsyncMock

from tools.marketplace_insights_api import build_marketplace_filter
from tools.tests.test_helpers import assert_api_response_success


@pytest.mark.asyncio
async def test_build_marketplace_filter_price_condition():
    """Test building filter with price and condition."""
    mock_context = AsyncMock()
    
    result = await build_marketplace_filter.fn(
        ctx=mock_context,
        price_min=100,
        price_max=500,
        conditions=["New", "Used"]
    )
    
    data = assert_api_response_success(result)
    assert data["data"]["filter_count"] >= 3  # price, priceCurrency, conditionIds
    assert "price:[100..500]" in data["data"]["filter"]
    assert "priceCurrency:USD" in data["data"]["filter"]
    assert "conditionIds:{1000|3000}" in data["data"]["filter"]


@pytest.mark.asyncio
async def test_build_marketplace_filter_shipping():
    """Test building filter with shipping options."""
    mock_context = AsyncMock()
    
    result = await build_marketplace_filter.fn(
        ctx=mock_context,
        free_shipping=True,
        returns_accepted=True,
        item_location_country="US"
    )
    
    data = assert_api_response_success(result)
    assert "maxDeliveryCost:0" in data["data"]["filter"]
    assert "returnsAccepted:true" in data["data"]["filter"]
    assert "itemLocationCountry:US" in data["data"]["filter"]


@pytest.mark.asyncio
async def test_build_marketplace_filter_empty():
    """Test building filter with no parameters."""
    mock_context = AsyncMock()
    
    result = await build_marketplace_filter.fn(ctx=mock_context)
    
    data = assert_api_response_success(result)
    assert data["data"]["filter"] == ""
    assert data["data"]["filter_count"] == 0


@pytest.mark.asyncio
async def test_build_marketplace_filter_complex():
    """Test building complex filter with many options."""
    mock_context = AsyncMock()
    
    result = await build_marketplace_filter.fn(
        ctx=mock_context,
        price_min=200,
        price_max=1000,
        conditions=["1000"],
        buying_options=["FIXED_PRICE", "BEST_OFFER"],
        seller_account_types=["BUSINESS"],
        authenticity_guarantee=True
    )
    
    data = assert_api_response_success(result)
    filter_str = data["data"]["filter"]
    
    # Check all components are present
    assert "price:[200..1000]" in filter_str
    assert "buyingOptions:{FIXED_PRICE|BEST_OFFER}" in filter_str
    assert "sellerAccountTypes:{BUSINESS}" in filter_str
    assert "qualifiedPrograms:{AUTHENTICITY_GUARANTEE}" in filter_str