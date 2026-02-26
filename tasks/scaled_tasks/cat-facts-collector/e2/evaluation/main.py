#!/usr/bin/env python3
"""Evaluation for cat-facts-collector-e2: 3 breeds × 3 APIs"""
import json, os, sys, argparse
from typing import Any, Dict, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
from eval_utils import EvalScore, check_for_failures, load_json_file_safe

EXPECTED_BREEDS = ['persian', 'siamese', 'maine coon']
EXPECTED_COUNT = 3
REQUIRED_FIELDS = ['breed_name', 'profile', 'facts', 'encyclopedia_entry']

def validate_breed(breed):
    name = breed.get("breed_name", "").lower()
    score = 0
    if any(eb in name or name in eb for eb in EXPECTED_BREEDS): score += 0.3
    if breed.get('profile'): score += 0.2
    
    if breed.get('facts'): score += 0.2
    if breed.get('encyclopedia_entry'): score += 0.2
    return score, []

def evaluate(workspace, groundtruth_dir):
    score = EvalScore("cat-facts-collector-e2")
    result_file = os.path.join(workspace, "cat_encyclopedia.json")
    
    if not os.path.exists(result_file):
        score.add("output_file", 10, 0, "cat_encyclopedia.json not found")
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
    
    breeds = result.get('breeds', [])
    actual = len(breeds) if isinstance(breeds, list) else 0
    score.add("count", 15, min(actual/EXPECTED_COUNT, 1.0), f"{actual}/{EXPECTED_COUNT} breeds")
    
    found = set(b.get("breed_name", "").lower() for b in breeds)
    matched = sum(1 for eb in EXPECTED_BREEDS if any(eb in f or f in eb for f in found))
    score.add("names", 15, matched/len(EXPECTED_BREEDS), f"{matched}/{len(EXPECTED_BREEDS)} breeds matched")
    
    valid = sum(1 for b in breeds[:EXPECTED_COUNT] if validate_breed(b)[0] >= 0.4)
    score.add("data", 20, valid/min(actual, EXPECTED_COUNT) if actual else 0, f"{valid} valid")
    
    quality = sum(sum(1 for f in REQUIRED_FIELDS if b.get(f) is not None)/len(REQUIRED_FIELDS) for b in breeds[:EXPECTED_COUNT])
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
