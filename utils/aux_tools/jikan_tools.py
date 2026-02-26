"""
Jikan API Tools (MyAnimeList Unofficial API)

Provides tools to query anime information from the Jikan API.
Designed for skill mode scenarios with large output data.

API Documentation: https://docs.api.jikan.moe
Rate Limit: 3 requests/second, 60 requests/minute
"""

import json
from typing import Any
from agents.tool import FunctionTool, RunContextWrapper
import requests
import time

# Base URL for Jikan API v4
JIKAN_BASE_URL = "https://api.jikan.moe/v4"

# Rate limiting
_last_request_time = 0
_MIN_REQUEST_INTERVAL = 0.4  # 400ms between requests


def _rate_limit():
    """Ensure we don't exceed rate limits."""
    global _last_request_time
    current_time = time.time()
    time_since_last = current_time - _last_request_time
    if time_since_last < _MIN_REQUEST_INTERVAL:
        time.sleep(_MIN_REQUEST_INTERVAL - time_since_last)
    _last_request_time = time.time()


def _make_request(endpoint: str, params: dict = None) -> dict:
    """Make a request to the Jikan API with error handling."""
    _rate_limit()
    
    url = f"{JIKAN_BASE_URL}{endpoint}"
    headers = {"User-Agent": "DikaNong-PatternReuse/1.0"}
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        return {"error": "Request timeout", "success": False}
    except requests.exceptions.RequestException as e:
        return {"error": str(e), "success": False}


def _parse_params(params_str: str) -> dict:
    """Parse parameters from string."""
    if not params_str:
        return {}
    if isinstance(params_str, dict):
        return params_str
    try:
        return json.loads(params_str)
    except json.JSONDecodeError:
        return {}


# ============== Tool Implementation Functions ==============

def _get_anime_details(anime_id: int) -> dict:
    """Get detailed information about an anime with VERBOSE data for skill mode."""
    data = _make_request(f"/anime/{anime_id}")
    
    if "error" in data:
        return data
    
    anime = data.get("data", {})
    
    # VERBOSE: Full synopsis without truncation
    synopsis = anime.get("synopsis", "")
    background = anime.get("background", "")
    
    # VERBOSE: Full studio details
    studios = []
    for s in anime.get("studios", []):
        studios.append({
            "mal_id": s.get("mal_id"),
            "name": s.get("name"),
            "type": s.get("type"),
            "url": s.get("url")
        })
    
    # VERBOSE: Full producer details
    producers = []
    for p in anime.get("producers", []):
        producers.append({
            "mal_id": p.get("mal_id"),
            "name": p.get("name"),
            "type": p.get("type"),
            "url": p.get("url")
        })
    
    # VERBOSE: Full licensor details
    licensors = []
    for l in anime.get("licensors", []):
        licensors.append({
            "mal_id": l.get("mal_id"),
            "name": l.get("name"),
            "type": l.get("type"),
            "url": l.get("url")
        })
    
    # VERBOSE: Full genre details
    genres = []
    for g in anime.get("genres", []):
        genres.append({
            "mal_id": g.get("mal_id"),
            "name": g.get("name"),
            "type": g.get("type"),
            "url": g.get("url")
        })
    
    # VERBOSE: Full theme details
    themes = []
    for t in anime.get("themes", []):
        themes.append({
            "mal_id": t.get("mal_id"),
            "name": t.get("name"),
            "type": t.get("type"),
            "url": t.get("url")
        })
    
    # VERBOSE: Title synonyms
    titles = anime.get("titles", [])
    title_synonyms = anime.get("title_synonyms", [])
    
    return {
        "success": True,
        "anime": {
            "mal_id": anime.get("mal_id"),
            "url": anime.get("url"),
            "title": anime.get("title"),
            "title_english": anime.get("title_english"),
            "title_japanese": anime.get("title_japanese"),
            "title_synonyms": title_synonyms,
            "titles": titles,
            "type": anime.get("type"),
            "episodes": anime.get("episodes"),
            "status": anime.get("status"),
            "airing": anime.get("airing"),
            "score": anime.get("score"),
            "scored_by": anime.get("scored_by"),
            "rank": anime.get("rank"),
            "popularity": anime.get("popularity"),
            "members": anime.get("members"),
            "favorites": anime.get("favorites"),
            "synopsis": synopsis,  # Full synopsis
            "background": background,  # Full background
            "season": anime.get("season"),
            "year": anime.get("year"),
            "broadcast": anime.get("broadcast"),
            "studios": studios,
            "producers": producers,
            "licensors": licensors,
            "genres": genres,
            "themes": themes,
            "explicit_genres": anime.get("explicit_genres", []),
            "demographics": [d.get("name") for d in anime.get("demographics", [])],
            "duration": anime.get("duration"),
            "rating": anime.get("rating"),
            "source": anime.get("source"),
            "aired": {
                "from": anime.get("aired", {}).get("from"),
                "to": anime.get("aired", {}).get("to"),
                "string": anime.get("aired", {}).get("string")
            },
            "images": anime.get("images", {}),
            "trailer": anime.get("trailer", {})
        }
    }


