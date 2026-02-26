#!/usr/bin/env python3
"""Evaluation for vocabulary-builder-e2: 3 words × 3 APIs"""
import json, os, sys, argparse
from typing import Any, Dict, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
from eval_utils import EvalScore, check_for_failures, load_json_file_safe

EXPECTED_WORDS = ['ephemeral', 'ubiquitous', 'pragmatic']
EXPECTED_COUNT = 3
REQUIRED_FIELDS = ['word', 'vocabulary_profile', 'meanings', 'synonyms', 'phonetic']

def validate_word(entry):
    word = entry.get("word", "").lower()
    score = 0
    if word in EXPECTED_WORDS: score += 0.3
    if entry.get('meanings'): score += 0.2
    if entry.get('synonyms'): score += 0.2
    if entry.get('phonetic'): score += 0.15
    if entry.get("vocabulary_profile"): score += 0.15
    return score, []

def evaluate(workspace, groundtruth_dir):
    score = EvalScore("vocabulary-builder-e2")
    result_file = os.path.join(workspace, "vocabulary_cards.json")
    
    if not os.path.exists(result_file):
        score.add("output_file", 10, 0, "vocabulary_cards.json not found")
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
    
    words = result.get('words', [])
    actual = len(words) if isinstance(words, list) else 0
    score.add("count", 15, min(actual/EXPECTED_COUNT, 1.0), f"{actual}/{EXPECTED_COUNT} words")
    
    found = set(w.get("word", "").lower() for w in words)
    matched = sum(1 for ew in EXPECTED_WORDS if ew in found)
    score.add("names", 15, matched/len(EXPECTED_WORDS), f"{matched}/{len(EXPECTED_WORDS)} words matched")
    
    valid = sum(1 for w in words[:EXPECTED_COUNT] if validate_word(w)[0] >= 0.4)
    score.add("data", 20, valid/min(actual, EXPECTED_COUNT) if actual else 0, f"{valid} valid")
    
    quality = sum(sum(1 for f in REQUIRED_FIELDS if w.get(f) is not None)/len(REQUIRED_FIELDS) for w in words[:EXPECTED_COUNT])
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
