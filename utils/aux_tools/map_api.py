"""
Map/Routing API Tools for WebArena Reuse Tasks

These tools provide access to OpenStreetMap-based APIs for geocoding and routing.
Uses Nominatim for geocoding and OSRM for routing calculations.
Designed for skill mode scenarios where multiple similar queries are executed.
"""

import json
from typing import Any
from agents.tool import FunctionTool, RunContextWrapper
import requests
import urllib.parse

# API endpoints
NOMINATIM_URL = "https://nominatim.openstreetmap.org"
OSRM_URL = "http://router.project-osrm.org"

# User-Agent header (required by Nominatim)
HEADERS = {
    "User-Agent": "DikaNong-WebArena-Tasks/1.0"
}


# ============== Core Functions ==============

def _map_geocode(place_name: str) -> dict:
    """Convert a place name to coordinates (geocoding)."""
    try:
        url = f"{NOMINATIM_URL}/search"
        params = {
            "q": place_name,
            "format": "json",
            "limit": 1,
            "addressdetails": 1
        }
        
        response = requests.get(url, params=params, headers=HEADERS, timeout=30)
        
        if response.status_code == 200:
            results = response.json()
            if results:
                r = results[0]
                return {
                    "success": True,
                    "place": {
                        "name": r.get("display_name"),
                        "lat": float(r.get("lat")),
                        "lon": float(r.get("lon")),
                        "type": r.get("type"),
                        "address": r.get("address", {})
                    }
                }
            else:
                return {"success": False, "error": f"Place '{place_name}' not found"}
        else:
            return {"success": False, "error": f"API error: {response.status_code}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _map_get_route(origin: str, destination: str, mode: str = "driving") -> dict:
    """Get route information between two places."""
    try:
        # First, geocode both places
        origin_result = _map_geocode(origin)
        if not origin_result.get("success"):
            return {"success": False, "error": f"Could not find origin: {origin}"}
        
        dest_result = _map_geocode(destination)
        if not dest_result.get("success"):
            return {"success": False, "error": f"Could not find destination: {destination}"}
        
        origin_coords = origin_result["place"]
        dest_coords = dest_result["place"]
        
        # Map mode to OSRM profile
        profile_map = {
            "driving": "car",
            "walking": "foot",
            "cycling": "bike"
        }
        profile = profile_map.get(mode, "car")
        
        # Get route from OSRM
        url = f"{OSRM_URL}/route/v1/{profile}/{origin_coords['lon']},{origin_coords['lat']};{dest_coords['lon']},{dest_coords['lat']}"
        params = {
            "overview": "false",
            "steps": "false"
        }
        
        response = requests.get(url, params=params, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("code") == "Ok" and data.get("routes"):
                route = data["routes"][0]
                duration_seconds = route.get("duration", 0)
                distance_meters = route.get("distance", 0)
                
                # Format duration
                hours = int(duration_seconds // 3600)
                minutes = int((duration_seconds % 3600) // 60)
                if hours > 0:
                    duration_str = f"{hours} hour{'s' if hours > 1 else ''} {minutes} minute{'s' if minutes != 1 else ''}"
                else:
                    duration_str = f"{minutes} minute{'s' if minutes != 1 else ''}"
                
                # Format distance
                if distance_meters >= 1000:
                    distance_str = f"{distance_meters/1000:.1f} km"
                else:
                    distance_str = f"{int(distance_meters)} m"
                
                return {
                    "success": True,
                    "route": {
                        "origin": origin_coords["name"],
                        "destination": dest_coords["name"],
                        "mode": mode,
                        "duration_seconds": duration_seconds,
                        "duration": duration_str,
                        "distance_meters": distance_meters,
                        "distance": distance_str
                    }
                }
            else:
                return {"success": False, "error": "Could not calculate route"}
        else:
            return {"success": False, "error": f"Routing API error: {response.status_code}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _map_search_nearby(place_name: str, category: str, radius_km: float = 5.0) -> dict:
    """Search for nearby places of a specific category."""
    try:
        # First, geocode the center location
        center_result = _map_geocode(place_name)
        if not center_result.get("success"):
            return {"success": False, "error": f"Could not find location: {place_name}"}
        
        center = center_result["place"]
        
        # Search using Nominatim
        url = f"{NOMINATIM_URL}/search"
        params = {
            "q": category,
            "format": "json",
            "limit": 10,
            "viewbox": f"{center['lon']-radius_km/111},{center['lat']+radius_km/111},{center['lon']+radius_km/111},{center['lat']-radius_km/111}",
            "bounded": 1
        }
        
        response = requests.get(url, params=params, headers=HEADERS, timeout=30)
        
        if response.status_code == 200:
            results = response.json()
            places = [{
                "name": r.get("display_name", "").split(",")[0],
                "full_name": r.get("display_name"),
                "lat": float(r.get("lat")),
                "lon": float(r.get("lon")),
                "type": r.get("type")
            } for r in results]
            
            return {
                "success": True,
                "center": center["name"],
                "category": category,
                "radius_km": radius_km,
                "places": places,
                "count": len(places)
            }
        else:
            return {"success": False, "error": f"API error: {response.status_code}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _map_reverse_geocode(lat: float, lon: float) -> dict:
    """Convert coordinates to a place name (reverse geocoding)."""
    try:
        url = f"{NOMINATIM_URL}/reverse"
        params = {
            "lat": lat,
            "lon": lon,
            "format": "json",
            "addressdetails": 1
        }
        
        response = requests.get(url, params=params, headers=HEADERS, timeout=30)
        
        if response.status_code == 200:
            r = response.json()
            if "error" in r:
                return {"success": False, "error": r["error"]}
            
            return {
                "success": True,
                "place": {
                    "name": r.get("display_name"),
                    "lat": float(r.get("lat")),
                    "lon": float(r.get("lon")),
                    "address": r.get("address", {})
                }
            }
        else:
            return {"success": False, "error": f"API error: {response.status_code}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============== Tool Handlers ==============

async def on_map_geocode(context: RunContextWrapper, params_str: str) -> Any:
    params = json.loads(params_str)
    place_name = params.get("place_name", "")
    result = _map_geocode(place_name)
    return result


async def on_map_get_route(context: RunContextWrapper, params_str: str) -> Any:
    params = json.loads(params_str)
    origin = params.get("origin", "")
    destination = params.get("destination", "")
    mode = params.get("mode", "driving")
    result = _map_get_route(origin, destination, mode)
    return result


async def on_map_search_nearby(context: RunContextWrapper, params_str: str) -> Any:
    params = json.loads(params_str)
    place_name = params.get("place_name", "")
    category = params.get("category", "")
    radius_km = params.get("radius_km", 5.0)
    result = _map_search_nearby(place_name, category, radius_km)
    return result


async def on_map_reverse_geocode(context: RunContextWrapper, params_str: str) -> Any:
    params = json.loads(params_str)
    lat = params.get("lat", 0)
    lon = params.get("lon", 0)
    result = _map_reverse_geocode(lat, lon)
    return result


# ============== Tool Definitions ==============

tool_map_geocode = FunctionTool(
    name='local-map_geocode',
    description='Convert a place name to geographic coordinates (latitude, longitude). Works with addresses, landmarks, cities, etc.',
    params_json_schema={
        "type": "object",
        "properties": {
            "place_name": {
                "type": "string",
                "description": "Name of the place to geocode (e.g., 'Eiffel Tower, Paris' or '123 Main St, New York')"
            }
        },
        "required": ["place_name"]
    },
    on_invoke_tool=on_map_geocode
)

tool_map_get_route = FunctionTool(
    name='local-map_get_route',
    description='Get route information between two places including estimated travel time and distance.',
    params_json_schema={
        "type": "object",
        "properties": {
            "origin": {
                "type": "string",
                "description": "Starting place name (e.g., 'Central Park, New York')"
            },
            "destination": {
                "type": "string",
                "description": "Destination place name"
            },
            "mode": {
                "type": "string",
                "enum": ["driving", "walking", "cycling"],
                "description": "Travel mode"
            }
        },
        "required": ["origin", "destination"]
    },
    on_invoke_tool=on_map_get_route
)

tool_map_search_nearby = FunctionTool(
    name='local-map_search_nearby',
    description='Search for nearby places of a specific category (e.g., restaurants, hotels, parks) around a location.',
    params_json_schema={
        "type": "object",
        "properties": {
            "place_name": {
                "type": "string",
                "description": "Center location name for the search"
            },
            "category": {
                "type": "string",
                "description": "Category to search (e.g., 'restaurant', 'hospital', 'hotel', 'park', 'museum')"
            },
            "radius_km": {
                "type": "number",
                "description": "Search radius in kilometers"
            }
        },
        "required": ["place_name", "category"]
    },
    on_invoke_tool=on_map_search_nearby
)

tool_map_reverse_geocode = FunctionTool(
    name='local-map_reverse_geocode',
    description='Convert geographic coordinates (latitude, longitude) to a place name and address.',
    params_json_schema={
        "type": "object",
        "properties": {
            "lat": {
                "type": "number",
                "description": "Latitude"
            },
            "lon": {
                "type": "number",
                "description": "Longitude"
            }
        },
        "required": ["lat", "lon"]
    },
    on_invoke_tool=on_map_reverse_geocode
)

# Export all tools as a list
map_api_tools = [
    tool_map_geocode,
    tool_map_get_route,
    tool_map_search_nearby,
    tool_map_reverse_geocode,
]