def _get_anime_characters(anime_id: int) -> dict:
    """Get characters for an anime with VERBOSE data for skill mode."""
    data = _make_request(f"/anime/{anime_id}/characters")
    
    if "error" in data:
        return data
    
    characters = data.get("data", [])
    processed = []
    
    # MODERATE VERBOSE: Return characters (limited to 25 to avoid context explosion)
    for char in characters[:25]:
        char_data = char.get("character", {})
        
        # VERBOSE: All voice actors with full details
        voice_actors = []
        for va in char.get("voice_actors", []):
            person = va.get("person", {})
            voice_actors.append({
                "mal_id": person.get("mal_id"),
                "name": person.get("name"),
                "language": va.get("language"),
                "url": person.get("url"),
                "images": person.get("images", {})
            })
        
        processed.append({
            "mal_id": char_data.get("mal_id"),
            "name": char_data.get("name"),
            "url": char_data.get("url"),
            "images": char_data.get("images", {}),
            "role": char.get("role"),
            "favorites": char.get("favorites"),
            "voice_actors_count": len(char.get("voice_actors", [])),
            "voice_actors": voice_actors
        })
    
    # VERBOSE: Calculate character statistics
    main_chars = [c for c in characters if c.get("role") == "Main"]
    supporting_chars = [c for c in characters if c.get("role") == "Supporting"]
    
    return {
        "success": True,
        "anime_id": anime_id,
        "total_characters": len(characters),
        "returned_count": len(processed),
        "statistics": {
            "main_characters": len(main_chars),
            "supporting_characters": len(supporting_chars),
            "total_favorites": sum(c.get("favorites", 0) for c in characters),
            "avg_favorites": round(sum(c.get("favorites", 0) for c in characters) / len(characters), 1) if characters else 0,
            "most_favorited": max(characters, key=lambda x: x.get("favorites", 0), default={}).get("character", {}).get("name") if characters else None
        },
        "characters": processed
    }


def _get_anime_episodes(anime_id: int, page: int = 1) -> dict:
    """Get episode list for an anime."""
    data = _make_request(f"/anime/{anime_id}/episodes", {"page": page})
    
    if "error" in data:
        return data
    
    episodes = data.get("data", [])
    pagination = data.get("pagination", {})
    
    processed = []
    for ep in episodes:
        processed.append({
            "mal_id": ep.get("mal_id"),
            "title": ep.get("title"),
            "title_japanese": ep.get("title_japanese"),
            "aired": ep.get("aired"),
            "score": ep.get("score"),
            "filler": ep.get("filler"),
            "recap": ep.get("recap")
        })
    
    return {
        "success": True,
        "anime_id": anime_id,
        "page": page,
        "episodes": processed,
        "pagination": {
            "last_visible_page": pagination.get("last_visible_page"),
            "has_next_page": pagination.get("has_next_page"),
            "total_episodes": len(episodes)
        }
    }


def _get_anime_recommendations(anime_id: int) -> dict:
    """Get recommendations for an anime."""
    data = _make_request(f"/anime/{anime_id}/recommendations")
    
    if "error" in data:
        return data
    
    recommendations = data.get("data", [])
    processed = []
    
    for rec in recommendations[:10]:  # Top 10 recommendations
        entry = rec.get("entry", {})
        processed.append({
            "mal_id": entry.get("mal_id"),
            "title": entry.get("title"),
            "votes": rec.get("votes")
        })
    
    return {
        "success": True,
        "anime_id": anime_id,
        "total_recommendations": len(recommendations),
        "recommendations": processed
    }


def _get_anime_statistics(anime_id: int) -> dict:
    """Get statistics for an anime."""
    data = _make_request(f"/anime/{anime_id}/statistics")
    
    if "error" in data:
        return data
    
    stats = data.get("data", {})
    
    return {
        "success": True,
        "anime_id": anime_id,
        "statistics": {
            "watching": stats.get("watching"),
            "completed": stats.get("completed"),
            "on_hold": stats.get("on_hold"),
            "dropped": stats.get("dropped"),
            "plan_to_watch": stats.get("plan_to_watch"),
            "total": stats.get("total"),
            "scores": stats.get("scores", [])
        }
    }


# ============== Tool Handlers ==============

async def on_get_anime_details(context: RunContextWrapper, params_str: str) -> Any:
    """Handler for getting anime details."""
    params = _parse_params(params_str)
    anime_id = params.get("anime_id")
    
    if not anime_id:
        return {"error": "anime_id is required", "success": False}
    
    result = _get_anime_details(int(anime_id))
    return result


async def on_get_anime_characters(context: RunContextWrapper, params_str: str) -> Any:
    """Handler for getting anime characters."""
    params = _parse_params(params_str)
    anime_id = params.get("anime_id")
    
    if not anime_id:
        return {"error": "anime_id is required", "success": False}
    
    result = _get_anime_characters(int(anime_id))
    return result


