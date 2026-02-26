# monkeypatch
from __future__ import annotations
from agents.mcp.util import *
from agents import _debug
import os
from utils.general.helper import print_color


import shortuuid

MAX_SINGLE_TURN_RETURN_CHARS = int(os.getenv("BENCH_MAX_SINGLE_TURN_RETURN_CHARS", 100000)) # Maximum number of characters allowed in a single turn tool return
ENABLE_OVERLONG_TOOL_OUTPUT_MANAGEMENT = os.getenv("BENCH_ENABLE_OVERLONG_TOOL_OUTPUT_MANAGEMENT", "true").lower() == "true"

print_color(f"BENCH_ENABLE_OVERLONG_TOOL_OUTPUT_MANAGEMENT: {ENABLE_OVERLONG_TOOL_OUTPUT_MANAGEMENT} | MAX_SINGLE_TURN_RETURN_CHARS: {MAX_SINGLE_TURN_RETURN_CHARS}", color="blue")

@classmethod
def my_to_function_tool(
    cls, tool: "MCPTool", server: "MCPServer", convert_schemas_to_strict: bool
) -> FunctionTool:
    """Convert an MCP tool to an Agents SDK function tool."""
    invoke_func = functools.partial(cls.invoke_mcp_tool, server, tool)
    schema, is_strict = tool.inputSchema, False

    # MCP spec doesn't require the inputSchema to have `properties`, but OpenAI spec does.
    if "properties" not in schema:
        schema["properties"] = {}

    if convert_schemas_to_strict:
        try:
            schema = ensure_strict_json_schema(schema)
            is_strict = True
        except Exception as e:
            logger.info(f"Error converting MCP schema to strict mode: {e}")

    return FunctionTool(
        name=server.name
        + "-"
        + tool.name,  # add the server name as prefix to distinguish duplicate tool names
        description=tool.description or "",
        params_json_schema=schema,
        on_invoke_tool=invoke_func,
        strict_json_schema=is_strict,
    )

def _detect_truncation(json_str: str) -> tuple[bool, str]:
    """Detect if JSON string appears to be truncated and provide diagnostic info."""
    if not json_str:
        return False, ""
    
    json_str = json_str.strip()
    
    # Check for obvious truncation signs
    truncation_signs = []
    
    # 1. Doesn't end with valid JSON terminator
    if not json_str.endswith(('}', ']', '"', 'true', 'false', 'null')) and not json_str[-1].isdigit():
        truncation_signs.append(f"ends with '{json_str[-20:]}' instead of valid JSON terminator")
    
    # 2. Unbalanced braces/brackets
    open_braces = json_str.count('{') - json_str.count('}')
    open_brackets = json_str.count('[') - json_str.count(']')
    if open_braces > 0:
        truncation_signs.append(f"{open_braces} unclosed '{{' braces")
    if open_brackets > 0:
        truncation_signs.append(f"{open_brackets} unclosed '[' brackets")
    
    # 3. Ends with backslash (escape sequence cut off)
    if json_str.endswith('\\'):
        truncation_signs.append("ends with incomplete escape sequence")
    
    # 4. Very long string (likely to hit limits)
    if len(json_str) > 10000:
        truncation_signs.append(f"very long ({len(json_str)} chars, may have hit token limit)")
    
    if truncation_signs:
        return True, "; ".join(truncation_signs)
    return False, ""

