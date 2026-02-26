#!/usr/bin/env python3
"""Evaluation for rickmorty-multiverse-explorer-e3: 3 characters × 3 APIs"""
import json, os, sys, argparse
from typing import Any, Dict, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
from eval_utils import EvalScore, check_for_failures, load_json_file_safe

EXPECTED_CHARS = [{"id": 1, "name": "Rick Sanchez"},
    {"id": 2, "name": "Morty Smith"},
    {"id": 3, "name": "Summer Smith"}]
EXPECTED_IDS = set(c["id"] for c in EXPECTED_CHARS)
EXPECTED_COUNT = 3
KNOWN_DATA = {1: {"name": "Rick Sanchez", "status": "Alive", "species": "Human", "min_episodes": 40}, 2: {"name": "Morty Smith", "status": "Alive", "species": "Human", "min_episodes": 40}, 3: {"name": "Summer Smith", "status": "Alive", "species": "Human", "min_episodes": 30}}
REQUIRED_FIELDS = ['id', 'name', 'significance_score', 'significance_tier', 'origin', 'episodes']

def validate_ids(chars):
    if not chars: return 0.0, [], list(EXPECTED_IDS)
    found = set(c.get('id', c.get('character_id')) for c in chars if isinstance(c.get('id', c.get('character_id')), int))
    matched = found & EXPECTED_IDS
    return len(matched) / len(EXPECTED_IDS), list(matched), list(EXPECTED_IDS - found)

def validate_data(char):
    char_id = char.get('id', char.get('character_id'))
    if char_id not in KNOWN_DATA: return 0.5, []
    known = KNOWN_DATA[char_id]
    score = 0
    if char.get('name') and known["name"].lower() in char.get('name', '').lower(): score += 0.3
    if char.get('status') and char.get('status', '').lower() == known["status"].lower(): score += 0.25
    if char.get('species') and char.get('species', '').lower() == known["species"].lower(): score += 0.25
    if char.get('significance_score') is not None: score += 0.2
    return score, []

def evaluate(workspace, groundtruth_dir):
    score = EvalScore("rickmorty-multiverse-explorer-e3")
    result_file = os.path.join(workspace, "rickmorty_analysis.json")
    
    if not os.path.exists(result_file):
        score.add("output_file", 10, 0, "rickmorty_analysis.json not found")
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
    
    chars = result.get('characters', [])
    actual = len(chars) if isinstance(chars, list) else 0
    score.add("count", 15, min(actual/EXPECTED_COUNT, 1.0), f"{actual}/{EXPECTED_COUNT} characters")
    
    ratio, matched, _ = validate_ids(chars)
    score.add("ids", 15, ratio, f"{len(matched)}/{EXPECTED_COUNT} IDs matched")
    
    valid = sum(1 for c in chars[:EXPECTED_COUNT] if validate_data(c)[0] >= 0.5)
    score.add("data", 20, valid/min(actual, EXPECTED_COUNT) if actual else 0, f"{valid} valid")
    
    quality = sum(sum(1 for f in REQUIRED_FIELDS if c.get(f) is not None)/len(REQUIRED_FIELDS) for c in chars[:EXPECTED_COUNT])
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
