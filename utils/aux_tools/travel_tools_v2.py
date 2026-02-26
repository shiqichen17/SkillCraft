# travel_tools_v2.py
# Enhanced Travel Planning Tools with Multi-Stage Dependencies
# Designed to demonstrate Skill Mode efficiency with 8-step serial workflow

import json
import hashlib
from typing import Any, List, Dict
from agents.tool import FunctionTool, RunContextWrapper


# ============== Enhanced Data Tables ==============

LOC = ["A", "B", "C", "D", "E", "F"]

# Destination Information
DESTINATIONS = {
    "A": {
        "city_name": "Alpha City",
        "country": "Alphaland",
        "best_areas": ["Downtown", "Riverside", "Arts District"],
        "peak_season": ["Jun", "Jul", "Aug"],
        "off_season": ["Jan", "Feb", "Mar"],
        "avg_daily_budget": 150,
        "language": "English",
        "currency": "ALD",
        "timezone": "UTC+1",
        "popular_attractions": ["Alpha Tower", "Central Park", "Art Museum"],
        "local_tips": ["Try the local seafood", "Visit markets on weekends"]
    },
    "B": {
        "city_name": "Beta Beach",
        "country": "Betaland",
        "best_areas": ["Beach Front", "Old Town", "Marina"],
        "peak_season": ["Dec", "Jan", "Feb"],
        "off_season": ["Jun", "Jul", "Aug"],
        "avg_daily_budget": 120,
        "language": "Spanish",
        "currency": "BTL",
        "timezone": "UTC-3",
        "popular_attractions": ["Golden Beach", "Historic Fort", "Sunset Point"],
        "local_tips": ["Beach is best at sunrise", "Bargain at local markets"]
    },
    "C": {
        "city_name": "Gamma Gardens",
        "country": "Gammastan",
        "best_areas": ["Garden District", "Tech Hub", "University Area"],
        "peak_season": ["Apr", "May", "Sep"],
        "off_season": ["Nov", "Dec", "Jan"],
        "avg_daily_budget": 100,
        "language": "French",
        "currency": "GMS",
        "timezone": "UTC+2",
        "popular_attractions": ["Botanical Gardens", "Science Museum", "Night Market"],
        "local_tips": ["Gardens are free on Sundays", "Try street food"]
    },
    "D": {
        "city_name": "Delta Downtown",
        "country": "Deltaland",
        "best_areas": ["Financial District", "Cultural Quarter", "Foodie Lane"],
        "peak_season": ["Mar", "Apr", "Oct"],
        "off_season": ["Jul", "Aug"],
        "avg_daily_budget": 180,
        "language": "German",
        "currency": "DLT",
        "timezone": "UTC+1",
        "popular_attractions": ["Delta Tower", "Opera House", "Food Street"],
        "local_tips": ["Book restaurants in advance", "Public transport is excellent"]
    },
    "E": {
        "city_name": "Epsilon Express",
        "country": "Epsilonia",
        "best_areas": ["Central Station", "Shopping Mall", "Business Park"],
        "peak_season": ["May", "Jun", "Sep"],
        "off_season": ["Dec", "Jan", "Feb"],
        "avg_daily_budget": 130,
        "language": "English",
        "currency": "EPS",
        "timezone": "UTC+0",
        "popular_attractions": ["Grand Station", "Shopping Center", "City Park"],
        "local_tips": ["Great transit hub", "Try the local coffee"]
    }
}

# Weather data (by city and month)
WEATHER_DATA = {
    "A": {"Jan": (5, 30), "Feb": (7, 25), "Mar": (12, 20), "Apr": (16, 15), "May": (20, 10), "Jun": (25, 5), 
          "Jul": (28, 5), "Aug": (27, 10), "Sep": (22, 15), "Oct": (16, 20), "Nov": (10, 25), "Dec": (6, 35)},
    "B": {"Jan": (28, 5), "Feb": (27, 5), "Mar": (25, 10), "Apr": (22, 15), "May": (18, 20), "Jun": (15, 30),
          "Jul": (14, 35), "Aug": (15, 30), "Sep": (18, 25), "Oct": (22, 15), "Nov": (25, 10), "Dec": (27, 5)},
    "C": {"Jan": (8, 25), "Feb": (10, 20), "Mar": (14, 15), "Apr": (18, 10), "May": (22, 5), "Jun": (26, 10),
          "Jul": (29, 15), "Aug": (28, 15), "Sep": (24, 10), "Oct": (18, 15), "Nov": (12, 20), "Dec": (9, 30)},
    "D": {"Jan": (2, 40), "Feb": (4, 35), "Mar": (9, 30), "Apr": (14, 20), "May": (18, 15), "Jun": (22, 10),
          "Jul": (25, 10), "Aug": (24, 15), "Sep": (19, 20), "Oct": (13, 25), "Nov": (7, 35), "Dec": (3, 45)},
    "E": {"Jan": (6, 35), "Feb": (7, 30), "Mar": (10, 25), "Apr": (13, 20), "May": (17, 15), "Jun": (20, 12),
          "Jul": (22, 10), "Aug": (21, 12), "Sep": (18, 18), "Oct": (14, 22), "Nov": (9, 30), "Dec": (6, 40)}
}

