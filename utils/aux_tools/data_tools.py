"""
Data Tools - Atomic-level data processing operations for skill mode testing.

These tools provide low-level data manipulation functionality that can be composed
in patterns to process API responses and other data.
"""

import json
import re
from typing import Any, List, Dict, Union
from agents.tool import FunctionTool, RunContextWrapper


# ============== Core Functions ==============

def _json_parse(text: str) -> Any:
    """Parse a JSON string into a Python object."""
    try:
        return {"success": True, "data": json.loads(text)}
    except json.JSONDecodeError as e:
        return {"success": False, "error": f"JSON parse error: {str(e)}"}


def _json_stringify(obj: Any, indent: int = None) -> str:
    """Convert a Python object to JSON string."""
    try:
        return json.dumps(obj, indent=indent, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})


def _list_sort(items: List, key: str, reverse: bool = False) -> List:
    """
    Sort a list of objects by a specified key.
    
    Args:
        items: List of dictionaries
        key: Field name to sort by
        reverse: True for descending, False for ascending
    """
    try:
        return sorted(items, key=lambda x: x.get(key, 0), reverse=reverse)
    except Exception:
        return items


def _list_filter(items: List, field: str, operator: str, value: Any) -> List:
    """
    Filter a list based on a condition.
    
    Operators: eq, ne, gt, gte, lt, lte, contains, startswith, endswith
    """
    ops = {
        'eq': lambda a, b: a == b,
        'ne': lambda a, b: a != b,
        'gt': lambda a, b: a > b,
        'gte': lambda a, b: a >= b,
        'lt': lambda a, b: a < b,
        'lte': lambda a, b: a <= b,
        'contains': lambda a, b: b in str(a) if a else False,
        'startswith': lambda a, b: str(a).startswith(b) if a else False,
        'endswith': lambda a, b: str(a).endswith(b) if a else False,
        'in': lambda a, b: a in b if isinstance(b, list) else False,
    }
    
    op_func = ops.get(operator, ops['eq'])
    
    try:
        return [item for item in items if op_func(item.get(field), value)]
    except Exception:
        return []


def _list_slice(items: List, start: int = 0, end: int = None) -> List:
    """Get a slice of a list."""
    if end is None:
        return items[start:]
    return items[start:end]


def _list_length(items: List) -> int:
    """Get the length of a list."""
    return len(items) if items else 0


def _list_map(items: List, fields: List[str]) -> List:
    """
    Extract specific fields from each item in a list.
    
    Args:
        items: List of dictionaries
        fields: List of field names to extract
    
    Returns:
        List of dictionaries with only the specified fields
    """
    result = []
    for item in items:
        extracted = {}
        for field in fields:
            if '.' in field:
                # Support nested field access like "author.name"
                parts = field.split('.')
                val = item
                for part in parts:
                    val = val.get(part, {}) if isinstance(val, dict) else None
                extracted[field.replace('.', '_')] = val
            else:
                extracted[field] = item.get(field)
        result.append(extracted)
    return result


def _list_unique(items: List, field: str = None) -> List:
    """
    Get unique items from a list.
    
    Args:
        items: List of items (primitives or dicts)
        field: If items are dicts, deduplicate by this field
    """
    if not items:
        return []
    
    if field:
        seen = set()
        result = []
        for item in items:
            key = item.get(field) if isinstance(item, dict) else item
            if key not in seen:
                seen.add(key)
                result.append(item)
        return result
    else:
        # For primitive lists
        return list(dict.fromkeys(items))


def _list_group_by(items: List, field: str) -> Dict[str, List]:
    """
    Group items by a field value.
    
    Returns dict with field values as keys and lists of matching items as values.
    """
    groups = {}
    for item in items:
        key = str(item.get(field, 'unknown'))
        if key not in groups:
            groups[key] = []
        groups[key].append(item)
    return groups


def _dict_get(obj: Dict, path: str, default: Any = None) -> Any:
    """
    Get a value from a nested dictionary using dot notation.
    
    Example: dict_get({"a": {"b": 1}}, "a.b") → 1
    """
    try:
        keys = path.split('.')
        val = obj
        for key in keys:
            if isinstance(val, dict):
                val = val.get(key)
            elif isinstance(val, list) and key.isdigit():
                val = val[int(key)]
            else:
                return default
        return val if val is not None else default
    except Exception:
        return default


