"""
D&D 5e API Tools

Provides tools to query Dungeons & Dragons 5th Edition SRD data.
Designed for skill mode scenarios with structured game data.

API Documentation: https://www.dnd5eapi.co/docs
No authentication required.

VERBOSE VERSION: Returns comprehensive data for Skill Mode efficiency.
- Intermediate tool outputs are verbose (full API data + related entities)
- Final task output should be concise (extracted summary)
- This allows Pattern to process data internally and save tokens in skill mode
"""

import json
from typing import Any
from agents.tool import FunctionTool, RunContextWrapper
import requests

# Base URL for D&D 5e API
DND_BASE_URL = "https://www.dnd5eapi.co/api"


def _make_request(endpoint: str) -> dict:
    """Make a request to the D&D API with error handling."""
    url = f"{DND_BASE_URL}{endpoint}"
    headers = {"User-Agent": "DikaNong-PatternReuse/1.0"}
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
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

def _get_class(class_name: str) -> dict:
    """Get detailed information about a D&D class with VERBOSE level progression for skill mode."""
    data = _make_request(f"/classes/{class_name.lower()}")
    
    if "error" in data:
        return data
    
    # VERBOSE: Get class level progression for ALL levels
    class_levels = []
    levels_data = _make_request(f"/classes/{class_name.lower()}/levels")
    if isinstance(levels_data, list):
        for level in levels_data:
            level_num = level.get("level")
            level_info = {
                "level": level_num,
                "ability_score_bonuses": level.get("ability_score_bonuses"),
                "prof_bonus": level.get("prof_bonus"),
                "features": [f.get("name") for f in level.get("features", [])]
            }
            
            # VERBOSE: Get ALL feature details for ALL levels
            if level.get("features"):
                level_info["feature_details"] = []
                for feature in level.get("features", []):  # ALL features
                    feature_url = feature.get("url")
                    if feature_url:
                        feature_data = _make_request(feature_url.replace("/api", ""))
                        if not feature_data.get("error"):
                            level_info["feature_details"].append({
                                "name": feature_data.get("name"),
                                "index": feature_data.get("index"),
                                "class": feature_data.get("class", {}).get("name"),
                                "level": feature_data.get("level"),
                                "description": feature_data.get("desc", []),  # FULL description
                                "prerequisites": feature_data.get("prerequisites", []),
                                "feature_specific": feature_data.get("feature_specific")
                            })
            
            # VERBOSE: Full spellcasting progression
            if level.get("spellcasting"):
                sc = level.get("spellcasting", {})
                level_info["spellcasting"] = {
                    "cantrips_known": sc.get("cantrips_known"),
                    "spells_known": sc.get("spells_known"),
                    "spell_slots_level_1": sc.get("spell_slots_level_1"),
                    "spell_slots_level_2": sc.get("spell_slots_level_2"),
                    "spell_slots_level_3": sc.get("spell_slots_level_3"),
                    "spell_slots_level_4": sc.get("spell_slots_level_4"),
                    "spell_slots_level_5": sc.get("spell_slots_level_5"),
                    "spell_slots_level_6": sc.get("spell_slots_level_6"),
                    "spell_slots_level_7": sc.get("spell_slots_level_7"),
                    "spell_slots_level_8": sc.get("spell_slots_level_8"),
                    "spell_slots_level_9": sc.get("spell_slots_level_9")
                }
            
            # VERBOSE: Class-specific resources
            if level.get("class_specific"):
                level_info["class_specific"] = level.get("class_specific")
            
            class_levels.append(level_info)
    
    # VERBOSE: Get ALL proficiency options
    proficiency_choices_full = []
    for pc in data.get("proficiency_choices", []):
        choice_info = {
            "choose": pc.get("choose"),
            "type": pc.get("type"),
            "description": pc.get("desc"),
            "options": []
        }
        for opt in pc.get("from", {}).get("options", []):
            if opt.get("item"):
                choice_info["options"].append({
                    "name": opt.get("item", {}).get("name"),
                    "url": opt.get("item", {}).get("url")
                })
            elif opt.get("choice"):
                choice_info["options"].append({
                    "nested_choice": True,
                    "choose": opt.get("choice", {}).get("choose"),
                    "from_type": opt.get("choice", {}).get("from", {}).get("option_set_type")
                })
        proficiency_choices_full.append(choice_info)
    
    # VERBOSE: Get ALL starting equipment options
    starting_equipment_options = []
    for seo in data.get("starting_equipment_options", []):
        option_info = {
            "choose": seo.get("choose"),
            "type": seo.get("type"),
            "description": seo.get("desc"),
            "options": []
        }
        for opt in seo.get("from", {}).get("options", []):
            if opt.get("of"):
                option_info["options"].append({
                    "count": opt.get("count"),
                    "item": opt.get("of", {}).get("name")
                })
            elif opt.get("equipment_option"):
                option_info["options"].append({
                    "equipment_category": opt.get("equipment_option", {}).get("from", {}).get("equipment_category", {}).get("name")
                })
        starting_equipment_options.append(option_info)
    
    # VERBOSE: Get full subclass details
    subclasses_full = []
    for sc in data.get("subclasses", []):
        sc_url = sc.get("url")
        if sc_url:
            sc_data = _make_request(sc_url.replace("/api", ""))
            if not sc_data.get("error"):
                subclasses_full.append({
                    "name": sc_data.get("name"),
                    "index": sc_data.get("index"),
                    "subclass_flavor": sc_data.get("subclass_flavor"),
                    "description": sc_data.get("desc", []),
                    "subclass_levels_url": sc_data.get("subclass_levels"),
                    "spells": sc_data.get("spells", [])
                })
    
    # VERBOSE: Get ALL other classes for comparison
    other_classes = []
    all_classes = _make_request("/classes")
    if isinstance(all_classes, dict) and "results" in all_classes:
        for cls in all_classes.get("results", []):
            if cls.get("index") != data.get("index"):
                cls_data = _make_request(f"/classes/{cls.get('index')}")
                if not cls_data.get("error"):
                    other_classes.append({
                        "name": cls_data.get("name"),
                        "index": cls_data.get("index"),
                        "hit_die": cls_data.get("hit_die"),
                        "proficiencies": [p.get("name") for p in cls_data.get("proficiencies", [])],
                        "saving_throws": [st.get("name") for st in cls_data.get("saving_throws", [])],
                        "subclasses": [s.get("name") for s in cls_data.get("subclasses", [])],
                        "spellcasting_ability": cls_data.get("spellcasting", {}).get("spellcasting_ability", {}).get("name") if cls_data.get("spellcasting") else None
                    })
    
    return {
        "success": True,
        "class": {
            "index": data.get("index"),
            "name": data.get("name"),
            "hit_die": data.get("hit_die"),
            "proficiency_choices": proficiency_choices_full,
            "proficiencies": [p.get("name") for p in data.get("proficiencies", [])],
            "saving_throws": [st.get("name") for st in data.get("saving_throws", [])],
            "starting_equipment": [
                {"name": eq.get("equipment", {}).get("name"), "quantity": eq.get("quantity")}
                for eq in data.get("starting_equipment", [])
            ],
            "starting_equipment_options": starting_equipment_options,
            "class_levels_url": data.get("class_levels"),
            "subclasses_full": subclasses_full,
            "spellcasting": {
                "level": data.get("spellcasting", {}).get("level"),
                "spellcasting_ability": data.get("spellcasting", {}).get("spellcasting_ability", {}).get("name"),
                "info": data.get("spellcasting", {}).get("info", [])
            } if data.get("spellcasting") else None,
            "multi_classing": {
                "prerequisites": [
                    {"ability": p.get("ability_score", {}).get("name"), "minimum": p.get("minimum_score")}
                    for p in data.get("multi_classing", {}).get("prerequisites", [])
                ],
                "proficiencies": [p.get("name") for p in data.get("multi_classing", {}).get("proficiencies", [])]
            } if data.get("multi_classing") else None
        },
        # VERBOSE: Full level progression for pattern to extract summary from
        "level_progression": {
            "total_levels": len(class_levels),
            "levels": class_levels
        },
        # VERBOSE: Other classes for comparison
        "other_classes": {
            "count": len(other_classes),
            "classes": other_classes
        },
        # Include raw API data
        "raw_api_data": data
    }