# Flights with unique IDs
FLIGHTS = [
    # Plan 1: E→A (2023-12-25) and A→E (2024-01-10)
    {"flight_id": "FL001", "from_location": "E", "to_location": "A", "date": "2023-12-25", "price": 450, 
     "departure_time": "08:30", "arrival_time": "11:45", "airline": "Alpha Airlines", "aircraft": "A320", "terminal": "T1"},
    {"flight_id": "FL002", "from_location": "A", "to_location": "E", "date": "2024-01-10", "price": 380,
     "departure_time": "14:00", "arrival_time": "17:15", "airline": "Epsilon Express", "aircraft": "B737", "terminal": "T2"},
    
    # Plan 2: E→B (2023-11-10) and B→E (2023-12-08)
    {"flight_id": "FL003", "from_location": "E", "to_location": "B", "date": "2023-11-10", "price": 350,
     "departure_time": "06:00", "arrival_time": "12:30", "airline": "Beta Air", "aircraft": "A350", "terminal": "T1"},
    {"flight_id": "FL004", "from_location": "E", "to_location": "B", "date": "2023-11-10", "price": 165,
     "departure_time": "22:00", "arrival_time": "04:30", "airline": "Budget Wings", "aircraft": "B737", "terminal": "T3"},
    {"flight_id": "FL005", "from_location": "B", "to_location": "E", "date": "2023-12-08", "price": 470,
     "departure_time": "09:00", "arrival_time": "15:30", "airline": "Beta Air", "aircraft": "A350", "terminal": "T1"},
    
    # Plan 3: E→C (2023-10-05) and C→E (2023-12-03)
    {"flight_id": "FL006", "from_location": "E", "to_location": "C", "date": "2023-10-05", "price": 600,
     "departure_time": "07:00", "arrival_time": "10:00", "airline": "Gamma Jet", "aircraft": "A321", "terminal": "T2"},
    {"flight_id": "FL007", "from_location": "C", "to_location": "E", "date": "2023-12-03", "price": 520,
     "departure_time": "16:00", "arrival_time": "19:00", "airline": "Gamma Jet", "aircraft": "A321", "terminal": "T1"},
    
    # Plan 4: E→D (2023-08-15) and D→E (2023-08-18)
    {"flight_id": "FL008", "from_location": "E", "to_location": "D", "date": "2023-08-15", "price": 400,
     "departure_time": "10:00", "arrival_time": "12:30", "airline": "Delta Wings", "aircraft": "B787", "terminal": "T1"},
    {"flight_id": "FL009", "from_location": "D", "to_location": "E", "date": "2023-08-18", "price": 420,
     "departure_time": "18:00", "arrival_time": "20:30", "airline": "Delta Wings", "aircraft": "B787", "terminal": "T2"},
    
    # Plan 5: A→C (2023-08-20) and C→A (2024-01-02)
    {"flight_id": "FL010", "from_location": "A", "to_location": "C", "date": "2023-08-20", "price": 250,
     "departure_time": "11:00", "arrival_time": "13:30", "airline": "Alpha Airlines", "aircraft": "A319", "terminal": "T1"},
    {"flight_id": "FL011", "from_location": "C", "to_location": "A", "date": "2024-01-02", "price": 280,
     "departure_time": "08:00", "arrival_time": "10:30", "airline": "Gamma Jet", "aircraft": "A321", "terminal": "T2"},
    
    # Plan 6: A→D (2023-12-28) and D→A (2024-01-01)
    {"flight_id": "FL012", "from_location": "A", "to_location": "D", "date": "2023-12-28", "price": 250,
     "departure_time": "09:00", "arrival_time": "11:00", "airline": "Delta Wings", "aircraft": "A320", "terminal": "T1"},
    {"flight_id": "FL013", "from_location": "D", "to_location": "A", "date": "2024-01-01", "price": 290,
     "departure_time": "15:00", "arrival_time": "17:00", "airline": "Alpha Airlines", "aircraft": "A320", "terminal": "T2"},
    
    # Plan 7: B→C (2023-11-13) and C→B (2024-01-05)
    {"flight_id": "FL014", "from_location": "B", "to_location": "C", "date": "2023-11-13", "price": 300,
     "departure_time": "13:00", "arrival_time": "17:00", "airline": "Beta Air", "aircraft": "B737", "terminal": "T1"},
    {"flight_id": "FL015", "from_location": "C", "to_location": "B", "date": "2024-01-05", "price": 300,
     "departure_time": "10:00", "arrival_time": "14:00", "airline": "Gamma Jet", "aircraft": "A319", "terminal": "T1"},
    
    # Plan 8: B→D (2023-12-06) and D→B (2024-01-01)
    {"flight_id": "FL016", "from_location": "B", "to_location": "D", "date": "2023-12-06", "price": 250,
     "departure_time": "07:00", "arrival_time": "12:00", "airline": "Delta Wings", "aircraft": "A350", "terminal": "T2"},
    {"flight_id": "FL017", "from_location": "D", "to_location": "B", "date": "2024-01-01", "price": 270,
     "departure_time": "20:00", "arrival_time": "01:00", "airline": "Beta Air", "aircraft": "A350", "terminal": "T1"},
    
    # Plan 9: D→C (2024-01-02) and C→D (2024-01-05)
    {"flight_id": "FL018", "from_location": "D", "to_location": "C", "date": "2024-01-02", "price": 380,
     "departure_time": "12:00", "arrival_time": "14:30", "airline": "Gamma Jet", "aircraft": "A320", "terminal": "T1"},
    {"flight_id": "FL019", "from_location": "C", "to_location": "D", "date": "2024-01-05", "price": 350,
     "departure_time": "16:00", "arrival_time": "18:30", "airline": "Delta Wings", "aircraft": "A320", "terminal": "T2"},
    
    # Plan 10: C→B (2024-01-05) and B→C (2024-01-07)
    {"flight_id": "FL020", "from_location": "B", "to_location": "C", "date": "2024-01-07", "price": 320,
     "departure_time": "08:00", "arrival_time": "12:00", "airline": "Beta Air", "aircraft": "B737", "terminal": "T1"},
]

