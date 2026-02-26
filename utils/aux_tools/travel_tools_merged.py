# travel_tools_merged.py
# Merged Travel Planning Tools - 5 tools with large outputs
# Design principle: Tools return structured data, agent just transfers it

import json
import hashlib
import re
from typing import Any, List, Dict
from agents.tool import FunctionTool, RunContextWrapper


# ============== Robust JSON Parsing ==============

def _parse_params_robust(params_str: str) -> Dict:
    """
    Robust JSON parsing that handles common LLM formatting errors:
    - Trailing commas
    - Single quotes instead of double quotes
    - Escaped single quotes (\')
    - Truncated JSON (attempts to complete it)
    - Extra whitespace and newlines
    """
    if not params_str or not params_str.strip():
        return {}
    
    text = params_str.strip()
    
    # Try direct parsing first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # Fix common issues
    fixed = text
    
    # 1. Fix escaped single quotes (\' -> ')
    fixed = fixed.replace("\\'", "'")
    
    # 2. Try to fix truncated JSON by completing brackets
    open_braces = fixed.count('{') - fixed.count('}')
    open_brackets = fixed.count('[') - fixed.count(']')
    
    # Remove trailing incomplete content (after last complete value)
    if open_braces > 0 or open_brackets > 0:
        # Try to find a good truncation point
        # Look for last complete key-value pair
        patterns = [
            r',\s*"[^"]*":\s*(?:"[^"]*"|[\d.]+|true|false|null|\{[^}]*\}|\[[^\]]*\])\s*$',  # ends with complete value
            r',\s*$',  # ends with comma
            r':\s*$',  # ends with colon
            r'"[^"]*$',  # incomplete string
        ]
        
        for pattern in patterns:
            match = re.search(pattern, fixed)
            if match and pattern in [r',\s*$', r':\s*$', r'"[^"]*$']:
                # Remove incomplete trailing content
                fixed = fixed[:match.start()]
                break
    
    # 3. Remove trailing commas before closing brackets/braces
    fixed = re.sub(r',(\s*[}\]])', r'\1', fixed)
    
    # 4. Complete missing brackets/braces
    open_braces = fixed.count('{') - fixed.count('}')
    open_brackets = fixed.count('[') - fixed.count(']')
    
    fixed = fixed + ('}' * open_braces) + (']' * open_brackets)
    
    # Try parsing again
    try:
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass
    
    # 5. Try replacing single quotes with double quotes (careful approach)
    try:
        # Only do this if there are single quotes and no valid JSON
        if "'" in text:
            # Replace single quotes used as string delimiters
            sq_fixed = re.sub(r"'([^']*)'", r'"\1"', text)
            sq_fixed = re.sub(r',(\s*[}\]])', r'\1', sq_fixed)
            return json.loads(sq_fixed)
    except json.JSONDecodeError:
        pass
    
    # 6. Last resort: try to extract key-value pairs manually
    try:
        result = {}
        # Look for common parameter patterns
        patterns = {
            'plan_id': r'"plan_id"\s*:\s*(\d+)',
            'travelers': r'"travelers"\s*:\s*(\d+)',
        }
        for key, pattern in patterns.items():
            match = re.search(pattern, text)
            if match:
                result[key] = int(match.group(1))
        
        # Look for nested objects
        obj_patterns = {
            'trip_info': r'"trip_info"\s*:\s*(\{[^}]+(?:\{[^}]*\}[^}]*)*\})',
            'flights': r'"flights"\s*:\s*(\{[^}]+(?:\{[^}]*\}[^}]*)*\})',
            'hotel': r'"hotel"\s*:\s*(\{[^}]+(?:\{[^}]*\}[^}]*)*\})',
            'budget_analysis': r'"budget_analysis"\s*:\s*(\{[^}]+(?:\{[^}]*\}[^}]*)*\})',
        }
        for key, pattern in obj_patterns.items():
            match = re.search(pattern, text, re.DOTALL)
            if match:
                try:
                    result[key] = json.loads(match.group(1))
                except:
                    result[key] = {}
        
        if result:
            return result
    except:
        pass
    
    # Return empty dict with error info if all parsing fails
    return {"_parse_error": f"Failed to parse JSON: {text[:200]}..."}


# ============== Rich Data Tables (Large Outputs) ==============

