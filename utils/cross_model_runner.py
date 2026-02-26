"""
Cross-Model Skill Mode Runner

This module manages skill sharing across different models for the same task.
Model A creates skills while executing a task, then Model B uses those skills
to execute the same task.

Usage:
    python test_all_tasks.py --mode cross-model \
        --model-a gpt-5 --provider-a openrouter \
        --model-b claude-4 --provider-b openrouter \
        --scaled-tasks --scaled-base gitlab-deep-analysis
"""

import json
import os
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

# Import skill formatting function
from utils.aux_tools.skill_cache import get_skills_summary_for_prompt


class CrossModelRunner:
    """
    Manages cross-model skill sharing.
    
    Model A (Skill Creator) executes tasks and creates skills.
    Model B (Skill User) executes the same tasks using Model A's skills.
    
    Attributes:
        model_a: Name of the skill-creating model
        provider_a: Provider for Model A
        model_b: Name of the skill-using model
        provider_b: Provider for Model B
        run_dir: Root directory for this test run
        dump_dir: Directory for cross-model dumps
    """
    
    def __init__(self, 
                 model_a: str, provider_a: str,
                 model_b: str, provider_b: str,
                 run_dir: Path, 
                 dump_dir: Path = None):
        """
        Initialize CrossModelRunner.
        
        Args:
            model_a: Name of Model A (skill creator)
            provider_a: Provider for Model A
            model_b: Name of Model B (skill user)
            provider_b: Provider for Model B
            run_dir: Root directory for this test run
            dump_dir: Directory for cross-model dumps (default: run_dir / "dumps_cross_model")
        """
        self.model_a = model_a
        self.provider_a = provider_a
        self.model_b = model_b
        self.provider_b = provider_b
        self.run_dir = Path(run_dir)
        self.dump_dir = Path(dump_dir) if dump_dir else self.run_dir / "dumps_cross_model"
        
        # Create dump directories
        self.dump_dir.mkdir(parents=True, exist_ok=True)
        
        # Directory for Model A's results
        self.model_a_dump_dir = self.dump_dir / self._safe_model_name(model_a)
        self.model_a_dump_dir.mkdir(parents=True, exist_ok=True)
        
        # Directory for Model B's results (with reference to Model A)
        model_b_dir_name = f"{self._safe_model_name(model_b)}_from_{self._safe_model_name(model_a)}"
        self.model_b_dump_dir = self.dump_dir / model_b_dir_name
        self.model_b_dump_dir.mkdir(parents=True, exist_ok=True)
        
        # Execution log
        self.execution_log_file = self.dump_dir / "cross_model_execution_log.json"
        self.execution_log = self._load_execution_log()
        
    @staticmethod
    def _safe_model_name(model_name: str) -> str:
        """Convert model name to safe directory name."""
        return model_name.replace("/", "_").replace(":", "-")
    
    def _load_execution_log(self) -> Dict:
        """Load or initialize execution log."""
        if self.execution_log_file.exists():
            try:
                with open(self.execution_log_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        
        return {
            "model_a": self.model_a,
            "provider_a": self.provider_a,
            "model_b": self.model_b,
            "provider_b": self.provider_b,
            "created_at": datetime.now().isoformat(),
            "tasks_completed": [],
            "task_results": {},
            "summary": {}
        }
    
    def _save_execution_log(self):
        """Save execution log to file."""
        with open(self.execution_log_file, 'w', encoding='utf-8') as f:
            json.dump(self.execution_log, f, indent=2, ensure_ascii=False)
    
    def get_model_a_dump_path(self) -> str:
        """Get dump path for Model A."""
        return str(self.model_a_dump_dir) + "/"
    
    def get_model_b_dump_path(self) -> str:
        """Get dump path for Model B."""
        return str(self.model_b_dump_dir) + "/"
    
    def get_model_a_workspace(self, task_path: str) -> Optional[Path]:
        """
        Get Model A's workspace directory for a specific task.
        
        Args:
            task_path: Task path (e.g., "scaled_tasks/gitlab-deep-analysis/e1")
            
        Returns:
            Path to workspace directory, or None if not found
        """
        # Handle task path format: scaled_tasks/base/level or demo/task
        safe_task_name = task_path.replace("/", "_").replace("-", "_")
        
        # Try to find the workspace in Model A's dump directory
        # Structure: dump_dir/model_a/scaled_tasks/base/SingleUserTurn-level/workspace
        possible_paths = []
        
        if task_path.startswith("scaled_tasks/"):
            parts = task_path.split("/")
            if len(parts) >= 3:
                base_task = parts[1]
                level = parts[2]
                possible_paths.append(
                    self.model_a_dump_dir / "scaled_tasks" / base_task / f"SingleUserTurn-{level}" / "workspace"
                )
        
        # Generic path
        possible_paths.append(self.model_a_dump_dir / safe_task_name / "workspace")
        
        for path in possible_paths:
            if path.exists():
                return path
        
        return None
    
    def get_model_a_skills(self, task_path: str) -> Dict[str, Dict]:
        """
        Get skills created by Model A for a specific task.
        
        Args:
            task_path: Task path
            
        Returns:
            Dictionary of skill_name -> skill_data
        """
        workspace = self.get_model_a_workspace(task_path)
        if not workspace:
            return {}
        
        skill_cache_file = workspace / "skill_cache.json"
        if not skill_cache_file.exists():
            return {}
        
        try:
            with open(skill_cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get("skills", {})
        except (json.JSONDecodeError, IOError) as e:
            print(f"[WARNING] Could not load Model A's skill cache: {e}")
            return {}
    
    def get_skills_summary_for_model_b(self, task_path: str) -> str:
        """
        Generate skills summary for injection into Model B's system prompt.
        
        Similar to cross-task mode, this provides Model B with information
        about available skills from Model A.
        
        Args:
            task_path: Task path
            
        Returns:
            Formatted string describing available skills
        """
        skills = self.get_model_a_skills(task_path)
        if not skills:
            return ""
        
        # Use the detailed formatting function from skill_cache
        return get_skills_summary_for_prompt(skills)
    
    def sync_skills_to_model_b_workspace(self, task_path: str, model_b_workspace: Path):
        """
        Copy Model A's skill cache to Model B's workspace before execution.
        
        Args:
            task_path: Task path
            model_b_workspace: Model B's workspace directory
        """
        model_b_workspace = Path(model_b_workspace)
        model_b_workspace.mkdir(parents=True, exist_ok=True)
        
        model_a_workspace = self.get_model_a_workspace(task_path)
        if not model_a_workspace:
            print(f"[CROSS-MODEL] Model A's workspace not found for {task_path}")
            return
        
        skill_cache_file = model_a_workspace / "skill_cache.json"
        if skill_cache_file.exists():
            target_file = model_b_workspace / "skill_cache.json"
            shutil.copy(skill_cache_file, target_file)
            skills = self.get_model_a_skills(task_path)
            print(f"[CROSS-MODEL] Synced {len(skills)} skills from Model A to Model B's workspace")
        else:
            print(f"[CROSS-MODEL] No skills to sync (Model A did not create any)")
    
    def record_model_a_result(self, task_path: str, result: Dict):
        """
        Record Model A's execution result.
        
        Args:
            task_path: Task path
            result: Task result dictionary
        """
        if task_path not in self.execution_log["task_results"]:
            self.execution_log["task_results"][task_path] = {}
        
        skills = self.get_model_a_skills(task_path)
        
        self.execution_log["task_results"][task_path]["model_a"] = {
            "success": result.get("success", False),
            "eval_pass": result.get("eval_pass", False),
            "eval_score_percent": result.get("eval_score_percent", 0),
            "skills_created": len(skills),
            "skill_names": list(skills.keys()),
            "save_skill_calls": result.get("save_skill_calls", 0),
            "execute_skill_calls": result.get("execute_skill_calls", 0),
            "skill_execution_success_rate": result.get("skill_execution_success_rate", 0),
            "cost_usd": result.get("actual_cost_usd") or result.get("agent_cost", {}).get("total_cost", 0),
            "completed_at": datetime.now().isoformat()
        }
        self._save_execution_log()
    
    def record_model_b_result(self, task_path: str, result: Dict, inherited_skills: int):
        """
        Record Model B's execution result.
        
        Args:
            task_path: Task path
            result: Task result dictionary
            inherited_skills: Number of skills inherited from Model A
        """
        if task_path not in self.execution_log["task_results"]:
            self.execution_log["task_results"][task_path] = {}
        
        # Get skills Model B now has (inherited + newly created)
        model_b_skills = self._get_model_b_skills(task_path)
        new_skills_created = max(0, len(model_b_skills) - inherited_skills)
        
        self.execution_log["task_results"][task_path]["model_b"] = {
            "success": result.get("success", False),
            "eval_pass": result.get("eval_pass", False),
            "eval_score_percent": result.get("eval_score_percent", 0),
            "inherited_skills": inherited_skills,
            "skills_used": result.get("execute_skill_calls", 0),
            "new_skills_created": new_skills_created,
            "save_skill_calls": result.get("save_skill_calls", 0),
            "execute_skill_calls": result.get("execute_skill_calls", 0),
            "skill_execution_success_rate": result.get("skill_execution_success_rate", 0),
            "cost_usd": result.get("actual_cost_usd") or result.get("agent_cost", {}).get("total_cost", 0),
            "completed_at": datetime.now().isoformat()
        }
        
        # Mark task as completed
        if task_path not in self.execution_log["tasks_completed"]:
            self.execution_log["tasks_completed"].append(task_path)
        
        self._save_execution_log()
    
    def _get_model_b_skills(self, task_path: str) -> Dict[str, Dict]:
        """Get skills from Model B's workspace."""
        safe_task_name = task_path.replace("/", "_").replace("-", "_")
        
        possible_paths = []
        if task_path.startswith("scaled_tasks/"):
            parts = task_path.split("/")
            if len(parts) >= 3:
                base_task = parts[1]
                level = parts[2]
                possible_paths.append(
                    self.model_b_dump_dir / "scaled_tasks" / base_task / f"SingleUserTurn-{level}" / "workspace"
                )
        possible_paths.append(self.model_b_dump_dir / safe_task_name / "workspace")
        
        for path in possible_paths:
            skill_cache_file = path / "skill_cache.json"
            if skill_cache_file.exists():
                try:
                    with open(skill_cache_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        return data.get("skills", {})
                except (json.JSONDecodeError, IOError):
                    pass
        
        return {}
    
    def get_task_comparison(self, task_path: str) -> Dict:
        """
        Get comparison between Model A and Model B for a specific task.
        
        Args:
            task_path: Task path
            
        Returns:
            Comparison dictionary
        """
        task_results = self.execution_log["task_results"].get(task_path, {})
        model_a_result = task_results.get("model_a", {})
        model_b_result = task_results.get("model_b", {})
        
        if not model_a_result or not model_b_result:
            return {}
        
        # Calculate comparison metrics
        model_a_cost = model_a_result.get("cost_usd", 0) or 0
        model_b_cost = model_b_result.get("cost_usd", 0) or 0
        
        cost_reduction = 0
        if model_a_cost > 0:
            cost_reduction = ((model_a_cost - model_b_cost) / model_a_cost) * 100
        
        inherited = model_b_result.get("inherited_skills", 0)
        used = model_b_result.get("skills_used", 0)
        reuse_rate = (used / inherited * 100) if inherited > 0 else 0
        
        return {
            "model_a_passed": model_a_result.get("eval_pass", False),
            "model_b_passed": model_b_result.get("eval_pass", False),
            "both_passed": model_a_result.get("eval_pass", False) and model_b_result.get("eval_pass", False),
            "model_a_cost_usd": model_a_cost,
            "model_b_cost_usd": model_b_cost,
            "cost_reduction_percent": round(cost_reduction, 2),
            "skills_created_by_a": model_a_result.get("skills_created", 0),
            "skills_inherited_by_b": inherited,
            "skills_used_by_b": used,
            "skill_mode_rate": round(reuse_rate, 2),
            "new_skills_by_b": model_b_result.get("new_skills_created", 0),
            "model_a_score": model_a_result.get("eval_score_percent", 0),
            "model_b_score": model_b_result.get("eval_score_percent", 0)
        }
    
    def get_summary(self) -> Dict:
        """
        Get overall summary of cross-model execution.
        
        Returns:
            Summary dictionary with aggregated statistics
        """
        task_results = self.execution_log.get("task_results", {})
        
        total_tasks = len(task_results)
        model_a_passed = 0
        model_b_passed = 0
        both_passed = 0
        total_cost_a = 0
        total_cost_b = 0
        total_skills_created = 0
        total_skills_inherited = 0
        total_skills_used = 0
        
        comparisons = []
        
        for task_path, results in task_results.items():
            model_a = results.get("model_a", {})
            model_b = results.get("model_b", {})
            
            if model_a.get("eval_pass"):
                model_a_passed += 1
            if model_b.get("eval_pass"):
                model_b_passed += 1
            if model_a.get("eval_pass") and model_b.get("eval_pass"):
                both_passed += 1
            
            total_cost_a += model_a.get("cost_usd", 0) or 0
            total_cost_b += model_b.get("cost_usd", 0) or 0
            total_skills_created += model_a.get("skills_created", 0)
            total_skills_inherited += model_b.get("inherited_skills", 0)
            total_skills_used += model_b.get("skills_used", 0)
            
            comparison = self.get_task_comparison(task_path)
            if comparison:
                comparisons.append(comparison)
        
        # Calculate averages
        avg_cost_reduction = 0
        avg_reuse_rate = 0
        if comparisons:
            avg_cost_reduction = sum(c.get("cost_reduction_percent", 0) for c in comparisons) / len(comparisons)
            avg_reuse_rate = sum(c.get("skill_mode_rate", 0) for c in comparisons) / len(comparisons)
        
        summary = {
            "model_a": self.model_a,
            "model_b": self.model_b,
            "total_tasks": total_tasks,
            "model_a_passed": model_a_passed,
            "model_b_passed": model_b_passed,
            "both_passed": both_passed,
            "model_a_pass_rate": round(model_a_passed / total_tasks * 100, 2) if total_tasks > 0 else 0,
            "model_b_pass_rate": round(model_b_passed / total_tasks * 100, 2) if total_tasks > 0 else 0,
            "total_cost_model_a": round(total_cost_a, 4),
            "total_cost_model_b": round(total_cost_b, 4),
            "total_skills_created": total_skills_created,
            "total_skills_inherited": total_skills_inherited,
            "total_skills_used": total_skills_used,
            "avg_cost_reduction_percent": round(avg_cost_reduction, 2),
            "avg_skill_mode_rate": round(avg_reuse_rate, 2),
            "task_comparisons": {task: self.get_task_comparison(task) for task in task_results.keys()}
        }
        
        # Update log
        self.execution_log["summary"] = summary
        self._save_execution_log()
        
        return summary
    
    def save_summary_report(self):
        """Save a human-readable summary report."""
        summary = self.get_summary()
        
        report_file = self.dump_dir / "cross_model_summary.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        print(f"\n[CROSS-MODEL] Summary report saved to: {report_file}")
        return summary
