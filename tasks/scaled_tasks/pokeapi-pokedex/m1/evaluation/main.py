#!/usr/bin/env python3
"""Evaluation for pokeapi-pokedex-m1: 4 Pokemon × 4 APIs"""
import json, os, sys, argparse
from typing import Any, Dict, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
from eval_utils import EvalScore, check_for_failures, load_json_file_safe

EXPECTED_IDS = [25, 6, 445, 94]
EXPECTED_COUNT = 4
REQUIRED_FIELDS = ['id', 'name', 'types', 'stats', 'species', 'evolution', 'moves']

def validate_pokemon(poke):
    poke_id = poke.get("id")
    score = 0
    if poke_id in EXPECTED_IDS: score += 0.25
    if poke.get("name"): score += 0.15
    if poke.get('types'): score += 0.15
    if poke.get('stats') or poke.get('stat_total'): score += 0.15
    if poke.get('species'): score += 0.15
    if poke.get('evolution'): score += 0.15
    if poke.get('moves'): score += 0.15
    
    return score, []

def evaluate(workspace, groundtruth_dir):
    score = EvalScore("pokeapi-pokedex-m1")
    result_file = os.path.join(workspace, "pokedex_entries.json")
    
    if not os.path.exists(result_file):
        score.add("output_file", 10, 0, "pokedex_entries.json not found")
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
    
    pokemon = result.get('pokemon', [])
    actual = len(pokemon) if isinstance(pokemon, list) else 0
    score.add("count", 15, min(actual/EXPECTED_COUNT, 1.0), f"{actual}/{EXPECTED_COUNT} Pokemon")
    
    found = set(p.get("id") for p in pokemon if p.get("id"))
    matched = sum(1 for eid in EXPECTED_IDS if eid in found)
    score.add("ids", 15, matched/len(EXPECTED_IDS), f"{matched}/{len(EXPECTED_IDS)} IDs matched")
    
    valid = sum(1 for p in pokemon[:EXPECTED_COUNT] if validate_pokemon(p)[0] >= 0.4)
    score.add("data", 20, valid/min(actual, EXPECTED_COUNT) if actual else 0, f"{valid} valid")
    
    quality = sum(sum(1 for f in REQUIRED_FIELDS if p.get(f) is not None)/len(REQUIRED_FIELDS) for p in pokemon[:EXPECTED_COUNT])
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