DESTINATIONS = {
    "A": {
        "city_name": "Alpha City",
        "country": "Alphaland",
        "currency": "ALD",
        "language": "English",
        "timezone": "UTC+1",
        "best_areas": ["Downtown", "Riverside", "Arts District"],
        "local_cuisine": ["Seafood Platter", "Alpha Stew", "River Fish"],
        "transport_tips": "Metro runs 6am-midnight, taxis affordable",
        "safety_rating": 4.5,
        "tourist_info": {
            "visa_required": False,
            "power_outlets": "Type A/B",
            "emergency_number": "112",
            "tipping_culture": "10-15% expected"
        },
        "weather_by_month": {
            "Jan": {"temp": 5, "rain_prob": 30, "desc": "Cold, occasional snow"},
            "Feb": {"temp": 7, "rain_prob": 25, "desc": "Cold, dry"},
            "Mar": {"temp": 12, "rain_prob": 20, "desc": "Cool, spring beginning"},
            "Apr": {"temp": 16, "rain_prob": 15, "desc": "Mild, pleasant"},
            "May": {"temp": 20, "rain_prob": 10, "desc": "Warm, ideal"},
            "Jun": {"temp": 25, "rain_prob": 5, "desc": "Hot, sunny"},
            "Jul": {"temp": 28, "rain_prob": 5, "desc": "Hot, peak season"},
            "Aug": {"temp": 27, "rain_prob": 10, "desc": "Hot, busy"},
            "Sep": {"temp": 22, "rain_prob": 15, "desc": "Warm, fewer crowds"},
            "Oct": {"temp": 16, "rain_prob": 20, "desc": "Cool, autumn colors"},
            "Nov": {"temp": 10, "rain_prob": 25, "desc": "Cold, quiet"},
            "Dec": {"temp": 6, "rain_prob": 35, "desc": "Cold, festive"}
        },
        "attractions": [
            {"name": "Alpha Tower", "type": "landmark", "rating": 4.5, "entry_fee": 25, "duration_hours": 2, "description": "Iconic 50-floor observation tower with 360° city views"},
            {"name": "Central Park Alpha", "type": "park", "rating": 4.8, "entry_fee": 0, "duration_hours": 3, "description": "200-acre urban park with lakes, gardens, and walking trails"},
            {"name": "Art Museum", "type": "museum", "rating": 4.6, "entry_fee": 15, "duration_hours": 2.5, "description": "World-class collection of modern and classical art"},
            {"name": "Historic District Walking Tour", "type": "tour", "rating": 4.4, "entry_fee": 30, "duration_hours": 3, "description": "Guided tour through 18th century architecture"},
            {"name": "Riverside Dining District", "type": "food", "rating": 4.7, "entry_fee": 0, "duration_hours": 2, "description": "Waterfront restaurants and cafes with local cuisine"}
        ]
    },
    "B": {
        "city_name": "Beta Beach",
        "country": "Betaland",
        "currency": "BTL",
        "language": "Spanish",
        "timezone": "UTC-3",
        "best_areas": ["Beach Front", "Old Town", "Marina"],
        "local_cuisine": ["Grilled Seafood", "Beach BBQ", "Tropical Cocktails"],
        "transport_tips": "Buses frequent, rent scooters for beach hopping",
        "safety_rating": 4.2,
        "tourist_info": {
            "visa_required": False,
            "power_outlets": "Type C/F",
            "emergency_number": "911",
            "tipping_culture": "5-10% optional"
        },
        "weather_by_month": {
            "Jan": {"temp": 28, "rain_prob": 5, "desc": "Hot, perfect beach weather"},
            "Feb": {"temp": 27, "rain_prob": 5, "desc": "Hot, dry season"},
            "Mar": {"temp": 25, "rain_prob": 10, "desc": "Warm, pleasant"},
            "Apr": {"temp": 22, "rain_prob": 15, "desc": "Mild, good for exploring"},
            "May": {"temp": 18, "rain_prob": 20, "desc": "Cool, off-season beginning"},
            "Jun": {"temp": 15, "rain_prob": 30, "desc": "Cool, rainy season"},
            "Jul": {"temp": 14, "rain_prob": 35, "desc": "Cool, winter"},
            "Aug": {"temp": 15, "rain_prob": 30, "desc": "Cool, end of winter"},
            "Sep": {"temp": 18, "rain_prob": 25, "desc": "Warming up"},
            "Oct": {"temp": 22, "rain_prob": 15, "desc": "Pleasant, spring"},
            "Nov": {"temp": 25, "rain_prob": 10, "desc": "Warm, great weather"},
            "Dec": {"temp": 27, "rain_prob": 5, "desc": "Hot, peak season"}
        },
        "attractions": [
            {"name": "Golden Beach", "type": "beach", "rating": 4.9, "entry_fee": 0, "duration_hours": 4, "description": "3km stretch of golden sand with crystal clear water"},
            {"name": "Historic Fort", "type": "landmark", "rating": 4.3, "entry_fee": 10, "duration_hours": 2, "description": "16th century colonial fortress with museum"},
            {"name": "Sunset Point", "type": "viewpoint", "rating": 4.7, "entry_fee": 5, "duration_hours": 1, "description": "Famous cliff viewpoint for spectacular sunsets"},
            {"name": "Marina Cruise", "type": "tour", "rating": 4.5, "entry_fee": 45, "duration_hours": 3, "description": "Boat tour around the marina and coastal islands"},
            {"name": "Old Town Markets", "type": "shopping", "rating": 4.4, "entry_fee": 0, "duration_hours": 2, "description": "Traditional market with local crafts and souvenirs"}
        ]
    },
    "C": {
        "city_name": "Gamma Gardens",
        "country": "Gammastan",
        "currency": "GMS",
        "language": "French",
        "timezone": "UTC+2",
        "best_areas": ["Garden District", "Tech Hub", "University Area"],
        "local_cuisine": ["Garden Salads", "Fusion Cuisine", "Artisan Coffee"],
        "transport_tips": "Excellent tram network, bike-friendly city",
        "safety_rating": 4.7,
        "tourist_info": {
            "visa_required": False,
            "power_outlets": "Type E",
            "emergency_number": "112",
            "tipping_culture": "Round up bills"
        },
        "weather_by_month": {
            "Jan": {"temp": 8, "rain_prob": 25, "desc": "Cold, grey"},
            "Feb": {"temp": 10, "rain_prob": 20, "desc": "Cold, improving"},
            "Mar": {"temp": 14, "rain_prob": 15, "desc": "Spring arriving"},
            "Apr": {"temp": 18, "rain_prob": 10, "desc": "Pleasant, flowers blooming"},
            "May": {"temp": 22, "rain_prob": 5, "desc": "Warm, ideal"},
            "Jun": {"temp": 26, "rain_prob": 10, "desc": "Hot, sunny"},
            "Jul": {"temp": 29, "rain_prob": 15, "desc": "Hot, occasional storms"},
            "Aug": {"temp": 28, "rain_prob": 15, "desc": "Hot, holiday season"},
            "Sep": {"temp": 24, "rain_prob": 10, "desc": "Warm, harvest festivals"},
            "Oct": {"temp": 18, "rain_prob": 15, "desc": "Cool, autumn colors"},
            "Nov": {"temp": 12, "rain_prob": 20, "desc": "Cool, quiet"},
            "Dec": {"temp": 9, "rain_prob": 30, "desc": "Cold, festive markets"}
        },
        "attractions": [
            {"name": "Botanical Gardens", "type": "park", "rating": 4.8, "entry_fee": 12, "duration_hours": 3, "description": "500-acre garden with 10,000+ plant species"},
            {"name": "Science Museum", "type": "museum", "rating": 4.6, "entry_fee": 18, "duration_hours": 3, "description": "Interactive science exhibits and planetarium"},
            {"name": "Night Market", "type": "food", "rating": 4.7, "entry_fee": 0, "duration_hours": 2, "description": "Evening food market with international cuisine"},
            {"name": "University Campus Tour", "type": "tour", "rating": 4.2, "entry_fee": 0, "duration_hours": 1.5, "description": "Historic university grounds with beautiful architecture"},
            {"name": "Tech Innovation Center", "type": "museum", "rating": 4.4, "entry_fee": 20, "duration_hours": 2, "description": "Showcase of cutting-edge technology and startups"}
        ]
    },
    "D": {
        "city_name": "Delta Downtown",
        "country": "Deltaland",
        "currency": "DLT",
        "language": "German",
        "timezone": "UTC+1",
        "best_areas": ["Financial District", "Cultural Quarter", "Foodie Lane"],
        "local_cuisine": ["Gourmet Burgers", "Craft Beer", "Fine Dining"],
        "transport_tips": "Efficient subway, walking friendly downtown",
        "safety_rating": 4.6,
        "tourist_info": {
            "visa_required": False,
            "power_outlets": "Type C/F",
            "emergency_number": "110",
            "tipping_culture": "5-10% for good service"
        },
        "weather_by_month": {
            "Jan": {"temp": 2, "rain_prob": 40, "desc": "Very cold, snowy"},
            "Feb": {"temp": 4, "rain_prob": 35, "desc": "Cold, winter persists"},
            "Mar": {"temp": 9, "rain_prob": 30, "desc": "Cool, spring beginning"},
            "Apr": {"temp": 14, "rain_prob": 20, "desc": "Mild, pleasant"},
            "May": {"temp": 18, "rain_prob": 15, "desc": "Warm, outdoor events"},
            "Jun": {"temp": 22, "rain_prob": 10, "desc": "Warm, festival season"},
            "Jul": {"temp": 25, "rain_prob": 10, "desc": "Hot, peak tourism"},
            "Aug": {"temp": 24, "rain_prob": 15, "desc": "Warm, busy"},
            "Sep": {"temp": 19, "rain_prob": 20, "desc": "Pleasant, wine festivals"},
            "Oct": {"temp": 13, "rain_prob": 25, "desc": "Cool, autumn"},
            "Nov": {"temp": 7, "rain_prob": 35, "desc": "Cold, grey"},
            "Dec": {"temp": 3, "rain_prob": 45, "desc": "Cold, Christmas markets"}
        },
        "attractions": [
            {"name": "Delta Tower", "type": "landmark", "rating": 4.6, "entry_fee": 22, "duration_hours": 2, "description": "Art deco skyscraper with observation deck"},
            {"name": "Opera House", "type": "culture", "rating": 4.9, "entry_fee": 50, "duration_hours": 3, "description": "World-renowned opera and ballet performances"},
            {"name": "Food Street Tour", "type": "food", "rating": 4.8, "entry_fee": 35, "duration_hours": 3, "description": "Guided culinary tour with 5 tastings"},
            {"name": "Financial District Walk", "type": "tour", "rating": 4.1, "entry_fee": 0, "duration_hours": 1.5, "description": "Self-guided tour of historic bank buildings"},
            {"name": "Modern Art Gallery", "type": "museum", "rating": 4.5, "entry_fee": 15, "duration_hours": 2, "description": "Contemporary art from emerging artists"}
        ]
    },
    "E": {
        "city_name": "Epsilon Express",
        "country": "Epsilonia",
        "currency": "EPS",
        "language": "English",
        "timezone": "UTC+0",
        "best_areas": ["Central Station", "Shopping Mall", "Business Park"],
        "local_cuisine": ["Fish and Chips", "Afternoon Tea", "Pub Food"],
        "transport_tips": "Excellent rail connections, buses comprehensive",
        "safety_rating": 4.4,
        "tourist_info": {
            "visa_required": False,
            "power_outlets": "Type G",
            "emergency_number": "999",
            "tipping_culture": "10% in restaurants"
        },
        "weather_by_month": {
            "Jan": {"temp": 6, "rain_prob": 35, "desc": "Cold, grey, drizzly"},
            "Feb": {"temp": 7, "rain_prob": 30, "desc": "Cold, occasional sun"},
            "Mar": {"temp": 10, "rain_prob": 25, "desc": "Cool, spring hints"},
            "Apr": {"temp": 13, "rain_prob": 20, "desc": "Mild, variable"},
            "May": {"temp": 17, "rain_prob": 15, "desc": "Pleasant, flowers"},
            "Jun": {"temp": 20, "rain_prob": 12, "desc": "Warm, long days"},
            "Jul": {"temp": 22, "rain_prob": 10, "desc": "Warmest month"},
            "Aug": {"temp": 21, "rain_prob": 12, "desc": "Warm, holiday time"},
            "Sep": {"temp": 18, "rain_prob": 18, "desc": "Mild, autumn arriving"},
            "Oct": {"temp": 14, "rain_prob": 22, "desc": "Cool, leaves changing"},
            "Nov": {"temp": 9, "rain_prob": 30, "desc": "Cold, dark evenings"},
            "Dec": {"temp": 6, "rain_prob": 40, "desc": "Cold, festive lights"}
        },
        "attractions": [
            {"name": "Grand Station", "type": "landmark", "rating": 4.4, "entry_fee": 0, "duration_hours": 1, "description": "Victorian-era train station with stunning architecture"},
            {"name": "Shopping Center", "type": "shopping", "rating": 4.3, "entry_fee": 0, "duration_hours": 3, "description": "Major shopping destination with 200+ stores"},
            {"name": "City Park", "type": "park", "rating": 4.5, "entry_fee": 0, "duration_hours": 2, "description": "Green oasis in the city center with pond"},
            {"name": "Coffee Culture Tour", "type": "food", "rating": 4.6, "entry_fee": 25, "duration_hours": 2, "description": "Visit specialty coffee roasters and cafes"},
            {"name": "Business District Walk", "type": "tour", "rating": 4.0, "entry_fee": 0, "duration_hours": 1, "description": "Modern architecture and corporate headquarters"}
        ]
    }
}

