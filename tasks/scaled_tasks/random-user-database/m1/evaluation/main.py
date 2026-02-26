#!/usr/bin/env python3
"""Evaluation for random-user-database-m1: 4 nationalities × 4 APIs"""
import json, os, sys, argparse
from typing import Any, Dict, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
from eval_utils import EvalScore, check_for_failures, load_json_file_safe

EXPECTED_CODES = ['US', 'GB', 'DE', 'FR']
EXPECTED_COUNT = 4
REGION_MAP = {"US": "North America", "GB": "Europe", "DE": "Europe", "FR": "Europe", "AU": "Oceania"}
REQUIRED_FIELDS = ['nationality_code', 'users', 'statistics']

def normalize_code(code): return code.upper().strip() if code else ""

def validate_codes(nats):
    if not nats: return 0.0, [], EXPECTED_CODES
    found = set(normalize_code(n.get('nationality_code', n.get('code', ''))) for n in nats)
    matched = found & set(EXPECTED_CODES)
    return len(matched) / len(EXPECTED_CODES), list(matched), list(set(EXPECTED_CODES) - found)

def validate_data(nat):
    code = normalize_code(nat.get('nationality_code', nat.get('code', '')))
    if code not in EXPECTED_CODES: return 0.3, []
    score = 0
    users = nat.get('users', [])
    if isinstance(users, list):
        if len(users) >= 4: score += 0.3
        elif len(users) > 0: score += 0.15
        valid = sum(1 for u in users[:5] if isinstance(u, dict) and u.get('name'))
        if valid >= 3: score += 0.25
    stats = nat.get('statistics', {})
    if isinstance(stats, dict) and (stats.get('gender_distribution') or stats.get('average_age')): score += 0.2
    region = nat.get('region', '')
    if region and REGION_MAP.get(code, '').lower() in region.lower(): score += 0.15
    if nat.get('user_count') == len(users): score += 0.1
    return score, []

def evaluate(workspace, groundtruth_dir):
    score = EvalScore("random-user-database-m1")
    result_file = os.path.join(workspace, "user_database.json")
    
    if not os.path.exists(result_file):
        score.add("output_file", 10, 0, "user_database.json not found")
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
    
    nats = result.get('nationalities', [])
    actual = len(nats) if isinstance(nats, list) else 0
    score.add("count", 15, min(actual/EXPECTED_COUNT, 1.0), f"{actual}/{EXPECTED_COUNT} nationalities")
    
    ratio, matched, _ = validate_codes(nats)
    score.add("codes", 15, ratio, f"{len(matched)}/{EXPECTED_COUNT} codes matched")
    
    valid = sum(1 for n in nats[:EXPECTED_COUNT] if validate_data(n)[0] >= 0.5)
    score.add("data", 20, valid/min(actual, EXPECTED_COUNT) if actual else 0, f"{valid} valid")
    
    quality = sum(sum(1 for f in REQUIRED_FIELDS if n.get(f) is not None)/len(REQUIRED_FIELDS) for n in nats[:EXPECTED_COUNT])
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
