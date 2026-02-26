#!/usr/bin/env python3
"""
Evaluation script for countries-encyclopedia-m2 task (Medium: 4 regions × 4 API calls).
Tools: region, details, borders, language

Evaluation criteria (Total: 100 points):
1. Output file exists (5 points)
2. Valid JSON format (5 points)
3. No fake data indicators (10 points)
4. Region count (10 points)
5. Region names match (10 points)
6. Population verification (20 points)
7. Region data completeness (20 points)
8. Language data (10 points)
9. Global summary validation (10 points)
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

EXPECTED_REGIONS = ["europe", "asia", "africa", "americas"]

REGION_GROUNDTRUTH = {
    "europe": {
        "country_count_range": (40, 55),
        "population_range": (700_000_000, 800_000_000),
    },
    "asia": {
        "country_count_range": (45, 55),
        "population_range": (4_500_000_000, 5_000_000_000),
    },
    "africa": {
        "country_count_range": (50, 60),
        "population_range": (1_300_000_000, 1_600_000_000),
    },
    "americas": {
        "country_count_range": (30, 40),
        "population_range": (900_000_000, 1_100_000_000),
    },
}


def verify_region_data(region: Dict) -> Tuple[float, List[str]]:
    name = region.get("name", "").lower()
    errors = []
    
    matched_region = None
    for known_region in REGION_GROUNDTRUTH:
        if known_region in name or name in known_region:
            matched_region = known_region
            break
    
    if not matched_region:
        return 1.0, []
    
    gt = REGION_GROUNDTRUTH[matched_region]
    checks_passed = 0
    checks_total = 2
    
    summary = region.get("summary", {})
    
    country_count = summary.get("country_count", 0)
    min_c, max_c = gt["country_count_range"]
    if min_c <= country_count <= max_c:
        checks_passed += 1
    elif country_count > 0:
        checks_passed += 0.3
    
    population = summary.get("total_population", 0)
    min_p, max_p = gt["population_range"]
    if min_p * 0.8 <= population <= max_p * 1.2:
        checks_passed += 1
    elif population > 0:
        checks_passed += 0.3
    
    return checks_passed / checks_total, errors


def validate_region_data(region: Dict) -> Tuple[bool, List[str]]:
    errors = []
    
    summary = region.get("summary", {})
    if not summary.get("country_count"):
        errors.append("Missing country count")
    if not summary.get("total_population"):
        errors.append("Missing population")
    
    top_countries = region.get("top_countries", [])
    if len(top_countries) < 1:
        errors.append("Missing top countries")
    
    if not region.get("border_analysis"):
        errors.append("Missing border analysis")
    
    if not region.get("language_analysis"):
        errors.append("Missing language analysis")
    
    return len(errors) == 0, errors


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
    score = EvalScore("countries-encyclopedia-m2")
    result_file = os.path.join(workspace, "countries_encyclopedia_linguistic.json")
    expected_count = len(EXPECTED_REGIONS)
    
    if not os.path.exists(result_file):
        score.add("output_file_exists", 5, 0, "countries_encyclopedia_linguistic.json not found")
        score.add_error("Required output file not found")
        return score.get_result()
    
    score.add("output_file_exists", 5, 1, "Output file found")
    
    try:
        result = load_json_file_safe(result_file)
        score.add("valid_json", 5, 1, "Valid JSON format")
    except json.JSONDecodeError as e:
        score.add("valid_json", 5, 0, f"Invalid JSON: {str(e)}")
        return score.get_result()
    
    has_failure, failure_msg = check_for_failures(result)
    if has_failure:
        score.add("no_failure_indicators", 10, 0, f"Fake data indicator: {failure_msg}")
    else:
        score.add("no_failure_indicators", 10, 1, "No fake data indicators found")
    
    regions = result.get("regions", [])
    actual_count = len(regions) if isinstance(regions, list) else 0
    count_ratio = min(actual_count / expected_count, 1.0)
    score.add("region_count", 10, count_ratio, f"{actual_count}/{expected_count} regions")
    
    found_regions = set()
    for region in regions:
        name = region.get("name", "").lower()
        found_regions.add(name)
    
    matched = sum(1 for r in EXPECTED_REGIONS if r in found_regions or any(r in fr for fr in found_regions))
    match_ratio = matched / len(EXPECTED_REGIONS)
    score.add("region_names", 10, match_ratio, f"{matched}/{len(EXPECTED_REGIONS)} regions matched")
    
    pop_scores = []
    for region in regions:
        pop_score, _ = verify_region_data(region)
        pop_scores.append(pop_score)
    
    if pop_scores:
        avg_pop = sum(pop_scores) / len(pop_scores)
        score.add("population_verification", 20, avg_pop, f"Data verification: {avg_pop*100:.1f}%")
    else:
        score.add("population_verification", 20, 0, "No regions to verify")
    
    valid_regions = 0
    for region in regions[:expected_count]:
        is_valid, _ = validate_region_data(region)
        if is_valid:
            valid_regions += 1
    
    if actual_count > 0:
        score.add("data_completeness", 20, valid_regions / min(actual_count, expected_count),
                  f"{valid_regions}/{min(actual_count, expected_count)} regions complete")
    else:
        score.add("data_completeness", 20, 0, "No regions to validate")
    
    language_scores = []
    for region in regions[:expected_count]:
        language_scores.append(validate_language_data(region))
    
    if language_scores:
        avg_language = sum(language_scores) / len(language_scores)
        score.add("language_data", 10, avg_language, f"Language data: {avg_language*100:.1f}%")
    else:
        score.add("language_data", 10, 0, "No language data")
    
    summary = result.get("global_summary", {})
    summary_checks = 0
    summary_total = 4
    
    if summary.get("total_regions") == actual_count:
        summary_checks += 1
    if summary.get("total_countries", 0) > 100:
        summary_checks += 1
    if summary.get("most_spoken_language"):
        summary_checks += 1
    if summary.get("total_world_population", 0) > 1_000_000_000 or summary.get("largest_region"):
        summary_checks += 1
    
    score.add("global_summary", 10, summary_checks / summary_total,
              f"Summary: {summary_checks}/{summary_total} checks passed")
    
    return score.get_result()


def main():
    parser = argparse.ArgumentParser(description='Evaluate countries-encyclopedia-m2 task')
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
