"""
World Bank API Tools

Provides tools to query economic indicators and country data from World Bank.
Designed for skill mode scenarios with structured economic data.

API Documentation: https://datahelpdesk.worldbank.org/knowledgebase/topics/125589
No authentication required.
"""

import json
from typing import Any
from agents.tool import FunctionTool, RunContextWrapper
import requests

# Base URL for World Bank API
WORLDBANK_BASE_URL = "https://api.worldbank.org/v2"


def _make_request(endpoint: str, params: dict = None) -> list:
    """Make a request to World Bank API with error handling."""
    url = f"{WORLDBANK_BASE_URL}{endpoint}"
    if params is None:
        params = {}
    params["format"] = "json"
    params["per_page"] = 100
    
    headers = {"User-Agent": "DikaNong-PatternReuse/1.0"}
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        # World Bank returns [metadata, data] format
        if isinstance(data, list) and len(data) >= 2:
            return data[1] if data[1] else []
        return data
    except requests.exceptions.Timeout:
        return [{"error": "Request timeout", "success": False}]
    except requests.exceptions.RequestException as e:
        return [{"error": str(e), "success": False}]
    except json.JSONDecodeError:
        return [{"error": "Invalid JSON response", "success": False}]


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

def _get_country_info(country_code: str) -> dict:
    """Get information about a country."""
    data = _make_request(f"/country/{country_code}")
    
    if isinstance(data, list) and len(data) > 0:
        if "error" in data[0]:
            return data[0]
        
        country = data[0]
        return {
            "success": True,
            "country": {
                "id": country.get("id"),
                "name": country.get("name"),
                "iso2Code": country.get("iso2Code"),
                "region": country.get("region", {}).get("value"),
                "income_level": country.get("incomeLevel", {}).get("value"),
                "lending_type": country.get("lendingType", {}).get("value"),
                "capital_city": country.get("capitalCity"),
                "longitude": country.get("longitude"),
                "latitude": country.get("latitude")
            }
        }
    
    return {"error": f"Country '{country_code}' not found", "success": False}


def _get_indicator(country_code: str, indicator: str, year_start: int = 2018, year_end: int = 2022) -> dict:
    """Get economic indicator for a country."""
    endpoint = f"/country/{country_code}/indicator/{indicator}"
    params = {"date": f"{year_start}:{year_end}"}
    
    data = _make_request(endpoint, params)
    
    if isinstance(data, list) and len(data) > 0:
        if "error" in data[0]:
            return data[0]
        
        values = []
        for item in data:
            if item.get("value") is not None:
                values.append({
                    "year": item.get("date"),
                    "value": item.get("value"),
                    "indicator": item.get("indicator", {}).get("value")
                })
        
        # Sort by year
        values.sort(key=lambda x: x.get("year", "0"), reverse=True)
        
        return {
            "success": True,
            "country_code": country_code,
            "indicator": indicator,
            "data_points": len(values),
            "values": values,
            "latest_value": values[0] if values else None
        }
    
    return {"error": f"No data for indicator '{indicator}'", "success": False}


def _get_gdp(country_code: str) -> dict:
    """Get GDP data for a country."""
    return _get_indicator(country_code, "NY.GDP.MKTP.CD")  # GDP (current US$)


def _get_population(country_code: str) -> dict:
    """Get population data for a country."""
    return _get_indicator(country_code, "SP.POP.TOTL")  # Population, total


