"""
Universal Claude Input Conversion System

Handles Claude Code's inconsistent list parameter formats:
- JSON arrays: ["a", "b", "c"] 
- Comma strings: "a,b,c"

Provides type-aware conversion for strings, integers, decimals, and enums.
"""

from typing import Any, Dict, List, Type, Union
from decimal import Decimal
from enum import Enum
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

class CommaString:
    """Special type to indicate comma-separated string output."""
    pass

@dataclass
class FieldSpec:
    """Specification for converting a field from Claude's input."""
    field_name: str
    target_type: Type  # str, int, Decimal, Enum class, or CommaString
    is_optional: bool = True
    allow_single_value: bool = True  # Convert "value" to ["value"]

class ConversionError(Exception):
    """Raised when field conversion fails."""
    pass

def convert_string_list(value: Union[str, List[str]], field_name: str) -> List[str]:
    """Convert comma-separated string or array to list of strings."""
    if isinstance(value, list):
        return [str(item).strip() for item in value]
    
    if isinstance(value, str):
        if not value.strip():
            return []
        return [item.strip() for item in value.split(',') if item.strip()]
    
    raise ConversionError(f"Cannot convert {type(value)} to string list for field '{field_name}'")

def convert_to_comma_string(value: Union[str, List[str]], field_name: str) -> str:
    """Convert array or comma-separated string to comma-separated string."""
    if isinstance(value, list):
        return ','.join(str(item).strip() for item in value if str(item).strip())
    
    if isinstance(value, str):
        if not value.strip():
            return ""
        # Clean up the string - split and rejoin to normalize
        items = [item.strip() for item in value.split(',') if item.strip()]
        return ','.join(items)
    
    raise ConversionError(f"Cannot convert {type(value)} to comma string for field '{field_name}'")

def convert_int_list(value: Union[str, List[Union[str, int]]], field_name: str) -> List[int]:
    """Convert comma-separated string or array to list of integers."""
    if isinstance(value, list):
        try:
            return [int(item) for item in value]
        except (ValueError, TypeError) as e:
            raise ConversionError(f"Invalid integer in list for field '{field_name}': {e}")
    
    if isinstance(value, str):
        if not value.strip():
            return []
        try:
            return [int(item.strip()) for item in value.split(',') if item.strip()]
        except ValueError as e:
            raise ConversionError(f"Invalid integer in comma-separated string for field '{field_name}': {e}")
    
    raise ConversionError(f"Cannot convert {type(value)} to integer list for field '{field_name}'")

def convert_decimal_list(value: Union[str, List[Union[str, float, Decimal]]], field_name: str) -> List[Decimal]:
    """Convert comma-separated string or array to list of Decimals."""
    if isinstance(value, list):
        try:
            return [Decimal(str(item)) for item in value]
        except (ValueError, TypeError) as e:
            raise ConversionError(f"Invalid decimal in list for field '{field_name}': {e}")
    
    if isinstance(value, str):
        if not value.strip():
            return []
        try:
            return [Decimal(item.strip()) for item in value.split(',') if item.strip()]
        except (ValueError, TypeError) as e:
            raise ConversionError(f"Invalid decimal in comma-separated string for field '{field_name}': {e}")
    
    raise ConversionError(f"Cannot convert {type(value)} to decimal list for field '{field_name}'")

def convert_enum_list(value: Union[str, List[Union[str, Enum]]], enum_class: Type[Enum], field_name: str) -> List[Enum]:
    """Convert comma-separated string or array to list of enum values."""
    if isinstance(value, list):
        try:
            result = []
            for item in value:
                if isinstance(item, enum_class):
                    result.append(item)
                elif isinstance(item, str):
                    result.append(enum_class(item))
                else:
                    result.append(enum_class(str(item)))
            return result
        except (ValueError, TypeError) as e:
            raise ConversionError(f"Invalid enum value in list for field '{field_name}': {e}")
    
    if isinstance(value, str):
        if not value.strip():
            return []
        try:
            return [enum_class(item.strip()) for item in value.split(',') if item.strip()]
        except (ValueError, TypeError) as e:
            raise ConversionError(f"Invalid enum value in comma-separated string for field '{field_name}': {e}")
    
    raise ConversionError(f"Cannot convert {type(value)} to enum list for field '{field_name}'")

def convert_field(value: Any, field_spec: FieldSpec) -> Any:
    """Convert a field value based on its specification."""
    if value is None:
        return None if field_spec.is_optional else []
    
    try:
        if field_spec.target_type is str:
            return convert_string_list(value, field_spec.field_name)
        elif field_spec.target_type is CommaString:
            return convert_to_comma_string(value, field_spec.field_name)
        elif field_spec.target_type is int:
            return convert_int_list(value, field_spec.field_name)
        elif field_spec.target_type is Decimal:
            return convert_decimal_list(value, field_spec.field_name)
        elif isinstance(field_spec.target_type, type) and issubclass(field_spec.target_type, Enum):
            return convert_enum_list(value, field_spec.target_type, field_spec.field_name)
        else:
            raise ConversionError(f"Unsupported target type {field_spec.target_type} for field '{field_spec.field_name}'")
    
    except ConversionError:
        raise
    except Exception as e:
        raise ConversionError(f"Unexpected error converting field '{field_spec.field_name}': {e}")

def preprocess_claude_json(json_data: Dict[str, Any], field_specs: Dict[str, FieldSpec]) -> Dict[str, Any]:
    """
    Preprocess Claude's JSON input to handle comma-separated strings.
    
    Args:
        json_data: Parsed JSON data from Claude
        field_specs: Specifications for fields that need conversion
        
    Returns:
        Preprocessed data ready for Pydantic validation
        
    Raises:
        ConversionError: If any field conversion fails
    """
    if not field_specs:
        return json_data
    
    result = json_data.copy()
    
    for field_name, field_spec in field_specs.items():
        if field_name in result:
            try:
                logger.debug(f"Converting field '{field_name}' with value: {result[field_name]}")
                converted_value = convert_field(result[field_name], field_spec)
                result[field_name] = converted_value
                logger.debug(f"Converted '{field_name}' to: {converted_value}")
            except ConversionError as e:
                logger.error(f"Field conversion failed: {e}")
                raise
    
    return result

# Common field specifications for reuse across tools
COMMON_FIELD_SPECS = {
    'conditions': FieldSpec('conditions', CommaString),
    'sellers': FieldSpec('sellers', CommaString), 
    'category_ids': FieldSpec('category_ids', CommaString),
    'marketplace_ids': FieldSpec('marketplace_ids', CommaString),
}