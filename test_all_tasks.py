#!/usr/bin/env python3
"""
SkillCraft scaled-task batch runner.

Main pipeline:
- task group: scaled_tasks
- modes: base / skill / direct-exec / cross-task / cross-model / static-reuse
"""

import argparse
import asyncio
import gc
import os
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

# API defaults
os.environ.setdefault(
    "TOOLATHLON_OPENAI_BASE_URL",
    os.environ.get("TOOLATHLON_OPENAI_BASE_URL", "https://openrouter.ai/api/v1"),
)

# Default model/provider
DEFAULT_MODEL = os.environ.get("TOOLATHLON_MODEL", "gemini-2.5-pro")
DEFAULT_PROVIDER = os.environ.get("TOOLATHLON_PROVIDER", "openrouter")

# Runtime directories
BASE_OUTPUT_DIR = Path(os.environ.get("TOOLATHLON_BASE_OUTPUT_DIR", "./test_runs"))
MCP_CONFIG_DIR = os.environ.get("TOOLATHLON_MCP_CONFIG_DIR", "configs/mcp_servers")

# Runtime limits
MAX_TURNS = int(os.environ.get("TOOLATHLON_MAX_TURNS", "150"))
MAX_STEPS = int(os.environ.get("TOOLATHLON_MAX_STEPS", "300"))
TASK_TIMEOUT_BASE = int(os.environ.get("TOOLATHLON_TASK_TIMEOUT", "3600"))
TASK_TIMEOUT_SKILL = int(os.environ.get("TOOLATHLON_TASK_TIMEOUT_SKILL", "3600"))
TASK_TIMEOUT_DIRECT_EXEC = int(os.environ.get("TOOLATHLON_TASK_TIMEOUT_DIRECT_EXEC", str(TASK_TIMEOUT_BASE)))
TASK_TIMEOUT_CROSS_MODEL = int(os.environ.get("TOOLATHLON_TASK_TIMEOUT_CROSS_MODEL", str(TASK_TIMEOUT_SKILL)))
TASK_TIMEOUT_STATIC_REUSE = int(os.environ.get("TOOLATHLON_TASK_TIMEOUT_STATIC_REUSE", str(TASK_TIMEOUT_SKILL)))
MAX_INPUT_TOKENS = int(os.environ.get("TOOLATHLON_MAX_INPUT_TOKENS", "1000000"))
MAX_OUTPUT_TOKENS = int(os.environ.get("TOOLATHLON_MAX_OUTPUT_TOKENS", "150000"))
MAX_SINGLE_REQUEST_INPUT_TOKENS = int(
    os.environ.get("TOOLATHLON_MAX_SINGLE_REQUEST_INPUT", "150000")
)
AGENT_MAX_TOKENS = int(os.environ.get("TOOLATHLON_AGENT_MAX_TOKENS", "8192"))
USER_MAX_TOKENS = int(os.environ.get("TOOLATHLON_USER_MAX_TOKENS", "1024"))

# Imports after sys.path injection
from utils.cross_model_runner import CrossModelRunner
from utils.cross_task_runner import CrossTaskRunner
from utils.data_structures.task_config import TaskConfig
from utils.evaluation.evaluator import TaskEvaluator
from utils.general.helper import print_color, read_json, write_json
from utils.openai_agents_monkey_patch.custom_mcp_util import *
from utils.openai_agents_monkey_patch.custom_run_impl import *
from utils.static_skill_runner import StaticReuseRunner
from utils.task_runner.runner import TaskRunner


SCALED_TASK_BASES = [
    "gitlab-deep-analysis",
    "countries-encyclopedia",
    "tvmaze-series-analyzer",
    "jikan-anime-analysis",
    "rickmorty-multiverse-explorer",
    "jsonplaceholder-blog-analyzer",
    "random-user-database",
    "openmeteo-weather",
    "usgs-earthquake-monitor",
    "world-bank-economic-snapshot",
    "university-directory-builder",
    "name-demographics-analyzer",
    "pokeapi-pokedex",
    "dnd-campaign-builder",
    "dnd-monster-compendium",
    "cocktail-menu-generator",
    "recipe-cookbook-builder",
    "dog-breeds-encyclopedia",
    "cat-facts-collector",
    "vocabulary-builder",
    "local-dna-analysis",
]

SCALED_TASKS_SUBSET_BASES = [
    "countries-encyclopedia",
    "gitlab-deep-analysis",
    "dog-breeds-encyclopedia",
    "cocktail-menu-generator",
    "random-user-database",
    "university-directory-builder",
    "tvmaze-series-analyzer",
    "usgs-earthquake-monitor",
]

DEFAULT_LEVELS = ["e1", "m1", "h1"]


def level_sort_key(level_name: str):
    prefix = level_name[0] if level_name else "z"
    suffix = level_name[1:]
    num = int(suffix) if suffix.isdigit() else 999
    prefix_order = {"e": 0, "m": 1, "h": 2}.get(prefix, 3)
    return (prefix_order, num)


def split_scaled_task(task_path: str) -> tuple[str, str]:
    parts = task_path.split("/")
    if len(parts) < 3 or parts[0] != "scaled_tasks":
        raise ValueError(f"Expected scaled task path, got: {task_path}")
    return parts[1], parts[2]


def parse_modes(mode_text: str) -> List[str]:
    raw = [m.strip() for m in mode_text.split(",") if m.strip()]
    supported = {
        "base",
        "skill",
        "direct-exec",
        "cross-task",
        "cross-model",
        "static-reuse",
    }
    if not raw:
        raise ValueError("At least one mode is required")

    deduped: List[str] = []
    for mode in raw:
        if mode == "all":
            for all_mode in [
                "base",
                "skill",
                "direct-exec",
                "cross-task",
                "cross-model",
                "static-reuse",
            ]:
                if all_mode not in deduped:
                    deduped.append(all_mode)
            continue

        if mode not in deduped:
            deduped.append(mode)

    invalid = [m for m in deduped if m not in supported]
    if invalid:
        raise ValueError(
            "Unsupported mode(s): "
            f"{', '.join(invalid)}. "
            "Supported: base, skill, direct-exec, cross-task, cross-model, static-reuse"
        )
    return deduped


def discover_scaled_task_levels(base_tasks: Optional[List[str]] = None) -> List[str]:
    levels = set()
    scaled_root = PROJECT_ROOT / "tasks" / "scaled_tasks"
    if not scaled_root.exists():
        return DEFAULT_LEVELS

    bases = base_tasks if base_tasks else SCALED_TASK_BASES
    for base_task in bases:
        base_dir = scaled_root / base_task
        if not base_dir.exists() or not base_dir.is_dir():
            continue
        for child in base_dir.iterdir():
            if child.is_dir() and (child / "task_config.json").exists():
                levels.add(child.name)

    if not levels:
        return DEFAULT_LEVELS
    return sorted(levels, key=level_sort_key)


