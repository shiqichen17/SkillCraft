"""
Cat Facts API Tools - Enhanced for 5x5 Skill Mode

Provides tools to query cat breed information and facts.
Designed for skill mode scenarios with breed-centric data collection.

API Documentation: https://catfact.ninja/
No authentication required.

5x5 Structure:
- 5 breeds: Persian, Siamese, Maine Coon, Ragdoll, Bengal
- 5 tools per breed:
  1. catfacts_breed_profile - Comprehensive breed profile
  2. catfacts_breed_relatives - Breeds from same country
  3. catfacts_breed_coat_family - Breeds with similar coat
  4. catfacts_breed_facts - Curated facts collection
  5. catfacts_breed_encyclopedia - Full encyclopedia entry
"""

import json
from typing import Any, List, Dict
from agents.tool import FunctionTool, RunContextWrapper
import requests

# Base URL for Cat Facts API
CATFACTS_BASE_URL = "https://catfact.ninja"

# Breed characteristics database (for enhanced data)
BREED_CHARACTERISTICS = {
    "persian": {
        "temperament": "Calm, gentle, quiet",
        "lifespan": "12-17 years",
        "weight": "7-12 lbs",
        "grooming": "High maintenance",
        "activity_level": "Low",
        "good_with_children": True,
        "good_with_pets": True,
        "shedding": "High",
        "health_concerns": ["Polycystic kidney disease", "Breathing difficulties", "Eye conditions"],
        "description": "The Persian cat is known for its long, luxurious coat and sweet, gentle personality. They are one of the oldest and most popular cat breeds."
    },
    "siamese": {
        "temperament": "Vocal, social, intelligent",
        "lifespan": "12-20 years",
        "weight": "6-14 lbs",
        "grooming": "Low maintenance",
        "activity_level": "High",
        "good_with_children": True,
        "good_with_pets": True,
        "shedding": "Low",
        "health_concerns": ["Respiratory issues", "Dental problems", "Heart disease"],
        "description": "The Siamese is one of the most recognizable cat breeds, known for their striking blue eyes, pointed coloration, and vocal nature."
    },
    "maine coon": {
        "temperament": "Friendly, playful, gentle giant",
        "lifespan": "12-15 years",
        "weight": "10-25 lbs",
        "grooming": "Moderate maintenance",
        "activity_level": "Moderate",
        "good_with_children": True,
        "good_with_pets": True,
        "shedding": "High",
        "health_concerns": ["Hip dysplasia", "Heart disease", "Spinal muscular atrophy"],
        "description": "The Maine Coon is one of the largest domesticated cat breeds, known for their friendly personality and impressive size."
    },
    "ragdoll": {
        "temperament": "Docile, calm, affectionate",
        "lifespan": "12-17 years",
        "weight": "10-20 lbs",
        "grooming": "Moderate maintenance",
        "activity_level": "Low to moderate",
        "good_with_children": True,
        "good_with_pets": True,
        "shedding": "Moderate",
        "health_concerns": ["Heart disease", "Bladder stones", "Feline infectious peritonitis"],
        "description": "Ragdolls are known for their tendency to go limp when picked up, hence their name. They are extremely docile and affectionate."
    },
    "bengal": {
        "temperament": "Active, playful, curious",
        "lifespan": "12-16 years",
        "weight": "8-15 lbs",
        "grooming": "Low maintenance",
        "activity_level": "Very high",
        "good_with_children": True,
        "good_with_pets": True,
        "shedding": "Low",
        "health_concerns": ["Heart disease", "Progressive retinal atrophy", "Anesthetic sensitivity"],
        "description": "The Bengal cat has a wild appearance with their spotted or marbled coat pattern, but they are fully domesticated and make energetic companions."
    }
}


def _make_request(endpoint: str, params: dict = None) -> Any:
    """Make a request to Cat Facts API with error handling."""
    url = f"{CATFACTS_BASE_URL}{endpoint}"
    headers = {"User-Agent": "DikaNong-PatternReuse/1.0", "Accept": "application/json"}
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
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


def _get_all_breeds() -> List[Dict]:
    """Fetch all breeds from API."""
    data = _make_request("/breeds", {"limit": 100})
    if isinstance(data, dict) and "error" in data:
        return []
    return data.get("data", [])


def _find_breed(breeds: List[Dict], breed_name: str) -> Dict:
    """Find a breed by name (case-insensitive partial match)."""
    breed_lower = breed_name.lower()
    for breed in breeds:
        if breed_lower in breed.get("breed", "").lower():
            return breed
    return None


def _get_facts(count: int = 50) -> List[Dict]:
    """Fetch facts from API. Enhanced to fetch more facts by default."""
    data = _make_request("/facts", {"limit": count})
    if isinstance(data, dict) and "error" in data:
        return []
    return data.get("data", [])


def _categorize_fact(length: int) -> str:
    """Categorize fact by length."""
    if length < 50:
        return "short"
    elif length < 100:
        return "medium"
    else:
        return "long"


def _analyze_fact(fact_data: Dict) -> Dict:
    """Analyze a single fact."""
    fact = fact_data.get("fact", "")
    length = fact_data.get("length", len(fact))
    words = fact.split()
    
    return {
        "fact": fact,
        "length": length,
        "word_count": len(words),
        "category": _categorize_fact(length),
        "avg_word_length": round(sum(len(w) for w in words) / max(len(words), 1), 2),
        "has_numbers": any(c.isdigit() for c in fact),
        "sentence_count": fact.count('.') + fact.count('!') + fact.count('?'),
        "starts_with_cat": fact.lower().startswith('cat'),
        "contains_statistics": any(word.isdigit() or '%' in word for word in words)
    }


# ============== Tool Implementation Functions ==============