def _get_race(race_name: str) -> dict:
    """Get detailed information about a D&D race with MODERATE verbosity for skill mode."""
    data = _make_request(f"/races/{race_name.lower()}")
    
    if "error" in data:
        return data
    
    # VERBOSE: Get FULL trait details
    traits_info = []
    for trait in data.get("traits", []):
        trait_url = trait.get("url", "")
        if trait_url:
            trait_data = _make_request(trait_url.replace("/api", ""))
            if not trait_data.get("error"):
                traits_info.append({
                    "name": trait_data.get("name"),
                    "index": trait_data.get("index"),
                    "description": trait_data.get("desc", []),  # FULL description
                    "races": [r.get("name") for r in trait_data.get("races", [])],
                    "subraces": [s.get("name") for s in trait_data.get("subraces", [])],
                    "proficiencies": [p.get("name") for p in trait_data.get("proficiencies", [])],
                    "proficiency_choices": trait_data.get("proficiency_choices"),
                    "trait_specific": trait_data.get("trait_specific")
                })
            else:
                traits_info.append({"name": trait.get("name")})
        else:
            traits_info.append({"name": trait.get("name")})
    
    # MODERATE: Get subrace details (simplified)
    subraces_info = []
    for subrace in data.get("subraces", []):
        subrace_url = subrace.get("url", "")
        if subrace_url:
            subrace_data = _make_request(subrace_url.replace("/api", ""))
            if not subrace_data.get("error"):
                subraces_info.append({
                    "name": subrace_data.get("name"),
                    "description": subrace_data.get("desc"),
                    "ability_bonuses": [
                        {"ability": ab.get("ability_score", {}).get("name"), "bonus": ab.get("bonus")}
                        for ab in subrace_data.get("ability_bonuses", [])
                    ],
                    "racial_traits": [t.get("name") for t in subrace_data.get("racial_traits", [])]
                })
            else:
                subraces_info.append({"name": subrace.get("name")})
    
    # Ability bonuses (no extra API calls)
    ability_bonuses = [
        {"ability": ab.get("ability_score", {}).get("name"), "bonus": ab.get("bonus")}
        for ab in data.get("ability_bonuses", [])
    ]
    
    # VERBOSE: Get ALL other races for comparison
    other_races = []
    all_races = _make_request("/races")
    if isinstance(all_races, dict) and "results" in all_races:
        for race in all_races.get("results", []):
            if race.get("index") != data.get("index"):
                race_data = _make_request(f"/races/{race.get('index')}")
                if not race_data.get("error"):
                    other_races.append({
                        "name": race_data.get("name"),
                        "index": race_data.get("index"),
                        "speed": race_data.get("speed"),
                        "size": race_data.get("size"),
                        "ability_bonuses": [
                            {"ability": ab.get("ability_score", {}).get("name"), "bonus": ab.get("bonus")}
                            for ab in race_data.get("ability_bonuses", [])
                        ],
                        "traits": [t.get("name") for t in race_data.get("traits", [])],
                        "languages": [l.get("name") for l in race_data.get("languages", [])],
                        "subraces": [s.get("name") for s in race_data.get("subraces", [])]
                    })
    
    return {
        "success": True,
        "race": {
            "index": data.get("index"),
            "name": data.get("name"),
            "speed": data.get("speed"),
            "ability_bonuses": ability_bonuses,
            "alignment": data.get("alignment"),
            "age": data.get("age"),
            "size": data.get("size"),
            "size_description": data.get("size_description"),
            "starting_proficiencies": [p.get("name") for p in data.get("starting_proficiencies", [])],
            "languages": [lang.get("name") for lang in data.get("languages", [])],
            "language_desc": data.get("language_desc"),
            "traits": [t.get("name") for t in data.get("traits", [])],
            "subraces": [sr.get("name") for sr in data.get("subraces", [])]
        },
        "traits_details": traits_info,
        "subraces_details": subraces_info,
        # VERBOSE: Other races for comparison
        "other_races": {
            "count": len(other_races),
            "races": other_races
        },
        # Include raw API data
        "raw_api_data": data
    }


