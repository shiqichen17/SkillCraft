"""
University Domains API Tools

Provides tools to query university information by country or name.
Designed for skill mode scenarios with structured education data.

API Documentation: https://github.com/Hipo/university-domains-list
No authentication required.
"""

import json
from typing import Any
from agents.tool import FunctionTool, RunContextWrapper
import requests

# Base URL for University Domains API
UNIVERSITY_BASE_URL = "http://universities.hipolabs.com"


def _make_request(endpoint: str, params: dict = None) -> list:
    """Make a request to University API with error handling."""
    url = f"{UNIVERSITY_BASE_URL}{endpoint}"
    headers = {"User-Agent": "DikaNong-PatternReuse/1.0"}
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        return [{"error": "Request timeout", "success": False}]
    except requests.exceptions.RequestException as e:
        return [{"error": str(e), "success": False}]


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

def _search_universities_by_country(country: str) -> dict:
    """Search for universities in a specific country with ULTRA VERBOSE data for skill mode."""
    data = _make_request("/search", {"country": country})
    
    if isinstance(data, list) and len(data) > 0 and "error" in data[0]:
        return data[0]
    
    # ULTRA VERBOSE: Return ALL universities (no limit)
    universities = []
    domain_types = {"edu": 0, "ac": 0, "gov": 0, "org": 0, "com": 0, "net": 0, "other": 0}
    states_provinces = {}
    domain_extensions = {}
    universities_by_state = {}
    
    for uni in data:  # No limit - return ALL universities
        domains = uni.get("domains", [])
        web_pages = uni.get("web_pages", [])
        state_province = uni.get("state-province") or "Unknown"
        
        # VERBOSE: Analyze each domain in detail
        domain_analysis = []
        for domain in domains:
            # Extract extension
            parts = domain.split(".")
            if len(parts) >= 2:
                ext = "." + ".".join(parts[-2:]) if parts[-1] in ["uk", "au", "jp", "de", "fr", "ca", "nz"] else "." + parts[-1]
                domain_extensions[ext] = domain_extensions.get(ext, 0) + 1
            
            # Categorize domain type
            if ".edu" in domain:
                domain_types["edu"] += 1
                dtype = "educational"
            elif ".ac." in domain:
                domain_types["ac"] += 1
                dtype = "academic"
            elif ".gov" in domain:
                domain_types["gov"] += 1
                dtype = "government"
            elif ".org" in domain:
                domain_types["org"] += 1
                dtype = "organization"
            elif ".com" in domain:
                domain_types["com"] += 1
                dtype = "commercial"
            elif ".net" in domain:
                domain_types["net"] += 1
                dtype = "network"
            else:
                domain_types["other"] += 1
                dtype = "other"
            
            domain_analysis.append({
                "domain": domain,
                "type": dtype,
                "extension": ext if len(parts) >= 2 else "unknown",
                "subdomain_count": len(parts) - 2 if len(parts) > 2 else 0,
                "is_secure_likely": domain.startswith("www.") or not "." in domain.split(".")[0]
            })
        
        # Count by state/province
        states_provinces[state_province] = states_provinces.get(state_province, 0) + 1
        
        # Group universities by state
        if state_province not in universities_by_state:
            universities_by_state[state_province] = []
        universities_by_state[state_province].append(uni.get("name"))
        
        # VERBOSE: Comprehensive university entry
        universities.append({
            "name": uni.get("name"),
            "country": uni.get("country"),
            "alpha_two_code": uni.get("alpha_two_code"),
            "state_province": state_province,
            "domains": domains,
            "domain_count": len(domains),
            "domain_analysis": domain_analysis,
            "primary_domain": domains[0] if domains else None,
            "secondary_domains": domains[1:] if len(domains) > 1 else [],
            "web_pages": web_pages,
            "primary_website": web_pages[0] if web_pages else None,
            "additional_websites": web_pages[1:] if len(web_pages) > 1 else [],
            "website_count": len(web_pages),
            "has_edu_domain": any(".edu" in d for d in domains),
            "has_ac_domain": any(".ac." in d for d in domains),
            "has_gov_domain": any(".gov" in d for d in domains),
            "has_multiple_domains": len(domains) > 1,
            "has_multiple_websites": len(web_pages) > 1,
            "name_length": len(uni.get("name", "")),
            "name_word_count": len(uni.get("name", "").split()),
            "is_college": "college" in uni.get("name", "").lower(),
            "is_university": "university" in uni.get("name", "").lower(),
            "is_institute": "institute" in uni.get("name", "").lower(),
            "is_school": "school" in uni.get("name", "").lower(),
            "is_academy": "academy" in uni.get("name", "").lower()
        })
    
    # ULTRA VERBOSE: Calculate comprehensive statistics
    total_domains = sum(len(u.get("domains", [])) for u in data)
    total_websites = sum(len(u.get("web_pages", [])) for u in data)
    
    # Sort domain extensions by frequency
    sorted_extensions = sorted(domain_extensions.items(), key=lambda x: x[1], reverse=True)
    
    # Calculate institution type distribution
    institution_types = {
        "universities": sum(1 for u in universities if u.get("is_university")),
        "colleges": sum(1 for u in universities if u.get("is_college")),
        "institutes": sum(1 for u in universities if u.get("is_institute")),
        "schools": sum(1 for u in universities if u.get("is_school")),
        "academies": sum(1 for u in universities if u.get("is_academy")),
        "other": sum(1 for u in universities if not any([u.get("is_university"), u.get("is_college"), u.get("is_institute"), u.get("is_school"), u.get("is_academy")]))
    }
    
    return {
        "success": True,
        "country": country,
        "total_universities": len(data),
        "returned_count": len(universities),
        "statistics": {
            "total_domains": total_domains,
            "total_websites": total_websites,
            "avg_domains_per_university": round(total_domains / len(data), 2) if data else 0,
            "avg_websites_per_university": round(total_websites / len(data), 2) if data else 0,
            "domain_type_distribution": domain_types,
            "domain_extension_distribution": dict(sorted_extensions[:20]),  # Top 20 extensions
            "all_domain_extensions": domain_extensions,
            "states_provinces_count": len(states_provinces),
            "states_provinces_distribution": states_provinces,
            "universities_by_state": universities_by_state,
            "institution_type_distribution": institution_types,
            "multi_domain_universities": sum(1 for u in universities if u.get("has_multiple_domains")),
            "multi_website_universities": sum(1 for u in universities if u.get("has_multiple_websites")),
            "edu_domain_count": domain_types["edu"],
            "ac_domain_count": domain_types["ac"]
        },
        "universities": universities
    }


