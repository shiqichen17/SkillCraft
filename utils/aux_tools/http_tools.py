"""
HTTP Tools - Atomic-level HTTP operations for skill mode testing.

These tools provide low-level HTTP functionality that can be composed
in patterns to build complex API interactions.
"""

import json
import urllib.parse
from typing import Any, Dict, Optional
from agents.tool import FunctionTool, RunContextWrapper
import requests


# ============== Core Functions ==============

def _http_get(url: str, headers: Dict = None, params: Dict = None, timeout: int = 30) -> Dict:
    """
    Send an HTTP GET request and return the response.
    
    Returns raw response body as string (caller needs to parse JSON if needed).
    """
    try:
        response = requests.get(
            url, 
            headers=headers or {},
            params=params,
            timeout=timeout
        )
        
        return {
            "success": True,
            "status_code": response.status_code,
            "body": response.text,
            "headers": dict(response.headers)
        }
    except requests.exceptions.Timeout:
        return {"success": False, "error": "Request timeout", "status_code": 0}
    except requests.exceptions.ConnectionError as e:
        return {"success": False, "error": f"Connection error: {str(e)}", "status_code": 0}
    except Exception as e:
        return {"success": False, "error": str(e), "status_code": 0}


def _http_post(url: str, data: Any = None, json_data: Dict = None, 
               headers: Dict = None, timeout: int = 30) -> Dict:
    """Send an HTTP POST request."""
    try:
        response = requests.post(
            url,
            data=data,
            json=json_data,
            headers=headers or {},
            timeout=timeout
        )
        
        return {
            "success": True,
            "status_code": response.status_code,
            "body": response.text,
            "headers": dict(response.headers)
        }
    except requests.exceptions.Timeout:
        return {"success": False, "error": "Request timeout", "status_code": 0}
    except Exception as e:
        return {"success": False, "error": str(e), "status_code": 0}


def _url_encode(text: str) -> str:
    """URL encode a string (for use in URL paths)."""
    return urllib.parse.quote(text, safe='')


def _url_build(base_url: str, path: str = "", params: Dict = None) -> str:
    """
    Build a complete URL with path and query parameters.
    
    Args:
        base_url: Base URL (e.g., "https://api.example.com")
        path: URL path (e.g., "/v1/users")
        params: Query parameters dict
    
    Returns:
        Complete URL string
    """
    url = base_url.rstrip('/') 
    if path:
        url = url + '/' + path.lstrip('/')
    
    if params:
        query_string = urllib.parse.urlencode(params)
        url = url + '?' + query_string
    
    return url


# ============== Tool Handlers ==============

async def on_http_get(context: RunContextWrapper, params_str: str) -> Any:
    params = json.loads(params_str)
    url = params.get("url", "")
    headers = params.get("headers")
    query_params = params.get("params")
    timeout = params.get("timeout", 30)
    result = _http_get(url, headers, query_params, timeout)
    return result


async def on_http_post(context: RunContextWrapper, params_str: str) -> Any:
    params = json.loads(params_str)
    url = params.get("url", "")
    data = params.get("data")
    json_data = params.get("json")
    headers = params.get("headers")
    timeout = params.get("timeout", 30)
    result = _http_post(url, data, json_data, headers, timeout)
    return result


async def on_url_encode(context: RunContextWrapper, params_str: str) -> Any:
    params = json.loads(params_str)
    text = params.get("text", "")
    return _url_encode(text)


async def on_url_build(context: RunContextWrapper, params_str: str) -> Any:
    params = json.loads(params_str)
    base_url = params.get("base_url", "")
    path = params.get("path", "")
    query_params = params.get("params")
    return _url_build(base_url, path, query_params)


# ============== Tool Definitions ==============

tool_http_get = FunctionTool(
    name='local-http_get',
    description='''Send an HTTP GET request to a URL. Returns the raw response body.

Example: http_get(url="https://api.example.com/data")

Returns: {"success": true, "status_code": 200, "body": "...", "headers": {...}}

Note: If the response is JSON, use json_parse to parse the body.''',
    params_json_schema={
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "The URL to send the GET request to"
            },
            "headers": {
                "type": "object",
                "description": "Optional HTTP headers as key-value pairs"
            },
            "params": {
                "type": "object",
                "description": "Optional query parameters as key-value pairs"
            },
            "timeout": {
                "type": "integer",
                "description": "Request timeout in seconds (default: 30)"
            }
        },
        "required": ["url"]
    },
    on_invoke_tool=on_http_get
)

tool_http_post = FunctionTool(
    name='local-http_post',
    description='''Send an HTTP POST request. Can send form data or JSON.

Example: http_post(url="https://api.example.com/data", json={"key": "value"})

Returns: {"success": true, "status_code": 200, "body": "...", "headers": {...}}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "The URL to send the POST request to"
            },
            "data": {
                "type": "string",
                "description": "Form data to send (for form submissions)"
            },
            "json": {
                "type": "object",
                "description": "JSON data to send (sets Content-Type: application/json)"
            },
            "headers": {
                "type": "object",
                "description": "Optional HTTP headers"
            },
            "timeout": {
                "type": "integer",
                "description": "Request timeout in seconds (default: 30)"
            }
        },
        "required": ["url"]
    },
    on_invoke_tool=on_http_post
)

tool_url_encode = FunctionTool(
    name='local-url_encode',
    description='''URL-encode a string for safe use in URL paths.

Example: url_encode(text="gitlab-org/gitlab") → "gitlab-org%2Fgitlab"

Use this when you need to include special characters (like /) in URL paths.''',
    params_json_schema={
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "The string to URL-encode"
            }
        },
        "required": ["text"]
    },
    on_invoke_tool=on_url_encode
)

tool_url_build = FunctionTool(
    name='local-url_build',
    description='''Build a complete URL from base URL, path, and query parameters.

Example: url_build(
    base_url="https://gitlab.com/api/v4",
    path="projects/123/issues",
    params={"state": "opened", "per_page": 10}
)
→ "https://gitlab.com/api/v4/projects/123/issues?state=opened&per_page=10"''',
    params_json_schema={
        "type": "object",
        "properties": {
            "base_url": {
                "type": "string",
                "description": "The base URL (e.g., 'https://api.example.com')"
            },
            "path": {
                "type": "string",
                "description": "URL path to append (e.g., '/v1/users')"
            },
            "params": {
                "type": "object",
                "description": "Query parameters as key-value pairs"
            }
        },
        "required": ["base_url"]
    },
    on_invoke_tool=on_url_build
)

# Export all tools
http_tools = [
    tool_http_get,
    tool_http_post,
    tool_url_encode,
    tool_url_build,
]