def _get_class_spells(class_name: str) -> dict:
    """Get spells available to a specific class with VERBOSE data for skill mode."""
    data = _make_request(f"/classes/{class_name.lower()}/spells")
    
    if "error" in data:
        return data
    
    spells = data.get("results", [])
    
    # VERBOSE: Get detailed info for ALL spells (up to 10 per level for balance)
    spell_details = []
    spells_by_level = {}
    detailed_per_level = {}
    
    for spell in spells:
        level = spell.get("level", 0)
        if level not in spells_by_level:
            spells_by_level[level] = []
            detailed_per_level[level] = 0
        
        spell_index = spell.get("index", "")
        spells_by_level[level].append(spell.get("name"))
        
        # VERBOSE: Fetch details for up to 10 spells per level
        if detailed_per_level[level] < 10:
            spell_data = _make_request(f"/spells/{spell_index}")
            
            if not spell_data.get("error"):
                detailed_spell = {
                    "name": spell_data.get("name"),
                    "index": spell_data.get("index"),
                    "level": spell_data.get("level"),
                    "school": spell_data.get("school", {}).get("name"),
                    "casting_time": spell_data.get("casting_time"),
                    "range": spell_data.get("range"),
                    "duration": spell_data.get("duration"),
                    "concentration": spell_data.get("concentration"),
                    "ritual": spell_data.get("ritual"),
                    "components": spell_data.get("components", []),
                    "material": spell_data.get("material"),
                    "description": spell_data.get("desc", []),  # FULL description
                    "higher_level": spell_data.get("higher_level", []),
                    "damage": spell_data.get("damage"),
                    "heal_at_slot_level": spell_data.get("heal_at_slot_level"),
                    "area_of_effect": spell_data.get("area_of_effect"),
                    "dc": spell_data.get("dc"),
                    "classes": [c.get("name") for c in spell_data.get("classes", [])],
                    "subclasses": [s.get("name") for s in spell_data.get("subclasses", [])]
                }
                spell_details.append(detailed_spell)
                detailed_per_level[level] += 1
    
    # Calculate statistics
    school_distribution = {}
    for spell in spell_details:
        school = spell.get("school", "Unknown")
        school_distribution[school] = school_distribution.get(school, 0) + 1
    
    return {
        "success": True,
        "class": class_name,
        "total_spells": data.get("count", len(spells)),
        "statistics": {
            "school_distribution": school_distribution,
            "by_level_count": {f"level_{level}": len(names) for level, names in sorted(spells_by_level.items())}
        },
        "spells_by_level": {
            f"level_{level}": names
            for level, names in sorted(spells_by_level.items())
        },
        "spell_details_sample": spell_details
    }


