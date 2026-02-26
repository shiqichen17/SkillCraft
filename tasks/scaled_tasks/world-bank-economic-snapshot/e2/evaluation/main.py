#!/usr/bin/env python3
"""Evaluation for world-bank-economic-snapshot-e2: 3 countries × 3 APIs"""
import json, os, sys, argparse
from typing import Any, Dict, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
from eval_utils import EvalScore, check_for_failures, load_json_file_safe

EXPECTED_CODES = ['US', 'CHN', 'JPN']
EXPECTED_COUNT = 3
REQUIRED_FIELDS = ['country_code', 'country_name', 'economic_power_rank', 'development_tier', 'economic_indicators']

def validate_economy(econ):
    code = econ.get("country_code", "").upper()
    score = 0
    if code in EXPECTED_CODES: score += 0.25
    if econ.get("country_name"): score += 0.15
    if econ.get("economic_power_rank") is not None: score += 0.2
    if econ.get("development_tier"): score += 0.2
    if econ.get('economic_indicators'): score += 0.2
    return score, []

def evaluate(workspace, groundtruth_dir):
    score = EvalScore("world-bank-economic-snapshot-e2")
    result_file = os.path.join(workspace, "economic_snapshot.json")
    
    if not os.path.exists(result_file):
        score.add("output_file", 10, 0, "economic_snapshot.json not found")
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
    
    economies = result.get('economies', [])
    actual = len(economies) if isinstance(economies, list) else 0
    score.add("count", 15, min(actual/EXPECTED_COUNT, 1.0), f"{actual}/{EXPECTED_COUNT} economies")
    
    found = set(e.get("country_code", "").upper() for e in economies)
    matched = sum(1 for ec in EXPECTED_CODES if ec in found)
    score.add("codes", 15, matched/len(EXPECTED_CODES), f"{matched}/{len(EXPECTED_CODES)} codes matched")
    
    valid = sum(1 for e in economies[:EXPECTED_COUNT] if validate_economy(e)[0] >= 0.4)
    score.add("data", 20, valid/min(actual, EXPECTED_COUNT) if actual else 0, f"{valid} valid")
    
    quality = sum(sum(1 for f in REQUIRED_FIELDS if e.get(f) is not None)/len(REQUIRED_FIELDS) for e in economies[:EXPECTED_COUNT])
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