# Hotels with unique IDs and detailed amenities
HOTELS = [
    {"hotel_id": "H001", "location": "A", "name": "Alpha Grand Hotel", "preferences": ["wifi", "pool"], 
     "price_per_night": 120, "rating": 4, "area": "Downtown",
     "amenities": {"wifi": True, "pool": True, "gym": False, "breakfast": True, "parking": True},
     "coordinates": {"lat": 40.7128, "lng": -74.0060}, "nearby_metro": "Central Station"},
    {"hotel_id": "H002", "location": "A", "name": "Budget Inn Alpha", "preferences": ["wifi", "pool"],
     "price_per_night": 50, "rating": 3, "area": "Riverside",
     "amenities": {"wifi": True, "pool": True, "gym": False, "breakfast": False, "parking": False},
     "coordinates": {"lat": 40.7200, "lng": -74.0100}, "nearby_metro": "River Stop"},
    {"hotel_id": "H003", "location": "B", "name": "Beach Resort Beta", "preferences": ["wifi", "gym"],
     "price_per_night": 150, "rating": 4, "area": "Beach Front",
     "amenities": {"wifi": True, "pool": False, "gym": True, "breakfast": True, "parking": True},
     "coordinates": {"lat": -23.5505, "lng": -46.6333}, "nearby_metro": "Beach Line"},
    {"hotel_id": "H004", "location": "B", "name": "Luxury Marina B", "preferences": ["pool", "gym", "wifi"],
     "price_per_night": 160, "rating": 5, "area": "Marina",
     "amenities": {"wifi": True, "pool": True, "gym": True, "breakfast": True, "parking": True},
     "coordinates": {"lat": -23.5600, "lng": -46.6400}, "nearby_metro": "Marina Central"},
    {"hotel_id": "H005", "location": "C", "name": "Garden View C", "preferences": ["pool"],
     "price_per_night": 100, "rating": 3, "area": "Garden District",
     "amenities": {"wifi": False, "pool": True, "gym": False, "breakfast": False, "parking": True},
     "coordinates": {"lat": 48.8566, "lng": 2.3522}, "nearby_metro": "Garden Metro"},
    {"hotel_id": "H006", "location": "C", "name": "Tech Hub Hotel", "preferences": ["wifi"],
     "price_per_night": 95, "rating": 4, "area": "Tech Hub",
     "amenities": {"wifi": True, "pool": False, "gym": False, "breakfast": True, "parking": False},
     "coordinates": {"lat": 48.8600, "lng": 2.3550}, "nearby_metro": "Tech Station"},
    {"hotel_id": "H007", "location": "C", "name": "Fitness Center C", "preferences": ["wifi", "gym"],
     "price_per_night": 103, "rating": 4, "area": "University Area",
     "amenities": {"wifi": True, "pool": False, "gym": True, "breakfast": True, "parking": True},
     "coordinates": {"lat": 48.8650, "lng": 2.3600}, "nearby_metro": "University Stop"},
    {"hotel_id": "H008", "location": "C", "name": "Premium Pool C", "preferences": ["wifi", "pool"],
     "price_per_night": 110, "rating": 5, "area": "Garden District",
     "amenities": {"wifi": True, "pool": True, "gym": False, "breakfast": True, "parking": True},
     "coordinates": {"lat": 48.8580, "lng": 2.3480}, "nearby_metro": "Garden Metro"},
    {"hotel_id": "H009", "location": "D", "name": "Business Hotel D", "preferences": ["wifi"],
     "price_per_night": 130, "rating": 4, "area": "Financial District",
     "amenities": {"wifi": True, "pool": False, "gym": False, "breakfast": True, "parking": False},
     "coordinates": {"lat": 52.5200, "lng": 13.4050}, "nearby_metro": "Finance Central"},
    {"hotel_id": "H010", "location": "D", "name": "Active Stay D", "preferences": ["wifi", "gym"],
     "price_per_night": 140, "rating": 4, "area": "Cultural Quarter",
     "amenities": {"wifi": True, "pool": False, "gym": True, "breakfast": True, "parking": True},
     "coordinates": {"lat": 52.5250, "lng": 13.4100}, "nearby_metro": "Culture Stop"},
    {"hotel_id": "H011", "location": "D", "name": "Grand Delta Resort", "preferences": ["wifi", "gym", "pool"],
     "price_per_night": 135, "rating": 5, "area": "Foodie Lane",
     "amenities": {"wifi": True, "pool": True, "gym": True, "breakfast": True, "parking": True},
     "coordinates": {"lat": 52.5300, "lng": 13.4150}, "nearby_metro": "Food Street"},
    {"hotel_id": "H012", "location": "E", "name": "Station Hotel E", "preferences": ["wifi", "gym"],
     "price_per_night": 190, "rating": 4, "area": "Central Station",
     "amenities": {"wifi": True, "pool": False, "gym": True, "breakfast": True, "parking": False},
     "coordinates": {"lat": 51.5074, "lng": -0.1278}, "nearby_metro": "Grand Central"},
    {"hotel_id": "H013", "location": "E", "name": "Premium E Resort", "preferences": ["wifi", "gym", "pool"],
     "price_per_night": 120, "rating": 5, "area": "Shopping Mall",
     "amenities": {"wifi": True, "pool": True, "gym": True, "breakfast": True, "parking": True},
     "coordinates": {"lat": 51.5100, "lng": -0.1300}, "nearby_metro": "Mall Station"},
]

