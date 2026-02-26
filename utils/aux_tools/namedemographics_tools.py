"""
Name Demographics API Tools (Genderize, Agify, Nationalize)

Provides tools to analyze names for gender, age, and nationality predictions.
Designed for skill mode scenarios with structured demographic data.

APIs:
- Genderize.io: https://genderize.io
- Agify.io: https://agify.io
- Nationalize.io: https://nationalize.io

No authentication required for basic usage.
"""

import json
from typing import Any
from agents.tool import FunctionTool, RunContextWrapper
import requests


def _make_request(url: str, params: dict = None) -> dict:
    """Make a request with error handling."""
    headers = {"User-Agent": "DikaNong-PatternReuse/1.0"}
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=15)
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


# ============== Tool Implementation Functions ==============

def _get_gender(name: str) -> dict:
    """Predict gender from a name using Genderize.io with VERBOSE similar names analysis."""
    data = _make_request("https://api.genderize.io", {"name": name})
    
    if "error" in data and data.get("success") is False:
        return data
    
    # VERBOSE: Generate similar names with gender predictions
    # Common name prefixes/suffixes for generating similar names
    similar_prefixes = ["", "A", "E", "I", "O", "M", "J", "S", "D", "L", "K", "N", "R", "T", "C"]
    similar_suffixes = ["a", "e", "i", "o", "y", "n", "s", "er", "on", "an", "ie", "ey", "ia", "el", "le"]
    
    similar_names_analysis = []
    base_name = name.lower()
    
    # Generate synthetic similar names based on name patterns
    import random
    random.seed(hash(name) % 10000)  # Deterministic based on name
    
    male_patterns = ["john", "michael", "david", "james", "robert", "william", "richard", "thomas", "charles", "joseph",
                     "daniel", "matthew", "anthony", "mark", "donald", "steven", "paul", "andrew", "joshua", "kevin"]
    female_patterns = ["mary", "patricia", "jennifer", "linda", "elizabeth", "barbara", "susan", "jessica", "sarah", "karen",
                       "nancy", "lisa", "betty", "margaret", "sandra", "ashley", "dorothy", "kimberly", "emily", "donna"]
    neutral_patterns = ["alex", "jordan", "taylor", "morgan", "casey", "riley", "avery", "quinn", "sage", "skyler"]
    
    all_patterns = male_patterns + female_patterns + neutral_patterns
    
    # ULTRA VERBOSE: Generate 100 similar names for skill mode
    for i in range(100):
        if i < len(all_patterns):
            similar_name = all_patterns[i]
        else:
            # Generate variations
            idx = i % len(all_patterns)
            similar_name = all_patterns[idx] + similar_suffixes[i % len(similar_suffixes)]
        
        # Determine gender based on pattern
        if similar_name.lower() in male_patterns or similar_name.lower().startswith(tuple(male_patterns)):
            gender = "male"
            prob = 0.85 + random.random() * 0.14
        elif similar_name.lower() in female_patterns or similar_name.lower().startswith(tuple(female_patterns)):
            gender = "female"
            prob = 0.85 + random.random() * 0.14
        else:
            gender = random.choice(["male", "female"])
            prob = 0.5 + random.random() * 0.3
        
        similar_names_analysis.append({
            "name": similar_name.capitalize(),
            "gender": gender,
            "probability": round(prob, 4),
            "count": random.randint(1000, 500000),
            "confidence": "high" if prob > 0.9 else "medium" if prob > 0.7 else "low",
            "cultural_origin": random.choice(["Western", "European", "Asian", "Latin", "Slavic", "African", "Middle Eastern"]),
            "era_popularity": random.choice(["1950s-1970s", "1970s-1990s", "1990s-2010s", "2010s-present", "Classic", "Modern"]),
            # ULTRA VERBOSE: Additional demographic data
            "birth_year_estimate": random.randint(1940, 2010),
            "generation": random.choice(["Silent Generation", "Baby Boomer", "Gen X", "Millennial", "Gen Z"]),
            "common_middle_names": random.sample(["Marie", "Ann", "Lee", "James", "Michael", "Elizabeth", "Grace", "Rose"], 3),
            "famous_bearers": random.randint(1, 25),
            "social_media_prevalence": round(random.uniform(0.1, 0.9), 3),
            "name_day": f"{random.randint(1,28)}/{random.randint(1,12)}",
            "numerology_number": random.randint(1, 9),
            "meaning_origin": random.choice(["Hebrew", "Greek", "Latin", "Germanic", "Celtic", "Arabic", "Sanskrit", "Japanese"]),
            "meaning_description": f"Derived from {random.choice(['noble', 'brave', 'wise', 'beloved', 'divine', 'strong', 'graceful', 'victorious'])} meaning",
            "popularity_trend_10yr": random.choice(["rising", "falling", "stable", "volatile"]),
            "regional_variants": [f"{similar_name}_{v}" for v in random.sample(["es", "fr", "de", "it", "pt", "ru", "jp"], 3)]
        })
    
    # Calculate aggregate statistics
    male_count = sum(1 for n in similar_names_analysis if n["gender"] == "male")
    female_count = len(similar_names_analysis) - male_count
    avg_probability = sum(n["probability"] for n in similar_names_analysis) / len(similar_names_analysis)
    
    if data.get("gender"):
        return {
            "success": True,
            "name": data.get("name"),
            "gender": data.get("gender"),
            "probability": data.get("probability"),
            "count": data.get("count"),
            "confidence": "high" if data.get("probability", 0) > 0.9 else 
                         "medium" if data.get("probability", 0) > 0.7 else "low",
            # VERBOSE: Similar names analysis for pattern to extract summary from
            "similar_names_analysis": {
                "total_analyzed": len(similar_names_analysis),
                "male_names_count": male_count,
                "female_names_count": female_count,
                "average_probability": round(avg_probability, 4),
                "names": similar_names_analysis
            }
        }
    
    return {
        "success": True,
        "name": name,
        "gender": None,
        "probability": 0,
        "count": 0,
        "confidence": "unknown",
        "similar_names_analysis": {
            "total_analyzed": len(similar_names_analysis),
            "male_names_count": male_count,
            "female_names_count": female_count,
            "average_probability": round(avg_probability, 4),
            "names": similar_names_analysis
        }
    }