def _aggregate_sum(items: List, field: str) -> float:
    """Sum values of a field across all items."""
    try:
        return sum(item.get(field, 0) for item in items)
    except Exception:
        return 0


def _aggregate_max(items: List, field: str) -> Dict:
    """Find the item with the maximum value for a field."""
    try:
        if not items:
            return {}
        return max(items, key=lambda x: x.get(field, 0))
    except Exception:
        return {}


def _aggregate_min(items: List, field: str) -> Dict:
    """Find the item with the minimum value for a field."""
    try:
        if not items:
            return {}
        return min(items, key=lambda x: x.get(field, float('inf')))
    except Exception:
        return {}


def _aggregate_avg(items: List, field: str) -> float:
    """Calculate the average of a field across all items."""
    try:
        if not items:
            return 0
        values = [item.get(field, 0) for item in items]
        return sum(values) / len(values)
    except Exception:
        return 0


def _aggregate_count(items: List, field: str = None, value: Any = None) -> int:
    """
    Count items, optionally filtering by field value.
    
    Args:
        items: List to count
        field: Optional field to check
        value: Value to match (if field specified)
    """
    if field is None:
        return len(items)
    return sum(1 for item in items if item.get(field) == value)


# ============== Tool Handlers ==============

async def on_json_parse(context: RunContextWrapper, params_str: str) -> Any:
    params = json.loads(params_str)
    text = params.get("text", "")
    result = _json_parse(text)
    return result


async def on_json_stringify(context: RunContextWrapper, params_str: str) -> Any:
    params = json.loads(params_str)
    obj = params.get("obj")
    indent = params.get("indent")
    return _json_stringify(obj, indent)


async def on_list_sort(context: RunContextWrapper, params_str: str) -> Any:
    params = json.loads(params_str)
    items = params.get("items", [])
    key = params.get("key", "")
    reverse = params.get("reverse", False)
    result = _list_sort(items, key, reverse)
    return result


async def on_list_filter(context: RunContextWrapper, params_str: str) -> Any:
    params = json.loads(params_str)
    items = params.get("items", [])
    field = params.get("field", "")
    operator = params.get("operator", "eq")
    value = params.get("value")
    result = _list_filter(items, field, operator, value)
    return result


async def on_list_slice(context: RunContextWrapper, params_str: str) -> Any:
    params = json.loads(params_str)
    items = params.get("items", [])
    start = params.get("start", 0)
    end = params.get("end")
    result = _list_slice(items, start, end)
    return result


async def on_list_length(context: RunContextWrapper, params_str: str) -> Any:
    params = json.loads(params_str)
    items = params.get("items", [])
    return str(_list_length(items))


async def on_list_map(context: RunContextWrapper, params_str: str) -> Any:
    params = json.loads(params_str)
    items = params.get("items", [])
    fields = params.get("fields", [])
    result = _list_map(items, fields)
    return result


async def on_list_unique(context: RunContextWrapper, params_str: str) -> Any:
    params = json.loads(params_str)
    items = params.get("items", [])
    field = params.get("field")
    result = _list_unique(items, field)
    return result


async def on_list_group_by(context: RunContextWrapper, params_str: str) -> Any:
    params = json.loads(params_str)
    items = params.get("items", [])
    field = params.get("field", "")
    result = _list_group_by(items, field)
    return result


async def on_dict_get(context: RunContextWrapper, params_str: str) -> Any:
    params = json.loads(params_str)
    obj = params.get("obj", {})
    path = params.get("path", "")
    default = params.get("default")
    result = _dict_get(obj, path, default)
    return result


async def on_aggregate_sum(context: RunContextWrapper, params_str: str) -> Any:
    params = json.loads(params_str)
    items = params.get("items", [])
    field = params.get("field", "")
    return str(_aggregate_sum(items, field))


async def on_aggregate_max(context: RunContextWrapper, params_str: str) -> Any:
    params = json.loads(params_str)
    items = params.get("items", [])
    field = params.get("field", "")
    result = _aggregate_max(items, field)
    return result


async def on_aggregate_min(context: RunContextWrapper, params_str: str) -> Any:
    params = json.loads(params_str)
    items = params.get("items", [])
    field = params.get("field", "")
    result = _aggregate_min(items, field)
    return result


