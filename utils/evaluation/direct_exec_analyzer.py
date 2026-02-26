"""
Direct Exec Usage Analyzer for Toolathlon Direct-Exec Mode.

Analyzes workspace logs to extract detailed direct exec statistics:
- Script execution counts
- Success/failure rates
- Execution timing statistics
- Script complexity metrics
"""

import json
import os
import re
import ast
from typing import Dict, List, Any, Optional
from pathlib import Path


def calculate_script_complexity(script_code: str) -> Dict[str, Any]:
    """
    Calculate complexity metrics for a script.
    
    Complexity formula:
    complexity_score = tool_calls × 3 + loops × 2 + conditionals × 1 + (lines / 5)
    
    Args:
        script_code: The Python script code
        
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


class DirectExecAnalyzer:
    """Analyze direct exec usage from workspace logs."""
    
    @staticmethod
    def analyze_direct_exec_usage(task_dir: str) -> Dict[str, Any]:
        """
        Analyze direct exec usage from the workspace direct_exec_logs directory.
        
        Args:
            task_dir: Path to the task output directory (e.g., dumps_direct_exec/model/task/SingleUserTurn-e1)
            
        Returns:
            Dictionary with direct exec analysis results
        """
        result = {
            "direct_exec_analysis": {
                "enabled": False,
                "total_executions": 0,
                "successful": 0,
                "failed": 0,
                "success_rate": 0.0,
                "scripts": [],
                "timing_stats": {
                    "avg_duration_ms": 0.0,
                    "min_duration_ms": 0.0,
                    "max_duration_ms": 0.0,
                    "total_duration_ms": 0.0
                },
                "complexity_stats": {
                    "avg_tool_calls": 0.0,
                    "avg_lines": 0.0,
                    "total_tool_calls": 0,
                    "avg_complexity_score": 0.0
                }
            }
        }
        
        # Find workspace directory
        workspace_dir = os.path.join(task_dir, "workspace")
        if not os.path.isdir(workspace_dir):
            return result
        
        # Find direct_exec_logs directory
        logs_dir = os.path.join(workspace_dir, "direct_exec_logs")
        if not os.path.isdir(logs_dir):
            return result
        
        result["direct_exec_analysis"]["enabled"] = True
        
        # Try to read exec_history.json first
        history_path = os.path.join(logs_dir, "exec_history.json")
        if os.path.exists(history_path):
            try:
                with open(history_path, 'r', encoding='utf-8') as f:
                    history = json.load(f)
                    
                result["direct_exec_analysis"]["total_executions"] = history.get("total_executions", 0)
                result["direct_exec_analysis"]["successful"] = history.get("successful", 0)
                result["direct_exec_analysis"]["failed"] = history.get("failed", 0)
                result["direct_exec_analysis"]["success_rate"] = history.get("success_rate", 0.0)
                
                # Process individual executions
                executions = history.get("executions", [])
                scripts = []
                durations = []
                
                for exec_entry in executions:
                    script_info = {
                        "execution_index": exec_entry.get("execution_index"),
                        "script_id": exec_entry.get("script_id"),
                        "status": exec_entry.get("status"),
                        "timestamp": exec_entry.get("timestamp"),
                        "duration_ms": exec_entry.get("duration_ms", 0),
                        "script_lines": exec_entry.get("script_lines", 0)
                    }
                    
                    # Read script file for complexity analysis
                    script_id = exec_entry.get("script_id", "")
                    exec_idx = exec_entry.get("execution_index", 0)
                    script_file = os.path.join(logs_dir, f"script_{exec_idx:03d}_{script_id}.py")
                    
                    if os.path.exists(script_file):
                        try:
                            with open(script_file, 'r', encoding='utf-8') as sf:
                                script_content = sf.read()
                                # Remove header comments
                                lines = script_content.split('\n')
                                code_start = 0
                                for i, line in enumerate(lines):
                                    if not line.startswith('#') and line.strip():
                                        code_start = i
                                        break
                                actual_code = '\n'.join(lines[code_start:])
                                complexity = calculate_script_complexity(actual_code)
                                script_info["complexity"] = complexity
                        except Exception:
                            pass
                    
                    if exec_entry.get("error_type"):
                        script_info["error_type"] = exec_entry.get("error_type")
                        script_info["error_message"] = exec_entry.get("error_message")
                    
                    scripts.append(script_info)
                    if exec_entry.get("duration_ms"):
                        durations.append(exec_entry.get("duration_ms"))
                
                result["direct_exec_analysis"]["scripts"] = scripts
                
                # Calculate timing statistics
                if durations:
                    result["direct_exec_analysis"]["timing_stats"] = {
                        "avg_duration_ms": round(sum(durations) / len(durations), 2),
                        "min_duration_ms": round(min(durations), 2),
                        "max_duration_ms": round(max(durations), 2),
                        "total_duration_ms": round(sum(durations), 2)
                    }
                
                # Calculate complexity statistics
                complexities = [s.get("complexity", {}) for s in scripts if s.get("complexity")]
                if complexities:
                    total_tool_calls = sum(c.get("tool_calls", 0) for c in complexities)
                    total_lines = sum(c.get("lines_of_code", 0) for c in complexities)
                    total_complexity = sum(c.get("complexity_score", 0) for c in complexities)
                    
                    result["direct_exec_analysis"]["complexity_stats"] = {
                        "avg_tool_calls": round(total_tool_calls / len(complexities), 2),
                        "avg_lines": round(total_lines / len(complexities), 2),
                        "total_tool_calls": total_tool_calls,
                        "avg_complexity_score": round(total_complexity / len(complexities), 2)
                    }
                    
            except Exception as e:
                result["direct_exec_analysis"]["error"] = str(e)
        else:
            # Fallback: count script files directly
            script_files = [f for f in os.listdir(logs_dir) if f.startswith("script_") and f.endswith(".py")]
            result_files = [f for f in os.listdir(logs_dir) if f.startswith("result_") and f.endswith(".json")]
            
            result["direct_exec_analysis"]["total_executions"] = len(script_files)
            
            # Count successes by checking result files
            successful = 0
            for rf in result_files:
                try:
                    result_path = os.path.join(logs_dir, rf)
                    with open(result_path, 'r', encoding='utf-8') as f:
                        res = json.load(f)
                        if res.get("status") == "success":
                            successful += 1
                except Exception:
                    pass
            
            result["direct_exec_analysis"]["successful"] = successful
            result["direct_exec_analysis"]["failed"] = len(script_files) - successful
            if len(script_files) > 0:
                result["direct_exec_analysis"]["success_rate"] = round(successful / len(script_files) * 100, 2)
        
        return result
    
    @staticmethod
    def get_summary_stats(task_dir: str) -> Dict[str, Any]:
        """
        Get a simplified summary of direct exec stats for quick reporting.
        
        Args:
            task_dir: Path to the task output directory
            
        Returns:
            Dictionary with summary statistics
        """
        full_analysis = DirectExecAnalyzer.analyze_direct_exec_usage(task_dir)
        analysis = full_analysis.get("direct_exec_analysis", {})
        
        return {
            "enabled": analysis.get("enabled", False),
            "total_executions": analysis.get("total_executions", 0),
            "successful": analysis.get("successful", 0),
            "failed": analysis.get("failed", 0),
            "success_rate": analysis.get("success_rate", 0.0),
            "avg_duration_ms": analysis.get("timing_stats", {}).get("avg_duration_ms", 0.0),
            "total_tool_calls": analysis.get("complexity_stats", {}).get("total_tool_calls", 0)
        }