@classmethod
async def my_invoke_mcp_tool(
    cls, server: "MCPServer", tool: "MCPTool", context: RunContextWrapper[Any], input_json: str
) -> str:
    """Invoke an MCP tool and return the result as a string."""
    try:
        json_data: dict[str, Any] = json.loads(input_json) if input_json else {}
    except Exception as e:
        # Check if this looks like a truncated response
        is_truncated, truncation_info = _detect_truncation(input_json)
        
        if is_truncated:
            error_msg = (
                f"Model output appears to be TRUNCATED for tool {tool.name}. "
                f"JSON length: {len(input_json)} chars. "
                f"Truncation indicators: {truncation_info}. "
                f"This usually means the model hit its max_tokens limit.\n\n"
                f"⚠️ DO NOT retry with the same approach! Use CHUNKED WRITING instead:\n\n"
                f"**For JSON arrays, use `local-file_write_json_chunk`:**\n"
                f"```\n"
                f"1. local-file_write_json_chunk(path=\"output.json\", chunk_type=\"start\", array_key=\"items\")\n"
                f"2. local-file_write_json_chunk(path=\"output.json\", chunk_type=\"item\", content='{{\"id\": 1, ...}}')\n"
                f"   (repeat for each item - write ONE item at a time)\n"
                f"3. local-file_write_json_chunk(path=\"output.json\", chunk_type=\"end\", array_key=\"items\")\n"
                f"```\n\n"
                f"**For plain text, use `local-file_append`:**\n"
                f"```\n"
                f"local-file_append(path=\"output.txt\", content=\"first part...\")\n"
                f"local-file_append(path=\"output.txt\", content=\"second part...\")\n"
                f"```\n\n"
                f"These tools write incrementally, avoiding max_tokens limit issues."
            )
            logger.error(error_msg)
            raise ModelBehaviorError(error_msg) from e
        
        if _debug.DONT_LOG_TOOL_DATA:
            logger.debug(f"Invalid JSON input for tool {tool.name}")
        else:
            logger.debug(f"Invalid JSON input for tool {tool.name}: {input_json}")
        raise ModelBehaviorError(
            f"Invalid JSON input for tool {tool.name}: {input_json}"
        ) from e

    if _debug.DONT_LOG_TOOL_DATA:
        logger.debug(f"Invoking MCP tool {tool.name}")
    else:
        logger.debug(f"Invoking MCP tool {tool.name} with input {input_json}")

    try:
        result = await server.call_tool(tool.name, json_data)
    except Exception as e:
        logger.error(f"Error invoking MCP tool {tool.name}: {e}")
        raise AgentsException(f"Error invoking MCP tool {tool.name}: {e}") from e

    if _debug.DONT_LOG_TOOL_DATA:
        logger.debug(f"MCP tool {tool.name} completed.")
    else:
        logger.debug(f"MCP tool {tool.name} returned {result}")

    # The MCP tool result is a list of content items, whereas OpenAI tool outputs are a single
    # string. We'll try to convert.
    if len(result.content) == 1:
        tool_output = result.content[0].model_dump_json()
    elif len(result.content) > 1:
        tool_output = json.dumps([item.model_dump() for item in result.content])
    else:
        # logger.error(f"Errored MCP tool result: {result}")
        tool_output = "[]" # Returning empty is a reasonable value

    current_span = get_current_span()
    if current_span:
        if isinstance(current_span.span_data, FunctionSpanData):
            current_span.span_data.output = tool_output
            current_span.span_data.mcp_data = {
                "server": server.name,
            }
        else:
            logger.warning(
                f"Current span is not a FunctionSpanData, skipping tool output: {current_span}"
            )

    # this is a very temp solution!
    if len(tool_output) > MAX_SINGLE_TURN_RETURN_CHARS:
        original_length = len(tool_output)

        logger.warning(f"Tool output is too long, return truncated one.")
        tool_short_uuid = shortuuid.uuid()

        agent_workspace = context.context.get('_agent_workspace', '.')
        agent_workspace = os.path.abspath(agent_workspace)
        overlong_toolcall_save_dir = os.path.join(agent_workspace, '.overlong_tool_outputs')
        os.makedirs(overlong_toolcall_save_dir, exist_ok=True)

        # save the original tool output to a file
        with open(os.path.join(overlong_toolcall_save_dir, f"{tool_short_uuid}.json"), "w", encoding="utf-8") as f:
            f.write(tool_output)
        logger.warning(f"Tool output saved to {os.path.join(overlong_toolcall_save_dir, f'{tool_short_uuid}.json')}")
        
        tool_output = tool_output[:MAX_SINGLE_TURN_RETURN_CHARS] + \
            f" ...\n\n(The output of the tool call (shortuuid identifier: {tool_short_uuid}) is too long! Only the first {MAX_SINGLE_TURN_RETURN_CHARS} characters are shown here. The original output length is {original_length} characters. The full output has been saved to the file {os.path.join(overlong_toolcall_save_dir, f'{tool_short_uuid}.json')}. Please check this file carefully, as it may be very long!)"

    return tool_output

# Replace method
MCPUtil.invoke_mcp_tool = my_invoke_mcp_tool
# Must replace the one above first
MCPUtil.to_function_tool = my_to_function_tool
