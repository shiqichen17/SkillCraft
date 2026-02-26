"""
NASA API Tools

Provides tools to access NASA's open data APIs.
Designed for skill mode scenarios with space/astronomy data.

API Documentation: https://api.nasa.gov/
Uses DEMO_KEY for basic access (rate limited).
"""

import json
import time
from typing import Any
from agents.tool import FunctionTool, RunContextWrapper
import requests
from datetime import datetime, timedelta

# Base URLs for NASA APIs
NASA_API_KEY = "DEMO_KEY"  # Demo key for basic access
APOD_URL = "https://api.nasa.gov/planetary/apod"
NEO_URL = "https://api.nasa.gov/neo/rest/v1"
MARS_ROVER_URL = "https://api.nasa.gov/mars-photos/api/v1"

# Rate limiting configuration
# NASA DEMO_KEY allows 30 requests/hour, 50 requests/day
API_RETRY_COUNT = 3
API_BASE_DELAY = 2  # Base delay in seconds between retries
API_REQUEST_DELAY = 0.5  # Delay before each request


def _make_request(url: str, params: dict = None, max_retries: int = API_RETRY_COUNT) -> Any:
    """Make a request to NASA API with error handling and automatic retry.
    
    Implements exponential backoff for rate limiting (429) errors.
    Also handles non-JSON responses (e.g., HTML error pages) gracefully.
    """
    headers = {"User-Agent": "DikaNong-PatternReuse/1.0"}
    if params is None:
        params = {}
    params["api_key"] = NASA_API_KEY
    
    # Small delay before each request to avoid hitting rate limits
    time.sleep(API_REQUEST_DELAY)
    
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            
            # Check for rate limiting
            if response.status_code == 429:
                if attempt < max_retries - 1:
                    delay = API_BASE_DELAY * (2 ** attempt)
                    time.sleep(delay)
                    continue
                else:
                    return {"error": "Rate limit exceeded after retries", "success": False}
            
            # Check for HTML response (API down or wrong endpoint)
            content_type = response.headers.get('content-type', '')
            if 'text/html' in content_type:
                return {"error": f"API returned HTML instead of JSON (status {response.status_code})", "success": False}
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                time.sleep(API_BASE_DELAY)
                continue
            return {"error": "Request timeout after retries", "success": False}
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1 and "429" in str(e):
                delay = API_BASE_DELAY * (2 ** attempt)
                time.sleep(delay)
                continue
            return {"error": str(e), "success": False}
        except json.JSONDecodeError:
            return {"error": "Invalid JSON response", "success": False}
    
    return {"error": "Max retries exceeded", "success": False}


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

def _get_apod(date: str = None) -> dict:
    """Get Astronomy Picture of the Day."""
    params = {}
    if date:
        params["date"] = date
    
    data = _make_request(APOD_URL, params)
    
    if isinstance(data, dict) and "error" in data and data.get("success") is False:
        return data
    
    if data.get("error"):
        return {"error": data.get("error", {}).get("message", "Unknown error"), "success": False}
    
    return {
        "success": True,
        "apod": {
            "title": data.get("title"),
            "date": data.get("date"),
            "explanation": data.get("explanation"),
            "url": data.get("url"),
            "hdurl": data.get("hdurl"),
            "media_type": data.get("media_type"),
            "copyright": data.get("copyright")
        }
    }


def _get_multiple_apod(count: int = 5) -> dict:
    """Get multiple random Astronomy Pictures of the Day."""
    params = {"count": min(count, 10)}
    
    data = _make_request(APOD_URL, params)
    
    if isinstance(data, dict) and "error" in data:
        return data
    
    if not isinstance(data, list):
        return {"error": "Unexpected response format", "success": False}
    
    pictures = []
    media_types = {"image": 0, "video": 0}
    
    for item in data:
        media_type = item.get("media_type", "image")
        media_types[media_type] = media_types.get(media_type, 0) + 1
        
        pictures.append({
            "title": item.get("title"),
            "date": item.get("date"),
            "explanation": item.get("explanation", "")[:200] + "..." if len(item.get("explanation", "")) > 200 else item.get("explanation"),
            "url": item.get("url"),
            "media_type": media_type
        })
    
    return {
        "success": True,
        "count": len(pictures),
        "pictures": pictures,
        "statistics": {
            "media_type_distribution": media_types,
            "date_range": {
                "earliest": min(p.get("date", "") for p in pictures),
                "latest": max(p.get("date", "") for p in pictures)
            }
        }
    }