def _get_equipment_category(category: str) -> dict:
    """Get equipment in a specific category with VERBOSE data for skill mode."""
    data = _make_request(f"/equipment-categories/{category.lower()}")
    
    if "error" in data:
        return data
    
    equipment = data.get("equipment", [])
    
    # VERBOSE: Get details for ALL items (up to 50)
    equipment_full = []
    for eq in equipment[:50]:
        eq_url = eq.get("url", "")
        if eq_url:
            eq_data = _make_request(eq_url.replace("/api", ""))
            if not eq_data.get("error"):
                item_info = {
                    "name": eq_data.get("name"),
                    "index": eq_data.get("index"),
                    "equipment_category": eq_data.get("equipment_category", {}).get("name"),
                    "cost": eq_data.get("cost"),
                    "weight": eq_data.get("weight"),
                    "description": eq_data.get("desc", [])  # FULL description
                }
                
                # Weapon-specific data (FULL)
                if eq_data.get("weapon_category"):
                    item_info["weapon_category"] = eq_data.get("weapon_category")
                    item_info["weapon_range"] = eq_data.get("weapon_range")
                    item_info["category_range"] = eq_data.get("category_range")
                    item_info["damage"] = eq_data.get("damage")
                    item_info["two_handed_damage"] = eq_data.get("two_handed_damage")
                    item_info["range"] = eq_data.get("range")
                    item_info["throw_range"] = eq_data.get("throw_range")
                    item_info["properties"] = []
                    for prop in eq_data.get("properties", []):
                        prop_data = _make_request(prop.get("url", "").replace("/api", ""))
                        if not prop_data.get("error"):
                            item_info["properties"].append({
                                "name": prop_data.get("name"),
                                "index": prop_data.get("index"),
                                "description": prop_data.get("desc", [])
                            })
                        else:
                            item_info["properties"].append({"name": prop.get("name")})
                    item_info["special"] = eq_data.get("special", [])
                
                # Armor-specific data (FULL)
                if eq_data.get("armor_category"):
                    item_info["armor_category"] = eq_data.get("armor_category")
                    item_info["armor_class"] = eq_data.get("armor_class")
                    item_info["str_minimum"] = eq_data.get("str_minimum")
                    item_info["stealth_disadvantage"] = eq_data.get("stealth_disadvantage")
                
                # Gear-specific data
                if eq_data.get("gear_category"):
                    item_info["gear_category"] = eq_data.get("gear_category", {}).get("name")
                
                # Tool-specific data
                if eq_data.get("tool_category"):
                    item_info["tool_category"] = eq_data.get("tool_category")
                
                # Vehicle-specific data
                if eq_data.get("vehicle_category"):
                    item_info["vehicle_category"] = eq_data.get("vehicle_category")
                    item_info["speed"] = eq_data.get("speed")
                    item_info["capacity"] = eq_data.get("capacity")
                
                equipment_full.append(item_info)
            else:
                equipment_full.append({"name": eq.get("name")})
        else:
            equipment_full.append({"name": eq.get("name")})
    
    # Just names for remaining items (if any over 50)
    remaining_names = [eq.get("name") for eq in equipment[50:]]
    
    # Calculate basic statistics from detailed items
    total_cost_gp = 0
    total_weight = 0
    
    for item in equipment_full:
        if isinstance(item, dict):
            cost = item.get("cost", {})
            if cost:
                quantity = cost.get("quantity", 0)
                unit = cost.get("unit", "gp")
                if unit == "cp":
                    total_cost_gp += quantity / 100
                elif unit == "sp":
                    total_cost_gp += quantity / 10
                elif unit == "gp":
                    total_cost_gp += quantity
            
            weight = item.get("weight", 0)
            if weight:
                total_weight += weight
    
    return {
        "success": True,
        "category": {
            "index": data.get("index"),
            "name": data.get("name"),
            "total_items": len(equipment),
            "equipment_names": [eq.get("name") for eq in equipment]
        },
        "equipment_detailed": equipment_full,
        "remaining_items": remaining_names,
        "statistics": {
            "detailed_items": len(equipment_full),
            "total_items": len(equipment),
            "sample_total_cost_gp": round(total_cost_gp, 2),
            "sample_total_weight": round(total_weight, 2)
        }
    }