def parse_levels(level_text: Optional[str], base_tasks: List[str]) -> List[str]:
    available = discover_scaled_task_levels(base_tasks)
    if not level_text:
        return available

    requested = [x.strip() for x in level_text.split(",") if x.strip()]
    expanded: List[str] = []

    for item in requested:
        if item in {"e", "m", "h"}:
            matched = [lvl for lvl in available if lvl.startswith(item)]
            if not matched:
                print_color(f"[WARN] No levels found for difficulty prefix: {item}", "yellow")
            expanded.extend(matched)
        else:
            expanded.append(item)

    deduped = []
    for lvl in expanded:
        if lvl not in deduped:
            deduped.append(lvl)
    return deduped


def parse_base_tasks(base_text: Optional[str], use_subset: bool) -> List[str]:
    if use_subset:
        return SCALED_TASKS_SUBSET_BASES
    if not base_text:
        return SCALED_TASK_BASES

    base_tasks = [x.strip() for x in base_text.split(",") if x.strip()]
    unknown = [b for b in base_tasks if not (PROJECT_ROOT / "tasks" / "scaled_tasks" / b).exists()]
    if unknown:
        raise ValueError(f"Unknown scaled base task(s): {', '.join(unknown)}")
    return base_tasks


def get_scaled_tasks(base_tasks: List[str], levels: List[str]) -> List[str]:
    tasks: List[str] = []
    for base_task in base_tasks:
        for level in levels:
            rel_path = f"scaled_tasks/{base_task}/{level}"
            config_path = PROJECT_ROOT / "tasks" / rel_path / "task_config.json"
            if config_path.exists():
                tasks.append(rel_path)
    return tasks


def validate_single_task(task_path: str) -> str:
    task_path = task_path.strip().lstrip("/")
    if task_path.startswith("tasks/"):
        task_path = task_path[len("tasks/") :]

    if not task_path.startswith("scaled_tasks/"):
        raise ValueError("--task must point to scaled_tasks/... (only scaled_tasks are supported)")

    config_path = PROJECT_ROOT / "tasks" / task_path / "task_config.json"
    if not config_path.exists():
        raise ValueError(f"Task not found: {task_path}")
    return task_path


def create_or_load_run_directory(continue_run: Optional[str]) -> Dict[str, str]:
    if continue_run:
        run_dir = Path(continue_run).resolve()
        if not run_dir.exists() or not run_dir.is_dir():
            raise ValueError(f"Run directory does not exist: {continue_run}")

        timestamp = run_dir.name.replace("run_", "")
        paths = {
            "run_timestamp": timestamp,
            "run_dir": str(run_dir),
            "dump_base": str(run_dir / "dumps_base_test"),
            "dump_skill": str(run_dir / "dumps_skill_test"),
            "dump_direct_exec": str(run_dir / "dumps_direct_exec"),
            "dump_cross_task": str(run_dir / "dumps_cross_task"),
            "dump_cross_model": str(run_dir / "dumps_cross_model"),
            "dump_static_reuse": str(run_dir / "dumps_static_reuse"),
            "skill_test_dir": str(run_dir / "skill_test"),
        }
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_dir = (BASE_OUTPUT_DIR / f"run_{timestamp}").resolve()
        paths = {
            "run_timestamp": timestamp,
            "run_dir": str(run_dir),
            "dump_base": str(run_dir / "dumps_base_test"),
            "dump_skill": str(run_dir / "dumps_skill_test"),
            "dump_direct_exec": str(run_dir / "dumps_direct_exec"),
            "dump_cross_task": str(run_dir / "dumps_cross_task"),
            "dump_cross_model": str(run_dir / "dumps_cross_model"),
            "dump_static_reuse": str(run_dir / "dumps_static_reuse"),
            "skill_test_dir": str(run_dir / "skill_test"),
        }

    Path(paths["run_dir"]).mkdir(parents=True, exist_ok=True)
    Path(paths["dump_base"]).mkdir(parents=True, exist_ok=True)
    Path(paths["dump_skill"]).mkdir(parents=True, exist_ok=True)
    Path(paths["dump_direct_exec"]).mkdir(parents=True, exist_ok=True)
    Path(paths["dump_cross_task"]).mkdir(parents=True, exist_ok=True)
    Path(paths["dump_cross_model"]).mkdir(parents=True, exist_ok=True)
    Path(paths["dump_static_reuse"]).mkdir(parents=True, exist_ok=True)
    Path(paths["skill_test_dir"]).mkdir(parents=True, exist_ok=True)

    run_info = {
        "timestamp": paths["run_timestamp"],
        "start_time": datetime.now().isoformat(),
        "dump_base": paths["dump_base"],
        "dump_skill": paths["dump_skill"],
        "dump_direct_exec": paths["dump_direct_exec"],
        "dump_cross_task": paths["dump_cross_task"],
        "dump_cross_model": paths["dump_cross_model"],
        "dump_static_reuse": paths["dump_static_reuse"],
        "skill_test": paths["skill_test_dir"],
    }
    write_json(run_info, Path(paths["run_dir"]) / "run_info.json")

    print_color("\n" + "=" * 70, "cyan")
    print_color(f"Run directory: {paths['run_dir']}", "cyan")
    print_color(f"  - Base dumps:        {paths['dump_base']}", "white")
    print_color(f"  - Skill dumps:       {paths['dump_skill']}", "white")
    print_color(f"  - Direct-exec dumps: {paths['dump_direct_exec']}", "white")
    print_color(f"  - Cross-task dumps:  {paths['dump_cross_task']}", "white")
    print_color(f"  - Cross-model dumps: {paths['dump_cross_model']}", "white")
    print_color(f"  - Static-reuse dumps:{paths['dump_static_reuse']}", "white")
    print_color("=" * 70 + "\n", "cyan")

    return paths


def load_existing_results(run_dir: Path, provider: str, model_name: str) -> List[dict]:
    filename = f"test_results_{provider}_{model_name.replace('/', '_')}.json"
    result_file = run_dir / filename
    if not result_file.exists():
        return []

    try:
        data = read_json(result_file)
        if isinstance(data, dict) and isinstance(data.get("results"), list):
            return data["results"]
    except Exception as exc:
        print_color(f"[WARN] Could not load existing results: {exc}", "yellow")
    return []


def count_skill_tool_calls(conversation_history: list) -> Dict[str, int]:
    counters = {
        "save_skill_calls": 0,
        "execute_skill_calls": 0,
        "get_skill_calls": 0,
        "list_skills_calls": 0,
    }

    mapping = {
        "local-save_skill": "save_skill_calls",
        "local-execute_skill": "execute_skill_calls",
        "local-get_skill": "get_skill_calls",
        "local-list_skills": "list_skills_calls",
    }

    for message in conversation_history or []:
        for tool_call in message.get("tool_calls", []):
            if not isinstance(tool_call, dict):
                continue
            tool_name = tool_call.get("name")
            if not tool_name:
                tool_name = tool_call.get("function", {}).get("name")
            if tool_name in mapping:
                counters[mapping[tool_name]] += 1

    return counters


