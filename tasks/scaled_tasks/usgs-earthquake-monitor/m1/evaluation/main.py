#!/usr/bin/env python3
"""Evaluation for usgs-earthquake-monitor-m1: 4 regions × 4 APIs"""
import json, os, sys, argparse
from typing import Any, Dict, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
from eval_utils import EvalScore, check_for_failures, load_json_file_safe

EXPECTED_REGIONS = ['tokyo, japan', 'los angeles, usa', 'jakarta, indonesia', 'santiago, chile']
EXPECTED_COUNT = 4
REQUIRED_FIELDS = ['name', 'coordinates', 'risk_level', 'earthquakes', 'depth_analysis', 'statistics']

def validate_region(region):
    name = region.get("name", "").lower()
    score = 0
    if any(er in name or name in er for er in EXPECTED_REGIONS): score += 0.3
    coords = region.get("coordinates", {})
    if coords.get("latitude") is not None and coords.get("longitude") is not None: score += 0.2
    if region.get("risk_level"): score += 0.2
    if region.get('earthquakes'): score += 0.15
    if region.get('depth_analysis'): score += 0.15
    return score, []

def evaluate(workspace, groundtruth_dir):
    score = EvalScore("usgs-earthquake-monitor-m1")
    result_file = os.path.join(workspace, "earthquake_analysis_results.json")
    
    if not os.path.exists(result_file):
        score.add("output_file", 10, 0, "earthquake_analysis_results.json not found")
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
    
    regions = result.get('regions', [])
    actual = len(regions) if isinstance(regions, list) else 0
    score.add("count", 15, min(actual/EXPECTED_COUNT, 1.0), f"{actual}/{EXPECTED_COUNT} regions")
    
    found = set(r.get("name", "").lower() for r in regions)
    matched = sum(1 for er in EXPECTED_REGIONS if any(er in f or f in er for f in found))
    score.add("names", 15, matched/len(EXPECTED_REGIONS), f"{matched}/{len(EXPECTED_REGIONS)} names matched")
    
    valid = sum(1 for r in regions[:EXPECTED_COUNT] if validate_region(r)[0] >= 0.4)
    score.add("data", 20, valid/min(actual, EXPECTED_COUNT) if actual else 0, f"{valid} valid")
    
    quality = sum(sum(1 for f in REQUIRED_FIELDS if r.get(f) is not None)/len(REQUIRED_FIELDS) for r in regions[:EXPECTED_COUNT])
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
