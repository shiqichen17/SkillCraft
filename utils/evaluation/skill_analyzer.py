"""
Skill Usage Analyzer for Toolathlon Skill Mode.

Analyzes conversation history to extract detailed skill usage statistics:
- Tool call counts for skill-related functions
- Skill creation success/failure rates
- Skill execution success/failure rates per skill
- Overall skill execution statistics
- Skill complexity metrics (tool calls, loops, conditionals, lines)
"""

import json
import os
import re
import ast
from typing import Dict, List, Any, Optional
from pathlib import Path


def calculate_skill_complexity(script_code: str) -> Dict[str, Any]:
    """
    Calculate complexity metrics for a skill script.
    
    Complexity formula:
    complexity_score = tool_calls × 3 + loops × 2 + conditionals × 1 + (lines / 5)
    
    Args:
        script_code: The Python script code of the skill
        
    Returns:
        Dictionary with complexity metrics
    """
    if not script_code:
        return {
            "tool_calls": 0,
            "loops": 0,
            "conditionals": 0,
            "lines_of_code": 0,
            "complexity_score": 0.0
        }
    
    # Count lines (non-empty, non-comment)
    lines = [l.strip() for l in script_code.split('\n') 
             if l.strip() and not l.strip().startswith('#')]
    lines_of_code = len(lines)
    
    # Count call_tool() invocations (simple string matching for reliability)
    tool_calls = script_code.count('call_tool(')
    
    # Count loops and conditionals using AST
    loops = 0
    conditionals = 0
    
    try:
        tree = ast.parse(script_code)
        for node in ast.walk(tree):
            if isinstance(node, (ast.For, ast.While)):
                loops += 1
            elif isinstance(node, ast.If):
                conditionals += 1
    except SyntaxError:
        # If AST parsing fails, use regex fallback
        loops = len(re.findall(r'\b(for|while)\b', script_code))
        conditionals = len(re.findall(r'\bif\b', script_code))
    
    # Calculate complexity score
    complexity_score = (
        tool_calls * 3 +
        loops * 2 +
        conditionals * 1 +
        lines_of_code / 5
    )
    
    return {
        "tool_calls": tool_calls,
        "loops": loops,
        "conditionals": conditionals,
        "lines_of_code": lines_of_code,
        "complexity_score": round(complexity_score, 2)
    }


