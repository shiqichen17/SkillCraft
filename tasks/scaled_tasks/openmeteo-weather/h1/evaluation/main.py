#!/usr/bin/env python3
"""Evaluation for openmeteo-weather-h1: 5 cities × 5 APIs"""
import json, os, sys, argparse
from typing import Any, Dict, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
from eval_utils import EvalScore, check_for_failures, load_json_file_safe

EXPECTED_CITIES = ['tokyo', 'new york', 'london', 'sydney', 'dubai']
EXPECTED_COUNT = 5
REQUIRED_FIELDS = ['name', 'coordinates', 'current', 'hourly_forecast', 'daily_forecast', 'historical']

CITY_COORDS = {
    "tokyo": {"lat": (35.5, 36.0), "lng": (139.5, 140.0)},
    "new york": {"lat": (40.5, 41.0), "lng": (-74.5, -73.5)},
    "london": {"lat": (51.3, 51.7), "lng": (-0.5, 0.2)},
    "sydney": {"lat": (-34.2, -33.5), "lng": (150.8, 151.5)},
    "dubai": {"lat": (24.8, 25.5), "lng": (55.0, 55.6)},
}

def validate_city(city):
    name = city.get("name", "").lower()
    score = 0
    if any(ec in name or name in ec for ec in EXPECTED_CITIES): score += 0.2
    coords = city.get("coordinates", {})
    lat, lng = coords.get("latitude"), coords.get("longitude", coords.get("lng"))
    if lat is not None and lng is not None:
        for c, r in CITY_COORDS.items():
            if c in name:
                if r["lat"][0] <= lat <= r["lat"][1]: score += 0.2
                if r["lng"][0] <= lng <= r["lng"][1]: score += 0.2
                break
        else:
            score += 0.3
    if city.get('current'): score += 0.15
    if city.get('hourly_forecast') or city.get('hourly'): score += 0.15
    if city.get('daily_forecast') or city.get('daily'): score += 0.15
    return score, []

def evaluate(workspace, groundtruth_dir):
    score = EvalScore("openmeteo-weather-h1")
    result_file = os.path.join(workspace, "weather_report.json")
    
    if not os.path.exists(result_file):
        score.add("output_file", 10, 0, "weather_report.json not found")
        return score.get_result()
    score.add("output_file", 10, 1, "Output file found")
    
    try:
        result = load_json_file_safe(result_file)
        score.add("valid_json", 10, 1, "Valid JSON")
    except: 
        score.add("valid_json", 10, 0, "Invalid JSON")
        return score.get_result()
    
    has_fail, msg = check_for_failures(result)
    score.add("no_fake_data", 10, 0 if has_fail else 1, msg if has_fail else "No fake data")
    
    cities = result.get('cities', [])
    actual = len(cities) if isinstance(cities, list) else 0
    score.add("count", 15, min(actual/EXPECTED_COUNT, 1.0), f"{actual}/{EXPECTED_COUNT} cities")
    
    found = set(c.get("name", "").lower() for c in cities)
    matched = sum(1 for ec in EXPECTED_CITIES if ec in found or any(ec in f for f in found))
    score.add("names", 15, matched/len(EXPECTED_CITIES), f"{matched}/{len(EXPECTED_CITIES)} names matched")
    
    valid = sum(1 for c in cities[:EXPECTED_COUNT] if validate_city(c)[0] >= 0.4)
    score.add("data", 20, valid/min(actual, EXPECTED_COUNT) if actual else 0, f"{valid} valid")
    
    quality = sum(sum(1 for f in REQUIRED_FIELDS if c.get(f) is not None)/len(REQUIRED_FIELDS) for c in cities[:EXPECTED_COUNT])
    score.add("completeness", 20, quality/min(actual, EXPECTED_COUNT) if actual else 0, f"Field completeness")
    
    return score.get_result()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--agent_workspace', required=True)
    parser.add_argument('--groundtruth_workspace', required=True)
    parser.add_argument('--res_log_file', help='unused')
    parser.add_argument('--launch_time', help='unused')
    args = parser.parse_args()
    result = evaluate(args.agent_workspace, args.groundtruth_workspace)
    print("=== SCORE_JSON_START ===")
    print(json.dumps(result, indent=2))
    print("=== SCORE_JSON_END ===")
    sys.exit(0 if result["passed"] else (2 if result["status"] == "partial" else 1))

if __name__ == "__main__": main()