# Flights database with detailed info
FLIGHTS = {
    # E -> A
    ("E", "A", "2023-12-25"): [
        {"flight_id": "FL001", "price": 450, "departure": "08:30", "arrival": "11:45", "airline": "Alpha Airlines", "aircraft": "A320", "duration": "3h 15m", "class": "Economy", "baggage": "23kg", "meal": True, "stops": 0},
        {"flight_id": "FL002", "price": 520, "departure": "14:00", "arrival": "17:15", "airline": "Epsilon Express", "aircraft": "B737", "duration": "3h 15m", "class": "Economy", "baggage": "23kg", "meal": True, "stops": 0},
    ],
    ("A", "E", "2024-01-10"): [
        {"flight_id": "FL003", "price": 380, "departure": "14:00", "arrival": "17:15", "airline": "Epsilon Express", "aircraft": "B737", "duration": "3h 15m", "class": "Economy", "baggage": "23kg", "meal": False, "stops": 0},
    ],
    # E -> B
    ("E", "B", "2023-11-10"): [
        {"flight_id": "FL004", "price": 350, "departure": "06:00", "arrival": "12:30", "airline": "Beta Air", "aircraft": "A350", "duration": "6h 30m", "class": "Economy", "baggage": "23kg", "meal": True, "stops": 0},
        {"flight_id": "FL005", "price": 165, "departure": "22:00", "arrival": "04:30", "airline": "Budget Wings", "aircraft": "B737", "duration": "6h 30m", "class": "Economy", "baggage": "15kg", "meal": False, "stops": 1},
    ],
    ("B", "E", "2023-12-08"): [
        {"flight_id": "FL006", "price": 470, "departure": "09:00", "arrival": "15:30", "airline": "Beta Air", "aircraft": "A350", "duration": "6h 30m", "class": "Economy", "baggage": "23kg", "meal": True, "stops": 0},
    ],
    # E -> C
    ("E", "C", "2023-10-05"): [
        {"flight_id": "FL007", "price": 600, "departure": "07:00", "arrival": "10:00", "airline": "Gamma Jet", "aircraft": "A321", "duration": "3h", "class": "Economy", "baggage": "23kg", "meal": True, "stops": 0},
    ],
    ("C", "E", "2023-12-03"): [
        {"flight_id": "FL008", "price": 520, "departure": "16:00", "arrival": "19:00", "airline": "Gamma Jet", "aircraft": "A321", "duration": "3h", "class": "Economy", "baggage": "23kg", "meal": False, "stops": 0},
    ],
    # E -> D
    ("E", "D", "2023-08-15"): [
        {"flight_id": "FL009", "price": 400, "departure": "10:00", "arrival": "12:30", "airline": "Delta Wings", "aircraft": "B787", "duration": "2h 30m", "class": "Economy", "baggage": "23kg", "meal": True, "stops": 0},
    ],
    ("D", "E", "2023-08-18"): [
        {"flight_id": "FL010", "price": 420, "departure": "18:00", "arrival": "20:30", "airline": "Delta Wings", "aircraft": "B787", "duration": "2h 30m", "class": "Economy", "baggage": "23kg", "meal": False, "stops": 0},
    ],
    # A -> C
    ("A", "C", "2023-08-20"): [
        {"flight_id": "FL011", "price": 250, "departure": "11:00", "arrival": "13:30", "airline": "Alpha Airlines", "aircraft": "A319", "duration": "2h 30m", "class": "Economy", "baggage": "23kg", "meal": False, "stops": 0},
    ],
    ("C", "A", "2024-01-02"): [
        {"flight_id": "FL012", "price": 280, "departure": "08:00", "arrival": "10:30", "airline": "Gamma Jet", "aircraft": "A321", "duration": "2h 30m", "class": "Economy", "baggage": "23kg", "meal": True, "stops": 0},
    ],
}