class SkillAnalyzer:
    """Analyzes skill usage from conversation history."""
    
    SKILL_TOOLS = [
        "local-save_skill",
        "local-execute_skill", 
        "local-get_skill",
        "local-list_skills"
    ]
    
    @staticmethod
    def find_skill_cache(task_dir: str) -> Optional[str]:
        """
        Find the skill_cache.json file in the task workspace.
        
        Args:
            task_dir: Path to the task directory
            
        Returns:
            Path to skill_cache.json or None if not found
        """
        workspace_dir = os.path.join(task_dir, "workspace")
        skill_cache_path = os.path.join(workspace_dir, "skill_cache.json")
        if os.path.exists(skill_cache_path):
            return skill_cache_path
        return None
    
    @staticmethod
    def load_skill_cache(task_dir: str) -> Dict[str, Any]:
        """
        Load skill_cache.json and calculate complexity for each skill.
        
        Args:
            task_dir: Path to the task directory
            
        Returns:
            Dictionary with skill names as keys, containing script and complexity
        """
        skill_cache_path = SkillAnalyzer.find_skill_cache(task_dir)
        if not skill_cache_path:
            return {}
        
        try:
            with open(skill_cache_path, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            skills = cache_data.get("skills", {})
            result = {}
            
            for skill_name, skill_data in skills.items():
                script_code = skill_data.get("script_code", "")
                complexity = calculate_skill_complexity(script_code)
                result[skill_name] = {
                    "script_code": script_code,
                    "parameters": skill_data.get("parameters", []),
                    "description": skill_data.get("description", ""),
                    "complexity": complexity
                }
            
            return result
        except Exception as e:
            print(f"Error loading skill_cache.json: {e}")
            return {}
    
    @staticmethod
    def find_session_history(task_dir: str) -> Optional[str]:
        """
        Find the session history file in the task directory.
        
        Args:
            task_dir: Path to the task directory (e.g., dumps_skill_test/model/task/SingleUserTurn-xxx)
            
        Returns:
            Path to session_history.jsonl or None if not found
        """
        conversation_dir = os.path.join(task_dir, "conversation_history")
        if not os.path.isdir(conversation_dir):
            return None
            
        for file in os.listdir(conversation_dir):
            if file.endswith("_session_history.jsonl"):
                return os.path.join(conversation_dir, file)
        return None
    
    @staticmethod
    def parse_session_history(session_file: str) -> List[Dict]:
        """
        Parse the session history JSONL file.
        
        Args:
            session_file: Path to the session_history.jsonl file
            
        Returns:
            List of parsed JSON entries
        """
        entries = []
        try:
            with open(session_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            entries.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            print(f"Error reading session history: {e}")
        return entries
    
    @staticmethod
    def analyze_skill_usage(task_dir: str) -> Dict[str, Any]:
        """
        Analyze skill usage from conversation history.
        
        Args:
            task_dir: Path to the task directory
            
        Returns:
            Dictionary containing skill analysis results
        """
        result = {
            "skill_analysis": {
                "enabled": True,
                "tool_calls": {
                    "local-save_skill": 0,
                    "local-execute_skill": 0,
                    "local-get_skill": 0,
                    "local-list_skills": 0
                },
                "skills": {},  # skill_name -> {created, executions, complexity}
                "summary": {
                    "total_skills_created": 0,
                    "skills_created_successfully": 0,
                    "skills_creation_failed": 0,
                    "total_executions": 0,
                    "successful_executions": 0,
                    "failed_executions": 0,
                    "execution_success_rate": 0.0,
                    # Complexity metrics
                    "avg_complexity_score": 0.0,
                    "avg_tool_calls_per_skill": 0.0,
                    "total_tool_calls_in_skills": 0,
                    "avg_lines_of_code": 0.0
                }
            }
        }
        
        # Load skill complexity data from skill_cache.json
        skill_complexity_data = SkillAnalyzer.load_skill_cache(task_dir)
        
        # Find and parse session history
        session_file = SkillAnalyzer.find_session_history(task_dir)
        if not session_file:
            result["skill_analysis"]["enabled"] = False
            result["skill_analysis"]["error"] = "Session history file not found"
            return result
        
        entries = SkillAnalyzer.parse_session_history(session_file)
        if not entries:
            result["skill_analysis"]["enabled"] = False
            result["skill_analysis"]["error"] = "Empty or invalid session history"
            return result
        
        analysis = result["skill_analysis"]
        skills = analysis["skills"]
        
        # Track pending tool calls (call_id -> tool_name, args)
        pending_calls = {}
        
        for entry in entries:
            item_type = entry.get("item_type", "")
            raw_content = entry.get("raw_content", {})
            
            # Process tool calls
            if item_type == "tool_call_item":
                tool_name = raw_content.get("name", "")
                call_id = raw_content.get("call_id", "")
                arguments = raw_content.get("arguments", "{}")
                
                # Count tool calls
                if tool_name in SkillAnalyzer.SKILL_TOOLS:
                    analysis["tool_calls"][tool_name] += 1
                    
                    # Parse arguments
                    try:
                        args = json.loads(arguments) if isinstance(arguments, str) else arguments
                    except json.JSONDecodeError:
                        args = {}
                    
                    # Track pending call
                    pending_calls[call_id] = {
                        "tool": tool_name,
                        "args": args,
                        "skill_name": args.get("skill_name", "unknown")
                    }
                    
                    # Initialize skill entry if needed
                    skill_name = args.get("skill_name", "")
                    if skill_name and skill_name not in skills:
                        # Get complexity data if available
                        complexity_info = skill_complexity_data.get(skill_name, {})
                        complexity = complexity_info.get("complexity", {
                            "tool_calls": 0,
                            "loops": 0,
                            "conditionals": 0,
                            "lines_of_code": 0,
                            "complexity_score": 0.0
                        })
                        skills[skill_name] = {
                            "created": False,
                            "creation_error": None,
                            "executions": [],
                            "complexity": complexity
                        }
            
            # Process tool outputs
            elif item_type == "tool_call_output_item":
                call_id = raw_content.get("call_id", "")
                output = raw_content.get("output", "")
                
                if call_id in pending_calls:
                    call_info = pending_calls[call_id]
                    tool_name = call_info["tool"]
                    skill_name = call_info["skill_name"]
                    
                    if tool_name == "local-save_skill":
                        # Analyze save result
                        if skill_name in skills:
                            if "saved successfully" in output.lower() or "success" in output.lower():
                                skills[skill_name]["created"] = True
                            else:
                                skills[skill_name]["creation_error"] = output[:200]
                    
                    elif tool_name == "local-execute_skill":
                        # Analyze execution result
                        if skill_name in skills:
                            execution = {
                                "success": True,
                                "error": None
                            }
                            
                            # FIXED: Parse the output as JSON first to check actual status
                            # Don't rely on simple string matching which gives false positives
                            try:
                                # Try to parse as JSON (skill execution returns dict)
                                if output.startswith('{') or output.startswith("{'"):
                                    # Handle both JSON and Python dict repr
                                    import ast
                                    try:
                                        parsed = json.loads(output)
                                    except json.JSONDecodeError:
                                        # Try Python literal eval for dict repr
                                        parsed = ast.literal_eval(output)
                                    
                                    # Check actual status field
                                    status = parsed.get("status", "").lower()
                                    if status in ["error", "failed", "low_quality"]:
                                        execution["success"] = False
                                        execution["error"] = parsed.get("error_message") or parsed.get("error") or output[:300]
                                    elif status == "success":
                                        execution["success"] = True
                                        execution["error"] = None
                                    else:
                                        # Unknown status, check for error_type field
                                        if parsed.get("error_type") or parsed.get("error_message"):
                                            execution["success"] = False
                                            execution["error"] = parsed.get("error_message") or output[:300]
                                else:
                                    # Not JSON, use string matching as fallback
                                    output_lower = output.lower()
                                    # More specific error skills to avoid false positives
                                    if any(err in output_lower for err in [
                                        '"status": "error"', "'status': 'error'",
                                        "traceback (most recent", "syntaxerror:", 
                                        "nameerror:", "typeerror:", "keyerror:",
                                        "skill not found", "execution failed",
                                        "tool call failed", "could not find server"
                                    ]):
                                        execution["success"] = False
                                        execution["error"] = output[:300] if len(output) > 300 else output
                            except Exception:
                                # Parsing failed, use conservative string matching
                                output_lower = output.lower()
                                if any(err in output_lower for err in [
                                    '"status": "error"', "'status': 'error'",
                                    "traceback (most recent", "execution failed"
                                ]):
                                    execution["success"] = False
                                    execution["error"] = output[:300] if len(output) > 300 else output
                            
                            skills[skill_name]["executions"].append(execution)
                    
                    del pending_calls[call_id]
        
        # Calculate summary statistics
        summary = analysis["summary"]
        
        # Complexity accumulators
        total_complexity_score = 0.0
        total_tool_calls_in_skills = 0
        total_lines_of_code = 0
        skills_with_complexity = 0
        
        for skill_name, skill_data in skills.items():
            summary["total_skills_created"] += 1
            if skill_data["created"]:
                summary["skills_created_successfully"] += 1
            else:
                summary["skills_creation_failed"] += 1
            
            for execution in skill_data["executions"]:
                summary["total_executions"] += 1
                if execution["success"]:
                    summary["successful_executions"] += 1
                else:
                    summary["failed_executions"] += 1
            
            # Accumulate complexity metrics
            complexity = skill_data.get("complexity", {})
            if complexity and complexity.get("complexity_score", 0) > 0:
                total_complexity_score += complexity.get("complexity_score", 0)
                total_tool_calls_in_skills += complexity.get("tool_calls", 0)
                total_lines_of_code += complexity.get("lines_of_code", 0)
                skills_with_complexity += 1
        
        # Calculate success rate
        if summary["total_executions"] > 0:
            summary["execution_success_rate"] = round(
                summary["successful_executions"] / summary["total_executions"] * 100, 1
            )
        
        # Calculate average complexity metrics
        if skills_with_complexity > 0:
            summary["avg_complexity_score"] = round(total_complexity_score / skills_with_complexity, 2)
            summary["avg_tool_calls_per_skill"] = round(total_tool_calls_in_skills / skills_with_complexity, 2)
            summary["total_tool_calls_in_skills"] = total_tool_calls_in_skills
            summary["avg_lines_of_code"] = round(total_lines_of_code / skills_with_complexity, 2)
        
        return result
    
    @staticmethod
    def add_skill_analysis_to_eval_res(eval_res: Dict, task_dir: str) -> Dict:
        """
        Add skill analysis to an existing eval_res dictionary.
        
        Args:
            eval_res: Existing evaluation results dictionary
            task_dir: Path to the task directory
            
        Returns:
            Updated eval_res with skill analysis
        """
        skill_result = SkillAnalyzer.analyze_skill_usage(task_dir)
        eval_res["skill_analysis"] = skill_result["skill_analysis"]
        return eval_res
    
    @staticmethod
    def update_eval_res_file(eval_res_path: str) -> bool:
        """
        Update an existing eval_res.json file with skill analysis.
        
        Args:
            eval_res_path: Path to the eval_res.json file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Read existing eval_res
            with open(eval_res_path, 'r', encoding='utf-8') as f:
                eval_res = json.load(f)
            
            # Get task directory
            task_dir = os.path.dirname(eval_res_path)
            
            # Add skill analysis
            eval_res = SkillAnalyzer.add_skill_analysis_to_eval_res(eval_res, task_dir)
            
            # Write back
            with open(eval_res_path, 'w', encoding='utf-8') as f:
                json.dump(eval_res, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception as e:
            print(f"Error updating eval_res: {e}")
            return False


def batch_update_skill_analysis(dump_dir: str) -> Dict[str, Any]:
    """
    Batch update all eval_res.json files in a dump directory with skill analysis.
    
    Args:
        dump_dir: Path to the dump directory (e.g., dumps_skill_test)
        
    Returns:
        Summary of updates
    """
    summary = {
        "total_files": 0,
        "updated": 0,
        "failed": 0,
        "errors": []
    }
    
    # Find all eval_res.json files
    for root, dirs, files in os.walk(dump_dir):
        for file in files:
            if file == "eval_res.json":
                eval_res_path = os.path.join(root, file)
                summary["total_files"] += 1
                
                if SkillAnalyzer.update_eval_res_file(eval_res_path):
                    summary["updated"] += 1
                    print(f"Updated: {eval_res_path}")
                else:
                    summary["failed"] += 1
                    summary["errors"].append(eval_res_path)
    
    return summary


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # Update specific directory or file
        path = sys.argv[1]
        
        if os.path.isfile(path) and path.endswith("eval_res.json"):
            # Update single file
            if SkillAnalyzer.update_eval_res_file(path):
                print(f"Successfully updated: {path}")
            else:
                print(f"Failed to update: {path}")
        elif os.path.isdir(path):
            # Batch update directory
            summary = batch_update_skill_analysis(path)
            print(f"\nSummary:")
            print(f"  Total files: {summary['total_files']}")
            print(f"  Updated: {summary['updated']}")
            print(f"  Failed: {summary['failed']}")
        else:
            print(f"Invalid path: {path}")
    else:
        print("Usage: python skill_analyzer.py <eval_res.json | dump_directory>")