def _get_age(name: str) -> dict:
    """Predict age from a name using Agify.io with VERBOSE historical trend and distribution."""
    data = _make_request("https://api.agify.io", {"name": name})
    
    if "error" in data and data.get("success") is False:
        return data
    
    age = data.get("age")
    
    # VERBOSE: Generate historical popularity trend (100 years)
    import random
    random.seed(hash(name) % 10000)
    
    historical_trend = []
    base_popularity = random.randint(50, 200)
    
    for year in range(1920, 2025, 5):
        # Simulate popularity changes over time
        decade = (year - 1920) // 10
        if decade < 3:  # 1920-1949: steady
            pop = base_popularity + random.randint(-20, 20)
        elif decade < 6:  # 1950-1979: peak for classic names
            if age and age > 40:
                pop = base_popularity * 2 + random.randint(-30, 50)
            else:
                pop = base_popularity + random.randint(-10, 30)
        elif decade < 8:  # 1980-1999: decline for classic, rise for modern
            if age and age > 30:
                pop = base_popularity + random.randint(-30, 10)
            else:
                pop = base_popularity * 1.5 + random.randint(-20, 40)
        else:  # 2000-present
            if age and age < 25:
                pop = base_popularity * 2 + random.randint(-20, 60)
            else:
                pop = base_popularity * 0.8 + random.randint(-20, 20)
        
        historical_trend.append({
            "year": year,
            "popularity_index": max(10, int(pop)),
            "rank_estimate": random.randint(1, 500),
            "births_estimate": max(1000, int(pop * 100 + random.randint(-5000, 5000)))
        })
    
    # VERBOSE: Generate age distribution
    age_distribution = []
    for age_bracket in ["0-9", "10-19", "20-29", "30-39", "40-49", "50-59", "60-69", "70-79", "80+"]:
        bracket_start = int(age_bracket.split("-")[0].replace("+", ""))
        
        # Higher percentage for ages close to predicted age
        if age:
            distance = abs(bracket_start + 5 - age)
            pct = max(0.5, 25 - distance * 0.8) + random.random() * 5
        else:
            pct = random.uniform(5, 15)
        
        age_distribution.append({
            "age_bracket": age_bracket,
            "percentage": round(pct, 2),
            "estimated_count": int(pct * 10000),
            "gender_split": {
                "male": round(random.uniform(0.4, 0.6), 3),
                "female": round(random.uniform(0.4, 0.6), 3)
            }
        })
    
    # Normalize percentages
    total_pct = sum(d["percentage"] for d in age_distribution)
    for d in age_distribution:
        d["percentage"] = round(d["percentage"] / total_pct * 100, 2)
        d["estimated_count"] = int(d["percentage"] * 10000)
    
    # VERBOSE: Regional age variations
    regional_ages = []
    regions = ["North America", "Western Europe", "Eastern Europe", "East Asia", 
               "South Asia", "Latin America", "Middle East", "Africa", "Oceania"]
    
    for region in regions:
        base_age = age if age else 35
        variation = random.randint(-15, 15)
        regional_age = max(15, min(80, base_age + variation))
        
        regional_ages.append({
            "region": region,
            "average_age": regional_age,
            "sample_size": random.randint(1000, 100000),
            "age_range": {
                "min": max(0, regional_age - 20),
                "max": min(100, regional_age + 20)
            },
            "popularity_rank": random.randint(1, 200)
        })
    
    if age:
        # Determine age group
        if age < 18:
            age_group = "youth"
        elif age < 30:
            age_group = "young_adult"
        elif age < 50:
            age_group = "adult"
        elif age < 65:
            age_group = "middle_aged"
        else:
            age_group = "senior"
        
        return {
            "success": True,
            "name": data.get("name"),
            "predicted_age": age,
            "age_group": age_group,
            "count": data.get("count"),
            # VERBOSE: Historical and distribution data for pattern to extract summary from
            "historical_trend": {
                "years_covered": "1920-2024",
                "data_points": len(historical_trend),
                "peak_year": max(historical_trend, key=lambda x: x["popularity_index"])["year"],
                "trend_data": historical_trend
            },
            "age_distribution": {
                "total_brackets": len(age_distribution),
                "peak_bracket": max(age_distribution, key=lambda x: x["percentage"])["age_bracket"],
                "distribution": age_distribution
            },
            "regional_variations": {
                "regions_analyzed": len(regional_ages),
                "data": regional_ages
            }
        }
    
    return {
        "success": True,
        "name": name,
        "predicted_age": None,
        "age_group": "unknown",
        "count": 0,
        "historical_trend": {
            "years_covered": "1920-2024",
            "data_points": len(historical_trend),
            "trend_data": historical_trend
        },
        "age_distribution": {
            "total_brackets": len(age_distribution),
            "distribution": age_distribution
        },
        "regional_variations": {
            "regions_analyzed": len(regional_ages),
            "data": regional_ages
        }
    }


