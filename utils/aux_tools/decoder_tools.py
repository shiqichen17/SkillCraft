# decoder_tools.py
# Message decoder tools based on M3ToolEval
import json
from typing import Any
from agents.tool import FunctionTool, RunContextWrapper


# ============== Decoder Functions ==============

def convert_hex_to_ascii(hex_string: str) -> str:
    """Converts a hexadecimal string to ASCII."""
    try:
        return bytes.fromhex(hex_string).decode('utf-8')
    except Exception as e:
        return f"Error: {str(e)}"


def reverse_string(s: str) -> str:
    """Reverses a string."""
    return s[::-1]


def caesar_decode(message: str, shift: int) -> str:
    """Decodes a string using the Caesar cipher."""
    shift = int(shift)
    decoded = ''.join(
        chr((ord(char) - shift - 65) % 26 + 65) if char.isupper()
        else chr((ord(char) - shift - 97) % 26 + 97) if char.islower()
        else char
        for char in message
    )
    return decoded


def caesar_encode(message: str, shift: int) -> str:
    """Encodes a string using the Caesar cipher."""
    shift = int(shift)
    encoded = ''.join(
        chr((ord(char) + shift - 65) % 26 + 65) if char.isupper()
        else chr((ord(char) + shift - 97) % 26 + 97) if char.islower()
        else char
        for char in message
    )
    return encoded


def string_length(s: str) -> int:
    """Finds the length of a string."""
    return len(s)


def convert_ascii_to_hex(ascii_string: str) -> str:
    """Converts an ASCII string to hexadecimal."""
    return ascii_string.encode().hex()


# ============== Tool Handlers ==============

async def on_hex_to_ascii(context: RunContextWrapper, params_str: str) -> Any:
    params = json.loads(params_str)
    hex_string = params.get("hex_string", "")
    return convert_hex_to_ascii(hex_string)


async def on_reverse_string(context: RunContextWrapper, params_str: str) -> Any:
    params = json.loads(params_str)
    s = params.get("string", "")
    return reverse_string(s)


async def on_caesar_decode(context: RunContextWrapper, params_str: str) -> Any:
    params = json.loads(params_str)
    message = params.get("message", "")
    shift = params.get("shift", 0)
    return caesar_decode(message, shift)


async def on_caesar_encode(context: RunContextWrapper, params_str: str) -> Any:
    params = json.loads(params_str)
    message = params.get("message", "")
    shift = params.get("shift", 0)
    return caesar_encode(message, shift)


async def on_string_length(context: RunContextWrapper, params_str: str) -> Any:
    params = json.loads(params_str)
    s = params.get("string", "")
    return str(string_length(s))


async def on_ascii_to_hex(context: RunContextWrapper, params_str: str) -> Any:
    params = json.loads(params_str)
    ascii_string = params.get("ascii_string", "")
    return convert_ascii_to_hex(ascii_string)


# ============== Tool Definitions ==============

tool_hex_to_ascii = FunctionTool(
    name='local-decoder_hex_to_ascii',
    description='Converts a hexadecimal string to ASCII text.',
    params_json_schema={
        "type": "object",
        "properties": {
            "hex_string": {
                "type": "string",
                "description": 'The hexadecimal string to convert (e.g., "48656c6c6f")',
            },
        },
        "required": ["hex_string"]
    },
    on_invoke_tool=on_hex_to_ascii
)

tool_reverse_string = FunctionTool(
    name='local-decoder_reverse_string',
    description='Reverses a string.',
    params_json_schema={
        "type": "object",
        "properties": {
            "string": {
                "type": "string",
                "description": 'The string to reverse',
            },
        },
        "required": ["string"]
    },
    on_invoke_tool=on_reverse_string
)

tool_caesar_decode = FunctionTool(
    name='local-decoder_caesar_decode',
    description='Decodes a string using the Caesar cipher with a given shift value.',
    params_json_schema={
        "type": "object",
        "properties": {
            "message": {
                "type": "string",
                "description": 'The message to decode',
            },
            "shift": {
                "type": "integer",
                "description": 'The shift value used in the Caesar cipher',
            },
        },
        "required": ["message", "shift"]
    },
    on_invoke_tool=on_caesar_decode
)

tool_caesar_encode = FunctionTool(
    name='local-decoder_caesar_encode',
    description='Encodes a string using the Caesar cipher with a given shift value.',
    params_json_schema={
        "type": "object",
        "properties": {
            "message": {
                "type": "string",
                "description": 'The message to encode',
            },
            "shift": {
                "type": "integer",
                "description": 'The shift value for the Caesar cipher',
            },
        },
        "required": ["message", "shift"]
    },
    on_invoke_tool=on_caesar_encode
)

tool_string_length = FunctionTool(
    name='local-decoder_string_length',
    description='Returns the length of a string.',
    params_json_schema={
        "type": "object",
        "properties": {
            "string": {
                "type": "string",
                "description": 'The string to measure',
            },
        },
        "required": ["string"]
    },
    on_invoke_tool=on_string_length
)

tool_ascii_to_hex = FunctionTool(
    name='local-decoder_ascii_to_hex',
    description='Converts an ASCII string to hexadecimal.',
    params_json_schema={
        "type": "object",
        "properties": {
            "ascii_string": {
                "type": "string",
                "description": 'The ASCII string to convert',
            },
        },
        "required": ["ascii_string"]
    },
    on_invoke_tool=on_ascii_to_hex
)

# Export all tools as a list
decoder_tools = [
    tool_hex_to_ascii,
    tool_reverse_string,
    tool_caesar_decode,
    tool_caesar_encode,
    tool_string_length,
    tool_ascii_to_hex,
]