def add_task_metrics_to_eval_res(eval_res_path: Path, key_stats: dict, agent_cost: dict) -> None:
    if not eval_res_path.exists():
        return

    try:
        eval_res = read_json(eval_res_path)
        eval_res["task_metrics"] = {
            "input_tokens": key_stats.get("input_tokens", 0),
            "output_tokens": key_stats.get("output_tokens", 0),
            "total_tokens": key_stats.get("total_tokens", 0),
            "last_input_tokens": key_stats.get("last_input_tokens", 0),
            "total_turns": key_stats.get("total_turns", 0),
            "total_steps": key_stats.get("total_in_turn_steps", 0),
            "llm_requests": key_stats.get("agent_llm_requests", 0),
            "tool_calls": key_stats.get("tool_calls", 0),
            "output_tokens_without_skill_creation_cost": key_stats.get(
                "output_tokens_without_skill_creation_cost",
                key_stats.get("output_without_skill_cost", key_stats.get("output_tokens", 0)),
            ),
            "skill_creation_output_tokens": key_stats.get("skill_creation_output_tokens", 0),
            "save_skill_call_count": key_stats.get("save_skill_call_count", 0),
            "cost_usd": round(agent_cost.get("total_cost", 0), 6),
            "cost_source": agent_cost.get("cost_source", "estimated"),
        }
        write_json(eval_res, eval_res_path)
    except Exception as exc:
        print_color(f"[WARN] Failed to add task metrics to eval_res: {exc}", "yellow")


def calc_pct(new_value: float, base_value: float) -> float:
    if base_value <= 0:
        return 0.0
    return round(((new_value / base_value) - 1.0) * 100.0, 2)


def build_efficiency_comparison(base_mode: dict, skill_mode: dict) -> dict:
    base_stats = base_mode.get("key_stats", {})
    skill_stats = skill_mode.get("key_stats", {})
    base_cost = base_mode.get("agent_cost", {}).get("total_cost", 0)
    skill_cost = skill_mode.get("agent_cost", {}).get("total_cost", 0)

    base_data = {
        "llm_requests": base_stats.get("agent_llm_requests", 0),
        "tool_calls": base_stats.get("tool_calls", 0),
        "total_turns": base_stats.get("total_turns", 0),
        "total_steps": base_stats.get("total_in_turn_steps", 0),
        "input_tokens": base_stats.get("input_tokens", 0),
        "output_tokens": base_stats.get("output_tokens", 0),
        "total_tokens": base_stats.get("total_tokens", 0),
        "last_input_tokens": base_stats.get("last_input_tokens", 0),
        "cost_usd": round(base_cost, 6),
    }
    skill_data = {
        "llm_requests": skill_stats.get("agent_llm_requests", 0),
        "tool_calls": skill_stats.get("tool_calls", 0),
        "total_turns": skill_stats.get("total_turns", 0),
        "total_steps": skill_stats.get("total_in_turn_steps", 0),
        "input_tokens": skill_stats.get("input_tokens", 0),
        "output_tokens": skill_stats.get("output_tokens", 0),
        "total_tokens": skill_stats.get("total_tokens", 0),
        "last_input_tokens": skill_stats.get("last_input_tokens", 0),
        "cost_usd": round(skill_cost, 6),
    }

    difference = {}
    for metric in base_data.keys():
        base_val = base_data[metric]
        skill_val = skill_data[metric]
        difference[metric] = skill_val - base_val
        difference[f"{metric}_diff_pct"] = calc_pct(skill_val, base_val)

    both_success = bool(base_mode.get("success") and skill_mode.get("success"))
    efficiency_improved = both_success and difference.get("output_tokens", 0) < 0

    return {
        "base_mode": base_data,
        "skill_mode": skill_data,
        "difference": difference,
        "efficiency_improved": efficiency_improved,
        "summary": (
            f"Output tokens: {base_data['output_tokens']}->{skill_data['output_tokens']} "
            f"({difference['output_tokens_diff_pct']:+.1f}%), "
            f"Cost: ${base_data['cost_usd']:.4f}->${skill_data['cost_usd']:.4f} "
            f"({difference['cost_usd_diff_pct']:+.1f}%)"
        ),
    }


