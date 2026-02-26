"""
TVMaze API Tools

Provides tools to query TV show information from the TVMaze API.
Designed for skill mode scenarios with structured output data.

API Documentation: https://www.tvmaze.com/api
Rate Limit: 20 requests/10 seconds
"""

import json
from typing import Any
from agents.tool import FunctionTool, RunContextWrapper
import requests
import time

# Base URL for TVMaze API
TVMAZE_BASE_URL = "https://api.tvmaze.com"

# Rate limiting
_last_request_time = 0
_MIN_REQUEST_INTERVAL = 0.5  # 500ms between requests


def _rate_limit():
    """Ensure we don't exceed rate limits."""
    global _last_request_time
    current_time = time.time()
    time_since_last = current_time - _last_request_time
    if time_since_last < _MIN_REQUEST_INTERVAL:
        time.sleep(_MIN_REQUEST_INTERVAL - time_since_last)
    _last_request_time = time.time()


def _make_request(endpoint: str, params: dict = None) -> dict:
    """Make a request to the TVMaze API with error handling."""
    _rate_limit()
    
    url = f"{TVMAZE_BASE_URL}{endpoint}"
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

def _get_show_info(show_id: int) -> dict:
    """Get detailed information about a TV show with VERBOSE data for skill mode."""
    data = _make_request(f"/shows/{show_id}")
    
    if isinstance(data, dict) and "error" in data:
        return data
    
    # VERBOSE: Full network details
    network_info = None
    if data.get("network"):
        network = data.get("network")
        network_info = {
            "id": network.get("id"),
            "name": network.get("name"),
            "country": {
                "name": network.get("country", {}).get("name"),
                "code": network.get("country", {}).get("code"),
                "timezone": network.get("country", {}).get("timezone")
            },
            "officialSite": network.get("officialSite")
        }
    
    # VERBOSE: Full web channel details
    webchannel_info = None
    if data.get("webChannel"):
        wc = data.get("webChannel")
        webchannel_info = {
            "id": wc.get("id"),
            "name": wc.get("name"),
            "country": wc.get("country"),
            "officialSite": wc.get("officialSite")
        }
    
    # VERBOSE: All images
    images = data.get("image", {})
    image_info = {
        "medium": images.get("medium"),
        "original": images.get("original")
    }
    
    # VERBOSE: External links
    externals = data.get("externals", {})
    external_ids = {
        "tvrage": externals.get("tvrage"),
        "thetvdb": externals.get("thetvdb"),
        "imdb": externals.get("imdb")
    }
    
    return {
        "success": True,
        "show": {
            "id": data.get("id"),
            "url": data.get("url"),
            "name": data.get("name"),
            "type": data.get("type"),
            "language": data.get("language"),
            "genres": data.get("genres", []),
            "status": data.get("status"),
            "runtime": data.get("runtime"),
            "averageRuntime": data.get("averageRuntime"),
            "premiered": data.get("premiered"),
            "ended": data.get("ended"),
            "officialSite": data.get("officialSite"),
            "rating": {
                "average": data.get("rating", {}).get("average")
            },
            "weight": data.get("weight"),
            "network": network_info,
            "webChannel": webchannel_info,
            "dvdCountry": data.get("dvdCountry"),
            "externals": external_ids,
            "summary": data.get("summary"),  # Full summary
            "updated": data.get("updated"),
            "schedule": data.get("schedule", {}),
            "images": image_info,
            "_links": data.get("_links", {})
        }
    }