def _get_monster(monster_name: str) -> dict:
    """Get detailed information about a monster with VERBOSE full data for skill mode."""
    data = _make_request(f"/monsters/{monster_name.lower().replace(' ', '-')}")
    
    if "error" in data:
        return data
    
    # VERBOSE: Calculate ability modifiers
    def calc_modifier(score):
        if score is None:
            return None
        return (score - 10) // 2
    
    stats = {
        "strength": data.get("strength"),
        "dexterity": data.get("dexterity"),
        "constitution": data.get("constitution"),
        "intelligence": data.get("intelligence"),
        "wisdom": data.get("wisdom"),
        "charisma": data.get("charisma")
    }
    
    stat_modifiers = {
        f"{stat}_modifier": calc_modifier(value)
        for stat, value in stats.items()
    }
    
    # VERBOSE: Full armor class details
    armor_class_details = []
    for ac in data.get("armor_class", []):
        ac_info = {
            "value": ac.get("value"),
            "type": ac.get("type"),
            "armor": [a.get("name") for a in ac.get("armor", [])] if ac.get("armor") else None,
            "condition": ac.get("condition", {}).get("name") if ac.get("condition") else None
        }
        armor_class_details.append(ac_info)
    
    # VERBOSE: Full special abilities with complete descriptions
    special_abilities_full = []
    for sa in data.get("special_abilities", []):
        ability_info = {
            "name": sa.get("name"),
            "description": sa.get("desc"),
            "usage": sa.get("usage"),
            "dc": {
                "dc_type": sa.get("dc", {}).get("dc_type", {}).get("name"),
                "dc_value": sa.get("dc", {}).get("dc_value"),
                "success_type": sa.get("dc", {}).get("success_type")
            } if sa.get("dc") else None,
            "damage": sa.get("damage"),
            "spellcasting": {
                "level": sa.get("spellcasting", {}).get("level"),
                "ability": sa.get("spellcasting", {}).get("ability", {}).get("name"),
                "dc": sa.get("spellcasting", {}).get("dc"),
                "slots": sa.get("spellcasting", {}).get("slots"),
                "spells": [
                    {"name": s.get("name"), "level": s.get("level"), "usage": s.get("usage")}
                    for s in sa.get("spellcasting", {}).get("spells", [])
                ]
            } if sa.get("spellcasting") else None
        }
        special_abilities_full.append(ability_info)
    
    # VERBOSE: Full actions with complete descriptions and damage
    actions_full = []
    for a in data.get("actions", []):
        action_info = {
            "name": a.get("name"),
            "description": a.get("desc"),
            "attack_bonus": a.get("attack_bonus"),
            "damage": [
                {
                    "damage_type": d.get("damage_type", {}).get("name"),
                    "damage_dice": d.get("damage_dice")
                }
                for d in a.get("damage", [])
            ] if a.get("damage") else None,
            "dc": {
                "dc_type": a.get("dc", {}).get("dc_type", {}).get("name"),
                "dc_value": a.get("dc", {}).get("dc_value"),
                "success_type": a.get("dc", {}).get("success_type")
            } if a.get("dc") else None,
            "usage": a.get("usage"),
            "multiattack_type": a.get("multiattack_type"),
            "actions": a.get("actions"),
            "options": a.get("options")
        }
        actions_full.append(action_info)
    
    # VERBOSE: Full legendary actions
    legendary_actions_full = []
    if data.get("legendary_actions"):
        for la in data.get("legendary_actions"):
            la_info = {
                "name": la.get("name"),
                "description": la.get("desc"),
                "attack_bonus": la.get("attack_bonus"),
                "damage": la.get("damage"),
                "dc": la.get("dc")
            }
            legendary_actions_full.append(la_info)
    
    # VERBOSE: Reactions
    reactions_full = []
    for r in data.get("reactions", []):
        reactions_full.append({
            "name": r.get("name"),
            "description": r.get("desc"),
            "dc": r.get("dc")
        })
    
    # VERBOSE: Get condition immunity details
    condition_immunities_full = []
    for ci in data.get("condition_immunities", []):
        ci_url = ci.get("url", "")
        if ci_url:
            ci_data = _make_request(ci_url.replace("/api", ""))
            if not ci_data.get("error"):
                condition_immunities_full.append({
                    "name": ci_data.get("name"),
                    "index": ci_data.get("index"),
                    "description": ci_data.get("desc", [])
                })
            else:
                condition_immunities_full.append({"name": ci.get("name")})
        else:
            condition_immunities_full.append({"name": ci.get("name")})
    
    # VERBOSE: Get proficiency details
    proficiencies_full = []
    for p in data.get("proficiencies", []):
        prof_url = p.get("proficiency", {}).get("url", "")
        prof_info = {
            "name": p.get("proficiency", {}).get("name"),
            "value": p.get("value")
        }
        if prof_url:
            prof_data = _make_request(prof_url.replace("/api", ""))
            if not prof_data.get("error"):
                prof_info["type"] = prof_data.get("type")
                prof_info["classes"] = [c.get("name") for c in prof_data.get("classes", [])]
                prof_info["races"] = [r.get("name") for r in prof_data.get("races", [])]
        proficiencies_full.append(prof_info)
    
    # REDUCED: Get related monsters of same type (10 monsters to avoid timeout)
    monster_type = data.get("type", "")
    related_monsters = []
    if monster_type:
        type_monsters = _make_request(f"/monsters?type={monster_type}")
        if isinstance(type_monsters, dict) and "results" in type_monsters:
            for m in type_monsters.get("results", [])[:10]:
                if m.get("index") != data.get("index"):
                    try:
                        # MEGA VERBOSE: Fetch COMPLETE monster data
                        related_data = _make_request(f"/monsters/{m.get('index')}")
                        if not related_data.get("error"):
                            # Include FULL monster data for pattern to analyze
                            related_monsters.append({
                                "name": related_data.get("name"),
                                "index": related_data.get("index"),
                                "size": related_data.get("size"),
                                "type": related_data.get("type"),
                                "subtype": related_data.get("subtype"),
                                "alignment": related_data.get("alignment"),
                                "armor_class": related_data.get("armor_class"),
                                "hit_points": related_data.get("hit_points"),
                                "hit_dice": related_data.get("hit_dice"),
                                "hit_points_roll": related_data.get("hit_points_roll"),
                                "speed": related_data.get("speed"),
                                "strength": related_data.get("strength"),
                                "dexterity": related_data.get("dexterity"),
                                "constitution": related_data.get("constitution"),
                                "intelligence": related_data.get("intelligence"),
                                "wisdom": related_data.get("wisdom"),
                                "charisma": related_data.get("charisma"),
                                "proficiencies": related_data.get("proficiencies", []),
                                "damage_vulnerabilities": related_data.get("damage_vulnerabilities", []),
                                "damage_resistances": related_data.get("damage_resistances", []),
                                "damage_immunities": related_data.get("damage_immunities", []),
                                "condition_immunities": [ci.get("name") for ci in related_data.get("condition_immunities", [])],
                                "senses": related_data.get("senses"),
                                "languages": related_data.get("languages"),
                                "challenge_rating": related_data.get("challenge_rating"),
                                "xp": related_data.get("xp"),
                                "special_abilities": related_data.get("special_abilities", []),
                                "actions": related_data.get("actions", []),
                                "legendary_actions": related_data.get("legendary_actions", []),
                                "reactions": related_data.get("reactions", [])
                            })
                    except:
                        pass
    
    # REDUCED: Get monsters of similar CR (6 monsters to avoid timeout)
    cr = data.get("challenge_rating")
    similar_cr_monsters = []
    if cr is not None:
        cr_monsters = _make_request(f"/monsters?challenge_rating={cr}")
        if isinstance(cr_monsters, dict) and "results" in cr_monsters:
            for m in cr_monsters.get("results", [])[:6]:
                if m.get("index") != data.get("index") and m.get("index") not in [rm.get("index") for rm in related_monsters]:
                    try:
                        # MEGA VERBOSE: Fetch COMPLETE monster data
                        cr_data = _make_request(f"/monsters/{m.get('index')}")
                        if not cr_data.get("error"):
                            similar_cr_monsters.append({
                                "name": cr_data.get("name"),
                                "index": cr_data.get("index"),
                                "size": cr_data.get("size"),
                                "type": cr_data.get("type"),
                                "subtype": cr_data.get("subtype"),
                                "alignment": cr_data.get("alignment"),
                                "armor_class": cr_data.get("armor_class"),
                                "hit_points": cr_data.get("hit_points"),
                                "hit_dice": cr_data.get("hit_dice"),
                                "speed": cr_data.get("speed"),
                                "strength": cr_data.get("strength"),
                                "dexterity": cr_data.get("dexterity"),
                                "constitution": cr_data.get("constitution"),
                                "intelligence": cr_data.get("intelligence"),
                                "wisdom": cr_data.get("wisdom"),
                                "charisma": cr_data.get("charisma"),
                                "proficiencies": cr_data.get("proficiencies", []),
                                "damage_vulnerabilities": cr_data.get("damage_vulnerabilities", []),
                                "damage_resistances": cr_data.get("damage_resistances", []),
                                "damage_immunities": cr_data.get("damage_immunities", []),
                                "condition_immunities": [ci.get("name") for ci in cr_data.get("condition_immunities", [])],
                                "senses": cr_data.get("senses"),
                                "languages": cr_data.get("languages"),
                                "challenge_rating": cr_data.get("challenge_rating"),
                                "xp": cr_data.get("xp"),
                                "special_abilities": cr_data.get("special_abilities", []),
                                "actions": cr_data.get("actions", [])
                            })
                    except:
                        pass
    
    # REDUCED: Get monsters from adjacent CR levels (6 monsters total to avoid timeout)
    adjacent_cr_monsters = []
    if cr is not None:
        adjacent_crs = []
        if cr >= 1:
            adjacent_crs.append(cr - 1)
        if cr >= 0.5:
            adjacent_crs.append(cr + 1)
        
        for adj_cr in adjacent_crs[:2]:  # Only 2 adjacent CRs
            adj_monsters = _make_request(f"/monsters?challenge_rating={adj_cr}")
            if isinstance(adj_monsters, dict) and "results" in adj_monsters:
                for m in adj_monsters.get("results", [])[:3]:  # Only 3 per CR
                    try:
                        adj_data = _make_request(f"/monsters/{m.get('index')}")
                        if not adj_data.get("error"):
                            adjacent_cr_monsters.append({
                                "name": adj_data.get("name"),
                                "index": adj_data.get("index"),
                                "type": adj_data.get("type"),
                                "challenge_rating": adj_data.get("challenge_rating"),
                                "hit_points": adj_data.get("hit_points"),
                                "armor_class": adj_data.get("armor_class"),
                                "speed": adj_data.get("speed"),
                                "special_abilities_count": len(adj_data.get("special_abilities", [])),
                                "actions_count": len(adj_data.get("actions", [])),
                                "actions": adj_data.get("actions", [])
                            })
                    except:
                        pass
    
    # VERBOSE: Get damage type details
    damage_types_full = {}
    all_damage_types = set()
    all_damage_types.update(data.get("damage_vulnerabilities", []))
    all_damage_types.update(data.get("damage_resistances", []))
    all_damage_types.update(data.get("damage_immunities", []))
    
    for dt in all_damage_types:
        dt_data = _make_request(f"/damage-types/{dt.lower().replace(' ', '-')}")
        if not dt_data.get("error"):
            damage_types_full[dt] = {
                "name": dt_data.get("name"),
                "index": dt_data.get("index"),
                "description": dt_data.get("desc", [])
            }
    
    # MODERATE: Fetch up to 5 spells if monster has spellcasting
    spellcasting_spells_full = []
    spell_count = 0
    for sa in special_abilities_full:
        if sa.get("spellcasting") and sa["spellcasting"].get("spells") and spell_count < 5:
            for spell in sa["spellcasting"]["spells"]:
                if spell_count >= 5:
                    break
                spell_name = spell.get("name", "").lower().replace(" ", "-")
                if spell_name:
                    spell_data = _make_request(f"/spells/{spell_name}")
                    if not spell_data.get("error"):
                        spellcasting_spells_full.append({
                            "name": spell_data.get("name"),
                            "level": spell_data.get("level"),
                            "school": spell_data.get("school", {}).get("name"),
                            "casting_time": spell_data.get("casting_time"),
                            "range": spell_data.get("range")
                        })
                        spell_count += 1
    
    return {
        "success": True,
        "monster": {
            "index": data.get("index"),
            "name": data.get("name"),
            "desc": data.get("desc"),
            "size": data.get("size"),
            "type": data.get("type"),
            "subtype": data.get("subtype"),
            "alignment": data.get("alignment"),
            "armor_class_primary": data.get("armor_class", [{}])[0].get("value") if data.get("armor_class") else None,
            "armor_class_details": armor_class_details,
            "hit_points": data.get("hit_points"),
            "hit_dice": data.get("hit_dice"),
            "hit_points_roll": data.get("hit_points_roll"),
            "speed": data.get("speed"),
            "stats": stats,
            "stat_modifiers": stat_modifiers,
            "proficiencies": [
                {"name": p.get("proficiency", {}).get("name"), "value": p.get("value")}
                for p in data.get("proficiencies", [])
            ],
            "damage_vulnerabilities": data.get("damage_vulnerabilities", []),
            "damage_resistances": data.get("damage_resistances", []),
            "damage_immunities": data.get("damage_immunities", []),
            "condition_immunities": [ci.get("name") for ci in data.get("condition_immunities", [])],
            "senses": data.get("senses", {}),
            "languages": data.get("languages"),
            "challenge_rating": data.get("challenge_rating"),
            "proficiency_bonus": data.get("proficiency_bonus"),
            "xp": data.get("xp"),
            # VERBOSE: Full ability data for pattern to extract summary from
            "special_abilities": special_abilities_full,
            "actions": actions_full,
            "reactions": reactions_full if reactions_full else None,
            "legendary_actions": legendary_actions_full if legendary_actions_full else None,
            "lair_actions": data.get("lair_actions"),
            "image": data.get("image")
        },
        # VERBOSE: Extended data for pattern to use
        "condition_immunities_full": condition_immunities_full,
        "proficiencies_full": proficiencies_full,
        "damage_types_full": damage_types_full,
        "spellcasting_spells_full": spellcasting_spells_full,
        "related_monsters": {
            "same_type": {
                "type": monster_type,
                "count": len(related_monsters),
                "monsters": related_monsters
            },
            "same_cr": {
                "challenge_rating": cr,
                "count": len(similar_cr_monsters),
                "monsters": similar_cr_monsters
            },
            "adjacent_cr": {
                "count": len(adjacent_cr_monsters),
                "monsters": adjacent_cr_monsters
            }
        },
        # MEGA VERBOSE: Include raw API response for maximum data
        "raw_api_data": data
    }