def _get_population_detailed(country_code: str) -> dict:
    """Get detailed population data including demographics."""
    pop_total = _get_indicator(country_code, "SP.POP.TOTL", 2015, 2022)
    pop_growth = _get_indicator(country_code, "SP.POP.GROW", 2015, 2022)
    urban_pop = _get_indicator(country_code, "SP.URB.TOTL.IN.ZS", 2015, 2022)
    life_exp = _get_indicator(country_code, "SP.DYN.LE00.IN", 2015, 2022)
    
    if not pop_total.get("success"):
        return {"error": f"No population data for '{country_code}'", "success": False}
    
    # Calculate growth rate
    values = pop_total.get("values", [])
    latest_pop = values[0].get("value") if values else None
    oldest_pop = values[-1].get("value") if values else None
    
    pop_change = None
    if latest_pop and oldest_pop and oldest_pop > 0:
        pop_change = ((latest_pop - oldest_pop) / oldest_pop) * 100
    
    return {
        "success": True,
        "country_code": country_code,
        "population": {
            "latest": pop_total.get("latest_value"),
            "historical": values[:5],
            "data_years": len(values)
        },
        "demographics": {
            "growth_rate": pop_growth.get("latest_value") if pop_growth.get("success") else None,
            "urban_percent": urban_pop.get("latest_value") if urban_pop.get("success") else None,
            "life_expectancy": life_exp.get("latest_value") if life_exp.get("success") else None
        },
        "trends": {
            "population_change_percent": round(pop_change, 2) if pop_change else None,
            "measurement_period": f"{values[-1].get('year') if values else 'N/A'} - {values[0].get('year') if values else 'N/A'}"
        }
    }


def _get_gdp_per_capita(country_code: str) -> dict:
    """Get GDP per capita for a country."""
    return _get_indicator(country_code, "NY.GDP.PCAP.CD")  # GDP per capita (current US$)