def _get_nationality(name: str) -> dict:
    """Predict nationality from a name using Nationalize.io with VERBOSE all-countries data."""
    data = _make_request("https://api.nationalize.io", {"name": name})
    
    if "error" in data and data.get("success") is False:
        return data
    
    countries = data.get("country", [])
    
    # VERBOSE: Comprehensive country code to name mapping with regions
    all_country_data = {
        "US": {"name": "United States", "region": "North America", "continent": "Americas", "population": 331000000},
        "GB": {"name": "United Kingdom", "region": "Western Europe", "continent": "Europe", "population": 67000000},
        "DE": {"name": "Germany", "region": "Western Europe", "continent": "Europe", "population": 83000000},
        "FR": {"name": "France", "region": "Western Europe", "continent": "Europe", "population": 67000000},
        "ES": {"name": "Spain", "region": "Southern Europe", "continent": "Europe", "population": 47000000},
        "IT": {"name": "Italy", "region": "Southern Europe", "continent": "Europe", "population": 60000000},
        "JP": {"name": "Japan", "region": "East Asia", "continent": "Asia", "population": 125000000},
        "CN": {"name": "China", "region": "East Asia", "continent": "Asia", "population": 1400000000},
        "IN": {"name": "India", "region": "South Asia", "continent": "Asia", "population": 1380000000},
        "BR": {"name": "Brazil", "region": "South America", "continent": "Americas", "population": 212000000},
        "RU": {"name": "Russia", "region": "Eastern Europe", "continent": "Europe", "population": 144000000},
        "AU": {"name": "Australia", "region": "Oceania", "continent": "Oceania", "population": 25000000},
        "CA": {"name": "Canada", "region": "North America", "continent": "Americas", "population": 38000000},
        "MX": {"name": "Mexico", "region": "North America", "continent": "Americas", "population": 128000000},
        "KR": {"name": "South Korea", "region": "East Asia", "continent": "Asia", "population": 52000000},
        "NL": {"name": "Netherlands", "region": "Western Europe", "continent": "Europe", "population": 17000000},
        "SE": {"name": "Sweden", "region": "Nordic", "continent": "Europe", "population": 10000000},
        "NO": {"name": "Norway", "region": "Nordic", "continent": "Europe", "population": 5000000},
        "DK": {"name": "Denmark", "region": "Nordic", "continent": "Europe", "population": 6000000},
        "FI": {"name": "Finland", "region": "Nordic", "continent": "Europe", "population": 5500000},
        "PL": {"name": "Poland", "region": "Eastern Europe", "continent": "Europe", "population": 38000000},
        "CZ": {"name": "Czech Republic", "region": "Eastern Europe", "continent": "Europe", "population": 10700000},
        "AT": {"name": "Austria", "region": "Western Europe", "continent": "Europe", "population": 9000000},
        "CH": {"name": "Switzerland", "region": "Western Europe", "continent": "Europe", "population": 8600000},
        "BE": {"name": "Belgium", "region": "Western Europe", "continent": "Europe", "population": 11500000},
        "PT": {"name": "Portugal", "region": "Southern Europe", "continent": "Europe", "population": 10300000},
        "IE": {"name": "Ireland", "region": "Western Europe", "continent": "Europe", "population": 5000000},
        "NZ": {"name": "New Zealand", "region": "Oceania", "continent": "Oceania", "population": 5000000},
        "AR": {"name": "Argentina", "region": "South America", "continent": "Americas", "population": 45000000},
        "CL": {"name": "Chile", "region": "South America", "continent": "Americas", "population": 19000000},
        "CO": {"name": "Colombia", "region": "South America", "continent": "Americas", "population": 50000000},
        "PE": {"name": "Peru", "region": "South America", "continent": "Americas", "population": 33000000},
        "VE": {"name": "Venezuela", "region": "South America", "continent": "Americas", "population": 28000000},
        "TR": {"name": "Turkey", "region": "Middle East", "continent": "Asia", "population": 84000000},
        "SA": {"name": "Saudi Arabia", "region": "Middle East", "continent": "Asia", "population": 35000000},
        "AE": {"name": "United Arab Emirates", "region": "Middle East", "continent": "Asia", "population": 10000000},
        "EG": {"name": "Egypt", "region": "North Africa", "continent": "Africa", "population": 102000000},
        "ZA": {"name": "South Africa", "region": "Southern Africa", "continent": "Africa", "population": 59000000},
        "NG": {"name": "Nigeria", "region": "West Africa", "continent": "Africa", "population": 206000000},
        "KE": {"name": "Kenya", "region": "East Africa", "continent": "Africa", "population": 54000000},
        "ID": {"name": "Indonesia", "region": "Southeast Asia", "continent": "Asia", "population": 273000000},
        "TH": {"name": "Thailand", "region": "Southeast Asia", "continent": "Asia", "population": 70000000},
        "VN": {"name": "Vietnam", "region": "Southeast Asia", "continent": "Asia", "population": 97000000},
        "PH": {"name": "Philippines", "region": "Southeast Asia", "continent": "Asia", "population": 110000000},
        "MY": {"name": "Malaysia", "region": "Southeast Asia", "continent": "Asia", "population": 32000000},
        "SG": {"name": "Singapore", "region": "Southeast Asia", "continent": "Asia", "population": 5800000},
        "PK": {"name": "Pakistan", "region": "South Asia", "continent": "Asia", "population": 220000000},
        "BD": {"name": "Bangladesh", "region": "South Asia", "continent": "Asia", "population": 165000000},
        "UA": {"name": "Ukraine", "region": "Eastern Europe", "continent": "Europe", "population": 44000000},
        "RO": {"name": "Romania", "region": "Eastern Europe", "continent": "Europe", "population": 19000000},
        "GR": {"name": "Greece", "region": "Southern Europe", "continent": "Europe", "population": 10700000},
        "HU": {"name": "Hungary", "region": "Eastern Europe", "continent": "Europe", "population": 9800000},
        "IL": {"name": "Israel", "region": "Middle East", "continent": "Asia", "population": 9200000},
    }
    
    import random
    random.seed(hash(name) % 10000)
    
    # Build comprehensive predictions for ALL countries
    all_predictions = []
    
    # First, add actual API predictions
    remaining_prob = 1.0
    for country in countries:
        code = country.get("country_id", "")
        prob = country.get("probability", 0)
        remaining_prob -= prob
        
        country_info = all_country_data.get(code, {"name": code, "region": "Unknown", "continent": "Unknown", "population": 0})
        all_predictions.append({
            "rank": len(all_predictions) + 1,
            "country_code": code,
            "country_name": country_info["name"],
            "probability": prob,
            "region": country_info["region"],
            "continent": country_info["continent"],
            "population": country_info["population"],
            "estimated_bearers": int(prob * country_info["population"] * 0.001) if country_info["population"] else 0,
            "source": "api"
        })
    
    # Add remaining countries with synthetic probabilities
    existing_codes = {p["country_code"] for p in all_predictions}
    remaining_countries = [(k, v) for k, v in all_country_data.items() if k not in existing_codes]
    random.shuffle(remaining_countries)
    
    for code, info in remaining_countries:
        # Distribute remaining probability
        prob = remaining_prob * random.uniform(0.01, 0.1) if remaining_prob > 0 else random.uniform(0.0001, 0.01)
        remaining_prob = max(0, remaining_prob - prob)
        
        all_predictions.append({
            "rank": len(all_predictions) + 1,
            "country_code": code,
            "country_name": info["name"],
            "probability": round(prob, 6),
            "region": info["region"],
            "continent": info["continent"],
            "population": info["population"],
            "estimated_bearers": int(prob * info["population"] * 0.001) if info["population"] else 0,
            "source": "estimated"
        })
    
    # Sort by probability
    all_predictions.sort(key=lambda x: x["probability"], reverse=True)
    for i, p in enumerate(all_predictions):
        p["rank"] = i + 1
    
    # Calculate regional aggregates
    regional_distribution = {}
    for p in all_predictions:
        region = p["region"]
        if region not in regional_distribution:
            regional_distribution[region] = {"total_probability": 0, "countries": 0, "top_country": None}
        regional_distribution[region]["total_probability"] += p["probability"]
        regional_distribution[region]["countries"] += 1
        if regional_distribution[region]["top_country"] is None:
            regional_distribution[region]["top_country"] = p["country_name"]
    
    regional_summary = [
        {"region": k, "probability": round(v["total_probability"], 4), "countries": v["countries"], "top_country": v["top_country"]}
        for k, v in sorted(regional_distribution.items(), key=lambda x: x[1]["total_probability"], reverse=True)
    ]
    
    top_country = all_predictions[0] if all_predictions else {}
    
    return {
        "success": True,
        "name": data.get("name"),
        "top_nationality": top_country.get("country_name"),
        "top_probability": top_country.get("probability"),
        "count": data.get("count"),
        # VERBOSE: All countries data for pattern to extract summary from
        "global_distribution": {
            "total_countries": len(all_predictions),
            "api_predictions": len(countries),
            "estimated_predictions": len(all_predictions) - len(countries),
            "regional_summary": regional_summary,
            "all_predictions": all_predictions
        }
    }


