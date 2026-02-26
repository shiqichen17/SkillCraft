#!/usr/bin/env python3
"""
Evaluation script for countries-encyclopedia-e3 task (Easy: 3 countries × 3 API calls).
Tools: details, borders, currency

Evaluation criteria (Total: 100 points):
1. Output file exists (10 points)
2. Valid JSON format (10 points)
3. No fake data indicators (10 points)
4. Country count (15 points)
5. Country names match (15 points)
6. Details data quality (15 points)
7. Border data quality (15 points)
8. Currency data quality (10 points)
"""
import json
import os
import sys
import argparse
from typing import Any, Dict, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))

from eval_utils import (
    EvalScore, check_for_failures, load_json_file_safe
)

EXPECTED_COUNTRIES = ["germany", "china", "brazil"]


def validate_details_data(country: Dict) -> float:
    details = country.get("details", {})
    if not details:
        return 0.0
    
    checks = 0
    if details.get("capital"):
        checks += 1
    if details.get("population") and details.get("population") > 0:
        checks += 1
    if details.get("area") and details.get("area") > 0:
        checks += 1
    if details.get("languages"):
        checks += 1
    
    return checks / 4


def validate_border_data(country: Dict) -> float:
    borders = country.get("border_analysis", {})
    if not borders:
        return 0.0
    
    checks = 0
    if borders.get("border_countries") or borders.get("total_neighbors") is not None:
        checks += 1
    if borders.get("total_neighbors") is not None or borders.get("total_borders") is not None:
        checks += 1
    
    return checks / 2


def validate_currency_data(country: Dict) -> float:
    currency = country.get("currency_analysis", {})
    if not currency:
        return 0.0
    
    checks = 0
    if currency.get("currency"):
        checks += 1
    if currency.get("countries_using") or currency.get("countries_count"):
        checks += 1
    
    return checks / 2


def evaluate(workspace: str, groundtruth_dir: str) -> Dict[str, Any]:
    score = EvalScore("countries-encyclopedia-e3")
    result_file = os.path.join(workspace, "country_profiles.json")
    expected_count = len(EXPECTED_COUNTRIES)
    
    if not os.path.exists(result_file):
        score.add("output_file_exists", 10, 0, "country_profiles.json not found")
        score.add_error("Required output file not found")
        return score.get_result()
    
    score.add("output_file_exists", 10, 1, "Output file found")
    
    try:
        result = load_json_file_safe(result_file)
        score.add("valid_json", 10, 1, "Valid JSON format")
    except json.JSONDecodeError as e:
        score.add("valid_json", 10, 0, f"Invalid JSON: {str(e)}")
        return score.get_result()
    
    has_failure, failure_msg = check_for_failures(result)
    if has_failure:
        score.add("no_failure_indicators", 10, 0, f"Fake data indicator: {failure_msg}")
    else:
        score.add("no_failure_indicators", 10, 1, "No fake data indicators found")
    
    countries = result.get("countries", [])
    actual_count = len(countries) if isinstance(countries, list) else 0
    count_ratio = min(actual_count / expected_count, 1.0)
    score.add("country_count", 15, count_ratio, f"{actual_count}/{expected_count} countries")
    
    found_countries = set()
    for country in countries:
        name = country.get("name", "").lower()
        found_countries.add(name)
    
    matched = sum(1 for c in EXPECTED_COUNTRIES if c in found_countries or any(c in fc for fc in found_countries))
    match_ratio = matched / len(EXPECTED_COUNTRIES)
    score.add("country_names", 15, match_ratio, f"{matched}/{len(EXPECTED_COUNTRIES)} countries matched")
    
    details_scores = []
    for country in countries[:expected_count]:
        details_scores.append(validate_details_data(country))
    
    if details_scores:
        avg_details = sum(details_scores) / len(details_scores)
        score.add("details_data", 15, avg_details, f"Details data: {avg_details*100:.1f}%")
    else:
        score.add("details_data", 15, 0, "No details data")
    
    border_scores = []
    for country in countries[:expected_count]:
        border_scores.append(validate_border_data(country))
    
    if border_scores:
        avg_border = sum(border_scores) / len(border_scores)
        score.add("border_data", 15, avg_border, f"Border data: {avg_border*100:.1f}%")
    else:
        score.add("border_data", 15, 0, "No border data")
    
    currency_scores = []
    for country in countries[:expected_count]:
        currency_scores.append(validate_currency_data(country))
    
    if currency_scores:
        avg_currency = sum(currency_scores) / len(currency_scores)
        score.add("currency_data", 10, avg_currency, f"Currency data: {avg_currency*100:.1f}%")
    else:
        score.add("currency_data", 10, 0, "No currency data")
    
    return score.get_result()


def main():
    parser = argparse.ArgumentParser(description='Evaluate countries-encyclopedia-e3 task')
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


if __name__ == "__main__":
    main()
