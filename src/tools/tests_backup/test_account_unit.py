"""Unit tests for Account API tools."""
import pytest
from tools.account_api import (
    _convert_rate_table,
    RateTableInput
)


class TestInputValidation:
    """Test input validation models."""
    
    def test_rate_table_input_valid(self):
        """Test valid rate table input."""
        input_data = RateTableInput(country_code="US")
        
        assert input_data.country_code == "US"
    
    def test_rate_table_input_invalid_code(self):
        """Test invalid country code."""
        with pytest.raises(ValueError, match="Country code must be 2 characters"):
            RateTableInput(country_code="USA")
    
    def test_rate_table_input_lowercase_conversion(self):
        """Test country code uppercase conversion."""
        input_data = RateTableInput(country_code="gb")
        
        assert input_data.country_code == "GB"


class TestDataConversion:
    """Test data conversion functions."""
    
    def test_convert_rate_table(self):
        """Test rate table conversion."""
        rate_table = {
            "rateTableId": "67890",
            "name": "Standard US Shipping",
            "description": "Standard shipping rates for US",
            "countryCode": "US",
            "locality": "DOMESTIC",
            "rateTableType": "SHIPPING",
            "shippingServices": [
                {
                    "shippingServiceCode": "USPSGround",
                    "shippingCarrierCode": "USPS"
                }
            ],
            "createdDate": "2024-01-01T00:00:00Z",
            "lastModifiedDate": "2024-01-01T00:00:00Z"
        }
        
        result = _convert_rate_table(rate_table)
        
        assert result["rate_table_id"] == "67890"
        assert result["name"] == "Standard US Shipping"
        assert result["description"] == "Standard shipping rates for US"
        assert result["country_code"] == "US"
        assert result["locality"] == "DOMESTIC"
        assert result["rate_table_type"] == "SHIPPING"
        assert len(result["shipping_services"]) == 1
        assert result["created_date"] == "2024-01-01T00:00:00Z"
        assert result["last_modified_date"] == "2024-01-01T00:00:00Z"