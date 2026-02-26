# skill_cache.py
# Tool for saving and reusing tool call skills with tool access
import json
import os
import ast
import traceback
import asyncio
import threading
import queue
import logging
from typing import Any, List, Dict, Optional, Callable
from agents.tool import FunctionTool, RunContextWrapper
from utils.tool_name_resolver import normalize_tool_name_for_skill

logger = logging.getLogger(__name__)


# Tools that should be blocked from being called within skills to prevent recursion
BLOCKED_TOOLS = {
    'local-save_skill',
    'local-execute_skill', 
    'local-get_skill',
    'local-list_skills',
}


def _get_skill_cache_path(context: RunContextWrapper) -> str:
    """
    Get the path to skill_cache.json file.
    
    Supports cross-task mode by checking for a custom cache path in context.
    Falls back to workspace/skill_cache.json if not specified.
    
    Args:
        context: The RunContextWrapper containing shared context
        
    Returns:
        Path to the skill_cache.json file
    """
    ctx = context.context if hasattr(context, 'context') and context.context is not None else {}
    
    # Check for custom cache path (used in cross-task mode)
    custom_cache_path = ctx.get("_skill_cache_path")
    if custom_cache_path:
        return custom_cache_path
    
    # Default: workspace/skill_cache.json
    workspace = ctx.get("_agent_workspace", ".")
    return os.path.join(workspace, "skill_cache.json")


def _infer_schema(value, depth: int = 0, max_depth: int = 3) -> str:
    """
    Infer a schema string from a Python value, similar to tool description format.
    
    Args:
        value: The value to analyze
        depth: Current recursion depth
        max_depth: Maximum recursion depth to prevent infinite loops
        
    Returns:
        Schema string like {"key": str, "nested": {"a": int}}
    """
    if depth > max_depth:
        return "..."
    
    if value is None:
        return "null"
    elif isinstance(value, bool):
        return "bool"
    elif isinstance(value, int):
        return "int"
    elif isinstance(value, float):
        return "float"
    elif isinstance(value, str):
        return "str"
    elif isinstance(value, list):
        if not value:
            return "[]"
        # Sample first element to infer list item type
        item_schema = _infer_schema(value[0], depth + 1, max_depth)
        return f"[{item_schema}]"
    elif isinstance(value, dict):
        if not value:
            return "{}"
        # Build dict schema
        parts = []
        for k, v in list(value.items())[:8]:  # Limit to 8 keys
            v_schema = _infer_schema(v, depth + 1, max_depth)
            parts.append(f'"{k}": {v_schema}')
        schema = "{" + ", ".join(parts)
        if len(value) > 8:
            schema += ", ..."
        schema += "}"
        return schema
    else:
        return type(value).__name__


def _update_skill_execution_stats(cache_file: str, skill_name: str, success: bool, error_msg: str = None, 
                                     result_value: any = None, input_args: dict = None):
    """
    Update execution statistics for a skill.
    
    Args:
        cache_file: Path to the skill cache file
        skill_name: Name of the skill
        success: Whether the execution was successful
        error_msg: Error message if execution failed
        result_value: The actual result value (used to infer output schema on success)
        input_args: The input arguments dict (used to infer input schema on success)
    """
    if not os.path.exists(cache_file):
        return
    
    try:
        with open(cache_file, 'r', encoding='utf-8') as f:
            cache = json.load(f)
        
        skill = cache.get("skills", {}).get(skill_name)
        if not skill:
            return
        
        # Initialize execution_stats if not present
        if "execution_stats" not in skill:
            skill["execution_stats"] = {
                "total_executions": 0,
                "successful_executions": 0,
                "failed_executions": 0,
                "last_execution_status": None,
                "last_execution_error": None
            }
        
        stats = skill["execution_stats"]
        stats["total_executions"] += 1
        
        if success:
            stats["successful_executions"] += 1
            stats["last_execution_status"] = "success"
            stats["last_execution_error"] = None
            
            # Infer and save output schema from actual result (only on first success or if not set)
            if result_value is not None and "output_schema" not in skill:
                skill["output_schema"] = _infer_schema(result_value)
            
            # Infer and save input schema from actual args (only on first success or if not set)
            if input_args and "input_schema" not in skill:
                # Build input schema: {param_name: type}
                input_schema_parts = []
                for param_name, param_value in input_args.items():
                    param_type = _infer_schema(param_value, max_depth=1)  # Shallow for inputs
                    input_schema_parts.append(f'"{param_name}": {param_type}')
                skill["input_schema"] = "{" + ", ".join(input_schema_parts) + "}"
        else:
            stats["failed_executions"] += 1
            stats["last_execution_status"] = "error"
            stats["last_execution_error"] = error_msg[:200] if error_msg else None  # Truncate long errors
        
        # Save updated cache (ensure directory exists)
        cache_dir = os.path.dirname(cache_file)
        if cache_dir:
            os.makedirs(cache_dir, exist_ok=True)
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache, f, indent=2, ensure_ascii=False)
            
    except Exception as e:
        # Silently fail - don't break execution just because stats update failed
        pass

# ============== QUEUE-BASED TOOL CALL BRIDGE ==============
# This solves the deadlock issue by using a request-response queue skill.
# The skill thread sends tool call requests to a queue, and the main event
# loop processes them and sends results back.

class ToolCallRequest:
    """A request for a tool call from a skill execution thread."""
    def __init__(self, tool_name: str, kwargs: dict):
        self.tool_name = tool_name
        self.kwargs = kwargs
        self.result_event = threading.Event()
        self.result: Any = None
        self.error: Optional[Exception] = None


