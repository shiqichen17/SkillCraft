"""
MusicBrainz API Tools

Provides tools to query artist and release information from MusicBrainz.
Designed for skill mode scenarios with structured music data.

API Documentation: https://musicbrainz.org/doc/MusicBrainz_API
Rate Limit: 1 request/second (enforced by User-Agent requirement)
"""

import json
import time
from typing import Any
from agents.tool import FunctionTool, RunContextWrapper
import requests

# Base URL for MusicBrainz API
MUSICBRAINZ_BASE_URL = "https://musicbrainz.org/ws/2"

# Rate limiting
_last_request_time = 0
_MIN_REQUEST_INTERVAL = 1.1  # Slightly over 1 second


def _rate_limit():
    """Ensure we don't exceed rate limits."""
    global _last_request_time
    current_time = time.time()
    time_since_last = current_time - _last_request_time
    if time_since_last < _MIN_REQUEST_INTERVAL:
        time.sleep(_MIN_REQUEST_INTERVAL - time_since_last)
    _last_request_time = time.time()


def _make_request(endpoint: str, params: dict = None) -> dict:
    """Make a request to MusicBrainz API with error handling."""
    _rate_limit()
    
    url = f"{MUSICBRAINZ_BASE_URL}{endpoint}"
    if params is None:
        params = {}
    params["fmt"] = "json"
    
    headers = {
        "User-Agent": "DikaNong-PatternReuse/1.0 (research@example.com)",
        "Accept": "application/json"
    }
    
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

def _get_artist(artist_id: str) -> dict:
    """Get detailed information about an artist."""
    data = _make_request(f"/artist/{artist_id}", {"inc": "releases+release-groups+tags"})
    
    if "error" in data:
        return data
    
    # Extract release groups (albums)
    release_groups = data.get("release-groups", [])
    albums = []
    for rg in release_groups[:10]:
        albums.append({
            "id": rg.get("id"),
            "title": rg.get("title"),
            "type": rg.get("primary-type"),
            "first_release_date": rg.get("first-release-date")
        })
    
    # Extract tags
    tags = data.get("tags", [])
    tag_list = [t.get("name") for t in sorted(tags, key=lambda x: x.get("count", 0), reverse=True)[:10]]
    
    return {
        "success": True,
        "artist": {
            "id": data.get("id"),
            "name": data.get("name"),
            "sort_name": data.get("sort-name"),
            "type": data.get("type"),
            "country": data.get("country"),
            "disambiguation": data.get("disambiguation"),
            "life_span": {
                "begin": data.get("life-span", {}).get("begin"),
                "end": data.get("life-span", {}).get("end"),
                "ended": data.get("life-span", {}).get("ended")
            },
            "area": data.get("area", {}).get("name") if data.get("area") else None,
            "albums": albums,
            "album_count": len(release_groups),
            "genres": tag_list
        }
    }


def _get_artist_releases(artist_id: str, release_type: str = "album") -> dict:
    """Get releases (albums) by an artist."""
    data = _make_request(f"/release-group", {
        "artist": artist_id,
        "type": release_type,
        "limit": 25
    })
    
    if "error" in data:
        return data
    
    release_groups = data.get("release-groups", [])
    
    releases = []
    for rg in release_groups:
        releases.append({
            "id": rg.get("id"),
            "title": rg.get("title"),
            "type": rg.get("primary-type"),
            "secondary_types": rg.get("secondary-types", []),
            "first_release_date": rg.get("first-release-date")
        })
    
    return {
        "success": True,
        "artist_id": artist_id,
        "release_type": release_type,
        "total_count": data.get("release-group-count", len(releases)),
        "releases": releases
    }


def _search_artist(query: str) -> dict:
    """Search for artists by name."""
    data = _make_request("/artist", {"query": query, "limit": 10})
    
    if "error" in data:
        return data
    
    artists = data.get("artists", [])
    
    results = []
    for artist in artists:
        results.append({
            "id": artist.get("id"),
            "name": artist.get("name"),
            "sort_name": artist.get("sort-name"),
            "type": artist.get("type"),
            "country": artist.get("country"),
            "score": artist.get("score"),
            "disambiguation": artist.get("disambiguation")
        })
    
    return {
        "success": True,
        "query": query,
        "count": data.get("count", len(artists)),
        "artists": results
    }


