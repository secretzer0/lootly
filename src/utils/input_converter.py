"""
Universal LLM Input Conversion System

Handles LLM Code's inconsistent input formats:
- JSON strings: '{"key": "value"}' -> parsed objects
- JSON arrays: ["a", "b", "c"] vs comma strings: "a,b,c"
- Type conversions for strings, integers, decimals, and enums

Provides MCP-compatible preprocessing for pydantic models.
"""

import json
import inspect
from typing import Any, Dict, List, Type, Union, Callable, get_type_hints, TYPE_CHECKING
from decimal import Decimal
from enum import Enum
from dataclasses import dataclass
from functools import wraps
import logging

if TYPE_CHECKING:
    from pydantic import BaseModel

logger = logging.getLogger(__name__)

class CommaString:
    """Special type to indicate comma-separated string output."""
    pass

@dataclass
class FieldSpec:
    """Specification for converting a field from LLM's input."""
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

def preprocess_llm_json(json_data: Dict[str, Any], field_specs: Dict[str, FieldSpec]) -> Dict[str, Any]:
    """
    Preprocess LLM's JSON input to handle comma-separated strings.
    
    Args:
        json_data: Parsed JSON data from LLM
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


def parse_json_string_parameter(value: Any, param_name: str) -> Any:
    """
    Parse JSON string parameter into a Python object.
    
    This handles the common MCP issue where pydantic model parameters
    are sent as JSON strings instead of parsed objects.
    
    Args:
        value: The parameter value (string, dict, or other)
        param_name: Parameter name for error reporting
        
    Returns:
        Parsed object if input was JSON string, otherwise original value
        
    Raises:
        ValueError: If JSON parsing fails
    """
    if isinstance(value, str):
        try:
            # Try to parse as JSON
            logger.debug(f"Attempting to parse JSON string for parameter '{param_name}': {value}")
            parsed_value = json.loads(value)
            logger.debug(f"Successfully parsed '{param_name}' from JSON string")
            return parsed_value
        except json.JSONDecodeError as e:
            # Not valid JSON, return as-is (might be a regular string parameter)
            logger.debug(f"Parameter '{param_name}' is not valid JSON, treating as string: {e}")
            return value
    
    # Not a string, return as-is
    return value


def mcp_pydantic_preprocessor(func: Callable) -> Callable:
    """
    Decorator to preprocess MCP tool parameters for pydantic validation.
    
    This decorator automatically:
    1. Parses JSON string parameters into objects
    2. Applies field-specific preprocessing (comma-separated strings, etc.)
    3. Validates using pydantic models
    
    Usage:
        @mcp_pydantic_preprocessor
        @mcp.tool
        async def my_tool(ctx: Context, search_input: MyPydanticModel) -> str:
            # search_input is now properly validated
            
    Args:
        func: The MCP tool function to wrap
        
    Returns:
        Wrapped function with automatic preprocessing
    """
    from pydantic import BaseModel
    
    # Get function signature
    sig = inspect.signature(func)
    
    # Find parameters that are pydantic models
    # We'll determine this lazily at runtime to avoid import issues
    pydantic_params = {}
    
    def _get_pydantic_params():
        """Lazily determine pydantic parameters to avoid import issues."""
        if pydantic_params:  # Already computed
            return pydantic_params
            
        try:
            # Try to get type hints safely
            type_hints = get_type_hints(func)
            for param_name, param in sig.parameters.items():
                if param_name in type_hints and param_name != 'ctx':  # Skip Context parameter
                    param_type = type_hints[param_name]
                    if isinstance(param_type, type) and issubclass(param_type, BaseModel):
                        pydantic_params[param_name] = param_type
        except (NameError, AttributeError) as e:
            # Fallback: try to identify pydantic models by annotation string
            logger.debug(f"Could not get type hints for {func.__name__}: {e}")
            for param_name, param in sig.parameters.items():
                if param_name != 'ctx' and param.annotation != inspect.Parameter.empty:
                    # Try to evaluate the annotation
                    try:
                        if hasattr(param.annotation, '__name__') and 'Input' in param.annotation.__name__:
                            # Assume it's a pydantic model if it ends with "Input"
                            pydantic_params[param_name] = param.annotation
                    except:
                        pass
        
        return pydantic_params
    
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Get pydantic parameters lazily
        current_pydantic_params = _get_pydantic_params()
        
        # Process each pydantic parameter
        for param_name, param_type in current_pydantic_params.items():
            if param_name in kwargs:
                value = kwargs[param_name]
                
                # Step 1: Parse JSON string if needed
                parsed_value = parse_json_string_parameter(value, param_name)
                
                # Step 2: Apply field-specific preprocessing if available
                if isinstance(parsed_value, dict):
                    # Determine field specs based on model type
                    field_specs = {}
                    if hasattr(param_type, '__name__'):
                        model_name = param_type.__name__
                        if model_name == 'BrowseSearchInput':
                            # Apply search-specific field conversions
                            field_specs = {
                                'conditions': COMMON_FIELD_SPECS['conditions'],
                                'category_ids': COMMON_FIELD_SPECS['category_ids'],
                                'sellers': COMMON_FIELD_SPECS['sellers']
                            }
                        # Add more model-specific field specs here as needed
                    
                    if field_specs:
                        try:
                            parsed_value = preprocess_llm_json(parsed_value, field_specs)
                            logger.debug(f"Applied field preprocessing to '{param_name}'")
                        except Exception as e:
                            logger.error(f"Field preprocessing failed for '{param_name}': {e}")
                            raise ValueError(f"Field preprocessing failed for '{param_name}': {e}")
                
                # Step 3: Create pydantic model instance (this handles validation)
                try:
                    if isinstance(parsed_value, dict):
                        kwargs[param_name] = param_type(**parsed_value)
                    else:
                        # If not a dict, let pydantic handle it (might be already a model instance)
                        kwargs[param_name] = parsed_value
                    logger.debug(f"Successfully validated pydantic model for '{param_name}'")
                except Exception as e:
                    logger.error(f"Pydantic validation failed for '{param_name}': {e}")
                    raise ValueError(f"Pydantic validation failed for '{param_name}': {e}")
        
        # Call the original function with processed arguments
        return await func(*args, **kwargs)
    
    return wrapper