class TaskTester:
    def __init__(
        self,
        model_name: str,
        provider: str,
        run_paths: Dict[str, str],
        enable_parallel_tools: bool,
        allow_skill_nesting: bool,
        max_skill_nesting_depth: int,
    ):
        self.model_name = model_name
        self.provider = provider
        self.run_paths = run_paths
        self.enable_parallel_tools = enable_parallel_tools
        self.allow_skill_nesting = allow_skill_nesting
        self.max_skill_nesting_depth = max_skill_nesting_depth

        self.output_dir = Path(run_paths["skill_test_dir"]) / f"{provider}_{model_name.replace('/', '_')}"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        os.chdir(PROJECT_ROOT)

    def _build_eval_config(
        self,
        *,
        dump_path: str,
        model_name: Optional[str] = None,
        provider: Optional[str] = None,
        enable_skill_cache: bool = False,
        enable_direct_exec: bool = False,
        allow_skill_nesting: bool = False,
        cross_task_mode: bool = False,
        cross_task_skills_summary: str = "",
        shared_skill_cache_path: Optional[str] = None,
        static_skill_mode: bool = False,
        static_skill_skills: Optional[Dict[str, Any]] = None,
        disable_save_skill: bool = False,
    ) -> dict:
        model = model_name or self.model_name
        model_provider = provider or self.provider

        global_task_config: Dict[str, Any] = {
            "max_turns": MAX_TURNS,
            "max_steps_under_single_turn_mode": MAX_STEPS,
            "dump_path": dump_path,
            "enable_skill_cache": enable_skill_cache,
            "enable_direct_exec": enable_direct_exec,
            "max_input_tokens": MAX_INPUT_TOKENS,
            "max_output_tokens": MAX_OUTPUT_TOKENS,
            "max_single_request_input_tokens": MAX_SINGLE_REQUEST_INPUT_TOKENS,
            "allow_skill_nesting": allow_skill_nesting,
            "max_skill_nesting_depth": self.max_skill_nesting_depth,
        }

        if cross_task_mode:
            global_task_config["cross_task_mode"] = True
        if cross_task_skills_summary:
            global_task_config["cross_task_skills_summary"] = cross_task_skills_summary
        if shared_skill_cache_path:
            global_task_config["shared_skill_cache_path"] = shared_skill_cache_path
        if static_skill_mode:
            global_task_config["static_skill_mode"] = True
        if static_skill_skills is not None:
            # used by TaskAgent._sync_static_skill_skills
            global_task_config["static_skill_skills"] = static_skill_skills
            # keep compatibility with existing helpers
            global_task_config["existing_skills"] = static_skill_skills
        if disable_save_skill:
            global_task_config["disable_save_skill"] = True

        config: Dict[str, Any] = {
            "global_task_config": global_task_config,
            "mcp": {
                "server_config_path": MCP_CONFIG_DIR,
            },
            "agent": {
                "model": {
                    "short_name": model,
                    "provider": model_provider,
                },
                "generation": {
                    "top_p": 1.0,
                    "max_tokens": AGENT_MAX_TOKENS,
                },
                "tool": {
                    "tool_choice": "auto",
                    "parallel_tool_calls": self.enable_parallel_tools,
                    "max_inner_turns": 2000,
                },
            },
            "user": {
                "model": {
                    "short_name": "gpt-5",
                    "provider": "openrouter",
                },
                "generation": {
                    "top_p": 1.0,
                    "max_tokens": USER_MAX_TOKENS,
                },
            },
        }

        if not self.enable_parallel_tools:
            config["global_task_config"]["tool_filter_config"] = {
                "filesystem": [
                    "read_file",
                    "write_file",
                    "edit_file",
                    "create_directory",
                    "list_directory",
                    "directory_tree",
                    "move_file",
                    "search_files",
                    "get_file_info",
                    "list_allowed_directories",
                ]
            }

        return config

    def _build_eval_config_for_mode(self, mode: str) -> dict:
        if mode == "base":
            return self._build_eval_config(
                dump_path=f"{self.run_paths['dump_base']}/",
                enable_skill_cache=False,
                enable_direct_exec=False,
                allow_skill_nesting=False,
            )
        if mode == "skill":
            return self._build_eval_config(
                dump_path=f"{self.run_paths['dump_skill']}/",
                enable_skill_cache=True,
                enable_direct_exec=False,
                allow_skill_nesting=self.allow_skill_nesting,
            )
        if mode == "direct-exec":
            return self._build_eval_config(
                dump_path=f"{self.run_paths['dump_direct_exec']}/",
                enable_skill_cache=False,
                enable_direct_exec=True,
                allow_skill_nesting=False,
            )
        raise ValueError(f"Unknown mode: {mode}")

    def _empty_result(self) -> Dict[str, Any]:
        return {
            "success": False,
            "completed": False,
            "partial_success": False,
            "failure_reason": None,
            "timeout": False,
            "mcp_failure": False,
            "agent_no_response": False,
            "api_rate_limit": False,
            "error_messages": [],
            "return_code": 1,
            "task_status": None,
            "eval_pass": False,
            "eval_status": "unknown",
            "eval_score": {},
            "eval_score_percent": 0,
            "eval_details": None,
            "log_file": None,
            "agent_workspace": None,
            "key_stats": {},
            "agent_cost": {},
            "user_cost": {},
            "skill_created": False,
            "skill_saved": False,
            "skill_used": False,
            "save_skill_calls": 0,
            "execute_skill_calls": 0,
            "get_skill_calls": 0,
            "list_skills_calls": 0,
            "skill_file_exists": False,
            "direct_exec_total": 0,
            "direct_exec_success": 0,
            "direct_exec_failed": 0,
            "direct_exec_success_rate": 0,
        }

    async def _run_task_with_eval_config(
        self,
        task_path: str,
        mode_label: str,
        eval_config: dict,
        *,
        task_timeout_default: int,
        add_skill_analysis: bool,
        add_direct_exec_analysis: bool,
        pre_run_hook: Optional[Callable[[TaskConfig, Dict[str, Any]], None]] = None,
        post_run_hook: Optional[Callable[[TaskConfig, Dict[str, Any]], None]] = None,
    ) -> Dict[str, Any]:
        print_color("\n" + "=" * 70, "cyan")
        print_color(f"Running task: {task_path}", "cyan")
        print_color(f"Mode: {mode_label}", "cyan")
        print_color("=" * 70, "cyan")

        result = self._empty_result()
        result["mode"] = mode_label

        task_config = None

        try:
            mcp_config, agent_config, user_config = TaskRunner.load_configs(eval_config)

            task_config = TaskConfig.build(
                task_path,
                agent_config.model.short_name,
                eval_config["global_task_config"],
                single_turn_mode=True,
                cn_mode=False,
            )
            result["log_file"] = task_config.log_file
            result["agent_workspace"] = task_config.agent_workspace

            if pre_run_hook:
                pre_run_hook(task_config, result)

            task_specific_timeout = task_config.raw_config.get("timeout", task_timeout_default)
            tool_filter_config = eval_config.get("global_task_config", {}).get("tool_filter_config")

            try:
                task_status = await asyncio.wait_for(
                    TaskRunner.run_single_task(
                        task_config=task_config,
                        agent_config=agent_config,
                        user_config=user_config,
                        mcp_config=mcp_config,
                        debug=False,
                        allow_resume=False,
                        manual=False,
                        single_turn_mode=True,
                        tool_filter_config=tool_filter_config,
                    ),
                    timeout=task_specific_timeout,
                )
                result["task_status"] = task_status.value
                result["completed"] = True
            except asyncio.TimeoutError:
                result["timeout"] = True
                result["task_status"] = "timeout"
                result["failure_reason"] = f"Task timeout (>{task_specific_timeout}s)"

            if task_config.log_file and os.path.exists(task_config.log_file):
                eval_res = await TaskEvaluator.evaluate_from_log_file(
                    task_config.log_file,
                    allow_resume=False,
                    add_skill_analysis=add_skill_analysis,
                    add_direct_exec_analysis=add_direct_exec_analysis,
                )
                result["eval_pass"] = bool(eval_res.get("pass", False))
                result["eval_status"] = eval_res.get("status", "unknown")
                result["eval_score"] = eval_res.get("score", {})
                result["eval_score_percent"] = eval_res.get("score", {}).get("percent", 0)
                result["eval_details"] = eval_res.get("details")

                direct_exec_analysis = eval_res.get("direct_exec_analysis", {})
                if direct_exec_analysis and direct_exec_analysis.get("enabled"):
                    result["direct_exec_total"] = direct_exec_analysis.get("total_executions", 0)
                    result["direct_exec_success"] = direct_exec_analysis.get("successful", 0)
                    result["direct_exec_failed"] = direct_exec_analysis.get("failed", 0)
                    result["direct_exec_success_rate"] = direct_exec_analysis.get("success_rate", 0)

                if result["eval_pass"]:
                    result["success"] = True
                    result["return_code"] = 0
                elif result["eval_status"] == "partial":
                    result["partial_success"] = True
                    result["return_code"] = 2
                    if not result["failure_reason"]:
                        result["failure_reason"] = (
                            f"Partial completion ({result['eval_score_percent']:.1f}%)"
                        )
                else:
                    if not result["failure_reason"]:
                        result["failure_reason"] = eval_res.get("failure", "Evaluation failed")

                dump_line = read_json(task_config.log_file)
                result["key_stats"] = dump_line.get("key_stats", {})
                result["agent_cost"] = dump_line.get("agent_cost", {})
                result["user_cost"] = dump_line.get("user_cost", {})

                tool_counts = count_skill_tool_calls(dump_line.get("conversation_history", []))
                result.update(tool_counts)
                result["skill_saved"] = result["save_skill_calls"] > 0
                result["skill_created"] = result["save_skill_calls"] > 0
                result["skill_used"] = result["execute_skill_calls"] > 0

                eval_res_path = Path(task_config.log_file).parent / "eval_res.json"
                add_task_metrics_to_eval_res(eval_res_path, result["key_stats"], result["agent_cost"])

                workspace_skill_file = Path(task_config.agent_workspace) / "skill_cache.json"
                result["skill_file_exists"] = workspace_skill_file.exists()
            else:
                if not result["failure_reason"]:
                    result["failure_reason"] = "No traj_log.json generated"

            if post_run_hook:
                post_run_hook(task_config, result)

        except Exception as exc:
            error_text = str(exc)
            result["failure_reason"] = f"Exception: {error_text}"
            result["error_messages"].append(error_text)
            if "mcp" in error_text.lower():
                result["mcp_failure"] = True
            if "rate" in error_text.lower() and "limit" in error_text.lower():
                result["api_rate_limit"] = True
            if "no response" in error_text.lower():
                result["agent_no_response"] = True
            traceback.print_exc()

        total_cost = result.get("agent_cost", {}).get("total_cost", 0)
        if total_cost:
            print_color(f"[COST] {task_path} ({mode_label}): ${total_cost:.6f}", "cyan")

        return result

    async def run_task_async(self, task_path: str, mode: str) -> Dict[str, Any]:
        eval_config = self._build_eval_config_for_mode(mode)
        if mode == "base":
            timeout = TASK_TIMEOUT_BASE
        elif mode == "skill":
            timeout = TASK_TIMEOUT_SKILL
        elif mode == "direct-exec":
            timeout = TASK_TIMEOUT_DIRECT_EXEC
        else:
            raise ValueError(f"Unsupported mode for run_task_async: {mode}")

        return await self._run_task_with_eval_config(
            task_path,
            mode,
            eval_config,
            task_timeout_default=timeout,
            add_skill_analysis=(mode == "skill"),
            add_direct_exec_analysis=(mode == "direct-exec"),
        )

    def run_task(self, task_path: str, mode: str) -> Dict[str, Any]:
        result = asyncio.run(self.run_task_async(task_path, mode))
        gc.collect()
        time.sleep(0.2)
        return result

    async def run_cross_task_async(
        self,
        task_path: str,
        cross_task_runner: CrossTaskRunner,
        level: str,
    ) -> Dict[str, Any]:
        skills_summary = cross_task_runner.get_skills_summary()

        # Ensure shared cache file exists so execute/list/get can read it from first level.
        if not cross_task_runner.shared_cache_file.exists():
            write_json(
                {"skills": {}, "metadata": {"base_task": cross_task_runner.base_task}},
                cross_task_runner.shared_cache_file,
            )

        eval_config = self._build_eval_config(
            dump_path=f"{self.run_paths['dump_cross_task']}/",
            enable_skill_cache=True,
            allow_skill_nesting=True,
            cross_task_mode=True,
            cross_task_skills_summary=skills_summary,
            shared_skill_cache_path=str(cross_task_runner.shared_cache_file.resolve()),
        )

        result = await self._run_task_with_eval_config(
            task_path,
            f"cross-task:{level}",
            eval_config,
            task_timeout_default=TASK_TIMEOUT_SKILL,
            add_skill_analysis=True,
            add_direct_exec_analysis=False,
        )
        result["cross_task_mode"] = True
        result["level"] = level
        result["inherited_skills"] = len(cross_task_runner.get_existing_skills())

        cross_task_runner.record_level_result(level, result)
        return result

    def run_cross_task_group(self, base_task: str, levels: Optional[List[str]] = None) -> Dict[str, Any]:
        print_color("\n" + "=" * 70, "cyan")
        print_color(f"[CROSS-TASK] Starting base task: {base_task}", "cyan")
        print_color("=" * 70, "cyan")

        cross_runner = CrossTaskRunner(
            base_task=base_task,
            run_dir=Path(self.run_paths["run_dir"]),
            dump_dir=Path(self.run_paths["dump_cross_task"]),
        )

        if levels is None:
            levels = discover_scaled_task_levels([base_task])
        levels = CrossTaskRunner.sort_levels(levels)

        detailed: Dict[str, Any] = {}
        for idx, level in enumerate(levels, start=1):
            task_path = f"scaled_tasks/{base_task}/{level}"
            config_exists = (PROJECT_ROOT / "tasks" / task_path / "task_config.json").exists()
            if not config_exists:
                print_color(f"[SKIP] Missing task config: {task_path}", "yellow")
                continue

            print_color(f"[CROSS-TASK] [{idx}/{len(levels)}] {task_path}", "magenta")
            result = asyncio.run(self.run_cross_task_async(task_path, cross_runner, level))
            detailed[level] = result
            gc.collect()
            time.sleep(0.2)

        summary = cross_runner.get_summary()
        summary["level_results_detailed"] = detailed

        summary_file = cross_runner.shared_cache_dir / "cross_task_summary.json"
        write_json(summary, summary_file)
        print_color(f"[CROSS-TASK] Summary saved: {summary_file}", "green")
        return summary

    async def run_static_reuse_task_async(
        self,
        task_path: str,
        static_runner: StaticReuseRunner,
        task_group: str,
    ) -> Dict[str, Any]:
        loaded_skills = static_runner.load_skills_for_task_group(task_group)
        skills_summary = static_runner.get_skills_summary(task_group)

        eval_config = self._build_eval_config(
            dump_path=f"{self.run_paths['dump_static_reuse']}/",
            enable_skill_cache=True,
            allow_skill_nesting=True,
            static_skill_mode=True,
            static_skill_skills=loaded_skills,
            cross_task_skills_summary=skills_summary,
            disable_save_skill=True,
        )

        result = await self._run_task_with_eval_config(
            task_path,
            "static-reuse",
            eval_config,
            task_timeout_default=TASK_TIMEOUT_STATIC_REUSE,
            add_skill_analysis=True,
            add_direct_exec_analysis=False,
        )
        result["static_reuse_mode"] = True
        result["loaded_skills"] = len(loaded_skills)

        static_runner.record_task_result(task_path, result)
        return result

    def run_static_reuse_task(
        self,
        task_path: str,
        static_runner: StaticReuseRunner,
        task_group: str,
    ) -> Dict[str, Any]:
        result = asyncio.run(self.run_static_reuse_task_async(task_path, static_runner, task_group))
        gc.collect()
        time.sleep(0.2)
        return result

    async def run_cross_model_task_async(
        self,
        task_path: str,
        cross_model_runner: CrossModelRunner,
    ) -> Dict[str, Any]:
        print_color("\n" + "=" * 70, "cyan")
        print_color(f"[CROSS-MODEL] Task: {task_path}", "cyan")
        print_color(
            f"Model A (creator): {cross_model_runner.model_a} ({cross_model_runner.provider_a})",
            "white",
        )
        print_color(
            f"Model B (user):    {cross_model_runner.model_b} ({cross_model_runner.provider_b})",
            "white",
        )
        print_color("=" * 70, "cyan")

        # Phase A: create skills
        model_a_config = self._build_eval_config(
            dump_path=cross_model_runner.get_model_a_dump_path(),
            model_name=cross_model_runner.model_a,
            provider=cross_model_runner.provider_a,
            enable_skill_cache=True,
            allow_skill_nesting=True,
        )
        model_a_result = await self._run_task_with_eval_config(
            task_path,
            "cross-model:model-a",
            model_a_config,
            task_timeout_default=TASK_TIMEOUT_CROSS_MODEL,
            add_skill_analysis=True,
            add_direct_exec_analysis=False,
        )
        cross_model_runner.record_model_a_result(task_path, model_a_result)

        inherited_skills = cross_model_runner.get_model_a_skills(task_path)
        skills_summary = cross_model_runner.get_skills_summary_for_model_b(task_path)

        # Phase B: use inherited skills
        model_b_config = self._build_eval_config(
            dump_path=cross_model_runner.get_model_b_dump_path(),
            model_name=cross_model_runner.model_b,
            provider=cross_model_runner.provider_b,
            enable_skill_cache=True,
            allow_skill_nesting=True,
            cross_task_mode=True,
            cross_task_skills_summary=skills_summary,
            static_skill_skills=inherited_skills,
        )
        model_b_result = await self._run_task_with_eval_config(
            task_path,
            "cross-model:model-b",
            model_b_config,
            task_timeout_default=TASK_TIMEOUT_CROSS_MODEL,
            add_skill_analysis=True,
            add_direct_exec_analysis=False,
        )
        cross_model_runner.record_model_b_result(task_path, model_b_result, len(inherited_skills))

        comparison = cross_model_runner.get_task_comparison(task_path)
        return {
            "task_path": task_path,
            "model_a": cross_model_runner.model_a,
            "model_b": cross_model_runner.model_b,
            "inherited_skills": len(inherited_skills),
            "model_a_result": model_a_result,
            "model_b_result": model_b_result,
            "comparison": comparison,
            "success": bool(model_a_result.get("eval_pass") and model_b_result.get("eval_pass")),
        }

    def run_cross_model_task(self, task_path: str, cross_model_runner: CrossModelRunner) -> Dict[str, Any]:
        result = asyncio.run(self.run_cross_model_task_async(task_path, cross_model_runner))
        gc.collect()
        time.sleep(0.2)
        return result


