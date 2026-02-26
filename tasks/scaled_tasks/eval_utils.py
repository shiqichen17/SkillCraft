#!/usr/bin/env python3
"""
Common evaluation utilities for advanced_reuse_tasks.
Provides:
1. Session history API call validation
2. Failure indicator detection
3. Numeric range validation
4. Groundtruth comparison helpers
5. DNA sequence verification
6. Recipe data verification
7. Safe JSON loading with LLM error recovery
"""

import json
import os
import re
from typing import Dict, List, Tuple, Any, Optional, Set
from pathlib import Path


# ==================== SAFE JSON LOADING ====================

def sanitize_json_content(content: str) -> str:
    """
    Fix common JSON errors produced by LLMs.
    
    Common issues:
    - \\' (escaped single quote) - not valid in JSON, should be just '
    - Trailing commas (sometimes)
    """
    # Fix escaped single quotes (\' -> ')
    # This is a common mistake when LLMs generate JSON
    content = content.replace("\\'", "'")
    
    return content


def load_json_file_safe(filepath: str) -> Dict:
    """
    Load and parse a JSON file with automatic error recovery for common LLM mistakes.
    
    This function handles:
    - Standard JSON files
    - JSON with escaped single quotes (\\') - common LLM error
    
    Args:
        filepath: Path to the JSON file
        
    Returns:
        Parsed JSON as dict
        
    Raises:
        json.JSONDecodeError: If JSON cannot be parsed even after sanitization
        FileNotFoundError: If file doesn't exist
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # First try direct parsing
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        # Try with sanitization
        sanitized = sanitize_json_content(content)
        return json.loads(sanitized)


# ==================== FAILURE INDICATORS ====================
# NOTE: Be careful with common technical terms that may appear in real data
# Words like "template" are common in GitLab issues and should NOT be flagged
FAILURE_INDICATORS = [
    "network is unreachable",
    "connection timed out",
    "connection refused",
    "failed to fetch",
    "error fetching",
    "unable to retrieve",
    # "template",  # REMOVED: too common in real technical content
    "placeholder_data",  # more specific
    "example data",
    "sample data",
    "dummy_value",  # more specific
    "mock_response",  # more specific
    "假设数据",  # more specific
    "模拟数据",  # more specific
    "示例数据",
    "无法获取",
    "网络不可达",
    "连接超时",
    "api error",
    "not implemented",
    "todo: implement",
    "fixme: fake",
    "xxx: placeholder",
    "未实现",
    "待完成",
]


def check_for_failures(result: dict) -> Tuple[bool, str]:
    """
    Check if the result contains failure indicators suggesting fake data.
    Returns: (has_failure, failure_message)
    
    Note: This check is intentionally conservative to avoid false positives.
    Real API data often contains technical terms that look like placeholders.
    """
    result_str = json.dumps(result, ensure_ascii=False).lower()
    
    for indicator in FAILURE_INDICATORS:
        indicator_lower = indicator.lower()
        if indicator_lower in result_str:
            # Count occurrences
            count = result_str.count(indicator_lower)
            
            # Allow rare occurrences (could be legitimate content)
            # Only flag if the indicator appears multiple times (suggests systematic fake data)
            if count <= 2:
                continue
                
            # Additional context check: skip if the indicator is part of longer legitimate content
            if count <= 5 and indicator_lower in ["api error", "connection refused"]:
                continue
            
            return True, f"Found failure indicator: '{indicator}' ({count} times)"
    
    return False, ""


# ==================== SESSION HISTORY VALIDATION ====================

def load_session_history(workspace: str) -> List[dict]:
    """
    Load session history from workspace.
    Searches for session_history.jsonl in conversation_history folder.
    """
    workspace_path = Path(workspace)
    
    # Try multiple possible locations (up to 5 levels up)
    search_paths = [workspace_path]
    current = workspace_path
    for _ in range(5):
        current = current.parent
        search_paths.append(current)
    
    for parent in search_paths:
        conv_dir = parent / "conversation_history"
        if conv_dir.exists():
            for f in conv_dir.glob("*_session_history.jsonl"):
                try:
                    entries = []
                    with open(f, 'r', encoding='utf-8') as file:
                        for line in file:
                            line = line.strip()
                            if line:
                                entries.append(json.loads(line))
                    if entries:
                        return entries
                except Exception:
                    continue
    
    return []


def count_api_calls(session_history: List[dict], tool_name_patterns: List[str]) -> Dict[str, int]:
    """
    Count API calls matching specific patterns from session history.
    
    Args:
        session_history: List of session history entries
        tool_name_patterns: List of tool name patterns to match (e.g., ["local-dna_", "mcp_howtocook_"])
    
    Returns:
        Dict mapping tool names to call counts
    """
    call_counts = {}
    
    for entry in session_history:
        if entry.get("item_type") == "tool_call_item":
            raw_content = entry.get("raw_content", {})
            tool_name = raw_content.get("name", "")
            
            if not tool_name:
                continue
            
            # Check if matches any pattern
            for pattern in tool_name_patterns:
                if pattern in tool_name or re.match(pattern, tool_name):
                    call_counts[tool_name] = call_counts.get(tool_name, 0) + 1
                    break
    
    return call_counts


def get_total_api_calls(session_history: List[dict], tool_patterns: List[str]) -> int:
    """Get total count of API calls matching patterns."""
    counts = count_api_calls(session_history, tool_patterns)
    return sum(counts.values())


def verify_minimum_api_calls(session_history: List[dict], 
                             tool_patterns: List[str],
                             min_calls: int) -> Tuple[bool, int, str]:
    """
    Verify that minimum number of API calls were made.
    
    Returns: (passed, actual_count, message)
    """
    total_calls = get_total_api_calls(session_history, tool_patterns)
    
    if total_calls >= min_calls:
        return True, total_calls, f"API calls verified: {total_calls} >= {min_calls}"
    else:
        return False, total_calls, f"Insufficient API calls: {total_calls} < {min_calls} required"


def get_tool_call_arguments(session_history: List[dict], 
                            tool_patterns: List[str]) -> List[Tuple[str, dict]]:
    """
    Get all tool calls with their arguments.
    
    Returns: List of (tool_name, arguments) tuples
    """
    results = []
    
    for entry in session_history:
        if entry.get("item_type") == "tool_call_item":
            raw_content = entry.get("raw_content", {})
            tool_name = raw_content.get("name", "")
            
            if not tool_name:
                continue
            
            for pattern in tool_patterns:
                if pattern in tool_name or re.match(pattern, tool_name):
                    try:
                        args = json.loads(raw_content.get("arguments", "{}"))
                    except:
                        args = {}
                    results.append((tool_name, args))
                    break
    
    return results


def extract_unique_inputs(session_history: List[dict], 
                          tool_patterns: List[str],
                          arg_name: str) -> Set[str]:
    """
    Extract unique values of a specific argument from tool calls.
    
    Args:
        session_history: Session history entries
        tool_patterns: Tool name patterns to match
        arg_name: Name of the argument to extract
    
    Returns: Set of unique argument values
    """
    unique_values = set()
    
    for tool_name, args in get_tool_call_arguments(session_history, tool_patterns):
        if arg_name in args:
            value = args[arg_name]
            if isinstance(value, str):
                unique_values.add(value)
            elif isinstance(value, list):
                unique_values.update(str(v) for v in value)
    
    return unique_values


# ==================== NUMERIC VALIDATION ====================

def validate_range(value: Any, min_val: float, max_val: float, 
                   field_name: str = "value") -> Tuple[bool, str]:
    """
    Validate that a numeric value is within expected range.
    
    Returns: (valid, message)
    """
    if value is None:
        return False, f"{field_name} is None"
    
    try:
        num_value = float(value)
        if min_val <= num_value <= max_val:
            return True, f"{field_name}={num_value} is within [{min_val}, {max_val}]"
        else:
            return False, f"{field_name}={num_value} is outside [{min_val}, {max_val}]"
    except (TypeError, ValueError):
        return False, f"{field_name}={value} is not a valid number"


def validate_percentage(value: Any, field_name: str = "percentage") -> Tuple[bool, str]:
    """Validate that a value is a valid percentage (0-100)."""
    return validate_range(value, 0, 100, field_name)


def validate_positive(value: Any, field_name: str = "value") -> Tuple[bool, str]:
    """Validate that a value is positive."""
    if value is None:
        return False, f"{field_name} is None"
    try:
        num_value = float(value)
        if num_value > 0:
            return True, f"{field_name}={num_value} is positive"
        else:
            return False, f"{field_name}={num_value} is not positive"
    except (TypeError, ValueError):
        return False, f"{field_name}={value} is not a valid number"


def validate_consistency(value: Any, expected: Any, tolerance: float = 0.01,
                        field_name: str = "value") -> Tuple[bool, str]:
    """Validate value matches expected with tolerance."""
    if value is None or expected is None:
        return False, f"{field_name}: value or expected is None"
    
    try:
        actual = float(value)
        exp = float(expected)
        if exp == 0:
            is_match = abs(actual) < tolerance
        else:
            is_match = abs(actual - exp) / abs(exp) <= tolerance
        
        if is_match:
            return True, f"{field_name}: {actual} matches expected {exp}"
        else:
            return False, f"{field_name}: {actual} does not match expected {exp}"
    except (TypeError, ValueError) as e:
        return False, f"{field_name}: comparison error - {e}"


# ==================== DNA SEQUENCE VALIDATION ====================

# DNA sequences from task definition
DNA_SEQUENCES = {
    "SEQ_01": "ATGCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCG",
    "SEQ_02": "GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTA",
    "SEQ_03": "AAATTTGGGCCCAAATTTGGGCCCAAATTTGGGCCCAAATTTGGGCCCAAATTTGGGCCC",
    "SEQ_04": "TATATATATATATATATATATATATATATATATATATATATATATATATATATATATATA",
    "SEQ_05": "GCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGCGC",
    "SEQ_06": "ATGATGATGATGATGATGATGATGATGATGATGATGATGATGATGATGATGATGATGATG",
    "SEQ_07": "CAGCAGCAGCAGCAGCAGCAGCAGCAGCAGCAGCAGCAGCAGCAGCAGCAGCAGCAGCAG",
    "SEQ_08": "TGCTGCTGCTGCTGCTGCTGCTGCTGCTGCTGCTGCTGCTGCTGCTGCTGCTGCTGCTGC",
    "SEQ_09": "AACCGGTTAACCGGTTAACCGGTTAACCGGTTAACCGGTTAACCGGTTAACCGGTTAACC",
    "SEQ_10": "GATTACAGATTACAGATTACAGATTACAGATTACAGATTACAGATTACAGATTACAGATT",
    "SEQ_11": "ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCG",
    "SEQ_12": "TAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGC",
    "SEQ_13": "AAAGGGCCCTTAAAGGGCCCTTAAAGGGCCCTTAAAGGGCCCTTAAAGGGCCCTTAAAGGG",
    "SEQ_14": "CGCGATATCGCGATATCGCGATATCGCGATATCGCGATATCGCGATATCGCGATATCGCG",
    "SEQ_15": "ATATATGCGCATATATGCGCATATATGCGCATATATGCGCATATATGCGCATATATGCGC",
    "SEQ_16": "GGGAAACCCGGGAAACCCGGGAAACCCGGGAAACCCGGGAAACCCGGGAAACCCGGGAAA",
    "SEQ_17": "TCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGA",
    "SEQ_18": "ACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGT",
    "SEQ_19": "TGCATGCATGCATGCATGCATGCATGCATGCATGCATGCATGCATGCATGCATGCATGCA",
    "SEQ_20": "CAGTCAGTCAGTCAGTCAGTCAGTCAGTCAGTCAGTCAGTCAGTCAGTCAGTCAGTCAGT",
    "SEQ_21": "AGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCT",
    "SEQ_22": "GATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATC",
    "SEQ_23": "CTGACTGACTGACTGACTGACTGACTGACTGACTGACTGACTGACTGACTGACTGACTGA",
    "SEQ_24": "AGTCAGTCAGTCAGTCAGTCAGTCAGTCAGTCAGTCAGTCAGTCAGTCAGTCAGTCAGTC",
    "SEQ_25": "TACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACG",
}


def calculate_gc_content(sequence: str) -> float:
    """Calculate GC content percentage of a DNA sequence."""
    if not sequence:
        return 0.0
    sequence = sequence.upper()
    gc_count = sequence.count('G') + sequence.count('C')
    return (gc_count / len(sequence)) * 100


def count_nucleotides(sequence: str) -> Dict[str, int]:
    """Count nucleotides in a DNA sequence."""
    sequence = sequence.upper()
    return {
        'A': sequence.count('A'),
        'T': sequence.count('T'),
        'G': sequence.count('G'),
        'C': sequence.count('C'),
    }


def is_valid_dna(sequence: str) -> bool:
    """Check if a sequence is valid DNA (only A, T, G, C)."""
    return bool(sequence) and set(sequence.upper()) <= {'A', 'T', 'G', 'C'}


def transcribe_dna_to_mrna(dna: str) -> str:
    """Transcribe DNA to mRNA (complement and T -> U)."""
    complement = {'A': 'U', 'T': 'A', 'G': 'C', 'C': 'G'}
    return ''.join(complement.get(n.upper(), 'X') for n in dna)


def get_expected_dna_results(seq_id: str) -> Optional[Dict[str, Any]]:
    """Get expected results for a DNA sequence."""
    if seq_id not in DNA_SEQUENCES:
        return None
    
    seq = DNA_SEQUENCES[seq_id]
    nucleotides = count_nucleotides(seq)
    gc = calculate_gc_content(seq)
    max_nuc = max(nucleotides.items(), key=lambda x: x[1])
    
    return {
        "id": seq_id,
        "length": len(seq),
        "is_valid": True,
        "nucleotide_counts": nucleotides,
        "max_nucleotide": max_nuc[0],
        "max_count": max_nuc[1],
        "gc_content": round(gc, 2),
        "mrna_prefix": transcribe_dna_to_mrna(seq[:10]),  # First 10 chars of mRNA
    }


def verify_dna_result(result: dict, expected: dict, tolerance: float = 0.01) -> Tuple[int, int, List[str]]:
    """
    Verify a single DNA sequence result against expected.
    
    Returns: (passed_checks, total_checks, error_messages)
    """
    passed = 0
    total = 0
    errors = []
    
    # Check nucleotide counts
    total += 1
    actual_counts = result.get("nucleotide_counts", {})
    expected_counts = expected["nucleotide_counts"]
    if actual_counts == expected_counts:
        passed += 1
    else:
        errors.append(f"Nucleotide counts mismatch: {actual_counts} vs {expected_counts}")
    
    # Check GC content
    total += 1
    actual_gc = result.get("gc_content")
    expected_gc = expected["gc_content"]
    if actual_gc is not None and abs(float(actual_gc) - expected_gc) <= tolerance * 100:
        passed += 1
    else:
        errors.append(f"GC content mismatch: {actual_gc} vs {expected_gc}")
    
    # Check is_valid
    total += 1
    if result.get("is_valid") == expected["is_valid"]:
        passed += 1
    else:
        errors.append(f"is_valid mismatch: {result.get('is_valid')} vs {expected['is_valid']}")
    
    # Check mRNA prefix (if available)
    mrna = result.get("mrna", "")
    if mrna:
        total += 1
        if isinstance(mrna, str) and mrna[:10].upper() == expected["mrna_prefix"]:
            passed += 1
        else:
            errors.append(f"mRNA prefix mismatch")
    
    return passed, total, errors


# ==================== RECIPE VALIDATION ====================

# Common Chinese dish names for validation
COMMON_DISHES = [
    "红烧肉", "宫保鸡丁", "麻婆豆腐", "糖醋排骨", "鱼香肉丝",
    "回锅肉", "水煮鱼", "口水鸡", "番茄炒蛋", "酸辣土豆丝",
    "干煸四季豆", "地三鲜", "蒜蓉西兰花", "虎皮青椒", "蛋炒饭",
    "葱油拌面", "酸辣粉", "炸酱面", "番茄蛋汤", "酸辣汤",
    "东坡肉", "辣子鸡", "蚝油生菜", "清炒时蔬", "紫菜蛋花汤",
    "冬瓜排骨汤", "红烧茄子", "可乐鸡翅", "青椒肉丝", "清炒西兰花",
]

# Expected cooking time ranges (minutes)
COOKING_TIME_RANGES = {
    "番茄炒蛋": (5, 20),
    "红烧肉": (60, 150),
    "宫保鸡丁": (15, 40),
    "麻婆豆腐": (15, 35),
    "鱼香肉丝": (15, 35),
    "糖醋排骨": (30, 80),
    "蛋炒饭": (5, 20),
    "酸辣土豆丝": (10, 30),
    "干煸四季豆": (15, 35),
    "地三鲜": (20, 45),
    "蒜蓉西兰花": (5, 20),
    "虎皮青椒": (10, 25),
    "葱油拌面": (10, 30),
    "酸辣粉": (15, 40),
    "炸酱面": (20, 50),
    "番茄蛋汤": (10, 25),
    "酸辣汤": (15, 35),
    "回锅肉": (20, 50),
    "水煮鱼": (25, 60),
    "口水鸡": (30, 90),  # includes cooling time
}

# Required ingredients for each dish (at least some of these should appear)
DISH_REQUIRED_INGREDIENTS = {
    "红烧肉": ["五花肉", "肉", "猪肉"],
    "宫保鸡丁": ["鸡", "花生"],
    "麻婆豆腐": ["豆腐"],
    "糖醋排骨": ["排骨"],
    "鱼香肉丝": ["肉丝", "猪肉", "肉"],
    "回锅肉": ["肉", "五花肉", "猪肉"],
    "水煮鱼": ["鱼"],
    "口水鸡": ["鸡"],
    "番茄炒蛋": ["番茄", "鸡蛋", "蛋"],
    "酸辣土豆丝": ["土豆"],
    "干煸四季豆": ["四季豆", "豆角"],
    "地三鲜": ["茄子", "土豆", "青椒"],
    "蒜蓉西兰花": ["西兰花"],
    "虎皮青椒": ["青椒"],
    "蛋炒饭": ["蛋", "饭", "鸡蛋"],
    "葱油拌面": ["面"],
    "酸辣粉": ["粉"],
    "炸酱面": ["面", "酱"],
    "番茄蛋汤": ["番茄", "蛋"],
    "酸辣汤": ["豆腐", "蛋"],
}


def normalize_dish_name(name: str) -> str:
    """Normalize dish name for matching."""
    return name.strip().replace(" ", "").replace("　", "")


def validate_dish_name(name: str) -> bool:
    """Check if dish name is plausible (not obviously fake)."""
    if not name or len(name) < 2:
        return False
    
    name_normalized = normalize_dish_name(name)
    
    # Exact match to known dishes
    for dish in COMMON_DISHES:
        if dish in name_normalized or name_normalized in dish:
            return True
    
    # Check if it contains Chinese characters (reasonable for Chinese dish)
    has_chinese = any('\u4e00' <= c <= '\u9fff' for c in name_normalized)
    if has_chinese and len(name_normalized) >= 2:
        return True
    
    return False


def validate_cooking_time(dish_name: str, time_min: Any) -> Tuple[bool, str]:
    """Validate cooking time is reasonable for the dish."""
    if time_min is None:
        return False, f"{dish_name}: cooking time is None"
    
    try:
        time_val = float(time_min)
    except (TypeError, ValueError):
        return False, f"{dish_name}: invalid cooking time type"
    
    # First check if it's a known dish with expected range
    dish_normalized = normalize_dish_name(dish_name)
    for known_dish, (min_time, max_time) in COOKING_TIME_RANGES.items():
        if known_dish in dish_normalized or dish_normalized in known_dish:
            if min_time <= time_val <= max_time:
                return True, f"{dish_name}: {time_val} min is within expected range [{min_time}, {max_time}]"
            else:
                return False, f"{dish_name}: {time_val} min is outside expected range [{min_time}, {max_time}]"
    
    # For unknown dishes, check general reasonableness (3-240 minutes)
    if 3 <= time_val <= 240:
        return True, f"{dish_name}: {time_val} min is within reasonable range"
    else:
        return False, f"{dish_name}: {time_val} min is outside reasonable range [3, 240]"


def validate_dish_ingredients(dish_name: str, ingredients: List) -> Tuple[bool, str]:
    """Validate that dish has expected ingredients."""
    if not ingredients or not isinstance(ingredients, list):
        return False, f"{dish_name}: no ingredients found"
    
    dish_normalized = normalize_dish_name(dish_name)
    ingredients_str = json.dumps(ingredients, ensure_ascii=False).lower()
    
    # Check if known dish has required ingredients
    for known_dish, required in DISH_REQUIRED_INGREDIENTS.items():
        if known_dish in dish_normalized or dish_normalized in known_dish:
            found_required = False
            for req in required:
                if req.lower() in ingredients_str:
                    found_required = True
                    break
            if not found_required:
                return False, f"{dish_name}: missing required ingredients (expected one of: {required})"
            return True, f"{dish_name}: has required ingredients"
    
    # For unknown dishes, just check there are some ingredients
    if len(ingredients) >= 1:
        return True, f"{dish_name}: has {len(ingredients)} ingredients"
    return False, f"{dish_name}: insufficient ingredients"


# ==================== GROUNDTRUTH HELPERS ====================

def load_groundtruth(groundtruth_dir: str, filename: str = "expected.json") -> Optional[dict]:
    """Load groundtruth data from file."""
    try:
        filepath = os.path.join(groundtruth_dir, filename)
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    return None


def compare_with_tolerance(actual: float, expected: float, tolerance: float = 0.05) -> bool:
    """Compare two values with relative tolerance."""
    if expected == 0:
        return abs(actual) < tolerance
    return abs(actual - expected) / abs(expected) <= tolerance


# ==================== SCORING HELPERS ====================

class EvalScore:
    """Helper class for building evaluation scores."""
    
    def __init__(self, task_name: str):
        self.task_name = task_name
        self.items = []
        self.errors = []
        self.warnings = []
        self.total_score = 0
        self.max_score = 0
    
    def add(self, name: str, max_points: float, score_ratio: float, 
            details: str = "", error: str = ""):
        """Add a scoring item."""
        score = max_points * min(1.0, max(0.0, score_ratio))
        self.total_score += score
        self.max_score += max_points
        
        if score_ratio >= 1.0:
            status = "pass"
        elif score_ratio > 0:
            status = "partial"
        else:
            status = "fail"
        
        self.items.append({
            "name": name,
            "score": round(score, 1),
            "max_score": max_points,
            "status": status,
            "details": details
        })
        
        if error:
            self.errors.append(error)
    
    def add_error(self, error: str):
        """Add an error message."""
        self.errors.append(error)
    
    def add_warning(self, warning: str):
        """Add a warning message."""
        self.warnings.append(warning)
    
    def get_result(self) -> dict:
        """Get the final evaluation result."""
        percent = round((self.total_score / self.max_score) * 100, 1) if self.max_score > 0 else 0
        
        return {
            "passed": percent >= 70,
            "status": "pass" if percent >= 90 else "partial" if percent >= 70 else "fail",
            "score": {
                "achieved": round(self.total_score, 1),
                "max": self.max_score,
                "percent": percent
            },
            "items": self.items,
            "errors": self.errors[:10],
            "warnings": self.warnings[:10]
        }
    
    def output_and_exit(self):
        """Output result and exit with appropriate code."""
        import sys
        result = self.get_result()
        print("=== SCORE_JSON_START ===")
        print(json.dumps(result, indent=2))
        print("=== SCORE_JSON_END ===")
        
        if result["passed"]:
            sys.exit(0)
        elif result["status"] == "partial":
            sys.exit(2)
        else:
            sys.exit(1)