def _get_show_episodes(show_id: int) -> dict:
    """Get all episodes for a TV show with VERBOSE data for skill mode."""
    data = _make_request(f"/shows/{show_id}/episodes")
    
    if isinstance(data, dict) and "error" in data:
        return data
    
    if not isinstance(data, list):
        return {"error": "Invalid response format", "success": False}
    
    # VERBOSE: Full episode details
    episodes = []
    for ep in data:
        episodes.append({
            "id": ep.get("id"),
            "url": ep.get("url"),
            "name": ep.get("name"),
            "season": ep.get("season"),
            "number": ep.get("number"),
            "type": ep.get("type"),
            "airdate": ep.get("airdate"),
            "airtime": ep.get("airtime"),
            "airstamp": ep.get("airstamp"),
            "runtime": ep.get("runtime"),
            "rating": {
                "average": ep.get("rating", {}).get("average")
            },
            "image": {
                "medium": ep.get("image", {}).get("medium") if ep.get("image") else None,
                "original": ep.get("image", {}).get("original") if ep.get("image") else None
            },
            "summary": ep.get("summary"),  # Full summary
            "_links": ep.get("_links", {})
        })
    
    # VERBOSE: Calculate comprehensive season statistics
    seasons = {}
    for ep in episodes:
        s = ep.get("season")
        if s:
            if s not in seasons:
                seasons[s] = {
                    "episodes": [],
                    "ratings": [],
                    "runtimes": [],
                    "first_airdate": None,
                    "last_airdate": None
                }
            seasons[s]["episodes"].append(ep)
            if ep.get("rating", {}).get("average"):
                seasons[s]["ratings"].append(ep["rating"]["average"])
            if ep.get("runtime"):
                seasons[s]["runtimes"].append(ep["runtime"])
            
            airdate = ep.get("airdate")
            if airdate:
                if not seasons[s]["first_airdate"] or airdate < seasons[s]["first_airdate"]:
                    seasons[s]["first_airdate"] = airdate
                if not seasons[s]["last_airdate"] or airdate > seasons[s]["last_airdate"]:
                    seasons[s]["last_airdate"] = airdate
    
    season_stats = []
    for s_num, s_data in sorted(seasons.items()):
        avg_rating = sum(s_data["ratings"]) / len(s_data["ratings"]) if s_data["ratings"] else None
        avg_runtime = sum(s_data["runtimes"]) / len(s_data["runtimes"]) if s_data["runtimes"] else None
        total_runtime = sum(s_data["runtimes"]) if s_data["runtimes"] else 0
        
        # Find best and worst episodes
        rated_eps = [(ep["name"], ep["rating"]["average"]) for ep in s_data["episodes"] if ep.get("rating", {}).get("average")]
        best_ep = max(rated_eps, key=lambda x: x[1]) if rated_eps else None
        worst_ep = min(rated_eps, key=lambda x: x[1]) if rated_eps else None
        
        season_stats.append({
            "season": s_num,
            "episode_count": len(s_data["episodes"]),
            "average_rating": round(avg_rating, 2) if avg_rating else None,
            "average_runtime": round(avg_runtime, 1) if avg_runtime else None,
            "total_runtime_minutes": total_runtime,
            "first_airdate": s_data["first_airdate"],
            "last_airdate": s_data["last_airdate"],
            "best_episode": {"name": best_ep[0], "rating": best_ep[1]} if best_ep else None,
            "worst_episode": {"name": worst_ep[0], "rating": worst_ep[1]} if worst_ep else None,
            "rated_episodes_count": len(rated_eps)
        })
    
    # VERBOSE: Overall statistics
    all_ratings = [ep.get("rating", {}).get("average") for ep in episodes if ep.get("rating", {}).get("average")]
    all_runtimes = [ep.get("runtime") for ep in episodes if ep.get("runtime")]
    
    return {
        "success": True,
        "show_id": show_id,
        "total_episodes": len(episodes),
        "total_seasons": len(seasons),
        "overall_statistics": {
            "average_rating": round(sum(all_ratings) / len(all_ratings), 2) if all_ratings else None,
            "highest_rating": max(all_ratings) if all_ratings else None,
            "lowest_rating": min(all_ratings) if all_ratings else None,
            "rated_episodes": len(all_ratings),
            "unrated_episodes": len(episodes) - len(all_ratings),
            "average_runtime": round(sum(all_runtimes) / len(all_runtimes), 1) if all_runtimes else None,
            "total_runtime_minutes": sum(all_runtimes) if all_runtimes else 0,
            "total_runtime_hours": round(sum(all_runtimes) / 60, 1) if all_runtimes else 0
        },
        "episodes": episodes,
        "season_statistics": season_stats
    }


def _get_show_seasons(show_id: int) -> dict:
    """Get season information for a TV show."""
    data = _make_request(f"/shows/{show_id}/seasons")
    
    if isinstance(data, dict) and "error" in data:
        return data
    
    if not isinstance(data, list):
        return {"error": "Invalid response format", "success": False}
    
    seasons = []
    for s in data:
        seasons.append({
            "id": s.get("id"),
            "number": s.get("number"),
            "name": s.get("name"),
            "episodeOrder": s.get("episodeOrder"),
            "premiereDate": s.get("premiereDate"),
            "endDate": s.get("endDate"),
            "network": s.get("network", {}).get("name") if s.get("network") else None
        })
    
    return {
        "success": True,
        "show_id": show_id,
        "total_seasons": len(seasons),
        "seasons": seasons,
        "total_ordered_episodes": sum(s.get("episodeOrder", 0) or 0 for s in seasons)
    }