class ToolCallQueue:
    """
    Queue-based bridge for tool calls from skill execution threads.
    
    This allows synchronous code in skill scripts to call async MCP tools
    without deadlocking the event loop.
    """
    def __init__(self):
        self.request_queue: queue.Queue[ToolCallRequest] = queue.Queue()
        self._processor_task: Optional[asyncio.Task] = None
        self._running = False
    
    def start_processor(self, loop: asyncio.AbstractEventLoop, call_tool_func: Callable):
        """Start the async processor that handles tool call requests."""
        if self._running:
            return
        self._running = True
        
        async def process_requests():
            """Continuously process tool call requests from the queue."""
            while self._running:
                try:
                    # Check queue with small timeout to allow cancellation
                    try:
                        request = self.request_queue.get_nowait()
                    except queue.Empty:
                        await asyncio.sleep(0.01)  # Small sleep to avoid busy-waiting
                        continue
                    
                    # Process the request
                    try:
                        result = await call_tool_func(request.tool_name, **request.kwargs)
                        request.result = result
                    except Exception as e:
                        request.error = e
                    finally:
                        request.result_event.set()  # Signal completion
                        
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    # Log but don't crash
                    print(f"[ToolCallQueue] Error processing request: {e}")
        
        self._processor_task = loop.create_task(process_requests())
    
    def stop_processor(self):
        """Stop the queue processor."""
        self._running = False
        if self._processor_task:
            self._processor_task.cancel()
    
    def call_tool_sync(self, tool_name: str, timeout: float = 600.0, **kwargs) -> Any:
        """
        Synchronously call a tool by queuing a request.
        
        This is called from skill execution threads.
        
        Args:
            tool_name: The tool name to call
            timeout: Maximum time to wait for result
            **kwargs: Tool arguments
            
        Returns:
            The tool call result
            
        Raises:
            RuntimeError: On timeout or tool call error
        """
        request = ToolCallRequest(tool_name, kwargs)
        self.request_queue.put(request)
        
        # Wait for result with timeout
        if not request.result_event.wait(timeout=timeout):
            raise RuntimeError(f"Tool call '{tool_name}' timed out after {timeout} seconds")
        
        if request.error:
            raise RuntimeError(f"Tool call '{tool_name}' failed: {str(request.error)}")
        
        return request.result


# ============== SKILL QUALITY CONFIG ==============
# Maximum skill iterations before warning (prevents infinite fix loops)
MAX_SKILL_ITERATIONS = 3

# Low quality indicators - if result has too many of these, it's considered low quality
LOW_QUALITY_VALUES = {'Unknown', 'unknown', 'UNKNOWN', 'None', 'null', 'N/A', 'n/a', ''}


def check_result_quality(result: Any, depth: int = 0) -> Dict[str, Any]:
    """
    Analyze the quality of a skill execution result.
    
    Returns:
        Dict with:
        - is_low_quality: bool
        - total_fields: int
        - low_quality_fields: int
        - zero_numeric_fields: int
        - details: list of issues found
    """
    if depth > 5:  # Prevent infinite recursion
        return {"is_low_quality": False, "total_fields": 0, "low_quality_fields": 0, "zero_numeric_fields": 0, "details": []}
    
    total_fields = 0
    low_quality_fields = 0
    zero_numeric_fields = 0
    details = []
    
    if isinstance(result, dict):
        for key, value in result.items():
            total_fields += 1
            
            # Check for low quality string values
            if isinstance(value, str) and value in LOW_QUALITY_VALUES:
                low_quality_fields += 1
                details.append(f"'{key}' is '{value}'")
            
            # Check for zero numeric values (often indicates extraction failure)
            elif isinstance(value, (int, float)) and value == 0:
                zero_numeric_fields += 1
                details.append(f"'{key}' is 0")
            
            # Recursively check nested structures
            elif isinstance(value, (dict, list)):
                nested = check_result_quality(value, depth + 1)
                low_quality_fields += nested["low_quality_fields"]
                zero_numeric_fields += nested["zero_numeric_fields"]
                total_fields += nested["total_fields"] - 1  # Subtract 1 to avoid double counting
                details.extend(nested["details"])
    
    elif isinstance(result, list):
        for i, item in enumerate(result):
            nested = check_result_quality(item, depth + 1)
            total_fields += nested["total_fields"]
            low_quality_fields += nested["low_quality_fields"]
            zero_numeric_fields += nested["zero_numeric_fields"]
            details.extend(nested["details"])
    
    elif isinstance(result, str) and result in LOW_QUALITY_VALUES:
        total_fields = 1
        low_quality_fields = 1
        details.append(f"Result is '{result}'")
    
    # Determine if result is low quality
    # More than 50% of fields are Unknown/None, or all numeric fields are 0
    problematic_fields = low_quality_fields + zero_numeric_fields
    is_low_quality = (
        (total_fields > 0 and problematic_fields / total_fields > 0.5) or
        (total_fields > 2 and low_quality_fields >= total_fields - 1)  # Almost all fields are Unknown
    )
    
    return {
        "is_low_quality": is_low_quality,
        "total_fields": total_fields,
        "low_quality_fields": low_quality_fields,
        "zero_numeric_fields": zero_numeric_fields,
        "details": details[:5]  # Limit to first 5 issues
    }


