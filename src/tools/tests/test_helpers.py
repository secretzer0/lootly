"""
Test helper functions for validating data structures and types.

These helpers enable the same test to work with both mock data (unit tests)
and real API responses (integration tests) by validating structure, not values.
"""
from typing import Any, Dict, Optional, Type, Union
from decimal import Decimal
from datetime import datetime
import re


class FieldValidator:
    """Validators for common field patterns."""
    
    @staticmethod
    def is_valid_price(value: Any) -> bool:
        """Validate price field (must be positive number)."""
        if value is None:
            return False
        try:
            num = float(value) if not isinstance(value, (int, float, Decimal)) else value
            return num >= 0
        except (TypeError, ValueError):
            return False
    
    @staticmethod
    def is_valid_percentage(value: Any) -> bool:
        """Validate percentage field (0-100)."""
        if value is None:
            return False
        try:
            num = float(value) if not isinstance(value, (int, float, Decimal)) else value
            return 0 <= num <= 100
        except (TypeError, ValueError):
            return False
    
    @staticmethod
    def is_valid_url(value: Any) -> bool:
        """Validate URL field."""
        if not isinstance(value, str):
            return False
        return value.startswith(('http://', 'https://'))
    
    @staticmethod
    def is_valid_email(value: Any) -> bool:
        """Validate email field."""
        if not isinstance(value, str):
            return False
        return '@' in value and '.' in value.split('@')[1]
    
    @staticmethod
    def is_valid_ebay_item_id(value: Any) -> bool:
        """Validate eBay item ID format (v1|number|number)."""
        if not isinstance(value, str):
            return False
        return bool(re.match(r'^v\d+\|\d+\|\d+$', value))
    
    @staticmethod
    def is_valid_datetime(value: Any) -> bool:
        """Validate datetime field."""
        if isinstance(value, datetime):
            return True
        if isinstance(value, str):
            try:
                # Try parsing ISO format
                datetime.fromisoformat(value.replace('Z', '+00:00'))
                return True
            except ValueError:
                return False
        return False
    
    @staticmethod
    def is_non_empty_string(value: Any) -> bool:
        """Validate non-empty string."""
        return isinstance(value, str) and len(value.strip()) > 0
    
    @staticmethod
    def is_positive_integer(value: Any) -> bool:
        """Validate positive integer."""
        return isinstance(value, int) and value > 0


def validate_field(
    obj: Dict[str, Any], 
    field_path: str, 
    expected_type: Type,
    required: bool = True,
    validator: Optional[callable] = None,
    allow_none: bool = False
) -> None:
    """
    Validate a field in an object.
    
    Args:
        obj: Object to validate
        field_path: Dot-separated path to field (e.g., "price.value")
        expected_type: Expected type of the field
        required: Whether field must be present
        validator: Optional validation function
        allow_none: Whether None is acceptable
        
    Raises:
        AssertionError: If validation fails
    """
    # Navigate to the field
    current = obj
    parts = field_path.split('.')
    
    for i, part in enumerate(parts):
        if current is None:
            if allow_none or not required:
                return
            raise AssertionError(f"Field '{'.'.join(parts[:i])}' is None but contains required field '{part}'")
            
        if isinstance(current, dict):
            if part not in current:
                if not required:
                    return
                raise AssertionError(f"Required field '{field_path}' not found")
            current = current[part]
        else:
            # Handle object attributes
            if not hasattr(current, part):
                if not required:
                    return
                raise AssertionError(f"Required attribute '{field_path}' not found")
            current = getattr(current, part)
    
    # Validate the field
    if current is None:
        if not allow_none:
            raise AssertionError(f"Field '{field_path}' is None but null not allowed")
        return
    
    # Check type
    if not isinstance(current, expected_type):
        # Special handling for numeric types
        if expected_type in (float, Decimal) and isinstance(current, (int, float, Decimal)):
            pass  # Allow numeric type flexibility
        else:
            raise AssertionError(
                f"Field '{field_path}' has type {type(current).__name__}, expected {expected_type.__name__}"
            )
    
    # Run validator if provided
    if validator and not validator(current):
        raise AssertionError(f"Field '{field_path}' failed validation with value: {current}")