def _search_universities_by_name(name: str) -> dict:
    """Search for universities by name."""
    data = _make_request("/search", {"name": name})
    
    if isinstance(data, list) and len(data) > 0 and "error" in data[0]:
        return data[0]
    
    universities = []
    countries = set()
    
    for uni in data[:15]:  # Limit to 15
        country = uni.get("country", "Unknown")
        countries.add(country)
        universities.append({
            "name": uni.get("name"),
            "country": country,
            "alpha_two_code": uni.get("alpha_two_code"),
            "domains": uni.get("domains", []),
            "web_pages": uni.get("web_pages", [])
        })
    
    return {
        "success": True,
        "query": name,
        "total_results": len(data),
        "returned_count": len(universities),
        "countries_found": list(countries),
        "universities": universities
    }


def _search_universities(country: str = None, name: str = None) -> dict:
    """Search for universities with flexible parameters."""
    params = {}
    if country:
        params["country"] = country
    if name:
        params["name"] = name
    
    if not params:
        return {"error": "At least one of country or name is required", "success": False}
    
    data = _make_request("/search", params)
    
    if isinstance(data, list) and len(data) > 0 and "error" in data[0]:
        return data[0]
    
    universities = []
    countries = set()
    
    for uni in data[:25]:  # Limit to 25
        country_name = uni.get("country", "Unknown")
        countries.add(country_name)
        universities.append({
            "name": uni.get("name"),
            "country": country_name,
            "alpha_two_code": uni.get("alpha_two_code"),
            "state_province": uni.get("state-province"),
            "domains": uni.get("domains", []),
            "web_pages": uni.get("web_pages", [])
        })
    
    return {
        "success": True,
        "query": params,
        "total_results": len(data),
        "returned_count": len(universities),
        "countries_found": list(countries),
        "universities": universities
    }