def _get_economic_snapshot(country_code: str) -> dict:
    """Get MODERATE VERBOSE comprehensive economic snapshot with historical data for skill mode."""
    country_info = _get_country_info(country_code)
    if not country_info.get("success"):
        return country_info
    
    # MODERATE VERBOSE: 20-year data range (balanced)
    year_start = 2003
    year_end = 2023
    
    # Get key indicators - VERBOSE: full historical data
    gdp = _get_indicator(country_code, "NY.GDP.MKTP.CD", year_start, year_end)
    population = _get_indicator(country_code, "SP.POP.TOTL", year_start, year_end)
    gdp_per_capita = _get_indicator(country_code, "NY.GDP.PCAP.CD", year_start, year_end)
    inflation = _get_indicator(country_code, "FP.CPI.TOTL.ZG", year_start, year_end)
    unemployment = _get_indicator(country_code, "SL.UEM.TOTL.ZS", year_start, year_end)
    
    # VERBOSE: Additional economic indicators
    gni = _get_indicator(country_code, "NY.GNP.MKTP.CD", year_start, year_end)  # GNI
    gni_per_capita = _get_indicator(country_code, "NY.GNP.PCAP.CD", year_start, year_end)  # GNI per capita
    gdp_growth = _get_indicator(country_code, "NY.GDP.MKTP.KD.ZG", year_start, year_end)  # GDP growth
    exports = _get_indicator(country_code, "NE.EXP.GNFS.ZS", year_start, year_end)  # Exports % GDP
    imports = _get_indicator(country_code, "NE.IMP.GNFS.ZS", year_start, year_end)  # Imports % GDP
    fdi = _get_indicator(country_code, "BX.KLT.DINV.WD.GD.ZS", year_start, year_end)  # FDI % GDP
    
    # VERBOSE: Social indicators
    urban_pop = _get_indicator(country_code, "SP.URB.TOTL.IN.ZS", year_start, year_end)
    life_exp = _get_indicator(country_code, "SP.DYN.LE00.IN", year_start, year_end)
    pop_growth = _get_indicator(country_code, "SP.POP.GROW", year_start, year_end)
    fertility = _get_indicator(country_code, "SP.DYN.TFRT.IN", year_start, year_end)
    
    # VERBOSE: Education indicators
    school_enrollment = _get_indicator(country_code, "SE.SEC.ENRR", year_start, year_end)
    literacy = _get_indicator(country_code, "SE.ADT.LITR.ZS", year_start, year_end)
    
    # VERBOSE: Health indicators
    health_expenditure = _get_indicator(country_code, "SH.XPD.CHEX.GD.ZS", year_start, year_end)
    infant_mortality = _get_indicator(country_code, "SP.DYN.IMRT.IN", year_start, year_end)
    
    # VERBOSE: Infrastructure indicators
    internet_users = _get_indicator(country_code, "IT.NET.USER.ZS", year_start, year_end)
    mobile_subscriptions = _get_indicator(country_code, "IT.CEL.SETS.P2", year_start, year_end)
    
    # ULTRA VERBOSE: Additional economic indicators
    trade_balance = _get_indicator(country_code, "NE.RSB.GNFS.ZS", year_start, year_end)  # Trade balance % GDP
    debt_gdp = _get_indicator(country_code, "GC.DOD.TOTL.GD.ZS", year_start, year_end)  # Debt % GDP
    tax_revenue = _get_indicator(country_code, "GC.TAX.TOTL.GD.ZS", year_start, year_end)  # Tax revenue % GDP
    military_exp = _get_indicator(country_code, "MS.MIL.XPND.GD.ZS", year_start, year_end)  # Military % GDP
    r_and_d = _get_indicator(country_code, "GB.XPD.RSDV.GD.ZS", year_start, year_end)  # R&D % GDP
    
    # ULTRA VERBOSE: Labor market indicators
    labor_force = _get_indicator(country_code, "SL.TLF.TOTL.IN", year_start, year_end)
    employment_ratio = _get_indicator(country_code, "SL.EMP.TOTL.SP.ZS", year_start, year_end)
    youth_unemployment = _get_indicator(country_code, "SL.UEM.1524.ZS", year_start, year_end)
    
    # ULTRA VERBOSE: Environment indicators
    co2_emissions = _get_indicator(country_code, "EN.ATM.CO2E.PC", year_start, year_end)
    renewable_energy = _get_indicator(country_code, "EG.FEC.RNEW.ZS", year_start, year_end)
    forest_area = _get_indicator(country_code, "AG.LND.FRST.ZS", year_start, year_end)
    
    # Calculate compound statistics
    gdp_values = gdp.get("values", []) if gdp.get("success") else []
    pop_values = population.get("values", []) if population.get("success") else []
    
    # VERBOSE: Calculate growth rates and trends
    gdp_cagr = None
    if len(gdp_values) >= 2:
        first_gdp = gdp_values[-1].get("value") if gdp_values else None
        last_gdp = gdp_values[0].get("value") if gdp_values else None
        years_diff = int(gdp_values[0].get("year", 0)) - int(gdp_values[-1].get("year", 0))
        if first_gdp and last_gdp and first_gdp > 0 and years_diff > 0:
            gdp_cagr = ((last_gdp / first_gdp) ** (1 / years_diff) - 1) * 100
    
    # VERBOSE: Year-over-year GDP changes
    yoy_gdp_changes = []
    for i in range(len(gdp_values) - 1):
        curr = gdp_values[i].get("value", 0)
        prev = gdp_values[i+1].get("value", 0)
        if prev and prev > 0:
            yoy_gdp_changes.append({
                "year": gdp_values[i].get("year"),
                "gdp": curr,
                "previous_year_gdp": prev,
                "change_absolute": curr - prev,
                "change_percent": round((curr - prev) / prev * 100, 2)
            })
    
    return {
        "success": True,
        "country": country_info.get("country"),
        "economic_indicators": {
            "gdp": gdp.get("latest_value") if gdp.get("success") else None,
            "population": population.get("latest_value") if population.get("success") else None,
            "gdp_per_capita": gdp_per_capita.get("latest_value") if gdp_per_capita.get("success") else None,
            "inflation_rate": inflation.get("latest_value") if inflation.get("success") else None,
            "unemployment_rate": unemployment.get("latest_value") if unemployment.get("success") else None
        },
        # VERBOSE: Full historical data for pattern to extract trends from
        "historical_gdp": gdp_values,
        "historical_population": pop_values,
        "historical_gdp_per_capita": gdp_per_capita.get("values", []) if gdp_per_capita.get("success") else [],
        "historical_inflation": inflation.get("values", []) if inflation.get("success") else [],
        "historical_unemployment": unemployment.get("values", []) if unemployment.get("success") else [],
        # VERBOSE: Additional economic indicators
        "additional_economic": {
            "gni": gni.get("values", []) if gni.get("success") else [],
            "gni_per_capita": gni_per_capita.get("values", []) if gni_per_capita.get("success") else [],
            "gdp_growth": gdp_growth.get("values", []) if gdp_growth.get("success") else [],
            "exports_pct_gdp": exports.get("values", []) if exports.get("success") else [],
            "imports_pct_gdp": imports.get("values", []) if imports.get("success") else [],
            "fdi_pct_gdp": fdi.get("values", []) if fdi.get("success") else []
        },
        # VERBOSE: Social indicators
        "social_indicators": {
            "urban_population_pct": urban_pop.get("values", []) if urban_pop.get("success") else [],
            "life_expectancy": life_exp.get("values", []) if life_exp.get("success") else [],
            "population_growth": pop_growth.get("values", []) if pop_growth.get("success") else [],
            "fertility_rate": fertility.get("values", []) if fertility.get("success") else []
        },
        # VERBOSE: Education indicators
        "education_indicators": {
            "school_enrollment": school_enrollment.get("values", []) if school_enrollment.get("success") else [],
            "adult_literacy": literacy.get("values", []) if literacy.get("success") else []
        },
        # VERBOSE: Health indicators
        "health_indicators": {
            "health_expenditure_pct_gdp": health_expenditure.get("values", []) if health_expenditure.get("success") else [],
            "infant_mortality": infant_mortality.get("values", []) if infant_mortality.get("success") else []
        },
        # VERBOSE: Infrastructure indicators
        "infrastructure_indicators": {
            "internet_users_pct": internet_users.get("values", []) if internet_users.get("success") else [],
            "mobile_subscriptions": mobile_subscriptions.get("values", []) if mobile_subscriptions.get("success") else []
        },
        # VERBOSE: Calculated statistics
        "trend_analysis": {
            "gdp_cagr_percent": round(gdp_cagr, 2) if gdp_cagr else None,
            "measurement_period": f"{year_start}-{year_end}",
            "yoy_gdp_changes": yoy_gdp_changes
        },
        # ULTRA VERBOSE: Additional economic indicators
        "fiscal_indicators": {
            "trade_balance_pct_gdp": trade_balance.get("values", []) if trade_balance.get("success") else [],
            "government_debt_pct_gdp": debt_gdp.get("values", []) if debt_gdp.get("success") else [],
            "tax_revenue_pct_gdp": tax_revenue.get("values", []) if tax_revenue.get("success") else [],
            "military_expenditure_pct_gdp": military_exp.get("values", []) if military_exp.get("success") else [],
            "rd_expenditure_pct_gdp": r_and_d.get("values", []) if r_and_d.get("success") else []
        },
        # ULTRA VERBOSE: Labor market indicators
        "labor_market": {
            "labor_force_total": labor_force.get("values", []) if labor_force.get("success") else [],
            "employment_to_population_ratio": employment_ratio.get("values", []) if employment_ratio.get("success") else [],
            "youth_unemployment_rate": youth_unemployment.get("values", []) if youth_unemployment.get("success") else []
        },
        # ULTRA VERBOSE: Environment indicators
        "environment_indicators": {
            "co2_emissions_per_capita": co2_emissions.get("values", []) if co2_emissions.get("success") else [],
            "renewable_energy_pct": renewable_energy.get("values", []) if renewable_energy.get("success") else [],
            "forest_area_pct": forest_area.get("values", []) if forest_area.get("success") else []
        }
    }