def save_results(
    run_dir: Path,
    model_name: str,
    provider: str,
    run_timestamp: str,
    modes: List[str],
    results: List[dict],
) -> None:
    payload = {
        "model": model_name,
        "provider": provider,
        "test_date": datetime.now().isoformat(),
        "run_timestamp": run_timestamp,
        "run_dir": str(run_dir),
        "modes": modes,
        "total_tasks": len(results),
        "results": results,
    }

    output_file = run_dir / f"test_results_{provider}_{model_name.replace('/', '_')}.json"
    write_json(payload, output_file)


def generate_summary(results: List[dict], modes: List[str], model_name: str, provider: str) -> dict:
    summary = {
        "model": model_name,
        "provider": provider,
        "total_tasks": len(results),
        "modes": modes,
        "base_mode_success": 0,
        "base_mode_completed": 0,
        "skill_mode_success": 0,
        "skill_mode_completed": 0,
        "direct_exec_mode_success": 0,
        "direct_exec_mode_completed": 0,
        "both_success": 0,
        "partial_tasks": 0,
        "timeouts": 0,
        "mcp_failures": 0,
        "api_rate_limits": 0,
        "skill_saved_tasks": 0,
        "skill_used_tasks": 0,
        "save_skill_calls_total": 0,
        "execute_skill_calls_total": 0,
        "get_skill_calls_total": 0,
        "list_skills_calls_total": 0,
        "aggregate_efficiency": {},
    }

    agg_base = {
        "llm_requests": 0,
        "tool_calls": 0,
        "total_turns": 0,
        "total_steps": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
        "last_input_tokens": 0,
        "cost_usd": 0.0,
    }
    agg_skill = {
        "llm_requests": 0,
        "tool_calls": 0,
        "total_turns": 0,
        "total_steps": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
        "last_input_tokens": 0,
        "cost_usd": 0.0,
    }

    for entry in results:
        base_mode = entry.get("base_mode", {})
        skill_mode = entry.get("skill_mode", {})
        direct_exec_mode = entry.get("direct-exec_mode", {})

        if base_mode.get("completed"):
            summary["base_mode_completed"] += 1
        if base_mode.get("success"):
            summary["base_mode_success"] += 1

        if skill_mode.get("completed"):
            summary["skill_mode_completed"] += 1
        if skill_mode.get("success"):
            summary["skill_mode_success"] += 1

        if direct_exec_mode.get("completed"):
            summary["direct_exec_mode_completed"] += 1
        if direct_exec_mode.get("success"):
            summary["direct_exec_mode_success"] += 1

        if base_mode.get("success") and skill_mode.get("success"):
            summary["both_success"] += 1
            comparison = entry.get("comparison")
            if comparison:
                for metric in agg_base.keys():
                    agg_base[metric] += comparison.get("base_mode", {}).get(metric, 0)
                    agg_skill[metric] += comparison.get("skill_mode", {}).get(metric, 0)

        if (
            base_mode.get("partial_success")
            or skill_mode.get("partial_success")
            or direct_exec_mode.get("partial_success")
        ):
            summary["partial_tasks"] += 1

        if (
            base_mode.get("timeout")
            or skill_mode.get("timeout")
            or direct_exec_mode.get("timeout")
        ):
            summary["timeouts"] += 1

        if (
            base_mode.get("mcp_failure")
            or skill_mode.get("mcp_failure")
            or direct_exec_mode.get("mcp_failure")
        ):
            summary["mcp_failures"] += 1

        if (
            base_mode.get("api_rate_limit")
            or skill_mode.get("api_rate_limit")
            or direct_exec_mode.get("api_rate_limit")
        ):
            summary["api_rate_limits"] += 1

        if skill_mode.get("skill_saved"):
            summary["skill_saved_tasks"] += 1
        if skill_mode.get("skill_used"):
            summary["skill_used_tasks"] += 1

        summary["save_skill_calls_total"] += skill_mode.get("save_skill_calls", 0)
        summary["execute_skill_calls_total"] += skill_mode.get("execute_skill_calls", 0)
        summary["get_skill_calls_total"] += skill_mode.get("get_skill_calls", 0)
        summary["list_skills_calls_total"] += skill_mode.get("list_skills_calls", 0)

    if summary["both_success"] > 0:
        diff = {}
        for metric in agg_base.keys():
            diff_value = agg_skill[metric] - agg_base[metric]
            diff[metric] = diff_value
            diff[f"{metric}_diff_pct"] = calc_pct(agg_skill[metric], agg_base[metric])

        summary["aggregate_efficiency"] = {
            "both_success_tasks": summary["both_success"],
            "base_mode": agg_base,
            "skill_mode": agg_skill,
            "difference": diff,
        }

    return summary