async def on_aggregate_avg(context: RunContextWrapper, params_str: str) -> Any:
    params = json.loads(params_str)
    items = params.get("items", [])
    field = params.get("field", "")
    return str(_aggregate_avg(items, field))


async def on_aggregate_count(context: RunContextWrapper, params_str: str) -> Any:
    params = json.loads(params_str)
    items = params.get("items", [])
    field = params.get("field")
    value = params.get("value")
    return str(_aggregate_count(items, field, value))


# ============== Tool Definitions ==============

tool_json_parse = FunctionTool(
    name='local-json_parse',
    description='''Parse a JSON string into a data structure.

Example: json_parse(text='{"name": "Alice", "age": 30}')
→ {"success": true, "data": {"name": "Alice", "age": 30}}

Use this after http_get to parse JSON API responses.''',
    params_json_schema={
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "JSON string to parse"
            }
        },
        "required": ["text"]
    },
    on_invoke_tool=on_json_parse
)

tool_json_stringify = FunctionTool(
    name='local-json_stringify',
    description='Convert a data structure to a JSON string.',
    params_json_schema={
        "type": "object",
        "properties": {
            "obj": {
                "description": "Object to convert to JSON"
            },
            "indent": {
                "type": "integer",
                "description": "Indentation level for pretty printing"
            }
        },
        "required": ["obj"]
    },
    on_invoke_tool=on_json_stringify
)

tool_list_sort = FunctionTool(
    name='local-list_sort',
    description='''Sort a list of objects by a specified field.

Example: list_sort(items=[{"name": "B", "score": 80}, {"name": "A", "score": 90}], key="score", reverse=true)
→ [{"name": "A", "score": 90}, {"name": "B", "score": 80}]''',
    params_json_schema={
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "description": "List of objects to sort"
            },
            "key": {
                "type": "string",
                "description": "Field name to sort by"
            },
            "reverse": {
                "type": "boolean",
                "description": "True for descending order (default: false)"
            }
        },
        "required": ["items", "key"]
    },
    on_invoke_tool=on_list_sort
)

tool_list_filter = FunctionTool(
    name='local-list_filter',
    description='''Filter a list based on a condition.

Operators: eq, ne, gt, gte, lt, lte, contains, startswith, endswith, in

Example: list_filter(items=[...], field="status", operator="eq", value="active")''',
    params_json_schema={
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "description": "List to filter"
            },
            "field": {
                "type": "string",
                "description": "Field to check"
            },
            "operator": {
                "type": "string",
                "enum": ["eq", "ne", "gt", "gte", "lt", "lte", "contains", "startswith", "endswith", "in"],
                "description": "Comparison operator"
            },
            "value": {
                "description": "Value to compare against"
            }
        },
        "required": ["items", "field", "operator", "value"]
    },
    on_invoke_tool=on_list_filter
)

tool_list_slice = FunctionTool(
    name='local-list_slice',
    description='''Get a portion of a list.

Example: list_slice(items=[1,2,3,4,5], start=0, end=3) → [1, 2, 3]
Example: list_slice(items=[1,2,3,4,5], start=2) → [3, 4, 5]''',
    params_json_schema={
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "description": "List to slice"
            },
            "start": {
                "type": "integer",
                "description": "Start index (default: 0)"
            },
            "end": {
                "type": "integer",
                "description": "End index (exclusive, default: end of list)"
            }
        },
        "required": ["items"]
    },
    on_invoke_tool=on_list_slice
)

tool_list_length = FunctionTool(
    name='local-list_length',
    description='Get the number of items in a list.',
    params_json_schema={
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "description": "List to count"
            }
        },
        "required": ["items"]
    },
    on_invoke_tool=on_list_length
)

tool_list_map = FunctionTool(
    name='local-list_map',
    description='''Extract specific fields from each item in a list.

Example: list_map(items=[{"name": "A", "age": 30, "city": "NYC"}, ...], fields=["name", "age"])
→ [{"name": "A", "age": 30}, ...]

Supports nested fields with dot notation: "author.name"''',
    params_json_schema={
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "description": "List of objects"
            },
            "fields": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Field names to extract (supports dot notation for nested fields)"
            }
        },
        "required": ["items", "fields"]
    },
    on_invoke_tool=on_list_map
)

