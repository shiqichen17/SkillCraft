# direct_exec.py
# Tool for direct Python script execution without skill management
# This is a simplified version for direct-exec mode

import json
import os
import traceback
import asyncio
import hashlib
from datetime import datetime
from typing import Any, List, Dict, Optional
from agents.tool import FunctionTool, RunContextWrapper

# Import the ToolBridge and ToolCallQueue from skill_cache for tool access
from utils.aux_tools.skill_cache import ToolBridge, ToolCallQueue


# Global execution history for current session
_exec_history: List[Dict] = []


def _generate_script_id(script_code: str) -> str:
    """Generate a short unique ID for a script based on its content."""
    hash_obj = hashlib.md5(script_code.encode('utf-8'))
    return hash_obj.hexdigest()[:8]


def _save_script_to_workspace(workspace: str, script_id: str, script_code: str, 
                               result: Dict, execution_index: int) -> str:
    """
    Save script content and result to workspace for logging.
    
    Returns the path to the saved script file.
    """
    # Create direct_exec_logs directory in workspace
    logs_dir = os.path.join(workspace, "direct_exec_logs")
    os.makedirs(logs_dir, exist_ok=True)
    
    # Save script content
    script_filename = f"script_{execution_index:03d}_{script_id}.py"
    script_path = os.path.join(logs_dir, script_filename)
    with open(script_path, 'w', encoding='utf-8') as f:
        f.write(f"# Script ID: {script_id}\n")
        f.write(f"# Execution Index: {execution_index}\n")
        f.write(f"# Timestamp: {datetime.now().isoformat()}\n")
        f.write(f"# Status: {result.get('status', 'unknown')}\n")
        f.write("#" + "="*60 + "\n\n")
        f.write(script_code)
    
    # Save result
    result_filename = f"result_{execution_index:03d}_{script_id}.json"
    result_path = os.path.join(logs_dir, result_filename)
    with open(result_path, 'w', encoding='utf-8') as f:
        # Make result JSON serializable
        serializable_result = _make_serializable(result)
        json.dump(serializable_result, f, indent=2, ensure_ascii=False)
    
    return script_path


def _make_serializable(obj: Any) -> Any:
    """Convert an object to JSON-serializable format."""
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj
    elif isinstance(obj, (list, tuple)):
        return [_make_serializable(item) for item in obj]
    elif isinstance(obj, dict):
        return {str(k): _make_serializable(v) for k, v in obj.items()}
    else:
        return str(obj)


def _update_exec_history(workspace: str, history_entry: Dict):
    """Update the execution history file in workspace."""
    global _exec_history
    _exec_history.append(history_entry)
    
    # Save to workspace
    logs_dir = os.path.join(workspace, "direct_exec_logs")
    os.makedirs(logs_dir, exist_ok=True)
    
    history_path = os.path.join(logs_dir, "exec_history.json")
    
    # Calculate summary statistics
    total = len(_exec_history)
    success_count = sum(1 for e in _exec_history if e.get('status') == 'success')
    error_count = total - success_count
    
    summary = {
        "total_executions": total,
        "successful": success_count,
        "failed": error_count,
        "success_rate": round(success_count / total * 100, 2) if total > 0 else 0,
        "last_updated": datetime.now().isoformat(),
        "executions": _exec_history
    }
    
    with open(history_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)


def reset_exec_history():
    """Reset the execution history (called at start of new task)."""
    global _exec_history
    _exec_history = []


def get_exec_stats() -> Dict:
    """Get current execution statistics."""
    global _exec_history
    total = len(_exec_history)
    success_count = sum(1 for e in _exec_history if e.get('status') == 'success')
    
    return {
        "total_executions": total,
        "successful": success_count,
        "failed": total - success_count,
        "success_rate": round(success_count / total * 100, 2) if total > 0 else 0
    }