# Attractions database
ATTRACTIONS = {
    "A": [
        {"name": "Alpha Tower", "type": "landmark", "rating": 4.5, "entry_fee": 25, "duration_hours": 2},
        {"name": "Central Park Alpha", "type": "park", "rating": 4.8, "entry_fee": 0, "duration_hours": 3},
        {"name": "Art Museum", "type": "museum", "rating": 4.6, "entry_fee": 15, "duration_hours": 2.5},
        {"name": "Historic District Walking Tour", "type": "tour", "rating": 4.4, "entry_fee": 30, "duration_hours": 3},
        {"name": "Riverside Dining", "type": "food", "rating": 4.7, "entry_fee": 0, "duration_hours": 2},
    ],
    "B": [
        {"name": "Golden Beach", "type": "beach", "rating": 4.9, "entry_fee": 0, "duration_hours": 4},
        {"name": "Historic Fort", "type": "landmark", "rating": 4.3, "entry_fee": 10, "duration_hours": 2},
        {"name": "Sunset Point", "type": "viewpoint", "rating": 4.7, "entry_fee": 5, "duration_hours": 1},
        {"name": "Marina Cruise", "type": "tour", "rating": 4.5, "entry_fee": 45, "duration_hours": 3},
        {"name": "Old Town Markets", "type": "shopping", "rating": 4.4, "entry_fee": 0, "duration_hours": 2},
    ],
    "C": [
        {"name": "Botanical Gardens", "type": "park", "rating": 4.8, "entry_fee": 12, "duration_hours": 3},
        {"name": "Science Museum", "type": "museum", "rating": 4.6, "entry_fee": 18, "duration_hours": 3},
        {"name": "Night Market", "type": "food", "rating": 4.7, "entry_fee": 0, "duration_hours": 2},
        {"name": "University Campus Tour", "type": "tour", "rating": 4.2, "entry_fee": 0, "duration_hours": 1.5},
        {"name": "Tech Innovation Center", "type": "museum", "rating": 4.4, "entry_fee": 20, "duration_hours": 2},
    ],
    "D": [
        {"name": "Delta Tower", "type": "landmark", "rating": 4.6, "entry_fee": 22, "duration_hours": 2},
        {"name": "Opera House", "type": "culture", "rating": 4.9, "entry_fee": 50, "duration_hours": 3},
        {"name": "Food Street Tour", "type": "food", "rating": 4.8, "entry_fee": 35, "duration_hours": 3},
        {"name": "Financial District Walk", "type": "tour", "rating": 4.1, "entry_fee": 0, "duration_hours": 1.5},
        {"name": "Modern Art Gallery", "type": "museum", "rating": 4.5, "entry_fee": 15, "duration_hours": 2},
    ],
    "E": [
        {"name": "Grand Station", "type": "landmark", "rating": 4.4, "entry_fee": 0, "duration_hours": 1},
        {"name": "Shopping Center", "type": "shopping", "rating": 4.3, "entry_fee": 0, "duration_hours": 3},
        {"name": "City Park", "type": "park", "rating": 4.5, "entry_fee": 0, "duration_hours": 2},
        {"name": "Coffee Culture Tour", "type": "food", "rating": 4.6, "entry_fee": 25, "duration_hours": 2},
        {"name": "Business District Walk", "type": "tour", "rating": 4.0, "entry_fee": 0, "duration_hours": 1},
    ],
}


