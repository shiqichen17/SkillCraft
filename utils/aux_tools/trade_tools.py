# trade_tools.py
# Intergalactic trade calculator tools based on M3ToolEval
import json
from typing import Any
from agents.tool import FunctionTool, RunContextWrapper


# ============== Trade Functions ==============

def convert_currency(base_price: float, conversion_rate: float) -> float:
    """Converts the commodity price to local currency."""
    return base_price * conversion_rate


def calculate_tariff(price: float, tariff_rate: float) -> float:
    """Calculates the trade tariff based on the converted price."""
    return price * tariff_rate / 100


def estimate_final_value(price: float, tariff: float) -> float:
    """Estimates the final trade value including the tariff."""
    return price + tariff


def calculator(expression: str) -> float:
    """Evaluates a mathematical expression and returns the result."""
    try:
        # Only allow safe operations
        allowed_chars = set('0123456789+-*/().% ')
        if not all(c in allowed_chars for c in expression):
            return f"Error: Invalid characters in expression"
        return eval(expression)
    except Exception as e:
        return f"Error: Failed to evaluate expression: {str(e)}"


def find_minimum(*args) -> float:
    """Finds the minimum value among the given arguments."""
    return min(args)


def find_maximum(*args) -> float:
    """Finds the maximum value among the given arguments."""
    return max(args)


# ============== Tool Handlers ==============

async def on_convert_currency(context: RunContextWrapper, params_str: str) -> Any:
    params = json.loads(params_str)
    base_price = float(params.get("base_price", 0))
    conversion_rate = float(params.get("conversion_rate", 1))
    result = convert_currency(base_price, conversion_rate)
    return str(result)


async def on_calculate_tariff(context: RunContextWrapper, params_str: str) -> Any:
    params = json.loads(params_str)
    price = float(params.get("price", 0))
    tariff_rate = float(params.get("tariff_rate", 0))
    result = calculate_tariff(price, tariff_rate)
    return str(result)


async def on_estimate_final_value(context: RunContextWrapper, params_str: str) -> Any:
    params = json.loads(params_str)
    price = float(params.get("price", 0))
    tariff = float(params.get("tariff", 0))
    result = estimate_final_value(price, tariff)
    return str(result)


async def on_calculator(context: RunContextWrapper, params_str: str) -> Any:
    params = json.loads(params_str)
    expression = params.get("expression", "0")
    result = calculator(expression)
    return str(result)


async def on_find_minimum(context: RunContextWrapper, params_str: str) -> Any:
    params = json.loads(params_str)
    values = params.get("values", [])
    if not values:
        return "Error: No values provided"
    result = find_minimum(*values)
    return str(result)


async def on_find_maximum(context: RunContextWrapper, params_str: str) -> Any:
    params = json.loads(params_str)
    values = params.get("values", [])
    if not values:
        return "Error: No values provided"
    result = find_maximum(*values)
    return str(result)


# ============== Tool Definitions ==============

tool_convert_currency = FunctionTool(
    name='local-trade_convert_currency',
    description='Converts a commodity price to local currency using a conversion rate. Returns base_price * conversion_rate.',
    params_json_schema={
        "type": "object",
        "properties": {
            "base_price": {
                "type": "number",
                "description": 'The base price in galactic credits',
            },
            "conversion_rate": {
                "type": "number",
                "description": 'The conversion rate to local currency',
            },
        },
        "required": ["base_price", "conversion_rate"]
    },
    on_invoke_tool=on_convert_currency
)

tool_calculate_tariff = FunctionTool(
    name='local-trade_calculate_tariff',
    description='Calculates the trade tariff. Returns price * (tariff_rate / 100).',
    params_json_schema={
        "type": "object",
        "properties": {
            "price": {
                "type": "number",
                "description": 'The price to calculate tariff on',
            },
            "tariff_rate": {
                "type": "number",
                "description": 'The tariff rate in percentage (e.g., 8 for 8%)',
            },
        },
        "required": ["price", "tariff_rate"]
    },
    on_invoke_tool=on_calculate_tariff
)

tool_estimate_final_value = FunctionTool(
    name='local-trade_estimate_final_value',
    description='Estimates the final trade value including tariff. Returns price + tariff.',
    params_json_schema={
        "type": "object",
        "properties": {
            "price": {
                "type": "number",
                "description": 'The converted price',
            },
            "tariff": {
                "type": "number",
                "description": 'The calculated tariff amount',
            },
        },
        "required": ["price", "tariff"]
    },
    on_invoke_tool=on_estimate_final_value
)

tool_calculator = FunctionTool(
    name='local-trade_calculator',
    description='Evaluates a mathematical expression and returns the result. Supports +, -, *, /, (), %.',
    params_json_schema={
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": 'The mathematical expression to evaluate (e.g., "100 * 50 * 1.5")',
            },
        },
        "required": ["expression"]
    },
    on_invoke_tool=on_calculator
)

tool_find_minimum = FunctionTool(
    name='local-trade_find_minimum',
    description='Finds the minimum value among the given values.',
    params_json_schema={
        "type": "object",
        "properties": {
            "values": {
                "type": "array",
                "items": {"type": "number"},
                "description": 'Array of numbers to find minimum from',
            },
        },
        "required": ["values"]
    },
    on_invoke_tool=on_find_minimum
)

tool_find_maximum = FunctionTool(
    name='local-trade_find_maximum',
    description='Finds the maximum value among the given values.',
    params_json_schema={
        "type": "object",
        "properties": {
            "values": {
                "type": "array",
                "items": {"type": "number"},
                "description": 'Array of numbers to find maximum from',
            },
        },
        "required": ["values"]
    },
    on_invoke_tool=on_find_maximum
)

# Export all tools as a list
trade_tools = [
    tool_convert_currency,
    tool_calculate_tariff,
    tool_estimate_final_value,
    tool_calculator,
    tool_find_minimum,
    tool_find_maximum,
]

