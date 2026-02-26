"""
Random User API Tools

Provides tools to generate random user profiles for testing/demo purposes.
Designed for skill mode scenarios with structured user data.

API Documentation: https://randomuser.me/documentation
No authentication required.
"""

import json
from typing import Any
from agents.tool import FunctionTool, RunContextWrapper
import requests

# Base URL for Random User API
RANDOMUSER_BASE_URL = "https://randomuser.me/api"


def _make_request(params: dict = None) -> dict:
    """Make a request to Random User API with error handling."""
    headers = {"User-Agent": "DikaNong-PatternReuse/1.0"}
    
    try:
        response = requests.get(RANDOMUSER_BASE_URL, headers=headers, params=params, timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        return {"error": "Request timeout", "success": False}
    except requests.exceptions.RequestException as e:
        return {"error": str(e), "success": False}
    except json.JSONDecodeError:
        return {"error": "Invalid JSON response", "success": False}


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


def _format_user(user: dict) -> dict:
    """Format a user object for output - ENHANCED VERBOSE version."""
    name = user.get("name", {})
    location = user.get("location", {})
    dob = user.get("dob", {})
    login = user.get("login", {})
    registered = user.get("registered", {})
    id_info = user.get("id", {})
    timezone = location.get("timezone", {})
    coordinates = location.get("coordinates", {})
    street = location.get("street", {})
    
    # Calculate age group
    age = dob.get("age", 0)
    if age < 25:
        age_group = "young_adult"
    elif age < 40:
        age_group = "adult"
    elif age < 55:
        age_group = "middle_aged"
    else:
        age_group = "senior"
    
    # Calculate generation
    birth_year = int(dob.get("date", "1990")[:4]) if dob.get("date") else 1990
    if birth_year >= 1997:
        generation = "Gen Z"
    elif birth_year >= 1981:
        generation = "Millennial"
    elif birth_year >= 1965:
        generation = "Gen X"
    elif birth_year >= 1946:
        generation = "Baby Boomer"
    else:
        generation = "Silent Generation"
    
    first_name = name.get("first", "")
    last_name = name.get("last", "")
    
    return {
        "name": {
            "title": name.get("title"),
            "first": first_name,
            "last": last_name,
            "full_name": f"{first_name} {last_name}",
            "display_name": f"{name.get('title', '')} {first_name} {last_name}".strip(),
            "initials": f"{first_name[:1]}{last_name[:1]}" if first_name and last_name else "",
            "first_name_length": len(first_name),
            "last_name_length": len(last_name)
        },
        "gender": user.get("gender"),
        "email": user.get("email"),
        "email_domain": user.get("email", "").split("@")[-1] if user.get("email") else None,
        "phone": user.get("phone"),
        "cell": user.get("cell"),
        "age": age,
        "age_group": age_group,
        "generation": generation,
        "birth_year": birth_year,
        "date_of_birth": dob.get("date", "")[:10],
        "date_of_birth_full": dob.get("date"),
        "location": {
            "street_number": street.get("number"),
            "street_name": street.get("name"),
            "street": f"{street.get('number', '')} {street.get('name', '')}",
            "city": location.get("city"),
            "state": location.get("state"),
            "country": location.get("country"),
            "postcode": str(location.get("postcode", "")),
            "coordinates": {
                "latitude": coordinates.get("latitude"),
                "longitude": coordinates.get("longitude")
            },
            "timezone": {
                "description": timezone.get("description"),
                "offset": timezone.get("offset")
            },
            "full_address": f"{street.get('number', '')} {street.get('name', '')}, {location.get('city', '')}, {location.get('state', '')} {location.get('postcode', '')}, {location.get('country', '')}"
        },
        "login": {
            "username": login.get("username"),
            "uuid": login.get("uuid"),
            "password": login.get("password"),
            "salt": login.get("salt"),
            "md5": login.get("md5"),
            "sha1": login.get("sha1"),
            "sha256": login.get("sha256")
        },
        "registered": {
            "date": registered.get("date"),
            "age": registered.get("age"),
            "date_short": registered.get("date", "")[:10] if registered.get("date") else None
        },
        "id": {
            "name": id_info.get("name"),
            "value": id_info.get("value")
        },
        "picture": {
            "large": user.get("picture", {}).get("large"),
            "medium": user.get("picture", {}).get("medium"),
            "thumbnail": user.get("picture", {}).get("thumbnail")
        },
        "nationality": user.get("nat"),
        "nat": user.get("nat")
    }


# ============== Tool Implementation Functions ==============

def _get_random_user(nationality: str = None, gender: str = None) -> dict:
    """Get a single random user."""
    params = {}
    if nationality:
        params["nat"] = nationality
    if gender:
        params["gender"] = gender
    
    data = _make_request(params)
    
    if "error" in data and data.get("success") is False:
        return data
    
    users = data.get("results", [])
    if not users:
        return {"error": "No users returned", "success": False}
    
    return {
        "success": True,
        "user": _format_user(users[0])
    }


def _get_multiple_users(count: int = 5, nationality: str = None, gender: str = None) -> dict:
    """Get multiple random users - ENHANCED VERBOSE version."""
    # VERBOSE: Return 10 users instead of 5 for more data
    actual_count = min(count * 2, 20) if count <= 10 else min(count, 20)
    params = {"results": actual_count}
    if nationality:
        params["nat"] = nationality
    if gender:
        params["gender"] = gender
    
    data = _make_request(params)
    
    if "error" in data and data.get("success") is False:
        return data
    
    users = data.get("results", [])
    formatted_users = [_format_user(u) for u in users]
    
    # VERBOSE: Calculate comprehensive statistics
    genders = {}
    nationalities = {}
    age_groups = {"young_adult": 0, "adult": 0, "middle_aged": 0, "senior": 0}
    generations = {}
    cities = {}
    states = {}
    email_domains = {}
    ages = []
    
    for user in formatted_users:
        # Gender stats
        g = user.get("gender", "unknown")
        genders[g] = genders.get(g, 0) + 1
        
        # Nationality stats
        nat = user.get("nationality", "unknown")
        nationalities[nat] = nationalities.get(nat, 0) + 1
        
        # Age stats
        age = user.get("age", 0)
        ages.append(age)
        
        # Age group stats
        age_group = user.get("age_group", "unknown")
        if age_group in age_groups:
            age_groups[age_group] += 1
        
        # Generation stats
        gen = user.get("generation", "unknown")
        generations[gen] = generations.get(gen, 0) + 1
        
        # Location stats
        city = user.get("location", {}).get("city", "unknown")
        cities[city] = cities.get(city, 0) + 1
        
        state = user.get("location", {}).get("state", "unknown")
        states[state] = states.get(state, 0) + 1
        
        # Email domain stats
        domain = user.get("email_domain", "unknown")
        email_domains[domain] = email_domains.get(domain, 0) + 1
    
    # Sort cities and states by count
    top_cities = dict(sorted(cities.items(), key=lambda x: x[1], reverse=True)[:10])
    top_states = dict(sorted(states.items(), key=lambda x: x[1], reverse=True)[:10])
    
    return {
        "success": True,
        "count": len(formatted_users),
        "requested_count": count,
        "actual_count": actual_count,
        "users": formatted_users,
        "statistics": {
            "gender_distribution": genders,
            "nationality_distribution": nationalities,
            "average_age": round(sum(ages) / len(ages), 1) if ages else 0,
            "min_age": min(ages) if ages else 0,
            "max_age": max(ages) if ages else 0,
            "age_range": max(ages) - min(ages) if ages else 0,
            "median_age": sorted(ages)[len(ages)//2] if ages else 0,
            "age_group_distribution": age_groups,
            "generation_distribution": generations,
            "top_cities": top_cities,
            "top_states": top_states,
            "unique_cities": len(cities),
            "unique_states": len(states),
            "email_domain_distribution": email_domains
        },
        "query_info": {
            "nationality_filter": nationality,
            "gender_filter": gender,
            "api_version": "1.4"
        }
    }


def _get_users_by_nationality(nationality: str, count: int = 5) -> dict:
    """Get random users from a specific nationality."""
    return _get_multiple_users(count, nationality=nationality)


def _get_user_profile(nationality: str = None) -> dict:
    """Get a user profile with extended information for a specific nationality - ENHANCED."""
    params = {}
    if nationality:
        params["nat"] = nationality
    
    data = _make_request(params)
    
    if "error" in data and data.get("success") is False:
        return data
    
    users = data.get("results", [])
    if not users:
        return {"error": "No users returned", "success": False}
    
    user = _format_user(users[0])
    info = data.get("info", {})
    user["seed"] = info.get("seed")
    
    # VERBOSE: Add API metadata
    return {
        "success": True,
        "user": user,
        "api_info": {
            "seed": info.get("seed"),
            "results": info.get("results"),
            "page": info.get("page"),
            "version": info.get("version")
        },
        "query_info": {
            "nationality_filter": nationality,
            "api_version": "1.4"
        }
    }


def _get_detailed_user(nationality: str = None) -> dict:
    """Get a random user with detailed location and contact info - ENHANCED VERBOSE."""
    params = {}
    if nationality:
        params["nat"] = nationality
    
    data = _make_request(params)
    
    if "error" in data and data.get("success") is False:
        return data
    
    users = data.get("results", [])
    if not users:
        return {"error": "No users returned", "success": False}
    
    user = users[0]
    name = user.get("name", {})
    loc = user.get("location", {})
    login = user.get("login", {})
    dob = user.get("dob", {})
    registered = user.get("registered", {})
    id_info = user.get("id", {})
    street = loc.get("street", {})
    timezone = loc.get("timezone", {})
    coordinates = loc.get("coordinates", {})
    
    first_name = name.get("first", "")
    last_name = name.get("last", "")
    
    # Calculate age group
    age = dob.get("age", 0)
    if age < 25:
        age_group = "young_adult"
    elif age < 40:
        age_group = "adult"
    elif age < 55:
        age_group = "middle_aged"
    else:
        age_group = "senior"
    
    # Calculate generation
    birth_year = int(dob.get("date", "1990")[:4]) if dob.get("date") else 1990
    if birth_year >= 1997:
        generation = "Gen Z"
    elif birth_year >= 1981:
        generation = "Millennial"
    elif birth_year >= 1965:
        generation = "Gen X"
    elif birth_year >= 1946:
        generation = "Baby Boomer"
    else:
        generation = "Silent Generation"
    
    return {
        "success": True,
        "user": {
            "name": f"{first_name} {last_name}",
            "title": name.get("title"),
            "first_name": first_name,
            "last_name": last_name,
            "display_name": f"{name.get('title', '')} {first_name} {last_name}".strip(),
            "initials": f"{first_name[:1]}{last_name[:1]}" if first_name and last_name else "",
            "gender": user.get("gender"),
            "nationality": user.get("nat"),
            "email": user.get("email"),
            "email_domain": user.get("email", "").split("@")[-1] if user.get("email") else None,
            "phone": user.get("phone"),
            "cell": user.get("cell")
        },
        "location": {
            "street_number": street.get("number"),
            "street_name": street.get("name"),
            "street": f"{street.get('number')} {street.get('name')}",
            "city": loc.get("city"),
            "state": loc.get("state"),
            "country": loc.get("country"),
            "postcode": str(loc.get("postcode")),
            "full_address": f"{street.get('number', '')} {street.get('name', '')}, {loc.get('city', '')}, {loc.get('state', '')} {loc.get('postcode', '')}, {loc.get('country', '')}",
            "coordinates": {
                "latitude": coordinates.get("latitude"),
                "longitude": coordinates.get("longitude")
            },
            "timezone": {
                "description": timezone.get("description"),
                "offset": timezone.get("offset")
            }
        },
        "account": {
            "username": login.get("username"),
            "uuid": login.get("uuid"),
            "password": login.get("password"),
            "salt": login.get("salt"),
            "md5": login.get("md5"),
            "sha1": login.get("sha1"),
            "sha256": login.get("sha256"),
            "registered_date": registered.get("date"),
            "registered_date_short": registered.get("date", "")[:10] if registered.get("date") else None,
            "registered_age": registered.get("age")
        },
        "personal": {
            "date_of_birth": dob.get("date"),
            "date_of_birth_short": dob.get("date", "")[:10] if dob.get("date") else None,
            "birth_year": birth_year,
            "age": age,
            "age_group": age_group,
            "generation": generation,
            "picture_large": user.get("picture", {}).get("large"),
            "picture_medium": user.get("picture", {}).get("medium"),
            "picture_thumbnail": user.get("picture", {}).get("thumbnail")
        },
        "id": {
            "name": id_info.get("name"),
            "value": id_info.get("value")
        },
        "query_info": {
            "nationality_filter": nationality,
            "api_version": "1.4"
        }
    }


# ============== Tool Handlers ==============

async def on_get_random_user(context: RunContextWrapper, params_str: str) -> Any:
    """Handler for getting a random user."""
    params = _parse_params(params_str)
    nationality = params.get("nationality")
    gender = params.get("gender")
    
    result = _get_random_user(nationality, gender)
    return result


async def on_get_multiple_users(context: RunContextWrapper, params_str: str) -> Any:
    """Handler for getting multiple users."""
    params = _parse_params(params_str)
    count = params.get("count", 5)
    nationality = params.get("nationality")
    gender = params.get("gender")
    
    result = _get_multiple_users(int(count), nationality, gender)
    return result


async def on_get_users_by_nationality(context: RunContextWrapper, params_str: str) -> Any:
    """Handler for getting users by nationality."""
    params = _parse_params(params_str)
    nationality = params.get("nationality")
    count = params.get("count", 5)
    
    if not nationality:
        return {"error": "nationality is required", "success": False}
    
    result = _get_users_by_nationality(nationality, int(count))
    return result


async def on_get_user_profile(context: RunContextWrapper, params_str: str) -> Any:
    """Handler for getting a user profile with extended information."""
    params = _parse_params(params_str)
    nationality = params.get("nationality")
    
    result = _get_user_profile(nationality)
    return result


async def on_get_detailed_user(context: RunContextWrapper, params_str: str) -> Any:
    """Handler for getting detailed user info."""
    params = _parse_params(params_str)
    nationality = params.get("nationality")
    
    result = _get_detailed_user(nationality)
    return result


# ============== Tool Definitions ==============

tool_randomuser_single = FunctionTool(
    name='local-randomuser_get_user',
    description='''Get a single random user profile.

**Returns:** dict:
{
  "success": bool,
  "user": {
    "name": {"title": str, "first": str, "last": str, "full_name": str},
    "gender": str,
    "email": str,
    "phone": str,
    "cell": str,
    "age": int,
    "age_group": str,
    "date_of_birth": str,
    "location": {"street": str, "city": str, "state": str, "country": str, "postcode": str, "timezone": str},
    "login": {"username": str, "uuid": str},
    "picture": {"large": str, "medium": str, "thumbnail": str},
    "nationality": str
  }
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "nationality": {
                "type": "string",
                "description": "Filter by nationality (e.g., 'US', 'GB', 'DE', 'FR')"
            },
            "gender": {
                "type": "string",
                "description": "Filter by gender ('male' or 'female')"
            }
        }
    },
    on_invoke_tool=on_get_random_user
)

tool_randomuser_multiple = FunctionTool(
    name='local-randomuser_get_users',
    description='''Get multiple random user profiles.

**Returns:** dict:
{
  "success": bool,
  "count": int,
  "users": [user_object],
  "statistics": {
    "gender_distribution": {"male": int, "female": int},
    "nationality_distribution": {"US": int, "GB": int, ...},
    "average_age": float
  }
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "count": {
                "type": "integer",
                "description": "Number of users to generate (max 20, default 5)"
            },
            "nationality": {
                "type": "string",
                "description": "Filter by nationality code"
            },
            "gender": {
                "type": "string",
                "description": "Filter by gender"
            }
        }
    },
    on_invoke_tool=on_get_multiple_users
)

tool_randomuser_by_nationality = FunctionTool(
    name='local-randomuser_by_nationality',
    description='''Get random users from a specific nationality.

**Returns:** dict:
{
  "success": bool,
  "count": int,
  "users": [user_object],
  "statistics": {"gender_distribution": {...}, "nationality_distribution": {...}, "average_age": float}
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "nationality": {
                "type": "string",
                "description": "Nationality code (e.g., 'US', 'GB', 'DE', 'AU', 'BR')"
            },
            "count": {
                "type": "integer",
                "description": "Number of users (default 5)"
            }
        },
        "required": ["nationality"]
    },
    on_invoke_tool=on_get_users_by_nationality
)

tool_randomuser_profile = FunctionTool(
    name='local-randomuser_profile',
    description='''Get user profile with extended information for a specific nationality.

**Returns:** dict:
{
  "success": bool,
  "user": {
    "name": {"title": str, "first": str, "last": str, "full_name": str},
    "gender": str,
    "email": str,
    "phone": str,
    "cell": str,
    "age": int,
    "age_group": str,              # "young_adult", "adult", "middle_aged", "senior"
    "date_of_birth": str,
    "location": {
      "street": str,
      "city": str,
      "state": str,
      "country": str,
      "postcode": str,
      "timezone": str
    },
    "login": {"username": str, "uuid": str},
    "picture": {"large": str, "medium": str, "thumbnail": str},
    "nationality": str,
    "seed": str                    # Can be used to reproduce this exact user
  }
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "nationality": {
                "type": "string",
                "description": "Nationality code (e.g., 'US', 'GB', 'DE', 'FR', 'AU')"
            }
        }
    },
    on_invoke_tool=on_get_user_profile
)