def _get_university_details(name: str, country: str = None) -> dict:
    """Get detailed information about a specific university."""
    params = {"name": name}
    if country:
        params["country"] = country
    
    data = _make_request("/search", params)
    
    if isinstance(data, list) and len(data) > 0 and "error" in data[0]:
        return data[0]
    
    if not data:
        return {"error": f"University '{name}' not found", "success": False}
    
    # Find best match
    best_match = None
    for uni in data:
        if name.lower() in uni.get("name", "").lower():
            best_match = uni
            break
    
    if not best_match:
        best_match = data[0]
    
    return {
        "success": True,
        "university": {
            "name": best_match.get("name"),
            "country": best_match.get("country"),
            "alpha_two_code": best_match.get("alpha_two_code"),
            "state_province": best_match.get("state-province"),
            "domains": best_match.get("domains", []),
            "web_pages": best_match.get("web_pages", []),
            "primary_domain": best_match.get("domains", [""])[0] if best_match.get("domains") else None,
            "primary_website": best_match.get("web_pages", [""])[0] if best_match.get("web_pages") else None
        },
        "similar_universities": len(data) - 1
    }


def _search_by_domain(domain: str) -> dict:
    """Search university by email domain."""
    # Try to find universities with matching domain
    data = _make_request("/search", {"domain": domain})
    
    if isinstance(data, list) and len(data) > 0 and "error" in data[0]:
        return data[0]
    
    if not data:
        return {"error": f"No university found for domain '{domain}'", "success": False}
    
    universities = []
    countries_found = set()
    
    for uni in data[:10]:
        country = uni.get("country", "Unknown")
        countries_found.add(country)
        universities.append({
            "name": uni.get("name"),
            "country": country,
            "alpha_two_code": uni.get("alpha_two_code"),
            "state_province": uni.get("state-province"),
            "all_domains": uni.get("domains", []),
            "web_pages": uni.get("web_pages", []),
            "match_quality": "exact" if domain in uni.get("domains", []) else "partial"
        })
    
    return {
        "success": True,
        "searched_domain": domain,
        "total_matches": len(data),
        "universities": universities,
        "countries_found": list(countries_found),
        "domain_info": {
            "is_edu": ".edu" in domain,
            "is_ac": ".ac." in domain,
            "tld": domain.split(".")[-1] if "." in domain else None
        }
    }


# ============== Tool Handlers ==============

async def on_search_by_domain(context: RunContextWrapper, params_str: str) -> Any:
    """Handler for searching by domain."""
    params = _parse_params(params_str)
    domain = params.get("domain")
    
    if not domain:
        return {"error": "domain is required", "success": False}
    
    result = _search_by_domain(domain)
    return result


async def on_search_by_country(context: RunContextWrapper, params_str: str) -> Any:
    """Handler for searching by country."""
    params = _parse_params(params_str)
    country = params.get("country")
    
    if not country:
        return {"error": "country is required", "success": False}
    
    result = _search_universities_by_country(country)
    return result


async def on_search_by_name(context: RunContextWrapper, params_str: str) -> Any:
    """Handler for searching by name."""
    params = _parse_params(params_str)
    name = params.get("name")
    
    if not name:
        return {"error": "name is required", "success": False}
    
    result = _search_universities_by_name(name)
    return result


async def on_search_universities(context: RunContextWrapper, params_str: str) -> Any:
    """Handler for flexible search."""
    params = _parse_params(params_str)
    
    result = _search_universities(
        country=params.get("country"),
        name=params.get("name")
    )
    return result