# Hotels database with rich details
HOTELS = {
    "A": [
        {"hotel_id": "H001", "name": "Alpha Grand Hotel", "area": "Downtown", "rating": 4.5, "price_per_night": 120,
         "amenities": {"wifi": True, "pool": True, "gym": True, "breakfast": True, "parking": True, "spa": False},
         "room_types": ["Standard", "Deluxe", "Suite"], "check_in": "14:00", "check_out": "11:00",
         "coordinates": {"lat": 40.7128, "lng": -74.0060}, "nearby_metro": "Central Station", "reviews_count": 1250,
         "description": "Elegant 4-star hotel in the heart of downtown with rooftop pool and city views"},
        {"hotel_id": "H002", "name": "Budget Inn Alpha", "area": "Riverside", "rating": 3.5, "price_per_night": 50,
         "amenities": {"wifi": True, "pool": True, "gym": False, "breakfast": False, "parking": False, "spa": False},
         "room_types": ["Standard", "Twin"], "check_in": "15:00", "check_out": "10:00",
         "coordinates": {"lat": 40.7200, "lng": -74.0100}, "nearby_metro": "River Stop", "reviews_count": 380,
         "description": "Affordable option near the river with basic amenities"},
    ],
    "B": [
        {"hotel_id": "H003", "name": "Beach Resort Beta", "area": "Beach Front", "rating": 4.7, "price_per_night": 150,
         "amenities": {"wifi": True, "pool": True, "gym": True, "breakfast": True, "parking": True, "spa": True},
         "room_types": ["Ocean View", "Beach Bungalow", "Suite"], "check_in": "14:00", "check_out": "12:00",
         "coordinates": {"lat": -23.5505, "lng": -46.6333}, "nearby_metro": "Beach Line", "reviews_count": 2100,
         "description": "Luxury beachfront resort with direct beach access and world-class spa"},
        {"hotel_id": "H004", "name": "Marina Hotel", "area": "Marina", "rating": 4.3, "price_per_night": 100,
         "amenities": {"wifi": True, "pool": False, "gym": True, "breakfast": True, "parking": True, "spa": False},
         "room_types": ["Standard", "Marina View"], "check_in": "15:00", "check_out": "11:00",
         "coordinates": {"lat": -23.5600, "lng": -46.6400}, "nearby_metro": "Marina Central", "reviews_count": 890,
         "description": "Modern hotel overlooking the marina with yacht-watching terrace"},
    ],
    "C": [
        {"hotel_id": "H005", "name": "Garden View Hotel", "area": "Garden District", "rating": 4.4, "price_per_night": 100,
         "amenities": {"wifi": True, "pool": True, "gym": False, "breakfast": True, "parking": True, "spa": False},
         "room_types": ["Garden View", "Standard"], "check_in": "14:00", "check_out": "11:00",
         "coordinates": {"lat": 48.8566, "lng": 2.3522}, "nearby_metro": "Garden Metro", "reviews_count": 760,
         "description": "Charming hotel next to the Botanical Gardens with garden-view rooms"},
        {"hotel_id": "H006", "name": "Tech Hub Inn", "area": "Tech Hub", "rating": 4.2, "price_per_night": 85,
         "amenities": {"wifi": True, "pool": False, "gym": True, "breakfast": True, "parking": False, "spa": False},
         "room_types": ["Standard", "Business"], "check_in": "14:00", "check_out": "12:00",
         "coordinates": {"lat": 48.8600, "lng": 2.3550}, "nearby_metro": "Tech Station", "reviews_count": 450,
         "description": "Modern hotel in the innovation district with co-working space"},
    ],
    "D": [
        {"hotel_id": "H007", "name": "Delta Plaza Hotel", "area": "Financial District", "rating": 4.6, "price_per_night": 140,
         "amenities": {"wifi": True, "pool": False, "gym": True, "breakfast": True, "parking": False, "spa": True},
         "room_types": ["Executive", "Suite", "Penthouse"], "check_in": "15:00", "check_out": "12:00",
         "coordinates": {"lat": 52.5200, "lng": 13.4050}, "nearby_metro": "Finance Central", "reviews_count": 1680,
         "description": "Premium business hotel with executive lounge and conference facilities"},
        {"hotel_id": "H008", "name": "Cultural Quarter B&B", "area": "Cultural Quarter", "rating": 4.4, "price_per_night": 90,
         "amenities": {"wifi": True, "pool": False, "gym": False, "breakfast": True, "parking": True, "spa": False},
         "room_types": ["Standard", "Deluxe"], "check_in": "14:00", "check_out": "10:00",
         "coordinates": {"lat": 52.5250, "lng": 13.4100}, "nearby_metro": "Culture Stop", "reviews_count": 520,
         "description": "Boutique B&B near museums and theaters with homemade breakfast"},
    ],
    "E": [
        {"hotel_id": "H009", "name": "Station Grand Hotel", "area": "Central Station", "rating": 4.3, "price_per_night": 130,
         "amenities": {"wifi": True, "pool": False, "gym": True, "breakfast": True, "parking": False, "spa": False},
         "room_types": ["Standard", "Superior", "Suite"], "check_in": "14:00", "check_out": "11:00",
         "coordinates": {"lat": 51.5074, "lng": -0.1278}, "nearby_metro": "Grand Central", "reviews_count": 2340,
         "description": "Historic hotel adjacent to the Grand Station with classic British charm"},
    ],
}


