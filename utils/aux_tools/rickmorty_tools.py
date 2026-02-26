"""
Rick and Morty API Tools

Provides tools to query character, location, and episode information from Rick and Morty.
Designed for skill mode scenarios with structured character data.

API Documentation: https://rickandmortyapi.com/documentation
No authentication required.
"""

import json
from typing import Any
from agents.tool import FunctionTool, RunContextWrapper
import requests

# Base URL for Rick and Morty API
RICKMORTY_BASE_URL = "https://rickandmortyapi.com/api"


def _make_request(endpoint: str, params: dict = None) -> dict:
    """Make a request to the Rick and Morty API with error handling."""
    url = f"{RICKMORTY_BASE_URL}{endpoint}"
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

def _get_character(character_id: int) -> dict:
    """Get detailed information about a character with VERBOSE extended data for skill mode."""
    import re
    data = _make_request(f"/character/{character_id}")
    
    if "error" in data and data.get("error") != None:
        return {"error": data.get("error"), "success": False}
    
    # Parse episode URLs to get IDs and codes
    episode_urls = data.get("episode", [])
    episode_ids = [url.split("/")[-1] for url in episode_urls]
    
    # Parse origin and location IDs
    origin_url = data.get("origin", {}).get("url", "")
    origin_id = origin_url.split("/")[-1] if origin_url else None
    location_url = data.get("location", {}).get("url", "")
    location_id = location_url.split("/")[-1] if location_url else None
    
    # Determine character category
    species = data.get("species", "")
    char_type = data.get("type") or "Normal"
    if "Rick" in data.get("name", ""):
        category = "Main Character - Rick Variant"
    elif "Morty" in data.get("name", ""):
        category = "Main Character - Morty Variant"
    elif species == "Human":
        category = "Human Character"
    elif species == "Alien":
        category = "Alien Character"
    else:
        category = f"{species} Character"
    
    # VERBOSE: Fetch FULL episode details for all episodes
    episode_details = []
    season_breakdown = {}
    if episode_ids:
        # ULTRA VERBOSE: Batch fetch ALL episodes (all 51)
        batch_ids = ",".join(episode_ids[:51])
        episodes_data = _make_request(f"/episode/{batch_ids}")
        
        if isinstance(episodes_data, list):
            for ep in episodes_data:
                ep_code = ep.get("episode", "")
                season = episode_num = None
                match = re.match(r"S(\d+)E(\d+)", ep_code)
                if match:
                    season = int(match.group(1))
                    episode_num = int(match.group(2))
                    season_key = f"Season {season}"
                    season_breakdown[season_key] = season_breakdown.get(season_key, 0) + 1
                
                # Get all character IDs in this episode
                ep_char_urls = ep.get("characters", [])
                ep_char_ids = [int(c.split("/")[-1]) for c in ep_char_urls if c.split("/")[-1].isdigit()]
                
                # ULTRA VERBOSE: Extended episode data for skill mode
                episode_details.append({
                    "id": ep.get("id"),
                    "name": ep.get("name"),
                    "episode_code": ep_code,
                    "season": season,
                    "episode_in_season": episode_num,
                    "air_date": ep.get("air_date"),
                    "total_characters": len(ep_char_urls),
                    "character_ids": ep_char_ids,
                    "main_chars_present": [cid for cid in ep_char_ids if cid in [1,2,3,4,5]],
                    "has_all_main_chars": len([cid for cid in ep_char_ids if cid in [1,2,3,4,5]]) == 5,
                    "created": ep.get("created"),
                    "url": ep.get("url"),
                    # ULTRA VERBOSE: Additional episode metadata
                    "character_density": round(len(ep_char_urls) / 22, 2) if ep_char_urls else 0,
                    "is_pilot": episode_num == 1 and season == 1,
                    "is_finale": ep_code in ["S01E11", "S02E10", "S03E10", "S04E10", "S05E10"],
                    "character_appearances_list": ep_char_ids[:30],
                    "recurring_chars": [cid for cid in ep_char_ids if cid <= 20],
                    "guest_char_count": len([cid for cid in ep_char_ids if cid > 20]),
                    "episode_type": "adventure" if len(ep_char_urls) > 15 else "character-focused",
                    "api_urls": {
                        "self": ep.get("url"),
                        "characters": [f"https://rickandmortyapi.com/api/character/{cid}" for cid in ep_char_ids[:10]]
                    }
                })
        elif isinstance(episodes_data, dict) and "id" in episodes_data:
            ep = episodes_data
            ep_code = ep.get("episode", "")
            match = re.match(r"S(\d+)E(\d+)", ep_code)
            season = episode_num = None
            if match:
                season = int(match.group(1))
                episode_num = int(match.group(2))
                season_key = f"Season {season}"
                season_breakdown[season_key] = season_breakdown.get(season_key, 0) + 1
            ep_char_urls = ep.get("characters", [])
            ep_char_ids = [int(c.split("/")[-1]) for c in ep_char_urls if c.split("/")[-1].isdigit()]
            episode_details.append({
                "id": ep.get("id"),
                "name": ep.get("name"),
                "episode_code": ep_code,
                "season": season,
                "episode_in_season": episode_num,
                "air_date": ep.get("air_date"),
                "total_characters": len(ep_char_urls),
                "character_ids": ep_char_ids,
                "main_chars_present": [cid for cid in ep_char_ids if cid in [1,2,3,4,5]],
                "has_all_main_chars": len([cid for cid in ep_char_ids if cid in [1,2,3,4,5]]) == 5,
                "created": ep.get("created"),
                "url": ep.get("url")
            })
    
    # Calculate episode statistics
    avg_chars_per_episode = sum(ep.get("total_characters", 0) for ep in episode_details) / len(episode_details) if episode_details else 0
    episodes_with_all_main = sum(1 for ep in episode_details if ep.get("has_all_main_chars"))
    
    return {
        "success": True,
        "character": {
            "id": data.get("id"),
            "name": data.get("name"),
            "status": data.get("status"),
            "species": species,
            "type": char_type,
            "gender": data.get("gender"),
            "category": category,
            "origin": {
                "name": data.get("origin", {}).get("name"),
                "url": data.get("origin", {}).get("url"),
                "id": int(origin_id) if origin_id and origin_id.isdigit() else None
            },
            "location": {
                "name": data.get("location", {}).get("name"),
                "url": data.get("location", {}).get("url"),
                "id": int(location_id) if location_id and location_id.isdigit() else None
            },
            "image": data.get("image"),
            "episode_data": {
                "total_count": len(episode_urls),
                "first_episode_id": int(episode_ids[0]) if episode_ids else None,
                "last_episode_id": int(episode_ids[-1]) if episode_ids else None,
                "all_episode_ids": [int(eid) for eid in episode_ids],
                "seasons_appeared": list(set([
                    f"S{(int(eid)-1)//11 + 1:02d}" for eid in episode_ids 
                    if eid.isdigit() and int(eid) <= 51
                ])) if episode_ids else [],
                "season_breakdown": season_breakdown,
                "avg_characters_per_episode": round(avg_chars_per_episode, 1),
                "episodes_with_all_main_characters": episodes_with_all_main,
                # VERBOSE: Full episode details for pattern to extract summary from
                "episode_details": episode_details
            },
            "metadata": {
                "created": data.get("created"),
                "api_url": f"https://rickandmortyapi.com/api/character/{character_id}",
                "is_main_character": "Rick" in data.get("name", "") or "Morty" in data.get("name", ""),
                "is_alive": data.get("status") == "Alive",
                "is_human": species == "Human"
            }
        }
    }


