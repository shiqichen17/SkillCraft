#!/usr/bin/env python3
"""Evaluation for jsonplaceholder-blog-analyzer-e3: 3 users × 3 APIs"""
import json, os, sys, argparse
from typing import Any, Dict, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
from eval_utils import EvalScore, check_for_failures, load_json_file_safe

EXPECTED_USERS = {1: {"name": "Leanne Graham", "posts": 10, "todos": 20},
    2: {"name": "Ervin Howell", "posts": 10, "todos": 20},
    3: {"name": "Clementine Bauch", "posts": 10, "todos": 20}}
EXPECTED_COUNT = 3
REQUIRED_FIELDS = ['user_id', 'metrics', 'activity']

def validate_ids(users):
    if not users: return 0.0, [], list(EXPECTED_USERS.keys())
    found = set(int(u.get('user_id', u.get('id', 0))) for u in users if u.get('user_id') or u.get('id'))
    matched = found & set(EXPECTED_USERS.keys())
    return len(matched) / len(EXPECTED_USERS), list(matched), list(set(EXPECTED_USERS.keys()) - found)

def validate_data(user):
    user_id = int(user.get('user_id', user.get('id', 0)))
    if user_id not in EXPECTED_USERS: return 0.3, []
    expected = EXPECTED_USERS[user_id]
    score = 0
    profile = user.get('profile', user)
    name = profile.get('name', '')
    if name and expected["name"].lower() in name.lower(): score += 0.25
    activity = user.get('activity', user)
    if activity.get('post_count') == expected["posts"]: score += 0.25
    elif activity.get('post_count'): score += 0.1
    if activity.get('todo_count') == expected["todos"]: score += 0.25
    elif activity.get('todo_count'): score += 0.1
    metrics = user.get('metrics', {})
    if metrics.get('productivity_score') is not None: score += 0.25
    return score, []

def evaluate(workspace, groundtruth_dir):
    score = EvalScore("jsonplaceholder-blog-analyzer-e3")
    result_file = os.path.join(workspace, "blog_analysis.json")
    
    if not os.path.exists(result_file):
        score.add("output_file", 10, 0, "blog_analysis.json not found")
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
    
    users = result.get('users', [])
    actual = len(users) if isinstance(users, list) else 0
    score.add("count", 15, min(actual/EXPECTED_COUNT, 1.0), f"{actual}/{EXPECTED_COUNT} users")
    
    ratio, matched, _ = validate_ids(users)
    score.add("ids", 15, ratio, f"{len(matched)}/{EXPECTED_COUNT} IDs matched")
    
    valid = sum(1 for u in users[:EXPECTED_COUNT] if validate_data(u)[0] >= 0.5)
    score.add("data", 20, valid/min(actual, EXPECTED_COUNT) if actual else 0, f"{valid} valid")
    
    quality = sum(sum(1 for f in REQUIRED_FIELDS if u.get(f) is not None)/len(REQUIRED_FIELDS) for u in users[:EXPECTED_COUNT])
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