# ============== Step 1: Get Destination Info ==============

def get_destination_info(city: str) -> Dict:
    """Get comprehensive destination information."""
    city_upper = city.strip('"').upper()
    if city_upper in DESTINATIONS:
        return DESTINATIONS[city_upper]
    return {"error": f"Destination {city} not found"}


async def on_get_destination_info(context: RunContextWrapper, params_str: str) -> Any:
    params = json.loads(params_str)
    city = params.get("city", "")
    result = get_destination_info(city)
    return result


tool_get_destination_info = FunctionTool(
    name='local-travel_get_destination_info',
    description='Get comprehensive destination city information including best areas, seasons, local tips, and attractions. This should be called FIRST before other travel planning steps.',
    params_json_schema={
        "type": "object",
        "properties": {
            "city": {
                "type": "string",
                "description": 'The destination city code (A, B, C, D, or E)',
            },
        },
        "required": ["city"]
    },
    on_invoke_tool=on_get_destination_info
)


# ============== Step 2: Check Weather ==============

def check_weather(city: str, start_date: str, end_date: str) -> Dict:
    """Check weather forecast for the destination."""
    city_upper = city.strip('"').upper()
    
    if city_upper not in WEATHER_DATA:
        return {"error": f"Weather data not available for {city}"}
    
    # Parse month from date
    try:
        month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        start_month_idx = int(start_date.split("-")[1]) - 1
        start_month = month_names[start_month_idx]
        
        temp, rain_prob = WEATHER_DATA[city_upper].get(start_month, (20, 20))
        
        # Determine clothing recommendation
        if temp < 10:
            clothing = "warm_layers"
        elif temp < 20:
            clothing = "light_jacket"
        else:
            clothing = "light_clothing"
        
        # Determine best outdoor days (lower rain = better)
        outdoor_quality = "excellent" if rain_prob < 15 else "good" if rain_prob < 30 else "moderate"
        
        return {
            "city": city_upper,
            "period": f"{start_date} to {end_date}",
            "avg_temperature_celsius": temp,
            "rain_probability_percent": rain_prob,
            "clothing_recommendation": clothing,
            "outdoor_activity_quality": outdoor_quality,
            "pack_umbrella": rain_prob > 25,
            "weather_summary": f"Expect {temp}°C with {rain_prob}% chance of rain"
        }
    except:
        return {"error": "Invalid date format"}


async def on_check_weather(context: RunContextWrapper, params_str: str) -> Any:
    params = json.loads(params_str)
    city = params.get("city", "")
    start_date = params.get("start_date", "")
    end_date = params.get("end_date", "")
    result = check_weather(city, start_date, end_date)
    return result


tool_check_weather = FunctionTool(
    name='local-travel_check_weather',
    description='Check weather forecast for destination during travel dates. Returns temperature, rain probability, and packing recommendations. Requires destination info from step 1.',
    params_json_schema={
        "type": "object",
        "properties": {
            "city": {"type": "string", "description": 'The destination city code'},
            "start_date": {"type": "string", "description": 'Start date in YYYY-MM-DD format'},
            "end_date": {"type": "string", "description": 'End date in YYYY-MM-DD format'},
        },
        "required": ["city", "start_date", "end_date"]
    },
    on_invoke_tool=on_check_weather
)


# ============== Step 3: Search Flights ==============

