#!/usr/bin/env python3
"""
Evaluation script for tvmaze-series-analyzer-e3 task.
3 shows × 3 API calls = 9 total calls.
"""
import json
import os
import sys
import argparse
from typing import Any, Dict, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from eval_utils import EvalScore, check_for_failures, load_json_file_safe

EXPECTED_SHOWS = [
    {"id": 169, "title": "Breaking Bad"},
    {"id": 82, "title": "Game of Thrones"},
    {"id": 526, "title": "The Office"}
]

EXPECTED_SHOW_IDS = set(s["id"] for s in EXPECTED_SHOWS)
EXPECTED_COUNT = 3

KNOWN_DATA = {
    169: {"name": "Breaking Bad", "min_rating": 9.0, "max_rating": 10.0, "min_episodes": 60, "max_episodes": 65},82: {"name": "Game of Thrones", "min_rating": 8.5, "max_rating": 10.0, "min_episodes": 70, "max_episodes": 75},526: {"name": "The Office", "min_rating": 8.0, "max_rating": 9.5, "min_episodes": 180, "max_episodes": 210}
}

REQUIRED_FIELDS = ['id', 'name', 'marathon_hours', 'binge_rating', 'seasons', 'cast', 'crew']


def validate_show_ids(shows: List[Dict]) -> tuple:
    if not shows:
        return 0.0, [], list(EXPECTED_SHOW_IDS)
    found_ids = set()
    for show in shows:
        show_id = show.get('id', show.get('show_id', show.get('tvmaze_id')))
        if isinstance(show_id, int):
            found_ids.add(show_id)
    matched = found_ids & EXPECTED_SHOW_IDS
    missing = list(EXPECTED_SHOW_IDS - found_ids)
    return len(matched) / len(EXPECTED_SHOW_IDS), list(matched), missing


def validate_summary_format(show: Dict) -> tuple:
    score = 0
    total = 0
    errors = []
    
    # Episodes not required
    
    
    
    
    
    
    # Check cast
    cast = show.get('cast', {})
    if isinstance(cast, dict):
        if cast.get('total_count') is not None or cast.get('total') is not None:
            score += 1
        total += 1
    
    # Check marathon_hours and binge_rating
    if show.get('marathon_hours') is not None and show.get('binge_rating') is not None:
        score += 1
    total += 1
    
    return score / max(total, 1), errors


def validate_show_data(show: Dict) -> tuple:
    show_id = show.get('id', show.get('show_id', show.get('tvmaze_id')))
    if show_id not in KNOWN_DATA:
        return 0.5, ["Unknown show ID"]
    known = KNOWN_DATA[show_id]
    score_val = 0
    
    name = show.get('name', show.get('title'))
    if name and known["name"].lower() in name.lower():
        score_val += 0.5
    
    rating = show.get('rating')
    if rating is not None:
        try:
            if known["min_rating"] <= float(rating) <= known["max_rating"]:
                score_val += 0.5
        except:
            pass
    else:
        score_val += 0.25  # Rating not always required
    
    return score_val, []


def evaluate(workspace: str, groundtruth_dir: str) -> Dict[str, Any]:
    score = EvalScore("tvmaze-series-analyzer-e3")
    result_file = os.path.join(workspace, "tv_series_analysis.json")
    
    # Check 1: Output file exists (10 points)
    if not os.path.exists(result_file):
        score.add("output_file_exists", 10, 0, "tv_series_analysis.json not found")
        score.add_error("Required output file not found")
        return score.get_result()
    score.add("output_file_exists", 10, 1, "Output file found")
    
    # Check 2: Valid JSON (10 points)
    try:
        result = load_json_file_safe(result_file)
        score.add("valid_json", 10, 1, "Valid JSON format")
    except json.JSONDecodeError as e:
        score.add("valid_json", 10, 0, f"Invalid JSON: {str(e)}")
        return score.get_result()
    
    # Check 3: No fake data (10 points)
    has_failure, failure_msg = check_for_failures(result)
    if has_failure:
        score.add("no_fake_data", 10, 0, f"Fake data: {failure_msg}")
    else:
        score.add("no_fake_data", 10, 1, "No fake data found")
    
    # Check 4: Show count (15 points)
    shows = result.get('shows', result.get('series', []))
    actual_count = len(shows) if isinstance(shows, list) else 0
    count_ratio = min(actual_count / EXPECTED_COUNT, 1.0)
    score.add("show_count", 15, count_ratio, f"{actual_count}/{EXPECTED_COUNT} shows")
    
    # Check 5: Show IDs (15 points)
    match_ratio, matched_ids, _ = validate_show_ids(shows)
    score.add("show_ids", 15, match_ratio, f"Show IDs: {len(matched_ids)}/{EXPECTED_COUNT} matched")
    
    # Check 6: Show data validation (20 points)
    valid_shows = 0
    for show in shows[:EXPECTED_COUNT]:
        show_score, _ = validate_show_data(show)
        if show_score >= 0.5:
            valid_shows += 1
    if actual_count > 0:
        score.add("show_data", 20, valid_shows / min(actual_count, EXPECTED_COUNT),
                  f"{valid_shows}/{min(actual_count, EXPECTED_COUNT)} shows valid")
    else:
        score.add("show_data", 20, 0, "No shows to validate")
    
    # Check 7: Data completeness (20 points)
    quality_score = 0
    for show in shows[:EXPECTED_COUNT]:
        fields_present = sum(1 for f in REQUIRED_FIELDS if show.get(f) is not None)
        quality_score += fields_present / len(REQUIRED_FIELDS)
    if actual_count > 0:
        score.add("data_completeness", 20, quality_score / min(actual_count, EXPECTED_COUNT),
                  f"Field completeness: {quality_score / min(actual_count, EXPECTED_COUNT) * 100:.1f}%")
    else:
        score.add("data_completeness", 20, 0, "No data to check")
    
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


if __name__ == "__main__":
    main()
