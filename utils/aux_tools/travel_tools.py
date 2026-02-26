# travel_tools.py
# Travel itinerary planning tools based on M3ToolEval
import json
from typing import Any, List, Dict
from agents.tool import FunctionTool, RunContextWrapper


# ============== Fake Data Tables ==============
# NOTE: All 10 travel plans must have both outbound AND return flights available
# This ensures the task tests Skill Mode capability, not edge case handling
LOC = ["A", "B", "C", "D", "E", "F"]

FLIGHTS = [
    # Plan 1: E→A (2023-12-25) and A→E (2024-01-10)
    {"from_location": "E", "to_location": "A", "date": "2023-12-25", "price": 450},
    {"from_location": "A", "to_location": "E", "date": "2024-01-10", "price": 380},
    
    # Plan 2: E→B (2023-11-10) and B→E (2023-12-08)
    {"from_location": "E", "to_location": "B", "date": "2023-11-10", "price": 350},
    {"from_location": "E", "to_location": "B", "date": "2023-11-10", "price": 165},
    {"from_location": "B", "to_location": "E", "date": "2023-12-08", "price": 470},
    
    # Plan 3: E→C (2023-10-05) and C→E (2023-12-03)
    {"from_location": "E", "to_location": "C", "date": "2023-10-05", "price": 600},
    {"from_location": "C", "to_location": "E", "date": "2023-12-03", "price": 520},
    
    # Plan 4: E→D (2023-08-15) and D→E (2023-08-18)
    {"from_location": "E", "to_location": "D", "date": "2023-08-15", "price": 400},
    {"from_location": "D", "to_location": "E", "date": "2023-08-18", "price": 420},
    
    # Plan 5: A→C (2023-08-20) and C→A (2024-01-02)
    {"from_location": "A", "to_location": "C", "date": "2023-08-20", "price": 250},
    {"from_location": "C", "to_location": "A", "date": "2024-01-02", "price": 280},
    
    # Plan 6: A→D (2023-12-28) and D→A (2024-01-01)
    {"from_location": "A", "to_location": "D", "date": "2023-12-28", "price": 250},
    {"from_location": "D", "to_location": "A", "date": "2024-01-01", "price": 290},
    
    # Plan 7: B→C (2023-11-13) and C→B (2024-01-05)
    {"from_location": "B", "to_location": "C", "date": "2023-11-13", "price": 300},
    {"from_location": "C", "to_location": "B", "date": "2024-01-05", "price": 300},
    
    # Plan 8: B→D (2023-12-06) and D→B (2024-01-01)
    {"from_location": "B", "to_location": "D", "date": "2023-12-06", "price": 250},
    {"from_location": "D", "to_location": "B", "date": "2024-01-01", "price": 270},
    
    # Plan 9: D→C (2024-01-02) and C→D (2024-01-05)
    {"from_location": "D", "to_location": "C", "date": "2024-01-02", "price": 380},
    {"from_location": "C", "to_location": "D", "date": "2024-01-05", "price": 350},
    
    # Plan 10: C→B (2024-01-05) and B→C (2024-01-07)
    # Note: C→B 2024-01-05 already exists for Plan 7 return, reuse it for Plan 10 outbound
    {"from_location": "B", "to_location": "C", "date": "2024-01-07", "price": 320},
    
    # Extra flights (for variety, not strictly required)
    {"from_location": "E", "to_location": "B", "date": "2023-12-15", "price": 360},
    {"from_location": "E", "to_location": "C", "date": "2023-12-01", "price": 580},
    {"from_location": "A", "to_location": "D", "date": "2023-12-29", "price": 410},
    {"from_location": "A", "to_location": "B", "date": "2023-12-29", "price": 460},
    {"from_location": "D", "to_location": "A", "date": "2023-08-18", "price": 490},
    {"from_location": "C", "to_location": "D", "date": "2023-12-03", "price": 450},
    {"from_location": "D", "to_location": "B", "date": "2023-12-06", "price": 490},
    {"from_location": "B", "to_location": "D", "date": "2024-01-01", "price": 490},
    {"from_location": "B", "to_location": "E", "date": "2024-01-07", "price": 320},
    {"from_location": "E", "to_location": "A", "date": "2024-01-10", "price": 360},
]

HOTELS = [
    {"location": "A", "preferences": ["wifi", "pool"], "price_per_night": 120, "rating": 4},
    {"location": "A", "preferences": ["wifi", "pool"], "price_per_night": 50, "rating": 3},
    {"location": "B", "preferences": ["wifi", "gym"], "price_per_night": 150, "rating": 4},
    {"location": "B", "preferences": ["pool", "gym", "wifi"], "price_per_night": 160, "rating": 5},
    {"location": "C", "preferences": ["pool"], "price_per_night": 100, "rating": 3},
    {"location": "C", "preferences": ["wifi"], "price_per_night": 95, "rating": 4},
    {"location": "C", "preferences": ["wifi", "gym"], "price_per_night": 103, "rating": 4},
    {"location": "C", "preferences": ["wifi", "pool"], "price_per_night": 110, "rating": 5},
    {"location": "D", "preferences": ["wifi"], "price_per_night": 130, "rating": 4},
    {"location": "D", "preferences": ["wifi", "gym"], "price_per_night": 140, "rating": 4},
    {"location": "D", "preferences": ["wifi", "gym", "pool"], "price_per_night": 135, "rating": 5},
    {"location": "E", "preferences": ["wifi", "gym"], "price_per_night": 190, "rating": 4},
    {"location": "E", "preferences": ["wifi", "gym", "pool"], "price_per_night": 120, "rating": 5},
]


# ============== Travel Functions ==============

