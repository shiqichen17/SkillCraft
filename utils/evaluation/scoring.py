#!/usr/bin/env python3
"""
Scoring utilities for task evaluation.

This module provides a flexible scoring system that allows partial credit
for task completion, rather than just pass/fail.

Usage in evaluation scripts:
    from utils.evaluation.scoring import EvalScore
    
    score = EvalScore(task_name="batch-invoice-extraction")
    
    # Add score items
    score.add("file_exists", 10, file_found, "invoice_summary.csv exists")
    score.add("correct_count", 20, 15/15, "Correct number of invoices")
    score.add("data_accuracy", 50, 0.85, "85% of fields correct")
    
    # Output result (to stdout for the evaluator to capture)
    score.output()
    
    # Exit with appropriate code
    score.exit()
"""

import json
import sys
from typing import Dict, List, Optional, Union
from dataclasses import dataclass, field


@dataclass
class ScoreItem:
    """A single scoring item."""
    name: str
    max_points: float
    achieved_ratio: float  # 0.0 to 1.0
    description: str
    details: Optional[str] = None
    
    @property
    def achieved_points(self) -> float:
        return self.max_points * min(1.0, max(0.0, self.achieved_ratio))
    
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "max_points": self.max_points,
            "achieved_points": round(self.achieved_points, 2),
            "achieved_ratio": round(self.achieved_ratio, 4),
            "description": self.description,
            "details": self.details
        }