async def on_exec_script_invoke(context: RunContextWrapper, params_str: str) -> Any:
    """
    Execute a Python script directly and return the result.
    
    Unlike execute_skill, this tool:
    - Does NOT require saving a skill first
    - Does NOT take args parameter (parameters should be hardcoded in script)
    - Executes the script immediately and returns result
    
    Flow:
    1. Start a queue processor task that runs in the main event loop
    2. Run the script in a thread pool
    3. When the script calls call_tool(), it puts a request in the queue
    4. The queue processor executes the tool call and returns the result
    5. The script thread waits for and receives the result
    """
    try:
        params = json.loads(params_str)
    except json.JSONDecodeError as e:
        return {
            "status": "error",
            "error": f"Invalid JSON in parameters: {str(e)}",
            "params_str_preview": params_str[:200] if len(params_str) > 200 else params_str
        }
    
    script_code = params.get("script_code", "")
    
    if not script_code:
        return {
            "status": "error",
            "error": "No script_code provided"
        }

    # Get workspace, MCP manager, and local tools from shared context
    ctx = context.context if hasattr(context, 'context') and context.context is not None else {}
    workspace = ctx.get("_agent_workspace", ".")
    mcp_manager = ctx.get("_mcp_manager")  # Get MCP manager for MCP tool access
    local_tools = ctx.get("_local_tools", [])  # Get local tools for local- tool access
    
    # Generate script ID and execution index for logging
    script_id = _generate_script_id(script_code)
    execution_index = len(_exec_history) + 1
    start_time = datetime.now()
    
    # Get the current event loop for the queue processor
    loop = asyncio.get_running_loop()
    
    # Create tool bridge and queue
    # Tool bridge is available if we have either MCP manager or local tools
    has_tools = mcp_manager is not None or len(local_tools) > 0
    
    # Direct exec mode doesn't support script nesting (no skills)
    tool_bridge = ToolBridge(
        mcp_manager, workspace, local_tools, 
        allow_skill_nesting=False,  # No nesting in direct exec mode
        max_nesting_depth=1,
        current_nesting_depth=0
    ) if has_tools else None
    tool_queue = ToolCallQueue() if has_tools else None
    
    if tool_bridge and tool_queue:
        tool_bridge._tool_queue = tool_queue
        # Start the queue processor - it runs in the main event loop
        tool_queue.start_processor(loop, tool_bridge._call_tool_async)
    
    try:
        # Build execution namespace
        exec_namespace = {}
        
        # Add built-in functions to the namespace
        exec_namespace['__builtins__'] = __builtins__
        
        # Add common Python modules
        import re
        import json as json_module
        import os as os_module
        exec_namespace['re'] = re
        exec_namespace['json'] = json_module
        exec_namespace['os'] = os_module
        
        # Inject tool bridge if available
        if tool_bridge:
            exec_namespace['call_tool'] = tool_bridge.call_tool
            exec_namespace['WORKSPACE'] = workspace

        # ===== RUN EXEC IN THREAD POOL =====
        def run_script():
            """Execute the script in a worker thread."""
            exec(script_code, exec_namespace)
            return exec_namespace.get('result', 'Script executed successfully (no result variable set)')
        
        # Use run_in_executor to run the script in a thread pool
        result = await loop.run_in_executor(None, run_script)
        
        end_time = datetime.now()
        duration_ms = (end_time - start_time).total_seconds() * 1000

        return_value = {
            "status": "success",
            "result": result,
            "tools_enabled": has_tools
        }
        
        # Log execution to workspace
        if workspace:
            _save_script_to_workspace(workspace, script_id, script_code, return_value, execution_index)
            _update_exec_history(workspace, {
                "execution_index": execution_index,
                "script_id": script_id,
                "status": "success",
                "timestamp": start_time.isoformat(),
                "duration_ms": round(duration_ms, 2),
                "script_lines": len(script_code.split('\n')),
                "result_preview": str(result)[:200] if result else None
            })
        
        return return_value

    except Exception as e:
        error_msg = str(e)
        tb = traceback.format_exc()
        
        # Extract detailed error information
        error_type = type(e).__name__
        
        # Find the line in the script that caused the error
        error_line = None
        error_line_content = None
        script_lines = script_code.split('\n')
        
        # Parse traceback to find line number in <string> (the script)
        import re as re_module
        line_match = re_module.search(r'File "<string>", line (\d+)', tb)
        if line_match:
            error_line = int(line_match.group(1))
            if 1 <= error_line <= len(script_lines):
                error_line_content = script_lines[error_line - 1].strip()
        
        end_time = datetime.now()
        duration_ms = (end_time - start_time).total_seconds() * 1000
        
        # Build comprehensive error report
        error_report = {
            "status": "error",
            "error_type": error_type,
            "error_message": error_msg,
            "error_line": error_line,
            "error_line_content": error_line_content,
            "full_traceback": tb,
            "script_code": script_code,  # Include full script for debugging
            "tools_enabled": has_tools,
            "debugging_hints": [
                f"Error type: {error_type}",
                f"Error occurred at line {error_line}: {error_line_content}" if error_line else "Could not determine error line",
                "Check if all required keys exist in the data structure",
                "Verify tool return types match your expectations",
                "Use json.loads() only on strings, not on already-parsed dicts",
            ]
        }
        
        # Log failed execution to workspace
        if workspace:
            _save_script_to_workspace(workspace, script_id, script_code, error_report, execution_index)
            _update_exec_history(workspace, {
                "execution_index": execution_index,
                "script_id": script_id,
                "status": "error",
                "timestamp": start_time.isoformat(),
                "duration_ms": round(duration_ms, 2),
                "script_lines": len(script_code.split('\n')),
                "error_type": error_type,
                "error_message": error_msg[:200],
                "error_line": error_line
            })
        
        return error_report
    finally:
        # Clean up the queue processor
        if tool_queue:
            tool_queue.stop_processor()


