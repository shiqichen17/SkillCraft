"""
Weather Tools for global-weather-monitor task
Based on Open-Meteo API - completely free, no API key required.

Open-Meteo API Documentation: https://open-meteo.com/en/docs
"""

import json
from typing import Any, Dict, List
from agents.tool import FunctionTool, RunContextWrapper
import requests

# Base URLs for Open-Meteo APIs
GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
HISTORICAL_URL = "https://archive-api.open-meteo.com/v1/archive"


# ============== City Data for Task ==============
# 10 major world cities for weather monitoring
CITIES = [
    {"name": "Tokyo", "country": "Japan"},
    {"name": "New York", "country": "United States"},
    {"name": "London", "country": "United Kingdom"},
    {"name": "Paris", "country": "France"},
    {"name": "Sydney", "country": "Australia"},
    {"name": "Dubai", "country": "United Arab Emirates"},
    {"name": "Singapore", "country": "Singapore"},
    {"name": "Toronto", "country": "Canada"},
    {"name": "Berlin", "country": "Germany"},
    {"name": "São Paulo", "country": "Brazil"},
]


# ============== Tool 1: Get City Coordinates ==============

async def on_get_coordinates(context: RunContextWrapper, params_str: str) -> Any:
    """Get latitude and longitude for a city using geocoding API."""
    try:
        params = json.loads(params_str) if params_str else {}
    except json.JSONDecodeError:
        return {"success": False, "error": "Invalid JSON parameters"}
    
    city_name = params.get("city_name", "")
    country = params.get("country", "")
    
    if not city_name:
        return {"success": False, "error": "city_name is required"}
    
    try:
        search_query = f"{city_name}, {country}" if country else city_name
        response = requests.get(
            GEOCODING_URL,
            params={"name": city_name, "count": 5, "language": "en", "format": "json"},
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        
        results = data.get("results", [])
        if not results:
            return {"success": False, "error": f"City '{city_name}' not found"}
        
        # Find best match (prefer exact country match)
        best_match = results[0]
        if country:
            for r in results:
                if country.lower() in r.get("country", "").lower():
                    best_match = r
                    break
        
        return {
            "success": True,
            "city": best_match.get("name"),
            "country": best_match.get("country"),
            "latitude": best_match.get("latitude"),
            "longitude": best_match.get("longitude"),
            "timezone": best_match.get("timezone"),
            "population": best_match.get("population"),
            "elevation": best_match.get("elevation"),
            "admin1": best_match.get("admin1", ""),  # State/Province
            "country_code": best_match.get("country_code"),
            "all_results_count": len(results)
        }
        
    except requests.RequestException as e:
        return {"success": False, "error": f"API error: {str(e)}"}


tool_get_coordinates = FunctionTool(
    name='local-weather_get_coordinates',
    description='''Get geographic coordinates (latitude, longitude) for a city.

**Input:** city_name (str), country (str, optional)

**Returns:** dict:
{
  "success": bool,
  "city": str,
  "country": str,
  "latitude": float,
  "longitude": float,
  "timezone": str,
  "population": int
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "city_name": {"type": "string", "description": "Name of the city (e.g., 'Tokyo', 'New York')"},
            "country": {"type": "string", "description": "Country name for disambiguation (optional)"},
        },
        "required": ["city_name"]
    },
    on_invoke_tool=on_get_coordinates
)


# ============== Tool 2: Get Current Weather ==============

async def on_get_current_weather(context: RunContextWrapper, params_str: str) -> Any:
    """Get current weather conditions for a location."""
    try:
        params = json.loads(params_str) if params_str else {}
    except json.JSONDecodeError:
        return {"success": False, "error": "Invalid JSON parameters"}
    
    latitude = params.get("latitude")
    longitude = params.get("longitude")
    city_name = params.get("city_name", "Unknown")
    
    if latitude is None or longitude is None:
        return {"success": False, "error": "latitude and longitude are required"}
    
    try:
        current_vars = [
            "temperature_2m", "relative_humidity_2m", "apparent_temperature",
            "is_day", "precipitation", "rain", "showers", "snowfall",
            "weather_code", "cloud_cover", "pressure_msl", "surface_pressure",
            "wind_speed_10m", "wind_direction_10m", "wind_gusts_10m"
        ]
        
        response = requests.get(
            WEATHER_URL,
            params={
                "latitude": latitude,
                "longitude": longitude,
                "current": ",".join(current_vars),
                "timezone": "auto"
            },
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        
        current = data.get("current", {})
        units = data.get("current_units", {})
        
        # Weather code descriptions
        weather_codes = {
            0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
            45: "Fog", 48: "Depositing rime fog",
            51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
            61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
            71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow",
            80: "Slight rain showers", 81: "Moderate rain showers", 82: "Violent rain showers",
            95: "Thunderstorm", 96: "Thunderstorm with slight hail", 99: "Thunderstorm with heavy hail"
        }
        
        weather_code = current.get("weather_code", 0)
        
        return {
            "success": True,
            "city": city_name,
            "location": {"latitude": latitude, "longitude": longitude},
            "timezone": data.get("timezone"),
            "time": current.get("time"),
            "current_conditions": {
                "temperature": current.get("temperature_2m"),
                "temperature_unit": units.get("temperature_2m", "°C"),
                "feels_like": current.get("apparent_temperature"),
                "humidity": current.get("relative_humidity_2m"),
                "humidity_unit": units.get("relative_humidity_2m", "%"),
                "weather_code": weather_code,
                "weather_description": weather_codes.get(weather_code, "Unknown"),
                "is_day": current.get("is_day") == 1,
                "cloud_cover": current.get("cloud_cover"),
                "cloud_cover_unit": units.get("cloud_cover", "%"),
                "precipitation": current.get("precipitation"),
                "precipitation_unit": units.get("precipitation", "mm"),
                "rain": current.get("rain"),
                "snowfall": current.get("snowfall"),
                "pressure": current.get("pressure_msl"),
                "pressure_unit": units.get("pressure_msl", "hPa"),
                "wind_speed": current.get("wind_speed_10m"),
                "wind_speed_unit": units.get("wind_speed_10m", "km/h"),
                "wind_direction": current.get("wind_direction_10m"),
                "wind_gusts": current.get("wind_gusts_10m")
            }
        }
        
    except requests.RequestException as e:
        return {"success": False, "error": f"API error: {str(e)}"}


tool_get_current_weather = FunctionTool(
    name='local-weather_get_current',
    description='''Get current weather conditions including temperature, humidity, precipitation, wind, and cloud cover.

**Input:** latitude (float), longitude (float), city_name (str, optional)

**Returns:** dict:
{
  "success": bool,
  "city": str,
  "current_conditions": {
    "temperature": float,
    "feels_like": float,
    "humidity": int,
    "weather_description": str,
    "wind_speed": float,
    ...
  }
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "latitude": {"type": "number", "description": "Latitude of the location"},
            "longitude": {"type": "number", "description": "Longitude of the location"},
            "city_name": {"type": "string", "description": "City name for labeling (optional)"},
        },
        "required": ["latitude", "longitude"]
    },
    on_invoke_tool=on_get_current_weather
)


