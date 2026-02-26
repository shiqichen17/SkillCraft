# stdio_servers/bash_server.py
# -*- coding: utf-8 -*-
import json
import os
from typing import Any
from agents.tool import FunctionTool, RunContextWrapper
from time import sleep

async def on_sleep_tool_invoke(context: RunContextWrapper, params_str: str) -> Any:
    params = json.loads(params_str)
    seconds = params.get("seconds", 1)
    sleep(seconds)
    return f"has slept {seconds} seconds, wake up!"

tool_sleep = FunctionTool(
    name='local-sleep',
    description='''Sleep for a specified duration.

**Input:** seconds (float) - Number of seconds to sleep

**Returns:** str - Message confirming sleep completion''',
    params_json_schema={
        "type": "object",
        "properties": {
            "seconds": {
                "type": "number",
                "description": 'the number of seconds to sleep',
            },
        },
        "required": ["seconds"]
    },
    on_invoke_tool=on_sleep_tool_invoke
)

async def on_done_tool_invoke(context: RunContextWrapper, params_str: str) -> Any:
    # Set a flag in the context to signal that claim_done was called
    # This allows the task agent to detect termination even if the runner
    # processes multiple turns before returning
    print(f"\033[92m[DEBUG claim_done] on_done_tool_invoke called!\033[0m", flush=True)
    print(f"\033[92m[DEBUG claim_done] context type: {type(context)}\033[0m", flush=True)
    print(f"\033[92m[DEBUG claim_done] hasattr(context, 'context'): {hasattr(context, 'context')}\033[0m", flush=True)
    
    if hasattr(context, 'context') and context.context is not None:
        context.context['_claim_done_called'] = True
        print(f"\033[92m[DEBUG claim_done] Set _claim_done_called = True in context\033[0m", flush=True)
        print(f"\033[92m[DEBUG claim_done] context.context id: {id(context.context)}\033[0m", flush=True)
    else:
        print(f"\033[91m[DEBUG claim_done] WARNING: Could not set flag - context.context is None or missing!\033[0m", flush=True)
    
    return "you have claimed the task is done!"

tool_done = FunctionTool(
    name='local-claim_done',
    description='''Claim the task is complete.

**Input:** None

**Returns:** str - Confirmation message''',
    params_json_schema={
        "type": "object",
        "properties": {
        },
    },
    on_invoke_tool=on_done_tool_invoke
)


# ============ FILE CHUNKED WRITING TOOLS ============
# These tools help handle output truncation by allowing incremental file writes

async def on_file_append_invoke(context: RunContextWrapper, params_str: str) -> Any:
    """
    Append content to a file. Creates the file if it doesn't exist.
    Useful for building large files incrementally when output might be truncated.
    """
    params = json.loads(params_str)
    filepath = params.get("path", "")
    content = params.get("content", "")
    
    if not filepath:
        return {"error": "Missing required parameter: path"}
    
    # Get workspace from context if available
    workspace = None
    if hasattr(context, 'context') and context.context is not None:
        workspace = context.context.get('workspace_path')
    
    # Resolve relative paths
    if workspace and not os.path.isabs(filepath):
        filepath = os.path.join(workspace, filepath)
    
    try:
        # Create parent directories if needed
        parent_dir = os.path.dirname(filepath)
        if parent_dir and not os.path.exists(parent_dir):
            os.makedirs(parent_dir, exist_ok=True)
        
        # Append to file
        with open(filepath, 'a', encoding='utf-8') as f:
            f.write(content)
        
        # Get current file size
        file_size = os.path.getsize(filepath)
        
        return {
            "success": True,
            "message": f"Successfully appended {len(content)} characters to {filepath}",
            "total_file_size": file_size,
            "appended_length": len(content)
        }
    except Exception as e:
        return {"error": f"Failed to append to file: {str(e)}"}

tool_file_append = FunctionTool(
    name='local-file_append',
    description='''Append content to a file. Creates the file if it doesn't exist.

**Input:** path (str), content (str)

**Returns:** dict - {"success": bool, "path": str, "bytes_written": int, "total_size": int}
    
USE THIS TOOL WHEN:
- Your output was truncated and you need to continue writing
- You need to build a large JSON/text file incrementally
- Writing in multiple steps to avoid max_tokens limit

CHUNKED JSON WRITING STRATEGY:
1. First call: write opening bracket and initial content
   local-file_append(path="result.json", content='{\n  "items": [\n')
2. Middle calls: append each item
   local-file_append(path="result.json", content='    {"name": "item1"},\n')
3. Final call: close the structure
   local-file_append(path="result.json", content='  ]\n}')

IMPORTANT: Plan your JSON structure to be appendable!''',
    params_json_schema={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path to the file (relative to workspace or absolute)"
            },
            "content": {
                "type": "string",
                "description": "Content to append to the file"
            }
        },
        "required": ["path", "content"]
    },
    on_invoke_tool=on_file_append_invoke
)