def _get_artist_relations(artist_id: str) -> dict:
    """Get related artists and collaborations."""
    data = _make_request(f"/artist/{artist_id}", {"inc": "artist-rels+url-rels+tags"})
    
    if "error" in data:
        return data
    
    # Extract related artists
    relations = data.get("relations", [])
    artist_relations = []
    url_relations = []
    
    for rel in relations:
        rel_type = rel.get("type")
        if "artist" in rel:
            artist_relations.append({
                "type": rel_type,
                "artist_id": rel["artist"].get("id"),
                "artist_name": rel["artist"].get("name"),
                "attributes": rel.get("attributes", [])
            })
        elif "url" in rel:
            url_relations.append({
                "type": rel_type,
                "url": rel["url"].get("resource")
            })
    
    # Extract tags (genres)
    tags = data.get("tags", [])
    tag_list = [{"name": t.get("name"), "count": t.get("count")} for t in tags]
    tag_list.sort(key=lambda x: x.get("count", 0), reverse=True)
    
    return {
        "success": True,
        "artist_id": artist_id,
        "name": data.get("name"),
        "related_artists": artist_relations[:15],
        "external_links": url_relations[:10],
        "tags_genres": tag_list[:10],
        "relation_count": len(artist_relations),
        "total_tags": len(tags)
    }


def _get_release_details(release_id: str) -> dict:
    """Get detailed information about a release."""
    data = _make_request(f"/release/{release_id}", {"inc": "recordings+artists"})
    
    if "error" in data:
        return data
    
    # Extract tracks
    media = data.get("media", [])
    tracks = []
    for medium in media:
        for track in medium.get("tracks", [])[:15]:
            recording = track.get("recording", {})
            tracks.append({
                "position": track.get("position"),
                "title": recording.get("title"),
                "length_ms": recording.get("length"),
                "length_formatted": f"{recording.get('length', 0) // 60000}:{(recording.get('length', 0) // 1000) % 60:02d}" if recording.get('length') else None
            })
    
    return {
        "success": True,
        "release": {
            "id": data.get("id"),
            "title": data.get("title"),
            "status": data.get("status"),
            "date": data.get("date"),
            "country": data.get("country"),
            "barcode": data.get("barcode"),
            "artists": [a.get("artist", {}).get("name") for a in data.get("artist-credit", [])],
            "track_count": sum(m.get("track-count", 0) for m in media),
            "tracks": tracks
        }
    }


# ============== Tool Handlers ==============

async def on_get_artist(context: RunContextWrapper, params_str: str) -> Any:
    """Handler for getting artist info."""
    params = _parse_params(params_str)
    artist_id = params.get("artist_id")
    
    if not artist_id:
        return {"error": "artist_id is required", "success": False}
    
    result = _get_artist(str(artist_id))
    return result


async def on_get_artist_relations(context: RunContextWrapper, params_str: str) -> Any:
    """Handler for getting artist relations."""
    params = _parse_params(params_str)
    artist_id = params.get("artist_id")
    
    if not artist_id:
        return {"error": "artist_id is required", "success": False}
    
    result = _get_artist_relations(str(artist_id))
    return result


async def on_get_artist_releases(context: RunContextWrapper, params_str: str) -> Any:
    """Handler for getting artist releases."""
    params = _parse_params(params_str)
    artist_id = params.get("artist_id")
    release_type = params.get("release_type", "album")
    
    if not artist_id:
        return {"error": "artist_id is required", "success": False}
    
    result = _get_artist_releases(str(artist_id), release_type)
    return result


async def on_search_artist(context: RunContextWrapper, params_str: str) -> Any:
    """Handler for searching artists."""
    params = _parse_params(params_str)
    query = params.get("query")
    
    if not query:
        return {"error": "query is required", "success": False}
    
    result = _search_artist(query)
    return result


async def on_get_release_details(context: RunContextWrapper, params_str: str) -> Any:
    """Handler for getting release details."""
    params = _parse_params(params_str)
    release_id = params.get("release_id")
    
    if not release_id:
        return {"error": "release_id is required", "success": False}
    
    result = _get_release_details(str(release_id))
    return result


# ============== Tool Definitions ==============