def _get_full_demographics(name: str) -> dict:
    """Get comprehensive demographics for a name with VERBOSE regional analysis."""
    gender_data = _get_gender(name)
    age_data = _get_age(name)
    nationality_data = _get_nationality(name)
    
    import random
    random.seed(hash(name) % 10000)
    
    # VERBOSE: Generate comprehensive regional analysis
    regions = [
        "North America", "Western Europe", "Eastern Europe", "Nordic",
        "Southern Europe", "East Asia", "South Asia", "Southeast Asia",
        "Middle East", "North Africa", "Sub-Saharan Africa", "Oceania",
        "Central America", "South America", "Caribbean"
    ]
    
    regional_analysis = []
    for region in regions:
        base_age = age_data.get("predicted_age", 35) or 35
        gender = gender_data.get("gender", "unknown")
        
        regional_analysis.append({
            "region": region,
            "gender_distribution": {
                "male": round(0.5 + (0.3 if gender == "male" else -0.3) * random.uniform(0.5, 1), 3),
                "female": round(0.5 + (0.3 if gender == "female" else -0.3) * random.uniform(0.5, 1), 3)
            },
            "average_age": base_age + random.randint(-10, 10),
            "popularity_rank": random.randint(1, 500),
            "estimated_bearers": random.randint(10000, 5000000),
            "trend": random.choice(["increasing", "stable", "decreasing"]),
            "cultural_significance": random.choice(["high", "medium", "low"]),
            "common_variants": [name + suffix for suffix in random.sample(["a", "o", "e", "i", "y", "ie", "ey", "son", "sen"], 3)],
            "peak_popularity_decade": random.choice(["1950s", "1960s", "1970s", "1980s", "1990s", "2000s", "2010s"])
        })
    
    # VERBOSE: Cross-cultural comparison
    cultural_comparison = []
    cultural_groups = ["Anglo-Saxon", "Germanic", "Romance", "Slavic", "East Asian", "South Asian", "Arabic", "African", "Latin American"]
    
    for culture in cultural_groups:
        cultural_comparison.append({
            "cultural_group": culture,
            "prevalence": random.choice(["very common", "common", "moderate", "uncommon", "rare"]),
            "traditional_meaning": f"Derived from {random.choice(['noble', 'brave', 'wise', 'beloved', 'divine', 'strong', 'graceful'])}",
            "gender_association": gender_data.get("gender", "neutral"),
            "typical_age_range": f"{random.randint(20, 40)}-{random.randint(50, 70)}",
            "famous_bearers": random.randint(5, 50),
            "historical_significance": random.choice(["significant", "moderate", "minimal"]),
            "religious_association": random.choice(["Christian", "Jewish", "Islamic", "Buddhist", "Hindu", "None", "Multiple"])
        })
    
    return {
        "success": True,
        "name": name,
        "demographics": {
            "gender": {
                "prediction": gender_data.get("gender"),
                "probability": gender_data.get("probability"),
                "confidence": gender_data.get("confidence"),
                "sample_count": gender_data.get("count")
            },
            "age": {
                "predicted_age": age_data.get("predicted_age"),
                "age_group": age_data.get("age_group"),
                "sample_count": age_data.get("count")
            },
            "nationality": {
                "top_country": nationality_data.get("top_nationality"),
                "probability": nationality_data.get("top_probability"),
                "alternatives": nationality_data.get("global_distribution", {}).get("all_predictions", [])[:5],
                "sample_count": nationality_data.get("count")
            }
        },
        # VERBOSE: Regional and cultural analysis for pattern to extract summary from
        "regional_analysis": {
            "regions_analyzed": len(regional_analysis),
            "data": regional_analysis
        },
        "cultural_comparison": {
            "cultures_analyzed": len(cultural_comparison),
            "data": cultural_comparison
        }
    }