class ToolBridge:
    """
    Bridge class to enable tool calls within skill execution.
    
    This uses a queue-based mechanism to allow synchronous skill code
    to call async MCP tools without deadlocking.
    
    Supports both:
    - MCP server tools (e.g., 'filesystem-read_file')
    - Local function tools (e.g., 'local-gitlab_get_commits')
    """
    
    def __init__(self, mcp_manager, workspace: str, local_tools: List = None, 
                 allow_skill_nesting: bool = False, max_nesting_depth: int = 10,
                 current_nesting_depth: int = 0):
        """
        Initialize the tool bridge.
        
        Args:
            mcp_manager: The MCPServerManager instance with connected servers
            workspace: The agent workspace path
            local_tools: List of FunctionTool objects for local tools (e.g., gitlab_api_tools)
            allow_skill_nesting: If True, allows calling skill tools (execute_skill, etc.) 
                                   within skills. Used in cross-task mode for skill composition.
            max_nesting_depth: Maximum allowed skill nesting depth (default: 10)
            current_nesting_depth: Current nesting level (0 = top-level skill)
        """
        self.mcp_manager = mcp_manager
        self.workspace = workspace
        self._tool_queue: Optional[ToolCallQueue] = None
        self.allow_skill_nesting = allow_skill_nesting
        self.max_nesting_depth = max_nesting_depth
        self.current_nesting_depth = current_nesting_depth
        
        # Build a lookup dict for local tools by name
        self._local_tools: Dict[str, Any] = {}
        if local_tools:
            for tool in local_tools:
                if hasattr(tool, 'name'):
                    self._local_tools[tool.name] = tool
    
    async def _call_local_tool(self, tool_name: str, **kwargs) -> Any:
        """
        Call a local function tool (tools with 'local-' prefix).
        
        Args:
            tool_name: Full tool name (e.g., 'local-gitlab_get_commits')
            **kwargs: Tool arguments
            
        Returns:
            Tool call result (parsed from JSON if applicable)
        """
        if tool_name not in self._local_tools:
            available = list(self._local_tools.keys())
            raise ValueError(f"Local tool '{tool_name}' not found. Available local tools: {available}")
        
        tool = self._local_tools[tool_name]
        
        # Call the tool's on_invoke_tool handler
        # The handler expects (context, params_str) where params_str is a JSON string
        params_str = json.dumps(kwargs)
        
        # Create a minimal context (local tools usually don't need the full context)
        class MinimalContext:
            def __init__(self, workspace):
                self.workspace = workspace
        
        context = MinimalContext(self.workspace)
        
        # Call the async handler
        result = await tool.on_invoke_tool(context, params_str)
        
        # Return result as-is to maintain consistency with direct tool calls
        # Do NOT auto-parse JSON strings - let the skill code handle parsing
        # This ensures call_tool() behavior matches what Agent sees when calling tools directly
        return result
    
    async def _call_tool_async(self, tool_name: str, **kwargs) -> Any:
        """
        Async method to call a tool.
        
        Args:
            tool_name: Full tool name (e.g., 'filesystem-read_file', 'local-gitlab_get_commits')
            **kwargs: Tool arguments
            
        Returns:
            Tool call result
        """
        # === Tool name auto-correction using unified resolver ===
        # Get available local tools for resolution
        local_tool_names = set(self._local_tools.keys()) if self._local_tools else set()
        original_name = tool_name
        tool_name = normalize_tool_name_for_skill(tool_name, local_tool_names)
        if tool_name != original_name:
            logger.debug(f"Skill tool name corrected: '{original_name}' -> '{tool_name}'")
        
        # Check for blocked tools to prevent recursion (unless skill nesting is allowed)
        if tool_name in BLOCKED_TOOLS:
            if not self.allow_skill_nesting:
                raise ValueError(
                    f"Tool '{tool_name}' cannot be called from within a skill to prevent recursion. "
                    f"Blocked tools: {', '.join(BLOCKED_TOOLS)}. "
                    f"Note: Skill nesting is allowed in cross-task mode with --enable-skill-nesting."
                )
            # Check nesting depth limit
            if self.current_nesting_depth >= self.max_nesting_depth:
                raise RecursionError(
                    f"Skill nesting depth limit exceeded! Current depth: {self.current_nesting_depth}, "
                    f"Max allowed: {self.max_nesting_depth}. "
                    f"Adjust with --max-skill-nesting-depth if needed."
                )
        
        # ===== Handle local- prefixed tools =====
        if tool_name.startswith('local-'):
            return await self._call_local_tool(tool_name, **kwargs)
        
        # ===== Handle MCP server tools =====
        if not self.mcp_manager:
            raise RuntimeError("Tool manager not available in skill execution context")
        
        # Parse tool name to get server and tool
        # Tool names are formatted as: server_name-tool_name (e.g., 'filesystem-read_file', 'pdf-tools-get_pdf_info')
        # Note: Some server names contain hyphens (e.g., 'pdf-tools'), so we need smart parsing
        
        connected_servers = self.mcp_manager.get_all_connected_servers()
        
        # Normalize tool_name for SERVER matching only (lowercase for case-insensitive server lookup)
        normalized_tool_name = tool_name.replace('_', '-').lower()
        # Keep original tool name for extracting the actual MCP tool name (PRESERVE CASE)
        original_tool_name = tool_name.replace('_', '-')
        
        # Strategy: Find the longest matching server name prefix
        target_server = None
        actual_tool_name = None
        best_match_len = 0
        
        for server in connected_servers:
            # Normalize server name for matching
            server_name = server.name.lower().replace('_', '-').replace(' ', '-')
            
            # Check if tool_name starts with server_name followed by a separator
            prefix_with_sep = server_name + '-'
            if normalized_tool_name.startswith(prefix_with_sep):
                if len(server_name) > best_match_len:
                    best_match_len = len(server_name)
                    target_server = server
                    # Extract actual tool name from ORIGINAL (case-preserved) tool name
                    # Server name length is the same, just extract from original
                    remaining = original_tool_name[len(prefix_with_sep):]
                    actual_tool_name = remaining.replace('-', '_')
        
        # Fallback: try simple split if no server matched
        if not target_server:
            parts = tool_name.replace('_', '-').split('-', 1)
            if len(parts) >= 2:
                server_prefix = parts[0].lower()
                for server in connected_servers:
                    server_name = server.name.lower().replace('_', '-').replace(' ', '-')
                    if server_name == server_prefix or server_name.startswith(server_prefix):
                        target_server = server
                        # Use original case for tool name
                        original_parts = tool_name.replace('_', '-').split('-', 1)
                        actual_tool_name = original_parts[1].replace('-', '_')
                        break
        
        if not target_server:
            available = [s.name for s in connected_servers]
            raise ValueError(f"Could not find server for tool '{tool_name}'. Available servers: {available}")
        
        # Call the tool
        try:
            # NOTE: target_server can be either:
            # - Raw SDK server (_MCPServerWithClientSession) which expects tool_name=
            # - FilteredMCPServerWrapper which expects name=
            # Using positional arguments to be compatible with both
            result = await target_server.call_tool(actual_tool_name, kwargs)
            
            # ===== EXTRACT ACTUAL CONTENT FROM MCP RESULT =====
            # MCP tools return CallToolResult objects, we need to extract the actual content
            extracted = self._extract_tool_result(result)
            return extracted
        except Exception as e:
            raise RuntimeError(f"Error calling tool {tool_name}: {str(e)}")
    
    def _extract_tool_result(self, result: Any) -> Any:
        """
        Extract content from an MCP tool result in a format CONSISTENT with Agent direct calls.
        
        IMPORTANT: This method now returns the SAME format that the Agent sees when 
        calling tools directly. For MCP tools, this means returning a dict like:
        {"type": "text", "text": "...actual content..."}
        
        This ensures Skill code can use the same parsing logic as direct tool calls:
        ```python
        raw = call_tool('howtocook-...', query=dish_name)
        data = json.loads(raw.get("text"))  # Works the same as direct calls!
        ```
        
        Args:
            result: The raw result from target_server.call_tool()
            
        Returns:
            For MCP tools: dict with {"type": "text", "text": "..."} format
            For local tools: the result as-is
            
        Raises:
            RuntimeError: If no content can be extracted from the result
        """
        if result is None:
            raise RuntimeError(
                "Tool returned None. The tool call may have failed silently. "
                "Check if the file/resource exists and is accessible."
            )
        
        # Handle CallToolResult or similar objects with 'content' attribute (MCP protocol)
        if hasattr(result, 'content'):
            content = result.content
            
            # Check for isError flag
            if hasattr(result, 'isError') and result.isError:
                error_text = self._try_extract_text(content)
                raise RuntimeError(f"Tool returned error: {error_text or 'Unknown error'}")
            
            if content is None:
                if hasattr(result, 'text'):
                    return {"type": "text", "text": result.text}
                if hasattr(result, 'data'):
                    return {"type": "text", "text": json.dumps(result.data, ensure_ascii=False)}
                raise RuntimeError("MCP CallToolResult has None content")
            
            # ===== RETURN FORMAT CONSISTENT WITH AGENT DIRECT CALLS =====
            # Agent sees: result.content[0].model_dump_json() which is {"type": "text", "text": "..."}
            # We return the SAME format as a dict so Skill code can use .get("text")
            
            # Handle list of content items (most common MCP format)
            if isinstance(content, list) and len(content) > 0:
                first_item = content[0]
                
                # TextContent objects with text attribute
                if hasattr(first_item, 'text'):
                    return {
                        "type": getattr(first_item, 'type', 'text'),
                        "text": first_item.text
                    }
                
                # Dict format content items
                if isinstance(first_item, dict):
                    if 'text' in first_item:
                        return {
                            "type": first_item.get('type', 'text'),
                            "text": first_item['text']
                        }
                    # Return the dict wrapped in text format
                    return {
                        "type": "text",
                        "text": json.dumps(first_item, ensure_ascii=False)
                    }
                
                # String item
                if isinstance(first_item, str):
                    return {"type": "text", "text": first_item}
                
                # Fallback: convert to string
                return {"type": "text", "text": str(first_item)}
            
            # Single TextContent object
            if hasattr(content, 'text'):
                return {
                    "type": getattr(content, 'type', 'text'),
                    "text": content.text
                }
            
            # Dict content
            if isinstance(content, dict):
                if 'text' in content:
                    return {
                        "type": content.get('type', 'text'),
                        "text": content['text']
                    }
                return {"type": "text", "text": json.dumps(content, ensure_ascii=False)}
            
            # String content
            if isinstance(content, str):
                return {"type": "text", "text": content}
            
            # Fallback
            return {"type": "text", "text": str(content)}
        
        # For non-MCP results (e.g., local tools), return as-is (preserve original type)
        # This includes: dict, list, str, int, float, bool, etc.
        if isinstance(result, dict):
            # Check for error in dict
            if result.get('error') or result.get('isError'):
                raise RuntimeError(f"Tool returned error: {result.get('error', result)}")
        
        # Return the result directly - no type conversion
        return result
    
    def _try_extract_text(self, content: Any) -> Optional[str]:
        """
        Try to extract text from various content formats.
        
        Returns:
            Extracted text or None if extraction fails
        """
        if content is None:
            return None
        
        # Direct string
        if isinstance(content, str):
            return content if content else None
        
        # Object with text attribute (TextContent, etc.)
        if hasattr(content, 'text'):
            text = content.text
            return text if text else None
        
        # List of content items
        if isinstance(content, list):
            if len(content) == 0:
                return None
            
            texts = []
            for item in content:
                if item is None:
                    continue
                    
                # TextContent objects
                if hasattr(item, 'text'):
                    if item.text:
                        texts.append(item.text)
                # Dict format
                elif isinstance(item, dict):
                    if 'text' in item and item['text']:
                        texts.append(item['text'])
                    elif 'content' in item and item['content']:
                        texts.append(str(item['content']))
                # String items
                elif isinstance(item, str) and item:
                    texts.append(item)
                # Other types
                else:
                    str_item = str(item)
                    if str_item and str_item != 'None':
                        texts.append(str_item)
            
            if texts:
                return '\n'.join(texts)
            return None
        
        # Dict with text key
        if isinstance(content, dict):
            if 'text' in content and content['text']:
                return content['text']
            if 'content' in content:
                return self._try_extract_text(content['content'])
            # Return dict as JSON string if it has data
            if content:
                return json.dumps(content, ensure_ascii=False)
            return None
        
        # Fallback: convert to string
        str_content = str(content)
        return str_content if str_content and str_content != 'None' else None
    
    def call_tool(self, tool_name: str, **kwargs) -> Any:
        """
        Synchronous wrapper to call a tool from within skill execution.
        
        This method uses a queue to communicate with the main event loop,
        avoiding deadlock issues with async/thread interaction.
        
        Args:
            tool_name: Full tool name (e.g., 'filesystem-read_file')
            **kwargs: Tool arguments
            
        Returns:
            Tool call result (guaranteed non-None on success)
            
        Raises:
            ValueError: If trying to call a blocked skill tool (prevents recursion)
            RuntimeError: If the tool call fails or returns no content
        """
        # Check for blocked tools first (unless skill nesting is allowed)
        if tool_name in BLOCKED_TOOLS:
            if not self.allow_skill_nesting:
                raise ValueError(
                    f"Tool '{tool_name}' cannot be called from within a skill to prevent recursion. "
                    f"Blocked tools: {', '.join(BLOCKED_TOOLS)}"
                )
            # Check nesting depth limit
            if self.current_nesting_depth >= self.max_nesting_depth:
                raise RecursionError(
                    f"Maximum skill nesting depth ({self.max_nesting_depth}) exceeded. "
                    f"Current depth: {self.current_nesting_depth}. "
                    f"This prevents infinite recursion in skill composition."
                )
        
        # Use queue-based call if available
        if self._tool_queue:
            result = self._tool_queue.call_tool_sync(tool_name, timeout=600.0, **kwargs)
        else:
            raise RuntimeError("Tool queue not initialized. Cannot call tools from skill.")
        
        # ===== VALIDATE RESULT =====
        if result is None:
            raise RuntimeError(
                f"Tool '{tool_name}' returned no content. "
                f"Arguments: {kwargs}. "
                f"Check if the resource exists and is accessible."
            )
        
        if isinstance(result, str) and not result.strip():
            raise RuntimeError(
                f"Tool '{tool_name}' returned empty string. "
                f"Arguments: {kwargs}. "
                f"The file may be empty or the operation produced no output."
            )
        
        return result