# Define the exec_script tool
tool_exec_script = FunctionTool(
    name='local-exec_script',
    description='''Execute a Python script directly and return the result.

**How it works:**
1. Pass the complete Python script code
2. The script runs with hardcoded parameters (no args needed)
3. Returns the value of the 'result' variable

**Return Format:**
```python
{
    "status": "success",  # or "error"
    "result": { ... },    # The actual data (from 'result' variable)
}
```

**CRITICAL: call_tool() returns Python objects directly - NO JSON string parsing needed!**
- local-* API tools return dict directly (e.g., {"success": True, "data": {...}})
- filesystem tools return string content directly
- All results can be used immediately without json.loads()

**Key Rules:**
1. Use `call_tool('server-tool_name', arg1=val1)` for ALL tool calls
2. Return values are Python objects - use .get() for dicts directly
3. **MUST set a 'result' variable** - this is what gets returned
4. Parameters should be **hardcoded** in the script (not passed as args)
5. Available modules: `call_tool()`, `json`, `re`, `os`

**Example: Fetch and process data from multiple sources**
```python
local-exec_script({
  "script_code": """
# Hardcode the items to process
items = ["item1", "item2", "item3"]

results = []
for item in items:
    # Fetch data using call_tool
    data = call_tool('local-some_api_tool', item_id=item)
    
    # Process the data (data is already a dict)
    processed = {
        'id': item,
        'value': data.get('value', 0),
        'name': data.get('name', 'Unknown')
    }
    results.append(processed)

# MUST set result variable
result = {
    'total_items': len(results),
    'items': results
}
"""
})
```

**When to use exec_script vs individual tool calls:**
- Use exec_script when you need to process multiple items in a single operation
- Use exec_script when you want to minimize context token usage
- Use individual tool calls when you need to inspect intermediate results
''',
    params_json_schema={
        "type": "object",
        "properties": {
            "script_code": {
                "type": "string",
                "description": "The Python script code to execute. Must set a 'result' variable."
            }
        },
        "required": ["script_code"]
    },
    on_invoke_tool=on_exec_script_invoke
)

# Export tools as a list for easy import
direct_exec_tools = [tool_exec_script]