def _get_spell(spell_name: str) -> dict:
    """Get detailed information about a spell with VERBOSE full data for skill mode."""
    data = _make_request(f"/spells/{spell_name.lower().replace(' ', '-')}")
    
    if "error" in data:
        return data
    
    # VERBOSE: Get full damage scaling
    damage_info = None
    if data.get("damage"):
        damage_info = {
            "damage_type": data.get("damage", {}).get("damage_type", {}).get("name"),
            "damage_at_slot_level": data.get("damage", {}).get("damage_at_slot_level", {}),
            "damage_at_character_level": data.get("damage", {}).get("damage_at_character_level", {})
        }
    
    # VERBOSE: Get heal scaling
    heal_info = None
    if data.get("heal_at_slot_level"):
        heal_info = data.get("heal_at_slot_level")
    
    # VERBOSE: Get DC info
    dc_info = None
    if data.get("dc"):
        dc_info = {
            "dc_type": data.get("dc", {}).get("dc_type", {}).get("name"),
            "dc_success": data.get("dc", {}).get("dc_success"),
            "description": data.get("dc", {}).get("desc")
        }
    
    # VERBOSE: Generate related spells analysis
    related_spells = []
    school = data.get("school", {}).get("index", "")
    level = data.get("level", 0)
    
    # Fetch spells from same school
    school_spells = _make_request(f"/spells?school={school}")
    if isinstance(school_spells, dict) and "results" in school_spells:
        for sp in school_spells.get("results", [])[:20]:
            if sp.get("index") != data.get("index"):
                related_spells.append({
                    "name": sp.get("name"),
                    "level": sp.get("level"),
                    "relationship": "same_school",
                    "url": sp.get("url")
                })
    
    return {
        "success": True,
        "spell": {
            "index": data.get("index"),
            "name": data.get("name"),
            "level": data.get("level"),
            "school": data.get("school", {}).get("name"),
            "casting_time": data.get("casting_time"),
            "range": data.get("range"),
            "components": data.get("components", []),
            "material": data.get("material"),
            "duration": data.get("duration"),
            "concentration": data.get("concentration"),
            "ritual": data.get("ritual"),
            # VERBOSE: Full descriptions without truncation
            "description": data.get("desc", []),
            "higher_level": data.get("higher_level", []),
            "classes": [c.get("name") for c in data.get("classes", [])],
            "subclasses": [sc.get("name") for sc in data.get("subclasses", [])],
            # VERBOSE: Full damage/heal info
            "damage": damage_info,
            "heal_at_slot_level": heal_info,
            "dc": dc_info,
            "area_of_effect": data.get("area_of_effect"),
            "attack_type": data.get("attack_type")
        },
        # VERBOSE: Related spells for pattern to use for comparison
        "related_spells": {
            "same_school_count": len(related_spells),
            "spells": related_spells
        }
    }