async def on_get_university_details(context: RunContextWrapper, params_str: str) -> Any:
    """Handler for getting university details."""
    params = _parse_params(params_str)
    name = params.get("name")
    country = params.get("country")
    
    if not name:
        return {"error": "name is required", "success": False}
    
    result = _get_university_details(name, country)
    return result


# ============== Tool Definitions ==============

tool_university_by_country = FunctionTool(
    name='local-university_by_country',
    description='''Search for universities in a specific country.

**Returns:** dict:
{
  "success": bool,
  "country": str,
  "total_universities": int,
  "returned_count": int,
  "total_domains": int,
  "universities": [
    {"name": str, "country": str, "alpha_two_code": str, "domains": [str], "web_pages": [str]}
  ]
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "country": {
                "type": "string",
                "description": "Country name (e.g., 'United States', 'United Kingdom', 'Germany')"
            }
        },
        "required": ["country"]
    },
    on_invoke_tool=on_search_by_country
)

tool_university_by_name = FunctionTool(
    name='local-university_by_name',
    description='''Search for universities by name.

**Returns:** dict:
{
  "success": bool,
  "query": str,
  "total_results": int,
  "returned_count": int,
  "countries_found": [str],
  "universities": [{"name": str, "country": str, "alpha_two_code": str, "domains": [str], "web_pages": [str]}]
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "University name or partial name to search"
            }
        },
        "required": ["name"]
    },
    on_invoke_tool=on_search_by_name
)

tool_university_search = FunctionTool(
    name='local-university_search',
    description='''Flexible search for universities by country and/or name.

**Returns:** dict:
{
  "success": bool,
  "query": {"country": str | null, "name": str | null},
  "total_results": int,
  "returned_count": int,
  "countries_found": [str],
  "universities": [{"name": str, "country": str, "alpha_two_code": str, "state_province": str | null, "domains": [str], "web_pages": [str]}]
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "country": {
                "type": "string",
                "description": "Country name (optional)"
            },
            "name": {
                "type": "string",
                "description": "University name or keyword (optional)"
            }
        }
    },
    on_invoke_tool=on_search_universities
)

tool_university_details = FunctionTool(
    name='local-university_details',
    description='''Get detailed information about a specific university.

**Returns:** dict:
{
  "success": bool,
  "university": {
    "name": str,
    "country": str,
    "alpha_two_code": str,
    "state_province": str | null,
    "domains": [str],
    "web_pages": [str],
    "primary_domain": str | null,
    "primary_website": str | null
  },
  "similar_universities": int
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "University name"
            },
            "country": {
                "type": "string",
                "description": "Country to narrow search (optional)"
            }
        },
        "required": ["name"]
    },
    on_invoke_tool=on_get_university_details
)


tool_university_by_domain = FunctionTool(
    name='local-university_by_domain',
    description='''Search for universities by email domain (e.g., "harvard.edu", "ox.ac.uk").

**Returns:** dict:
{
  "success": bool,
  "searched_domain": str,             # The domain searched
  "total_matches": int,               # Total matching universities
  "universities": [                   # Up to 10 matches
    {
      "name": str,                    # University name
      "country": str,                 # Country
      "alpha_two_code": str,          # ISO 2-letter country code
      "state_province": str | null,   # State/province if available
      "all_domains": [str],           # All domains for this university
      "web_pages": [str],             # Official websites
      "match_quality": str            # "exact" or "partial"
    }
  ],
  "countries_found": [str],           # Unique countries in results
  "domain_info": {
    "is_edu": bool,                   # Whether domain contains .edu
    "is_ac": bool,                    # Whether domain contains .ac.
    "tld": str | null                 # Top-level domain
  }
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "domain": {
                "type": "string",
                "description": "Email domain to search (e.g., 'mit.edu', 'cam.ac.uk')"
            }
        },
        "required": ["domain"]
    },
    on_invoke_tool=on_search_by_domain
)


# Export all tools as a list
university_tools = [
    tool_university_by_country,
    tool_university_by_name,
    tool_university_search,
    tool_university_details,
    tool_university_by_domain,
]