async def on_file_write_json_chunk_invoke(context: RunContextWrapper, params_str: str) -> Any:
    """
    Write a chunk of a JSON array/object to a file with automatic structure handling.
    Manages opening/closing brackets automatically for valid JSON.
    """
    params = json.loads(params_str)
    filepath = params.get("path", "")
    chunk_type = params.get("chunk_type", "item")  # "start", "item", "end"
    content = params.get("content", "")
    array_key = params.get("array_key", None)  # e.g., "items" for {"items": [...]}
    
    if not filepath:
        return {"error": "Missing required parameter: path"}
    
    # Get workspace from context if available
    workspace = None
    if hasattr(context, 'context') and context.context is not None:
        workspace = context.context.get('workspace_path')
    
    # Resolve relative paths
    if workspace and not os.path.isabs(filepath):
        filepath = os.path.join(workspace, filepath)
    
    try:
        # Create parent directories if needed
        parent_dir = os.path.dirname(filepath)
        if parent_dir and not os.path.exists(parent_dir):
            os.makedirs(parent_dir, exist_ok=True)
        
        if chunk_type == "start":
            # Initialize JSON structure
            if array_key:
                initial = f'{{\n  "{array_key}": [\n'
            else:
                initial = '[\n'
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(initial)
            return {
                "success": True,
                "message": f"Started JSON file: {filepath}",
                "chunk_type": "start",
                "next_action": "Add items with chunk_type='item', then close with chunk_type='end'"
            }
        
        elif chunk_type == "item":
            # Read current content to check if we need a comma
            needs_comma = False
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    current = f.read()
                    # Check if there's already content after the opening bracket
                    stripped = current.rstrip()
                    if stripped and not stripped.endswith('[') and not stripped.endswith(','):
                        needs_comma = True
            
            with open(filepath, 'a', encoding='utf-8') as f:
                if needs_comma:
                    f.write(',\n')
                # Indent the content
                indented = '    ' + content.replace('\n', '\n    ')
                f.write(indented)
            
            return {
                "success": True,
                "message": "Added item to JSON array",
                "chunk_type": "item"
            }
        
        elif chunk_type == "end":
            # Close JSON structure
            with open(filepath, 'a', encoding='utf-8') as f:
                if array_key:
                    f.write('\n  ]\n}')
                else:
                    f.write('\n]')
            
            # Validate the final JSON
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    json.load(f)
                valid = True
            except json.JSONDecodeError as e:
                valid = False
                return {
                    "success": False,
                    "error": f"Final JSON is invalid: {str(e)}",
                    "chunk_type": "end"
                }
            
            file_size = os.path.getsize(filepath)
            return {
                "success": True,
                "message": f"Completed JSON file: {filepath}",
                "chunk_type": "end",
                "total_file_size": file_size,
                "json_valid": valid
            }
        
        else:
            return {"error": f"Invalid chunk_type: {chunk_type}. Use 'start', 'item', or 'end'"}
    
    except Exception as e:
        return {"error": f"Failed to write JSON chunk: {str(e)}"}

tool_file_write_json_chunk = FunctionTool(
    name='local-file_write_json_chunk',
    description='''Write JSON content in chunks to avoid truncation. Automatically handles commas and brackets.

**Input:** path (str), chunk_type (str: "start"|"item"|"end"), content (str, for "item"), array_key (str, optional)

**Returns:** dict - {"success": bool, "path": str, "chunk_type": str, "message": str}

USAGE PATTERN:
1. Start: local-file_write_json_chunk(path="output.json", chunk_type="start", array_key="results")
2. Items: local-file_write_json_chunk(path="output.json", chunk_type="item", content='{"id": 1, "data": "..."}')
3. End:   local-file_write_json_chunk(path="output.json", chunk_type="end", array_key="results")

This produces valid JSON: {"results": [{"id": 1, "data": "..."}, ...]}

WHEN TO USE:
- When you need to write a large JSON array
- When your output might be truncated due to max_tokens limit
- When processing items one at a time''',
    params_json_schema={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path to the JSON file"
            },
            "chunk_type": {
                "type": "string",
                "enum": ["start", "item", "end"],
                "description": "Type of chunk: 'start' to initialize, 'item' to add content, 'end' to close"
            },
            "content": {
                "type": "string",
                "description": "JSON content for 'item' type (will be added to the array)"
            },
            "array_key": {
                "type": "string",
                "description": "Optional key for wrapping array in object, e.g., 'items' creates {\"items\": [...]}"
            }
        },
        "required": ["path", "chunk_type"]
    },
    on_invoke_tool=on_file_write_json_chunk_invoke
)


if __name__ == "__main__":
    pass