def _get_neo_feed(start_date: str = None, end_date: str = None) -> dict:
    """Get Near Earth Objects feed."""
    if not start_date:
        start_date = datetime.now().strftime("%Y-%m-%d")
    if not end_date:
        end_date = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")
    
    params = {
        "start_date": start_date,
        "end_date": end_date
    }
    
    data = _make_request(f"{NEO_URL}/feed", params)
    
    if isinstance(data, dict) and "error" in data and data.get("success") is False:
        return data
    
    if data.get("error"):
        return {"error": str(data.get("error")), "success": False}
    
    neo_objects = data.get("near_earth_objects", {})
    
    all_neos = []
    hazardous_count = 0
    
    for date, neos in neo_objects.items():
        for neo in neos:
            is_hazardous = neo.get("is_potentially_hazardous_asteroid", False)
            if is_hazardous:
                hazardous_count += 1
            
            diameter = neo.get("estimated_diameter", {}).get("meters", {})
            
            all_neos.append({
                "id": neo.get("id"),
                "name": neo.get("name"),
                "date": date,
                "is_hazardous": is_hazardous,
                "diameter_meters": {
                    "min": round(diameter.get("estimated_diameter_min", 0), 2),
                    "max": round(diameter.get("estimated_diameter_max", 0), 2)
                },
                "miss_distance_km": round(float(neo.get("close_approach_data", [{}])[0].get("miss_distance", {}).get("kilometers", 0)), 0)
            })
    
    return {
        "success": True,
        "date_range": {"start": start_date, "end": end_date},
        "total_count": data.get("element_count", len(all_neos)),
        "hazardous_count": hazardous_count,
        "neo_objects": all_neos[:15]  # Limit output
    }


def _get_mars_photos(rover: str = "curiosity", sol: int = 1000) -> dict:
    """Get Mars rover photos."""
    rover = rover.lower()
    
    params = {"sol": sol}
    
    data = _make_request(f"{MARS_ROVER_URL}/rovers/{rover}/photos", params)
    
    if isinstance(data, dict) and "error" in data and data.get("success") is False:
        return data
    
    photos = data.get("photos", [])[:10]  # Limit to 10
    
    cameras = {}
    for photo in photos:
        camera = photo.get("camera", {}).get("name", "Unknown")
        cameras[camera] = cameras.get(camera, 0) + 1
    
    photo_list = []
    for photo in photos:
        photo_list.append({
            "id": photo.get("id"),
            "sol": photo.get("sol"),
            "earth_date": photo.get("earth_date"),
            "camera": photo.get("camera", {}).get("full_name"),
            "img_src": photo.get("img_src")
        })
    
    rover_info = photos[0].get("rover", {}) if photos else {}
    
    return {
        "success": True,
        "rover": rover,
        "sol": sol,
        "total_photos": len(data.get("photos", [])),
        "returned_count": len(photo_list),
        "photos": photo_list,
        "camera_distribution": cameras,
        "rover_info": {
            "name": rover_info.get("name"),
            "landing_date": rover_info.get("landing_date"),
            "status": rover_info.get("status"),
            "max_sol": rover_info.get("max_sol")
        }
    }