def _get_location(location_id: int) -> dict:
    """Get detailed information about a location with VERBOSE resident data for skill mode."""
    data = _make_request(f"/location/{location_id}")
    
    if "error" in data and data.get("error") != None:
        return {"error": data.get("error"), "success": False}
    
    # Parse resident URLs
    resident_urls = data.get("residents", [])
    resident_ids = [int(r.split("/")[-1]) for r in resident_urls if r.split("/")[-1].isdigit()]
    
    # Determine location category based on type
    loc_type = data.get("type", "")
    dimension = data.get("dimension", "")
    
    if "Earth" in data.get("name", "") or dimension == "Dimension C-137":
        category = "Earth Location"
    elif "Citadel" in data.get("name", ""):
        category = "Citadel Location"
    elif loc_type == "Planet":
        category = "Alien Planet"
    elif loc_type == "Space station":
        category = "Space Station"
    elif loc_type == "Microverse":
        category = "Microverse Location"
    else:
        category = f"{loc_type} Location" if loc_type else "Unknown Location"
    
    # VERBOSE: Fetch FULL details for ALL residents
    resident_details = []
    if resident_ids:
        # Batch fetch up to 50 residents
        batch_ids = ",".join(str(rid) for rid in resident_ids[:50])
        residents_data = _make_request(f"/character/{batch_ids}")
        
        if isinstance(residents_data, list):
            for char in residents_data:
                ep_urls = char.get("episode", [])
                ep_ids = [int(e.split("/")[-1]) for e in ep_urls if e.split("/")[-1].isdigit()]
                # ULTRA VERBOSE: Extended resident data
                resident_details.append({
                    "id": char.get("id"),
                    "name": char.get("name"),
                    "status": char.get("status"),
                    "species": char.get("species"),
                    "type": char.get("type") or "Normal",
                    "gender": char.get("gender"),
                    "origin_name": char.get("origin", {}).get("name"),
                    "origin_url": char.get("origin", {}).get("url"),
                    "location_name": char.get("location", {}).get("name"),
                    "location_url": char.get("location", {}).get("url"),
                    "image": char.get("image"),
                    "episode_count": len(ep_urls),
                    "episode_ids": ep_ids,  # All episodes, not just 20
                    "first_episode": ep_ids[0] if ep_ids else None,
                    "last_episode": ep_ids[-1] if ep_ids else None,
                    "created": char.get("created"),
                    "url": char.get("url"),
                    # ULTRA VERBOSE: Additional character metadata
                    "is_main_character": char.get("id") in [1, 2, 3, 4, 5],
                    "is_recurring": len(ep_urls) > 5,
                    "appearance_frequency": "frequent" if len(ep_urls) > 20 else "regular" if len(ep_urls) > 5 else "rare",
                    "character_category": "Rick Variant" if "Rick" in char.get("name", "") else "Morty Variant" if "Morty" in char.get("name", "") else char.get("species", "Unknown"),
                    "seasons_appeared": list(set([(eid - 1) // 11 + 1 for eid in ep_ids if eid <= 51])) if ep_ids else [],
                    "api_links": {
                        "character": char.get("url"),
                        "origin": char.get("origin", {}).get("url"),
                        "location": char.get("location", {}).get("url")
                    }
                })
        elif isinstance(residents_data, dict) and "id" in residents_data:
            char = residents_data
            ep_urls = char.get("episode", [])
            ep_ids = [int(e.split("/")[-1]) for e in ep_urls if e.split("/")[-1].isdigit()]
            resident_details.append({
                "id": char.get("id"),
                "name": char.get("name"),
                "status": char.get("status"),
                "species": char.get("species"),
                "type": char.get("type") or "Normal",
                "gender": char.get("gender"),
                "origin_name": char.get("origin", {}).get("name"),
                "origin_url": char.get("origin", {}).get("url"),
                "location_name": char.get("location", {}).get("name"),
                "location_url": char.get("location", {}).get("url"),
                "image": char.get("image"),
                "episode_count": len(ep_urls),
                "episode_ids": ep_ids[:20],
                "first_episode": ep_ids[0] if ep_ids else None,
                "last_episode": ep_ids[-1] if ep_ids else None,
                "created": char.get("created"),
                "url": char.get("url")
            })
    
    # Calculate resident statistics
    species_counts = {}
    status_counts = {}
    gender_counts = {}
    total_episodes = 0
    for r in resident_details:
        sp = r.get("species", "unknown")
        species_counts[sp] = species_counts.get(sp, 0) + 1
        st = r.get("status", "unknown")
        status_counts[st] = status_counts.get(st, 0) + 1
        g = r.get("gender", "unknown")
        gender_counts[g] = gender_counts.get(g, 0) + 1
        total_episodes += r.get("episode_count", 0)
    
    return {
        "success": True,
        "location": {
            "id": data.get("id"),
            "name": data.get("name"),
            "type": loc_type,
            "dimension": dimension,
            "category": category,
            "residents": {
                "total_count": len(resident_urls),
                "resident_ids": resident_ids,
                "has_main_characters": any(rid in [1, 2, 3, 4, 5] for rid in resident_ids),
                "main_character_ids": [rid for rid in resident_ids if rid in [1, 2, 3, 4, 5]],
                "population_category": "Small" if len(resident_ids) < 5 else "Medium" if len(resident_ids) < 20 else "Large",
                "statistics": {
                    "species_distribution": species_counts,
                    "status_distribution": status_counts,
                    "gender_distribution": gender_counts,
                    "total_episode_appearances": total_episodes,
                    "avg_episodes_per_resident": round(total_episodes / len(resident_details), 1) if resident_details else 0
                },
                # VERBOSE: Full resident details for pattern to extract summary from
                "resident_details": resident_details
            },
            "metadata": {
                "created": data.get("created"),
                "api_url": f"https://rickandmortyapi.com/api/location/{location_id}",
                "is_earth": "Earth" in data.get("name", ""),
                "is_c137": dimension == "Dimension C-137",
                "is_known_dimension": dimension not in ["unknown", "Unknown", ""]
            }
        }
    }


def _get_episode(episode_id: int) -> dict:
    """Get detailed information about an episode with VERBOSE character data for skill mode."""
    import re
    data = _make_request(f"/episode/{episode_id}")
    
    if "error" in data and data.get("error") != None:
        return {"error": data.get("error"), "success": False}
    
    # Parse character URLs
    character_urls = data.get("characters", [])
    character_ids = [int(c.split("/")[-1]) for c in character_urls if c.split("/")[-1].isdigit()]
    
    # Parse episode code
    episode_code = data.get("episode", "")
    season_num = episode_num = None
    if episode_code:
        match = re.match(r"S(\d+)E(\d+)", episode_code)
        if match:
            season_num = int(match.group(1))
            episode_num = int(match.group(2))
    
    # Main characters check
    main_char_ids = {1, 2, 3, 4, 5}
    main_chars_present = [cid for cid in character_ids if cid in main_char_ids]
    
    # VERBOSE: Fetch FULL details for ALL characters in this episode
    character_details = []
    if character_ids:
        # Batch fetch up to 40 characters
        batch_ids = ",".join(str(cid) for cid in character_ids[:40])
        chars_data = _make_request(f"/character/{batch_ids}")
        
        if isinstance(chars_data, list):
            for char in chars_data:
                ep_urls = char.get("episode", [])
                ep_ids = [int(e.split("/")[-1]) for e in ep_urls if e.split("/")[-1].isdigit()]
                origin_url = char.get("origin", {}).get("url", "")
                origin_id = origin_url.split("/")[-1] if origin_url else None
                loc_url = char.get("location", {}).get("url", "")
                loc_id = loc_url.split("/")[-1] if loc_url else None
                
                character_details.append({
                    "id": char.get("id"),
                    "name": char.get("name"),
                    "status": char.get("status"),
                    "species": char.get("species"),
                    "type": char.get("type") or "Normal",
                    "gender": char.get("gender"),
                    "origin": {
                        "name": char.get("origin", {}).get("name"),
                        "id": int(origin_id) if origin_id and origin_id.isdigit() else None
                    },
                    "location": {
                        "name": char.get("location", {}).get("name"),
                        "id": int(loc_id) if loc_id and loc_id.isdigit() else None
                    },
                    "image": char.get("image"),
                    "total_episodes": len(ep_urls),
                    "episode_ids": ep_ids,
                    "is_main_character": char.get("id") in main_char_ids,
                    "created": char.get("created"),
                    "url": char.get("url")
                })
        elif isinstance(chars_data, dict) and "id" in chars_data:
            char = chars_data
            ep_urls = char.get("episode", [])
            ep_ids = [int(e.split("/")[-1]) for e in ep_urls if e.split("/")[-1].isdigit()]
            origin_url = char.get("origin", {}).get("url", "")
            origin_id = origin_url.split("/")[-1] if origin_url else None
            loc_url = char.get("location", {}).get("url", "")
            loc_id = loc_url.split("/")[-1] if loc_url else None
            
            character_details.append({
                "id": char.get("id"),
                "name": char.get("name"),
                "status": char.get("status"),
                "species": char.get("species"),
                "type": char.get("type") or "Normal",
                "gender": char.get("gender"),
                "origin": {
                    "name": char.get("origin", {}).get("name"),
                    "id": int(origin_id) if origin_id and origin_id.isdigit() else None
                },
                "location": {
                    "name": char.get("location", {}).get("name"),
                    "id": int(loc_id) if loc_id and loc_id.isdigit() else None
                },
                "image": char.get("image"),
                "total_episodes": len(ep_urls),
                "episode_ids": ep_ids,
                "is_main_character": char.get("id") in main_char_ids,
                "created": char.get("created"),
                "url": char.get("url")
            })
    
    # Calculate character statistics
    species_counts = {}
    status_counts = {}
    gender_counts = {}
    for c in character_details:
        sp = c.get("species", "unknown")
        species_counts[sp] = species_counts.get(sp, 0) + 1
        st = c.get("status", "unknown")
        status_counts[st] = status_counts.get(st, 0) + 1
        g = c.get("gender", "unknown")
        gender_counts[g] = gender_counts.get(g, 0) + 1
    
    return {
        "success": True,
        "episode": {
            "id": data.get("id"),
            "name": data.get("name"),
            "air_date": data.get("air_date"),
            "episode_code": episode_code,
            "season": season_num,
            "episode_in_season": episode_num,
            "characters": {
                "total_count": len(character_urls),
                "character_ids": character_ids,
                "main_characters_present": main_chars_present,
                "has_all_main_characters": len(main_chars_present) == 5,
                "statistics": {
                    "species_distribution": species_counts,
                    "status_distribution": status_counts,
                    "gender_distribution": gender_counts,
                    "main_character_count": len(main_chars_present),
                    "supporting_character_count": len(character_ids) - len(main_chars_present)
                },
                # VERBOSE: Full character details for pattern to extract summary from
                "character_details": character_details
            },
            "metadata": {
                "created": data.get("created"),
                "api_url": f"https://rickandmortyapi.com/api/episode/{episode_id}",
                "is_season_premiere": episode_num == 1 if episode_num else False,
                "is_season_finale": episode_num in [10, 11] if episode_num else False
            }
        }
    }


def _search_characters(name: str = None, status: str = None, species: str = None) -> dict:
    """Search for characters by name, status, or species with VERBOSE extended data for skill mode."""
    params = {}
    if name:
        params["name"] = name
    if status:
        params["status"] = status
    if species:
        params["species"] = species
    
    data = _make_request("/character", params)
    
    if "error" in data and data.get("error") != None:
        return {"error": data.get("error"), "success": False}
    
    results = data.get("results", [])
    info = data.get("info", {})
    
    # VERBOSE: Return up to 20 characters with full episode lists
    characters = []
    for char in results[:20]:
        episode_urls = char.get("episode", [])
        episode_ids = [int(e.split("/")[-1]) for e in episode_urls if e.split("/")[-1].isdigit()]
        
        origin_url = char.get("origin", {}).get("url", "")
        origin_id = origin_url.split("/")[-1] if origin_url else None
        loc_url = char.get("location", {}).get("url", "")
        loc_id = loc_url.split("/")[-1] if loc_url else None
        
        # Determine character category
        char_species = char.get("species", "")
        if "Rick" in char.get("name", ""):
            category = "Rick Variant"
        elif "Morty" in char.get("name", ""):
            category = "Morty Variant"
        elif char_species == "Human":
            category = "Human"
        elif char_species == "Alien":
            category = "Alien"
        else:
            category = char_species or "Unknown"
        
        # Calculate seasons appeared
        seasons = list(set([
            f"S{(int(eid)-1)//11 + 1:02d}" for eid in episode_ids 
            if eid <= 51
        ])) if episode_ids else []
        
        characters.append({
            "id": char.get("id"),
            "name": char.get("name"),
            "status": char.get("status"),
            "species": char.get("species"),
            "type": char.get("type") or "Normal",
            "gender": char.get("gender"),
            "category": category,
            "origin": {
                "name": char.get("origin", {}).get("name"),
                "url": char.get("origin", {}).get("url"),
                "id": int(origin_id) if origin_id and origin_id.isdigit() else None
            },
            "location": {
                "name": char.get("location", {}).get("name"),
                "url": char.get("location", {}).get("url"),
                "id": int(loc_id) if loc_id and loc_id.isdigit() else None
            },
            "image": char.get("image"),
            "episode_count": len(episode_urls),
            "episode_ids": episode_ids,  # VERBOSE: Full episode list
            "first_seen_episode": episode_ids[0] if episode_ids else None,
            "last_seen_episode": episode_ids[-1] if episode_ids else None,
            "seasons_appeared": seasons,
            "is_main_character": char.get("id") in [1, 2, 3, 4, 5],
            "created": char.get("created"),
            "url": char.get("url")
        })
    
    # Calculate statistics
    status_counts = {}
    species_counts = {}
    gender_counts = {}
    category_counts = {}
    total_episodes = 0
    for char in characters:
        s = char.get("status", "unknown")
        status_counts[s] = status_counts.get(s, 0) + 1
        sp = char.get("species", "unknown")
        species_counts[sp] = species_counts.get(sp, 0) + 1
        g = char.get("gender", "unknown")
        gender_counts[g] = gender_counts.get(g, 0) + 1
        cat = char.get("category", "Unknown")
        category_counts[cat] = category_counts.get(cat, 0) + 1
        total_episodes += char.get("episode_count", 0)
    
    return {
        "success": True,
        "query": params,
        "pagination": {
            "total_count": info.get("count", len(results)),
            "pages": info.get("pages", 1),
            "current_page": 1,
            "results_shown": len(characters)
        },
        "statistics": {
            "status_distribution": status_counts,
            "species_distribution": species_counts,
            "gender_distribution": gender_counts,
            "category_distribution": category_counts,
            "total_episode_appearances": total_episodes,
            "avg_episodes_per_character": round(total_episodes / len(characters), 1) if characters else 0,
            "main_characters_found": sum(1 for c in characters if c.get("is_main_character"))
        },
        # VERBOSE: Full character details for pattern to extract summary from
        "characters": characters
    }


def _get_character_episodes(character_id: int) -> dict:
    """Get ALL episodes a character appears in with VERBOSE extended data for skill mode."""
    import re
    char_data = _make_request(f"/character/{character_id}")
    
    if "error" in char_data and char_data.get("error") != None:
        return {"error": char_data.get("error"), "success": False}
    
    episode_urls = char_data.get("episode", [])
    episode_ids = [url.split("/")[-1] for url in episode_urls]
    
    episodes = []
    season_breakdown = {}
    
    if episode_ids:
        # VERBOSE: Fetch ALL episodes (up to 51)
        batch_ids = ",".join(episode_ids[:51])
        episodes_data = _make_request(f"/episode/{batch_ids}")
        
        if isinstance(episodes_data, list):
            for ep in episodes_data:
                ep_code = ep.get("episode", "")
                season = episode_num = None
                match = re.match(r"S(\d+)E(\d+)", ep_code)
                if match:
                    season = int(match.group(1))
                    episode_num = int(match.group(2))
                    season_key = f"Season {season}"
                    season_breakdown[season_key] = season_breakdown.get(season_key, 0) + 1
                
                # VERBOSE: Include ALL character IDs for each episode
                ep_char_urls = ep.get("characters", [])
                ep_char_ids = [int(c.split("/")[-1]) for c in ep_char_urls if c.split("/")[-1].isdigit()]
                
                episodes.append({
                    "id": ep.get("id"),
                    "name": ep.get("name"),
                    "episode_code": ep_code,
                    "season": season,
                    "episode_in_season": episode_num,
                    "air_date": ep.get("air_date"),
                    "total_characters": len(ep_char_urls),
                    "character_ids": ep_char_ids,
                    "main_chars_present": [cid for cid in ep_char_ids if cid in [1,2,3,4,5]],
                    "has_all_main_chars": len([cid for cid in ep_char_ids if cid in [1,2,3,4,5]]) == 5,
                    "created": ep.get("created"),
                    "url": ep.get("url")
                })
        elif isinstance(episodes_data, dict) and "id" in episodes_data:
            ep = episodes_data
            ep_code = ep.get("episode", "")
            season = episode_num = None
            match = re.match(r"S(\d+)E(\d+)", ep_code)
            if match:
                season = int(match.group(1))
                episode_num = int(match.group(2))
                season_key = f"Season {season}"
                season_breakdown[season_key] = season_breakdown.get(season_key, 0) + 1
            
            ep_char_urls = ep.get("characters", [])
            ep_char_ids = [int(c.split("/")[-1]) for c in ep_char_urls if c.split("/")[-1].isdigit()]
            
            episodes.append({
                "id": ep.get("id"),
                "name": ep.get("name"),
                "episode_code": ep_code,
                "season": season,
                "episode_in_season": episode_num,
                "air_date": ep.get("air_date"),
                "total_characters": len(ep_char_urls),
                "character_ids": ep_char_ids,
                "main_chars_present": [cid for cid in ep_char_ids if cid in [1,2,3,4,5]],
                "has_all_main_chars": len([cid for cid in ep_char_ids if cid in [1,2,3,4,5]]) == 5,
                "created": ep.get("created"),
                "url": ep.get("url")
            })
    
    # Calculate episode statistics
    total_chars = sum(ep.get("total_characters", 0) for ep in episodes)
    avg_chars = total_chars / len(episodes) if episodes else 0
    eps_with_all_main = sum(1 for ep in episodes if ep.get("has_all_main_chars"))
    
    return {
        "success": True,
        "character": {
            "id": character_id,
            "name": char_data.get("name"),
            "status": char_data.get("status"),
            "species": char_data.get("species"),
            "gender": char_data.get("gender"),
            "type": char_data.get("type") or "Normal",
            "image": char_data.get("image"),
            "origin_name": char_data.get("origin", {}).get("name"),
            "location_name": char_data.get("location", {}).get("name")
        },
        "episode_summary": {
            "total_episodes": len(episode_urls),
            "episodes_retrieved": len(episodes),
            "season_breakdown": season_breakdown,
            "first_appearance": episodes[0]["episode_code"] if episodes else None,
            "last_appearance": episodes[-1]["episode_code"] if episodes else None,
            "avg_characters_per_episode": round(avg_chars, 1),
            "episodes_with_all_main_characters": eps_with_all_main,
            "total_character_interactions": total_chars
        },
        # VERBOSE: Full episode details for pattern to extract summary from
        "episodes": episodes
    }


# ============== Tool Handlers ==============

async def on_get_character(context: RunContextWrapper, params_str: str) -> Any:
    """Handler for getting character info."""
    params = _parse_params(params_str)
    character_id = params.get("character_id")
    
    if not character_id:
        return {"error": "character_id is required", "success": False}
    
    result = _get_character(int(character_id))
    return result


async def on_get_location(context: RunContextWrapper, params_str: str) -> Any:
    """Handler for getting location info."""
    params = _parse_params(params_str)
    location_id = params.get("location_id")
    
    if not location_id:
        return {"error": "location_id is required", "success": False}
    
    result = _get_location(int(location_id))
    return result


async def on_get_episode(context: RunContextWrapper, params_str: str) -> Any:
    """Handler for getting episode info."""
    params = _parse_params(params_str)
    episode_id = params.get("episode_id")
    
    if not episode_id:
        return {"error": "episode_id is required", "success": False}
    
    result = _get_episode(int(episode_id))
    return result


async def on_search_characters(context: RunContextWrapper, params_str: str) -> Any:
    """Handler for searching characters."""
    params = _parse_params(params_str)
    
    result = _search_characters(
        name=params.get("name"),
        status=params.get("status"),
        species=params.get("species")
    )
    return result


async def on_get_character_episodes(context: RunContextWrapper, params_str: str) -> Any:
    """Handler for getting character episodes."""
    params = _parse_params(params_str)
    character_id = params.get("character_id")
    
    if not character_id:
        return {"error": "character_id is required", "success": False}
    
    result = _get_character_episodes(int(character_id))
    return result


# ============== Tool Definitions ==============

tool_rickmorty_get_character = FunctionTool(
    name='local-rickmorty_get_character',
    description='''Get detailed information about a Rick and Morty character with extended data.

**Returns:** dict:
{
  "success": bool,
  "character": {
    "id": int,
    "name": str,
    "status": str,                    // "Alive", "Dead", "unknown"
    "species": str,                   // "Human", "Alien", etc.
    "type": str,                      // subspecies or "Normal"
    "gender": str,                    // "Male", "Female", "Genderless", "unknown"
    "category": str,                  // "Main Character - Rick Variant", "Human Character", etc.
    "origin": {
      "name": str,
      "url": str,
      "id": int | null
    },
    "location": {
      "name": str,
      "url": str,
      "id": int | null
    },
    "image": str,
    "episode_data": {
      "total_count": int,
      "first_episode_id": int | null,
      "last_episode_id": int | null,
      "all_episode_ids": [int],       // up to 30 episode IDs
      "seasons_appeared": [str]       // ["S01", "S02", ...]
    },
    "metadata": {
      "created": str,
      "api_url": str,
      "is_main_character": bool,
      "is_alive": bool,
      "is_human": bool
    }
  }
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "character_id": {
                "type": "integer",
                "description": "The ID of the character (1-826)"
            }
        },
        "required": ["character_id"]
    },
    on_invoke_tool=on_get_character
)

tool_rickmorty_get_location = FunctionTool(
    name='local-rickmorty_get_location',
    description='''Get detailed information about a location with extended data.

**Returns:** dict:
{
  "success": bool,
  "location": {
    "id": int,
    "name": str,
    "type": str,                      // "Planet", "Space station", "Microverse", etc.
    "dimension": str,                 // "Dimension C-137", "unknown", etc.
    "category": str,                  // "Earth Location", "Alien Planet", "Space Station", etc.
    "residents": {
      "total_count": int,
      "resident_ids": [int],          // up to 20 resident IDs
      "has_main_characters": bool,
      "population_category": str      // "Small", "Medium", "Large"
    },
    "metadata": {
      "created": str,
      "api_url": str,
      "is_earth": bool,
      "is_c137": bool,
      "is_known_dimension": bool
    }
  }
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "location_id": {
                "type": "integer",
                "description": "The ID of the location"
            }
        },
        "required": ["location_id"]
    },
    on_invoke_tool=on_get_location
)

tool_rickmorty_get_episode = FunctionTool(
    name='local-rickmorty_get_episode',
    description='''Get detailed information about an episode with extended data.

**Returns:** dict:
{
  "success": bool,
  "episode": {
    "id": int,
    "name": str,
    "air_date": str,
    "episode_code": str,              // "S01E01" format
    "season": int | null,
    "episode_in_season": int | null,
    "characters": {
      "total_count": int,
      "character_ids": [int],         // up to 25 character IDs
      "main_characters_present": [int], // IDs of main characters (1-5) present
      "has_all_main_characters": bool
    },
    "metadata": {
      "created": str,
      "api_url": str,
      "is_season_premiere": bool,
      "is_season_finale": bool
    }
  }
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "episode_id": {
                "type": "integer",
                "description": "The ID of the episode"
            }
        },
        "required": ["episode_id"]
    },
    on_invoke_tool=on_get_episode
)

tool_rickmorty_search_characters = FunctionTool(
    name='local-rickmorty_search_characters',
    description='''Search for characters by name, status, or species with extended data.

**Returns:** dict:
{
  "success": bool,
  "query": {"name": str, "status": str, "species": str},
  "pagination": {
    "total_count": int,
    "pages": int,
    "current_page": int,
    "results_shown": int
  },
  "statistics": {
    "status_distribution": {"Alive": int, "Dead": int, "unknown": int},
    "species_distribution": {"Human": int, "Alien": int, ...}
  },
  "characters": [
    {
      "id": int,
      "name": str,
      "status": str,
      "species": str,
      "type": str,
      "gender": str,
      "origin": {"name": str, "id": int | null},
      "location": {"name": str, "id": int | null},
      "image": str,
      "episode_count": int,
      "first_seen_episode": int | null
    }
  ]
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Character name to search for"
            },
            "status": {
                "type": "string",
                "description": "Status filter: Alive, Dead, or unknown"
            },
            "species": {
                "type": "string",
                "description": "Species filter: Human, Alien, etc."
            }
        }
    },
    on_invoke_tool=on_search_characters
)

tool_rickmorty_get_character_episodes = FunctionTool(
    name='local-rickmorty_get_character_episodes',
    description='''Get all episodes that a specific character appears in with extended data.

**Returns:** dict:
{
  "success": bool,
  "character": {
    "id": int,
    "name": str,
    "status": str,
    "species": str
  },
  "episode_summary": {
    "total_episodes": int,
    "episodes_retrieved": int,        // up to 20
    "season_breakdown": {"Season 1": int, "Season 2": int, ...},
    "first_appearance": str | null,   // episode code
    "last_appearance": str | null     // episode code
  },
  "episodes": [
    {
      "id": int,
      "name": str,
      "episode_code": str,
      "season": int | null,
      "episode_in_season": int | null,
      "air_date": str,
      "character_count": int
    }
  ]
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "character_id": {
                "type": "integer",
                "description": "The ID of the character"
            }
        },
        "required": ["character_id"]
    },
    on_invoke_tool=on_get_character_episodes
)


# Export all tools as a list
rickmorty_tools = [
    tool_rickmorty_get_character,
    tool_rickmorty_get_location,
    tool_rickmorty_get_episode,
    tool_rickmorty_search_characters,
    tool_rickmorty_get_character_episodes,
]

