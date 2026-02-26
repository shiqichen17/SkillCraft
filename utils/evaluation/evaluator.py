from typing import Dict, Any, List, Optional
from utils.roles.task_agent import TaskStatus
from utils.data_structures.task_config import TaskConfig
from utils.general.helper import run_command, read_json, write_json
from utils.evaluation.skill_analyzer import SkillAnalyzer
from utils.evaluation.direct_exec_analyzer import DirectExecAnalyzer
import logging
import os
import json
import re


def parse_score_from_output(output: str) -> Optional[Dict]:
    """
    Parse scoring JSON from evaluation output.
    
    Looks for content between === SCORE_JSON_START === and === SCORE_JSON_END ===
    """
    skill = r'=== SCORE_JSON_START ===\s*(.+?)\s*=== SCORE_JSON_END ==='
    match = re.search(skill, output, re.DOTALL)
    
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            return None
    return None


# Common internal/metadata files to exclude from fallback detection
EXCLUDED_FALLBACK_FILES = {
    'skill_cache.json',
    'kids.json',  # Used by some tasks as initial data
    '.metadata.json',
    'config.json',
    'task_config.json',
}


def find_candidate_result_files(workspace: str) -> List[str]:
    """
    Find candidate result files in workspace for fallback evaluation.
    
    Returns a list of JSON files that could be task outputs, sorted by
    likelihood of being the actual result (larger files first, common
    naming skills prioritized).
    """
    if not workspace or not os.path.isdir(workspace):
        return []
    
    candidates = []
    for filename in os.listdir(workspace):
        if not filename.endswith('.json'):
            continue
        if filename in EXCLUDED_FALLBACK_FILES:
            continue
        if filename.startswith('.'):
            continue
            
        filepath = os.path.join(workspace, filename)
        if not os.path.isfile(filepath):
            continue
            
        filesize = os.path.getsize(filepath)
        if filesize < 10:  # Ignore nearly empty files
            continue
        
        # Prioritize common result file naming skills
        priority = 0
        lower_name = filename.lower()
        if any(kw in lower_name for kw in ['result', 'output', 'report', 'data', 'analysis']):
            priority = 3
        elif any(kw in lower_name for kw in ['encyclopedia', 'database', 'collection', 'cookbook', 'compendium']):
            priority = 2
        elif '_' in filename or '-' in filename:  # Structured names more likely to be outputs
            priority = 1
            
        candidates.append((filename, filesize, priority))
    
    # Sort by priority (descending), then by filesize (descending)
    candidates.sort(key=lambda x: (-x[2], -x[1]))
    return [c[0] for c in candidates]


def extract_expected_output_from_task(task_config: 'TaskConfig') -> Optional[str]:
    """
    Try to extract the expected output filename from task description.
    
    Looks for skills like:
    - "Save results to `filename.json`"
    - "Output file: filename.json"
    - "Create filename.json"
    """
    task_str = task_config.task_str or ""
    
    # Common skills for output file specification
    skills = [
        r'[Ss]ave.*?[`"\']([a-zA-Z0-9_-]+\.json)[`"\']',
        r'[Oo]utput\s+[Ff]ile[:\s]+[`"\']?([a-zA-Z0-9_-]+\.json)[`"\']?',
        r'[Cc]reate\s+[`"\']?([a-zA-Z0-9_-]+\.json)[`"\']?',
        r'[Gg]enerate\s+[`"\']?([a-zA-Z0-9_-]+\.json)[`"\']?',
        r'[Ww]rite.*?to\s+[`"\']?([a-zA-Z0-9_-]+\.json)[`"\']?',
        r'[Ff]inal.*?[`"\']([a-zA-Z0-9_-]+\.json)[`"\']',
    ]
    
    for skill in skills:
        match = re.search(skill, task_str)
        if match:
            return match.group(1)
    
    return None