class EvalScore:
    """
    Evaluation score calculator with partial credit support.
    
    Example:
        score = EvalScore("my-task")
        
        # Full credit for existing file
        score.add("file_created", 10, 1.0, "Output file exists")
        
        # Partial credit based on ratio
        score.add("accuracy", 50, correct_count / total_count, 
                  f"{correct_count}/{total_count} items correct")
        
        # Boolean check (converted to 0.0 or 1.0)
        score.add("valid_format", 20, is_valid_json, "Output is valid JSON")
        
        score.output()
        score.exit()
    """
    
    def __init__(self, task_name: str = "unknown"):
        self.task_name = task_name
        self.items: List[ScoreItem] = []
        self.errors: List[str] = []
        self.warnings: List[str] = []
        
        # Thresholds for pass/partial/fail
        self.pass_threshold = 0.9  # 90% = pass
        self.partial_threshold = 0.3  # 30% = partial credit (not complete fail)
    
    def add(self, 
            name: str, 
            max_points: float, 
            achieved: Union[float, bool, int],
            description: str,
            details: Optional[str] = None) -> 'EvalScore':
        """
        Add a scoring item.
        
        Args:
            name: Unique identifier for this score item
            max_points: Maximum points possible for this item
            achieved: Either a ratio (0.0-1.0), boolean, or integer count
            description: Human-readable description of what's being scored
            details: Optional additional details
        
        Returns:
            self for chaining
        """
        # Convert to ratio
        if isinstance(achieved, bool):
            ratio = 1.0 if achieved else 0.0
        elif isinstance(achieved, int):
            ratio = float(achieved) / max_points if max_points > 0 else 0.0
        else:
            ratio = float(achieved)
        
        self.items.append(ScoreItem(
            name=name,
            max_points=max_points,
            achieved_ratio=ratio,
            description=description,
            details=details
        ))
        return self
    
    def add_file_check(self, 
                       filepath: str, 
                       points: float = 10,
                       required: bool = True) -> 'EvalScore':
        """
        Add a file existence check.
        
        Args:
            filepath: Path to check
            points: Points for file existing
            required: If True and file missing, add to errors
        """
        import os
        exists = os.path.exists(filepath)
        filename = os.path.basename(filepath)
        
        self.add(
            f"file_{filename.replace('.', '_')}",
            points,
            exists,
            f"File '{filename}' exists",
            f"Path: {filepath}"
        )
        
        if required and not exists:
            self.errors.append(f"Required file missing: {filename}")
        
        return self
    
    def add_count_check(self,
                        name: str,
                        expected: int,
                        actual: int,
                        points: float = 20,
                        description: Optional[str] = None) -> 'EvalScore':
        """
        Add a count comparison check with partial credit.
        
        Gives full credit if actual == expected, partial otherwise.
        """
        if expected == 0:
            ratio = 1.0 if actual == 0 else 0.0
        else:
            ratio = min(1.0, actual / expected)
        
        desc = description or f"Count check: expected {expected}, got {actual}"
        self.add(name, points, ratio, desc, f"Expected: {expected}, Actual: {actual}")
        
        return self
    
    def add_accuracy_check(self,
                          name: str,
                          correct: int,
                          total: int,
                          points: float = 50,
                          description: Optional[str] = None) -> 'EvalScore':
        """
        Add an accuracy check (correct / total).
        """
        if total == 0:
            ratio = 0.0
        else:
            ratio = correct / total
        
        desc = description or f"Accuracy: {correct}/{total} ({ratio*100:.1f}%)"
        self.add(name, points, ratio, desc)
        
        return self
    
    def add_error(self, message: str) -> 'EvalScore':
        """Add an error message."""
        self.errors.append(message)
        return self
    
    def add_warning(self, message: str) -> 'EvalScore':
        """Add a warning message."""
        self.warnings.append(message)
        return self
    
    @property
    def max_total(self) -> float:
        """Total possible points."""
        return sum(item.max_points for item in self.items)
    
    @property
    def achieved_total(self) -> float:
        """Total achieved points."""
        return sum(item.achieved_points for item in self.items)
    
    @property
    def score_ratio(self) -> float:
        """Overall score as ratio (0.0 - 1.0)."""
        if self.max_total == 0:
            return 0.0
        return self.achieved_total / self.max_total
    
    @property
    def score_percent(self) -> float:
        """Overall score as percentage."""
        return self.score_ratio * 100
    
    @property
    def passed(self) -> bool:
        """Whether the task passed (>= pass_threshold)."""
        return self.score_ratio >= self.pass_threshold and len(self.errors) == 0
    
    @property
    def partial(self) -> bool:
        """Whether the task got partial credit."""
        return self.partial_threshold <= self.score_ratio < self.pass_threshold
    
    @property
    def status(self) -> str:
        """Overall status: 'pass', 'partial', or 'fail'."""
        if len(self.errors) > 0:
            return "fail"
        if self.score_ratio >= self.pass_threshold:
            return "pass"
        elif self.score_ratio >= self.partial_threshold:
            return "partial"
        else:
            return "fail"
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON output."""
        return {
            "task_name": self.task_name,
            "status": self.status,
            "passed": self.passed,
            "score": {
                "achieved": round(self.achieved_total, 2),
                "max": round(self.max_total, 2),
                "percent": round(self.score_percent, 1),
                "ratio": round(self.score_ratio, 4)
            },
            "thresholds": {
                "pass": self.pass_threshold,
                "partial": self.partial_threshold
            },
            "items": [item.to_dict() for item in self.items],
            "errors": self.errors,
            "warnings": self.warnings
        }
    
    def output(self, format: str = "both") -> None:
        """
        Output the score result.
        
        Args:
            format: "json", "human", or "both"
        """
        if format in ("human", "both"):
            self._print_human_readable()
        
        if format in ("json", "both"):
            print("\n=== SCORE_JSON_START ===")
            print(json.dumps(self.to_dict(), indent=2))
            print("=== SCORE_JSON_END ===")
    
    def _print_human_readable(self) -> None:
        """Print human-readable output."""
        print(f"\n{'='*60}")
        print(f"📊 EVALUATION SCORE: {self.task_name}")
        print(f"{'='*60}\n")
        
        # Print individual items
        for item in self.items:
            check = "✅" if item.achieved_ratio >= 0.8 else "⚠️" if item.achieved_ratio >= 0.3 else "❌"
            print(f"{check} {item.description}")
            print(f"   Points: {item.achieved_points:.1f} / {item.max_points:.1f} ({item.achieved_ratio*100:.1f}%)")
            if item.details:
                print(f"   Details: {item.details}")
            print()
        
        # Print errors
        if self.errors:
            print("\n❌ ERRORS:")
            for err in self.errors:
                print(f"   - {err}")
        
        # Print warnings
        if self.warnings:
            print("\n⚠️ WARNINGS:")
            for warn in self.warnings:
                print(f"   - {warn}")
        
        # Print summary
        print(f"\n{'='*60}")
        status_emoji = "✅" if self.status == "pass" else "⚠️" if self.status == "partial" else "❌"
        print(f"{status_emoji} FINAL SCORE: {self.achieved_total:.1f} / {self.max_total:.1f} ({self.score_percent:.1f}%)")
        print(f"   Status: {self.status.upper()}")
        print(f"   Pass threshold: {self.pass_threshold*100:.0f}%")
        print(f"{'='*60}\n")
    
    def exit(self) -> None:
        """
        Exit with appropriate code for the evaluator.
        
        Exit codes:
            0: Pass (>= pass_threshold)
            1: Fail (< partial_threshold or errors)
            2: Partial (between thresholds, no errors)
        """
        if self.status == "pass":
            sys.exit(0)
        elif self.status == "partial":
            sys.exit(2)  # Special code for partial
        else:
            sys.exit(1)


# Utility functions for common checks
def check_json_file(filepath: str) -> tuple:
    """
    Check if a JSON file exists and is valid.
    
    Returns:
        (exists: bool, data: dict or None, error: str or None)
    """
    import os
    if not os.path.exists(filepath):
        return False, None, "File not found"
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return True, data, None
    except json.JSONDecodeError as e:
        return True, None, f"Invalid JSON: {e}"
    except Exception as e:
        return True, None, str(e)


def check_csv_file(filepath: str) -> tuple:
    """
    Check if a CSV file exists and is valid.
    
    Returns:
        (exists: bool, rows: list or None, error: str or None)
    """
    import os
    import csv
    
    if not os.path.exists(filepath):
        return False, None, "File not found"
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        return True, rows, None
    except Exception as e:
        return True, None, str(e)


def compare_values(expected, actual, tolerance: float = 0.01) -> bool:
    """Compare two values with tolerance for floats."""
    if isinstance(expected, float) or isinstance(actual, float):
        return abs(float(expected) - float(actual)) <= tolerance
    return expected == actual

