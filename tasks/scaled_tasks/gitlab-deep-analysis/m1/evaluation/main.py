#!/usr/bin/env python3
"""
Evaluation script for gitlab-deep-analysis-m1 task (Medium: 4 projects × 4 API calls).

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

# Add parent directories to path for eval_utils import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))

from eval_utils import (
    EvalScore, check_for_failures, load_json_file_safe
)

# Expected projects for m1 task (4 projects)
EXPECTED_PROJECTS = [
    "gitlab-org/gitlab-runner",
    "gitlab-org/gitaly",
    "gitlab-org/gitlab-pages",
    "gitlab-org/gitlab-shell",
]

# Required fields for m1 (4 API calls: project_info, contributors, commits, branches)
REQUIRED_FIELDS = ['path', 'name', 'description', 'stars', 'forks', 'default_branch',
                   'contributors', 'commits', 'branches', 'activity_score', 'health_status']


def validate_project_paths(projects: List[Dict], expected_count: int) -> tuple:
    """Validate that project paths match expected projects."""
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
    """Cross-validate summary against project data."""
    errors = []
    checks_passed = 0
    total_checks = 4
    
    # Check total_projects
    if summary.get('total_projects') == len(projects):
        checks_passed += 1
    else:
        errors.append(f"total_projects mismatch: {summary.get('total_projects')} vs {len(projects)}")
    
    # Check avg_activity_score is reasonable
    avg_score = summary.get('avg_activity_score')
    if avg_score is not None:
        try:
            if 0 <= float(avg_score) <= 100:
                checks_passed += 1
            else:
                errors.append(f"avg_activity_score out of range: {avg_score}")
        except:
            errors.append("avg_activity_score not a number")
    
    # Check total_stars is positive
    total_stars = summary.get('total_stars')
    if total_stars is not None and isinstance(total_stars, (int, float)) and total_stars >= 0:
        checks_passed += 1
    elif total_stars is not None:
        errors.append(f"Invalid total_stars: {total_stars}")
    
    # Check healthiest_project exists
    healthiest = summary.get('healthiest_project')
    if healthiest:
        checks_passed += 1
    else:
        errors.append("Missing healthiest_project")
    
    return checks_passed / total_checks if total_checks > 0 else 0, errors


def validate_project_data(project: Dict) -> bool:
    """Validate a single project has required data for m1 level."""
    # Check path exists and is string
    path = project.get('path', '')
    if not isinstance(path, str) or len(path) < 2:
        return False
    
    # Check contributors
    contributors = project.get('contributors')
    if contributors is not None:
        if isinstance(contributors, dict):
            total = contributors.get('total', -1)
            if not isinstance(total, (int, float)) or total < 0:
                return False
        elif isinstance(contributors, (int, float)):
            if contributors < 0:
                return False
        else:
            return False
    
    # Check commits
    commits = project.get('commits')
    if commits is not None:
        if isinstance(commits, dict):
            count = commits.get('recent_count', commits.get('total', -1))
            if not isinstance(count, (int, float)) or count < 0:
                return False
        elif isinstance(commits, (int, float)):
            if commits < 0:
                return False
        else:
            return False
    
    # Check branches (required for m1)
    branches = project.get('branches')
    if branches is not None:
        if isinstance(branches, dict):
            total = branches.get('total', -1)
            if not isinstance(total, (int, float)) or total < 0:
                return False
        elif isinstance(branches, (int, float)):
            if branches < 0:
                return False
        else:
            return False
    
    # Check activity_score is reasonable (0-100)
    activity = project.get('activity_score')
    if activity is not None:
        try:
            activity_val = float(activity)
            if not (0 <= activity_val <= 100):
                return False
        except (TypeError, ValueError):
            return False
    
    return True


def evaluate(workspace: str, groundtruth_dir: str) -> Dict[str, Any]:
    """Evaluate the gitlab_analysis_results.json output."""
    score = EvalScore("gitlab-deep-analysis-m1")
    result_file = os.path.join(workspace, "gitlab_analysis_results.json")
    expected_count = len(EXPECTED_PROJECTS)  # 3 for m1
    
    # ========== Check 1: Output file exists (5 points) ==========
    if not os.path.exists(result_file):
        score.add("output_file_exists", 5, 0, "gitlab_analysis_results.json not found")
        score.add_error("Required output file not found")
        return score.get_result()
    
    score.add("output_file_exists", 5, 1, "Output file found")
    
    # ========== Check 2: Valid JSON format (5 points) ==========
    try:
        result = load_json_file_safe(result_file)
        score.add("valid_json", 5, 1, "Valid JSON format")
    except json.JSONDecodeError as e:
        score.add("valid_json", 5, 0, f"Invalid JSON: {str(e)}")
        score.add_error(f"JSON parsing failed: {str(e)}")
        return score.get_result()
    
    # ========== Check 3: No failure indicators (10 points) ==========
    has_failure, failure_msg = check_for_failures(result)
    if has_failure:
        score.add("no_failure_indicators", 10, 0, f"Fake data indicator: {failure_msg}")
        score.add_error(f"Possible fabricated data detected: {failure_msg}")
    else:
        score.add("no_failure_indicators", 10, 1, "No fake data indicators found")
    
    # ========== Check 4: Project count (10 points) ==========
    projects = result.get('projects', [])
    actual_count = len(projects) if isinstance(projects, list) else 0
    
    count_ratio = min(actual_count / expected_count, 1.0)
    score.add("project_count", 10, count_ratio,
              f"{actual_count}/{expected_count} projects")
    
    # ========== Check 5: Project paths validation (15 points) ==========
    match_ratio, matched_paths, missing_paths = validate_project_paths(projects, expected_count)
    
    if missing_paths and len(missing_paths) <= 2:
        score.add("project_paths", 15, match_ratio,
                  f"Project paths: {len(matched_paths)}/{expected_count} matched. Missing: {missing_paths}")
        score.add_warning(f"Missing projects: {missing_paths}")
    elif missing_paths:
        score.add("project_paths", 15, match_ratio,
                  f"Project paths: {len(matched_paths)}/{expected_count} matched. Missing {len(missing_paths)} projects")
        score.add_warning(f"Missing {len(missing_paths)} expected projects")
    else:
        score.add("project_paths", 15, 1.0, f"All {expected_count} expected project paths found")
    
    # ========== Check 6: Project data validation (30 points) ==========
    valid_projects = 0
    for project in projects[:expected_count]:
        if validate_project_data(project):
            valid_projects += 1
    
    if actual_count > 0:
        score.add("project_data_validation", 30, valid_projects / min(actual_count, expected_count),
                  f"Project validation: {valid_projects}/{min(actual_count, expected_count)} valid projects")
    else:
        score.add("project_data_validation", 30, 0, "No projects to verify")
    
    # ========== Check 7: Summary cross-validation (10 points) ==========
    summary = result.get('summary', {})
    if summary and projects:
        cv_ratio, cv_errors = cross_validate_summary(projects, summary)
        score.add("summary_cross_validation", 10, cv_ratio,
                  f"Summary cross-validation: {cv_ratio*100:.0f}% passed")
        for err in cv_errors[:2]:
            score.add_warning(f"Cross-validation: {err}")
    else:
        score.add("summary_cross_validation", 10, 0, "Missing summary or projects")
    
    # ========== Check 8: Data quality/completeness (15 points) ==========
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
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Evaluate gitlab-deep-analysis-m1 task')
    parser.add_argument('--agent_workspace', required=True, help='Path to agent workspace')
    parser.add_argument('--groundtruth_workspace', required=True, help='Path to groundtruth')
    parser.add_argument('--res_log_file', help='Path to result log file (unused)')
    parser.add_argument('--launch_time', help='Launch time (unused)')
    args = parser.parse_args()
    
    result = evaluate(args.agent_workspace, args.groundtruth_workspace)
    
    print("=== SCORE_JSON_START ===")
    print(json.dumps(result, indent=2))
    print("=== SCORE_JSON_END ===")
    
    if result["passed"]:
        sys.exit(0)
    elif result["status"] == "partial":
        sys.exit(2)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