def search_flights(from_location: str, to_location: str, date: str) -> List[Dict]:
    """Search for available flights."""
    from_loc = from_location.strip('"').upper()
    to_loc = to_location.strip('"').upper()
    
    matching_flights = []
    for flight in FLIGHTS:
        if (flight["from_location"].upper() == from_loc and 
            flight["to_location"].upper() == to_loc and 
            flight["date"] == date):
            # Return summary for search results
            matching_flights.append({
                "flight_id": flight["flight_id"],
                "price": flight["price"],
                "departure_time": flight["departure_time"],
                "arrival_time": flight["arrival_time"],
                "airline": flight["airline"]
            })
    
    return matching_flights


async def on_search_flights(context: RunContextWrapper, params_str: str) -> Any:
    params = json.loads(params_str)
    from_location = params.get("from_location", "")
    to_location = params.get("to_location", "")
    date = params.get("date", "")
    result = search_flights(from_location, to_location, date)
    return result


tool_search_flights = FunctionTool(
    name='local-travel_search_flights',
    description='Search for available flights. Returns a list of flight options with IDs. Use get_flight_details to get full details of the selected flight.',
    params_json_schema={
        "type": "object",
        "properties": {
            "from_location": {"type": "string", "description": 'Origin city code'},
            "to_location": {"type": "string", "description": 'Destination city code'},
            "date": {"type": "string", "description": 'Travel date in YYYY-MM-DD format'},
        },
        "required": ["from_location", "to_location", "date"]
    },
    on_invoke_tool=on_search_flights
)


# ============== Step 4: Get Flight Details ==============

def get_flight_details(flight_id: str) -> Dict:
    """Get detailed information about a specific flight."""
    flight_id_clean = flight_id.strip('"').upper()
    
    for flight in FLIGHTS:
        if flight["flight_id"].upper() == flight_id_clean:
            return {
                "flight_id": flight["flight_id"],
                "route": f"{flight['from_location']} → {flight['to_location']}",
                "date": flight["date"],
                "price": flight["price"],
                "departure_time": flight["departure_time"],
                "arrival_time": flight["arrival_time"],
                "airline": flight["airline"],
                "aircraft": flight["aircraft"],
                "terminal": flight["terminal"],
                "baggage_allowance_kg": 23,
                "meal_included": flight["price"] > 300,
                "class": "Economy"
            }
    
    return {"error": f"Flight {flight_id} not found"}


async def on_get_flight_details(context: RunContextWrapper, params_str: str) -> Any:
    params = json.loads(params_str)
    flight_id = params.get("flight_id", "")
    result = get_flight_details(flight_id)
    return result


tool_get_flight_details = FunctionTool(
    name='local-travel_get_flight_details',
    description='Get detailed information about a specific flight by its ID. Requires flight_id from search_flights step.',
    params_json_schema={
        "type": "object",
        "properties": {
            "flight_id": {"type": "string", "description": 'The flight ID (e.g., FL001)'},
        },
        "required": ["flight_id"]
    },
    on_invoke_tool=on_get_flight_details
)


# ============== Step 5: Search Hotels ==============

def search_hotels(city: str, checkin_date: str, checkout_date: str, preferences: List[str] = None, preferred_area: str = None) -> List[Dict]:
    """Search for hotels matching criteria."""
    city_upper = city.strip('"').upper()
    prefs = [p.strip('"').lower() for p in (preferences or [])]
    
    matching_hotels = []
    for hotel in HOTELS:
        if hotel["location"].upper() != city_upper:
            continue
        
        # Check preferences
        if prefs and not all(pref in hotel["preferences"] for pref in prefs):
            continue
        
        # Check preferred area
        if preferred_area and preferred_area.lower() not in hotel["area"].lower():
            continue
        
        # Return summary for search
        matching_hotels.append({
            "hotel_id": hotel["hotel_id"],
            "name": hotel["name"],
            "price_per_night": hotel["price_per_night"],
            "rating": hotel["rating"],
            "area": hotel["area"]
        })
    
    return matching_hotels


async def on_search_hotels(context: RunContextWrapper, params_str: str) -> Any:
    params = json.loads(params_str)
    city = params.get("city", "")
    checkin_date = params.get("checkin_date", "")
    checkout_date = params.get("checkout_date", "")
    preferences = params.get("preferences", [])
    preferred_area = params.get("preferred_area", None)
    result = search_hotels(city, checkin_date, checkout_date, preferences, preferred_area)
    return result


tool_search_hotels = FunctionTool(
    name='local-travel_search_hotels',
    description='Search for hotels in a city. Can filter by preferences and preferred area. Use destination info to determine best areas. Use get_hotel_amenities to get full details.',
    params_json_schema={
        "type": "object",
        "properties": {
            "city": {"type": "string", "description": 'City code'},
            "checkin_date": {"type": "string", "description": 'Check-in date YYYY-MM-DD'},
            "checkout_date": {"type": "string", "description": 'Check-out date YYYY-MM-DD'},
            "preferences": {"type": "array", "items": {"type": "string"}, "description": 'Desired amenities'},
            "preferred_area": {"type": "string", "description": 'Preferred area from destination info'},
        },
        "required": ["city", "checkin_date", "checkout_date"]
    },
    on_invoke_tool=on_search_hotels
)