async def on_save_skill_invoke(context: RunContextWrapper, params_str: str) -> Any:
    """Save a reusable skill as executable script."""
    params = json.loads(params_str)
    skill_name = params.get("skill_name")
    script_code = params.get("script_code")  # The actual executable code
    parameters = params.get("parameters", [])  # Parameter names for the script
    description = params.get("description", "")
    # Optional explicit schema (for cross-task reuse clarity)
    explicit_input_schema = params.get("input_schema")  # e.g., '{"project_path": "str"}'
    explicit_output_schema = params.get("output_schema")  # e.g., '{"name": "str", "count": "int"}'

    # ===== AUTO-FIX COMMON FORMATTING ISSUES =====
    # Convert escaped newlines to actual newlines (common LLM output issue)
    if script_code:
        # Fix escaped newlines: "\\n" literal string -> actual newline
        # This handles cases where LLM outputs literal backslash-n instead of newline
        if '\\n' in script_code and '\n' not in script_code:
            script_code = script_code.replace('\\n', '\n')
        # Also handle double-escaped (from JSON in JSON): "\\\\n" -> newline
        if '\\\\n' in script_code:
            script_code = script_code.replace('\\\\n', '\n')
        # Handle escaped tabs
        if '\\t' in script_code and '\t' not in script_code:
            script_code = script_code.replace('\\t', '\t')
        # Strip leading/trailing whitespace from the entire script
        script_code = script_code.strip()

    # ===== SYNTAX VALIDATION (Warning Only) =====
    # Check for Python syntax errors but still save the skill for debugging
    syntax_warning = None
    if script_code:
        try:
            ast.parse(script_code)
        except SyntaxError as e:
            error_line = e.lineno if e.lineno else "unknown"
            error_msg = e.msg if e.msg else "unknown error"
            # Extract the problematic line for context
            lines = script_code.split('\n')
            context_lines = []
            if e.lineno and e.lineno > 0:
                start = max(0, e.lineno - 2)
                end = min(len(lines), e.lineno + 1)
                for i in range(start, end):
                    prefix = ">>> " if i == e.lineno - 1 else "    "
                    context_lines.append(f"{prefix}{i+1}: {lines[i]}")
            
            syntax_warning = {
                "error_line": error_line,
                "error_msg": error_msg,
                "context": "\n".join(context_lines)
            }

    # Get workspace and cache file path from shared context
    ctx = context.context if hasattr(context, 'context') and context.context is not None else {}
    workspace = ctx.get("_agent_workspace", ".")
    cache_file = _get_skill_cache_path(context)

    # Load existing cache
    if os.path.exists(cache_file):
        with open(cache_file, 'r', encoding='utf-8') as f:
            cache = json.load(f)
    else:
        cache = {"skills": {}, "_iteration_counts": {}}
    
    # Ensure _iteration_counts exists
    if "_iteration_counts" not in cache:
        cache["_iteration_counts"] = {}

    # Track skill iterations (how many times this skill name has been saved/modified)
    base_name = skill_name.rstrip('0123456789').rstrip('_').rstrip('-')  # Remove version suffixes
    iteration_key = base_name
    cache["_iteration_counts"][iteration_key] = cache["_iteration_counts"].get(iteration_key, 0) + 1
    iteration_count = cache["_iteration_counts"][iteration_key]

    # Save skill with executable script
    skill_data = {
        "script_code": script_code,
        "parameters": parameters,
        "description": description,
        "saved_at": ctx.get("_context_meta", {}).get("current_turn", 0),
        "version": iteration_count
    }
    
    # Include explicit schema if provided (for cross-task clarity)
    if explicit_input_schema:
        skill_data["input_schema"] = explicit_input_schema
    if explicit_output_schema:
        skill_data["output_schema"] = explicit_output_schema
    
    # Include syntax warning if any (skill is still saved for debugging)
    if syntax_warning:
        skill_data["syntax_error"] = syntax_warning
    
    cache["skills"][skill_name] = skill_data

    # Write back to file (ensure directory exists)
    cache_dir = os.path.dirname(cache_file)
    if cache_dir:
        os.makedirs(cache_dir, exist_ok=True)
    with open(cache_file, 'w', encoding='utf-8') as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)

    # Build response with warnings if needed
    if syntax_warning:
        response = (
            f"⚠️ Skill '{skill_name}' saved with SYNTAX ERROR (for debugging).\n\n"
            f"Error at line {syntax_warning['error_line']}: {syntax_warning['error_msg']}\n"
            f"Code context:\n{syntax_warning['context']}\n\n"
            f"The skill was saved but will likely fail when executed. "
            f"Please fix the syntax and save again with a corrected version."
        )
    else:
        response = f"Skill '{skill_name}' saved successfully! You can now execute it with execute_skill or get the code with get_skill."
    
    if iteration_count >= MAX_SKILL_ITERATIONS:
        response += f"\n\n⚠️ WARNING: You have modified skills for '{base_name}' {iteration_count} times. "
        response += "If skills keep failing, consider:\n"
        response += "1. Processing the task directly without skills\n"
        response += "2. Simplifying the skill logic\n"
        response += "3. Testing with a simpler input first"
    
    return response