def _get_show_cast(show_id: int) -> dict:
    """Get cast information for a TV show with VERBOSE data for skill mode."""
    data = _make_request(f"/shows/{show_id}/cast")
    
    if isinstance(data, dict) and "error" in data:
        return data
    
    if not isinstance(data, list):
        return {"error": "Invalid response format", "success": False}
    
    # VERBOSE: Return ALL cast members with full details
    cast = []
    countries = {}
    genders = {}
    
    for member in data:
        person = member.get("person", {})
        character = member.get("character", {})
        
        country = person.get("country", {}).get("name") if person.get("country") else "Unknown"
        gender = person.get("gender") or "Unknown"
        countries[country] = countries.get(country, 0) + 1
        genders[gender] = genders.get(gender, 0) + 1
        
        cast.append({
            "person": {
                "id": person.get("id"),
                "url": person.get("url"),
                "name": person.get("name"),
                "birthday": person.get("birthday"),
                "deathday": person.get("deathday"),
                "country": {
                    "name": country,
                    "code": person.get("country", {}).get("code") if person.get("country") else None,
                    "timezone": person.get("country", {}).get("timezone") if person.get("country") else None
                },
                "gender": gender,
                "image": {
                    "medium": person.get("image", {}).get("medium") if person.get("image") else None,
                    "original": person.get("image", {}).get("original") if person.get("image") else None
                },
                "updated": person.get("updated"),
                "_links": person.get("_links", {})
            },
            "character": {
                "id": character.get("id"),
                "url": character.get("url"),
                "name": character.get("name"),
                "image": {
                    "medium": character.get("image", {}).get("medium") if character.get("image") else None,
                    "original": character.get("image", {}).get("original") if character.get("image") else None
                },
                "_links": character.get("_links", {})
            },
            "self": member.get("self"),
            "voice": member.get("voice")
        })
    
    # VERBOSE: Cast statistics
    voice_actors = len([c for c in cast if c.get("voice")])
    live_actors = len(cast) - voice_actors
    
    return {
        "success": True,
        "show_id": show_id,
        "total_cast": len(data),
        "statistics": {
            "live_actors": live_actors,
            "voice_actors": voice_actors,
            "country_distribution": countries,
            "gender_distribution": genders
        },
        "cast": cast
    }


def _get_show_crew(show_id: int) -> dict:
    """Get crew information for a TV show."""
    data = _make_request(f"/shows/{show_id}/crew")
    
    if isinstance(data, dict) and "error" in data:
        return data
    
    if not isinstance(data, list):
        return {"error": "Invalid response format", "success": False}
    
    crew = []
    crew_by_role = {}
    
    for member in data:
        person = member.get("person", {})
        crew_type = member.get("type", "Unknown")
        
        crew.append({
            "type": crew_type,
            "person": {
                "id": person.get("id"),
                "name": person.get("name"),
                "country": person.get("country", {}).get("name") if person.get("country") else None
            }
        })
        
        if crew_type not in crew_by_role:
            crew_by_role[crew_type] = []
        crew_by_role[crew_type].append(person.get("name"))
    
    return {
        "success": True,
        "show_id": show_id,
        "total_crew": len(crew),
        "crew": crew[:30],  # Limit output
        "roles_summary": {role: len(names) for role, names in crew_by_role.items()},
        "creators": crew_by_role.get("Creator", []),
        "directors": crew_by_role.get("Director", [])[:5],
        "writers": crew_by_role.get("Writer", [])[:5]
    }


# ============== Tool Handlers ==============

async def on_get_show_info(context: RunContextWrapper, params_str: str) -> Any:
    """Handler for getting show info."""
    params = _parse_params(params_str)
    show_id = params.get("show_id")
    
    if not show_id:
        return {"error": "show_id is required", "success": False}
    
    result = _get_show_info(int(show_id))
    return result


async def on_get_show_episodes(context: RunContextWrapper, params_str: str) -> Any:
    """Handler for getting show episodes."""
    params = _parse_params(params_str)
    show_id = params.get("show_id")
    
    if not show_id:
        return {"error": "show_id is required", "success": False}
    
    result = _get_show_episodes(int(show_id))
    return result


async def on_get_show_seasons(context: RunContextWrapper, params_str: str) -> Any:
    """Handler for getting show seasons."""
    params = _parse_params(params_str)
    show_id = params.get("show_id")
    
    if not show_id:
        return {"error": "show_id is required", "success": False}
    
    result = _get_show_seasons(int(show_id))
    return result


