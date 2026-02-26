"""
Countries Tools for countries-encyclopedia task
Based on REST Countries API - completely free, no API key required.

REST Countries API Documentation: https://restcountries.com
"""

import json
from typing import Any, Dict, List
from agents.tool import FunctionTool, RunContextWrapper
import requests

# Base URL for REST Countries API
COUNTRIES_URL = "https://restcountries.com/v3.1"


# ============== Regions for Task ==============
# 5 major world regions for country encyclopedia
REGIONS = [
    {"name": "Europe", "subregions": ["Northern Europe", "Western Europe", "Southern Europe", "Eastern Europe"]},
    {"name": "Asia", "subregions": ["Eastern Asia", "South-Eastern Asia", "Southern Asia", "Western Asia", "Central Asia"]},
    {"name": "Africa", "subregions": ["Northern Africa", "Western Africa", "Eastern Africa", "Southern Africa", "Middle Africa"]},
    {"name": "Americas", "subregions": ["Northern America", "South America", "Central America", "Caribbean"]},
    {"name": "Oceania", "subregions": ["Australia and New Zealand", "Melanesia", "Micronesia", "Polynesia"]},
]


# ============== Tool 1: Get Countries by Region ==============

async def on_get_region_countries(context: RunContextWrapper, params_str: str) -> Any:
    """Get all countries in a region."""
    try:
        params = json.loads(params_str) if params_str else {}
    except json.JSONDecodeError:
        return {"success": False, "error": "Invalid JSON parameters"}
    
    region = params.get("region", "")
    
    if not region:
        return {"success": False, "error": "region is required"}
    
    try:
        response = requests.get(
            f"{COUNTRIES_URL}/region/{region.lower()}",
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        
        countries = []
        for country in data:
            # VERBOSE: Extract comprehensive data for each country
            # Native names
            native_names = {}
            for lang_code, native in country.get("name", {}).get("nativeName", {}).items():
                native_names[lang_code] = {
                    "official": native.get("official"),
                    "common": native.get("common")
                }
            
            # Currencies
            currencies = []
            for code, info in country.get("currencies", {}).items():
                currencies.append({
                    "code": code,
                    "name": info.get("name"),
                    "symbol": info.get("symbol")
                })
            
            # Languages
            languages = []
            for code, name in country.get("languages", {}).items():
                languages.append({"code": code, "name": name})
            
            # Demonyms
            demonyms = {}
            for lang, dem in country.get("demonyms", {}).items():
                demonyms[lang] = {"female": dem.get("f"), "male": dem.get("m")}
            
            # Translations (all available)
            translations = country.get("translations", {})
            
            countries.append({
                "name": country.get("name", {}).get("common"),
                "official_name": country.get("name", {}).get("official"),
                "native_names": native_names,
                "cca2": country.get("cca2"),
                "cca3": country.get("cca3"),
                "ccn3": country.get("ccn3"),
                "cioc": country.get("cioc"),
                "fifa": country.get("fifa"),
                "capital": country.get("capital", []),
                "capital_latlng": country.get("capitalInfo", {}).get("latlng", []),
                "population": country.get("population"),
                "area": country.get("area"),
                "population_density": round(country.get("population", 0) / country.get("area", 1), 2) if country.get("area") else None,
                "subregion": country.get("subregion"),
                "continents": country.get("continents", []),
                "latlng": country.get("latlng", []),
                "landlocked": country.get("landlocked"),
                "borders": country.get("borders", []),
                "border_count": len(country.get("borders", [])),
                "currencies": currencies,
                "languages": languages,
                "timezones": country.get("timezones", []),
                "start_of_week": country.get("startOfWeek"),
                "car": country.get("car", {}),
                "dial_codes": country.get("idd", {}).get("suffixes", []),
                "tld": country.get("tld", []),
                "flag_emoji": country.get("flag"),
                "flags": country.get("flags", {}),
                "coat_of_arms": country.get("coatOfArms", {}),
                "maps": country.get("maps", {}),
                "gini": country.get("gini"),
                "independent": country.get("independent"),
                "un_member": country.get("unMember"),
                "status": country.get("status"),
                "demonyms": demonyms,
                "translations": translations
            })
        
        # Sort by population (largest first)
        countries.sort(key=lambda x: x.get("population", 0) or 0, reverse=True)
        
        # Calculate summary
        total_population = sum(c.get("population", 0) or 0 for c in countries)
        total_area = sum(c.get("area", 0) or 0 for c in countries)
        subregions = list(set(c.get("subregion") for c in countries if c.get("subregion")))
        
        return {
            "success": True,
            "region": region,
            "summary": {
                "country_count": len(countries),
                "total_population": total_population,
                "total_area_km2": total_area,
                "subregions": subregions,
                "subregion_count": len(subregions),
                "un_members": sum(1 for c in countries if c.get("un_member")),
                "independent_countries": sum(1 for c in countries if c.get("independent"))
            },
            "countries": countries
        }
        
    except requests.RequestException as e:
        return {"success": False, "error": f"API error: {str(e)}"}


tool_get_region_countries = FunctionTool(
    name='local-countries_get_region',
    description='''Get all countries in a region (Europe, Asia, Africa, Americas, Oceania) with basic info.

**Input:** region (str) - Region name (e.g., 'Europe', 'Asia', 'Africa', 'Americas', 'Oceania')

**Returns:** dict:
{
  "success": bool,
  "region": str,
  "summary": {
    "country_count": int,
    "total_population": int,
    "total_area_km2": float,
    "subregions": [str],
    "subregion_count": int,
    "un_members": int,
    "independent_countries": int
  },
  "countries": [
    {
      "name": str,
      "official_name": str,
      "cca2": str,
      "cca3": str,
      "capital": str | null,
      "population": int,
      "area": float,
      "subregion": str,
      "flag_emoji": str,
      "independent": bool,
      "un_member": bool
    }
  ]
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "region": {"type": "string", "description": "Region name (e.g., 'Europe', 'Asia', 'Africa', 'Americas', 'Oceania')"},
        },
        "required": ["region"]
    },
    on_invoke_tool=on_get_region_countries
)


# ============== Tool 2: Get Country Details ==============

async def on_get_country_details(context: RunContextWrapper, params_str: str) -> Any:
    """Get detailed information about a specific country."""
    try:
        params = json.loads(params_str) if params_str else {}
    except json.JSONDecodeError:
        return {"success": False, "error": "Invalid JSON parameters"}
    
    country_name = params.get("country_name") or params.get("country_code")
    
    if not country_name:
        return {"success": False, "error": "country_name or country_code is required"}
    
    try:
        data = None
        
        # Check if input looks like an ISO code (2-3 uppercase letters)
        is_code = len(country_name) <= 3 and country_name.isalpha() and country_name.isupper()
        
        if is_code:
            # Try alpha code endpoint first for ISO codes
            response = requests.get(
                f"{COUNTRIES_URL}/alpha/{country_name}",
                timeout=30
            )
            if response.status_code == 200:
                result = response.json()
                # API returns list for alpha endpoint
                data = result if isinstance(result, list) else [result]
        
        if not data:
            # Try exact name match
            response = requests.get(
                f"{COUNTRIES_URL}/name/{country_name}?fullText=true",
                timeout=30
            )
            
            if response.status_code == 404:
                # Try partial match
                response = requests.get(
                    f"{COUNTRIES_URL}/name/{country_name}",
                    timeout=30
                )
            
            if response.status_code == 200:
                data = response.json()
        
        if not data:
            return {"success": False, "error": f"Country '{country_name}' not found. Use full country name or ISO alpha-2/alpha-3 code."}
        
        country = data[0]
        
        # Extract currencies
        currencies = []
        for code, info in country.get("currencies", {}).items():
            currencies.append({
                "code": code,
                "name": info.get("name"),
                "symbol": info.get("symbol")
            })
        
        # Extract languages
        languages = []
        for code, name in country.get("languages", {}).items():
            languages.append({
                "code": code,
                "name": name
            })
        
        # Get car info (simplified)
        car = country.get("car", {})
        
        # VERBOSE: Return comprehensive data for skill mode
        # Get native names
        native_names = {}
        for lang_code, native in country.get("name", {}).get("nativeName", {}).items():
            native_names[lang_code] = {
                "official": native.get("official"),
                "common": native.get("common")
            }
        
        # Get demonyms
        demonyms = {}
        for lang, dem in country.get("demonyms", {}).items():
            demonyms[lang] = {
                "female": dem.get("f"),
                "male": dem.get("m")
            }
        
        # Get translations (top 10 languages)
        translations = {}
        trans_data = country.get("translations", {})
        for lang in list(trans_data.keys())[:10]:
            translations[lang] = trans_data[lang]
        
        # VERBOSE: Full geographic data
        latlng = country.get("latlng", [])
        capital_latlng = country.get("capitalInfo", {}).get("latlng", [])
        
        return {
            "success": True,
            "country": {
                "name": {
                    "common": country.get("name", {}).get("common"),
                    "official": country.get("name", {}).get("official"),
                    "native": native_names
                },
                "codes": {
                    "cca2": country.get("cca2"),
                    "cca3": country.get("cca3"),
                    "ccn3": country.get("ccn3"),
                    "cioc": country.get("cioc"),
                    "fifa": country.get("fifa")
                },
                "capital": country.get("capital", []),
                "capital_latlng": capital_latlng,
                "region": country.get("region"),
                "subregion": country.get("subregion"),
                "continents": country.get("continents", []),
                "latlng": latlng,
                "landlocked": country.get("landlocked"),
                "borders": country.get("borders", []),
                "area": country.get("area"),
                "population": country.get("population"),
                "population_density": round(country.get("population", 0) / country.get("area", 1), 2) if country.get("area") else None,
                "gini": country.get("gini"),
                "currencies": currencies,
                "languages": languages,
                "timezones": country.get("timezones", []),
                "start_of_week": country.get("startOfWeek"),
                "car": {
                    "signs": car.get("signs", []),
                    "side": car.get("side")
                },
                "dial_codes": country.get("idd", {}).get("suffixes", []),
                "tld": country.get("tld", []),
                "independent": country.get("independent"),
                "un_member": country.get("unMember"),
                "status": country.get("status"),
                "flag_emoji": country.get("flag"),
                "flags": {
                    "png": country.get("flags", {}).get("png"),
                    "svg": country.get("flags", {}).get("svg"),
                    "alt": country.get("flags", {}).get("alt")
                },
                "coat_of_arms": {
                    "png": country.get("coatOfArms", {}).get("png"),
                    "svg": country.get("coatOfArms", {}).get("svg")
                },
                "maps": {
                    "googleMaps": country.get("maps", {}).get("googleMaps"),
                    "openStreetMaps": country.get("maps", {}).get("openStreetMaps")
                },
                "demonyms": demonyms,
                "translations": translations
            }
        }
        
    except requests.RequestException as e:
        return {"success": False, "error": f"API error: {str(e)}"}


tool_get_country_details = FunctionTool(
    name='local-countries_get_details',
    description='''Get comprehensive details about a specific country including currencies, languages, borders, and more.

**Input:** country_name (str) - Country name (e.g., 'Germany', 'Japan') or ISO alpha-2/alpha-3 code (e.g., 'DE', 'JP', 'GBR', 'CHN')

**Returns:** dict:
{
  "success": bool,
  "country": {
    "name": {"common": str, "official": str, "native": dict},
    "codes": {"cca2": str, "cca3": str, "ccn3": str, "cioc": str, "fifa": str},
    "capital": [str],
    "capital_latlng": [float, float],
    "region": str,
    "subregion": str,
    "continents": [str],
    "latlng": [float, float],
    "landlocked": bool,
    "borders": [str],
    "area": float,
    "population": int,
    "population_density": float,
    "gini": dict | null,
    "currencies": [{"code": str, "name": str, "symbol": str}],
    "languages": [{"code": str, "name": str}],
    "timezones": [str],
    "start_of_week": str,
    "car": {"signs": [str], "side": str},
    "dial_codes": [str],
    "tld": [str],
    "independent": bool,
    "un_member": bool,
    "status": str,
    "flag_emoji": str,
    "flags": {"png": str, "svg": str},
    "coat_of_arms": {"png": str, "svg": str},
    "maps": {"googleMaps": str, "openStreetMaps": str},
    "demonyms": {"eng": {"female": str, "male": str}},
    "translations_count": int,
    "translations": dict
  }
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "country_name": {"type": "string", "description": "Country name (e.g., 'Germany', 'Japan') or country code (e.g., 'DE', 'JP')"},
        },
        "required": ["country_name"]
    },
    on_invoke_tool=on_get_country_details
)