# ============== Tool Handlers ==============

async def on_get_country_info(context: RunContextWrapper, params_str: str) -> Any:
    """Handler for getting country info."""
    params = _parse_params(params_str)
    country_code = params.get("country_code")
    
    if not country_code:
        return {"error": "country_code is required", "success": False}
    
    result = _get_country_info(country_code)
    return result


async def on_get_indicator(context: RunContextWrapper, params_str: str) -> Any:
    """Handler for getting indicator data."""
    params = _parse_params(params_str)
    country_code = params.get("country_code")
    indicator = params.get("indicator")
    
    if not country_code or not indicator:
        return {"error": "country_code and indicator are required", "success": False}
    
    result = _get_indicator(country_code, indicator)
    return result


async def on_get_gdp(context: RunContextWrapper, params_str: str) -> Any:
    """Handler for getting GDP data."""
    params = _parse_params(params_str)
    country_code = params.get("country_code")
    
    if not country_code:
        return {"error": "country_code is required", "success": False}
    
    result = _get_gdp(country_code)
    return result


async def on_get_economic_snapshot(context: RunContextWrapper, params_str: str) -> Any:
    """Handler for getting economic snapshot."""
    params = _parse_params(params_str)
    country_code = params.get("country_code")
    
    if not country_code:
        return {"error": "country_code is required", "success": False}
    
    result = _get_economic_snapshot(country_code)
    return result