async def on_get_skill_invoke(context: RunContextWrapper, params_str: str) -> Any:
    """Get a saved skill's executable code."""
    params = json.loads(params_str)
    skill_name = params.get("skill_name")

    # Get cache file path (supports cross-task mode)
    cache_file = _get_skill_cache_path(context)

    if not os.path.exists(cache_file):
        return f"No skill cache found. You haven't saved any skills yet."

    with open(cache_file, 'r', encoding='utf-8') as f:
        cache = json.load(f)

    skill = cache.get("skills", {}).get(skill_name)

    if not skill:
        return f"Skill '{skill_name}' not found. Use list_skills to see available skills."

    return json.dumps(skill, indent=2, ensure_ascii=False)


async def on_list_skills_invoke(context: RunContextWrapper, params_str: str) -> Any:
    """List all saved executable skills with detailed information."""
    # Get cache file path (supports cross-task mode)
    cache_file = _get_skill_cache_path(context)

    if not os.path.exists(cache_file):
        return "No skills saved yet. When you identify a repeating task skill, save it with save_skill for reuse!"

    with open(cache_file, 'r', encoding='utf-8') as f:
        cache = json.load(f)

    skills = cache.get("skills", {})

    if not skills:
        return "No skills saved yet."

    result = format_skills_list(skills)
    return result