# ============== Tool 3: Get Hourly Forecast ==============

async def on_get_hourly_forecast(context: RunContextWrapper, params_str: str) -> Any:
    """Get hourly weather forecast for the next 7 days (168 hours)."""
    try:
        params = json.loads(params_str) if params_str else {}
    except json.JSONDecodeError:
        return {"success": False, "error": "Invalid JSON parameters"}
    
    latitude = params.get("latitude")
    longitude = params.get("longitude")
    city_name = params.get("city_name", "Unknown")
    
    if latitude is None or longitude is None:
        return {"success": False, "error": "latitude and longitude are required"}
    
    try:
        hourly_vars = [
            "temperature_2m", "relative_humidity_2m", "apparent_temperature",
            "precipitation_probability", "precipitation", "rain", "snowfall",
            "weather_code", "cloud_cover", "visibility",
            "wind_speed_10m", "wind_direction_10m", "wind_gusts_10m",
            "uv_index", "is_day"
        ]
        
        response = requests.get(
            WEATHER_URL,
            params={
                "latitude": latitude,
                "longitude": longitude,
                "hourly": ",".join(hourly_vars),
                "timezone": "auto",
                "forecast_days": 7
            },
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        
        hourly = data.get("hourly", {})
        units = data.get("hourly_units", {})
        
        # Get raw data arrays
        times = hourly.get("time", [])
        temps = hourly.get("temperature_2m", [])
        precip_probs = hourly.get("precipitation_probability", [])
        precips = hourly.get("precipitation", [])
        humidities = hourly.get("relative_humidity_2m", [])
        
        # Build full 168-hour forecast array with all fields
        weather_codes = {
            0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
            45: "Fog", 48: "Depositing rime fog",
            51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
            61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
            71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow",
            80: "Slight rain showers", 81: "Moderate rain showers", 82: "Violent rain showers",
            95: "Thunderstorm", 96: "Thunderstorm with slight hail", 99: "Thunderstorm with heavy hail"
        }
        
        hourly_forecast = []
        for i, time in enumerate(times):
            weather_code = hourly.get("weather_code", [0])[i] if i < len(hourly.get("weather_code", [])) else 0
            hourly_forecast.append({
                "time": time,
                "temperature": hourly.get("temperature_2m", [None])[i] if i < len(hourly.get("temperature_2m", [])) else None,
                "feels_like": hourly.get("apparent_temperature", [None])[i] if i < len(hourly.get("apparent_temperature", [])) else None,
                "humidity": hourly.get("relative_humidity_2m", [None])[i] if i < len(hourly.get("relative_humidity_2m", [])) else None,
                "precipitation_probability": hourly.get("precipitation_probability", [None])[i] if i < len(hourly.get("precipitation_probability", [])) else None,
                "precipitation": hourly.get("precipitation", [None])[i] if i < len(hourly.get("precipitation", [])) else None,
                "rain": hourly.get("rain", [None])[i] if i < len(hourly.get("rain", [])) else None,
                "snowfall": hourly.get("snowfall", [None])[i] if i < len(hourly.get("snowfall", [])) else None,
                "weather_code": weather_code,
                "weather_description": weather_codes.get(weather_code, "Unknown"),
                "cloud_cover": hourly.get("cloud_cover", [None])[i] if i < len(hourly.get("cloud_cover", [])) else None,
                "visibility": hourly.get("visibility", [None])[i] if i < len(hourly.get("visibility", [])) else None,
                "wind_speed": hourly.get("wind_speed_10m", [None])[i] if i < len(hourly.get("wind_speed_10m", [])) else None,
                "wind_direction": hourly.get("wind_direction_10m", [None])[i] if i < len(hourly.get("wind_direction_10m", [])) else None,
                "wind_gusts": hourly.get("wind_gusts_10m", [None])[i] if i < len(hourly.get("wind_gusts_10m", [])) else None,
                "uv_index": hourly.get("uv_index", [None])[i] if i < len(hourly.get("uv_index", [])) else None,
                "is_day": hourly.get("is_day", [None])[i] == 1 if i < len(hourly.get("is_day", [])) else None
            })
        
        # Calculate summary statistics
        valid_temps = [h["temperature"] for h in hourly_forecast if h["temperature"] is not None]
        valid_precip_probs = [h["precipitation_probability"] for h in hourly_forecast if h["precipitation_probability"] is not None]
        valid_humidities = [h["humidity"] for h in hourly_forecast if h["humidity"] is not None]
        valid_precips = [h["precipitation"] for h in hourly_forecast if h["precipitation"] is not None]
        
        return {
            "success": True,
            "city": city_name,
            "location": {"latitude": latitude, "longitude": longitude},
            "timezone": data.get("timezone"),
            "units": {
                "temperature": units.get("temperature_2m", "°C"),
                "precipitation": units.get("precipitation", "mm"),
                "humidity": units.get("relative_humidity_2m", "%"),
                "wind_speed": units.get("wind_speed_10m", "km/h"),
                "visibility": units.get("visibility", "m")
            },
            "total_hours": len(hourly_forecast),
            "hourly_forecast": hourly_forecast,
            "summary": {
                "avg_temperature": round(sum(valid_temps) / len(valid_temps), 1) if valid_temps else None,
                "max_temperature": max(valid_temps) if valid_temps else None,
                "min_temperature": min(valid_temps) if valid_temps else None,
                "avg_precipitation_probability": round(sum(valid_precip_probs) / len(valid_precip_probs), 1) if valid_precip_probs else None,
                "avg_humidity": round(sum(valid_humidities) / len(valid_humidities), 1) if valid_humidities else None,
                "total_precipitation": round(sum(valid_precips), 1) if valid_precips else 0
            }
        }
        
    except requests.RequestException as e:
        return {"success": False, "error": f"API error: {str(e)}"}


tool_get_hourly_forecast = FunctionTool(
    name='local-weather_get_hourly',
    description='''Get full hourly weather forecast for next 7 days (168 hours) with detailed conditions.

**Input:** latitude (float), longitude (float), city_name (str, optional)

**Returns:** dict with ~168 hourly entries:
{
  "success": bool,
  "city": str,
  "total_hours": 168,
  "hourly_forecast": [{"time": str, "temperature": float, "feels_like": float, "humidity": int, "precipitation_probability": int, "precipitation": float, "weather_description": str, "cloud_cover": int, "wind_speed": float, "uv_index": float, ...}],
  "summary": {"avg_temperature": float, "max_temperature": float, "min_temperature": float, "total_precipitation": float, ...}
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "latitude": {"type": "number", "description": "Latitude of the location"},
            "longitude": {"type": "number", "description": "Longitude of the location"},
            "city_name": {"type": "string", "description": "City name for labeling (optional)"},
        },
        "required": ["latitude", "longitude"]
    },
    on_invoke_tool=on_get_hourly_forecast
)


# ============== Tool 4: Get Daily Forecast ==============

async def on_get_daily_forecast(context: RunContextWrapper, params_str: str) -> Any:
    """Get daily weather forecast for the next 14 days."""
    try:
        params = json.loads(params_str) if params_str else {}
    except json.JSONDecodeError:
        return {"success": False, "error": "Invalid JSON parameters"}
    
    latitude = params.get("latitude")
    longitude = params.get("longitude")
    city_name = params.get("city_name", "Unknown")
    
    if latitude is None or longitude is None:
        return {"success": False, "error": "latitude and longitude are required"}
    
    try:
        daily_vars = [
            "temperature_2m_max", "temperature_2m_min", "apparent_temperature_max",
            "apparent_temperature_min", "sunrise", "sunset", "daylight_duration",
            "sunshine_duration", "uv_index_max", "uv_index_clear_sky_max",
            "precipitation_sum", "rain_sum", "showers_sum", "snowfall_sum",
            "precipitation_hours", "precipitation_probability_max",
            "wind_speed_10m_max", "wind_gusts_10m_max", "wind_direction_10m_dominant",
            "weather_code"
        ]
        
        response = requests.get(
            WEATHER_URL,
            params={
                "latitude": latitude,
                "longitude": longitude,
                "daily": ",".join(daily_vars),
                "timezone": "auto",
                "forecast_days": 14
            },
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        
        daily = data.get("daily", {})
        units = data.get("daily_units", {})
        
        # Weather code descriptions
        weather_codes = {
            0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
            45: "Fog", 48: "Depositing rime fog",
            51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
            61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
            71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow",
            80: "Slight rain showers", 81: "Moderate rain showers", 82: "Violent rain showers",
            95: "Thunderstorm", 96: "Thunderstorm with slight hail", 99: "Thunderstorm with heavy hail"
        }
        
        # Build full daily forecast array with all available fields
        dates = daily.get("time", [])
        
        forecast = []
        for i, date in enumerate(dates):
            weather_code = daily.get("weather_code", [0])[i] if i < len(daily.get("weather_code", [])) else 0
            forecast.append({
                "date": date,
                "temperature_max": daily.get("temperature_2m_max", [None])[i] if i < len(daily.get("temperature_2m_max", [])) else None,
                "temperature_min": daily.get("temperature_2m_min", [None])[i] if i < len(daily.get("temperature_2m_min", [])) else None,
                "apparent_temp_max": daily.get("apparent_temperature_max", [None])[i] if i < len(daily.get("apparent_temperature_max", [])) else None,
                "apparent_temp_min": daily.get("apparent_temperature_min", [None])[i] if i < len(daily.get("apparent_temperature_min", [])) else None,
                "sunrise": daily.get("sunrise", [None])[i] if i < len(daily.get("sunrise", [])) else None,
                "sunset": daily.get("sunset", [None])[i] if i < len(daily.get("sunset", [])) else None,
                "daylight_duration": daily.get("daylight_duration", [None])[i] if i < len(daily.get("daylight_duration", [])) else None,
                "sunshine_duration": daily.get("sunshine_duration", [None])[i] if i < len(daily.get("sunshine_duration", [])) else None,
                "uv_index_max": daily.get("uv_index_max", [None])[i] if i < len(daily.get("uv_index_max", [])) else None,
                "uv_index_clear_sky_max": daily.get("uv_index_clear_sky_max", [None])[i] if i < len(daily.get("uv_index_clear_sky_max", [])) else None,
                "precipitation_sum": daily.get("precipitation_sum", [None])[i] if i < len(daily.get("precipitation_sum", [])) else None,
                "rain_sum": daily.get("rain_sum", [None])[i] if i < len(daily.get("rain_sum", [])) else None,
                "showers_sum": daily.get("showers_sum", [None])[i] if i < len(daily.get("showers_sum", [])) else None,
                "snowfall_sum": daily.get("snowfall_sum", [None])[i] if i < len(daily.get("snowfall_sum", [])) else None,
                "precipitation_hours": daily.get("precipitation_hours", [None])[i] if i < len(daily.get("precipitation_hours", [])) else None,
                "precipitation_probability_max": daily.get("precipitation_probability_max", [None])[i] if i < len(daily.get("precipitation_probability_max", [])) else None,
                "wind_speed_max": daily.get("wind_speed_10m_max", [None])[i] if i < len(daily.get("wind_speed_10m_max", [])) else None,
                "wind_gusts_max": daily.get("wind_gusts_10m_max", [None])[i] if i < len(daily.get("wind_gusts_10m_max", [])) else None,
                "wind_direction_dominant": daily.get("wind_direction_10m_dominant", [None])[i] if i < len(daily.get("wind_direction_10m_dominant", [])) else None,
                "weather_code": weather_code,
                "weather_description": weather_codes.get(weather_code, "Unknown")
            })
        
        # Calculate summary statistics
        valid_maxs = [f["temperature_max"] for f in forecast if f["temperature_max"] is not None]
        valid_mins = [f["temperature_min"] for f in forecast if f["temperature_min"] is not None]
        valid_precips = [f["precipitation_sum"] for f in forecast if f["precipitation_sum"] is not None]
        valid_uv = [f["uv_index_max"] for f in forecast if f["uv_index_max"] is not None]
        
        return {
            "success": True,
            "city": city_name,
            "location": {"latitude": latitude, "longitude": longitude},
            "timezone": data.get("timezone"),
            "units": {
                "temperature": units.get("temperature_2m_max", "°C"),
                "precipitation": units.get("precipitation_sum", "mm"),
                "wind_speed": units.get("wind_speed_10m_max", "km/h"),
                "daylight_duration": units.get("daylight_duration", "seconds"),
                "sunshine_duration": units.get("sunshine_duration", "seconds")
            },
            "forecast_days": len(forecast),
            "daily_forecast": forecast,
            "summary": {
                "avg_high": round(sum(valid_maxs) / len(valid_maxs), 1) if valid_maxs else None,
                "avg_low": round(sum(valid_mins) / len(valid_mins), 1) if valid_mins else None,
                "max_temp": max(valid_maxs) if valid_maxs else None,
                "min_temp": min(valid_mins) if valid_mins else None,
                "rainy_days": sum(1 for p in valid_precips if p > 0.1),
                "total_precipitation": round(sum(valid_precips), 1) if valid_precips else 0,
                "avg_uv_index": round(sum(valid_uv) / len(valid_uv), 1) if valid_uv else None
            }
        }
        
    except requests.RequestException as e:
        return {"success": False, "error": f"API error: {str(e)}"}


tool_get_daily_forecast = FunctionTool(
    name='local-weather_get_daily',
    description='''Get full daily weather forecast for next 14 days with detailed conditions.

**Input:** latitude (float), longitude (float), city_name (str, optional)

**Returns:** dict with 14 daily entries:
{
  "success": bool,
  "city": str,
  "forecast_days": 14,
  "daily_forecast": [{"date": str, "temperature_max": float, "temperature_min": float, "apparent_temp_max": float, "sunrise": str, "sunset": str, "daylight_duration": float, "uv_index_max": float, "precipitation_sum": float, "precipitation_probability_max": int, "wind_speed_max": float, "weather_description": str, ...}],
  "summary": {"avg_high": float, "avg_low": float, "rainy_days": int, "total_precipitation": float, "avg_uv_index": float}
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "latitude": {"type": "number", "description": "Latitude of the location"},
            "longitude": {"type": "number", "description": "Longitude of the location"},
            "city_name": {"type": "string", "description": "City name for labeling (optional)"},
        },
        "required": ["latitude", "longitude"]
    },
    on_invoke_tool=on_get_daily_forecast
)