# ============== Step 6: Get Hotel Amenities ==============

def get_hotel_amenities(hotel_id: str) -> Dict:
    """Get detailed amenities and location for a specific hotel."""
    hotel_id_clean = hotel_id.strip('"').upper()
    
    for hotel in HOTELS:
        if hotel["hotel_id"].upper() == hotel_id_clean:
            return {
                "hotel_id": hotel["hotel_id"],
                "name": hotel["name"],
                "location": hotel["location"],
                "area": hotel["area"],
                "price_per_night": hotel["price_per_night"],
                "rating": hotel["rating"],
                "amenities": hotel["amenities"],
                "coordinates": hotel["coordinates"],
                "nearby_metro": hotel["nearby_metro"],
                "check_in_time": "14:00",
                "check_out_time": "11:00"
            }
    
    return {"error": f"Hotel {hotel_id} not found"}


async def on_get_hotel_amenities(context: RunContextWrapper, params_str: str) -> Any:
    params = json.loads(params_str)
    hotel_id = params.get("hotel_id", "")
    result = get_hotel_amenities(hotel_id)
    return result


tool_get_hotel_amenities = FunctionTool(
    name='local-travel_get_hotel_amenities',
    description='Get detailed amenities and location information for a specific hotel. Requires hotel_id from search_hotels step.',
    params_json_schema={
        "type": "object",
        "properties": {
            "hotel_id": {"type": "string", "description": 'The hotel ID (e.g., H001)'},
        },
        "required": ["hotel_id"]
    },
    on_invoke_tool=on_get_hotel_amenities
)


# ============== Step 7: Find Nearby Attractions ==============

def find_nearby_attractions(city: str, interests: List[str] = None, max_attractions: int = 5) -> List[Dict]:
    """Find attractions near the hotel based on interests."""
    city_upper = city.strip('"').upper()
    
    if city_upper not in ATTRACTIONS:
        return {"error": f"No attractions found for {city}"}
    
    city_attractions = ATTRACTIONS[city_upper]
    
    # Filter by interests if provided
    if interests:
        interests_lower = [i.strip('"').lower() for i in interests]
        filtered = [a for a in city_attractions if a["type"].lower() in interests_lower or 
                   any(interest in a["name"].lower() for interest in interests_lower)]
        if filtered:
            city_attractions = filtered
    
    # Sort by rating and return top attractions
    sorted_attractions = sorted(city_attractions, key=lambda x: x["rating"], reverse=True)
    
    return sorted_attractions[:max_attractions]


async def on_find_nearby_attractions(context: RunContextWrapper, params_str: str) -> Any:
    params = json.loads(params_str)
    city = params.get("city", "")
    interests = params.get("interests", [])
    max_attractions = params.get("max_attractions", 5)
    result = find_nearby_attractions(city, interests, max_attractions)
    return result


tool_find_nearby_attractions = FunctionTool(
    name='local-travel_find_nearby_attractions',
    description='Find attractions near the hotel location based on interests. Use hotel location from get_hotel_amenities and weather info to plan activities.',
    params_json_schema={
        "type": "object",
        "properties": {
            "city": {"type": "string", "description": 'City code'},
            "interests": {"type": "array", "items": {"type": "string"}, "description": 'Interest types: landmark, museum, park, food, tour, beach, shopping, culture'},
            "max_attractions": {"type": "integer", "description": 'Maximum number of attractions to return (default 5)'},
        },
        "required": ["city"]
    },
    on_invoke_tool=on_find_nearby_attractions
)


# ============== Step 8: Generate Itinerary ==============