def format_skills_list(skills: Dict[str, Any], include_header: bool = True) -> str:
    """
    Format skills into a detailed list string.
    
    Args:
        skills: Dictionary of skill_name -> skill_data
        include_header: Whether to include the header line
        
    Returns:
        Formatted string with detailed skill information
    """
    if not skills:
        return "No skills available."
    
    lines = []
    if include_header:
        lines.append(f"📦 Available Skills ({len(skills)} total):")
        lines.append("")
    
    for name, info in skills.items():
        # Basic info
        description = info.get('description', 'No description')
        lines.append(f"### `{name}`")
        lines.append(f"**Description:** {description}")
        
        # Parameters (input) - prefer actual schema from execution, fallback to param names
        params = info.get('parameters', [])  # Always get params for later use
        input_schema = info.get('input_schema')
        if input_schema:
            lines.append(f"**Input:** `{input_schema}`")
        elif params:
            lines.append(f"**Input:** `{', '.join(params)}` (types inferred on first execution)")
        else:
            lines.append("**Input:** None")
        
        # Output schema - prefer actual schema from execution, fallback to code analysis
        output_schema = info.get('output_schema')
        if output_schema:
            lines.append(f"**Output Schema:** `{output_schema}`")
        else:
            # Fallback: analyze from script_code
            script_code = info.get('script_code', '')
            output_hint = _analyze_output_format(script_code)
            if output_hint:
                lines.append(f"**Output:** {output_hint} (estimated)")
        
        # Source level (for cross-task mode)
        source_level = info.get('source_level')
        if source_level:
            lines.append(f"**Source:** Created in level `{source_level}`")
        
        # Execution status
        execution_stats = info.get('execution_stats', {})
        if execution_stats:
            total = execution_stats.get('total_executions', 0)
            success = execution_stats.get('successful_executions', 0)
            failed = execution_stats.get('failed_executions', 0)
            last_status = execution_stats.get('last_execution_status', 'unknown')
            
            status_emoji = "✅" if last_status == "success" else ("❌" if last_status == "error" else "⚪")
            lines.append(f"**Execution History:** {total} total ({success} success, {failed} failed)")
            lines.append(f"**Last Execution:** {status_emoji} {last_status}")
        else:
            lines.append("**Execution History:** Not yet executed")
        
        # Usage example
        if params:
            args_example = ', '.join([f'"{p}": <value>' for p in params])
            lines.append(f"**Usage:** `local-execute_skill({{\"skill_name\": \"{name}\", \"args\": {{{args_example}}}}})`")
        else:
            lines.append(f"**Usage:** `local-execute_skill({{\"skill_name\": \"{name}\", \"args\": {{}}}})`")
        
        lines.append("")  # Empty line between skills
    
    return "\n".join(lines)


def _analyze_output_format(script_code: str) -> str:
    """
    Analyze the skill script to determine output format.
    
    Looks for the 'result = ' assignment to understand what the skill returns.
    """
    if not script_code:
        return ""
    
    # Try to find 'result = {...}' or 'result = [...]' skills
    import re
    
    # Look for result = { ... } (dictionary)
    dict_match = re.search(r'result\s*=\s*\{([^}]+)\}', script_code, re.DOTALL)
    if dict_match:
        # Extract keys from the dictionary
        content = dict_match.group(1)
        # Find quoted keys: 'key' or "key"
        keys = re.findall(r'["\'](\w+)["\']:\s*', content)
        if keys:
            return f"Dict with keys: `{', '.join(keys[:5])}`" + (", ..." if len(keys) > 5 else "")
    
    # Look for result = [ ... ] (list)
    if re.search(r'result\s*=\s*\[', script_code):
        return "List of items"
    
    # Look for result = call_tool(...) (direct tool result)
    if re.search(r'result\s*=\s*call_tool\s*\(', script_code):
        return "Direct tool result"
    
    return "Custom format"


