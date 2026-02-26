#!/usr/bin/env python3
"""Evaluation for cocktail-menu-generator-e3: 3 cocktails × 3 APIs"""
import json, os, sys, argparse
from typing import Any, Dict, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
from eval_utils import EvalScore, check_for_failures, load_json_file_safe

EXPECTED_NAMES = ['margarita', 'mojito', 'old fashioned']
EXPECTED_COUNT = 3
REQUIRED_FIELDS = ['name', 'complexity_rating', 'estimated_prep_time_min', 'category', 'glass', 'similar_cocktails']

def validate_cocktail(cocktail):
    name = cocktail.get("name", "").lower()
    score = 0
    if any(en in name or name in en for en in EXPECTED_NAMES): score += 0.25
    if cocktail.get('category'): score += 0.15
    if cocktail.get('glass'): score += 0.1
    if cocktail.get("complexity_rating"): score += 0.2
    if cocktail.get("estimated_prep_time_min") is not None: score += 0.15
    if cocktail.get("ingredient_count") is not None: score += 0.15
    return score, []

def evaluate(workspace, groundtruth_dir):
    score = EvalScore("cocktail-menu-generator-e3")
    result_file = os.path.join(workspace, "cocktail_menu.json")
    
    if not os.path.exists(result_file):
        score.add("output_file", 10, 0, "cocktail_menu.json not found")
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
    
    cocktails = result.get('cocktails', [])
    actual = len(cocktails) if isinstance(cocktails, list) else 0
    score.add("count", 15, min(actual/EXPECTED_COUNT, 1.0), f"{actual}/{EXPECTED_COUNT} cocktails")
    
    found = set(c.get("name", "").lower() for c in cocktails)
    matched = sum(1 for en in EXPECTED_NAMES if any(en in f or f in en for f in found))
    score.add("names", 15, matched/len(EXPECTED_NAMES), f"{matched}/{len(EXPECTED_NAMES)} names matched")
    
    valid = sum(1 for c in cocktails[:EXPECTED_COUNT] if validate_cocktail(c)[0] >= 0.4)
    score.add("data", 20, valid/min(actual, EXPECTED_COUNT) if actual else 0, f"{valid} valid")
    
    quality = sum(sum(1 for f in REQUIRED_FIELDS if c.get(f) is not None)/len(REQUIRED_FIELDS) for c in cocktails[:EXPECTED_COUNT])
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