def _get_asteroid_details(asteroid_id: str) -> dict:
    """Get detailed information about a specific asteroid."""
    url = f"{NEO_URL}/{asteroid_id}"
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e), "success": False}
    
    # Extract close approach data
    close_approaches = data.get("close_approach_data", [])[:5]
    approaches = []
    for ca in close_approaches:
        approaches.append({
            "date": ca.get("close_approach_date"),
            "relative_velocity_kph": ca.get("relative_velocity", {}).get("kilometers_per_hour"),
            "miss_distance_km": ca.get("miss_distance", {}).get("kilometers"),
            "orbiting_body": ca.get("orbiting_body")
        })
    
    est_diameter = data.get("estimated_diameter", {})
    
    return {
        "success": True,
        "asteroid": {
            "id": data.get("id"),
            "name": data.get("name"),
            "nasa_jpl_url": data.get("nasa_jpl_url"),
            "is_potentially_hazardous": data.get("is_potentially_hazardous_asteroid"),
            "is_sentry_object": data.get("is_sentry_object"),
            "absolute_magnitude": data.get("absolute_magnitude_h")
        },
        "estimated_diameter": {
            "kilometers": {
                "min": est_diameter.get("kilometers", {}).get("estimated_diameter_min"),
                "max": est_diameter.get("kilometers", {}).get("estimated_diameter_max")
            },
            "meters": {
                "min": est_diameter.get("meters", {}).get("estimated_diameter_min"),
                "max": est_diameter.get("meters", {}).get("estimated_diameter_max")
            }
        },
        "orbital_data": {
            "orbit_id": data.get("orbital_data", {}).get("orbit_id"),
            "orbit_class": data.get("orbital_data", {}).get("orbit_class", {}).get("orbit_class_type"),
            "orbit_class_description": data.get("orbital_data", {}).get("orbit_class", {}).get("orbit_class_description"),
            "eccentricity": data.get("orbital_data", {}).get("eccentricity"),
            "orbital_period": data.get("orbital_data", {}).get("orbital_period")
        },
        "close_approaches": approaches
    }


# ============== Tool Handlers ==============

async def on_get_apod(context: RunContextWrapper, params_str: str) -> Any:
    """Handler for APOD."""
    params = _parse_params(params_str)
    date = params.get("date")
    
    result = _get_apod(date)
    return result


async def on_get_multiple_apod(context: RunContextWrapper, params_str: str) -> Any:
    """Handler for multiple APODs."""
    params = _parse_params(params_str)
    count = params.get("count", 5)
    
    result = _get_multiple_apod(int(count))
    return result


async def on_get_neo_feed(context: RunContextWrapper, params_str: str) -> Any:
    """Handler for NEO feed."""
    params = _parse_params(params_str)
    start_date = params.get("start_date")
    end_date = params.get("end_date")
    
    result = _get_neo_feed(start_date, end_date)
    return result


async def on_get_mars_photos(context: RunContextWrapper, params_str: str) -> Any:
    """Handler for Mars photos."""
    params = _parse_params(params_str)
    rover = params.get("rover", "curiosity")
    sol = params.get("sol", 1000)
    
    result = _get_mars_photos(rover, int(sol))
    return result


async def on_get_asteroid_details(context: RunContextWrapper, params_str: str) -> Any:
    """Handler for asteroid details."""
    params = _parse_params(params_str)
    asteroid_id = params.get("asteroid_id")
    
    if not asteroid_id:
        return {"error": "asteroid_id is required", "success": False}
    
    result = _get_asteroid_details(str(asteroid_id))
    return result


# ============== Tool Definitions ==============

tool_nasa_apod = FunctionTool(
    name='local-nasa_apod',
    description='''Get Astronomy Picture of the Day (APOD) from NASA.

**Returns:** dict:
{
  "success": bool,
  "apod": {
    "title": str,
    "date": str,
    "explanation": str,
    "url": str,
    "hdurl": str | null,
    "media_type": str,
    "copyright": str | null
  }
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "date": {
                "type": "string",
                "description": "Date in YYYY-MM-DD format (optional, defaults to today)"
            }
        }
    },
    on_invoke_tool=on_get_apod
)

tool_nasa_multiple_apod = FunctionTool(
    name='local-nasa_random_apod',
    description='''Get multiple random Astronomy Pictures of the Day.

**Returns:** dict:
{
  "success": bool,
  "count": int,
  "pictures": [
    {
      "title": str,
      "date": str,
      "explanation": str,
      "url": str,
      "media_type": str
    }
  ],
  "statistics": {
    "media_type_distribution": {"image": int, "video": int},
    "date_range": {"earliest": str, "latest": str}
  }
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "count": {
                "type": "integer",
                "description": "Number of random APODs to fetch (default 5, max 10)"
            }
        }
    },
    on_invoke_tool=on_get_multiple_apod
)