async def on_execute_skill_invoke(context: RunContextWrapper, params_str: str) -> Any:
    """
    Execute a saved skill with given arguments.
    
    This enhanced version uses a queue-based mechanism for tool calls,
    allowing skill code to call MCP tools without deadlocking.
    
    Flow:
    1. Start a queue processor task that runs in the main event loop
    2. Run the skill script in a thread pool
    3. When the script calls call_tool(), it puts a request in the queue
    4. The queue processor executes the tool call and returns the result
    5. The script thread waits for and receives the result
    """
    try:
        params = json.loads(params_str)
    except json.JSONDecodeError as e:
        return {
            "skill_name": "unknown",
            "status": "error",
            "error": f"Invalid JSON in parameters: {str(e)}",
            "params_str_preview": params_str[:200] if len(params_str) > 200 else params_str
        }
    
    skill_name = params.get("skill_name")
    args = params.get("args", {})  # Arguments to pass to the script

    # Get workspace, MCP manager, and local tools from shared context
    ctx = context.context if hasattr(context, 'context') and context.context is not None else {}
    workspace = ctx.get("_agent_workspace", ".")
    mcp_manager = ctx.get("_mcp_manager")  # Get MCP manager for MCP tool access
    local_tools = ctx.get("_local_tools", [])  # Get local tools for local- tool access
    cache_file = _get_skill_cache_path(context)  # Supports cross-task mode
    
    # Check if cross-task mode is enabled (allows skill nesting)
    is_cross_task = ctx.get("_cross_task_mode", False)
    
    # Skill nesting configuration
    allow_skill_nesting = ctx.get("_allow_skill_nesting", is_cross_task)  # Default: follows cross-task mode
    max_nesting_depth = ctx.get("_max_skill_nesting_depth", 10)  # Default: 10
    current_nesting_depth = ctx.get("_current_skill_nesting_depth", 0)  # Track current depth

    if not os.path.exists(cache_file):
        return {"error": "No skill cache found"}

    with open(cache_file, 'r', encoding='utf-8') as f:
        cache = json.load(f)

    skill = cache.get("skills", {}).get(skill_name)

    if not skill:
        return {"error": f"Skill '{skill_name}' not found"}

    script_code = skill.get("script_code", "")

    if not script_code:
        return {"error": f"Skill '{skill_name}' has no executable code"}

    # Get the current event loop for the queue processor
    loop = asyncio.get_running_loop()
    
    # Create tool bridge and queue
    # Tool bridge is available if we have either MCP manager or local tools
    has_tools = mcp_manager is not None or len(local_tools) > 0
    # Pass skill nesting configuration to tool bridge
    # Increment nesting depth by 1 for this execution level
    tool_bridge = ToolBridge(
        mcp_manager, workspace, local_tools, 
        allow_skill_nesting=allow_skill_nesting,
        max_nesting_depth=max_nesting_depth,
        current_nesting_depth=current_nesting_depth + 1  # +1 because we're entering a skill
    ) if has_tools else None
    tool_queue = ToolCallQueue() if has_tools else None
    
    if tool_bridge and tool_queue:
        tool_bridge._tool_queue = tool_queue
        # Start the queue processor - it runs in the main event loop
        tool_queue.start_processor(loop, tool_bridge._call_tool_async)
    
    try:
        # Build execution namespace with provided arguments
        exec_namespace = args.copy()
        
        # Add built-in functions to the namespace
        exec_namespace['__builtins__'] = __builtins__
        
        # Add common Python modules
        import re
        import json as json_module
        import os as os_module
        exec_namespace['re'] = re
        exec_namespace['json'] = json_module
        exec_namespace['os'] = os_module
        
        # 🔑 Inject tool bridge if MCP manager is available
        if tool_bridge:
            exec_namespace['call_tool'] = tool_bridge.call_tool
            exec_namespace['WORKSPACE'] = workspace

        # ===== RUN EXEC IN THREAD POOL =====
        # The key insight: while this thread runs the skill script,
        # the main event loop remains free to process tool call requests
        # from the queue.
        def run_script():
            """Execute the skill script in a worker thread."""
            exec(script_code, exec_namespace)
            return exec_namespace.get('result', 'Script executed successfully (no result variable set)')
        
        # Use run_in_executor to run the script in a thread pool
        # The main loop can process queue requests while waiting
        result = await loop.run_in_executor(None, run_script)

        # ===== QUALITY CHECK =====
        quality_info = check_result_quality(result)
        
        if quality_info["is_low_quality"]:
            # Update stats - count as partial success (still capture schema)
            _update_skill_execution_stats(cache_file, skill_name, success=True, result_value=result, input_args=args)
            return {
                "skill_name": skill_name,
                "status": "low_quality",
                "result": result,
                "tools_enabled": mcp_manager is not None,
                "quality_warning": (
                    f"⚠️ Skill executed but result quality is LOW. "
                    f"Found {quality_info['low_quality_fields']} Unknown/None fields "
                    f"and {quality_info['zero_numeric_fields']} zero values "
                    f"out of {quality_info['total_fields']} total fields. "
                    f"Issues: {', '.join(quality_info['details'][:3])}"
                ),
                "suggestion": (
                    "The skill's extraction logic may not match the data format. Consider:\n"
                    "1. Checking the actual data structure first\n"
                    "2. Fixing the regex or parsing logic\n"
                    "3. Processing this item directly without the skill"
                )
            }
        
        # Update stats - successful execution (capture input/output schema)
        _update_skill_execution_stats(cache_file, skill_name, success=True, result_value=result, input_args=args)
        return {
            "skill_name": skill_name,
            "status": "success",
            "result": result,
            "tools_enabled": mcp_manager is not None
        }

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
        
        # Update stats - failed execution
        _update_skill_execution_stats(cache_file, skill_name, success=False, error_msg=error_msg)
        
        # Build comprehensive error report
        error_report = {
            "skill_name": skill_name,
            "status": "error",
            "error_type": error_type,
            "error_message": error_msg,
            "error_line": error_line,
            "error_line_content": error_line_content,
            "full_traceback": tb,
            "script_code": script_code,  # Include full script for debugging
            "args_provided": args,
            "tools_enabled": mcp_manager is not None,
            "debugging_hints": [
                f"Error type: {error_type}",
                f"Error occurred at line {error_line}: {error_line_content}" if error_line else "Could not determine error line",
                "Check if all required keys exist in the data structure",
                "Verify tool return types match your expectations",
                "Use json.loads() only on strings, not on already-parsed dicts",
            ]
        }
        
        return error_report
    finally:
        # Clean up the queue processor
        if tool_queue:
            tool_queue.stop_processor()


