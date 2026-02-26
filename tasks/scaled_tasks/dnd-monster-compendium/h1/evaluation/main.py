#!/usr/bin/env python3
"""Evaluation for dnd-monster-compendium-h1: 5 monsters × 5 APIs"""
import json, os, sys, argparse
from typing import Any, Dict, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
from eval_utils import EvalScore, check_for_failures, load_json_file_safe

EXPECTED_INDICES = ['adult-red-dragon', 'kraken', 'aboleth', 'lich', 'tarrasque']
EXPECTED_COUNT = 5
REQUIRED_FIELDS = ['index', 'name', 'threat_rating', 'recommended_party_level', 'challenge_rating', 'xp']

def validate_monster(monster):
    index = monster.get("index", "").lower()
    score = 0
    if index in EXPECTED_INDICES: score += 0.3
    if monster.get("name"): score += 0.15
    if monster.get('challenge_rating') is not None: score += 0.15
    if monster.get('xp') is not None: score += 0.1
    if monster.get("threat_rating"): score += 0.15
    if monster.get("recommended_party_level") is not None: score += 0.15
    return score, []

def evaluate(workspace, groundtruth_dir):
    score = EvalScore("dnd-monster-compendium-h1")
    result_file = os.path.join(workspace, "monster_compendium.json")
    
    if not os.path.exists(result_file):
        score.add("output_file", 10, 0, "monster_compendium.json not found")
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
    
    monsters = result.get('monsters', [])
    actual = len(monsters) if isinstance(monsters, list) else 0
    score.add("count", 15, min(actual/EXPECTED_COUNT, 1.0), f"{actual}/{EXPECTED_COUNT} monsters")
    
    found = set(mo.get("index", "").lower() for mo in monsters)
    matched = sum(1 for ei in EXPECTED_INDICES if ei in found)
    score.add("indices", 15, matched/len(EXPECTED_INDICES), f"{matched}/{len(EXPECTED_INDICES)} indices matched")
    
    valid = sum(1 for mo in monsters[:EXPECTED_COUNT] if validate_monster(mo)[0] >= 0.4)
    score.add("data", 20, valid/min(actual, EXPECTED_COUNT) if actual else 0, f"{valid} valid")
    
    quality = sum(sum(1 for f in REQUIRED_FIELDS if mo.get(f) is not None)/len(REQUIRED_FIELDS) for mo in monsters[:EXPECTED_COUNT])
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