tool_nasa_neo = FunctionTool(
    name='local-nasa_neo_feed',
    description='''Get Near Earth Objects (asteroids) approaching Earth.

**Returns:** dict:
{
  "success": bool,
  "date_range": {"start": str, "end": str},
  "total_count": int,
  "hazardous_count": int,
  "neo_objects": [
    {
      "id": str,
      "name": str,
      "date": str,
      "is_hazardous": bool,
      "diameter_meters": {"min": float, "max": float},
      "miss_distance_km": float
    }
  ]
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "start_date": {
                "type": "string",
                "description": "Start date in YYYY-MM-DD format"
            },
            "end_date": {
                "type": "string",
                "description": "End date in YYYY-MM-DD format (max 7 days from start)"
            }
        }
    },
    on_invoke_tool=on_get_neo_feed
)

tool_nasa_mars = FunctionTool(
    name='local-nasa_mars_photos',
    description='''Get photos from Mars rovers (Curiosity, Opportunity, Spirit).

**Returns:** dict:
{
  "success": bool,
  "rover": str,
  "sol": int,
  "total_photos": int,
  "returned_count": int,
  "photos": [
    {
      "id": int,
      "sol": int,
      "earth_date": str,
      "camera": str,
      "img_src": str
    }
  ],
  "camera_distribution": {"FHAZ": int, "RHAZ": int, ...},
  "rover_info": {
    "name": str,
    "landing_date": str,
    "status": str,
    "max_sol": int
  }
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "rover": {
                "type": "string",
                "description": "Rover name: curiosity, opportunity, or spirit (default: curiosity)"
            },
            "sol": {
                "type": "integer",
                "description": "Martian sol (day) to get photos from (default: 1000)"
            }
        }
    },
    on_invoke_tool=on_get_mars_photos
)


tool_nasa_asteroid = FunctionTool(
    name='local-nasa_asteroid_details',
    description='''Get detailed information about a specific asteroid by its ID.

**Returns:** dict:
{
  "success": bool,
  "asteroid": {
    "id": str,                        # Asteroid ID
    "name": str,                      # Official name
    "nasa_jpl_url": str,              # NASA JPL page URL
    "is_potentially_hazardous": bool, # Hazardous classification
    "is_sentry_object": bool,         # Sentry monitoring status
    "absolute_magnitude": float       # H magnitude
  },
  "estimated_diameter": {
    "kilometers": {"min": float, "max": float},
    "meters": {"min": float, "max": float}
  },
  "orbital_data": {
    "orbit_id": str,                  # Orbit solution ID
    "orbit_class": str,               # Class type (e.g., "APO", "AMO")
    "orbit_class_description": str,   # Human-readable description
    "eccentricity": str,              # Orbital eccentricity
    "orbital_period": str             # Period in days
  },
  "close_approaches": [               # Up to 5 close approaches
    {
      "date": str,                    # Close approach date
      "relative_velocity_kph": str,   # Speed in km/h
      "miss_distance_km": str,        # Distance in km
      "orbiting_body": str            # Body being orbited (e.g., "Earth")
    }
  ]
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "asteroid_id": {
                "type": "string",
                "description": "NASA asteroid ID (e.g., '3542519' from NEO feed)"
            }
        },
        "required": ["asteroid_id"]
    },
    on_invoke_tool=on_get_asteroid_details
)


# Export all tools as a list
nasa_tools = [
    tool_nasa_apod,
    tool_nasa_multiple_apod,
    tool_nasa_neo,
    tool_nasa_mars,
    tool_nasa_asteroid,
]