def _get_breed_profile(breed_name: str) -> dict:
    """
    TOOL 1: Get comprehensive breed profile with related breeds and statistics.
    ENHANCED: Returns ALL related breeds with full details for maximum verbosity.
    """
    breeds = _get_all_breeds()
    
    if not breeds:
        return {"error": "Failed to fetch breed data", "success": False}
    
    # Find target breed
    target_breed = _find_breed(breeds, breed_name)
    
    if not target_breed:
        return {"error": f"Breed '{breed_name}' not found", "success": False}
    
    breed_key = breed_name.lower()
    characteristics = BREED_CHARACTERISTICS.get(breed_key, {})
    
    country = target_breed.get("country", "Unknown")
    coat = target_breed.get("coat", "Unknown")
    pattern = target_breed.get("pattern", "Unknown")
    
    # ENHANCED VERBOSE: Get ALL breeds from same country with FULL details
    same_country_breeds = []
    for b in breeds:
        if b.get("country") == country and b.get("breed") != target_breed.get("breed"):
            breed_info = {
                "breed": b.get("breed"),
                "coat": b.get("coat"),
                "pattern": b.get("pattern"),
                "origin": b.get("origin"),
                "coat_similarity": "exact" if b.get("coat") == coat else "different",
                "pattern_similarity": "exact" if b.get("pattern") == pattern else "different",
                "comparison_notes": f"Both from {country}. Coat: {b.get('coat')} vs {coat}."
            }
            # Add characteristics if available
            bkey = b.get("breed", "").lower()
            if bkey in BREED_CHARACTERISTICS:
                breed_info["characteristics"] = BREED_CHARACTERISTICS[bkey]
            same_country_breeds.append(breed_info)
    
    # ENHANCED VERBOSE: Get ALL breeds with same coat type with FULL details
    same_coat_breeds = []
    for b in breeds:
        if b.get("coat") == coat and b.get("breed") != target_breed.get("breed"):
            breed_info = {
                "breed": b.get("breed"),
                "country": b.get("country"),
                "pattern": b.get("pattern"),
                "origin": b.get("origin"),
                "country_similarity": "exact" if b.get("country") == country else "different",
                "pattern_similarity": "exact" if b.get("pattern") == pattern else "different",
                "comparison_notes": f"Both have {coat} coat. Country: {b.get('country')} vs {country}.",
                "grooming_compatibility": "similar" if coat == "Long" else "varies"
            }
            bkey = b.get("breed", "").lower()
            if bkey in BREED_CHARACTERISTICS:
                breed_info["characteristics"] = BREED_CHARACTERISTICS[bkey]
            same_coat_breeds.append(breed_info)
    
    # ENHANCED VERBOSE: Get ALL breeds with same pattern
    same_pattern_breeds = []
    for b in breeds:
        if b.get("pattern") == pattern and b.get("breed") != target_breed.get("breed"):
            breed_info = {
                "breed": b.get("breed"),
                "country": b.get("country"),
                "coat": b.get("coat"),
                "origin": b.get("origin"),
                "visual_notes": f"Similar {pattern} pattern appearance"
            }
            bkey = b.get("breed", "").lower()
            if bkey in BREED_CHARACTERISTICS:
                breed_info["characteristics"] = BREED_CHARACTERISTICS[bkey]
            same_pattern_breeds.append(breed_info)
    
    # ENHANCED: Calculate comprehensive statistics
    coat_distribution = {}
    country_distribution = {}
    pattern_distribution = {}
    origin_distribution = {}
    
    for b in breeds:
        c = b.get("coat", "Unknown")
        coat_distribution[c] = coat_distribution.get(c, 0) + 1
        co = b.get("country", "Unknown")
        country_distribution[co] = country_distribution.get(co, 0) + 1
        pt = b.get("pattern", "Unknown")
        pattern_distribution[pt] = pattern_distribution.get(pt, 0) + 1
        og = b.get("origin", "Unknown")
        origin_distribution[og] = origin_distribution.get(og, 0) + 1
    
    # Sort all distributions
    coat_distribution = dict(sorted(coat_distribution.items(), key=lambda x: -x[1]))
    country_distribution = dict(sorted(country_distribution.items(), key=lambda x: -x[1]))
    pattern_distribution = dict(sorted(pattern_distribution.items(), key=lambda x: -x[1]))
    origin_distribution = dict(sorted(origin_distribution.items(), key=lambda x: -x[1]))
    
    # ENHANCED: Calculate rankings
    coat_rank = list(coat_distribution.keys()).index(coat) + 1 if coat in coat_distribution else None
    country_breeds_count = len(same_country_breeds) + 1
    country_rank = sorted([(k, v) for k, v in country_distribution.items()], key=lambda x: -x[1])
    country_rank_pos = next((i for i, (k, v) in enumerate(country_rank) if k == country), None)
    
    # ENHANCED: Full breed database snapshot for context
    all_breeds_summary = []
    for b in breeds:
        all_breeds_summary.append({
            "breed": b.get("breed"),
            "country": b.get("country"),
            "coat": b.get("coat"),
            "pattern": b.get("pattern"),
            "origin": b.get("origin"),
            "matches_target_country": b.get("country") == country,
            "matches_target_coat": b.get("coat") == coat,
            "matches_target_pattern": b.get("pattern") == pattern
        })
    
    return {
        "success": True,
        "breed": {
            "name": target_breed.get("breed"),
            "country": country,
            "origin": target_breed.get("origin"),
            "coat": coat,
            "pattern": pattern,
            "characteristics": characteristics,
            "raw_api_data": target_breed
        },
        "related_breeds": {
            "same_country": same_country_breeds,  # ALL breeds, not limited
            "same_country_count": len(same_country_breeds),
            "same_coat": same_coat_breeds,  # ALL breeds, not limited
            "same_coat_count": len(same_coat_breeds),
            "same_pattern": same_pattern_breeds,  # NEW: pattern-based grouping
            "same_pattern_count": len(same_pattern_breeds)
        },
        "database_statistics": {
            "total_breeds": len(breeds),
            "coat_type_distribution": coat_distribution,
            "country_distribution": country_distribution,
            "pattern_distribution": pattern_distribution,
            "origin_distribution": origin_distribution,
            "breeds_from_target_country": country_breeds_count,
            "breeds_with_target_coat": len(same_coat_breeds) + 1,
            "breeds_with_target_pattern": len(same_pattern_breeds) + 1,
            "target_coat_rank": coat_rank,
            "target_country_rank": country_rank_pos + 1 if country_rank_pos is not None else None
        },
        "all_breeds_reference": all_breeds_summary,  # ENHANCED: Full database for context
        "analysis": {
            "country_concentration": f"{country} has {country_breeds_count} breeds ({round(country_breeds_count/len(breeds)*100, 1)}% of all breeds)",
            "coat_popularity": f"{coat} coat is #{coat_rank} most common" if coat_rank else "Unknown",
            "uniqueness_score": round(100 - (len(same_country_breeds) + len(same_coat_breeds)) / len(breeds) * 50, 1)
        },
        "api_info": {
            "endpoint": "/breeds",
            "api_version": "v1",
            "queries_made": 1,
            "total_breeds_fetched": len(breeds)
        }
    }