def _get_name_statistics(name: str) -> dict:
    """Get statistical analysis and cultural insights with VERBOSE variant names analysis."""
    gender_data = _get_gender(name)
    age_data = _get_age(name)
    nationality_data = _get_nationality(name)
    
    # Get nationality predictions from the verbose data
    global_dist = nationality_data.get("global_distribution", {})
    nationalities = global_dist.get("all_predictions", [])
    
    # Calculate diversity score based on nationality spread
    diversity_score = 0
    if len(nationalities) >= 3:
        probs = [n.get("probability", 0) for n in nationalities[:3]]
        if probs[0] < 0.5:
            diversity_score = 80
        elif probs[0] < 0.7:
            diversity_score = 60
        else:
            diversity_score = 40
    
    # Determine cultural region
    cultural_regions = {
        "US": "North America", "CA": "North America", "MX": "Latin America",
        "GB": "Western Europe", "DE": "Western Europe", "FR": "Western Europe",
        "ES": "Southern Europe", "IT": "Southern Europe", "PT": "Southern Europe",
        "JP": "East Asia", "CN": "East Asia", "KR": "East Asia",
        "IN": "South Asia", "PK": "South Asia", "BD": "South Asia",
        "BR": "Latin America", "AR": "Latin America", "CL": "Latin America",
        "RU": "Eastern Europe", "PL": "Eastern Europe", "CZ": "Eastern Europe",
        "AU": "Oceania", "NZ": "Oceania",
        "SE": "Nordic", "NO": "Nordic", "DK": "Nordic", "FI": "Nordic",
        "NL": "Western Europe", "BE": "Western Europe", "CH": "Western Europe",
    }
    
    top_country_code = nationalities[0].get("country_code") if nationalities else None
    cultural_region = cultural_regions.get(top_country_code, "Other")
    
    # Popularity indicator based on sample counts
    total_count = (gender_data.get("count", 0) + age_data.get("count", 0)) // 2
    if total_count > 100000:
        popularity = "very_common"
    elif total_count > 50000:
        popularity = "common"
    elif total_count > 10000:
        popularity = "moderate"
    elif total_count > 1000:
        popularity = "uncommon"
    else:
        popularity = "rare"
    
    import random
    random.seed(hash(name) % 10000)
    
    # VERBOSE: Generate comprehensive variant names analysis
    variant_types = ["diminutive", "formal", "cultural", "spelling", "phonetic", "historical", "modern"]
    variant_suffixes = ["a", "e", "i", "o", "y", "ie", "ey", "ina", "ita", "ette", "son", "sen", "ski", "ov", "ez"]
    variant_prefixes = ["", "Mc", "Mac", "O'", "De", "La", "Le", "Van", "Von", "Al-", "Ben-"]
    
    variant_names_analysis = []
    base_gender = gender_data.get("gender", "unknown")
    base_age = age_data.get("predicted_age", 35) or 35
    
    for i in range(40):
        # Generate variant name
        if i < len(variant_suffixes):
            variant = name + variant_suffixes[i]
        elif i < len(variant_suffixes) + len(variant_prefixes):
            prefix = variant_prefixes[i - len(variant_suffixes)]
            variant = prefix + name
        else:
            variant = name[:len(name)-1] + random.choice(variant_suffixes)
        
        variant_gender = base_gender if random.random() > 0.3 else ("female" if base_gender == "male" else "male")
        variant_age = base_age + random.randint(-20, 20)
        
        variant_names_analysis.append({
            "variant_name": variant.capitalize(),
            "variant_type": random.choice(variant_types),
            "relationship_to_base": random.choice(["direct_variant", "diminutive", "formal_version", "cultural_adaptation", "spelling_variant"]),
            "gender_prediction": {
                "gender": variant_gender,
                "probability": round(random.uniform(0.6, 0.99), 4)
            },
            "age_prediction": {
                "predicted_age": max(15, min(80, variant_age)),
                "age_group": "youth" if variant_age < 18 else "young_adult" if variant_age < 30 else "adult" if variant_age < 50 else "middle_aged" if variant_age < 65 else "senior"
            },
            "top_nationality": random.choice([n["country_name"] for n in nationalities[:10]]) if nationalities else "Unknown",
            "popularity": random.choice(["very_common", "common", "moderate", "uncommon", "rare"]),
            "cultural_region": random.choice(list(set(cultural_regions.values()))),
            "sample_count": random.randint(100, 100000),
            "trend": random.choice(["increasing", "stable", "decreasing"]),
            "famous_bearers_count": random.randint(0, 20)
        })
    
    # VERBOSE: Historical popularity data
    historical_popularity = []
    for decade in range(1920, 2030, 10):
        historical_popularity.append({
            "decade": f"{decade}s",
            "rank": random.randint(1, 500),
            "estimated_births": random.randint(10000, 500000),
            "peak_year": decade + random.randint(0, 9),
            "trend": random.choice(["rising", "peak", "declining", "stable"])
        })
    
    # VERBOSE: Linguistic analysis
    linguistic_analysis = {
        "syllable_count": len(name) // 2 + 1,
        "phonetic_complexity": random.choice(["simple", "moderate", "complex"]),
        "pronunciation_variations": random.randint(1, 5),
        "common_misspellings": [name[:len(name)-1] + c for c in random.sample("aeiouynsk", 3)],
        "rhyming_names": [random.choice(["Amy", "Jamie", "Tammy", "Casey", "Tracy"]) for _ in range(5)],
        "initial_letter_popularity": random.choice(["very popular", "popular", "moderate", "uncommon"]),
        "name_length_category": "short" if len(name) < 5 else "medium" if len(name) < 8 else "long",
        "starts_with_vowel": name[0].lower() in "aeiou",
        "ends_with_vowel": name[-1].lower() in "aeiou",
        "contains_double_letters": any(name[i] == name[i+1] for i in range(len(name)-1)) if len(name) > 1 else False
    }
    
    return {
        "success": True,
        "name": name,
        "statistics": {
            "sample_count": total_count,
            "popularity": popularity,
            "cultural_region": cultural_region,
            "diversity_score": diversity_score,
            "gender_certainty": "high" if gender_data.get("probability", 0) > 0.9 else 
                               "medium" if gender_data.get("probability", 0) > 0.7 else "low",
            "age_reliability": "high" if age_data.get("count", 0) > 10000 else
                             "medium" if age_data.get("count", 0) > 1000 else "low"
        },
        "summary": {
            "is_international": diversity_score > 50,
            "primary_region": cultural_region,
            "data_quality": "good" if total_count > 10000 else "moderate" if total_count > 1000 else "limited"
        },
        # VERBOSE: Variant names and historical data for pattern to extract summary from
        "variant_names_analysis": {
            "total_variants_analyzed": len(variant_names_analysis),
            "variants": variant_names_analysis
        },
        "historical_popularity": {
            "decades_covered": len(historical_popularity),
            "data": historical_popularity
        },
        "linguistic_analysis": linguistic_analysis
    }


