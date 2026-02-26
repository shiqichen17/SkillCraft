"""
Pokemon Tools for pokemon-pokedex-generator task
Based on PokéAPI - completely free, no API key required.

PokéAPI Documentation: https://pokeapi.co/docs/v2

HIGH VERBOSE VERSION (v2): Returns detailed data for Skill Mode efficiency.
- Target Base Mode Input Tokens: 1M - 2M
- Intermediate tool outputs are verbose (full API data + related Pokemon)
- Final task output should be concise (extracted summary)
- This allows Pattern to process data internally and save tokens in skill mode

Changes from MODERATE to HIGH VERBOSE:
- on_get_pokemon: Add 8 related Pokemon of same primary type with full data
- on_get_species: All flavor texts (15+), all genera, all pokedex numbers
- on_get_moves: Fetch details for 40 moves instead of 10, include all move lists
- on_get_evolution: Full Pokemon data for each stage
"""

import json
from typing import Any, Dict, List
from agents.tool import FunctionTool, RunContextWrapper
import requests

# Base URL for PokéAPI
POKEAPI_URL = "https://pokeapi.co/api/v2"

# Cache for type->pokemon mapping to reduce API calls
_type_pokemon_cache = {}


# ============== Pokemon List for Task ==============
# 10 popular Pokemon across different generations
POKEMON_LIST = [
    {"id": 25, "name": "pikachu"},      # Gen 1 - Electric
    {"id": 6, "name": "charizard"},     # Gen 1 - Fire/Flying
    {"id": 150, "name": "mewtwo"},      # Gen 1 - Psychic (Legendary)
    {"id": 249, "name": "lugia"},       # Gen 2 - Psychic/Flying (Legendary)
    {"id": 384, "name": "rayquaza"},    # Gen 3 - Dragon/Flying (Legendary)
    {"id": 445, "name": "garchomp"},    # Gen 4 - Dragon/Ground
    {"id": 637, "name": "volcarona"},   # Gen 5 - Bug/Fire
    {"id": 706, "name": "goodra"},      # Gen 6 - Dragon
    {"id": 887, "name": "dragapult"},   # Gen 8 - Dragon/Ghost
    {"id": 94, "name": "gengar"},       # Gen 1 - Ghost/Poison
]


# ============== Tool 1: Get Pokemon Details (VERBOSE) ==============

def _fetch_pokemon_basic_data(pokemon_id_or_name):
    """Helper to fetch Pokemon data for related Pokemon - MODERATE."""
    try:
        resp = requests.get(f"{POKEAPI_URL}/pokemon/{str(pokemon_id_or_name).lower()}", timeout=15)
        if resp.status_code != 200:
            return None
        data = resp.json()
        
        stat_total = sum(s["base_stat"] for s in data.get("stats", []))
        
        return {
            "id": data.get("id"),
            "name": data.get("name"),
            "types": [t["type"]["name"] for t in data.get("types", [])],
            "abilities": [a["ability"]["name"] for a in data.get("abilities", [])],
            "stat_total": stat_total,
            "sprite": data.get("sprites", {}).get("front_default"),
            "moves_count": len(data.get("moves", []))
        }
    except:
        return None