def _get_breed_relatives(breed_name: str) -> dict:
    """
    TOOL 2: Get detailed information about all breeds from the same country.
    ENHANCED: Returns comprehensive cross-comparison between all relatives.
    """
    breeds = _get_all_breeds()
    
    if not breeds:
        return {"error": "Failed to fetch breed data", "success": False}
    
    target_breed = _find_breed(breeds, breed_name)
    
    if not target_breed:
        return {"error": f"Breed '{breed_name}' not found", "success": False}
    
    country = target_breed.get("country", "Unknown")
    target_coat = target_breed.get("coat", "Unknown")
    target_pattern = target_breed.get("pattern", "Unknown")
    
    # ENHANCED VERBOSE: Get all breeds from same country with FULL comparison
    relatives = []
    coat_types_in_country = {}
    patterns_in_country = {}
    origins_in_country = {}
    
    for b in breeds:
        if b.get("country") == country:
            breed_info = {
                "breed": b.get("breed"),
                "coat": b.get("coat"),
                "pattern": b.get("pattern"),
                "origin": b.get("origin"),
                "is_target": b.get("breed") == target_breed.get("breed"),
                "coat_match": b.get("coat") == target_coat,
                "pattern_match": b.get("pattern") == target_pattern,
                "similarity_score": 0,
                "raw_breed_data": b  # ENHANCED: Include raw data
            }
            
            # Calculate similarity score
            if b.get("coat") == target_coat:
                breed_info["similarity_score"] += 30
            if b.get("pattern") == target_pattern:
                breed_info["similarity_score"] += 20
            if b.get("origin") == target_breed.get("origin"):
                breed_info["similarity_score"] += 10
            if breed_info["is_target"]:
                breed_info["similarity_score"] = 100
            
            # Add detailed comparison notes
            breed_info["comparison_analysis"] = {
                "coat_comparison": f"{b.get('coat')} vs {target_coat} ({'MATCH' if b.get('coat') == target_coat else 'DIFFERENT'})",
                "pattern_comparison": f"{b.get('pattern')} vs {target_pattern} ({'MATCH' if b.get('pattern') == target_pattern else 'DIFFERENT'})",
                "shared_traits": [],
                "different_traits": []
            }
            
            if b.get("coat") == target_coat:
                breed_info["comparison_analysis"]["shared_traits"].append(f"Same coat type: {target_coat}")
            else:
                breed_info["comparison_analysis"]["different_traits"].append(f"Different coat: {b.get('coat')} vs {target_coat}")
            
            if b.get("pattern") == target_pattern:
                breed_info["comparison_analysis"]["shared_traits"].append(f"Same pattern: {target_pattern}")
            else:
                breed_info["comparison_analysis"]["different_traits"].append(f"Different pattern: {b.get('pattern')} vs {target_pattern}")
            
            # Add characteristics if available
            breed_key = b.get("breed", "").lower()
            if breed_key in BREED_CHARACTERISTICS:
                breed_info["characteristics"] = BREED_CHARACTERISTICS[breed_key]
            
            relatives.append(breed_info)
            
            # Track distributions
            ct = b.get("coat", "Unknown")
            coat_types_in_country[ct] = coat_types_in_country.get(ct, 0) + 1
            pt = b.get("pattern", "Unknown")
            patterns_in_country[pt] = patterns_in_country.get(pt, 0) + 1
            og = b.get("origin", "Unknown")
            origins_in_country[og] = origins_in_country.get(og, 0) + 1
    
    # Sort by similarity score
    relatives.sort(key=lambda x: -x["similarity_score"])
    
    # ENHANCED: Calculate comprehensive global statistics
    global_coat_dist = {}
    global_country_dist = {}
    global_pattern_dist = {}
    global_origin_dist = {}
    
    for b in breeds:
        ct = b.get("coat", "Unknown")
        global_coat_dist[ct] = global_coat_dist.get(ct, 0) + 1
        co = b.get("country", "Unknown")
        global_country_dist[co] = global_country_dist.get(co, 0) + 1
        pt = b.get("pattern", "Unknown")
        global_pattern_dist[pt] = global_pattern_dist.get(pt, 0) + 1
        og = b.get("origin", "Unknown")
        global_origin_dist[og] = global_origin_dist.get(og, 0) + 1
    
    # ENHANCED: Cross-comparison matrix between relatives
    cross_comparison = []
    for i, r1 in enumerate(relatives[:15]):  # Top 15 for cross-comparison
        for j, r2 in enumerate(relatives[:15]):
            if i < j:  # Only unique pairs
                cross_comparison.append({
                    "breed_1": r1["breed"],
                    "breed_2": r2["breed"],
                    "coat_match": r1["coat"] == r2["coat"],
                    "pattern_match": r1["pattern"] == r2["pattern"],
                    "origin_match": r1["origin"] == r2["origin"],
                    "similarity": sum([
                        30 if r1["coat"] == r2["coat"] else 0,
                        20 if r1["pattern"] == r2["pattern"] else 0,
                        10 if r1["origin"] == r2["origin"] else 0
                    ])
                })
    
    # ENHANCED: Country analysis
    country_ranking = sorted(global_country_dist.items(), key=lambda x: -x[1])
    country_rank = next((i for i, (k, v) in enumerate(country_ranking) if k == country), None)
    
    # ENHANCED: Breeds from neighboring/similar countries
    similar_countries = []
    for co, count in country_ranking[:20]:
        if co != country:
            breeds_from_country = [b for b in breeds if b.get("country") == co]
            similar_countries.append({
                "country": co,
                "breed_count": count,
                "breeds": [{
                    "breed": b.get("breed"),
                    "coat": b.get("coat"),
                    "pattern": b.get("pattern")
                } for b in breeds_from_country]
            })
    
    return {
        "success": True,
        "target_breed": target_breed.get("breed"),
        "target_breed_full_data": target_breed,
        "country": country,
        "relatives": relatives,
        "cross_comparison_matrix": cross_comparison,
        "country_statistics": {
            "total_breeds_in_country": len(relatives),
            "percentage_of_all_breeds": round(len(relatives) / max(len(breeds), 1) * 100, 2),
            "coat_types_distribution": coat_types_in_country,
            "pattern_distribution": patterns_in_country,
            "origin_distribution": origins_in_country,
            "unique_coat_types": len(coat_types_in_country),
            "unique_patterns": len(patterns_in_country),
            "unique_origins": len(origins_in_country),
            "most_common_coat": max(coat_types_in_country.items(), key=lambda x: x[1])[0] if coat_types_in_country else None,
            "most_common_pattern": max(patterns_in_country.items(), key=lambda x: x[1])[0] if patterns_in_country else None
        },
        "global_comparison": {
            "total_breeds_globally": len(breeds),
            "total_countries": len(set(b.get("country") for b in breeds)),
            "global_coat_distribution": global_coat_dist,
            "global_pattern_distribution": global_pattern_dist,
            "global_origin_distribution": global_origin_dist,
            "country_ranking": country_ranking,
            "target_country_rank": country_rank + 1 if country_rank is not None else None,
            "countries_with_more_breeds": country_rank if country_rank is not None else None
        },
        "similar_countries_data": similar_countries,
        "analysis": {
            "country_significance": f"{country} ranks #{country_rank + 1 if country_rank is not None else 'N/A'} with {len(relatives)} breeds",
            "coat_diversity": f"{len(coat_types_in_country)} different coat types in {country}",
            "pattern_diversity": f"{len(patterns_in_country)} different patterns in {country}",
            "avg_similarity_to_target": round(sum(r["similarity_score"] for r in relatives) / max(len(relatives), 1), 1)
        },
        "api_info": {
            "endpoint": "/breeds",
            "api_version": "v1",
            "queries_made": 1,
            "total_breeds_fetched": len(breeds)
        }
    }


