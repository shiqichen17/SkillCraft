#!/usr/bin/env python3
"""
Evaluation script for countries-encyclopedia-e2 task (Easy: 3 regions × 3 API calls).
Tools: region, currency, language

Evaluation criteria (Total: 100 points):
1. Output file exists (10 points)
2. Valid JSON format (10 points)
3. No fake data indicators (10 points)
4. Region count (15 points)
5. Region names match (15 points)
6. Currency data quality (20 points)
7. Language data quality (20 points)
"""
import json
import os
import sys
import argparse
from typing import Any, Dict, List, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))

from eval_utils import (
    EvalScore, check_for_failures, load_json_file_safe
)

EXPECTED_REGIONS = ["europe", "asia", "africa"]


def validate_currency_data(region: Dict) -> float:
    currency = region.get("currency_analysis", {})
    if not currency:
        return 0.0
    
    checks = 0
    if currency.get("currency"):
        checks += 1
    if currency.get("countries_using") or currency.get("countries_count"):
        checks += 1
    if currency.get("total_population_using") or currency.get("total_population"):
        checks += 1
    
    return checks / 3


def validate_language_data(region: Dict) -> float:
    language = region.get("language_analysis", {})
    if not language:
        return 0.0
    
    checks = 0
    if language.get("language"):
        checks += 1
    if language.get("countries_speaking") or language.get("countries_count"):
        checks += 1
    if language.get("total_speakers"):
        checks += 1
    
    return checks / 3


def evaluate(workspace: str, groundtruth_dir: str) -> Dict[str, Any]:
    score = EvalScore("countries-encyclopedia-e2")
    result_file = os.path.join(workspace, "countries_economic_linguistic.json")
    expected_count = len(EXPECTED_REGIONS)
    
    if not os.path.exists(result_file):
        score.add("output_file_exists", 10, 0, "countries_economic_linguistic.json not found")
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
    
    regions = result.get("regions", [])
    actual_count = len(regions) if isinstance(regions, list) else 0
    count_ratio = min(actual_count / expected_count, 1.0)
    score.add("region_count", 15, count_ratio, f"{actual_count}/{expected_count} regions")
    
    found_regions = set()
    for region in regions:
        name = region.get("name", "").lower()
        found_regions.add(name)
    
    matched = sum(1 for r in EXPECTED_REGIONS if r in found_regions or any(r in fr for fr in found_regions))
    match_ratio = matched / len(EXPECTED_REGIONS)
    score.add("region_names", 15, match_ratio, f"{matched}/{len(EXPECTED_REGIONS)} regions matched")
    
    currency_scores = []
    for region in regions[:expected_count]:
        currency_scores.append(validate_currency_data(region))
    
    if currency_scores:
        avg_currency = sum(currency_scores) / len(currency_scores)
        score.add("currency_data", 20, avg_currency, f"Currency data: {avg_currency*100:.1f}%")
    else:
        score.add("currency_data", 20, 0, "No currency data")
    
    language_scores = []
    for region in regions[:expected_count]:
        language_scores.append(validate_language_data(region))
    
    if language_scores:
        avg_language = sum(language_scores) / len(language_scores)
        score.add("language_data", 20, avg_language, f"Language data: {avg_language*100:.1f}%")
    else:
        score.add("language_data", 20, 0, "No language data")
    
    return score.get_result()


def main():
    parser = argparse.ArgumentParser(description='Evaluate countries-encyclopedia-e2 task')
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