# ============== Tool 1: Get Complete Trip Info ==============

def get_trip_info(destination: str, outbound_date: str, return_date: str) -> Dict:
    """Get comprehensive destination info including weather forecast."""
    dest_upper = destination.strip('"').upper()
    
    if dest_upper not in DESTINATIONS:
        return {"error": f"Destination {destination} not found"}
    
    dest = DESTINATIONS[dest_upper]
    
    # Get weather for travel period
    month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    try:
        start_month = month_names[int(outbound_date.split("-")[1]) - 1]
        weather = dest["weather_by_month"].get(start_month, {"temp": 20, "rain_prob": 20, "desc": "Pleasant"})
    except:
        weather = {"temp": 20, "rain_prob": 20, "desc": "Pleasant"}
    
    # Clothing recommendation
    if weather["temp"] < 10:
        clothing = "Pack warm layers, winter coat, gloves"
    elif weather["temp"] < 20:
        clothing = "Pack light jacket, layers for cooler evenings"
    else:
        clothing = "Pack light clothing, sunscreen, sunglasses"
    
    # Calculate trip duration
    try:
        from datetime import datetime
        start = datetime.strptime(outbound_date, "%Y-%m-%d")
        end = datetime.strptime(return_date, "%Y-%m-%d")
        duration_days = (end - start).days
    except:
        duration_days = 5
    
    # Generate activities suggestion
    activities = []
    for attr in dest["attractions"]:
        activities.append({
            "name": attr["name"],
            "type": attr["type"],
            "duration": f"{attr['duration_hours']}h",
            "cost": f"${attr['entry_fee']}",
            "when": "morning" if attr["type"] in ["park", "museum"] else "afternoon"
        })
    
    return {
        "destination": {
            "code": dest_upper,
            "city": dest["city_name"],
            "country": dest["country"],
            "currency": dest["currency"],
            "language": dest["language"],
            "timezone": dest["timezone"],
            "safety_rating": dest["safety_rating"],
            "safety_grade": "A" if dest["safety_rating"] >= 4.5 else ("B" if dest["safety_rating"] >= 4.0 else "C")
        },
        "travel_info": {
            **dest["tourist_info"],
            "best_time_to_visit": "Spring/Fall" if 10 <= weather["temp"] <= 25 else ("Summer" if weather["temp"] > 25 else "Winter"),
            "local_customs": f"Greeting in {dest['language']}, tipping: {dest['tourist_info'].get('tipping_culture', 'varies')}"
        },
        "trip_dates": {
            "outbound": outbound_date,
            "return": return_date,
            "duration_days": duration_days,
            "month": start_month
        },
        "best_areas": dest["best_areas"],
        "local_cuisine": dest["local_cuisine"],
        "transport_tips": dest["transport_tips"],
        "weather_forecast": {
            "temperature_celsius": weather["temp"],
            "temperature_fahrenheit": round(weather["temp"] * 9/5 + 32),
            "rain_probability_percent": weather["rain_prob"],
            "description": weather["desc"],
            "packing_recommendation": clothing,
            "umbrella_needed": weather["rain_prob"] > 25,
            "sunscreen_needed": weather["temp"] > 22
        },
        "complete_weather_calendar": dest["weather_by_month"],
        "attractions": dest["attractions"],
        "suggested_activities": activities,
        "estimated_daily_expense": {
            "budget": 80,
            "mid_range": 150,
            "luxury": 300,
            "currency": dest["currency"]
        }
    }


async def on_get_trip_info(context: RunContextWrapper, params_str: str) -> Any:
    params = _parse_params_robust(params_str)
    if "_parse_error" in params:
        return {"error": params["_parse_error"]}
    result = get_trip_info(
        params.get("destination", ""),
        params.get("outbound_date", ""),
        params.get("return_date", "")
    )
    return result