# ============== Tool Handlers ==============

async def on_get_gender(context: RunContextWrapper, params_str: str) -> Any:
    """Handler for gender prediction."""
    params = _parse_params(params_str)
    name = params.get("name")
    
    if not name:
        return {"error": "name is required", "success": False}
    
    result = _get_gender(name)
    return result


async def on_get_age(context: RunContextWrapper, params_str: str) -> Any:
    """Handler for age prediction."""
    params = _parse_params(params_str)
    name = params.get("name")
    
    if not name:
        return {"error": "name is required", "success": False}
    
    result = _get_age(name)
    return result


async def on_get_nationality(context: RunContextWrapper, params_str: str) -> Any:
    """Handler for nationality prediction."""
    params = _parse_params(params_str)
    name = params.get("name")
    
    if not name:
        return {"error": "name is required", "success": False}
    
    result = _get_nationality(name)
    return result


async def on_get_full_demographics(context: RunContextWrapper, params_str: str) -> Any:
    """Handler for full demographics."""
    params = _parse_params(params_str)
    name = params.get("name")
    
    if not name:
        return {"error": "name is required", "success": False}
    
    result = _get_full_demographics(name)
    return result


async def on_get_name_statistics(context: RunContextWrapper, params_str: str) -> Any:
    """Handler for name statistics."""
    params = _parse_params(params_str)
    name = params.get("name")
    
    if not name:
        return {"error": "name is required", "success": False}
    
    result = _get_name_statistics(name)
    return result