async def on_get_show_cast(context: RunContextWrapper, params_str: str) -> Any:
    """Handler for getting show cast."""
    params = _parse_params(params_str)
    show_id = params.get("show_id")
    
    if not show_id:
        return {"error": "show_id is required", "success": False}
    
    result = _get_show_cast(int(show_id))
    return result


async def on_get_show_crew(context: RunContextWrapper, params_str: str) -> Any:
    """Handler for getting show crew."""
    params = _parse_params(params_str)
    show_id = params.get("show_id")
    
    if not show_id:
        return {"error": "show_id is required", "success": False}
    
    result = _get_show_crew(int(show_id))
    return result


# ============== Tool Definitions ==============

tool_tvmaze_get_show_info = FunctionTool(
    name='local-tvmaze_get_show_info',
    description='''Get detailed information about a TV show.

**Returns:** dict:
{
  "success": bool,
  "show": {
    "id": int,
    "name": str,
    "type": str,
    "language": str,
    "genres": [str],
    "status": str,
    "runtime": int,
    "averageRuntime": int,
    "premiered": str,
    "ended": str | null,
    "officialSite": str | null,
    "rating": float | null,
    "weight": int,
    "network": str | null,
    "country": str | null,
    "webChannel": str | null,
    "summary": str,
    "schedule": {"time": str, "days": [str]},
    "image": str | null
  }
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "show_id": {
                "type": "integer",
                "description": "The TVMaze ID of the TV show"
            }
        },
        "required": ["show_id"]
    },
    on_invoke_tool=on_get_show_info
)

tool_tvmaze_get_show_episodes = FunctionTool(
    name='local-tvmaze_get_show_episodes',
    description='''Get all episodes for a TV show.

**Returns:** dict:
{
  "success": bool,
  "show_id": int,
  "total_episodes": int,
  "episodes": [
    {
      "id": int,
      "name": str,
      "season": int,
      "number": int,
      "airdate": str,
      "runtime": int,
      "rating": float | null,
      "summary": str
    }
  ],
  "season_statistics": [{"season": int, "episode_count": int, "average_rating": float | null}],
  "total_runtime_minutes": int
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "show_id": {
                "type": "integer",
                "description": "The TVMaze ID of the TV show"
            }
        },
        "required": ["show_id"]
    },
    on_invoke_tool=on_get_show_episodes
)

tool_tvmaze_get_show_seasons = FunctionTool(
    name='local-tvmaze_get_show_seasons',
    description='''Get season information for a TV show.

**Returns:** dict:
{
  "success": bool,
  "show_id": int,
  "total_seasons": int,
  "seasons": [
    {
      "id": int,
      "number": int,
      "name": str | null,
      "episodeOrder": int | null,
      "premiereDate": str,
      "endDate": str | null,
      "network": str | null
    }
  ],
  "total_ordered_episodes": int
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "show_id": {
                "type": "integer",
                "description": "The TVMaze ID of the TV show"
            }
        },
        "required": ["show_id"]
    },
    on_invoke_tool=on_get_show_seasons
)

tool_tvmaze_get_show_cast = FunctionTool(
    name='local-tvmaze_get_show_cast',
    description='''Get cast information for a TV show.

**Returns:** dict:
{
  "success": bool,
  "show_id": int,
  "total_cast": int,
  "cast": [
    {
      "person": {"id": int, "name": str, "birthday": str | null, "country": str | null, "gender": str},
      "character": {"id": int, "name": str},
      "self": bool,
      "voice": bool
    }
  ],
  "main_cast_count": int
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "show_id": {
                "type": "integer",
                "description": "The TVMaze ID of the TV show"
            }
        },
        "required": ["show_id"]
    },
    on_invoke_tool=on_get_show_cast
)

tool_tvmaze_get_show_crew = FunctionTool(
    name='local-tvmaze_get_show_crew',
    description='''Get crew information for a TV show.

**Returns:** dict:
{
  "success": bool,
  "show_id": int,
  "total_crew": int,
  "crew": [{"type": str, "person": {"id": int, "name": str, "country": str | null}}],
  "roles_summary": {"Creator": int, "Director": int, "Writer": int, ...},
  "creators": [str],
  "directors": [str],
  "writers": [str]
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "show_id": {
                "type": "integer",
                "description": "The TVMaze ID of the TV show"
            }
        },
        "required": ["show_id"]
    },
    on_invoke_tool=on_get_show_crew
)


# Export all tools as a list
tvmaze_tools = [
    tool_tvmaze_get_show_info,
    tool_tvmaze_get_show_episodes,
    tool_tvmaze_get_show_seasons,
    tool_tvmaze_get_show_cast,
    tool_tvmaze_get_show_crew,
]