# ============== Tool Handlers ==============

async def on_get_class(context: RunContextWrapper, params_str: str) -> Any:
    """Handler for getting class info."""
    params = _parse_params(params_str)
    class_name = params.get("class_name")
    
    if not class_name:
        return {"error": "class_name is required", "success": False}
    
    result = _get_class(class_name)
    return result


async def on_get_race(context: RunContextWrapper, params_str: str) -> Any:
    """Handler for getting race info."""
    params = _parse_params(params_str)
    race_name = params.get("race_name")
    
    if not race_name:
        return {"error": "race_name is required", "success": False}
    
    result = _get_race(race_name)
    return result


async def on_get_class_spells(context: RunContextWrapper, params_str: str) -> Any:
    """Handler for getting class spells."""
    params = _parse_params(params_str)
    class_name = params.get("class_name")
    
    if not class_name:
        return {"error": "class_name is required", "success": False}
    
    result = _get_class_spells(class_name)
    return result


async def on_get_equipment_category(context: RunContextWrapper, params_str: str) -> Any:
    """Handler for getting equipment category."""
    params = _parse_params(params_str)
    category = params.get("category")
    
    if not category:
        return {"error": "category is required", "success": False}
    
    result = _get_equipment_category(category)
    return result


async def on_get_monster(context: RunContextWrapper, params_str: str) -> Any:
    """Handler for getting monster info."""
    params = _parse_params(params_str)
    monster_name = params.get("monster_name")
    
    if not monster_name:
        return {"error": "monster_name is required", "success": False}
    
    result = _get_monster(monster_name)
    return result


async def on_get_spell(context: RunContextWrapper, params_str: str) -> Any:
    """Handler for getting spell info."""
    params = _parse_params(params_str)
    spell_name = params.get("spell_name")
    
    if not spell_name:
        return {"error": "spell_name is required", "success": False}
    
    result = _get_spell(spell_name)
    return result