# Define the tools
tool_save_skill = FunctionTool(
    name='local-save_skill',
    description='''Save a reusable skill as executable script. Use this when you identify a task that will be repeated with different inputs.

**CRITICAL: call_tool() returns Python objects directly - NO JSON string parsing needed!**
- local-* API tools return dict directly (e.g., {"success": True, "data": {...}})
- filesystem tools return string content directly
- All results can be used immediately without json.loads()

**Example for API tools:**
```python
data = call_tool('local-gitlab_get_project_info', project_path=project_path)
# data is already a dict, use .get() directly
project = data.get('project', {})
result = {'name': project.get('name')}
```

**Key rules:**
1. Use call_tool('server-tool_name', arg1=val1) for ALL tool calls
2. Return values are Python objects - use .get() for dicts directly
3. MUST set a 'result' variable with your output
4. Parameters are passed as variables (e.g., project_path, file_path)
5. Skill tools (save_skill, execute_skill) cannot be called within skills
6. Available: call_tool(), json, re, os modules
''',
    params_json_schema={
        "type": "object",
        "properties": {
            "skill_name": {
                "type": "string",
                "description": "Name for this skill (e.g., 'stock_full_analysis')"
            },
            "script_code": {
                "type": "string",
                "description": "Complete executable Python code. Can use call_tool() to call tools. Should set a 'result' variable."
            },
            "parameters": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of parameter names the script expects (e.g., ['symbol', 'date'])"
            },
            "description": {
                "type": "string",
                "description": "Description of what this skill does"
            },
            "input_schema": {
                "type": "string",
                "description": "Optional: Input parameter types as JSON-like string (e.g., '{\"project_path\": \"str\", \"limit\": \"int\"}'). Helps future tasks understand how to call this skill."
            },
            "output_schema": {
                "type": "string",
                "description": "Optional: Output structure description (e.g., '{\"name\": \"str\", \"stats\": {\"count\": \"int\"}}'). Helps future tasks understand what this skill returns."
            }
        },
        "required": ["skill_name", "script_code"]
    },
    on_invoke_tool=on_save_skill_invoke
)

tool_get_skill = FunctionTool(
    name='local-get_skill',
    description='Retrieve a saved tool call skill to reuse it',
    params_json_schema={
        "type": "object",
        "properties": {
            "skill_name": {
                "type": "string",
                "description": "Name of the skill to retrieve"
            }
        },
        "required": ["skill_name"]
    },
    on_invoke_tool=on_get_skill_invoke
)

tool_list_skills = FunctionTool(
    name='local-list_skills',
    description='List all saved executable skills',
    params_json_schema={
        "type": "object",
        "properties": {}
    },
    on_invoke_tool=on_list_skills_invoke
)

tool_execute_skill = FunctionTool(
    name='local-execute_skill',
    description='''Execute a saved skill with provided arguments and get the result.

**How it works:**
1. Pass the skill name and args (a dict of parameters)
2. The skill script runs with your args as variables
3. Returns a response dict with status and result

**Return Format:**
```python
{
    "skill_name": "analyze_project",
    "status": "success",  # or "error"
    "result": { ... },    # <-- The actual data is HERE! Use response['result'] to access it
    "tools_enabled": True
}
```

**Example Usage:**
```python
response = call_tool('local-execute_skill', skill_name="analyze_project", args={"project_path": "gitlab-org/gitlab"})
# IMPORTANT: Access the actual result via response['result']
data = response['result']  # or response.get('result', {})
name = data['name']
```

**Important:**
- The skill MUST set a 'result' variable, otherwise you'll get "no result variable set"
- Tools can be called within skills using call_tool()
- In cross-task mode, skills CAN call other skills via call_tool('local-execute_skill', ...)
''',
    params_json_schema={
        "type": "object",
        "properties": {
            "skill_name": {
                "type": "string",
                "description": "Name of the skill to execute"
            },
            "args": {
                "type": "object",
                "description": "Dictionary of arguments to pass to the script (e.g., {'symbol': 'AAPL', 'date': '2024-01-01'})"
            }
        },
        "required": ["skill_name"]
    },
    on_invoke_tool=on_execute_skill_invoke
)

# Export tools as a list for easy import
# Standard tools for single-session tasks (get_skill and list_skills excluded)
skill_cache_tools = [tool_save_skill, tool_execute_skill]

# Full tool list for cross-task mode (includes get_skill and list_skills)
# These are useful when skills can be inherited from previous tasks
skill_cache_tools_full = [tool_save_skill, tool_get_skill, tool_list_skills, tool_execute_skill]

# Tools for static-skill mode (NO save_skill - only execute/browse existing skills)
# Used when loading pre-created skills from external source
skill_cache_tools_static = [tool_get_skill, tool_list_skills, tool_execute_skill]


def get_skills_summary_for_prompt(skills: Dict[str, Any]) -> str:
    """
    Generate a formatted skills summary for injection into system prompt.
    
    This is used in cross-task mode to inform the agent about available skills
    from previous tasks in the same task group.
    
    Args:
        skills: Dictionary of skill_name -> skill_data
        
    Returns:
        Formatted string suitable for prompt injection
    """
    if not skills:
        return ""
    
    lines = [
        "",
        "## 🔄 Available Skills (from previous tasks in this group)",
        "",
        "The following skills have been created by earlier tasks and are ready to use.",
        "**You can directly use these skills with `local-execute_skill`** instead of creating new ones.",
        "",
    ]
    
    # Use the detailed format function
    lines.append(format_skills_list(skills, include_header=False))
    lines.append("")
    
    return "\n".join(lines)