tool_randomuser_detailed = FunctionTool(
    name='local-randomuser_detailed',
    description='''Get a random user with detailed location, contact, and account information.

**Returns:** dict:
{
  "success": bool,
  "user": {
    "name": str,                      # Full name
    "gender": str,                    # "male" or "female"
    "nationality": str,               # 2-letter country code
    "email": str,                     # Email address
    "phone": str,                     # Phone number
    "cell": str                       # Cell phone number
  },
  "location": {
    "street": str,                    # Street address
    "city": str,                      # City name
    "state": str,                     # State/province
    "country": str,                   # Country name
    "postcode": str,                  # Postal code
    "coordinates": {
      "latitude": str,                # Latitude
      "longitude": str                # Longitude
    },
    "timezone": str                   # Timezone description
  },
  "account": {
    "username": str,                  # Username
    "uuid": str,                      # Unique identifier
    "registered_date": str,           # Registration date (ISO format)
    "registered_age": int             # Years since registration
  },
  "personal": {
    "date_of_birth": str,             # DOB (ISO format)
    "age": int,                       # Current age
    "picture_large": str,             # Large profile picture URL
    "picture_thumbnail": str          # Thumbnail picture URL
  }
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "nationality": {
                "type": "string",
                "description": "Optional 2-letter nationality code (e.g., 'US', 'GB', 'AU')"
            }
        }
    },
    on_invoke_tool=on_get_detailed_user
)


# Export all tools as a list
randomuser_tools = [
    tool_randomuser_single,
    tool_randomuser_multiple,
    tool_randomuser_by_nationality,
    tool_randomuser_profile,
    tool_randomuser_detailed,
]