# ============== Tool Definitions ==============

tool_dnd_get_class = FunctionTool(
    name='local-dnd_get_class',
    description='''Get detailed information about a D&D 5e class.

**Returns:** dict:
{
  "success": bool,
  "class": {
    "index": str,
    "name": str,
    "hit_die": int,
    "proficiency_choices": [{"choose": int, "type": str, "options": [str]}],
    "proficiencies": [str],
    "saving_throws": [str],
    "starting_equipment": [{"name": str, "quantity": int}],
    "class_levels_url": str,
    "subclasses": [str],
    "spellcasting": {"level": int, "spellcasting_ability": str} | null,
    "multi_classing": {
      "prerequisites": [{"ability": str, "minimum": int}],
      "proficiencies": [str]
    } | null
  }
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "class_name": {
                "type": "string",
                "description": "Name of the class (e.g., fighter, wizard, rogue, cleric, paladin, warlock)"
            }
        },
        "required": ["class_name"]
    },
    on_invoke_tool=on_get_class
)

tool_dnd_get_race = FunctionTool(
    name='local-dnd_get_race',
    description='''Get detailed information about a D&D 5e race.

**Returns:** dict:
{
  "success": bool,
  "race": {
    "index": str,
    "name": str,
    "speed": int,
    "ability_bonuses": [{"ability": str, "bonus": int}],
    "alignment": str,
    "age": str,
    "size": str,
    "size_description": str,
    "starting_proficiencies": [str],
    "languages": [str],
    "language_desc": str,
    "traits": [str],
    "subraces": [str]
  }
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "race_name": {
                "type": "string",
                "description": "Name of the race (e.g., human, elf, dwarf, halfling, dragonborn, tiefling)"
            }
        },
        "required": ["race_name"]
    },
    on_invoke_tool=on_get_race
)

tool_dnd_get_class_spells = FunctionTool(
    name='local-dnd_get_class_spells',
    description='''Get all spells available to a specific D&D 5e class, organized by spell level.

**Returns:** dict:
{
  "success": bool,
  "class": str,
  "total_spells": int,
  "spells_by_level": {
    "level_0": {"count": int, "spells": [str]},
    "level_1": {"count": int, "spells": [str]},
    ...
  },
  "sample_spells": [str]
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "class_name": {
                "type": "string",
                "description": "Name of the spellcasting class (e.g., wizard, cleric, bard, warlock)"
            }
        },
        "required": ["class_name"]
    },
    on_invoke_tool=on_get_class_spells
)

tool_dnd_get_equipment_category = FunctionTool(
    name='local-dnd_get_equipment_category',
    description='''Get equipment list for a specific category in D&D 5e.

**Returns:** dict:
{
  "success": bool,
  "category": {
    "index": str,
    "name": str,
    "total_items": int,
    "equipment": [str]
  }
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "category": {
                "type": "string",
                "description": "Equipment category (e.g., weapon, armor, adventuring-gear, tools)"
            }
        },
        "required": ["category"]
    },
    on_invoke_tool=on_get_equipment_category
)

tool_dnd_get_monster = FunctionTool(
    name='local-dnd_get_monster',
    description='''Get detailed information about a D&D 5e monster.

**Returns:** dict:
{
  "success": bool,
  "monster": {
    "index": str,
    "name": str,
    "size": str,
    "type": str,
    "subtype": str | null,
    "alignment": str,
    "armor_class": int,
    "hit_points": int,
    "hit_dice": str,
    "speed": {"walk": str, "fly": str, ...},
    "stats": {"strength": int, "dexterity": int, "constitution": int, "intelligence": int, "wisdom": int, "charisma": int},
    "proficiencies": [{"name": str, "value": int}],
    "damage_vulnerabilities": [str],
    "damage_resistances": [str],
    "damage_immunities": [str],
    "condition_immunities": [str],
    "senses": {"darkvision": str, "passive_perception": int, ...},
    "languages": str,
    "challenge_rating": float,
    "xp": int,
    "special_abilities": [{"name": str, "desc": str}],
    "actions": [{"name": str, "desc": str}],
    "legendary_actions": [{"name": str, "desc": str}] | null
  }
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "monster_name": {
                "type": "string",
                "description": "Name of the monster using lowercase with hyphens (e.g., adult-red-dragon, kraken, aboleth, lich, tarrasque). Note: Some iconic monsters like beholder, mind-flayer are not in SRD."
            }
        },
        "required": ["monster_name"]
    },
    on_invoke_tool=on_get_monster
)

tool_dnd_get_spell = FunctionTool(
    name='local-dnd_get_spell',
    description='''Get detailed information about a D&D 5e spell.

**Returns:** dict:
{
  "success": bool,
  "spell": {
    "index": str,
    "name": str,
    "level": int,
    "school": str,
    "casting_time": str,
    "range": str,
    "components": [str],
    "material": str | null,
    "duration": str,
    "concentration": bool,
    "ritual": bool,
    "description": str,
    "higher_level": str | null,
    "classes": [str],
    "subclasses": [str],
    "damage": str | null
  }
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "spell_name": {
                "type": "string",
                "description": "Name of the spell (e.g., fireball, magic-missile, cure-wounds)"
            }
        },
        "required": ["spell_name"]
    },
    on_invoke_tool=on_get_spell
)


# Export all tools as a list
dnd_api_tools = [
    tool_dnd_get_class,
    tool_dnd_get_race,
    tool_dnd_get_class_spells,
    tool_dnd_get_equipment_category,
    tool_dnd_get_monster,
    tool_dnd_get_spell,
]