def find_flights(from_location: str, to_location: str, date: str) -> List[Dict]:
    """Finds flights based on source, destination and date."""
    from_loc = from_location.strip('"').upper()
    to_loc = to_location.strip('"').upper()
    
    return [
        flight for flight in FLIGHTS
        if flight["from_location"].upper() == from_loc
        and flight["to_location"].upper() == to_loc
        and flight["date"] == date
    ]


def book_hotel(location: str, *preferences: str) -> List[Dict]:
    """Books a hotel based on location and preferences."""
    loc = location.strip('"').upper()
    prefs = [p.strip('"').lower() for p in preferences]
    
    suitable_hotels = [
        hotel for hotel in HOTELS
        if hotel["location"].upper() == loc
        and all(pref in hotel["preferences"] for pref in prefs)
    ]
    return suitable_hotels


def budget_calculator(flight_price: float, hotel_price_per_night: float, num_nights: int) -> float:
    """Calculates the total budget for a trip."""
    return flight_price + hotel_price_per_night * num_nights


# ============== Tool Handlers ==============

async def on_find_flights(context: RunContextWrapper, params_str: str) -> Any:
    params = json.loads(params_str)
    from_location = params.get("from_location", "")
    to_location = params.get("to_location", "")
    date = params.get("date", "")
    
    flights = find_flights(from_location, to_location, date)
    return flights


async def on_book_hotel(context: RunContextWrapper, params_str: str) -> Any:
    params = json.loads(params_str)
    location = params.get("location", "")
    preferences = params.get("preferences", [])
    
    hotels = book_hotel(location, *preferences)
    return hotels


async def on_budget_calculator(context: RunContextWrapper, params_str: str) -> Any:
    params = json.loads(params_str)
    flight_price = float(params.get("flight_price", 0))
    hotel_price_per_night = float(params.get("hotel_price_per_night", 0))
    num_nights = int(params.get("num_nights", 0))
    
    budget = budget_calculator(flight_price, hotel_price_per_night, num_nights)
    return str(budget)


async def on_find_min(context: RunContextWrapper, params_str: str) -> Any:
    params = json.loads(params_str)
    values = params.get("values", [])
    if not values:
        return "Error: No values provided"
    return str(min(values))


async def on_find_max(context: RunContextWrapper, params_str: str) -> Any:
    params = json.loads(params_str)
    values = params.get("values", [])
    if not values:
        return "Error: No values provided"
    return str(max(values))


async def on_sum_values(context: RunContextWrapper, params_str: str) -> Any:
    params = json.loads(params_str)
    values = params.get("values", [])
    return str(sum(values))


# ============== Tool Definitions ==============

tool_find_flights = FunctionTool(
    name='local-travel_find_flights',
    description='Finds flights based on origin, destination and date. Returns a list of available flights with prices.',
    params_json_schema={
        "type": "object",
        "properties": {
            "from_location": {
                "type": "string",
                "description": 'The origin location (A, B, C, D, E, or F)',
            },
            "to_location": {
                "type": "string",
                "description": 'The destination location (A, B, C, D, E, or F)',
            },
            "date": {
                "type": "string",
                "description": 'The travel date in YYYY-MM-DD format',
            },
        },
        "required": ["from_location", "to_location", "date"]
    },
    on_invoke_tool=on_find_flights
)

tool_book_hotel = FunctionTool(
    name='local-travel_book_hotel',
    description='Finds hotels at a location with specified preferences. Returns a list of matching hotels.',
    params_json_schema={
        "type": "object",
        "properties": {
            "location": {
                "type": "string",
                "description": 'The hotel location (A, B, C, D, E, or F)',
            },
            "preferences": {
                "type": "array",
                "items": {"type": "string"},
                "description": 'Hotel preferences like "wifi", "pool", "gym"',
            },
        },
        "required": ["location"]
    },
    on_invoke_tool=on_book_hotel
)

tool_budget_calculator = FunctionTool(
    name='local-travel_budget_calculator',
    description='Calculates the total trip budget. Returns flight_price + (hotel_price_per_night * num_nights).',
    params_json_schema={
        "type": "object",
        "properties": {
            "flight_price": {
                "type": "number",
                "description": 'The flight price',
            },
            "hotel_price_per_night": {
                "type": "number",
                "description": 'The nightly hotel rate',
            },
            "num_nights": {
                "type": "integer",
                "description": 'Number of nights staying',
            },
        },
        "required": ["flight_price", "hotel_price_per_night", "num_nights"]
    },
    on_invoke_tool=on_budget_calculator
)

tool_find_min = FunctionTool(
    name='local-travel_find_min',
    description='Finds the minimum value from an array of numbers.',
    params_json_schema={
        "type": "object",
        "properties": {
            "values": {
                "type": "array",
                "items": {"type": "number"},
                "description": 'Array of numbers',
            },
        },
        "required": ["values"]
    },
    on_invoke_tool=on_find_min
)

tool_find_max = FunctionTool(
    name='local-travel_find_max',
    description='Finds the maximum value from an array of numbers.',
    params_json_schema={
        "type": "object",
        "properties": {
            "values": {
                "type": "array",
                "items": {"type": "number"},
                "description": 'Array of numbers',
            },
        },
        "required": ["values"]
    },
    on_invoke_tool=on_find_max
)

tool_sum_values = FunctionTool(
    name='local-travel_sum',
    description='Sums an array of numbers.',
    params_json_schema={
        "type": "object",
        "properties": {
            "values": {
                "type": "array",
                "items": {"type": "number"},
                "description": 'Array of numbers to sum',
            },
        },
        "required": ["values"]
    },
    on_invoke_tool=on_sum_values
)

# Export all tools as a list
travel_tools = [
    tool_find_flights,
    tool_book_hotel,
    tool_budget_calculator,
    tool_find_min,
    tool_find_max,
    tool_sum_values,
]