def _get_breed_coat_family(breed_name: str) -> dict:
    """
    TOOL 3: Get all breeds with similar coat type and detailed comparison.
    ENHANCED: Returns comprehensive coat analysis with cross-breed comparisons.
    """
    breeds = _get_all_breeds()
    
    if not breeds:
        return {"error": "Failed to fetch breed data", "success": False}
    
    target_breed = _find_breed(breeds, breed_name)
    
    if not target_breed:
        return {"error": f"Breed '{breed_name}' not found", "success": False}
    
    target_coat = target_breed.get("coat", "Unknown")
    target_country = target_breed.get("country", "Unknown")
    target_pattern = target_breed.get("pattern", "Unknown")
    target_origin = target_breed.get("origin", "Unknown")
    
    # ENHANCED VERBOSE: Get ALL breeds with same coat type with FULL details
    coat_family = []
    countries_with_coat = {}
    patterns_with_coat = {}
    origins_with_coat = {}
    
    for b in breeds:
        if b.get("coat") == target_coat:
            similarity_score = 0
            if b.get("country") == target_country:
                similarity_score += 30
            if b.get("pattern") == target_pattern:
                similarity_score += 20
            if b.get("origin") == target_origin:
                similarity_score += 10
            if b.get("breed") == target_breed.get("breed"):
                similarity_score += 50
            
            breed_info = {
                "breed": b.get("breed"),
                "country": b.get("country"),
                "pattern": b.get("pattern"),
                "origin": b.get("origin"),
                "is_target": b.get("breed") == target_breed.get("breed"),
                "similarity_score": similarity_score,
                "same_country": b.get("country") == target_country,
                "same_pattern": b.get("pattern") == target_pattern,
                "same_origin": b.get("origin") == target_origin,
                "raw_breed_data": b,  # ENHANCED: Full raw data
                "comparison_details": {
                    "country_comparison": f"{b.get('country')} vs {target_country}",
                    "pattern_comparison": f"{b.get('pattern')} vs {target_pattern}",
                    "origin_comparison": f"{b.get('origin')} vs {target_origin}",
                    "shared_attributes": sum([
                        1 if b.get("country") == target_country else 0,
                        1 if b.get("pattern") == target_pattern else 0,
                        1 if b.get("origin") == target_origin else 0
                    ])
                },
                "grooming_notes": {
                    "coat_type": target_coat,
                    "maintenance_level": "High" if target_coat == "Long" else ("Medium" if target_coat == "Semi-long" else "Low"),
                    "shedding_expected": "High" if target_coat in ["Long", "Semi-long"] else "Moderate",
                    "recommended_brushing": "Daily" if target_coat == "Long" else ("Weekly" if target_coat == "Semi-long" else "Occasional")
                }
            }
            
            # Add characteristics if available
            breed_key = b.get("breed", "").lower()
            if breed_key in BREED_CHARACTERISTICS:
                breed_info["characteristics"] = BREED_CHARACTERISTICS[breed_key]
            
            coat_family.append(breed_info)
            
            # Track distributions
            co = b.get("country", "Unknown")
            countries_with_coat[co] = countries_with_coat.get(co, 0) + 1
            pt = b.get("pattern", "Unknown")
            patterns_with_coat[pt] = patterns_with_coat.get(pt, 0) + 1
            og = b.get("origin", "Unknown")
            origins_with_coat[og] = origins_with_coat.get(og, 0) + 1
    
    # Sort by similarity
    coat_family.sort(key=lambda x: -x.get("similarity_score", 0))
    
    # ENHANCED: Analyze ALL coat types globally with full breed lists
    all_coat_types = {}
    coat_type_breeds = {}
    for b in breeds:
        ct = b.get("coat", "Unknown")
        all_coat_types[ct] = all_coat_types.get(ct, 0) + 1
        if ct not in coat_type_breeds:
            coat_type_breeds[ct] = []
        coat_type_breeds[ct].append({
            "breed": b.get("breed"),
            "country": b.get("country"),
            "pattern": b.get("pattern")
        })
    
    # ENHANCED: Cross-comparison between coat family members
    coat_family_cross_comparison = []
    for i, b1 in enumerate(coat_family[:20]):
        for j, b2 in enumerate(coat_family[:20]):
            if i < j:
                coat_family_cross_comparison.append({
                    "breed_1": b1["breed"],
                    "breed_2": b2["breed"],
                    "country_match": b1["country"] == b2["country"],
                    "pattern_match": b1["pattern"] == b2["pattern"],
                    "origin_match": b1["origin"] == b2["origin"],
                    "pair_similarity": sum([
                        30 if b1["country"] == b2["country"] else 0,
                        20 if b1["pattern"] == b2["pattern"] else 0,
                        10 if b1["origin"] == b2["origin"] else 0
                    ])
                })
    
    # ENHANCED: Other coat types comparison
    other_coat_analysis = []
    for ct, count in sorted(all_coat_types.items(), key=lambda x: -x[1]):
        if ct != target_coat:
            other_coat_analysis.append({
                "coat_type": ct,
                "breed_count": count,
                "percentage": round(count / len(breeds) * 100, 2),
                "sample_breeds": coat_type_breeds.get(ct, [])[:10],
                "comparison_to_target": {
                    "count_difference": count - len(coat_family),
                    "more_common": count > len(coat_family)
                }
            })
    
    # Calculate coat ranking
    coat_ranking = sorted(all_coat_types.items(), key=lambda x: -x[1])
    target_coat_rank = next((i for i, (k, v) in enumerate(coat_ranking) if k == target_coat), None)
    
    return {
        "success": True,
        "target_breed": target_breed.get("breed"),
        "target_breed_full_data": target_breed,
        "coat_type": target_coat,
        "coat_family": coat_family,
        "coat_family_cross_comparison": coat_family_cross_comparison,
        "coat_statistics": {
            "total_breeds_with_coat": len(coat_family),
            "percentage_of_all_breeds": round(len(coat_family) / max(len(breeds), 1) * 100, 2),
            "countries_represented": countries_with_coat,
            "unique_countries": len(countries_with_coat),
            "patterns_in_family": patterns_with_coat,
            "unique_patterns": len(patterns_with_coat),
            "origins_in_family": origins_with_coat,
            "unique_origins": len(origins_with_coat),
            "most_common_country": max(countries_with_coat.items(), key=lambda x: x[1])[0] if countries_with_coat else None,
            "most_common_pattern": max(patterns_with_coat.items(), key=lambda x: x[1])[0] if patterns_with_coat else None,
            "avg_similarity_to_target": round(sum(b["similarity_score"] for b in coat_family) / max(len(coat_family), 1), 1)
        },
        "global_coat_analysis": {
            "all_coat_types": all_coat_types,
            "total_coat_types": len(all_coat_types),
            "coat_ranking": coat_ranking,
            "most_common_coat": coat_ranking[0][0] if coat_ranking else None,
            "rarest_coat": coat_ranking[-1][0] if coat_ranking else None,
            "target_coat_rank": target_coat_rank + 1 if target_coat_rank is not None else None,
            "target_coat_is_most_common": target_coat_rank == 0 if target_coat_rank is not None else False
        },
        "other_coat_types_analysis": other_coat_analysis,
        "grooming_guide": {
            "coat_type": target_coat,
            "general_maintenance": "High maintenance" if target_coat == "Long" else ("Moderate" if target_coat == "Semi-long" else "Low maintenance"),
            "recommended_tools": ["Slicker brush", "Wide-tooth comb", "De-matting tool"] if target_coat == "Long" else ["Bristle brush", "Rubber grooming mitt"],
            "bathing_frequency": "Monthly" if target_coat == "Long" else "As needed",
            "professional_grooming": "Recommended" if target_coat == "Long" else "Optional"
        },
        "analysis": {
            "coat_popularity": f"{target_coat} is #{target_coat_rank + 1 if target_coat_rank is not None else 'N/A'} most common coat type",
            "family_diversity": f"{len(coat_family)} breeds with {len(countries_with_coat)} different countries",
            "pattern_variety": f"{len(patterns_with_coat)} different patterns within {target_coat} coat family"
        },
        "api_info": {
            "endpoint": "/breeds",
            "api_version": "v1",
            "queries_made": 1,
            "total_breeds_fetched": len(breeds)
        }
    }