# ============== Tool Definitions ==============

tool_name_gender = FunctionTool(
    name='local-name_gender',
    description='''Predict gender from a first name using Genderize.io.

Returns dict:
{
    "success": bool,              # Whether prediction succeeded
    "name": str,                  # The name analyzed
    "gender": str | None,         # Predicted gender: "male", "female", or None
    "probability": float,         # Confidence (0.0-1.0)
    "count": int,                 # Number of samples in database
    "confidence": str             # "high" (>0.9), "medium" (>0.7), "low", or "unknown"
}

On error: {"error": str, "success": False}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "First name to analyze (e.g., 'John', 'Maria')"
            }
        },
        "required": ["name"]
    },
    on_invoke_tool=on_get_gender
)

tool_name_age = FunctionTool(
    name='local-name_age',
    description='''Predict age from a first name using Agify.io.

Returns dict:
{
    "success": bool,              # Whether prediction succeeded
    "name": str,                  # The name analyzed
    "predicted_age": int | None,  # Predicted age in years
    "age_group": str,             # Category: "youth" (<18), "young_adult" (<30),
                                  # "adult" (<50), "middle_aged" (<65), "senior" (65+), or "unknown"
    "count": int                  # Number of samples in database
}

On error: {"error": str, "success": False}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "First name to analyze (e.g., 'Michael', 'Emma')"
            }
        },
        "required": ["name"]
    },
    on_invoke_tool=on_get_age
)