async def on_get_pokemon(context: RunContextWrapper, params_str: str) -> Any:
    """Get Pokemon details - HIGH VERBOSE: includes related Pokemon of same type."""
    try:
        params = json.loads(params_str) if params_str else {}
    except json.JSONDecodeError:
        return {"success": False, "error": "Invalid JSON parameters"}
    
    pokemon_id = params.get("pokemon_id") or params.get("pokemon_name")
    
    if not pokemon_id:
        return {"success": False, "error": "pokemon_id or pokemon_name is required"}
    
    try:
        response = requests.get(
            f"{POKEAPI_URL}/pokemon/{str(pokemon_id).lower()}",
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        
        # HIGH VERBOSE: Type info with damage relations AND related Pokemon list
        types_info = []
        related_pokemon_same_type = []
        
        for t in data.get("types", []):
            type_name = t["type"]["name"]
            type_url = t["type"]["url"]
            try:
                type_resp = requests.get(type_url, timeout=15)
                type_data = type_resp.json()
                damage_relations = type_data.get("damage_relations", {})
                
                # HIGH VERBOSE: Get full type data including moves and pokemon
                type_moves = [m["name"] for m in type_data.get("moves", [])[:30]]
                type_pokemon_list = type_data.get("pokemon", [])
                
                types_info.append({
                    "slot": t["slot"],
                    "name": type_name,
                    "id": type_data.get("id"),
                    "generation": type_data.get("generation", {}).get("name") if type_data.get("generation") else None,
                    "damage_relations": {
                        "double_damage_from": [d["name"] for d in damage_relations.get("double_damage_from", [])],
                        "double_damage_to": [d["name"] for d in damage_relations.get("double_damage_to", [])],
                        "half_damage_from": [d["name"] for d in damage_relations.get("half_damage_from", [])],
                        "half_damage_to": [d["name"] for d in damage_relations.get("half_damage_to", [])],
                        "no_damage_from": [d["name"] for d in damage_relations.get("no_damage_from", [])],
                        "no_damage_to": [d["name"] for d in damage_relations.get("no_damage_to", [])]
                    },
                    "move_count": len(type_data.get("moves", [])),
                    "sample_moves": type_moves,
                    "pokemon_count": len(type_pokemon_list)
                })
                
                # MODERATE-HIGH VERBOSE: Fetch 6 related Pokemon of this type (for primary type only)
                if t["slot"] == 1 and len(related_pokemon_same_type) == 0:
                    current_pokemon_name = data.get("name", "").lower()
                    count = 0
                    for tp in type_pokemon_list:
                        pokemon_name = tp["pokemon"]["name"]
                        if pokemon_name != current_pokemon_name and count < 6:
                            poke_data = _fetch_pokemon_basic_data(pokemon_name)
                            if poke_data:
                                related_pokemon_same_type.append(poke_data)
                                count += 1
                    if count >= 6:
                        break
                            
            except:
                types_info.append({"slot": t["slot"], "name": type_name})
        
        # HIGH VERBOSE: Ability info with effects AND pokemon list sample
        abilities_info = []
        for ability in data.get("abilities", []):
            ability_name = ability["ability"]["name"]
            ability_url = ability["ability"]["url"]
            try:
                ability_resp = requests.get(ability_url, timeout=15)
                ability_data = ability_resp.json()
                effect_en = None
                short_effect_en = None
                for entry in ability_data.get("effect_entries", []):
                    if entry["language"]["name"] == "en":
                        effect_en = entry["effect"]
                        short_effect_en = entry["short_effect"]
                        break
                
                # HIGH VERBOSE: Include flavor texts and pokemon sample
                flavor_texts = []
                for entry in ability_data.get("flavor_text_entries", []):
                    if entry["language"]["name"] == "en":
                        flavor_texts.append({
                            "text": entry["flavor_text"].replace("\n", " "),
                            "version": entry["version_group"]["name"]
                        })
                        if len(flavor_texts) >= 5:
                            break
                
                pokemon_with_ability = [
                    {"name": p["pokemon"]["name"], "is_hidden": p["is_hidden"]}
                    for p in ability_data.get("pokemon", [])[:15]
                ]
                
                abilities_info.append({
                    "name": ability_name,
                    "id": ability_data.get("id"),
                    "is_hidden": ability["is_hidden"],
                    "slot": ability["slot"],
                    "effect": effect_en,
                    "short_effect": short_effect_en,
                    "flavor_texts": flavor_texts,
                    "generation": ability_data.get("generation", {}).get("name"),
                    "pokemon_count": len(ability_data.get("pokemon", [])),
                    "pokemon_sample": pokemon_with_ability
                })
            except:
                abilities_info.append({
                    "name": ability_name,
                    "is_hidden": ability["is_hidden"],
                    "slot": ability["slot"]
                })
        
        # Stats with effort values
        stats_info = []
        stat_total = 0
        for stat in data.get("stats", []):
            stat_name = stat["stat"]["name"]
            base_stat = stat["base_stat"]
            effort = stat["effort"]
            stat_total += base_stat
            stats_info.append({
                "name": stat_name,
                "base_stat": base_stat,
                "effort": effort
            })
        
        # MODERATE VERBOSE: Key sprites only (no version history - too large!)
        sprites = data.get("sprites", {})
        sprites_info = {
            "front_default": sprites.get("front_default"),
            "front_shiny": sprites.get("front_shiny"),
            "back_default": sprites.get("back_default"),
            "back_shiny": sprites.get("back_shiny"),
            "official_artwork": sprites.get("other", {}).get("official-artwork", {}).get("front_default"),
            "official_artwork_shiny": sprites.get("other", {}).get("official-artwork", {}).get("front_shiny"),
            "dream_world": sprites.get("other", {}).get("dream_world", {}).get("front_default")
            # Removed: versions, home, showdown - too large!
        }
        
        # HIGH VERBOSE: Held items with full version details
        held_items = []
        for item in data.get("held_items", []):
            held_items.append({
                "item": item["item"]["name"],
                "item_url": item["item"]["url"],
                "version_details": item.get("version_details", [])
            })
        
        # HIGH VERBOSE: Forms with URLs
        forms = [{"name": f["name"], "url": f["url"]} for f in data.get("forms", [])]
        
        # MODERATE-HIGH VERBOSE: Get first 80 moves with basic info (not full version details)
        moves_info = []
        for move in data.get("moves", [])[:80]:  # Limit to 80 moves
            move_name = move["move"]["name"]
            version_details = move.get("version_group_details", [])
            latest = version_details[-1] if version_details else {}
            moves_info.append({
                "name": move_name,
                "learn_method": latest.get("move_learn_method", {}).get("name") if latest else None,
                "level": latest.get("level_learned_at") if latest else None
            })
        
        # HIGH VERBOSE: Get ALL encounter locations
        encounter_locations = []
        try:
            encounters_url = data.get("location_area_encounters")
            if encounters_url:
                enc_resp = requests.get(encounters_url, timeout=15)
                enc_data = enc_resp.json()
                for enc in enc_data:  # No limit
                    encounter_locations.append({
                        "location": enc.get("location_area", {}).get("name"),
                        "url": enc.get("location_area", {}).get("url"),
                        "version_details": enc.get("version_details", [])
                    })
        except:
            pass
        
        # HIGH VERBOSE: All game indices
        game_indices = [
            {"game_index": gi["game_index"], "version": gi["version"]["name"]}
            for gi in data.get("game_indices", [])
        ]
        
        return {
            "success": True,
            "pokemon": {
                "id": data.get("id"),
                "name": data.get("name"),
                "order": data.get("order"),
                "height": data.get("height"),
                "height_meters": data.get("height", 0) / 10,
                "weight": data.get("weight"),
                "weight_kg": data.get("weight", 0) / 10,
                "base_experience": data.get("base_experience"),
                "species_url": data.get("species", {}).get("url"),
                "is_default": data.get("is_default"),
                # Type data with damage relations
                "types": types_info,
                "type_names": [t["name"] for t in types_info],
                # Ability data with effects
                "abilities": abilities_info,
                "ability_names": [a["name"] for a in abilities_info],
                # Stats
                "stats": stats_info,
                "stats_summary": {s["name"]: s["base_stat"] for s in stats_info},
                "stat_total": stat_total,
                # MODERATE VERBOSE: Key sprites
                "sprites": sprites_info,
                "sprite_url": sprites_info.get("front_default"),
                # MODERATE VERBOSE: Additional data
                "held_items": held_items,
                "forms": forms,
                "moves_count": len(data.get("moves", [])),
                "moves_preview": moves_info,  # First 50 moves only
                "encounter_locations": encounter_locations,
                "game_indices": game_indices,
                # Raw data fields
                "cries": data.get("cries", {}),
                "past_abilities": data.get("past_abilities", []),
                "past_types": data.get("past_types", [])
            },
            # HIGH VERBOSE: Related Pokemon of same primary type
            "related_pokemon": {
                "same_type": related_pokemon_same_type,
                "same_type_count": len(related_pokemon_same_type)
            }
        }
        
    except requests.RequestException as e:
        return {"success": False, "error": f"API error: {str(e)}"}


tool_get_pokemon = FunctionTool(
    name='local-pokemon_get_details',
    description='''Get Pokemon details including types, abilities, stats, and sprite.

**Input:** pokemon_id (int | str) - Pokemon ID number or name (e.g., 25 or 'pikachu')

**Returns:** dict:
{
  "success": bool,
  "pokemon": {
    "id": int, "name": str,
    "height": int, "height_meters": float,
    "weight": int, "weight_kg": float,
    "base_experience": int,
    "types": [str],  // e.g., ["electric"]
    "abilities": [{"name": str, "is_hidden": bool}],
    "stats": {"hp": int, "attack": int, "defense": int, "special-attack": int, "special-defense": int, "speed": int},
    "stat_total": int,
    "sprite_url": str,
    "moves_count": int
  }
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "pokemon_id": {"type": ["integer", "string"], "description": "Pokemon ID number or name (e.g., 25 or 'pikachu')"},
        },
        "required": ["pokemon_id"]
    },
    on_invoke_tool=on_get_pokemon
)


# ============== Tool 2: Get Pokemon Species (VERBOSE) ==============

async def on_get_species(context: RunContextWrapper, params_str: str) -> Any:
    """Get Pokemon species information - HIGH VERBOSE: all flavor texts, genera, pokedex entries."""
    try:
        params = json.loads(params_str) if params_str else {}
    except json.JSONDecodeError:
        return {"success": False, "error": "Invalid JSON parameters"}
    
    pokemon_id = params.get("pokemon_id") or params.get("pokemon_name")
    
    if not pokemon_id:
        return {"success": False, "error": "pokemon_id or pokemon_name is required"}
    
    try:
        response = requests.get(
            f"{POKEAPI_URL}/pokemon-species/{str(pokemon_id).lower()}",
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        
        # HIGH VERBOSE: All genera (multiple languages)
        genera = []
        genus_en = None
        for g in data.get("genera", []):
            genera.append({
                "genus": g["genus"],
                "language": g["language"]["name"]
            })
            if g["language"]["name"] == "en":
                genus_en = g["genus"]
        
        # MODERATE-HIGH VERBOSE: First 15 English flavor texts
        flavor_texts_en = []
        for entry in data.get("flavor_text_entries", []):
            if entry["language"]["name"] == "en":
                text = entry["flavor_text"].replace("\n", " ").replace("\f", " ")
                flavor_texts_en.append({
                    "text": text,
                    "version": entry["version"]["name"]
                })
                if len(flavor_texts_en) >= 15:
                    break
        
        # HIGH VERBOSE: Names in multiple languages
        names = []
        for name_entry in data.get("names", []):
            names.append({
                "name": name_entry["name"],
                "language": name_entry["language"]["name"]
            })
        
        # Get evolution chain ID
        evolution_chain_url = data.get("evolution_chain", {}).get("url")
        evolution_chain_id = None
        if evolution_chain_url:
            evolution_chain_id = int(evolution_chain_url.rstrip("/").split("/")[-1])
        
        # Get evolves_from_species
        evolves_from = None
        evolves_from_url = None
        if data.get("evolves_from_species"):
            evolves_from = data["evolves_from_species"]["name"]
            evolves_from_url = data["evolves_from_species"]["url"]
        
        # HIGH VERBOSE: All varieties (forms) with URLs
        varieties = [
            {
                "name": v["pokemon"]["name"],
                "url": v["pokemon"]["url"],
                "is_default": v["is_default"]
            }
            for v in data.get("varieties", [])
        ]
        
        # Egg groups with URLs
        egg_groups = [
            {"name": eg["name"], "url": eg["url"]}
            for eg in data.get("egg_groups", [])
        ]
        
        # MODERATE-HIGH VERBOSE: First 20 pokedex numbers
        pokedex_numbers = [
            {"dex": pn["pokedex"]["name"], "number": pn["entry_number"]}
            for pn in data.get("pokedex_numbers", [])[:20]
        ]
        
        # HIGH VERBOSE: Pal Park encounters
        pal_park_encounters = [
            {
                "area": enc["area"]["name"],
                "base_score": enc["base_score"],
                "rate": enc["rate"]
            }
            for enc in data.get("pal_park_encounters", [])
        ]
        
        # HIGH VERBOSE: Form descriptions
        form_descriptions = []
        for fd in data.get("form_descriptions", []):
            form_descriptions.append({
                "description": fd["description"],
                "language": fd["language"]["name"]
            })
        
        return {
            "success": True,
            "species": {
                "id": data.get("id"),
                "name": data.get("name"),
                "order": data.get("order"),
                "genus": genus_en,
                # HIGH VERBOSE: All genera
                "genera_all": genera,
                # HIGH VERBOSE: All flavor texts
                "flavor_texts": flavor_texts_en,
                "flavor_text": flavor_texts_en[0]["text"] if flavor_texts_en else None,
                "flavor_text_count": len(flavor_texts_en),
                # HIGH VERBOSE: All names
                "names": names,
                # Core data
                "generation": data.get("generation", {}).get("name"),
                "is_legendary": data.get("is_legendary"),
                "is_mythical": data.get("is_mythical"),
                "is_baby": data.get("is_baby"),
                "has_gender_differences": data.get("has_gender_differences"),
                "forms_switchable": data.get("forms_switchable"),
                # Appearance
                "color": data.get("color", {}).get("name") if data.get("color") else None,
                "shape": data.get("shape", {}).get("name") if data.get("shape") else None,
                "habitat": data.get("habitat", {}).get("name") if data.get("habitat") else None,
                # Stats
                "capture_rate": data.get("capture_rate"),
                "base_happiness": data.get("base_happiness"),
                "gender_rate": data.get("gender_rate"),
                "hatch_counter": data.get("hatch_counter"),
                "growth_rate": data.get("growth_rate", {}).get("name") if data.get("growth_rate") else None,
                # Evolution
                "evolution_chain_id": evolution_chain_id,
                "evolves_from_species": evolves_from,
                "evolves_from_species_url": evolves_from_url,
                # HIGH VERBOSE: All additional data
                "egg_groups": egg_groups,
                "varieties": varieties,
                "pokedex_numbers": pokedex_numbers,
                "pal_park_encounters": pal_park_encounters,
                "form_descriptions": form_descriptions
            }
        }
        
    except requests.RequestException as e:
        return {"success": False, "error": f"API error: {str(e)}"}


tool_get_species = FunctionTool(
    name='local-pokemon_get_species',
    description='''Get Pokemon species information including genus, generation, legendary status, and evolution chain ID.

**Input:** pokemon_id (int | str) - Pokemon ID number or name (e.g., 25 or 'pikachu')

**Returns:** dict:
{
  "success": bool,
  "species": {
    "id": int, "name": str,
    "genus": str,  // e.g., "Mouse Pokémon"
    "generation": str,  // e.g., "generation-i"
    "is_legendary": bool, "is_mythical": bool, "is_baby": bool,
    "color": str, "shape": str, "habitat": str,
    "capture_rate": int, "base_happiness": int, "gender_rate": int,
    "evolution_chain_id": int,  // Use this for pokemon_get_evolution
    "evolves_from_species": str | null
  }
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "pokemon_id": {"type": ["integer", "string"], "description": "Pokemon ID number or name (e.g., 25 or 'pikachu')"},
        },
        "required": ["pokemon_id"]
    },
    on_invoke_tool=on_get_species
)