def _get_breed_facts(breed_name: str) -> dict:
    """
    TOOL 4: Get curated facts collection with detailed analysis.
    ENHANCED: Fetches 50 facts with comprehensive multi-dimensional analysis.
    """
    breeds = _get_all_breeds()
    
    if not breeds:
        return {"error": "Failed to fetch breed data", "success": False}
    
    target_breed = _find_breed(breeds, breed_name)
    
    if not target_breed:
        return {"error": f"Breed '{breed_name}' not found", "success": False}
    
    # ENHANCED: Fetch more facts (50 instead of 30)
    facts_data = _get_facts(50)
    
    if not facts_data:
        return {"error": "Failed to fetch facts", "success": False}
    
    # ENHANCED: Comprehensive fact analysis
    analyzed_facts = []
    total_length = 0
    category_counts = {"short": 0, "medium": 0, "long": 0}
    word_counts = []
    word_length_distribution = {}
    topic_keywords = {
        "behavior": ["behavior", "hunt", "play", "sleep", "groom", "scratch", "climb", "jump"],
        "anatomy": ["eye", "ear", "tail", "paw", "claw", "whisker", "fur", "bone", "muscle"],
        "health": ["disease", "health", "life", "age", "year", "old", "young", "kitten"],
        "diet": ["eat", "food", "hunt", "prey", "meat", "water", "drink"],
        "history": ["ancient", "egypt", "history", "century", "year", "domesticat"],
        "senses": ["see", "hear", "smell", "sense", "vision", "sound", "night"]
    }
    topic_counts = {k: 0 for k in topic_keywords}
    
    for fact_item in facts_data:
        analysis = _analyze_fact(fact_item)
        
        # ENHANCED: Add topic classification
        fact_lower = analysis["fact"].lower()
        detected_topics = []
        for topic, keywords in topic_keywords.items():
            if any(kw in fact_lower for kw in keywords):
                detected_topics.append(topic)
                topic_counts[topic] += 1
        analysis["detected_topics"] = detected_topics
        analysis["primary_topic"] = detected_topics[0] if detected_topics else "general"
        
        # ENHANCED: Add readability metrics
        words = analysis["fact"].split()
        for word in words:
            wlen = len(word)
            word_length_distribution[wlen] = word_length_distribution.get(wlen, 0) + 1
        
        analysis["readability"] = {
            "avg_word_length": analysis["avg_word_length"],
            "complexity": "simple" if analysis["avg_word_length"] < 4.5 else ("moderate" if analysis["avg_word_length"] < 5.5 else "complex"),
            "sentence_complexity": "simple" if analysis["sentence_count"] <= 1 else ("moderate" if analysis["sentence_count"] <= 2 else "complex")
        }
        
        analyzed_facts.append(analysis)
        total_length += analysis["length"]
        category_counts[analysis["category"]] += 1
        word_counts.append(analysis["word_count"])
    
    # ENHANCED: Create multiple curated collections
    short_facts = [f for f in analyzed_facts if f["category"] == "short"]
    medium_facts = [f for f in analyzed_facts if f["category"] == "medium"]
    long_facts = [f for f in analyzed_facts if f["category"] == "long"]
    statistical_facts = [f for f in analyzed_facts if f["has_numbers"]]
    cat_starting_facts = [f for f in analyzed_facts if f["starts_with_cat"]]
    
    # ENHANCED: Topic-based collections
    topic_collections = {}
    for topic in topic_keywords:
        topic_collections[topic] = [f for f in analyzed_facts if topic in f.get("detected_topics", [])]
    
    # ENHANCED: Calculate comprehensive statistics
    avg_length = round(total_length / max(len(analyzed_facts), 1), 2)
    avg_words = round(sum(word_counts) / max(len(word_counts), 1), 2)
    
    breed_key = breed_name.lower()
    breed_chars = BREED_CHARACTERISTICS.get(breed_key, {})
    
    # ENHANCED: Word frequency analysis
    all_words = []
    for f in analyzed_facts:
        all_words.extend(f["fact"].lower().split())
    word_frequency = {}
    for word in all_words:
        # Clean word
        clean_word = ''.join(c for c in word if c.isalnum())
        if len(clean_word) > 3:  # Only words > 3 chars
            word_frequency[clean_word] = word_frequency.get(clean_word, 0) + 1
    top_words = sorted(word_frequency.items(), key=lambda x: -x[1])[:30]
    
    # ENHANCED: Fact complexity distribution
    complexity_distribution = {
        "simple": len([f for f in analyzed_facts if f["readability"]["complexity"] == "simple"]),
        "moderate": len([f for f in analyzed_facts if f["readability"]["complexity"] == "moderate"]),
        "complex": len([f for f in analyzed_facts if f["readability"]["complexity"] == "complex"])
    }
    
    return {
        "success": True,
        "target_breed": target_breed.get("breed"),
        "target_breed_full_data": target_breed,
        "breed_info": {
            "country": target_breed.get("country"),
            "coat": target_breed.get("coat"),
            "pattern": target_breed.get("pattern"),
            "origin": target_breed.get("origin"),
            "characteristics": breed_chars
        },
        "facts_collection": {
            "all_facts": analyzed_facts,  # ALL 50 facts with full analysis
            "short_facts": short_facts,
            "medium_facts": medium_facts,
            "long_facts": long_facts,
            "statistical_facts": statistical_facts,
            "cat_starting_facts": cat_starting_facts,
            "topic_collections": topic_collections
        },
        "facts_statistics": {
            "total_facts": len(analyzed_facts),
            "total_characters": total_length,
            "total_words": sum(word_counts),
            "average_length": avg_length,
            "average_word_count": avg_words,
            "min_length": min(f["length"] for f in analyzed_facts) if analyzed_facts else 0,
            "max_length": max(f["length"] for f in analyzed_facts) if analyzed_facts else 0,
            "length_std_dev": round((sum((f["length"] - avg_length) ** 2 for f in analyzed_facts) / max(len(analyzed_facts), 1)) ** 0.5, 2),
            "category_distribution": category_counts,
            "topic_distribution": topic_counts,
            "complexity_distribution": complexity_distribution,
            "facts_with_numbers": len(statistical_facts),
            "facts_starting_with_cat": len(cat_starting_facts),
            "longest_fact": max(analyzed_facts, key=lambda x: x["length"]) if analyzed_facts else None,
            "shortest_fact": min(analyzed_facts, key=lambda x: x["length"]) if analyzed_facts else None,
            "total_sentences": sum(f["sentence_count"] for f in analyzed_facts),
            "avg_sentences_per_fact": round(sum(f["sentence_count"] for f in analyzed_facts) / max(len(analyzed_facts), 1), 2)
        },
        "linguistic_analysis": {
            "word_length_distribution": dict(sorted(word_length_distribution.items())),
            "top_words": top_words,
            "vocabulary_richness": len(word_frequency),
            "total_unique_words": len(set(all_words)),
            "avg_word_length_overall": round(sum(len(w) for w in all_words) / max(len(all_words), 1), 2)
        },
        "breed_context": {
            "breed_name": target_breed.get("breed"),
            "related_to_breed": f"Facts collected in context of {target_breed.get('breed')} breed research",
            "breed_characteristics_summary": breed_chars.get("description", "No description available"),
            "potential_relevance": "General cat facts applicable to all breeds including " + target_breed.get("breed", "unknown")
        },
        "api_info": {
            "endpoint": "/facts",
            "api_version": "v1",
            "facts_requested": 50,
            "facts_received": len(analyzed_facts),
            "queries_made": 2
        }
    }