def generate_itinerary(plan_id: int, outbound_flight: Dict, return_flight: Dict, hotel: Dict, 
                       attractions: List[Dict], weather: Dict, dest_info: Dict, 
                       travelers: int, budget: float) -> Dict:
    """Generate a complete travel itinerary with cost analysis."""
    
    # Calculate costs
    outbound_price = outbound_flight.get("price", 0)
    return_price = return_flight.get("price", 0)
    total_flight_cost = outbound_price + return_price
    
    hotel_price = hotel.get("price_per_night", 0)
    nights = 3  # Default, could be calculated from dates
    total_hotel_cost = hotel_price * nights
    
    total_cost = total_flight_cost + total_hotel_cost
    per_person_cost = total_cost / travelers if travelers > 0 else total_cost
    
    under_budget = total_cost <= budget
    savings = budget - total_cost if under_budget else 0
    
    # Calculate optimization score
    budget_score = max(0, min(40, ((budget - total_cost) / budget * 40))) if budget > 0 else 0
    rating_score = (hotel.get("rating", 3) / 5) * 30
    pref_score = 30  # Assume all preferences matched if we got here
    optimization_score = round(budget_score + rating_score + pref_score)
    
    # Determine recommendation
    if optimization_score >= 80:
        recommendation = "excellent_value"
    elif optimization_score >= 60:
        recommendation = "good_value"
    elif optimization_score >= 40:
        recommendation = "fair_value"
    else:
        recommendation = "poor_value"
    
    return {
        "plan_id": plan_id,
        "destination": {
            "city": dest_info.get("city_name", "Unknown"),
            "country": dest_info.get("country", "Unknown"),
            "best_area": dest_info.get("best_areas", ["Unknown"])[0] if dest_info.get("best_areas") else "Unknown"
        },
        "weather_summary": weather.get("weather_summary", ""),
        "packing_tips": weather.get("clothing_recommendation", ""),
        "flights": {
            "outbound": {
                "flight_id": outbound_flight.get("flight_id", ""),
                "price": outbound_price,
                "departure": outbound_flight.get("departure_time", ""),
                "arrival": outbound_flight.get("arrival_time", ""),
                "airline": outbound_flight.get("airline", "")
            },
            "return": {
                "flight_id": return_flight.get("flight_id", ""),
                "price": return_price,
                "departure": return_flight.get("departure_time", ""),
                "arrival": return_flight.get("arrival_time", ""),
                "airline": return_flight.get("airline", "")
            },
            "total_flight_cost": total_flight_cost
        },
        "hotel": {
            "hotel_id": hotel.get("hotel_id", ""),
            "name": hotel.get("name", ""),
            "area": hotel.get("area", ""),
            "price_per_night": hotel_price,
            "nights": nights,
            "total_hotel_cost": total_hotel_cost,
            "rating": hotel.get("rating", 0),
            "nearby_metro": hotel.get("nearby_metro", "")
        },
        "recommended_attractions": [
            {"name": a["name"], "type": a["type"], "rating": a["rating"]} 
            for a in attractions[:3]
        ],
        "cost_analysis": {
            "total_cost": total_cost,
            "per_person_cost": round(per_person_cost, 2),
            "budget": budget,
            "under_budget": under_budget,
            "savings": savings
        },
        "optimization_score": optimization_score,
        "recommendation": recommendation,
        "local_tips": dest_info.get("local_tips", [])[:2]
    }


async def on_generate_itinerary(context: RunContextWrapper, params_str: str) -> Any:
    params = json.loads(params_str)
    result = generate_itinerary(
        plan_id=params.get("plan_id", 0),
        outbound_flight=params.get("outbound_flight", {}),
        return_flight=params.get("return_flight", {}),
        hotel=params.get("hotel", {}),
        attractions=params.get("attractions", []),
        weather=params.get("weather", {}),
        dest_info=params.get("dest_info", {}),
        travelers=params.get("travelers", 1),
        budget=params.get("budget", 0)
    )
    return result


tool_generate_itinerary = FunctionTool(
    name='local-travel_generate_itinerary',
    description='Generate a complete travel itinerary with cost analysis. Requires data from ALL previous steps: destination info, weather, flights, hotel, and attractions.',
    params_json_schema={
        "type": "object",
        "properties": {
            "plan_id": {"type": "integer", "description": 'Travel plan ID'},
            "outbound_flight": {"type": "object", "description": 'Outbound flight details from get_flight_details'},
            "return_flight": {"type": "object", "description": 'Return flight details from get_flight_details'},
            "hotel": {"type": "object", "description": 'Hotel details from get_hotel_amenities'},
            "attractions": {"type": "array", "description": 'Attractions from find_nearby_attractions'},
            "weather": {"type": "object", "description": 'Weather info from check_weather'},
            "dest_info": {"type": "object", "description": 'Destination info from get_destination_info'},
            "travelers": {"type": "integer", "description": 'Number of travelers'},
            "budget": {"type": "number", "description": 'Budget limit'},
        },
        "required": ["plan_id", "outbound_flight", "return_flight", "hotel", "travelers", "budget"]
    },
    on_invoke_tool=on_generate_itinerary
)


# ============== Export all v2 tools ==============

travel_tools_v2 = [
    tool_get_destination_info,   # Step 1
    tool_check_weather,          # Step 2
    tool_search_flights,         # Step 3
    tool_get_flight_details,     # Step 4
    tool_search_hotels,          # Step 5
    tool_get_hotel_amenities,    # Step 6
    tool_find_nearby_attractions,# Step 7
    tool_generate_itinerary,     # Step 8
]

