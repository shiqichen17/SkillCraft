"""
Static Skill Mode Runner

This module manages static skill loading from an external directory.
Unlike cross-task mode where skills are created and accumulated during execution,
static-skill mode loads pre-existing skills from a specified directory and
does NOT allow the agent to create new skills.

Key differences from cross-task mode:
1. Skills are loaded from external directory (--skill-source)
2. Agent cannot create new skills (save_skill disabled)
3. Can filter which difficulty levels to load skills from (--source-levels)
4. Can filter which difficulty levels to run tasks on (--target-levels)

Usage:
    python test_all_tasks.py --static-skill \
        --skill-source /path/to/dumps_cross_task/model/scaled_tasks \
        --source-levels e \
        --target-levels h \
        --scaled-tasks
"""

import json
import os
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Set, Any
from datetime import datetime

# Import skill formatting function
from utils.aux_tools.skill_cache import get_skills_summary_for_prompt


class StaticReuseRunner:
    """
    Manages static skill loading for test execution.
    
    Unlike CrossTaskRunner, this class:
    - Loads skills from an external source directory
    - Does NOT collect new skills from task execution
    - Supports filtering by source difficulty levels
    
    Attributes:
        skill_source: The external directory containing skill caches
        source_levels: Which difficulty levels to load skills from
        loaded_skills: Dictionary of loaded skills
    """
    
    # Difficulty level hierarchy
    LEVEL_ORDER = ["e1", "e2", "e3", "m1", "m2", "m3", "h1", "h2", "h3"]
    
    def __init__(
        self, 
        skill_source: str,
        source_levels: Optional[List[str]] = None,
        run_dir: Path = None,
        dump_dir: Path = None
    ):
        """
        Initialize StaticReuseRunner.
        
        Args:
            skill_source: Path to the external skill cache directory
                           (e.g., /path/to/dumps_cross_task/model/scaled_tasks)
            source_levels: List of difficulty levels to load skills from.
                          If None, loads all available skills.
                          Examples: ["e1", "e2", "e3"] or ["e"] or ["e1"]
            run_dir: The root directory for this test run
            dump_dir: The directory for static-skill dumps
        """
        self.skill_source = Path(skill_source)
        self.source_levels = self._expand_source_levels(source_levels) if source_levels else None
        self.run_dir = Path(run_dir) if run_dir else None
        self.dump_dir = Path(dump_dir) if dump_dir else (self.run_dir / "dumps_static_skill" if self.run_dir else None)
        
        # Cache for loaded skills per task group
        self._loaded_skills_cache: Dict[str, Dict[str, Any]] = {}
        
        # Execution log
        self.execution_log = {
            "skill_source": str(self.skill_source),
            "source_levels": source_levels,
            "expanded_source_levels": self.source_levels,
            "created_at": datetime.now().isoformat(),
            "task_groups_loaded": {},
            "tasks_executed": []
        }
        
        print(f"[STATIC-REUSE] Initialized")
        print(f"  Skill source: {self.skill_source}")
        print(f"  Source levels: {self.source_levels or 'all'}")
    
    def _expand_source_levels(self, levels: List[str]) -> List[str]:
        """
        Expand level specifications to concrete level names.
        
        Args:
            levels: List of level specs (e.g., ["e", "m1"])
            
        Returns:
            Expanded list of concrete level names (e.g., ["e1", "e2", "e3", "m1"])
        """
        if not levels:
            return None
        
        expanded = set()
        for level in levels:
            level = level.strip().lower()
            if len(level) == 1 and level in ('e', 'm', 'h'):
                # Expand prefix to all levels with that prefix
                expanded.update(l for l in self.LEVEL_ORDER if l.startswith(level))
            else:
                # Specific level (e.g., "e1", "m2")
                expanded.add(level)
        
        # Sort by level order
        return sorted(list(expanded), key=lambda x: self.LEVEL_ORDER.index(x) if x in self.LEVEL_ORDER else 99)
    
    def load_skills_for_task_group(self, task_group: str) -> Dict[str, Any]:
        """
        Load skills for a specific task group from the source directory.
        
        Args:
            task_group: The task group name (e.g., "gitlab-deep-analysis")
            
        Returns:
            Dictionary of skill_name -> skill_data
        """
        # Check cache first
        if task_group in self._loaded_skills_cache:
            return self._loaded_skills_cache[task_group]
        
        skills = {}
        task_group_dir = self.skill_source / task_group
        
        if not task_group_dir.exists():
            print(f"[STATIC-REUSE] Warning: Task group directory not found: {task_group_dir}")
            self._loaded_skills_cache[task_group] = {}
            return {}
        
        # Find all skill cache files
        levels_loaded = []
        for level_dir in task_group_dir.iterdir():
            if not level_dir.is_dir():
                continue
            
            # Extract level from directory name (e.g., "SingleUserTurn-e1" -> "e1")
            level = level_dir.name.replace("SingleUserTurn-", "")
            
            # Check if this level should be loaded
            if self.source_levels and level not in self.source_levels:
                continue
            
            # Look for skill_cache.json
            skill_cache_file = level_dir / "skill_cache.json"
            if not skill_cache_file.exists():
                skill_cache_file = level_dir / "workspace" / "skill_cache.json"
            
            if skill_cache_file.exists():
                try:
                    with open(skill_cache_file, 'r', encoding='utf-8') as f:
                        cache_data = json.load(f)
                    
                    level_skills = cache_data.get("skills", {})
                    
                    # Filter and add source info to each skill
                    loaded_count = 0
                    skipped_count = 0
                    for name, skill in level_skills.items():
                        # Skip skills with failed last execution status
                        # Check nested execution_stats.last_execution_status field
                        exec_stats = skill.get("execution_stats", {})
                        last_status = exec_stats.get("last_execution_status", "success")
                        # Also check top-level field for backward compatibility
                        if not exec_stats:
                            last_status = skill.get("last_execution_status", "success")
                        
                        if last_status != "success":
                            skipped_count += 1
                            print(f"    [STATIC-REUSE] Skipping skill '{name}' (last_execution_status={last_status})")
                            continue
                        
                        skill["source_level"] = level
                        skill["source_task_group"] = task_group
                        skills[name] = skill
                        loaded_count += 1
                    
                    levels_loaded.append(level)
                    skip_info = f", skipped {skipped_count} failed" if skipped_count > 0 else ""
                    print(f"  [STATIC-REUSE] Loaded {loaded_count} skills from {task_group}/{level}{skip_info}")
                    
                except (json.JSONDecodeError, IOError) as e:
                    print(f"  [STATIC-REUSE] Warning: Could not load {skill_cache_file}: {e}")
        
        # Update execution log
        self.execution_log["task_groups_loaded"][task_group] = {
            "levels_loaded": levels_loaded,
            "skills_count": len(skills),
            "skill_names": list(skills.keys())
        }
        
        # Cache the results
        self._loaded_skills_cache[task_group] = skills
        
        print(f"[STATIC-REUSE] Loaded {len(skills)} total skills for {task_group} from levels: {levels_loaded}")
        return skills
    
    def get_skills_summary(self, task_group: str) -> str:
        """
        Get a formatted summary of loaded skills for injection into system prompt.
        
        Args:
            task_group: The task group name
            
        Returns:
            Formatted string describing available skills
        """
        skills = self.load_skills_for_task_group(task_group)
        if not skills:
            return ""
        
        return get_skills_summary_for_prompt(skills)
    
    def sync_skills_to_workspace(self, workspace: Path, task_group: str):
        """
        Copy loaded skills to task workspace before execution.
        
        Args:
            workspace: The task's workspace directory
            task_group: The task group name (to load correct skills)
        """
        workspace = Path(workspace)
        workspace.mkdir(parents=True, exist_ok=True)
        
        skills = self.load_skills_for_task_group(task_group)
        
        if skills:
            # Create skill cache structure
            cache_data = {
                "skills": skills,
                "metadata": {
                    "source": str(self.skill_source),
                    "source_levels": self.source_levels,
                    "task_group": task_group,
                    "loaded_at": datetime.now().isoformat(),
                    "mode": "static_skill",
                    "read_only": True  # Flag to indicate skills should not be modified
                }
            }
            
            target_file = workspace / "skill_cache.json"
            with open(target_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
            
            print(f"[STATIC-REUSE] Synced {len(skills)} skills to workspace")
        else:
            print("[STATIC-REUSE] No skills to sync")
    
    def record_task_result(self, task_path: str, result: Dict):
        """
        Record the result of executing a task.
        
        Args:
            task_path: The task path (e.g., "scaled_tasks/gitlab-deep-analysis/e1")
            result: The task result dictionary
        """
        self.execution_log["tasks_executed"].append({
            "task_path": task_path,
            "success": result.get("success", False),
            "eval_score_percent": result.get("eval_score_percent", 0),
            "execute_skill_calls": result.get("execute_skill_calls", 0),
            "skill_execution_success_rate": result.get("skill_execution_success_rate", 0),
            "completed_at": datetime.now().isoformat()
        })
    
    def save_execution_log(self):
        """Save execution log to file."""
        if self.dump_dir:
            self.dump_dir.mkdir(parents=True, exist_ok=True)
            log_file = self.dump_dir / "static_skill_execution_log.json"
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(self.execution_log, f, indent=2, ensure_ascii=False)
            print(f"[STATIC-REUSE] Execution log saved to: {log_file}")
    
    def get_summary(self) -> Dict:
        """
        Get a summary of the static reuse execution.
        
        Returns:
            Summary dictionary with statistics
        """
        tasks = self.execution_log.get("tasks_executed", [])
        successful = sum(1 for t in tasks if t.get("success", False))
        
        return {
            "skill_source": str(self.skill_source),
            "source_levels": self.source_levels,
            "task_groups_loaded": len(self.execution_log.get("task_groups_loaded", {})),
            "total_skills_loaded": sum(
                g.get("skills_count", 0) 
                for g in self.execution_log.get("task_groups_loaded", {}).values()
            ),
            "tasks_executed": len(tasks),
            "tasks_successful": successful,
            "success_rate": successful / len(tasks) * 100 if tasks else 0
        }
    
    @staticmethod
    def parse_target_levels(target_levels_str: Optional[str]) -> Optional[List[str]]:
        """
        Parse --target-levels argument into concrete level names.
        
        Args:
            target_levels_str: Comma-separated level specs (e.g., "h", "m,h", "h1")
            
        Returns:
            List of concrete level names, or None for all levels
        """
        if not target_levels_str:
            return None
        
        level_order = ["e1", "e2", "e3", "m1", "m2", "m3", "h1", "h2", "h3"]
        
        levels = set()
        for spec in target_levels_str.split(","):
            spec = spec.strip().lower()
            if len(spec) == 1 and spec in ('e', 'm', 'h'):
                # Expand prefix
                levels.update(l for l in level_order if l.startswith(spec))
            else:
                levels.add(spec)
        
        return sorted(list(levels), key=lambda x: level_order.index(x) if x in level_order else 99)
    
    @staticmethod
    def filter_tasks_by_levels(tasks: List[str], target_levels: Optional[List[str]]) -> List[str]:
        """
        Filter task paths by target difficulty levels.
        
        Args:
            tasks: List of task paths (e.g., ["scaled_tasks/xxx/e1", "scaled_tasks/xxx/e2"])
            target_levels: List of levels to keep, or None to keep all
            
        Returns:
            Filtered list of task paths
        """
        if not target_levels:
            return tasks
        
        filtered = []
        for task in tasks:
            # Extract level from path (e.g., "scaled_tasks/xxx/e1" -> "e1")
            parts = task.rstrip("/").split("/")
            level = parts[-1] if parts else ""
            
            if level in target_levels:
                filtered.append(task)
        
        return filtered


def get_static_skill_config(
    skills: Dict[str, Any],
    skills_summary: str
) -> Dict:
    """
    Generate configuration for static-skill mode.
    
    Args:
        skills: Dictionary of loaded skills
        skills_summary: Formatted skills summary for prompt injection
        
    Returns:
        Configuration dictionary for static-skill mode
    """
    return {
        "static_skill_mode": True,
        "enable_skill_cache": True,  # Need skill tools enabled
        "disable_save_skill": True,  # But disable saving new skills
        "cross_task_mode": False,  # Not cross-task mode
        "existing_skills": skills,
        "cross_task_skills_summary": skills_summary,  # Reuse the prompt injection mechanism
    }