tool_musicbrainz_get_artist = FunctionTool(
    name='local-musicbrainz_get_artist',
    description='''Get detailed information about a music artist.

**Returns:** dict:
{
  "success": bool,
  "artist": {
    "id": str,
    "name": str,
    "sort_name": str,
    "type": str,
    "country": str | null,
    "disambiguation": str | null,
    "life_span": {"begin": str | null (ISO date like "1970-06-27"), "end": str | null (ISO date), "ended": bool},
    "area": str | null,
    "albums": [{"id": str, "title": str, "type": str, "first_release_date": str | null}],
    "album_count": int,
    "genres": [str]
  }
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "artist_id": {
                "type": "string",
                "description": "The MusicBrainz UUID of the artist"
            }
        },
        "required": ["artist_id"]
    },
    on_invoke_tool=on_get_artist
)

tool_musicbrainz_get_releases = FunctionTool(
    name='local-musicbrainz_get_releases',
    description='''Get releases (albums, singles, etc.) by an artist.

**Returns:** dict:
{
  "success": bool,
  "artist_id": str,
  "release_type": str,
  "total_count": int,
  "releases": [
    {
      "id": str,
      "title": str,
      "type": str,
      "secondary_types": [str],
      "first_release_date": str | null
    }
  ]
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "artist_id": {
                "type": "string",
                "description": "The MusicBrainz UUID of the artist"
            },
            "release_type": {
                "type": "string",
                "description": "Type of release: album, single, ep, compilation (default: album)"
            }
        },
        "required": ["artist_id"]
    },
    on_invoke_tool=on_get_artist_releases
)

tool_musicbrainz_search = FunctionTool(
    name='local-musicbrainz_search_artist',
    description='''Search for artists by name.

**Returns:** dict:
{
  "success": bool,
  "query": str,
  "count": int,
  "artists": [
    {
      "id": str,
      "name": str,
      "sort_name": str,
      "type": str,
      "country": str | null,
      "score": int,
      "disambiguation": str | null
    }
  ]
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Artist name to search for"
            }
        },
        "required": ["query"]
    },
    on_invoke_tool=on_search_artist
)

tool_musicbrainz_release_details = FunctionTool(
    name='local-musicbrainz_release_details',
    description='''Get detailed information about a release including track listing.

**Returns:** dict:
{
  "success": bool,
  "release": {
    "id": str,
    "title": str,
    "status": str,
    "date": str | null,
    "country": str | null,
    "barcode": str | null,
    "artists": [str],
    "track_count": int,
    "tracks": [
      {
        "position": int,
        "title": str,
        "length_ms": int | null,
        "length_formatted": str | null
      }
    ]
  }
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "release_id": {
                "type": "string",
                "description": "The MusicBrainz UUID of the release"
            }
        },
        "required": ["release_id"]
    },
    on_invoke_tool=on_get_release_details
)


tool_musicbrainz_artist_relations = FunctionTool(
    name='local-musicbrainz_artist_relations',
    description='''Get related artists, collaborations, external links, and genre tags for an artist.

**Returns:** dict:
{
  "success": bool,
  "artist_id": str,                   # Artist UUID
  "name": str,                        # Artist name
  "related_artists": [                # Up to 15 related artists
    {
      "type": str,                    # Relation type (e.g., "member of band", "collaboration")
      "artist_id": str,               # Related artist's UUID
      "artist_name": str,             # Related artist's name
      "attributes": [str]             # Relation attributes
    }
  ],
  "external_links": [                 # Up to 10 external links
    {
      "type": str,                    # Link type (e.g., "official homepage", "wikipedia")
      "url": str                      # URL
    }
  ],
  "tags_genres": [                    # Up to 10 top tags/genres
    {
      "name": str,                    # Tag name (e.g., "rock", "pop")
      "count": int                    # Tag vote count
    }
  ],
  "relation_count": int,              # Total number of artist relations
  "total_tags": int                   # Total number of tags
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "artist_id": {
                "type": "string",
                "description": "The MusicBrainz UUID of the artist"
            }
        },
        "required": ["artist_id"]
    },
    on_invoke_tool=on_get_artist_relations
)


# Export all tools as a list
musicbrainz_tools = [
    tool_musicbrainz_get_artist,
    tool_musicbrainz_get_releases,
    tool_musicbrainz_search,
    tool_musicbrainz_release_details,
    tool_musicbrainz_artist_relations,
]