tool_list_unique = FunctionTool(
    name='local-list_unique',
    description='Remove duplicates from a list, optionally by a specific field.',
    params_json_schema={
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "description": "List to deduplicate"
            },
            "field": {
                "type": "string",
                "description": "Field to use for uniqueness (for lists of objects)"
            }
        },
        "required": ["items"]
    },
    on_invoke_tool=on_list_unique
)

tool_list_group_by = FunctionTool(
    name='local-list_group_by',
    description='''Group items by a field value.

Example: list_group_by(items=[{"type": "A", "val": 1}, {"type": "B", "val": 2}, {"type": "A", "val": 3}], field="type")
→ {"A": [{"type": "A", "val": 1}, {"type": "A", "val": 3}], "B": [{"type": "B", "val": 2}]}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "description": "List to group"
            },
            "field": {
                "type": "string",
                "description": "Field to group by"
            }
        },
        "required": ["items", "field"]
    },
    on_invoke_tool=on_list_group_by
)

tool_dict_get = FunctionTool(
    name='local-dict_get',
    description='''Get a value from a nested dictionary using dot notation.

Example: dict_get(obj={"a": {"b": {"c": 123}}}, path="a.b.c") → 123
Example: dict_get(obj={"items": [1, 2, 3]}, path="items.0") → 1''',
    params_json_schema={
        "type": "object",
        "properties": {
            "obj": {
                "type": "object",
                "description": "Dictionary to extract from"
            },
            "path": {
                "type": "string",
                "description": "Dot-separated path (e.g., 'user.name' or 'items.0')"
            },
            "default": {
                "description": "Default value if path not found"
            }
        },
        "required": ["obj", "path"]
    },
    on_invoke_tool=on_dict_get
)

tool_aggregate_sum = FunctionTool(
    name='local-aggregate_sum',
    description='Sum the values of a numeric field across all items in a list.',
    params_json_schema={
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "description": "List of objects"
            },
            "field": {
                "type": "string",
                "description": "Numeric field to sum"
            }
        },
        "required": ["items", "field"]
    },
    on_invoke_tool=on_aggregate_sum
)

tool_aggregate_max = FunctionTool(
    name='local-aggregate_max',
    description='Find the item with the maximum value for a field. Returns the entire item.',
    params_json_schema={
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "description": "List of objects"
            },
            "field": {
                "type": "string",
                "description": "Field to find maximum of"
            }
        },
        "required": ["items", "field"]
    },
    on_invoke_tool=on_aggregate_max
)

tool_aggregate_min = FunctionTool(
    name='local-aggregate_min',
    description='Find the item with the minimum value for a field. Returns the entire item.',
    params_json_schema={
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "description": "List of objects"
            },
            "field": {
                "type": "string",
                "description": "Field to find minimum of"
            }
        },
        "required": ["items", "field"]
    },
    on_invoke_tool=on_aggregate_min
)

tool_aggregate_avg = FunctionTool(
    name='local-aggregate_avg',
    description='Calculate the average of a numeric field across all items.',
    params_json_schema={
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "description": "List of objects"
            },
            "field": {
                "type": "string",
                "description": "Numeric field to average"
            }
        },
        "required": ["items", "field"]
    },
    on_invoke_tool=on_aggregate_avg
)

tool_aggregate_count = FunctionTool(
    name='local-aggregate_count',
    description='''Count items in a list, optionally filtering by a field value.

Example: aggregate_count(items=[...]) → total count
Example: aggregate_count(items=[...], field="status", value="active") → count where status=="active"''',
    params_json_schema={
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "description": "List to count"
            },
            "field": {
                "type": "string",
                "description": "Optional: field to filter by"
            },
            "value": {
                "description": "Optional: value to match"
            }
        },
        "required": ["items"]
    },
    on_invoke_tool=on_aggregate_count
)

# Export all tools
data_tools = [
    tool_json_parse,
    tool_json_stringify,
    tool_list_sort,
    tool_list_filter,
    tool_list_slice,
    tool_list_length,
    tool_list_map,
    tool_list_unique,
    tool_list_group_by,
    tool_dict_get,
    tool_aggregate_sum,
    tool_aggregate_max,
    tool_aggregate_min,
    tool_aggregate_avg,
    tool_aggregate_count,
]