def _get_breed_encyclopedia(breed_name: str) -> dict:
    """
    TOOL 5: Generate comprehensive encyclopedia entry for the breed.
    ENHANCED: Creates exhaustive encyclopedia with all related breeds and extensive analysis.
    """
    breeds = _get_all_breeds()
    
    if not breeds:
        return {"error": "Failed to fetch breed data", "success": False}
    
    target_breed = _find_breed(breeds, breed_name)
    
    if not target_breed:
        return {"error": f"Breed '{breed_name}' not found", "success": False}
    
    breed_key = breed_name.lower()
    characteristics = BREED_CHARACTERISTICS.get(breed_key, {})
    
    country = target_breed.get("country", "Unknown")
    coat = target_breed.get("coat", "Unknown")
    pattern = target_breed.get("pattern", "Unknown")
    origin = target_breed.get("origin", "Unknown")
    
    # ENHANCED: Get ALL related breeds with full data
    same_country = []
    for b in breeds:
        if b.get("country") == country and b.get("breed") != target_breed.get("breed"):
            breed_info = {
                "breed": b.get("breed"),
                "coat": b.get("coat"),
                "pattern": b.get("pattern"),
                "origin": b.get("origin"),
                "coat_match": b.get("coat") == coat,
                "pattern_match": b.get("pattern") == pattern
            }
            bkey = b.get("breed", "").lower()
            if bkey in BREED_CHARACTERISTICS:
                breed_info["characteristics"] = BREED_CHARACTERISTICS[bkey]
            same_country.append(breed_info)
    
    same_coat = []
    for b in breeds:
        if b.get("coat") == coat and b.get("breed") != target_breed.get("breed"):
            breed_info = {
                "breed": b.get("breed"),
                "country": b.get("country"),
                "pattern": b.get("pattern"),
                "origin": b.get("origin"),
                "country_match": b.get("country") == country,
                "pattern_match": b.get("pattern") == pattern
            }
            bkey = b.get("breed", "").lower()
            if bkey in BREED_CHARACTERISTICS:
                breed_info["characteristics"] = BREED_CHARACTERISTICS[bkey]
            same_coat.append(breed_info)
    
    same_pattern = []
    for b in breeds:
        if b.get("pattern") == pattern and b.get("breed") != target_breed.get("breed"):
            breed_info = {
                "breed": b.get("breed"),
                "country": b.get("country"),
                "coat": b.get("coat"),
                "origin": b.get("origin")
            }
            bkey = b.get("breed", "").lower()
            if bkey in BREED_CHARACTERISTICS:
                breed_info["characteristics"] = BREED_CHARACTERISTICS[bkey]
            same_pattern.append(breed_info)
    
    # ENHANCED: Get more facts (25 instead of 15)
    facts_data = _get_facts(25)
    analyzed_facts = [_analyze_fact(f) for f in facts_data]
    
    # ENHANCED: Build comprehensive encyclopedia entry
    entry = {
        "title": target_breed.get("breed"),
        "subtitle": f"A {coat} cat from {country}",
        "taxonomy": {
            "kingdom": "Animalia",
            "phylum": "Chordata",
            "class": "Mammalia",
            "order": "Carnivora",
            "family": "Felidae",
            "genus": "Felis",
            "species": "Felis catus",
            "breed": target_breed.get("breed")
        },
        "overview": characteristics.get("description", f"The {target_breed.get('breed')} is a popular cat breed known for its {coat.lower()} coat."),
        "quick_facts": {
            "origin": country,
            "coat_type": coat,
            "coat_pattern": pattern,
            "temperament": characteristics.get("temperament", "Friendly"),
            "lifespan": characteristics.get("lifespan", "12-15 years"),
            "weight": characteristics.get("weight", "Varies"),
            "activity_level": characteristics.get("activity_level", "Moderate")
        },
        "sections": {
            "origin_and_history": {
                "country_of_origin": country,
                "origin_details": origin,
                "origin_type": "Natural" if origin == "Natural" else ("Hybrid" if "hybrid" in origin.lower() else "Selective breeding"),
                "historical_significance": f"The {target_breed.get('breed')} has been bred in {country} and is known worldwide.",
                "development_history": f"This breed originated through {origin.lower() if origin else 'unknown'} means in {country}.",
                "recognition_status": "Recognized by major cat registries",
                "related_breeds_from_country": same_country,  # ALL related breeds
                "country_breed_count": len(same_country) + 1
            },
            "physical_characteristics": {
                "coat_type": coat,
                "coat_pattern": pattern,
                "coat_description": f"The {target_breed.get('breed')} has a distinctive {coat.lower()} coat with {pattern.lower() if pattern else 'varied'} pattern.",
                "weight_range": characteristics.get("weight", "Varies"),
                "body_type": "Varies by individual",
                "eye_colors": "Varies",
                "grooming_needs": characteristics.get("grooming", "Moderate"),
                "shedding_level": characteristics.get("shedding", "Moderate"),
                "hypoallergenic": False,
                "similar_coat_breeds": same_coat,  # ALL coat-similar breeds
                "similar_pattern_breeds": same_pattern,  # ALL pattern-similar breeds
                "coat_care_guide": {
                    "brushing_frequency": "Daily" if coat == "Long" else ("2-3 times per week" if coat == "Semi-long" else "Weekly"),
                    "bathing_frequency": "Monthly" if coat == "Long" else "As needed",
                    "recommended_tools": ["Slicker brush", "Steel comb", "De-shedding tool"] if coat == "Long" else ["Bristle brush", "Rubber grooming mitt"],
                    "professional_grooming": "Recommended" if coat == "Long" else "Optional",
                    "mat_prevention": "Essential" if coat == "Long" else "Not typically needed"
                }
            },
            "temperament_and_behavior": {
                "temperament": characteristics.get("temperament", "Friendly"),
                "temperament_details": characteristics.get("description", "A wonderful companion cat."),
                "activity_level": characteristics.get("activity_level", "Moderate"),
                "vocalization": "Moderate",
                "intelligence": "High",
                "trainability": "Moderate to high",
                "good_with_children": characteristics.get("good_with_children", True),
                "good_with_other_pets": characteristics.get("good_with_pets", True),
                "good_with_strangers": True,
                "independence": "Moderate",
                "playfulness": characteristics.get("activity_level", "Moderate"),
                "behavioral_traits": [
                    f"Known for being {characteristics.get('temperament', 'friendly').lower()}",
                    f"Activity level: {characteristics.get('activity_level', 'moderate')}",
                    "Adapts well to indoor living"
                ],
                "ideal_environment": {
                    "living_space": "Apartment or house",
                    "outdoor_access": "Indoor preferred, supervised outdoor OK",
                    "family_type": "Singles, couples, families with children",
                    "owner_experience": "Suitable for first-time owners"
                }
            },
            "health_and_care": {
                "lifespan": characteristics.get("lifespan", "12-15 years"),
                "common_health_concerns": characteristics.get("health_concerns", []),
                "genetic_health_issues": characteristics.get("health_concerns", []),
                "recommended_health_tests": [
                    "Annual veterinary checkup",
                    "Dental examination",
                    "Blood work screening"
                ],
                "vaccination_schedule": "Standard feline vaccination protocol",
                "spay_neuter_recommendation": "Recommended by 6 months",
                "care_recommendations": f"Regular grooming is {'essential' if coat == 'Long' else 'recommended'} for this breed.",
                "nutrition_needs": {
                    "diet_type": "High-quality cat food",
                    "feeding_frequency": "2-3 times daily for adults",
                    "special_dietary_needs": "None specific to breed",
                    "weight_management": "Monitor to prevent obesity"
                },
                "exercise_needs": {
                    "daily_play_time": "15-30 minutes",
                    "recommended_activities": ["Interactive toys", "Climbing structures", "Puzzle feeders"],
                    "mental_stimulation": "Important for breed health"
                }
            },
            "fun_facts": {
                "curated_facts": [f["fact"] for f in analyzed_facts],  # ALL facts
                "breed_specific_notes": [
                    f"Originated from {country}",
                    f"Has a distinctive {coat.lower()} coat",
                    f"Pattern: {pattern}",
                    f"Known for being {characteristics.get('temperament', 'friendly').lower()}",
                    f"Typical lifespan: {characteristics.get('lifespan', '12-15 years')}",
                    f"Activity level: {characteristics.get('activity_level', 'moderate')}"
                ],
                "interesting_trivia": [
                    f"The {target_breed.get('breed')} shares its country of origin ({country}) with {len(same_country)} other breeds.",
                    f"There are {len(same_coat)} other breeds with similar {coat.lower()} coats.",
                    f"The {pattern} pattern is found in {len(same_pattern)} other breeds."
                ]
            },
            "breed_comparisons": {
                "similar_breeds": [{
                    "breed": b.get("breed"),
                    "similarity_reason": f"Same coat type ({coat})",
                    "key_difference": f"From {b.get('country')} instead of {country}"
                } for b in same_coat[:10]],
                "commonly_confused_with": [b.get("breed") for b in same_coat[:5]],
                "complementary_breeds": [b.get("breed") for b in same_country[:5]]
            }
        }
    }
    
    # ENHANCED: Comprehensive media suggestions
    media = {
        "suggested_image_categories": [
            f"{target_breed.get('breed')} portrait",
            f"{target_breed.get('breed')} full body",
            f"{target_breed.get('breed')} coat detail",
            f"{target_breed.get('breed')} with family",
            f"{target_breed.get('breed')} kitten",
            f"{target_breed.get('breed')} playing",
            f"{target_breed.get('breed')} grooming",
            f"{target_breed.get('breed')} sleeping"
        ],
        "gallery_layout": {
            "recommended_images": 12,
            "layout_type": "grid",
            "columns": 4,
            "aspect_ratio": "4:3",
            "thumbnail_size": "200x150",
            "lightbox_enabled": True
        },
        "video_suggestions": [
            f"{target_breed.get('breed')} breed overview",
            f"Grooming a {target_breed.get('breed')}",
            f"{target_breed.get('breed')} temperament and behavior",
            f"{target_breed.get('breed')} care guide",
            f"Living with a {target_breed.get('breed')}",
            f"{target_breed.get('breed')} vs similar breeds"
        ],
        "infographic_topics": [
            f"{target_breed.get('breed')} quick facts",
            f"{target_breed.get('breed')} care requirements",
            f"{target_breed.get('breed')} health guide"
        ]
    }
    
    # ENHANCED: Comprehensive cross-references
    cross_references = {
        "related_by_country": [{
            "breed": b.get("breed"),
            "coat": b.get("coat"),
            "pattern": b.get("pattern"),
            "relation": "same country",
            "similarity_score": sum([
                30 if b.get("coat") == coat else 0,
                20 if b.get("pattern") == pattern else 0
            ])
        } for b in same_country],
        "related_by_coat": [{
            "breed": b.get("breed"),
            "country": b.get("country"),
            "pattern": b.get("pattern"),
            "relation": "similar coat",
            "similarity_score": sum([
                30 if b.get("country") == country else 0,
                20 if b.get("pattern") == pattern else 0
            ])
        } for b in same_coat],
        "related_by_pattern": [{
            "breed": b.get("breed"),
            "country": b.get("country"),
            "coat": b.get("coat"),
            "relation": "similar pattern"
        } for b in same_pattern],
        "see_also": [
            "Cat breed classification",
            f"{coat} coat care guide",
            f"Cats from {country}",
            f"{pattern} pattern breeds",
            "Cat health and nutrition",
            "Cat behavior and training"
        ],
        "external_resources": [
            {"name": "Cat Fanciers' Association", "url": "https://cfa.org"},
            {"name": "The International Cat Association", "url": "https://tica.org"},
            {"name": "Cat Breeds Encyclopedia", "url": "https://catbreedsjunction.com"}
        ]
    }
    
    # ENHANCED: Comprehensive database statistics
    # Calculate distributions
    all_coat_types = {}
    all_countries = {}
    all_patterns = {}
    all_origins = {}
    for b in breeds:
        ct = b.get("coat", "Unknown")
        all_coat_types[ct] = all_coat_types.get(ct, 0) + 1
        co = b.get("country", "Unknown")
        all_countries[co] = all_countries.get(co, 0) + 1
        pt = b.get("pattern", "Unknown")
        all_patterns[pt] = all_patterns.get(pt, 0) + 1
        og = b.get("origin", "Unknown")
        all_origins[og] = all_origins.get(og, 0) + 1
    
    db_stats = {
        "total_breeds_in_database": len(breeds),
        "breeds_from_same_country": len(same_country) + 1,
        "breeds_with_same_coat": len(same_coat) + 1,
        "breeds_with_same_pattern": len(same_pattern) + 1,
        "country_breed_percentage": round((len(same_country) + 1) / len(breeds) * 100, 2),
        "coat_breed_percentage": round((len(same_coat) + 1) / len(breeds) * 100, 2),
        "pattern_breed_percentage": round((len(same_pattern) + 1) / len(breeds) * 100, 2),
        "database_distributions": {
            "coat_types": all_coat_types,
            "countries": dict(sorted(all_countries.items(), key=lambda x: -x[1])),
            "patterns": all_patterns,
            "origins": all_origins
        },
        "rankings": {
            "country_rank": sorted(list(all_countries.keys()), key=lambda x: -all_countries[x]).index(country) + 1 if country in all_countries else None,
            "coat_rank": sorted(list(all_coat_types.keys()), key=lambda x: -all_coat_types[x]).index(coat) + 1 if coat in all_coat_types else None
        }
    }
    
    # ENHANCED: All breeds reference
    all_breeds_reference = [{
        "breed": b.get("breed"),
        "country": b.get("country"),
        "coat": b.get("coat"),
        "pattern": b.get("pattern"),
        "origin": b.get("origin"),
        "matches_country": b.get("country") == country,
        "matches_coat": b.get("coat") == coat,
        "matches_pattern": b.get("pattern") == pattern
    } for b in breeds]
    
    return {
        "success": True,
        "breed": target_breed.get("breed"),
        "raw_breed_data": target_breed,
        "encyclopedia_entry": entry,
        "media_suggestions": media,
        "cross_references": cross_references,
        "database_statistics": db_stats,
        "all_breeds_reference": all_breeds_reference,
        "metadata": {
            "entry_version": "2.0",
            "last_updated": "2024-01-15",
            "sources": ["catfact.ninja API", "Breed characteristics database", "General feline knowledge base"],
            "word_count": len(str(entry).split()),
            "section_count": len(entry.get("sections", {})),
            "completeness_score": 95 if characteristics else 70,
            "data_quality": "high" if characteristics else "moderate"
        },
        "api_info": {
            "endpoint": "/breeds, /facts",
            "api_version": "v1",
            "queries_made": 2,
            "breeds_fetched": len(breeds),
            "facts_fetched": len(analyzed_facts)
        }
    }


