"""
Wikipedia API Tools for WebArena Reuse Tasks

These tools provide access to Wikipedia API for searching and retrieving article information.
Designed for skill mode scenarios where multiple similar queries are executed.
"""

import json
from typing import Any
from agents.tool import FunctionTool, RunContextWrapper
import requests

# Wikipedia API endpoint
WIKIPEDIA_API_URL = "https://en.wikipedia.org/w/api.php"


# ============== Core Functions ==============

def _wikipedia_search(query: str, limit: int = 10) -> dict:
    """Search Wikipedia for articles matching a query."""
    try:
        params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "srlimit": min(limit, 50),
            "format": "json",
            "utf8": 1
        }
        
        response = requests.get(WIKIPEDIA_API_URL, params=params, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            results = data.get("query", {}).get("search", [])
            simplified = [{
                "title": r.get("title"),
                "snippet": r.get("snippet", "").replace("<span class=\"searchmatch\">", "").replace("</span>", ""),
                "pageid": r.get("pageid"),
                "wordcount": r.get("wordcount")
            } for r in results]
            return {
                "success": True,
                "results": simplified,
                "count": len(simplified)
            }
        else:
            return {"success": False, "error": f"API error: {response.status_code}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _wikipedia_get_summary(title: str) -> dict:
    """Get the summary/introduction of a Wikipedia article."""
    try:
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{requests.utils.quote(title)}"
        
        response = requests.get(url, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            return {
                "success": True,
                "title": data.get("title"),
                "extract": data.get("extract", ""),
                "description": data.get("description", ""),
                "page_url": data.get("content_urls", {}).get("desktop", {}).get("page", "")
            }
        elif response.status_code == 404:
            return {"success": False, "error": f"Article '{title}' not found"}
        else:
            return {"success": False, "error": f"API error: {response.status_code}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _wikipedia_get_categories(title: str) -> dict:
    """Get the categories of a Wikipedia article."""
    try:
        params = {
            "action": "query",
            "titles": title,
            "prop": "categories",
            "cllimit": 50,
            "format": "json"
        }
        
        response = requests.get(WIKIPEDIA_API_URL, params=params, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            pages = data.get("query", {}).get("pages", {})
            
            for page_id, page_data in pages.items():
                if page_id == "-1":
                    return {"success": False, "error": f"Article '{title}' not found"}
                
                categories = page_data.get("categories", [])
                cat_names = [c.get("title", "").replace("Category:", "") for c in categories]
                return {
                    "success": True,
                    "title": page_data.get("title"),
                    "categories": cat_names,
                    "count": len(cat_names)
                }
            
            return {"success": False, "error": "No page data returned"}
        else:
            return {"success": False, "error": f"API error: {response.status_code}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _wikipedia_get_links(title: str, limit: int = 50) -> dict:
    """Get the internal links from a Wikipedia article."""
    try:
        params = {
            "action": "query",
            "titles": title,
            "prop": "links",
            "pllimit": min(limit, 500),
            "format": "json"
        }
        
        response = requests.get(WIKIPEDIA_API_URL, params=params, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            pages = data.get("query", {}).get("pages", {})
            
            for page_id, page_data in pages.items():
                if page_id == "-1":
                    return {"success": False, "error": f"Article '{title}' not found"}
                
                links = page_data.get("links", [])
                link_titles = [l.get("title") for l in links if l.get("ns") == 0]
                return {
                    "success": True,
                    "title": page_data.get("title"),
                    "links": link_titles,
                    "count": len(link_titles)
                }
            
            return {"success": False, "error": "No page data returned"}
        else:
            return {"success": False, "error": f"API error: {response.status_code}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============== Tool Handlers ==============

async def on_wikipedia_search(context: RunContextWrapper, params_str: str) -> Any:
    params = json.loads(params_str)
    query = params.get("query", "")
    limit = params.get("limit", 10)
    result = _wikipedia_search(query, limit)
    return result


async def on_wikipedia_get_summary(context: RunContextWrapper, params_str: str) -> Any:
    params = json.loads(params_str)
    title = params.get("title", "")
    result = _wikipedia_get_summary(title)
    return result


async def on_wikipedia_get_categories(context: RunContextWrapper, params_str: str) -> Any:
    params = json.loads(params_str)
    title = params.get("title", "")
    result = _wikipedia_get_categories(title)
    return result


async def on_wikipedia_get_links(context: RunContextWrapper, params_str: str) -> Any:
    params = json.loads(params_str)
    title = params.get("title", "")
    limit = params.get("limit", 50)
    result = _wikipedia_get_links(title, limit)
    return result


# ============== Tool Definitions ==============

tool_wikipedia_search = FunctionTool(
    name='local-wikipedia_search',
    description='Search Wikipedia for articles matching a query. Returns titles, snippets, and page IDs.',
    params_json_schema={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query"
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of results (1-50)"
            }
        },
        "required": ["query"]
    },
    on_invoke_tool=on_wikipedia_search
)

tool_wikipedia_get_summary = FunctionTool(
    name='local-wikipedia_get_summary',
    description='Get the summary/introduction text of a Wikipedia article.',
    params_json_schema={
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Wikipedia article title (exact title or close match)"
            }
        },
        "required": ["title"]
    },
    on_invoke_tool=on_wikipedia_get_summary
)

tool_wikipedia_get_categories = FunctionTool(
    name='local-wikipedia_get_categories',
    description='Get the categories that a Wikipedia article belongs to.',
    params_json_schema={
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Wikipedia article title"
            }
        },
        "required": ["title"]
    },
    on_invoke_tool=on_wikipedia_get_categories
)

tool_wikipedia_get_links = FunctionTool(
    name='local-wikipedia_get_links',
    description='Get the internal Wikipedia links from an article (other articles it links to).',
    params_json_schema={
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Wikipedia article title"
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of links to return"
            }
        },
        "required": ["title"]
    },
    on_invoke_tool=on_wikipedia_get_links
)

# Export all tools as a list
wikipedia_api_tools = [
    tool_wikipedia_search,
    tool_wikipedia_get_summary,
    tool_wikipedia_get_categories,
    tool_wikipedia_get_links,
]