tool_get_trip_info = FunctionTool(
    name='local-travel_get_trip_info',
    description='''Get comprehensive destination information including weather forecast, local tips, and top attractions. Call this FIRST for each travel plan.

**Input:** destination (str), outbound_date (str: YYYY-MM-DD), return_date (str: YYYY-MM-DD)

**Returns:** dict:
{
  "destination": {"code": str, "city": str, "country": str, "currency": str, "language": str, "timezone": str, "safety_rating": float, "safety_grade": str},
  "travel_info": {"visa_required": bool, "power_outlets": str, "emergency_number": str, "tipping_culture": str, "best_time_to_visit": str, "local_customs": str},
  "trip_dates": {"outbound": str, "return": str, "duration_days": int, "month": str},
  "best_areas": [str],
  "local_cuisine": [str],
  "transport_tips": str,
  "weather_forecast": {"temperature_celsius": int, "temperature_fahrenheit": int, "rain_probability_percent": int, "description": str, "packing_recommendation": str, "umbrella_needed": bool, "sunscreen_needed": bool},
  "complete_weather_calendar": {...},
  "attractions": [{"name": str, "type": str, "rating": float, "entry_fee": int, "duration_hours": float, "description": str}],
  "suggested_activities": [{"name": str, "type": str, "duration": str, "cost": str, "when": str}],
  "estimated_daily_expense": {"budget": int, "mid_range": int, "luxury": int, "currency": str}
}

On error: {"error": str}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "destination": {"type": "string", "description": "Destination city code (A, B, C, D, or E)"},
            "outbound_date": {"type": "string", "description": "Outbound date YYYY-MM-DD"},
            "return_date": {"type": "string", "description": "Return date YYYY-MM-DD"},
        },
        "required": ["destination", "outbound_date", "return_date"]
    },
    on_invoke_tool=on_get_trip_info
)


# ============== Tool 2: Search All Flights ==============

def search_all_flights(origin: str, destination: str, outbound_date: str, return_date: str) -> Dict:
    """Search for both outbound and return flights."""
    orig = origin.strip('"').upper()
    dest = destination.strip('"').upper()
    
    outbound_key = (orig, dest, outbound_date)
    return_key = (dest, orig, return_date)
    
    outbound_flights = FLIGHTS.get(outbound_key, [])
    return_flights = FLIGHTS.get(return_key, [])
    
    # Find cheapest options
    cheapest_outbound = min(outbound_flights, key=lambda x: x["price"]) if outbound_flights else None
    cheapest_return = min(return_flights, key=lambda x: x["price"]) if return_flights else None
    
    total_flight_cost = 0
    if cheapest_outbound:
        total_flight_cost += cheapest_outbound["price"]
    if cheapest_return:
        total_flight_cost += cheapest_return["price"]
    
    return {
        "route": f"{orig} ↔ {dest}",
        "outbound_options": outbound_flights,
        "return_options": return_flights,
        "recommended": {
            "outbound": cheapest_outbound,
            "return": cheapest_return,
            "total_flight_cost": total_flight_cost
        },
        "booking_tips": "Book 3-4 weeks in advance for best prices"
    }


async def on_search_all_flights(context: RunContextWrapper, params_str: str) -> Any:
    params = _parse_params_robust(params_str)
    if "_parse_error" in params:
        return {"error": params["_parse_error"]}
    result = search_all_flights(
        params.get("origin", ""),
        params.get("destination", ""),
        params.get("outbound_date", ""),
        params.get("return_date", "")
    )
    return result


tool_search_all_flights = FunctionTool(
    name='local-travel_search_flights',
    description='''Search for outbound and return flights. Returns all options and recommends cheapest combination.

**Input:** origin (str), destination (str), outbound_date (str: YYYY-MM-DD), return_date (str: YYYY-MM-DD)

**Returns:** dict:
{
  "route": str,  # e.g., "E ↔ A"
  "outbound_options": [{"flight_id": str, "price": int, "departure": str, "arrival": str, "airline": str, "aircraft": str, "duration": str, "class": str, "baggage": str, "meal": bool, "stops": int}],
  "return_options": [...],
  "recommended": {
    "outbound": {...} | null,
    "return": {...} | null,
    "total_flight_cost": int
  },
  "booking_tips": str
}

On error: {"error": str}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "origin": {"type": "string", "description": "Origin city code"},
            "destination": {"type": "string", "description": "Destination city code"},
            "outbound_date": {"type": "string", "description": "Outbound date YYYY-MM-DD"},
            "return_date": {"type": "string", "description": "Return date YYYY-MM-DD"},
        },
        "required": ["origin", "destination", "outbound_date", "return_date"]
    },
    on_invoke_tool=on_search_all_flights
)


# ============== Tool 3: Search Hotels ==============

def search_hotels(city: str, nights: int, preferences: List[str] = None) -> Dict:
    """Search for hotels matching preferences with detailed analysis."""
    city_upper = city.strip('"').upper()
    prefs = [p.strip('"').lower() for p in (preferences or [])]
    
    city_hotels = HOTELS.get(city_upper, [])
    
    # Score hotels by preferences matched
    scored_hotels = []
    for hotel in city_hotels:
        matched = [p for p in prefs if hotel["amenities"].get(p, False)]
        unmatched = [p for p in prefs if not hotel["amenities"].get(p, False)]
        score = len(matched) / len(prefs) if prefs else 1.0
        
        # Calculate value score (rating per dollar)
        value_score = round(hotel["rating"] / hotel["price_per_night"] * 100, 2)
        
        # Amenities summary
        amenities_list = [k for k, v in hotel["amenities"].items() if v]
        
        scored_hotels.append({
            **hotel,
            "preferences_matched": matched,
            "preferences_unmatched": unmatched,
            "match_score": round(score, 2),
            "total_cost": hotel["price_per_night"] * nights,
            "cost_per_night": hotel["price_per_night"],
            "value_score": value_score,
            "amenities_list": amenities_list,
            "amenities_count": len(amenities_list),
            "location_quality": "excellent" if hotel["area"] in ["Downtown", "Beach Front", "Central Station"] else "good"
        })
    
    # Sort by match score then rating
    scored_hotels.sort(key=lambda x: (-x["match_score"], -x["rating"]))
    
    recommended = scored_hotels[0] if scored_hotels else None
    cheapest = min(scored_hotels, key=lambda x: x["price_per_night"]) if scored_hotels else None
    best_rated = max(scored_hotels, key=lambda x: x["rating"]) if scored_hotels else None
    
    # Calculate price range
    prices = [h["price_per_night"] for h in scored_hotels]
    
    return {
        "city": city_upper,
        "search_criteria": {
            "nights": nights,
            "preferences": prefs,
            "check_date": "as per travel dates"
        },
        "all_options": scored_hotels,
        "recommendations": {
            "best_match": recommended,
            "budget_option": cheapest,
            "luxury_option": best_rated
        },
        "price_analysis": {
            "min_per_night": min(prices) if prices else 0,
            "max_per_night": max(prices) if prices else 0,
            "avg_per_night": round(sum(prices) / len(prices), 2) if prices else 0,
            "total_stay_min": min(prices) * nights if prices else 0,
            "total_stay_max": max(prices) * nights if prices else 0
        },
        "availability_summary": {
            "total_hotels": len(scored_hotels),
            "with_breakfast": sum(1 for h in scored_hotels if h["amenities"].get("breakfast")),
            "with_pool": sum(1 for h in scored_hotels if h["amenities"].get("pool")),
            "with_gym": sum(1 for h in scored_hotels if h["amenities"].get("gym")),
            "avg_rating": round(sum(h["rating"] for h in scored_hotels) / len(scored_hotels), 2) if scored_hotels else 0
        }
    }