# ============== Tool Handlers ==============

async def on_get_breed_profile(context: RunContextWrapper, params_str: str) -> Any:
    """Handler for getting breed profile."""
    params = _parse_params(params_str)
    breed_name = params.get("breed_name")
    
    if not breed_name:
        return {"error": "breed_name is required", "success": False}
    
    return _get_breed_profile(breed_name)


async def on_get_breed_relatives(context: RunContextWrapper, params_str: str) -> Any:
    """Handler for getting breed relatives."""
    params = _parse_params(params_str)
    breed_name = params.get("breed_name")
    
    if not breed_name:
        return {"error": "breed_name is required", "success": False}
    
    return _get_breed_relatives(breed_name)


async def on_get_breed_coat_family(context: RunContextWrapper, params_str: str) -> Any:
    """Handler for getting coat family."""
    params = _parse_params(params_str)
    breed_name = params.get("breed_name")
    
    if not breed_name:
        return {"error": "breed_name is required", "success": False}
    
    return _get_breed_coat_family(breed_name)


async def on_get_breed_facts(context: RunContextWrapper, params_str: str) -> Any:
    """Handler for getting breed facts."""
    params = _parse_params(params_str)
    breed_name = params.get("breed_name")
    
    if not breed_name:
        return {"error": "breed_name is required", "success": False}
    
    return _get_breed_facts(breed_name)