async def on_get_population_detailed(context: RunContextWrapper, params_str: str) -> Any:
    """Handler for getting detailed population data."""
    params = _parse_params(params_str)
    country_code = params.get("country_code")
    
    if not country_code:
        return {"error": "country_code is required", "success": False}
    
    result = _get_population_detailed(country_code)
    return result


# ============== Tool Definitions ==============

tool_worldbank_country = FunctionTool(
    name='local-worldbank_country_info',
    description='''Get information about a country from World Bank database.

Returns dict:
{
    "success": bool,              # Whether request succeeded
    "country": {
        "id": str,                # Country code (e.g., "USA", "CHN")
        "name": str,              # Full country name (e.g., "United States")
        "iso2Code": str,          # ISO 2-letter code (e.g., "US")
        "region": str,            # World Bank region (e.g., "North America")
        "income_level": str,      # Income classification (e.g., "High income")
        "lending_type": str,      # Lending category
        "capital_city": str,      # Capital city name
        "longitude": str,         # Geographic longitude
        "latitude": str           # Geographic latitude
    }
}

On error: {"error": str, "success": False}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "country_code": {
                "type": "string",
                "description": "ISO 3166-1 alpha-2 or alpha-3 country code (e.g., 'US', 'USA', 'CHN')"
            }
        },
        "required": ["country_code"]
    },
    on_invoke_tool=on_get_country_info
)

tool_worldbank_indicator = FunctionTool(
    name='local-worldbank_indicator',
    description='''Get specific economic indicator data for a country.

Returns dict:
{
    "success": bool,              # Whether request succeeded
    "country_code": str,          # Country code queried
    "indicator": str,             # Indicator code (e.g., "NY.GDP.MKTP.CD")
    "data_points": int,           # Number of data points returned
    "values": [                   # Historical values (newest first)
        {
            "year": str,          # Year (e.g., "2022")
            "value": float,       # Indicator value
            "indicator": str      # Indicator name/description
        }
    ],
    "latest_value": {             # Most recent data point
        "year": str,
        "value": float,
        "indicator": str
    } | None
}

On error: {"error": str, "success": False}

Common indicator codes:
- NY.GDP.MKTP.CD: GDP (current US$)
- SP.POP.TOTL: Population total
- NY.GDP.PCAP.CD: GDP per capita (current US$)
- FP.CPI.TOTL.ZG: Inflation rate (%)
- SL.UEM.TOTL.ZS: Unemployment rate (%)''',
    params_json_schema={
        "type": "object",
        "properties": {
            "country_code": {
                "type": "string",
                "description": "Country code (e.g., 'US', 'CHN')"
            },
            "indicator": {
                "type": "string",
                "description": "World Bank indicator code (e.g., 'NY.GDP.MKTP.CD' for GDP)"
            }
        },
        "required": ["country_code", "indicator"]
    },
    on_invoke_tool=on_get_indicator
)

tool_worldbank_gdp = FunctionTool(
    name='local-worldbank_gdp',
    description='''Get GDP data for a country (shortcut for GDP indicator NY.GDP.MKTP.CD).

Returns dict:
{
    "success": bool,              # Whether request succeeded
    "country_code": str,          # Country code queried
    "indicator": str,             # "NY.GDP.MKTP.CD"
    "data_points": int,           # Number of data points (typically 5 years)
    "values": [                   # Historical GDP values (newest first)
        {
            "year": str,          # Year (e.g., "2022")
            "value": float,       # GDP in current US dollars
            "indicator": str      # "GDP (current US$)"
        }
    ],
    "latest_value": {             # Most recent GDP data
        "year": str,
        "value": float,
        "indicator": str
    } | None
}

On error: {"error": str, "success": False}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "country_code": {
                "type": "string",
                "description": "Country code (e.g., 'US', 'CHN', 'JPN')"
            }
        },
        "required": ["country_code"]
    },
    on_invoke_tool=on_get_gdp
)