tool_name_nationality = FunctionTool(
    name='local-name_nationality',
    description='''Predict nationality from a first name using Nationalize.io.

Returns dict:
{
    "success": bool,              # Whether prediction succeeded
    "name": str,                  # The name analyzed
    "top_nationality": str | None,  # Most likely country name (e.g., "Germany")
    "top_probability": float,     # Confidence for top prediction (0.0-1.0)
    "all_predictions": [          # Up to 5 predictions
        {
            "country_code": str,  # ISO 2-letter code (e.g., "DE")
            "country_name": str,  # Full country name (e.g., "Germany")
            "probability": float  # Confidence (0.0-1.0)
        }
    ],
    "count": int                  # Number of samples in database
}

On error: {"error": str, "success": False}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "First name to analyze (e.g., 'Hans', 'Yuki')"
            }
        },
        "required": ["name"]
    },
    on_invoke_tool=on_get_nationality
)

tool_name_demographics = FunctionTool(
    name='local-name_full_demographics',
    description='''Get comprehensive demographics (gender, age, nationality) for a name.

Returns dict:
{
    "success": bool,              # Whether analysis succeeded
    "name": str,                  # The name analyzed
    "demographics": {
        "gender": {
            "prediction": str | None,  # "male", "female", or None
            "probability": float,      # Confidence (0.0-1.0)
            "confidence": str          # "high", "medium", "low", or "unknown"
        },
        "age": {
            "predicted_age": int | None,  # Predicted age in years
            "age_group": str              # Category: "youth", "young_adult", etc.
        },
        "nationality": {
            "top_country": str | None,    # Most likely country name
            "probability": float,         # Confidence for top prediction
            "alternatives": [             # 2nd and 3rd predictions
                {"country_code": str, "country_name": str, "probability": float}
            ]
        }
    }
}

On error: {"error": str, "success": False}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "First name to analyze"
            }
        },
        "required": ["name"]
    },
    on_invoke_tool=on_get_full_demographics
)


tool_name_statistics = FunctionTool(
    name='local-name_statistics',
    description='''Get statistical analysis and cultural insights for a name.

Returns dict:
{
    "success": bool,              # Whether analysis succeeded
    "name": str,                  # The name analyzed
    "statistics": {
        "sample_count": int,      # Total samples in databases
        "popularity": str,        # "very_common", "common", "moderate", "uncommon", or "rare"
        "cultural_region": str,   # Geographic region: "Western Europe", "East Asia", "North America", etc.
        "diversity_score": int,   # How internationally diverse (0-100, higher = more diverse)
        "gender_certainty": str,  # "high", "medium", or "low"
        "age_reliability": str    # "high", "medium", or "low"
    },
    "summary": {
        "is_international": bool,   # True if name is used across multiple regions
        "primary_region": str,      # Main cultural region
        "data_quality": str         # "good", "moderate", or "limited"
    }
}

On error: {"error": str, "success": False}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "First name to analyze for statistics and cultural insights"
            }
        },
        "required": ["name"]
    },
    on_invoke_tool=on_get_name_statistics
)


# Export all tools as a list
namedemographics_tools = [
    tool_name_gender,
    tool_name_age,
    tool_name_nationality,
    tool_name_demographics,
    tool_name_statistics,
]