class TaskEvaluator:
    """Task evaluator"""
    
    @staticmethod
    async def evaluate_one(dump_line: Dict[str, Any]) -> Dict[str, Any]:
        """
        Single task evaluation
        Expected content to be checked:
        - user response: check all outputs from user side
        - response: check all outputs from llm
        - tool calls: check all tool calls from llm
        - tool outputs: check all tool outputs
        ====== The following checks need to be started from config ======
        - local status: check files in specific workspace directory (e.g. saved some things, modified some things etc)
        - remote status: manually call MCP server to check if remote status is normally modified [not sure if possible]
        Use the above content to determine whether the task execution is successful or not
        """
        task_config = TaskConfig.from_dict(dump_line['config'])
        task_status = dump_line['status']
        # Prepare information for evaluation
        res_log_file = task_config.log_file
        agent_workspace = task_config.agent_workspace
        groundtruth_workspace = task_config.evaluation.groundtruth_workspace
        eval_command = task_config.evaluation.evaluation_command
        launch_time = task_config.launch_time
        print(f"launch time in eval is {launch_time}")

        # Check task status: only SUCCESS is possible to pass normally
        # BUT: if eval_command exists and workspace has output files, run evaluation anyway (fallback mode)
        # This handles cases where agent completed the work but forgot to call claim_done
        is_fallback_mode = False
        fallback_details = []
        
        if task_status != TaskStatus.SUCCESS.value:
            # Check if we should run fallback evaluation
            should_fallback = False
            found_files = []
            expected_file = None
            
            if eval_command and agent_workspace:
                # Strategy 1: Try to find the expected output file from task description
                expected_file = extract_expected_output_from_task(task_config)
                if expected_file:
                    expected_path = os.path.join(agent_workspace, expected_file)
                    if os.path.isfile(expected_path) and os.path.getsize(expected_path) > 10:
                        should_fallback = True
                        found_files.append(expected_file)
                        fallback_details.append(f"Found expected output file '{expected_file}'")
                        print(f"[FALLBACK] Found expected output file '{expected_file}' in workspace, will run evaluation despite task status={task_status}")
                
                # Strategy 2: If expected file not found, look for any candidate result files
                if not should_fallback:
                    candidates = find_candidate_result_files(agent_workspace)
                    if candidates:
                        should_fallback = True
                        found_files = candidates[:3]  # Report up to 3 files
                        fallback_details.append(f"Found candidate output files: {', '.join(found_files)}")
                        print(f"[FALLBACK] Found candidate output file(s) {found_files} in workspace, will run evaluation despite task status={task_status}")
            
            if not should_fallback:
                return {
                    "pass": None,
                    "details": f"Task status: {task_status}, only SUCCESS counts as pass; pass is null. No output files found for fallback evaluation."
                }
            
            is_fallback_mode = True
            fallback_details.append(f"Original task_status={task_status}")
            fallback_details.append("Agent likely completed work but didn't call claim_done")

        # Evaluate all content (only when task status is SUCCESS)
        if eval_command is not None:
            args = f"--res_log_file {res_log_file} --agent_workspace {agent_workspace} --groundtruth_workspace {groundtruth_workspace} --launch_time \"{launch_time}\""
            command = f"{eval_command} {args}"
            output, error, returncode = await run_command(command, debug=True)
            print("== Evaluation STDOUT ==")
            print(output)
            print("== Evaluation STDERR ==")
            print(error)
            
            # Try to parse scoring JSON from output
            score_data = parse_score_from_output(output)
            
            if score_data:
                # New scoring system
                result = {
                    "pass": score_data.get("passed", False),
                    "status": score_data.get("status", "unknown"),
                    "score": score_data.get("score", {}),
                    "score_percent": score_data.get("score", {}).get("percent", 0),
                    "items": score_data.get("items", []),
                    "errors": score_data.get("errors", []),
                    "warnings": score_data.get("warnings", []),
                    "details": f"Score: {score_data.get('score', {}).get('percent', 0):.1f}%",
                    "failure": output if not score_data.get("passed") else None
                }
                # Add fallback mode indicator
                if is_fallback_mode:
                    result["fallback_mode"] = True
                    result["original_task_status"] = task_status
                    result["fallback_details"] = fallback_details
                    result["warnings"] = result.get("warnings", []) + [
                        f"Evaluated in FALLBACK mode: {'; '.join(fallback_details)}"
                    ]
                return result
            else:
                # Legacy pass/fail system
                if returncode == 0:
                    result = {
                        "pass": True,
                        "status": "pass",
                        "score": {"achieved": 100, "max": 100, "percent": 100.0},
                        "details": "All evaluation checks passed"
                    }
                elif returncode == 2:
                    # Partial credit (special exit code)
                    result = {
                        "pass": False,
                        "status": "partial",
                        "score": {"achieved": 50, "max": 100, "percent": 50.0},
                        "details": "Partial completion",
                        "failure": output
                    }
                else:
                    result = {
                        "pass": False,
                        "status": "fail",
                        "score": {"achieved": 0, "max": 100, "percent": 0.0},
                        "failure": output,
                    }
                # Add fallback mode indicator
                if is_fallback_mode:
                    result["fallback_mode"] = True
                    result["original_task_status"] = task_status
                    result["fallback_details"] = fallback_details
                    result["warnings"] = [
                        f"Evaluated in FALLBACK mode: {'; '.join(fallback_details)}"
                    ]
                return result
                
        # No eval command - default to pass
        result = {
            "pass": True,
            "status": "pass",
            "score": {"achieved": 100, "max": 100, "percent": 100.0},
            "details": "No evaluation command, task status is success"
        }
        if is_fallback_mode:
            result["fallback_mode"] = True
            result["original_task_status"] = task_status
            result["fallback_details"] = fallback_details
            result["warnings"] = [
                f"Evaluated in FALLBACK mode: {'; '.join(fallback_details)}"
            ]
        return result
    
    @staticmethod
    async def evaluate_from_log_file(log_file_path: str, allow_resume: bool = False, 
                                      add_skill_analysis: bool = True,
                                      add_direct_exec_analysis: bool = False) -> Dict[str, Any]:
        """Evaluate task from log file
        
        Args:
            log_file_path: Path to the traj_log.json file
            allow_resume: If True, load existing eval_res if available
            add_skill_analysis: If True, add skill usage analysis (for skill mode)
            add_direct_exec_analysis: If True, add direct exec usage analysis (for direct-exec mode)
        """
        try:            
            if not os.path.exists(log_file_path):
                return {
                    "pass": False,
                    "failure": "log_file_not_found",
                    "details": f"Log file not found: {log_file_path}"
                }
            
            task_dir = os.path.dirname(log_file_path)
            eval_file_path = os.path.join(task_dir, "eval_res.json")
            
            # if allow_resume AND we can load pre exist eval res, we just load it
            if allow_resume and os.path.exists(eval_file_path):
                eval_res = read_json(eval_file_path)
                return eval_res
            
            # otherwise, we do real eval and store the eval result
            dump_line = read_json(log_file_path)
            eval_res = await TaskEvaluator.evaluate_one(dump_line)
            
            # Add skill analysis if requested (typically for skill mode)
            if add_skill_analysis:
                try:
                    skill_result = SkillAnalyzer.analyze_skill_usage(task_dir)
                    eval_res["skill_analysis"] = skill_result.get("skill_analysis", {})
                except Exception as pe:
                    logging.warning(f"Skill analysis failed: {pe}")
                    eval_res["skill_analysis"] = {
                        "enabled": False,
                        "error": str(pe)
                    }
            
            # Add direct exec analysis if requested (for direct-exec mode)
            if add_direct_exec_analysis:
                try:
                    direct_exec_result = DirectExecAnalyzer.analyze_direct_exec_usage(task_dir)
                    eval_res["direct_exec_analysis"] = direct_exec_result.get("direct_exec_analysis", {})
                except Exception as de:
                    logging.warning(f"Direct exec analysis failed: {de}")
                    eval_res["direct_exec_analysis"] = {
                        "enabled": False,
                        "error": str(de)
                    }
            
            write_json(eval_res, eval_file_path)
            return eval_res
            
        except Exception as e:
            logging.error(f"Error evaluating from log file {log_file_path}: {e}")
            return {
                "pass": False,
                "failure": "evaluation_error",
                "details": str(e)
            }
    
    @staticmethod
    async def batch_evaluate(run_results: List[Dict[str, Any]], allow_resume: bool=False) -> List[Dict[str, Any]]:
        """Batch evaluate task results"""
        eval_results = []
        
        for run_result in run_results:
            eval_result = {
                "task_config_path": run_result["task_config_path"],
                "task_id": run_result.get("task_id", "unknown"),
            }
            
            if not run_result.get("success", False):
                eval_result["evaluation"] = {
                    "pass": False,
                    "failure": "task_execution_failed",
                    "details": run_result.get("error", "Unknown error")
                }
            else:
                log_file = run_result.get("log_file")
                if log_file:
                    eval_result["evaluation"] = await TaskEvaluator.evaluate_from_log_file(log_file, allow_resume = allow_resume)
                else:
                    eval_result["evaluation"] = {
                        "pass": False,
                        "failure": "no_log_file",
                        "details": "No log file generated"
                    }
            
            eval_result["pass"] = eval_result["evaluation"]["pass"]
            eval_results.append(eval_result)
        
        return eval_results