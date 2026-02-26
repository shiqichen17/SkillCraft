#!/usr/bin/env python3
"""
Evaluation script for gitlab-deep-analysis-e2 task (Easy: 3 projects × 3 API calls).
Tools: project_info, branches, issues

Evaluation criteria (Total: 100 points):
1. Output file exists (5 points)
2. Valid JSON format (5 points)
3. No fake data indicators (10 points)
4. Correct project count (10 points)
5. Project paths match expected list (15 points)
6. Project data validation (30 points)
7. Summary cross-validation (10 points)
8. Data quality/completeness (15 points)
"""
import json
import os
import sys
import argparse
from typing import Any, Dict, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))

from eval_utils import (
    EvalScore, check_for_failures, load_json_file_safe
)

EXPECTED_PROJECTS = [
    "gitlab-org/gitlab",
    "gitlab-org/gitlab-runner",
    "gitlab-org/gitlab-pages",
]

# Required fields for e2 (project_info, branches, issues)
REQUIRED_FIELDS = ['path', 'name', 'description', 'stars', 'forks', 
                   'branches', 'issues']


def validate_project_paths(projects: List[Dict], expected_count: int) -> tuple:
    if not projects:
        return 0.0, [], EXPECTED_PROJECTS
    
    found_paths = set()
    for p in projects:
        path = p.get('path', '')
        if isinstance(path, str):
            found_paths.add(path.lower())
    
    expected_set = set(p.lower() for p in EXPECTED_PROJECTS)
    matched = found_paths & expected_set
    missing = [p for p in EXPECTED_PROJECTS if p.lower() not in found_paths]
    
    match_ratio = len(matched) / len(EXPECTED_PROJECTS) if EXPECTED_PROJECTS else 0
    return match_ratio, list(matched), missing


def cross_validate_summary(projects: List[Dict], summary: Dict) -> tuple:
    errors = []
    checks_passed = 0
    total_checks = 4
    
    if summary.get('total_projects') == len(projects):
        checks_passed += 1
    else:
        errors.append(f"total_projects mismatch")
    
    total_branches = summary.get('total_branches')
    if total_branches is not None and isinstance(total_branches, (int, float)) and total_branches >= 0:
        checks_passed += 1
    
    total_issues = summary.get('total_issues')
    if total_issues is not None and isinstance(total_issues, (int, float)) and total_issues >= 0:
        checks_passed += 1
    
    most_active = summary.get('most_active_project')
    if most_active:
        checks_passed += 1
    
    return checks_passed / total_checks if total_checks > 0 else 0, errors


def validate_project_data(project: Dict) -> bool:
    path = project.get('path', '')
    if not isinstance(path, str) or len(path) < 2:
        return False
    
    # Check branches
    branches = project.get('branches')
    if branches is not None:
        if isinstance(branches, dict):
            total = branches.get('total_count', branches.get('total', -1))
            if not isinstance(total, (int, float)) or total < 0:
                return False
        elif isinstance(branches, (int, float)):
            if branches < 0:
                return False
    
    # Check issues
    issues = project.get('issues')
    if issues is not None:
        if isinstance(issues, dict):
            total = issues.get('total_count', issues.get('total', -1))
            if not isinstance(total, (int, float)) or total < 0:
                return False
        elif isinstance(issues, (int, float)):
            if issues < 0:
                return False
    
    return True


def evaluate(workspace: str, groundtruth_dir: str) -> Dict[str, Any]:
    score = EvalScore("gitlab-deep-analysis-e2")
    result_file = os.path.join(workspace, "gitlab_analysis.json")
    expected_count = len(EXPECTED_PROJECTS)
    
    if not os.path.exists(result_file):
        score.add("output_file_exists", 5, 0, "gitlab_analysis.json not found")
        score.add_error("Required output file not found")
        return score.get_result()
    
    score.add("output_file_exists", 5, 1, "Output file found")
    
    try:
        result = load_json_file_safe(result_file)
        score.add("valid_json", 5, 1, "Valid JSON format")
    except json.JSONDecodeError as e:
        score.add("valid_json", 5, 0, f"Invalid JSON: {str(e)}")
        return score.get_result()
    
    has_failure, failure_msg = check_for_failures(result)
    if has_failure:
        score.add("no_failure_indicators", 10, 0, f"Fake data indicator: {failure_msg}")
    else:
        score.add("no_failure_indicators", 10, 1, "No fake data indicators found")
    
    projects = result.get('projects', [])
    actual_count = len(projects) if isinstance(projects, list) else 0
    
    count_ratio = min(actual_count / expected_count, 1.0)
    score.add("project_count", 10, count_ratio, f"{actual_count}/{expected_count} projects")
    
    match_ratio, matched_paths, missing_paths = validate_project_paths(projects, expected_count)
    score.add("project_paths", 15, match_ratio,
              f"Project paths: {len(matched_paths)}/{expected_count} matched")
    
    valid_projects = 0
    for project in projects[:expected_count]:
        if validate_project_data(project):
            valid_projects += 1
    
    if actual_count > 0:
        score.add("project_data_validation", 30, valid_projects / min(actual_count, expected_count),
                  f"Project validation: {valid_projects}/{min(actual_count, expected_count)} valid")
    else:
        score.add("project_data_validation", 30, 0, "No projects to verify")
    
    summary = result.get('summary', {})
    if summary and projects:
        cv_ratio, cv_errors = cross_validate_summary(projects, summary)
        score.add("summary_cross_validation", 10, cv_ratio,
                  f"Summary cross-validation: {cv_ratio*100:.0f}% passed")
    else:
        score.add("summary_cross_validation", 10, 0, "Missing summary or projects")
    
    quality_score = 0
    for project in projects[:expected_count]:
        fields_present = sum(1 for f in REQUIRED_FIELDS if project.get(f) is not None)
        quality_score += (fields_present / len(REQUIRED_FIELDS))
    
    if actual_count > 0:
        quality_ratio = quality_score / min(actual_count, expected_count)
        score.add("data_quality", 15, quality_ratio,
                  f"Data quality: {quality_ratio*100:.1f}% complete")
    else:
        score.add("data_quality", 15, 0, "No projects to evaluate")
    
    return score.get_result()


def main():
    parser = argparse.ArgumentParser(description='Evaluate gitlab-deep-analysis-e2 task')
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