async def on_get_anime_episodes(context: RunContextWrapper, params_str: str) -> Any:
    """Handler for getting anime episodes."""
    params = _parse_params(params_str)
    anime_id = params.get("anime_id")
    page = params.get("page", 1)
    
    if not anime_id:
        return {"error": "anime_id is required", "success": False}
    
    result = _get_anime_episodes(int(anime_id), int(page))
    return result


async def on_get_anime_recommendations(context: RunContextWrapper, params_str: str) -> Any:
    """Handler for getting anime recommendations."""
    params = _parse_params(params_str)
    anime_id = params.get("anime_id")
    
    if not anime_id:
        return {"error": "anime_id is required", "success": False}
    
    result = _get_anime_recommendations(int(anime_id))
    return result


async def on_get_anime_statistics(context: RunContextWrapper, params_str: str) -> Any:
    """Handler for getting anime statistics."""
    params = _parse_params(params_str)
    anime_id = params.get("anime_id")
    
    if not anime_id:
        return {"error": "anime_id is required", "success": False}
    
    result = _get_anime_statistics(int(anime_id))
    return result


# ============== Tool Definitions ==============

tool_jikan_get_anime_details = FunctionTool(
    name='local-jikan_get_anime_details',
    description='''Get detailed information about an anime.

**Returns:** dict:
{
  "success": bool,
  "anime": {
    "mal_id": int,
    "title": str,
    "title_english": str | null,
    "title_japanese": str,
    "type": str,
    "episodes": int | null,
    "status": str,
    "score": float | null,
    "scored_by": int,
    "rank": int,
    "popularity": int,
    "members": int,
    "favorites": int,
    "synopsis": str,
    "season": str | null,
    "year": int | null,
    "studios": [str],
    "genres": [str],
    "themes": [str],
    "demographics": [str],
    "duration": str,
    "rating": str,
    "source": str,
    "aired": {"from": str | null, "to": str | null}
  }
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "anime_id": {
                "type": "integer",
                "description": "The MyAnimeList ID of the anime"
            }
        },
        "required": ["anime_id"]
    },
    on_invoke_tool=on_get_anime_details
)

tool_jikan_get_anime_characters = FunctionTool(
    name='local-jikan_get_anime_characters',
    description='''Get the character list for an anime with voice actors.

**Returns:** dict:
{
  "success": bool,
  "anime_id": int,
  "total_characters": int,
  "characters": [
    {
      "mal_id": int,
      "name": str,
      "role": str,
      "favorites": int,
      "voice_actors": [{"name": str, "language": str}]
    }
  ],
  "main_characters": int,
  "supporting_characters": int
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "anime_id": {
                "type": "integer",
                "description": "The MyAnimeList ID of the anime"
            }
        },
        "required": ["anime_id"]
    },
    on_invoke_tool=on_get_anime_characters
)

tool_jikan_get_anime_episodes = FunctionTool(
    name='local-jikan_get_anime_episodes',
    description='''Get the episode list for an anime.

**Returns:** dict:
{
  "success": bool,
  "anime_id": int,
  "page": int,
  "episodes": [
    {
      "mal_id": int,
      "title": str,
      "title_japanese": str | null,
      "aired": str | null,
      "score": float | null,
      "filler": bool,
      "recap": bool
    }
  ],
  "pagination": {
    "last_visible_page": int,
    "has_next_page": bool,
    "total_episodes": int
  }
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "anime_id": {
                "type": "integer",
                "description": "The MyAnimeList ID of the anime"
            },
            "page": {
                "type": "integer",
                "description": "Page number for pagination (default: 1)"
            }
        },
        "required": ["anime_id"]
    },
    on_invoke_tool=on_get_anime_episodes
)

tool_jikan_get_anime_recommendations = FunctionTool(
    name='local-jikan_get_anime_recommendations',
    description='''Get user recommendations for similar anime.

**Returns:** dict:
{
  "success": bool,
  "anime_id": int,
  "total_recommendations": int,
  "recommendations": [
    {
      "mal_id": int,
      "title": str,
      "votes": int
    }
  ]
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "anime_id": {
                "type": "integer",
                "description": "The MyAnimeList ID of the anime"
            }
        },
        "required": ["anime_id"]
    },
    on_invoke_tool=on_get_anime_recommendations
)

tool_jikan_get_anime_statistics = FunctionTool(
    name='local-jikan_get_anime_statistics',
    description='''Get watching statistics for an anime.

**Returns:** dict:
{
  "success": bool,
  "anime_id": int,
  "statistics": {
    "watching": int,
    "completed": int,
    "on_hold": int,
    "dropped": int,
    "plan_to_watch": int,
    "total": int,
    "scores": [{"score": int, "votes": int, "percentage": float}]
  }
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "anime_id": {
                "type": "integer",
                "description": "The MyAnimeList ID of the anime"
            }
        },
        "required": ["anime_id"]
    },
    on_invoke_tool=on_get_anime_statistics
)


# Export all tools as a list
jikan_tools = [
    tool_jikan_get_anime_details,
    tool_jikan_get_anime_characters,
    tool_jikan_get_anime_episodes,
    tool_jikan_get_anime_recommendations,
    tool_jikan_get_anime_statistics,
]