async def on_get_breed_encyclopedia(context: RunContextWrapper, params_str: str) -> Any:
    """Handler for getting encyclopedia entry."""
    params = _parse_params(params_str)
    breed_name = params.get("breed_name")
    
    if not breed_name:
        return {"error": "breed_name is required", "success": False}
    
    return _get_breed_encyclopedia(breed_name)


# ============== Tool Definitions ==============

tool_catfacts_breed_profile = FunctionTool(
    name='local-catfacts_breed_profile',
    description='''Get comprehensive profile for a cat breed including characteristics, related breeds, and statistics.

**Input**: breed_name (string) - Cat breed name (e.g., 'Persian', 'Siamese', 'Maine Coon')

**Returns:** dict with breed info, characteristics, related breeds (same country/coat), and database statistics.''',
    params_json_schema={
        "type": "object",
        "properties": {
            "breed_name": {
                "type": "string",
                "description": "Cat breed name (e.g., 'Persian', 'Siamese', 'Maine Coon', 'Ragdoll', 'Bengal')"
            }
        },
        "required": ["breed_name"]
    },
    on_invoke_tool=on_get_breed_profile
)

tool_catfacts_breed_relatives = FunctionTool(
    name='local-catfacts_breed_relatives',
    description='''Get all cat breeds from the same country as the target breed with detailed comparison.

**Input**: breed_name (string) - Cat breed name

**Returns:** dict with all breeds from same country, country statistics, and global comparison.''',
    params_json_schema={
        "type": "object",
        "properties": {
            "breed_name": {
                "type": "string",
                "description": "Cat breed name (e.g., 'Persian', 'Siamese', 'Maine Coon', 'Ragdoll', 'Bengal')"
            }
        },
        "required": ["breed_name"]
    },
    on_invoke_tool=on_get_breed_relatives
)

tool_catfacts_breed_coat_family = FunctionTool(
    name='local-catfacts_breed_coat_family',
    description='''Get all cat breeds with the same coat type as the target breed with similarity analysis.

**Input**: breed_name (string) - Cat breed name

**Returns:** dict with coat family breeds, similarity scores, and global coat analysis.''',
    params_json_schema={
        "type": "object",
        "properties": {
            "breed_name": {
                "type": "string",
                "description": "Cat breed name (e.g., 'Persian', 'Siamese', 'Maine Coon', 'Ragdoll', 'Bengal')"
            }
        },
        "required": ["breed_name"]
    },
    on_invoke_tool=on_get_breed_coat_family
)

tool_catfacts_breed_facts = FunctionTool(
    name='local-catfacts_breed_facts',
    description='''Get curated cat facts collection with detailed analysis for breed context.

**Input**: breed_name (string) - Cat breed name

**Returns:** dict with categorized facts (short/medium/long), statistics, and breed info.''',
    params_json_schema={
        "type": "object",
        "properties": {
            "breed_name": {
                "type": "string",
                "description": "Cat breed name (e.g., 'Persian', 'Siamese', 'Maine Coon', 'Ragdoll', 'Bengal')"
            }
        },
        "required": ["breed_name"]
    },
    on_invoke_tool=on_get_breed_facts
)

tool_catfacts_breed_encyclopedia = FunctionTool(
    name='local-catfacts_breed_encyclopedia',
    description='''Generate comprehensive encyclopedia entry for a cat breed.

**Input**: breed_name (string) - Cat breed name

**Returns:** dict with full encyclopedia entry, media suggestions, cross-references, and metadata.''',
    params_json_schema={
        "type": "object",
        "properties": {
            "breed_name": {
                "type": "string",
                "description": "Cat breed name (e.g., 'Persian', 'Siamese', 'Maine Coon', 'Ragdoll', 'Bengal')"
            }
        },
        "required": ["breed_name"]
    },
    on_invoke_tool=on_get_breed_encyclopedia
)


# Export all tools as a list
catfacts_tools = [
    tool_catfacts_breed_profile,
    tool_catfacts_breed_relatives,
    tool_catfacts_breed_coat_family,
    tool_catfacts_breed_facts,
    tool_catfacts_breed_encyclopedia,
]
