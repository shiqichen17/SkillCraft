"""
Cross-Task Skill Mode Runner

This module manages skill sharing across different difficulty levels of the same base task.
For example, skills created in pokeapi-pokedex/e1 can be reused in e2, e3, m1, m2, h1.

Usage:
    python test_all_tasks.py --scaled-tasks --cross-task --base pokeapi-pokedex
"""

import json
import os
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

# Import skill formatting function
from utils.aux_tools.skill_cache import get_skills_summary_for_prompt


class CrossTaskRunner:
    """
    Manages cross-task skill sharing within a task group.
    
    A task group consists of different difficulty levels of the same base task:
    e.g., pokeapi-pokedex/e1, pokeapi-pokedex/e2, ..., pokeapi-pokedex/h1
    
    Attributes:
        base_task: The base task name (e.g., "pokeapi-pokedex")
        run_dir: The root directory for this test run
        shared_cache_dir: Directory for shared skill cache
        shared_cache_file: Path to the shared skill_cache.json
    """
    
    # Execution order for difficulty levels
    LEVEL_ORDER = ["e1", "e2", "e3", "m1", "m2", "m3", "h1", "h2", "h3"]
    
    def __init__(self, base_task: str, run_dir: Path, dump_dir: Path = None):
        """
        Initialize CrossTaskRunner for a specific base task.
        
        Args:
            base_task: The base task name (e.g., "pokeapi-pokedex")
            run_dir: The root directory for this test run
            dump_dir: The directory for cross-task dumps (default: run_dir / "dumps_cross_task")
        """
        self.base_task = base_task
        self.run_dir = Path(run_dir)
        self.dump_dir = Path(dump_dir) if dump_dir else self.run_dir / "dumps_cross_task"
        
        # Create shared cache directory under dump_dir/shared/{base_task}
        self.shared_cache_dir = self.dump_dir / "shared" / base_task
        self.shared_cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Shared skill cache file
        self.shared_cache_file = self.shared_cache_dir / "skill_cache.json"
        
        # Execution log
        self.execution_log_file = self.shared_cache_dir / "execution_log.json"
        self.execution_log = self._load_execution_log()
        
    def _load_execution_log(self) -> Dict:
        """Load or initialize execution log."""
        if self.execution_log_file.exists():
            with open(self.execution_log_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            "base_task": self.base_task,
            "created_at": datetime.now().isoformat(),
            "levels_completed": [],
            "skills_created": {},
            "skills_reused": {},
            "level_results": {}
        }
    
    def _save_execution_log(self):
        """Save execution log to file."""
        with open(self.execution_log_file, 'w', encoding='utf-8') as f:
            json.dump(self.execution_log, f, indent=2, ensure_ascii=False)
    
    def get_existing_skills(self) -> Dict[str, Dict]:
        """
        Read existing skills from shared cache.
        
        Returns:
            Dictionary of skill_name -> skill_data
        """
        if self.shared_cache_file.exists():
            try:
                with open(self.shared_cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get("skills", {})
            except (json.JSONDecodeError, IOError) as e:
                print(f"[WARNING] Could not load shared skill cache: {e}")
        return {}
    
    def get_skills_summary(self) -> str:
        """
        Get a detailed summary of existing skills for injection into system prompt.
        
        Uses the formatted output from skill_cache module which includes:
        - Skill name and description
        - Input parameters
        - Output format hints
        - Execution history and last status
        - Usage example
        
        Returns:
            Formatted string describing available skills
        """
        skills = self.get_existing_skills()
        if not skills:
            return ""
        
        # Use the detailed formatting function from skill_cache
        return get_skills_summary_for_prompt(skills)
    
    def sync_skills_to_workspace(self, workspace: Path):
        """
        Copy shared skill cache to task workspace before execution.
        
        Args:
            workspace: The task's workspace directory
        """
        workspace = Path(workspace)
        workspace.mkdir(parents=True, exist_ok=True)
        
        if self.shared_cache_file.exists():
            target_file = workspace / "skill_cache.json"
            shutil.copy(self.shared_cache_file, target_file)
            print(f"[CROSS-TASK] Synced {len(self.get_existing_skills())} skills to workspace")
        else:
            print("[CROSS-TASK] No existing skills to sync (first task in group)")
    
    def collect_skills_from_workspace(self, workspace: Path, level: str):
        """
        Collect skills from task workspace after execution and merge into shared cache.
        
        Args:
            workspace: The task's workspace directory
            level: The difficulty level (e.g., "e1", "m1")
        """
        workspace = Path(workspace)
        task_cache_file = workspace / "skill_cache.json"
        
        if not task_cache_file.exists():
            print(f"[CROSS-TASK] No skill cache found in workspace for {level}")
            return
        
        try:
            with open(task_cache_file, 'r', encoding='utf-8') as f:
                task_cache = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"[WARNING] Could not read task skill cache: {e}")
            return
        
        task_skills = task_cache.get("skills", {})
        if not task_skills:
            print(f"[CROSS-TASK] No skills created in {level}")
            return
        
        # Load existing shared cache
        shared_cache = {"skills": {}, "metadata": {}}
        if self.shared_cache_file.exists():
            try:
                with open(self.shared_cache_file, 'r', encoding='utf-8') as f:
                    shared_cache = json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        
        # Merge skills (new skills override old ones with same name)
        existing_skills = shared_cache.get("skills", {})
        new_skill_count = 0
        updated_skill_count = 0
        
        for name, skill in task_skills.items():
            if name in existing_skills:
                updated_skill_count += 1
            else:
                new_skill_count += 1
            
            # Add source level info
            skill["source_level"] = level
            skill["added_at"] = datetime.now().isoformat()
            existing_skills[name] = skill
        
        shared_cache["skills"] = existing_skills
        shared_cache["metadata"] = {
            "base_task": self.base_task,
            "last_updated": datetime.now().isoformat(),
            "last_level": level,
            "total_skills": len(existing_skills)
        }
        
        # Save merged cache
        with open(self.shared_cache_file, 'w', encoding='utf-8') as f:
            json.dump(shared_cache, f, indent=2, ensure_ascii=False)
        
        print(f"[CROSS-TASK] Collected skills from {level}: {new_skill_count} new, {updated_skill_count} updated")
        print(f"[CROSS-TASK] Total skills in shared cache: {len(existing_skills)}")
        
        # Update execution log
        self.execution_log["skills_created"][level] = list(task_skills.keys())
        self._save_execution_log()
    
    def record_level_result(self, level: str, result: Dict):
        """
        Record the result of executing a task level.
        
        Args:
            level: The difficulty level (e.g., "e1", "m1")
            result: The task result dictionary
        """
        self.execution_log["levels_completed"].append(level)
        self.execution_log["level_results"][level] = {
            "success": result.get("success", False),
            "eval_pass": result.get("eval_pass", False),
            "eval_score_percent": result.get("eval_score_percent", 0),
            "save_skill_calls": result.get("save_skill_calls", 0),
            "execute_skill_calls": result.get("execute_skill_calls", 0),
            "skill_execution_success_rate": result.get("skill_execution_success_rate", 0),
            "cost_usd": result.get("actual_cost_usd") or result.get("agent_cost", {}).get("total_cost", 0),
            "completed_at": datetime.now().isoformat()
        }
        self._save_execution_log()
    
    def get_summary(self) -> Dict:
        """
        Get a summary of the cross-task execution.
        
        Returns:
            Summary dictionary with statistics
        """
        levels_completed = self.execution_log.get("levels_completed", [])
        level_results = self.execution_log.get("level_results", {})
        skills = self.get_existing_skills()
        
        total_cost = sum(r.get("cost_usd", 0) for r in level_results.values())
        successful_levels = sum(1 for r in level_results.values() if r.get("eval_pass", False))
        
        return {
            "base_task": self.base_task,
            "levels_completed": len(levels_completed),
            "levels_passed": successful_levels,
            "total_skills": len(skills),
            "total_cost_usd": total_cost,
            "skills_by_level": self.execution_log.get("skills_created", {}),
            "level_results": level_results
        }
    
    @staticmethod
    def sort_levels(levels: List[str]) -> List[str]:
        """
        Sort difficulty levels in execution order: e1 < e2 < ... < m1 < m2 < ... < h1 < h2 < ...
        
        Args:
            levels: List of level strings
            
        Returns:
            Sorted list of levels
        """
        def level_sort_key(lvl: str) -> tuple:
            # Extract prefix (e/m/h) and number
            prefix = lvl[0] if lvl else 'z'
            try:
                num = int(lvl[1:]) if len(lvl) > 1 else 0
            except ValueError:
                num = 0
            
            # Order: e < m < h
            prefix_order = {'e': 0, 'm': 1, 'h': 2}.get(prefix, 3)
            return (prefix_order, num)
        
        return sorted(levels, key=level_sort_key)


def get_cross_task_config(existing_skills: Dict[str, Dict], shared_cache_path: Optional[Path] = None) -> Dict:
    """
    Generate configuration for cross-task mode.
    
    This can be passed to task execution to enable skill sharing.
    
    Args:
        existing_skills: Dictionary of existing skills
        shared_cache_path: Path to shared skill cache file
        
    Returns:
        Configuration dictionary for cross-task mode
    """
    return {
        "cross_task_mode": True,
        "existing_skills": existing_skills,
        "shared_cache_path": str(shared_cache_path) if shared_cache_path else None,
        "skills_summary": _format_skills_summary(existing_skills) if existing_skills else ""
    }


def _format_skills_summary(skills: Dict[str, Dict]) -> str:
    """Format skills into a summary string for prompt injection."""
    if not skills:
        return ""
    
    lines = []
    for name, skill in skills.items():
        desc = skill.get("description", "")
        params = skill.get("parameters", [])
        lines.append(f"- {name}({', '.join(params)}): {desc}")
    
    return "\n".join(lines)
