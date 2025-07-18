# Universal Claude Input Conversion System - Implementation Plan

## Problem Statement
Claude Code inconsistently sends list parameters as either JSON arrays `["a","b"]` or comma-separated strings `"a,b"`. Our MCP tools must handle both formats with proper type conversion (strings, integers, decimals, enums) while maintaining backward compatibility.

## Solution Architecture

**Core Strategy: Targeted Preprocessing with Type-Aware Conversion**

## Phase 1: Build Conversion Framework

### Create `src/utils/claude_input_converter.py`

```python
"""
Universal Claude Input Conversion System

Handles Claude Code's inconsistent list parameter formats:
- JSON arrays: ["a", "b", "c"] 
- Comma strings: "a,b,c"

Provides type-aware conversion for strings, integers, decimals, and enums.
"""

from typing import Any, Dict, List, Type, Union, Optional
from decimal import Decimal
from enum import Enum
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class FieldSpec:
    """Specification for converting a field from Claude's input."""
    field_name: str
    target_type: Type  # str, int, Decimal, or Enum class
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
        if field_spec.target_type == str:
            return convert_string_list(value, field_spec.field_name)
        elif field_spec.target_type == int:
            return convert_int_list(value, field_spec.field_name)
        elif field_spec.target_type == Decimal:
            return convert_decimal_list(value, field_spec.field_name)
        elif issubclass(field_spec.target_type, Enum):
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

# Common field specifications for reuse
COMMON_FIELD_SPECS = {
    'conditions': FieldSpec('conditions', str),
    'sellers': FieldSpec('sellers', str), 
    'category_ids': FieldSpec('category_ids', str),
    'marketplace_ids': FieldSpec('marketplace_ids', str),
}
```

## Phase 2: Tool Integration Pattern

### Template for Union[str, PydanticModel] tools:

```python
# Add imports
import json
from typing import Union
from pydantic import ValidationError
from utils.claude_input_converter import preprocess_claude_json, COMMON_FIELD_SPECS, ConversionError

@mcp.tool
async def example_tool(
    ctx: Context,
    input_data: Union[str, PydanticModel]
) -> str:
    """Tool with hybrid input support."""
    
    # Define field specs for this tool
    field_specs = {
        'conditions': COMMON_FIELD_SPECS['conditions'],
        'sellers': COMMON_FIELD_SPECS['sellers'],
        # Add tool-specific specs as needed
    }
    
    # Parse input - handles both JSON strings and Pydantic objects
    try:
        if isinstance(input_data, str):
            await ctx.info("Parsing JSON parameters...")
            raw_data = json.loads(input_data)
            
            # Preprocess Claude's input formats
            processed_data = preprocess_claude_json(raw_data, field_specs)
            
            # Create Pydantic object
            input_data = PydanticModel(**processed_data)
            
        elif not isinstance(input_data, PydanticModel):
            raise ValueError(f"Expected JSON string or PydanticModel object, got {type(input_data)}")
            
    except json.JSONDecodeError as e:
        await ctx.error(f"Invalid JSON: {str(e)}")
        return error_response(
            ErrorCode.VALIDATION_ERROR,
            f"Invalid JSON: {str(e)}. Please provide valid JSON."
        ).to_json_string()
        
    except ConversionError as e:
        await ctx.error(f"Input conversion failed: {str(e)}")
        return error_response(
            ErrorCode.VALIDATION_ERROR,
            f"Input conversion failed: {str(e)}"
        ).to_json_string()
        
    except ValidationError as e:
        await ctx.error(f"Invalid parameters: {str(e)}")
        error_details = []
        serializable_errors = []
        for error in e.errors():
            field = " -> ".join(str(x) for x in error["loc"])
            error_details.append(f"{field}: {error['msg']}")
            serializable_errors.append({
                "field": field,
                "message": error["msg"],
                "type": error.get("type", "validation_error"),
                "input": error.get("input", "")
            })
        return error_response(
            ErrorCode.VALIDATION_ERROR,
            f"Invalid parameters: {'; '.join(error_details)}",
            {"validation_errors": serializable_errors}
        ).to_json_string()
    
    # Continue with normal tool logic...
```

## Phase 3: Implementation Priority

1. **browse_api.py** - Highest priority, simplest conversion
2. **marketplace_insights_api.py** - Medium priority
3. **Policy APIs** - Lower priority, more complex

## Phase 4: Testing Strategy

### Test Cases for Each Field Type:

```python
# String lists
assert convert_string_list("a,b,c", "test") == ["a", "b", "c"]
assert convert_string_list(["a", "b", "c"], "test") == ["a", "b", "c"]
assert convert_string_list("", "test") == []

# Integer lists  
assert convert_int_list("1,2,3", "test") == [1, 2, 3]
assert convert_int_list([1, 2, 3], "test") == [1, 2, 3]
assert convert_int_list("", "test") == []

# Decimal lists
assert convert_decimal_list("1.5,2.7", "test") == [Decimal("1.5"), Decimal("2.7")]

# Enum lists (with actual enum)
assert convert_enum_list("VALUE1,VALUE2", MyEnum, "test") == [MyEnum.VALUE1, MyEnum.VALUE2]
```

## Success Criteria

- ✅ All MCP tools handle both Claude input formats seamlessly
- ✅ Proper type conversion for all List[T] fields
- ✅ Zero breaking changes to existing functionality  
- ✅ Clear, maintainable code patterns
- ✅ Complete elimination of serialization errors
- ✅ Comprehensive test coverage for edge cases

## Risk Mitigation

1. **Incremental Implementation**: Start with browse_api.py as proof of concept
2. **Comprehensive Testing**: Test all combinations of input formats
3. **Graceful Error Handling**: Clear error messages for debugging
4. **Backward Compatibility**: Existing Pydantic inputs continue to work