async def on_search_hotels(context: RunContextWrapper, params_str: str) -> Any:
    params = _parse_params_robust(params_str)
    if "_parse_error" in params:
        return {"error": params["_parse_error"]}
    result = search_hotels(
        params.get("city", ""),
        params.get("nights", 1),
        params.get("preferences", [])
    )
    return result


tool_search_hotels = FunctionTool(
    name='local-travel_search_hotels',
    description='''Search for hotels matching preferences. Returns all options with match scores and recommends best option.

**Input:** city (str), nights (int), preferences (list[str], optional) - amenities like wifi, pool, gym, breakfast

**Returns:** dict:
{
  "city": str,
  "search_criteria": {"nights": int, "preferences": [str], "check_date": str},
  "all_options": [{"hotel_id": str, "name": str, "area": str, "rating": float, "price_per_night": int, "amenities": {...}, "room_types": [str], "check_in": str, "check_out": str, "coordinates": {"lat": float, "lng": float}, "nearby_metro": str, "reviews_count": int, "description": str, "preferences_matched": [str], "preferences_unmatched": [str], "match_score": float, "total_cost": int, "cost_per_night": int, "value_score": float, "amenities_list": [str], "amenities_count": int, "location_quality": str}],
  "recommendations": {
    "best_match": {...} | null,
    "budget_option": {...} | null,
    "luxury_option": {...} | null
  },
  "price_analysis": {"min_per_night": int, "max_per_night": int, "avg_per_night": float, "total_stay_min": int, "total_stay_max": int},
  "availability_summary": {"total_hotels": int, "with_breakfast": int, "with_pool": int, "with_gym": int, "avg_rating": float}
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "city": {"type": "string", "description": "City code"},
            "nights": {"type": "integer", "description": "Number of nights"},
            "preferences": {"type": "array", "items": {"type": "string"}, "description": "Desired amenities (wifi, pool, gym, breakfast, parking, spa)"},
        },
        "required": ["city", "nights"]
    },
    on_invoke_tool=on_search_hotels
)


# ============== Tool 4: Calculate Budget ==============

def calculate_budget(flight_cost: float, hotel_cost: float, travelers: int, budget: float) -> Dict:
    """Calculate complete budget analysis."""
    total_cost = flight_cost + hotel_cost
    per_person_cost = total_cost / travelers if travelers > 0 else total_cost
    under_budget = total_cost <= budget
    savings = budget - total_cost if under_budget else 0
    overage = total_cost - budget if not under_budget else 0
    
    # Calculate optimization score (0-100)
    budget_score = max(0, min(40, ((budget - total_cost) / budget * 40))) if budget > 0 else 0
    
    return {
        "cost_breakdown": {
            "flights": flight_cost,
            "hotel": hotel_cost,
            "total": total_cost
        },
        "per_person": {
            "total": round(per_person_cost, 2),
            "flights": round(flight_cost / travelers, 2) if travelers > 0 else 0,
            "hotel": round(hotel_cost / travelers, 2) if travelers > 0 else 0
        },
        "budget_analysis": {
            "budget": budget,
            "total_cost": total_cost,
            "under_budget": under_budget,
            "savings": savings,
            "overage": overage,
            "budget_utilization": round((total_cost / budget) * 100, 1) if budget > 0 else 0
        },
        "budget_score": round(budget_score, 1)
    }


async def on_calculate_budget(context: RunContextWrapper, params_str: str) -> Any:
    params = _parse_params_robust(params_str)
    if "_parse_error" in params:
        return {"error": params["_parse_error"]}
    result = calculate_budget(
        params.get("flight_cost", 0),
        params.get("hotel_cost", 0),
        params.get("travelers", 1),
        params.get("budget", 0)
    )
    return result


tool_calculate_budget = FunctionTool(
    name='local-travel_calculate_budget',
    description='''Calculate complete budget analysis including per-person costs and savings.

**Input:** flight_cost (float), hotel_cost (float), travelers (int), budget (float)

**Returns:** dict:
{
  "cost_breakdown": {"flights": float, "hotel": float, "total": float},
  "per_person": {"total": float, "flights": float, "hotel": float},
  "budget_analysis": {"budget": float, "total_cost": float, "under_budget": bool, "savings": float, "overage": float, "budget_utilization": float},
  "budget_score": float
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "flight_cost": {"type": "number", "description": "Total flight cost"},
            "hotel_cost": {"type": "number", "description": "Total hotel cost"},
            "travelers": {"type": "integer", "description": "Number of travelers"},
            "budget": {"type": "number", "description": "Budget limit"},
        },
        "required": ["flight_cost", "hotel_cost", "travelers", "budget"]
    },
    on_invoke_tool=on_calculate_budget
)


# ============== Tool 5: Generate Travel Plan ==============