# ============== Tool 3: Get Border Countries ==============

async def on_get_borders(context: RunContextWrapper, params_str: str) -> Any:
    """Get detailed information about a country's neighbors."""
    try:
        params = json.loads(params_str) if params_str else {}
    except json.JSONDecodeError:
        return {"success": False, "error": "Invalid JSON parameters"}
    
    country_codes = params.get("country_codes", [])
    
    if not country_codes:
        return {"success": False, "error": "country_codes list is required"}
    
    if isinstance(country_codes, str):
        country_codes = [country_codes]
    
    try:
        codes_str = ",".join(country_codes)
        response = requests.get(
            f"{COUNTRIES_URL}/alpha?codes={codes_str}",
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        
        neighbors = []
        for country in data:
            # VERBOSE: Extract comprehensive data for neighbor countries
            # Native names
            native_names = {}
            for lang_code, native in country.get("name", {}).get("nativeName", {}).items():
                native_names[lang_code] = {
                    "official": native.get("official"),
                    "common": native.get("common")
                }
            
            # Currencies with full details
            currencies = []
            for code, info in country.get("currencies", {}).items():
                currencies.append({
                    "code": code,
                    "name": info.get("name"),
                    "symbol": info.get("symbol")
                })
            
            # Languages with codes
            languages = []
            for code, name in country.get("languages", {}).items():
                languages.append({"code": code, "name": name})
            
            # Demonyms
            demonyms = {}
            for lang, dem in country.get("demonyms", {}).items():
                demonyms[lang] = {"female": dem.get("f"), "male": dem.get("m")}
            
            # Translations
            translations = country.get("translations", {})
            
            neighbors.append({
                "name": country.get("name", {}).get("common"),
                "official_name": country.get("name", {}).get("official"),
                "native_names": native_names,
                "cca2": country.get("cca2"),
                "cca3": country.get("cca3"),
                "ccn3": country.get("ccn3"),
                "cioc": country.get("cioc"),
                "fifa": country.get("fifa"),
                "capital": country.get("capital", []),
                "capital_latlng": country.get("capitalInfo", {}).get("latlng", []),
                "population": country.get("population"),
                "area": country.get("area"),
                "population_density": round(country.get("population", 0) / country.get("area", 1), 2) if country.get("area") else None,
                "region": country.get("region"),
                "subregion": country.get("subregion"),
                "continents": country.get("continents", []),
                "latlng": country.get("latlng", []),
                "landlocked": country.get("landlocked"),
                "borders": country.get("borders", []),
                "languages": languages,
                "currencies": currencies,
                "timezones": country.get("timezones", []),
                "start_of_week": country.get("startOfWeek"),
                "car": country.get("car", {}),
                "dial_codes": country.get("idd", {}).get("suffixes", []),
                "tld": country.get("tld", []),
                "flag_emoji": country.get("flag"),
                "flags": country.get("flags", {}),
                "coat_of_arms": country.get("coatOfArms", {}),
                "maps": country.get("maps", {}),
                "gini": country.get("gini"),
                "independent": country.get("independent"),
                "un_member": country.get("unMember"),
                "demonyms": demonyms,
                "translations": translations
            })
        
        return {
            "success": True,
            "requested_codes": country_codes,
            "found_count": len(neighbors),
            "total_population": sum(n.get("population", 0) or 0 for n in neighbors),
            "total_area_km2": sum(n.get("area", 0) or 0 for n in neighbors),
            "neighbors": neighbors
        }
        
    except requests.RequestException as e:
        return {"success": False, "error": f"API error: {str(e)}"}


tool_get_borders = FunctionTool(
    name='local-countries_get_borders',
    description='''Get detailed information about neighboring countries using their country codes.

**Input:** country_codes (list[str]) - List of 3-letter country codes (e.g., ['DEU', 'FRA', 'POL'])

**Returns:** dict:
{
  "success": bool,
  "requested_codes": [str],
  "found_count": int,
  "total_population": int,
  "total_area_km2": float,
  "neighbors": [
    {
      "name": str,
      "official_name": str,
      "cca3": str,
      "capital": str | null,
      "population": int,
      "area": float,
      "region": str,
      "subregion": str,
      "languages": [str],
      "currencies": [str],
      "flag_emoji": str
    }
  ]
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "country_codes": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of 3-letter country codes (e.g., ['DEU', 'FRA', 'POL'])"
            },
        },
        "required": ["country_codes"]
    },
    on_invoke_tool=on_get_borders
)


# ============== Tool 4: Get Countries by Currency ==============

async def on_get_by_currency(context: RunContextWrapper, params_str: str) -> Any:
    """Get all countries using a specific currency."""
    try:
        params = json.loads(params_str) if params_str else {}
    except json.JSONDecodeError:
        return {"success": False, "error": "Invalid JSON parameters"}
    
    currency = params.get("currency", "")
    
    if not currency:
        return {"success": False, "error": "currency is required"}
    
    try:
        response = requests.get(
            f"{COUNTRIES_URL}/currency/{currency.lower()}",
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        
        countries = []
        for country in data:
            # VERBOSE: Get comprehensive country data
            currency_info = country.get("currencies", {}).get(currency.upper(), {})
            
            # Native names
            native_names = {}
            for lang_code, native in country.get("name", {}).get("nativeName", {}).items():
                native_names[lang_code] = {
                    "official": native.get("official"),
                    "common": native.get("common")
                }
            
            # All currencies
            all_currencies = []
            for code, info in country.get("currencies", {}).items():
                all_currencies.append({
                    "code": code,
                    "name": info.get("name"),
                    "symbol": info.get("symbol")
                })
            
            # Languages
            languages = []
            for code, name in country.get("languages", {}).items():
                languages.append({"code": code, "name": name})
            
            # Demonyms
            demonyms = {}
            for lang, dem in country.get("demonyms", {}).items():
                demonyms[lang] = {"female": dem.get("f"), "male": dem.get("m")}
            
            # Translations
            translations = country.get("translations", {})
            
            countries.append({
                "name": country.get("name", {}).get("common"),
                "official_name": country.get("name", {}).get("official"),
                "native_names": native_names,
                "cca2": country.get("cca2"),
                "cca3": country.get("cca3"),
                "ccn3": country.get("ccn3"),
                "capital": country.get("capital", []),
                "capital_latlng": country.get("capitalInfo", {}).get("latlng", []),
                "population": country.get("population"),
                "area": country.get("area"),
                "population_density": round(country.get("population", 0) / country.get("area", 1), 2) if country.get("area") else None,
                "region": country.get("region"),
                "subregion": country.get("subregion"),
                "continents": country.get("continents", []),
                "latlng": country.get("latlng", []),
                "landlocked": country.get("landlocked"),
                "borders": country.get("borders", []),
                "currency_name": currency_info.get("name"),
                "currency_symbol": currency_info.get("symbol"),
                "all_currencies": all_currencies,
                "languages": languages,
                "timezones": country.get("timezones", []),
                "flag_emoji": country.get("flag"),
                "flags": country.get("flags", {}),
                "coat_of_arms": country.get("coatOfArms", {}),
                "maps": country.get("maps", {}),
                "independent": country.get("independent"),
                "un_member": country.get("unMember"),
                "demonyms": demonyms,
                "translations": translations
            })
        
        # Sort by population
        countries.sort(key=lambda x: x.get("population", 0) or 0, reverse=True)
        
        return {
            "success": True,
            "currency_code": currency.upper(),
            "country_count": len(countries),
            "total_population": sum(c.get("population", 0) or 0 for c in countries),
            "regions": list(set(c.get("region") for c in countries if c.get("region"))),
            "countries": countries
        }
        
    except requests.RequestException as e:
        return {"success": False, "error": f"API error: {str(e)}"}


tool_get_by_currency = FunctionTool(
    name='local-countries_get_by_currency',
    description='''Get all countries that use a specific currency (e.g., EUR, USD, GBP).

**Input:** currency (str) - Currency code (e.g., 'EUR', 'USD', 'GBP')

**Returns:** dict:
{
  "success": bool,
  "currency_code": str,
  "country_count": int,
  "total_population": int,
  "regions": [str],
  "countries": [
    {
      "name": str,
      "official_name": str,
      "cca3": str,
      "capital": str | null,
      "population": int,
      "region": str,
      "subregion": str,
      "currency_name": str,
      "currency_symbol": str,
      "flag_emoji": str
    }
  ]
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "currency": {"type": "string", "description": "Currency code (e.g., 'EUR', 'USD', 'GBP')"},
        },
        "required": ["currency"]
    },
    on_invoke_tool=on_get_by_currency
)