tool_worldbank_snapshot = FunctionTool(
    name='local-worldbank_economic_snapshot',
    description='''Get comprehensive economic snapshot with multiple indicators for a country.

Returns dict:
{
    "success": bool,              # Whether request succeeded
    "country": {                  # Country information
        "id": str,                # Country code
        "name": str,              # Full country name
        "iso2Code": str,          # ISO 2-letter code
        "region": str,            # World Bank region
        "income_level": str,      # Income classification
        "lending_type": str,      # Lending category
        "capital_city": str,      # Capital city
        "longitude": str,
        "latitude": str
    },
    "economic_indicators": {
        "gdp": {                  # Latest GDP data
            "year": str,
            "value": float,       # GDP in current US$
            "indicator": str
        } | None,
        "population": {           # Latest population
            "year": str,
            "value": float,       # Total population
            "indicator": str
        } | None,
        "gdp_per_capita": {       # GDP per capita
            "year": str,
            "value": float,       # Per capita in US$
            "indicator": str
        } | None,
        "inflation_rate": {       # Latest inflation
            "year": str,
            "value": float,       # Percentage
            "indicator": str
        } | None,
        "unemployment_rate": {    # Latest unemployment
            "year": str,
            "value": float,       # Percentage
            "indicator": str
        } | None
    },
    "historical_gdp": [           # Up to 5 years of GDP data
        {"year": str, "value": float, "indicator": str}
    ]
}

On error: {"error": str, "success": False}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "country_code": {
                "type": "string",
                "description": "Country code (e.g., 'US', 'CHN', 'DEU')"
            }
        },
        "required": ["country_code"]
    },
    on_invoke_tool=on_get_economic_snapshot
)


tool_worldbank_population = FunctionTool(
    name='local-worldbank_population',
    description='''Get detailed population data including demographics for a country.

**Returns:** dict:
{
  "success": bool,
  "country_code": str,                # Country code queried
  "population": {
    "latest": {                       # Most recent population data
      "year": str,
      "value": float,                 # Population count
      "indicator": str
    } | None,
    "historical": [                   # Up to 5 years of data
      {"year": str, "value": float, "indicator": str}
    ],
    "data_years": int                 # Number of data points
  },
  "demographics": {
    "growth_rate": {                  # Annual population growth rate
      "year": str,
      "value": float,                 # Percentage
      "indicator": str
    } | None,
    "urban_percent": {                # Urban population percentage
      "year": str,
      "value": float,                 # Percentage
      "indicator": str
    } | None,
    "life_expectancy": {              # Life expectancy at birth
      "year": str,
      "value": float,                 # Years
      "indicator": str
    } | None
  },
  "trends": {
    "population_change_percent": float | None,  # Change over measurement period
    "measurement_period": str         # e.g., "2015 - 2022"
  }
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "country_code": {
                "type": "string",
                "description": "Country code (e.g., 'US', 'CHN', 'IND')"
            }
        },
        "required": ["country_code"]
    },
    on_invoke_tool=on_get_population_detailed
)


# Export all tools as a list
worldbank_tools = [
    tool_worldbank_country,
    tool_worldbank_indicator,
    tool_worldbank_gdp,
    tool_worldbank_snapshot,
    tool_worldbank_population,
]