def validate_list_field(
    obj: Dict[str, Any],
    field_path: str,
    min_length: Optional[int] = None,
    max_length: Optional[int] = None,
    item_validator: Optional[callable] = None
) -> None:
    """
    Validate a list field.
    
    Args:
        obj: Object to validate
        field_path: Path to list field
        min_length: Minimum list length
        max_length: Maximum list length
        item_validator: Function to validate each item
    """
    # First validate it's a list
    validate_field(obj, field_path, list)
    
    # Get the list
    current = obj
    for part in field_path.split('.'):
        if isinstance(current, dict):
            current = current.get(part)
        else:
            current = getattr(current, part, None)
    
    if current is None:
        return
    
    # Check length constraints
    length = len(current)
    if min_length is not None and length < min_length:
        raise AssertionError(f"List field '{field_path}' has {length} items, minimum {min_length} required")
    if max_length is not None and length > max_length:
        raise AssertionError(f"List field '{field_path}' has {length} items, maximum {max_length} allowed")
    
    # Validate items
    if item_validator:
        for i, item in enumerate(current):
            try:
                item_validator(item)
            except AssertionError as e:
                raise AssertionError(f"Item {i} in '{field_path}': {str(e)}")


def validate_money_field(obj: Dict[str, Any], field_path: str, required: bool = True) -> None:
    """Validate a money field with value and currency."""
    base_path = field_path
    
    # If the field itself is required, check it exists
    if required:
        validate_field(obj, base_path, (dict, object), required=True)
    
    # Check the money structure
    validate_field(obj, f"{base_path}.value", (int, float, Decimal), 
                  validator=FieldValidator.is_valid_price)
    validate_field(obj, f"{base_path}.currency", str,
                  validator=lambda x: len(x) == 3)  # Currency code like "USD"


def validate_item_structure(item: Union[Dict[str, Any], Any]) -> None:
    """
    Validate the structure of an eBay item.
    
    This function validates that all required fields are present and have
    the correct types, but doesn't check specific values.
    """
    # Core fields - always required
    validate_field(item, "item_id", str, validator=FieldValidator.is_valid_ebay_item_id)
    validate_field(item, "title", str, validator=FieldValidator.is_non_empty_string)
    
    # Price is required and must be valid
    validate_money_field(item, "price")
    
    # Optional fields with type validation
    validate_field(item, "subtitle", str, required=False, allow_none=True)
    validate_field(item, "description", str, required=False, allow_none=True)
    
    # URL fields
    validate_field(item, "item_url", str, validator=FieldValidator.is_valid_url)
    validate_field(item, "image_url", str, required=False, allow_none=True, validator=FieldValidator.is_valid_url)
    
    # Numeric fields
    validate_field(item, "quantity_available", int, required=False, allow_none=True,
                  validator=lambda x: x >= 0)
    validate_field(item, "quantity_sold", int, required=False, allow_none=True,
                  validator=lambda x: x >= 0)
    
    # Seller info (if present)
    if "seller" in (item if isinstance(item, dict) else vars(item)):
        validate_field(item, "seller.username", str, validator=FieldValidator.is_non_empty_string)
        validate_field(item, "seller.feedback_score", int, required=False,
                      validator=lambda x: x >= 0)
        validate_field(item, "seller.feedback_percentage", (int, float, Decimal), required=False,
                      allow_none=True, validator=FieldValidator.is_valid_percentage)
    
    # Location (if present)
    if "location" in (item if isinstance(item, dict) else vars(item)) or hasattr(item, 'item_location'):
        location_field = "location" if "location" in (item if isinstance(item, dict) else vars(item)) else "item_location"
        validate_field(item, f"{location_field}.country", str, 
                      validator=lambda x: len(x) == 2)  # Country code
        validate_field(item, f"{location_field}.city", str, required=False)
        validate_field(item, f"{location_field}.postal_code", str, required=False)


def assert_api_response_success(response: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Assert that an API response indicates success and return the parsed data.
    
    Args:
        response: JSON string or parsed response
        
    Returns:
        Parsed response data
        
    Raises:
        AssertionError: If response indicates failure
    """
    import json
    
    if isinstance(response, str):
        try:
            data = json.loads(response)
        except json.JSONDecodeError as e:
            raise AssertionError(f"Invalid JSON response: {e}")
    else:
        data = response
    
    assert "status" in data, "Response missing 'status' field"
    assert data["status"] == "success", f"Response status is '{data['status']}', expected 'success'"
    assert "data" in data, "Success response missing 'data' field"
    
    return data


def assert_list_response_structure(
    response_data: Dict[str, Any],
    item_validator: callable,
    min_items: int = 0,
    max_items: Optional[int] = None
) -> None:
    """
    Validate a list response structure (like search results).
    
    Args:
        response_data: The 'data' portion of the response
        item_validator: Function to validate each item
        min_items: Minimum expected items
        max_items: Maximum expected items
    """
    # Common list response fields
    validate_field(response_data, "total", int, required=False,
                  validator=lambda x: x >= 0)
    validate_field(response_data, "offset", int, required=False,
                  validator=lambda x: x >= 0)
    validate_field(response_data, "limit", int, required=False,
                  validator=lambda x: x > 0)
    
    # Validate items list
    validate_list_field(response_data, "items", 
                       min_length=min_items, 
                       max_length=max_items,
                       item_validator=item_validator)