# ============== Tool 5: Get Countries by Language ==============

async def on_get_by_language(context: RunContextWrapper, params_str: str) -> Any:
    """Get all countries where a specific language is spoken."""
    try:
        params = json.loads(params_str) if params_str else {}
    except json.JSONDecodeError:
        return {"success": False, "error": "Invalid JSON parameters"}
    
    language = params.get("language", "")
    
    if not language:
        return {"success": False, "error": "language is required"}
    
    try:
        response = requests.get(
            f"{COUNTRIES_URL}/lang/{language.lower()}",
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        
        countries = []
        for country in data:
            # VERBOSE: Get comprehensive country data
            # Native names
            native_names = {}
            for lang_code, native in country.get("name", {}).get("nativeName", {}).items():
                native_names[lang_code] = {
                    "official": native.get("official"),
                    "common": native.get("common")
                }
            
            # Currencies
            currencies = []
            for code, info in country.get("currencies", {}).items():
                currencies.append({
                    "code": code,
                    "name": info.get("name"),
                    "symbol": info.get("symbol")
                })
            
            # All languages with codes
            languages = []
            for code, name in country.get("languages", {}).items():
                languages.append({"code": code, "name": name})
            
            # Demonyms
            demonyms = {}
            for lang, dem in country.get("demonyms", {}).items():
                demonyms[lang] = {"female": dem.get("f"), "male": dem.get("m")}
            
            # Translations
            translations = country.get("translations", {})
            
            countries.append({
                "name": country.get("name", {}).get("common"),
                "official_name": country.get("name", {}).get("official"),
                "native_names": native_names,
                "cca2": country.get("cca2"),
                "cca3": country.get("cca3"),
                "ccn3": country.get("ccn3"),
                "capital": country.get("capital", []),
                "capital_latlng": country.get("capitalInfo", {}).get("latlng", []),
                "population": country.get("population"),
                "area": country.get("area"),
                "population_density": round(country.get("population", 0) / country.get("area", 1), 2) if country.get("area") else None,
                "region": country.get("region"),
                "subregion": country.get("subregion"),
                "continents": country.get("continents", []),
                "latlng": country.get("latlng", []),
                "landlocked": country.get("landlocked"),
                "borders": country.get("borders", []),
                "all_languages": languages,
                "currencies": currencies,
                "timezones": country.get("timezones", []),
                "flag_emoji": country.get("flag"),
                "flags": country.get("flags", {}),
                "coat_of_arms": country.get("coatOfArms", {}),
                "maps": country.get("maps", {}),
                "independent": country.get("independent"),
                "un_member": country.get("unMember"),
                "demonyms": demonyms,
                "translations": translations
            })
        
        # Sort by population
        countries.sort(key=lambda x: x.get("population", 0) or 0, reverse=True)
        
        return {
            "success": True,
            "language": language,
            "country_count": len(countries),
            "total_population": sum(c.get("population", 0) or 0 for c in countries),
            "total_area_km2": sum(c.get("area", 0) or 0 for c in countries),
            "regions": list(set(c.get("region") for c in countries if c.get("region"))),
            "countries": countries
        }
        
    except requests.RequestException as e:
        return {"success": False, "error": f"API error: {str(e)}"}


tool_get_by_language = FunctionTool(
    name='local-countries_get_by_language',
    description='''Get all countries where a specific language is spoken (e.g., english, spanish, french).

**Input:** language (str) - Language name (e.g., 'english', 'spanish', 'french', 'arabic')

**Returns:** dict:
{
  "success": bool,
  "language": str,
  "country_count": int,
  "total_population": int,
  "total_area_km2": float,
  "regions": [str],
  "countries": [
    {
      "name": str,
      "official_name": str,
      "cca3": str,
      "capital": str | null,
      "population": int,
      "area": float,
      "region": str,
      "subregion": str,
      "all_languages": [str],
      "flag_emoji": str
    }
  ]
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "language": {"type": "string", "description": "Language name (e.g., 'english', 'spanish', 'french', 'arabic')"},
        },
        "required": ["language"]
    },
    on_invoke_tool=on_get_by_language
)


# ============== Export all tools ==============

countries_tools = [
    tool_get_region_countries,  # Step 1: Get countries in a region
    tool_get_country_details,   # Step 2: Get detailed country info
    tool_get_borders,           # Step 3: Get border country details
    tool_get_by_currency,       # Step 4: Get countries by currency
    tool_get_by_language,       # Step 5: Get countries by language
]