# ============== Tool 3: Get Evolution Chain (VERBOSE) ==============

async def on_get_evolution_chain(context: RunContextWrapper, params_str: str) -> Any:
    """Get the evolution chain - HIGH VERBOSE: full Pokemon data for each evolution stage."""
    try:
        params = json.loads(params_str) if params_str else {}
    except json.JSONDecodeError:
        return {"success": False, "error": "Invalid JSON parameters"}
    
    chain_id = params.get("chain_id")
    
    if not chain_id:
        return {"success": False, "error": "chain_id is required"}
    
    try:
        response = requests.get(
            f"{POKEAPI_URL}/evolution-chain/{chain_id}",
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        
        def get_evolution_trigger(details_list):
            """Get evolution trigger description - HIGH VERBOSE: all evolution methods."""
            if not details_list:
                return None, None, []
            
            all_methods = []
            for details in details_list:
                trigger = details.get("trigger", {}).get("name")
                level = details.get("min_level")
                
                # Build trigger description
                if level:
                    trigger_desc = f"level {level}"
                elif details.get("item"):
                    trigger_desc = f"use {details['item']['name']}"
                elif details.get("min_happiness"):
                    trigger_desc = f"happiness {details['min_happiness']}"
                elif details.get("held_item"):
                    trigger_desc = f"hold {details['held_item']['name']}"
                elif details.get("known_move"):
                    trigger_desc = f"know {details['known_move']['name']}"
                elif details.get("time_of_day"):
                    trigger_desc = f"{trigger} at {details['time_of_day']}"
                elif details.get("location"):
                    trigger_desc = f"level up at {details['location']['name']}"
                elif details.get("min_beauty"):
                    trigger_desc = f"beauty {details['min_beauty']}"
                elif details.get("min_affection"):
                    trigger_desc = f"affection {details['min_affection']}"
                elif details.get("trade_species"):
                    trigger_desc = f"trade for {details['trade_species']['name']}"
                else:
                    trigger_desc = trigger
                
                # HIGH VERBOSE: All requirements
                requirements = {
                    "trigger": trigger,
                    "min_level": level,
                    "item": details.get("item", {}).get("name") if details.get("item") else None,
                    "held_item": details.get("held_item", {}).get("name") if details.get("held_item") else None,
                    "min_happiness": details.get("min_happiness"),
                    "time_of_day": details.get("time_of_day") if details.get("time_of_day") else None,
                    "known_move": details.get("known_move", {}).get("name") if details.get("known_move") else None,
                    "known_move_type": details.get("known_move_type", {}).get("name") if details.get("known_move_type") else None,
                    "location": details.get("location", {}).get("name") if details.get("location") else None,
                    "min_beauty": details.get("min_beauty"),
                    "min_affection": details.get("min_affection"),
                    "needs_overworld_rain": details.get("needs_overworld_rain"),
                    "party_species": details.get("party_species", {}).get("name") if details.get("party_species") else None,
                    "party_type": details.get("party_type", {}).get("name") if details.get("party_type") else None,
                    "relative_physical_stats": details.get("relative_physical_stats"),
                    "trade_species": details.get("trade_species", {}).get("name") if details.get("trade_species") else None,
                    "turn_upside_down": details.get("turn_upside_down"),
                    "gender": details.get("gender")
                }
                # Filter out None values
                requirements = {k: v for k, v in requirements.items() if v is not None}
                
                all_methods.append({
                    "trigger_desc": trigger_desc,
                    "requirements": requirements
                })
            
            primary = all_methods[0] if all_methods else {"trigger_desc": None, "requirements": {}}
            return primary["trigger_desc"], primary["requirements"], all_methods
        
        def parse_chain(chain_node, stage=1, flat_list=None, parent_name=None):
            """Parse evolution chain - MODERATE: basic Pokemon data only."""
            if flat_list is None:
                flat_list = []
            
            species_name = chain_node["species"]["name"]
            species_url = chain_node["species"]["url"]
            species_id = int(species_url.rstrip("/").split("/")[-1])
            
            trigger_desc, requirements, all_evolution_methods = get_evolution_trigger(chain_node.get("evolution_details", []))
            
            # MODERATE: Fetch basic Pokemon data only
            pokemon_data = {}
            try:
                pokemon_resp = requests.get(f"{POKEAPI_URL}/pokemon/{species_id}", timeout=10)
                if pokemon_resp.status_code == 200:
                    pdata = pokemon_resp.json()
                    stat_total = sum(s["base_stat"] for s in pdata.get("stats", []))
                    
                    pokemon_data = {
                        "id": pdata.get("id"),
                        "types": [t["type"]["name"] for t in pdata.get("types", [])],
                        "stats_total": stat_total,
                        "sprite": pdata.get("sprites", {}).get("front_default")
                    }
            except:
                pass
            
            # Skip species_data fetch to reduce tokens
            species_data = {}
            
            entry = {
                "species_name": species_name,
                "species_id": species_id,
                "species_url": species_url,
                "stage": stage,
                "evolves_from": parent_name,
                "evolution_trigger": trigger_desc,
                "requirements": requirements,
                # HIGH VERBOSE: All evolution methods (some Pokemon have multiple)
                "all_evolution_methods": all_evolution_methods,
                "pokemon_data": pokemon_data,
                "species_data": species_data,
                "branch_count": len(chain_node.get("evolves_to", []))
            }
            
            flat_list.append(entry)
            
            for evolution in chain_node.get("evolves_to", []):
                parse_chain(evolution, stage + 1, flat_list, species_name)
            
            return flat_list
        
        chain = data.get("chain", {})
        flat_list = parse_chain(chain)
        
        return {
            "success": True,
            "evolution_chain": {
                "id": data.get("id"),
                "baby_trigger_item": data.get("baby_trigger_item", {}).get("name") if data.get("baby_trigger_item") else None,
                "stages_count": max(e["stage"] for e in flat_list) if flat_list else 0,
                "total_pokemon": len(flat_list),
                "has_branching": any(e["branch_count"] > 1 for e in flat_list),
                "chain": flat_list
            }
        }
        
    except requests.RequestException as e:
        return {"success": False, "error": f"API error: {str(e)}"}


tool_get_evolution_chain = FunctionTool(
    name='local-pokemon_get_evolution',
    description='''Get evolution chain data.

**Input:** chain_id (int) - Evolution chain ID (from pokemon_get_species)

**Returns:** dict:
{
  "success": bool,
  "evolution_chain": {
    "id": int,
    "stages_count": int,
    "total_pokemon": int,
    "chain": [{
      "species_name": str,       // e.g., "pikachu" - use this to match by name
      "species_id": int,         // e.g., 25 - use this to match pokemon.id from get_details
      "stage": int,              // 1=base, 2=first evo, 3=final evo
      "evolves_from": str | null,
      "evolution_trigger": str | null,  // e.g., "level 16", "use thunder-stone"
      "min_level": int | null
    }]
  }
}

**TIP:** To find current Pokemon in chain, match `chain[].species_id` with `pokemon.id` from get_details (NOT the input parameter).''',
    params_json_schema={
        "type": "object",
        "properties": {
            "chain_id": {"type": "integer", "description": "Evolution chain ID (from pokemon_get_species)"},
        },
        "required": ["chain_id"]
    },
    on_invoke_tool=on_get_evolution_chain
)


# ============== Tool 4: Get Pokemon Moves (VERBOSE) ==============

async def on_get_moves(context: RunContextWrapper, params_str: str) -> Any:
    """Get Pokemon moves - HIGH VERBOSE: detailed move data with 40 move details."""
    try:
        params = json.loads(params_str) if params_str else {}
    except json.JSONDecodeError:
        return {"success": False, "error": "Invalid JSON parameters"}
    
    pokemon_id = params.get("pokemon_id") or params.get("pokemon_name")
    
    if not pokemon_id:
        return {"success": False, "error": "pokemon_id or pokemon_name is required"}
    
    try:
        response = requests.get(
            f"{POKEAPI_URL}/pokemon/{str(pokemon_id).lower()}",
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        
        # Categorize moves by learning method (latest version only)
        level_up_moves = []
        machine_moves = []
        egg_moves = []
        tutor_moves = []
        total_moves = len(data.get("moves", []))  # Total unique moves
        
        for move_data in data.get("moves", []):
            move_name = move_data["move"]["name"]
            version_details = move_data.get("version_group_details", [])
            
            # Get latest version details for categorization
            if version_details:
                latest = version_details[-1]
                method = latest["move_learn_method"]["name"]
                level = latest.get("level_learned_at", 0)
                
                if method == "level-up" and level > 0:
                    level_up_moves.append({"name": move_name, "level": level})
                elif method == "machine":
                    machine_moves.append({"name": move_name})
                elif method == "egg":
                    egg_moves.append({"name": move_name})
                elif method == "tutor":
                    tutor_moves.append({"name": move_name})
        
        # Sort level-up moves by level
        level_up_moves.sort(key=lambda x: x["level"])
        
        # MODERATE-HIGH VERBOSE: Fetch details for 10 key moves
        move_details = []
        moves_to_fetch = []
        moves_to_fetch.extend([m["name"] for m in level_up_moves[:6]])
        moves_to_fetch.extend([m["name"] for m in machine_moves[:4]])
        
        for move_name in moves_to_fetch[:10]:
            try:
                move_resp = requests.get(f"{POKEAPI_URL}/move/{move_name}", timeout=10)
                move_info = move_resp.json()
                
                effect_en = None
                short_effect_en = None
                for entry in move_info.get("effect_entries", []):
                    if entry["language"]["name"] == "en":
                        effect_en = entry["effect"]
                        short_effect_en = entry["short_effect"]
                        break
                
                # HIGH VERBOSE: Flavor texts (limited to 3)
                flavor_texts = []
                for entry in move_info.get("flavor_text_entries", []):
                    if entry["language"]["name"] == "en":
                        flavor_texts.append({
                            "text": entry["flavor_text"].replace("\n", " "),
                            "version": entry["version_group"]["name"]
                        })
                        if len(flavor_texts) >= 3:
                            break
                
                # HIGH VERBOSE: Contest info
                contest_type = move_info.get("contest_type", {}).get("name") if move_info.get("contest_type") else None
                
                # HIGH VERBOSE: Stat changes
                stat_changes = [
                    {"stat": sc["stat"]["name"], "change": sc["change"]}
                    for sc in move_info.get("stat_changes", [])
                ]
                
                move_details.append({
                    "name": move_info.get("name"),
                    "id": move_info.get("id"),
                    "power": move_info.get("power"),
                    "accuracy": move_info.get("accuracy"),
                    "pp": move_info.get("pp"),
                    "priority": move_info.get("priority"),
                    "type": move_info.get("type", {}).get("name"),
                    "damage_class": move_info.get("damage_class", {}).get("name"),
                    "generation": move_info.get("generation", {}).get("name"),
                    "effect": effect_en,
                    "short_effect": short_effect_en,
                    "effect_chance": move_info.get("effect_chance"),
                    "flavor_texts": flavor_texts,
                    "target": move_info.get("target", {}).get("name"),
                    "contest_type": contest_type,
                    "stat_changes": stat_changes
                })
            except:
                move_details.append({"name": move_name, "error": "Failed to fetch"})
        
        return {
            "success": True,
            "pokemon_name": data.get("name"),
            "pokemon_id": data.get("id"),
            "moves_summary": {
                "total_unique_moves": total_moves,
                "level_up_count": len(level_up_moves),
                "machine_count": len(machine_moves),
                "egg_count": len(egg_moves),
                "tutor_count": len(tutor_moves)
            },
            # MODERATE-HIGH VERBOSE: Move lists (names only, no URLs)
            "level_up_moves": level_up_moves,
            "machine_moves": machine_moves[:50],  # Limit to 50
            "egg_moves": egg_moves,
            "tutor_moves": tutor_moves[:30],  # Limit to 30
            # MODERATE-HIGH VERBOSE: Detailed info for 10 key moves
            "move_details": move_details,
            "move_details_count": len(move_details)
        }
        
    except requests.RequestException as e:
        return {"success": False, "error": f"API error: {str(e)}"}


tool_get_moves = FunctionTool(
    name='local-pokemon_get_moves',
    description='''Get Pokemon move counts by learning method (summary only, not full move lists).

**Input:** pokemon_id (int | str) - Pokemon ID number or name (e.g., 25 or 'pikachu')

**Returns:** dict:
{
  "success": bool,
  "pokemon_name": str,
  "pokemon_id": int,
  "moves_summary": {
    "total_unique_moves": int,
    "level_up_count": int,
    "machine_count": int,  // TM/HM moves
    "tutor_count": int,
    "egg_count": int,
    "other_count": int
  }
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "pokemon_id": {"type": ["integer", "string"], "description": "Pokemon ID number or name (e.g., 25 or 'pikachu')"},
        },
        "required": ["pokemon_id"]
    },
    on_invoke_tool=on_get_moves
)


# ============== Tool 5: Get Pokemon Abilities (VERBOSE) ==============

async def on_get_abilities(context: RunContextWrapper, params_str: str) -> Any:
    """Get ability details - HIGH VERBOSE: extended ability data with more Pokemon samples."""
    try:
        params = json.loads(params_str) if params_str else {}
    except json.JSONDecodeError:
        return {"success": False, "error": "Invalid JSON parameters"}
    
    ability_names = params.get("ability_names", [])
    
    if not ability_names:
        return {"success": False, "error": "ability_names list is required"}
    
    if isinstance(ability_names, str):
        ability_names = [ability_names]
    
    abilities = []
    
    for ability_name in ability_names:
        try:
            response = requests.get(
                f"{POKEAPI_URL}/ability/{ability_name.lower()}",
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            # MODERATE: English effect only
            effect_en = None
            short_effect_en = None
            for entry in data.get("effect_entries", []):
                if entry["language"]["name"] == "en":
                    effect_en = entry["effect"]
                    short_effect_en = entry["short_effect"]
                    break
            
            # MODERATE-HIGH: First 6 English flavor texts
            flavor_texts = []
            for entry in data.get("flavor_text_entries", []):
                if entry["language"]["name"] == "en":
                    flavor_texts.append({
                        "text": entry["flavor_text"].replace("\n", " "),
                        "version": entry["version_group"]["name"]
                    })
                    if len(flavor_texts) >= 6:
                        break
            
            # MODERATE-HIGH: Pokemon sample (20)
            pokemon_list = data.get("pokemon", [])
            pokemon_sample = [
                {
                    "name": p["pokemon"]["name"],
                    "is_hidden": p["is_hidden"]
                }
                for p in pokemon_list[:20]
            ]
            
            abilities.append({
                "name": data.get("name"),
                "id": data.get("id"),
                "effect": effect_en,
                "short_effect": short_effect_en,
                "flavor_texts": flavor_texts,
                "generation": data.get("generation", {}).get("name") if data.get("generation") else None,
                "is_main_series": data.get("is_main_series"),
                "pokemon_count": len(pokemon_list),
                "pokemon_sample": pokemon_sample
            })
            
        except requests.RequestException as e:
            abilities.append({
                "name": ability_name,
                "error": f"Failed to fetch: {str(e)}"
            })
    
    return {
        "success": True,
        "abilities": abilities,
        "total_abilities_fetched": len([a for a in abilities if "error" not in a])
    }


tool_get_abilities = FunctionTool(
    name='local-pokemon_get_abilities',
    description='''Get ability information.

**Input:** ability_names (list[str]) - List of ability names (e.g., ['static', 'lightning-rod'])

**Returns:** dict:
{
  "success": bool,
  "abilities": [{
    "name": str,
    "id": int,
    "short_effect": str,  // e.g., "Has a 30% chance of paralyzing attacking Pokemon on contact."
    "is_main_series": bool,
    "generation": str,
    "pokemon_count": int  // Number of Pokemon with this ability
  }]
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "ability_names": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of ability names (e.g., ['static', 'lightning-rod'])"
            },
        },
        "required": ["ability_names"]
    },
    on_invoke_tool=on_get_abilities
)


# ============== Export all tools ==============

pokemon_tools = [
    tool_get_pokemon,           # Step 1: Get Pokemon details
    tool_get_species,           # Step 2: Get species info
    tool_get_evolution_chain,   # Step 3: Get evolution chain
    tool_get_moves,             # Step 4: Get move counts (summary only)
    tool_get_abilities,         # Step 5: Get ability details
]