def generate_travel_plan(
    plan_id: int,
    trip_info: Dict,
    flights: Dict,
    hotel: Dict,
    budget_analysis: Dict,
    travelers: int
) -> Dict:
    """Generate complete travel plan combining all information."""
    
    # Extract key info
    dest = trip_info.get("destination", {})
    weather = trip_info.get("weather_forecast", {})
    recommended_flight = flights.get("recommended", {})
    recommended_hotel = hotel.get("recommended", {})
    budget = budget_analysis.get("budget_analysis", {})
    
    # Calculate optimization score
    budget_score = budget_analysis.get("budget_score", 0)
    hotel_rating = recommended_hotel.get("rating", 3) if recommended_hotel else 3
    rating_score = (hotel_rating / 5) * 30
    match_score = (recommended_hotel.get("match_score", 0) if recommended_hotel else 0) * 30
    optimization_score = round(budget_score + rating_score + match_score)
    
    # Determine recommendation
    if optimization_score >= 80:
        recommendation = "excellent_value"
    elif optimization_score >= 60:
        recommendation = "good_value"
    elif optimization_score >= 40:
        recommendation = "fair_value"
    else:
        recommendation = "poor_value"
    
    # Calculate daily budget
    hotel_per_night = recommended_hotel.get("price_per_night", 0) if recommended_hotel else 0
    trip_dates = trip_info.get("trip_dates", {})
    duration = trip_dates.get("duration_days", 5)
    
    total_cost = budget.get("total_cost", 0)
    daily_accommodation = hotel_per_night
    daily_activities = 50  # Estimated
    daily_food = 40  # Estimated
    
    # Build itinerary suggestions
    attractions = trip_info.get("attractions", [])
    itinerary = []
    for i, attr in enumerate(attractions[:duration]):
        itinerary.append({
            "day": i + 1,
            "activity": attr.get("name", "Free time"),
            "type": attr.get("type", "leisure"),
            "duration": f"{attr.get('duration_hours', 2)}h",
            "cost": attr.get("entry_fee", 0)
        })
    
    return {
        "plan_id": plan_id,
        "plan_summary": {
            "destination": dest.get("city", "Unknown"),
            "country": dest.get("country", "Unknown"),
            "duration_days": duration,
            "travelers": travelers,
            "total_cost": total_cost,
            "status": recommendation
        },
        "destination_details": dest,
        "trip_dates": trip_dates,
        "weather_forecast": weather,
        "flights": {
            "outbound": recommended_flight.get("outbound"),
            "return": recommended_flight.get("return"),
            "total_cost": recommended_flight.get("total_flight_cost", 0),
            "booking_tip": flights.get("booking_tips", "Book early for best prices")
        },
        "accommodation": {
            "hotel_name": recommended_hotel.get("name", "N/A") if recommended_hotel else "N/A",
            "hotel_area": recommended_hotel.get("area", "N/A") if recommended_hotel else "N/A",
            "hotel_rating": recommended_hotel.get("rating", 0) if recommended_hotel else 0,
            "price_per_night": hotel_per_night,
            "total_nights": hotel.get("nights", duration),
            "total_cost": recommended_hotel.get("total_cost", 0) if recommended_hotel else 0,
            "amenities": recommended_hotel.get("amenities_list", []) if recommended_hotel else [],
            "match_score": recommended_hotel.get("match_score", 0) if recommended_hotel else 0
        },
        "budget_analysis": {
            **budget,
            "daily_breakdown": {
                "accommodation": daily_accommodation,
                "activities_estimate": daily_activities,
                "food_estimate": daily_food,
                "total_daily": daily_accommodation + daily_activities + daily_food
            }
        },
        "suggested_itinerary": itinerary,
        "local_tips": {
            "cuisine": trip_info.get("local_cuisine", []),
            "transport": trip_info.get("transport_tips", ""),
            "best_areas": trip_info.get("best_areas", [])
        },
        "packing_list": {
            "essentials": ["Passport", "Travel insurance", "Phone charger", "Adaptor"],
            "weather_specific": weather.get("packing_recommendation", "").split(", ") if weather.get("packing_recommendation") else [],
            "umbrella": weather.get("umbrella_needed", False)
        },
        "scores": {
            "optimization_score": optimization_score,
            "recommendation": recommendation,
            "value_rating": "⭐" * (optimization_score // 20)
        }
    }


async def on_generate_travel_plan(context: RunContextWrapper, params_str: str) -> Any:
    params = _parse_params_robust(params_str)
    if "_parse_error" in params:
        return {"error": params["_parse_error"]}
    result = generate_travel_plan(
        params.get("plan_id", 0),
        params.get("trip_info", {}),
        params.get("flights", {}),
        params.get("hotel", {}),
        params.get("budget_analysis", {}),
        params.get("travelers", 1)
    )
    return result


tool_generate_travel_plan = FunctionTool(
    name='local-travel_generate_plan',
    description='''Generate complete travel plan from all previous tool results. Call this LAST for each travel plan.

**Input:** plan_id (int), trip_info (dict), flights (dict), hotel (dict), budget_analysis (dict), travelers (int)

**Returns:** dict:
{
  "plan_id": int,
  "plan_summary": {"destination": str, "country": str, "duration_days": int, "travelers": int, "total_cost": float, "status": str},
  "destination_details": {...},
  "trip_dates": {...},
  "weather_forecast": {...},
  "flights": {"outbound": {...} | null, "return": {...} | null, "total_cost": float, "booking_tip": str},
  "accommodation": {"hotel_name": str, "hotel_area": str, "hotel_rating": float, "price_per_night": float, "total_nights": int, "total_cost": float, "amenities": [str], "match_score": float},
  "budget_analysis": {..., "daily_breakdown": {"accommodation": float, "activities_estimate": float, "food_estimate": float, "total_daily": float}},
  "suggested_itinerary": [{"day": int, "activity": str, "type": str, "duration": str, "cost": int}],
  "local_tips": {"cuisine": [str], "transport": str, "best_areas": [str]},
  "packing_list": {"essentials": [str], "weather_specific": [str], "umbrella": bool},
  "scores": {"optimization_score": int, "recommendation": str, "value_rating": str}
}''',
    params_json_schema={
        "type": "object",
        "properties": {
            "plan_id": {"type": "integer", "description": "Plan number"},
            "trip_info": {"type": "object", "description": "Result from travel_get_trip_info"},
            "flights": {"type": "object", "description": "Result from travel_search_flights"},
            "hotel": {"type": "object", "description": "Result from travel_search_hotels"},
            "budget_analysis": {"type": "object", "description": "Result from travel_calculate_budget"},
            "travelers": {"type": "integer", "description": "Number of travelers"},
        },
        "required": ["plan_id", "trip_info", "flights", "hotel", "budget_analysis", "travelers"]
    },
    on_invoke_tool=on_generate_travel_plan
)


# ============== Export all tools ==============

travel_tools_merged = [
    tool_get_trip_info,      # Step 1: Get destination + weather
    tool_search_all_flights,  # Step 2: Search flights
    tool_search_hotels,       # Step 3: Search hotels
    tool_calculate_budget,    # Step 4: Calculate budget
    tool_generate_travel_plan, # Step 5: Generate plan
]