def save_summary(run_dir: Path, model_name: str, provider: str, summary: dict) -> None:
    summary_file = run_dir / f"summary_{provider}_{model_name.replace('/', '_')}.json"
    write_json(summary, summary_file)


def should_skip_mode(existing_entry: dict, mode: str) -> bool:
    mode_key = f"{mode}_mode"
    mode_result = existing_entry.get(mode_key, {})
    return bool(mode_result.get("completed"))


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run SkillCraft scaled tasks in base/skill/direct-exec/cross-task/"
            "cross-model/static-reuse modes"
        )
    )
    parser.add_argument(
        "--mode",
        default="base,skill",
        help=(
            "Comma-separated modes: base,skill,direct-exec,cross-task,cross-model,static-reuse "
            "(or all)"
        ),
    )
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Model short name")
    parser.add_argument("--provider", default=DEFAULT_PROVIDER, help="Model provider")

    parser.add_argument(
        "--task",
        help="Single scaled task path, e.g. scaled_tasks/gitlab-deep-analysis/e1",
    )
    parser.add_argument(
        "--scaled-tasks",
        action="store_true",
        help="Retained option. Only scaled_tasks are supported.",
    )
    parser.add_argument(
        "--scaled-base",
        help="Comma-separated scaled base tasks",
    )
    parser.add_argument(
        "--scaled-level",
        help="Comma-separated levels (e1,m1,h1) or prefixes (e,m,h)",
    )
    parser.add_argument(
        "--scaled-tasks-subset",
        action="store_true",
        help="Run the predefined high-quality scaled-task subset",
    )
    parser.add_argument(
        "--continue-run",
        help="Continue in an existing run directory (e.g. test_runs/run_YYYYMMDD_HHMMSS)",
    )

    parser.add_argument(
        "--enable-parallel-tools",
        action="store_true",
        help="Enable parallel tool calls",
    )
    parser.add_argument(
        "--allow-skill-nesting",
        action="store_true",
        help="Allow skill nesting in skill-capable modes",
    )
    parser.add_argument(
        "--max-skill-nesting-depth",
        type=int,
        default=10,
        help="Maximum skill nesting depth when skill nesting is enabled",
    )

    # cross-model args
    parser.add_argument("--model-a", help="Cross-model creator model")
    parser.add_argument("--provider-a", help="Cross-model creator provider")
    parser.add_argument("--model-b", help="Cross-model user model")
    parser.add_argument("--provider-b", help="Cross-model user provider")

    # static-reuse args
    parser.add_argument("--skill-source", help="Source directory for pre-created skill caches")
    parser.add_argument(
        "--source-levels",
        help="Skill source difficulty filter, e.g. e or e1,e2,m1",
    )
    parser.add_argument(
        "--target-levels",
        help="Execution target difficulty filter, e.g. h or m1,h1",
    )

    args = parser.parse_args()

    try:
        modes = parse_modes(args.mode)
        run_paths = create_or_load_run_directory(args.continue_run)
        run_dir = Path(run_paths["run_dir"])

        if args.task:
            task_list = [validate_single_task(args.task)]
        else:
            base_tasks = parse_base_tasks(args.scaled_base, args.scaled_tasks_subset)
            levels = parse_levels(args.scaled_level, base_tasks)
            task_list = get_scaled_tasks(base_tasks, levels)
            if not task_list:
                raise ValueError("No scaled tasks matched current filters")

        print_color(f"Selected tasks: {len(task_list)}", "green")
        print_color(f"Modes: {', '.join(modes)}", "green")

        tester = TaskTester(
            model_name=args.model,
            provider=args.provider,
            run_paths=run_paths,
            enable_parallel_tools=args.enable_parallel_tools,
            allow_skill_nesting=args.allow_skill_nesting,
            max_skill_nesting_depth=args.max_skill_nesting_depth,
        )

        # ---------- Standard per-task modes ----------
        standard_modes = [m for m in modes if m in {"base", "skill", "direct-exec"}]
        ordered_results: List[Dict[str, Any]] = []
        summary: Optional[Dict[str, Any]] = None

        if standard_modes:
            existing_results = load_existing_results(run_dir, args.provider, args.model)
            result_map = {entry.get("task"): entry for entry in existing_results if entry.get("task")}
            task_order = [entry.get("task") for entry in existing_results if entry.get("task")]

            for index, task_path in enumerate(task_list, start=1):
                print_color("\n" + "-" * 70, "magenta")
                print_color(f"[{index}/{len(task_list)}] {task_path}", "magenta")
                print_color("-" * 70, "magenta")

                if task_path not in result_map:
                    result_map[task_path] = {
                        "task": task_path,
                        "model": args.model,
                        "provider": args.provider,
                        "timestamp": datetime.now().isoformat(),
                    }
                    task_order.append(task_path)

                entry = result_map[task_path]

                for mode in standard_modes:
                    mode_key = f"{mode}_mode"
                    if args.continue_run and should_skip_mode(entry, mode):
                        print_color(f"[SKIP] Existing completed result: {task_path} ({mode})", "yellow")
                        continue

                    print_color(f"[RUN] {task_path} ({mode})", "cyan")
                    entry[mode_key] = tester.run_task(task_path, mode)

                    save_results(
                        run_dir=run_dir,
                        model_name=args.model,
                        provider=args.provider,
                        run_timestamp=run_paths["run_timestamp"],
                        modes=standard_modes,
                        results=[result_map[t] for t in task_order if t in result_map],
                    )

                if entry.get("base_mode") and entry.get("skill_mode"):
                    entry["comparison"] = build_efficiency_comparison(
                        entry["base_mode"], entry["skill_mode"]
                    )

            ordered_results = [result_map[t] for t in task_order if t in result_map]
            save_results(
                run_dir=run_dir,
                model_name=args.model,
                provider=args.provider,
                run_timestamp=run_paths["run_timestamp"],
                modes=standard_modes,
                results=ordered_results,
            )

            summary = generate_summary(
                results=ordered_results,
                modes=standard_modes,
                model_name=args.model,
                provider=args.provider,
            )
            save_summary(run_dir, args.model, args.provider, summary)

        # ---------- Cross-task mode ----------
        special_outputs: Dict[str, str] = {}

        if "cross-task" in modes:
            print_color("\n" + "=" * 70, "cyan")
            print_color("[PHASE] cross-task", "cyan")
            print_color("=" * 70, "cyan")

            base_to_levels: Dict[str, List[str]] = {}
            if args.task:
                base, single_level = split_scaled_task(task_list[0])
                levels = [single_level]
                if args.scaled_level:
                    levels = parse_levels(args.scaled_level, [base])
                base_to_levels[base] = levels
            else:
                base_tasks = parse_base_tasks(args.scaled_base, args.scaled_tasks_subset)
                levels = parse_levels(args.scaled_level, base_tasks)
                for base in base_tasks:
                    valid_levels = []
                    for level in levels:
                        rel_path = PROJECT_ROOT / "tasks" / "scaled_tasks" / base / level / "task_config.json"
                        if rel_path.exists():
                            valid_levels.append(level)
                    if valid_levels:
                        base_to_levels[base] = valid_levels

            cross_task_summaries: Dict[str, Any] = {}
            for base_task, levels in base_to_levels.items():
                cross_task_summaries[base_task] = tester.run_cross_task_group(base_task, levels)

            cross_task_summary_file = run_dir / f"cross_task_summary_{args.provider}_{args.model.replace('/', '_')}.json"
            write_json(
                {
                    "mode": "cross-task",
                    "model": args.model,
                    "provider": args.provider,
                    "run_dir": str(run_dir),
                    "summaries": cross_task_summaries,
                    "generated_at": datetime.now().isoformat(),
                },
                cross_task_summary_file,
            )
            special_outputs["cross-task"] = str(cross_task_summary_file)

        # ---------- Direct-exec mode is handled in standard per-task modes ----------

        # ---------- Cross-model mode ----------
        if "cross-model" in modes:
            print_color("\n" + "=" * 70, "cyan")
            print_color("[PHASE] cross-model", "cyan")
            print_color("=" * 70, "cyan")

            if not args.model_a or not args.model_b:
                raise ValueError("cross-model mode requires --model-a and --model-b")

            provider_a = args.provider_a or args.provider
            provider_b = args.provider_b or args.provider
            cross_model_runner = CrossModelRunner(
                model_a=args.model_a,
                provider_a=provider_a,
                model_b=args.model_b,
                provider_b=provider_b,
                run_dir=run_dir,
                dump_dir=Path(run_paths["dump_cross_model"]),
            )

            cross_model_results: List[Dict[str, Any]] = []
            for index, task_path in enumerate(task_list, start=1):
                print_color(f"[CROSS-MODEL] [{index}/{len(task_list)}] {task_path}", "magenta")
                cross_model_results.append(tester.run_cross_model_task(task_path, cross_model_runner))

            cross_model_summary = cross_model_runner.save_summary_report()
            cross_model_results_file = run_dir / (
                f"cross_model_results_{args.model_a.replace('/', '_')}_to_{args.model_b.replace('/', '_')}.json"
            )
            write_json(
                {
                    "mode": "cross-model",
                    "model_a": args.model_a,
                    "provider_a": provider_a,
                    "model_b": args.model_b,
                    "provider_b": provider_b,
                    "run_dir": str(run_dir),
                    "results": cross_model_results,
                    "summary": cross_model_summary,
                    "generated_at": datetime.now().isoformat(),
                },
                cross_model_results_file,
            )
            special_outputs["cross-model"] = str(cross_model_results_file)

        # ---------- Static-reuse mode ----------
        if "static-reuse" in modes:
            print_color("\n" + "=" * 70, "cyan")
            print_color("[PHASE] static-reuse", "cyan")
            print_color("=" * 70, "cyan")

            if not args.skill_source:
                raise ValueError("static-reuse mode requires --skill-source")

            source_levels = [x.strip() for x in args.source_levels.split(",")] if args.source_levels else None
            static_runner = StaticReuseRunner(
                skill_source=args.skill_source,
                source_levels=source_levels,
                run_dir=run_dir,
                dump_dir=Path(run_paths["dump_static_reuse"]),
            )

            target_levels = StaticReuseRunner.parse_target_levels(args.target_levels)
            static_task_list = StaticReuseRunner.filter_tasks_by_levels(task_list, target_levels)
            if not static_task_list:
                raise ValueError("No tasks remained after applying --target-levels filter")

            static_results: List[Dict[str, Any]] = []
            for index, task_path in enumerate(static_task_list, start=1):
                task_group, _ = split_scaled_task(task_path)
                print_color(f"[STATIC-REUSE] [{index}/{len(static_task_list)}] {task_path}", "magenta")
                static_results.append(tester.run_static_reuse_task(task_path, static_runner, task_group))

            static_runner.save_execution_log()
            static_summary = static_runner.get_summary()
            static_results_file = run_dir / f"static_reuse_results_{args.provider}_{args.model.replace('/', '_')}.json"
            write_json(
                {
                    "mode": "static-reuse",
                    "model": args.model,
                    "provider": args.provider,
                    "skill_source": args.skill_source,
                    "source_levels": source_levels,
                    "target_levels": target_levels,
                    "run_dir": str(run_dir),
                    "results": static_results,
                    "summary": static_summary,
                    "generated_at": datetime.now().isoformat(),
                },
                static_results_file,
            )
            special_outputs["static-reuse"] = str(static_results_file)

        print_color("\n" + "=" * 70, "green")
        print_color("Pipeline finished", "green")
        print_color(f"Run directory: {run_dir}", "green")
        if summary is not None:
            print_color(f"Total standard tasks: {len(ordered_results)}", "green")
            print_color(f"Base success: {summary['base_mode_success']}", "green")
            print_color(f"Skill success: {summary['skill_mode_success']}", "green")
            print_color(f"Direct-exec success: {summary['direct_exec_mode_success']}", "green")
            print_color(f"Both success: {summary['both_success']}", "green")
        if special_outputs:
            print_color("Special-mode outputs:", "green")
            for mode_name, output_path in special_outputs.items():
                print_color(f"  - {mode_name}: {output_path}", "white")
        print_color("=" * 70 + "\n", "green")

        return 0

    except Exception as exc:
        print_color(f"[ERROR] {exc}", "red")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
