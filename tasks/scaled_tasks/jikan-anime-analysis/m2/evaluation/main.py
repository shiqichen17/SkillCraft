#!/usr/bin/env python3
"""Evaluation for jikan-anime-analysis-m2: 4 anime × 4 APIs"""
import json, os, sys, argparse
from typing import Any, Dict, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
from eval_utils import EvalScore, check_for_failures, load_json_file_safe

EXPECTED_ANIME = [{"mal_id": 1, "title": "Cowboy Bebop"},
    {"mal_id": 5114, "title": "Fullmetal Alchemist: Brotherhood"},
    {"mal_id": 1535, "title": "Death Note"},
    {"mal_id": 16498, "title": "Attack on Titan"}]
EXPECTED_IDS = set(a["mal_id"] for a in EXPECTED_ANIME)
EXPECTED_COUNT = 4
KNOWN_DATA = {1: {"min_score": 8.0, "max_score": 9.5, "min_episodes": 20, "max_episodes": 30}, 5114: {"min_score": 9.0, "max_score": 10.0, "min_episodes": 60, "max_episodes": 70}, 1535: {"min_score": 8.0, "max_score": 9.5, "min_episodes": 35, "max_episodes": 40}, 16498: {"min_score": 8.0, "max_score": 9.5, "min_episodes": 20, "max_episodes": 30}}
REQUIRED_FIELDS = ['mal_id', 'title', 'quality_score', 'popularity_tier', 'score', 'characters', 'episodes_info', 'recommendations']

def validate_ids(anime_list):
    if not anime_list: return 0.0, [], list(EXPECTED_IDS)
    found = set(a.get('mal_id', a.get('id')) for a in anime_list if isinstance(a.get('mal_id', a.get('id')), int))
    matched = found & EXPECTED_IDS
    return len(matched) / len(EXPECTED_IDS), list(matched), list(EXPECTED_IDS - found)

def validate_data(anime):
    mal_id = anime.get('mal_id', anime.get('id'))
    if mal_id not in KNOWN_DATA: return 0.5, []
    known = KNOWN_DATA[mal_id]
    score = 0
    if anime.get('title'): score += 0.3
    s = anime.get('score')
    if s:
        try:
            if known["min_score"] <= float(s) <= known["max_score"]: score += 0.4
        except: pass
    else: score += 0.2
    if anime.get('quality_score') is not None: score += 0.3
    return score, []

def evaluate(workspace, groundtruth_dir):
    score = EvalScore("jikan-anime-analysis-m2")
    result_file = os.path.join(workspace, "anime_analysis_results.json")
    
    if not os.path.exists(result_file):
        score.add("output_file", 10, 0, "anime_analysis_results.json not found")
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
    
    anime_list = result.get('anime_list', result.get('anime', []))
    actual = len(anime_list) if isinstance(anime_list, list) else 0
    score.add("count", 15, min(actual/EXPECTED_COUNT, 1.0), f"{actual}/{EXPECTED_COUNT} anime")
    
    ratio, matched, _ = validate_ids(anime_list)
    score.add("ids", 15, ratio, f"{len(matched)}/{EXPECTED_COUNT} IDs matched")
    
    valid = sum(1 for a in anime_list[:EXPECTED_COUNT] if validate_data(a)[0] >= 0.5)
    score.add("data", 20, valid/min(actual, EXPECTED_COUNT) if actual else 0, f"{valid} valid")
    
    quality = sum(sum(1 for f in REQUIRED_FIELDS if a.get(f) is not None)/len(REQUIRED_FIELDS) for a in anime_list[:EXPECTED_COUNT])
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