# ============== Tool 5: Get Historical Weather ==============

async def on_get_historical_weather(context: RunContextWrapper, params_str: str) -> Any:
    """Get historical weather data for the past 30 days."""
    try:
        params = json.loads(params_str) if params_str else {}
    except json.JSONDecodeError:
        return {"success": False, "error": "Invalid JSON parameters"}
    
    latitude = params.get("latitude")
    longitude = params.get("longitude")
    city_name = params.get("city_name", "Unknown")
    
    if latitude is None or longitude is None:
        return {"success": False, "error": "latitude and longitude are required"}
    
    try:
        from datetime import datetime, timedelta
        
        end_date = datetime.now() - timedelta(days=1)  # Yesterday
        start_date = end_date - timedelta(days=30)
        
        daily_vars = [
            "temperature_2m_max", "temperature_2m_min", "temperature_2m_mean",
            "apparent_temperature_max", "apparent_temperature_min", "apparent_temperature_mean",
            "sunrise", "sunset", "daylight_duration", "sunshine_duration",
            "precipitation_sum", "rain_sum", "snowfall_sum",
            "precipitation_hours", "wind_speed_10m_max", "wind_gusts_10m_max",
            "wind_direction_10m_dominant", "weather_code"
        ]
        
        response = requests.get(
            HISTORICAL_URL,
            params={
                "latitude": latitude,
                "longitude": longitude,
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d"),
                "daily": ",".join(daily_vars),
                "timezone": "auto"
            },
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        
        daily = data.get("daily", {})
        units = data.get("daily_units", {})
        
        # Weather code descriptions
        weather_codes = {
            0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
            45: "Fog", 48: "Depositing rime fog",
            51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
            61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
            71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow",
            80: "Slight rain showers", 81: "Moderate rain showers", 82: "Violent rain showers",
            95: "Thunderstorm", 96: "Thunderstorm with slight hail", 99: "Thunderstorm with heavy hail"
        }
        
        # Build full daily history array with all available fields
        dates = daily.get("time", [])
        
        daily_history = []
        for i, date in enumerate(dates):
            weather_code = daily.get("weather_code", [0])[i] if i < len(daily.get("weather_code", [])) else 0
            daily_history.append({
                "date": date,
                "temperature_max": daily.get("temperature_2m_max", [None])[i] if i < len(daily.get("temperature_2m_max", [])) else None,
                "temperature_min": daily.get("temperature_2m_min", [None])[i] if i < len(daily.get("temperature_2m_min", [])) else None,
                "temperature_mean": daily.get("temperature_2m_mean", [None])[i] if i < len(daily.get("temperature_2m_mean", [])) else None,
                "apparent_temp_max": daily.get("apparent_temperature_max", [None])[i] if i < len(daily.get("apparent_temperature_max", [])) else None,
                "apparent_temp_min": daily.get("apparent_temperature_min", [None])[i] if i < len(daily.get("apparent_temperature_min", [])) else None,
                "apparent_temp_mean": daily.get("apparent_temperature_mean", [None])[i] if i < len(daily.get("apparent_temperature_mean", [])) else None,
                "sunrise": daily.get("sunrise", [None])[i] if i < len(daily.get("sunrise", [])) else None,
                "sunset": daily.get("sunset", [None])[i] if i < len(daily.get("sunset", [])) else None,
                "daylight_duration": daily.get("daylight_duration", [None])[i] if i < len(daily.get("daylight_duration", [])) else None,
                "sunshine_duration": daily.get("sunshine_duration", [None])[i] if i < len(daily.get("sunshine_duration", [])) else None,
                "precipitation_sum": daily.get("precipitation_sum", [None])[i] if i < len(daily.get("precipitation_sum", [])) else None,
                "rain_sum": daily.get("rain_sum", [None])[i] if i < len(daily.get("rain_sum", [])) else None,
                "snowfall_sum": daily.get("snowfall_sum", [None])[i] if i < len(daily.get("snowfall_sum", [])) else None,
                "precipitation_hours": daily.get("precipitation_hours", [None])[i] if i < len(daily.get("precipitation_hours", [])) else None,
                "wind_speed_max": daily.get("wind_speed_10m_max", [None])[i] if i < len(daily.get("wind_speed_10m_max", [])) else None,
                "wind_gusts_max": daily.get("wind_gusts_10m_max", [None])[i] if i < len(daily.get("wind_gusts_10m_max", [])) else None,
                "wind_direction_dominant": daily.get("wind_direction_10m_dominant", [None])[i] if i < len(daily.get("wind_direction_10m_dominant", [])) else None,
                "weather_code": weather_code,
                "weather_description": weather_codes.get(weather_code, "Unknown")
            })
        
        # Calculate summary statistics
        valid_maxs = [h["temperature_max"] for h in daily_history if h["temperature_max"] is not None]
        valid_mins = [h["temperature_min"] for h in daily_history if h["temperature_min"] is not None]
        valid_means = [h["temperature_mean"] for h in daily_history if h["temperature_mean"] is not None]
        valid_precips = [h["precipitation_sum"] for h in daily_history if h["precipitation_sum"] is not None]
        
        return {
            "success": True,
            "city": city_name,
            "location": {"latitude": latitude, "longitude": longitude},
            "timezone": data.get("timezone"),
            "units": {
                "temperature": units.get("temperature_2m_max", "°C"),
                "precipitation": units.get("precipitation_sum", "mm"),
                "wind_speed": units.get("wind_speed_10m_max", "km/h")
            },
            "period": {
                "start": start_date.strftime("%Y-%m-%d"),
                "end": end_date.strftime("%Y-%m-%d"),
                "days": len(daily_history)
            },
            "daily_history": daily_history,
            "summary": {
                "avg_high": round(sum(valid_maxs) / len(valid_maxs), 1) if valid_maxs else None,
                "avg_low": round(sum(valid_mins) / len(valid_mins), 1) if valid_mins else None,
                "avg_mean": round(sum(valid_means) / len(valid_means), 1) if valid_means else None,
                "highest": max(valid_maxs) if valid_maxs else None,
                "lowest": min(valid_mins) if valid_mins else None,
                "total_precipitation": round(sum(valid_precips), 1) if valid_precips else 0,
                "rainy_days": sum(1 for p in valid_precips if p > 0.1)
            }
        }
        
    except requests.RequestException as e:
        return {"success": False, "error": f"API error: {str(e)}"}


tool_get_historical_weather = FunctionTool(
    name='local-weather_get_historical',
    description='''Get full historical weather data for past 30 days with detailed daily breakdown.

**Input:** latitude (float), longitude (float), city_name (str, optional)

**Returns:** dict with 30 daily history entries:
{
  "success": bool,
  "city": str,
  "period": {"start": str, "end": str, "days": 30},
  "daily_history": [{"date": str, "temperature_max": float, "temperature_min": float, "temperature_mean": float, "apparent_temp_max": float, "sunrise": str, "sunset": str, "precipitation_sum": float, "wind_speed_max": float, "weather_description": str, ...}],
  "summary": {"avg_high": float, "avg_low": float, "highest": float, "lowest": float, "total_precipitation": float, "rainy_days": int}
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "latitude": {"type": "number", "description": "Latitude of the location"},
            "longitude": {"type": "number", "description": "Longitude of the location"},
            "city_name": {"type": "string", "description": "City name for labeling (optional)"},
        },
        "required": ["latitude", "longitude"]
    },
    on_invoke_tool=on_get_historical_weather
)


# ============== Export all tools ==============

weather_tools = [
    tool_get_coordinates,       # Step 1: Get city coordinates
    tool_get_current_weather,   # Step 2: Get current conditions
    tool_get_hourly_forecast,   # Step 3: Get hourly forecast (168 hours)
    tool_get_daily_forecast,    # Step 4: Get daily forecast (14 days)
    tool_get_historical_weather, # Step 5: Get historical data (30 days)
]

