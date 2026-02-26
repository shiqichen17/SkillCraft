from typing import Any, Optional, Dict, List, Tuple, Callable
import os
import json
import uuid
import datetime
import traceback
from enum import Enum
import pickle
from pathlib import Path

from agents import (
    Agent,
    RunConfig,
    Usage,
    # Runner,
    ModelSettings,
    ToolCallItem,
    # MessageOutputItem,
    # ToolCallOutputItem,
    ModelProvider,
    ItemHelpers
)

from agents.exceptions import MaxTurnsExceeded

from utils.roles.context_managed_runner import ContextManagedRunner
from utils.api_model.model_provider import ContextTooLongError

from utils.mcp.tool_servers import MCPServerManager
from utils.api_model.model_provider import calculate_cost, get_context_window
from utils.roles.user import User, UserRuntimeConfig
from utils.api_model.openai_client import AsyncOpenAIClientWithRetry
from utils.general.helper import copy_folder_contents, run_command, specifical_inialize_for_mcp
from utils.data_structures.task_config import TaskConfig
from utils.data_structures.agent_config import AgentConfig
from utils.data_structures.mcp_config import MCPConfig
from utils.data_structures.user_config import UserConfig
import shutil

import asyncio
from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout

from utils.aux_tools.basic import tool_sleep, tool_done, tool_file_append, tool_file_write_json_chunk
from utils.aux_tools.ai_webpage_summary import tool_ai_webpage_summary
from utils.aux_tools.context_management_tools import context_management_tools
from utils.aux_tools.history_tools import history_tools
from utils.aux_tools.python_interpretor import tool_python_execute
from utils.aux_tools.web_search import tool_web_search
from utils.aux_tools.overlong_tool_manager import overlong_tool_tools
from utils.general.incremental_usage_tracker import (
    IncrementalUsageTracker, 
    reconstruct_usage_from_session_history,
    get_usage_from_model_tracking
)
from utils.aux_tools.skill_cache import skill_cache_tools, skill_cache_tools_full, skill_cache_tools_static
from utils.aux_tools.direct_exec import direct_exec_tools, reset_exec_history
# Atomic tools (for testing skill creation ability)
from utils.aux_tools.http_tools import http_tools
from utils.aux_tools.data_tools import data_tools
# M3ToolEval-based local tools
from utils.aux_tools.dna_tools import dna_tools
from utils.aux_tools.decoder_tools import decoder_tools
from utils.aux_tools.trade_tools import trade_tools
from utils.aux_tools.travel_tools import travel_tools
from utils.aux_tools.travel_tools_v2 import travel_tools_v2
from utils.aux_tools.travel_tools_merged import travel_tools_merged
# WebArena API-based local tools
from utils.aux_tools.gitlab_api import gitlab_api_tools
from utils.aux_tools.wikipedia_api import wikipedia_api_tools
from utils.aux_tools.map_api import map_api_tools
# Specialized tools for batch tasks (simplified for skill mode)
from utils.aux_tools.code_parser_tools import code_parser_tools
from utils.aux_tools.config_validator_tools import config_validator_tools
from utils.aux_tools.log_parser_tools import log_parser_tools
from utils.aux_tools.csv_tools import csv_tools
from utils.aux_tools.markdown_tools import markdown_tools
from utils.aux_tools.file_classifier_tools import file_classifier_tools
# New API-based tools for skill mode tasks
from utils.aux_tools.weather_tools import weather_tools
from utils.aux_tools.pokemon_tools import pokemon_tools
from utils.aux_tools.countries_tools import countries_tools
from utils.aux_tools.openlibrary_tools import openlibrary_tools
# Batch 1 API tools (2025-12)
from utils.aux_tools.jikan_tools import jikan_tools
from utils.aux_tools.tvmaze_tools import tvmaze_tools
from utils.aux_tools.usgs_earthquake_tools import usgs_earthquake_tools
from utils.aux_tools.dnd_tools import dnd_api_tools
# Batch 2 API tools (2025-12)
from utils.aux_tools.rickmorty_tools import rickmorty_tools
from utils.aux_tools.cocktail_tools import cocktail_tools
from utils.aux_tools.mealdb_tools import mealdb_tools
from utils.aux_tools.trivia_tools import trivia_tools
# Batch 3 API tools (2025-12)
from utils.aux_tools.musicbrainz_tools import musicbrainz_tools
from utils.aux_tools.dogapi_tools import dogapi_tools
from utils.aux_tools.university_tools import university_tools
# Batch 4 API tools (2025-12)
from utils.aux_tools.worldbank_tools import worldbank_tools
from utils.aux_tools.namedemographics_tools import namedemographics_tools
from utils.aux_tools.dictionary_tools import dictionary_tools
from utils.aux_tools.randomuser_tools import randomuser_tools
# Batch 5 API tools (2025-12)
from utils.aux_tools.jsonplaceholder_tools import jsonplaceholder_tools
from utils.aux_tools.catfacts_tools import catfacts_tools
from utils.aux_tools.nasa_tools import nasa_tools

from utils.general.helper import print_color
from utils.status_manager import TaskStatusManager

local_tool_mappings = {
    "ai_webpage_summary": tool_ai_webpage_summary,
    "sleep": tool_sleep,
    "claim_done": tool_done,
    "file_append": tool_file_append,
    "file_write_json_chunk": tool_file_write_json_chunk,
    "manage_context": context_management_tools,
    "history": history_tools,
    'python_execute': tool_python_execute,
    "web_search": tool_web_search,
    "handle_overlong_tool_outputs": overlong_tool_tools,
    "skill_cache": skill_cache_tools,
    "direct_exec": direct_exec_tools,
    # Atomic tools (for testing skill creation ability)
    "http_tools": http_tools,
    "data_tools": data_tools,
    # M3ToolEval-based tools
    "dna_tools": dna_tools,
    "decoder_tools": decoder_tools,
    "trade_tools": trade_tools,
    "travel_tools": travel_tools,
    "travel_tools_v2": travel_tools_v2,
    "travel_tools_merged": travel_tools_merged,
    # WebArena API-based tools
    "gitlab_api": gitlab_api_tools,
    "wikipedia_api": wikipedia_api_tools,
    "map_api": map_api_tools,
    # Specialized tools for batch tasks (simplified for skill mode)
    "code_parser_tools": code_parser_tools,
    "config_validator_tools": config_validator_tools,
    "log_parser_tools": log_parser_tools,
    "csv_tools": csv_tools,
    "markdown_tools": markdown_tools,
    "file_classifier_tools": file_classifier_tools,
    # New API-based tools for skill mode tasks
    "weather_tools": weather_tools,
    "pokemon_tools": pokemon_tools,
    "countries_tools": countries_tools,
    "openlibrary_tools": openlibrary_tools,
    # Batch 1 API tools (2025-12)
    "jikan_api": jikan_tools,
    "tvmaze_api": tvmaze_tools,
    "usgs_earthquake_api": usgs_earthquake_tools,
    "dnd_api": dnd_api_tools,
    # Batch 2 API tools (2025-12)
    "rickmorty_api": rickmorty_tools,
    "cocktail_api": cocktail_tools,
    "mealdb_api": mealdb_tools,
    "trivia_api": trivia_tools,
    # Batch 3 API tools (2025-12)
    "musicbrainz_api": musicbrainz_tools,
    "dogapi": dogapi_tools,
    "university_api": university_tools,
    # Batch 4 API tools (2025-12)
    "worldbank_api": worldbank_tools,
    "namedemographics_api": namedemographics_tools,
    "dictionary_api": dictionary_tools,
    "randomuser_api": randomuser_tools,
    # Batch 5 API tools (2025-12)
    "jsonplaceholder_api": jsonplaceholder_tools,
    "catfacts_api": catfacts_tools,
    "nasa_api": nasa_tools,
}

class TaskStatus(Enum):
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    MAX_TURNS_REACHED = "max_turns_reached"
    TOKEN_LIMIT_EXCEEDED = "token_limit_exceeded"  # Force terminated due to token limit
    INTERRUPTED = "interrupted"  # New status: task interrupted
    INCOMPLETE = "incomplete"  # Agent stopped without calling claim_done

class CustomJSONEncoder(json.JSONEncoder):
    """Custom JSON Encoder: write Python booleans as lowercase 'true'/'false'."""
    def default(self, o):
        if isinstance(o, bool):
            return str(o).lower()
        return super().default(o)

class TaskAgent:
    """Encapsulates an agent class to execute tasks."""
    
    def __init__(
        self,
        task_config: TaskConfig,
        agent_config: AgentConfig,
        agent_model_provider: ModelProvider,
        user_config: UserConfig,
        user_client: AsyncOpenAIClientWithRetry,
        mcp_config: MCPConfig,
        agent_hooks=None,
        run_hooks=None,
        termination_checker: Optional[Callable[[str, List[Dict], str], bool]] = None,
        debug: bool = False,
        allow_resume: bool = False,
        manual: bool = False,
        single_turn_mode: bool = False,
        tool_filter_config: Optional[Dict[str, List[str]]] = None,
    ):
        self.task_config = task_config
        self.agent_config = agent_config
        self.agent_model_provider = agent_model_provider
        self.user_config = user_config
        self.user_client = user_client
        self.mcp_config = mcp_config
        self.agent_hooks = agent_hooks
        self.run_hooks = run_hooks
        self.termination_checker = termination_checker or self._default_termination_checker
        self.tool_filter_config = tool_filter_config  # For strict skill test mode
        
        self.agent: Optional[Agent] = None
        self.mcp_manager: Optional[MCPServerManager] = None
        self.user_simulator: Optional[User] = None
        self.all_tools: List[Dict] = []
        # self.logs: List[Dict] = []
        self.session_id: Optional[str] = None
        self.history_dir: Optional[str] = None
        self.initial_run_time: Optional[str] = None
        self.logs_to_record: List[Dict] = []
        self.usage = Usage()
        self.task_status = TaskStatus.FAILED
        
        # Stats info
        self.stats = {
            "interaction_turns": 0,
            "tool_calls": 0,
            "agent_llm_requests": 0,
            "total_tokens": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "last_input_tokens": 0,  # Only the last API call's input tokens (no overlap)
            "total_in_turn_steps": 0,  # Total number of steps (items) across all turns
            # New metrics for fair comparison
            "skill_creation_output_tokens": 0,  # Output tokens used for creating skills (estimated)
            "save_skill_call_count": 0,  # Number of save_skill calls
        }
        
        # Track whether current turn involves skill creation
        self._current_turn_has_save_skill = False
        self._current_turn_output_tokens = 0
        
        # Track token limit exceeded status
        self._token_limit_exceeded = False
        self._token_limit_reason = None

        self.debug = debug
        self.allow_resume = allow_resume
        self.manual = manual
        if self.manual:
            # global prompt session
            self._session = PromptSession()
        
        # Checkpoint file path
        self.checkpoint_file = None
        self.checkpoint_interval = 1  # Save checkpoint every N turns

        self.single_turn_mode = single_turn_mode

        self.shared_context = {}

        # Save first-round user input for context reset
        self.first_user_input = None
        self.cumulative_inner_steps = 0  # Total count of assistant "inner steps"
        
        # Track if agent explicitly called claim_done
        self.agent_called_claim_done = False

        # Task status manager
        self.status_manager = TaskStatusManager(task_config.task_root)
        
        # Incremental usage tracker - for robust token tracking even on abnormal termination
        # Will be fully initialized when session starts (when history_dir and session_id are set)
        self._incremental_tracker: Optional[IncrementalUsageTracker] = None

    async def ainput(self, prompt='> '):
        """Async version of input()."""
        with patch_stdout():
            return await self._session.prompt_async(prompt)

    def _debug_print(self, *args):
        if self.debug:
            print(*args)

    def _sync_static_skill_skills(self, skills: dict) -> None:
        """
        Sync pre-loaded skills to workspace for static-skill mode.
        Called AFTER workspace initialization to ensure files persist.
        
        Args:
            skills: Dictionary of skills from static_skill_runner
        """
        import json
        from datetime import datetime
        
        workspace = Path(self.task_config.agent_workspace)
        workspace.mkdir(parents=True, exist_ok=True)
        
        cache_data = {
            "skills": skills,
            "metadata": {
                "mode": "static_skill",
                "read_only": True,
                "loaded_at": datetime.now().isoformat(),
                "skill_count": len(skills)
            }
        }
        
        target_file = workspace / "skill_cache.json"
        with open(target_file, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, indent=2, ensure_ascii=False)
        
        print_color(f"[DEBUG] Synced {len(skills)} static-skill skills to workspace", "green")

    def _update_incremental_tracker(self) -> None:
        """
        Update the incremental usage tracker with current stats.
        This ensures token data is persisted immediately for crash recovery.
        """
        if self._incremental_tracker is None:
            return
        
        try:
            # Get model-level cost tracking if available
            openrouter_cost = 0.0
            cost_source = "estimated"
            if hasattr(self, '_agent_model') and self._agent_model is not None:
                model_tracking = get_usage_from_model_tracking(self._agent_model)
                if model_tracking:
                    openrouter_cost = model_tracking.get('openrouter_cost', 0.0)
                    cost_source = model_tracking.get('cost_source', 'estimated')
            
            # Update tracker with current stats
            self._incremental_tracker.update(
                input_tokens=self.usage.input_tokens,
                output_tokens=self.usage.output_tokens,
                requests=self.usage.requests,
                last_input_tokens=self.stats.get("last_input_tokens", 0),
                tool_calls=self.stats.get("tool_calls", 0),
                turns=self.stats.get("interaction_turns", 0) + self.stats.get("assistant_turns", 0),
                openrouter_cost=openrouter_cost,
                cost_source=cost_source
            )
        except Exception as e:
            # Don't let tracker errors break the main flow
            self._debug_print(f"[USAGE TRACKER] Warning: Failed to update incremental tracker: {e}")

    def _extract_first_user_input(self) -> str:
        """Extract the user's first input."""
        if self.first_user_input:
            return self.first_user_input
        
        # If missing, try to extract from logs
        for log in self.logs:
            if log.get("role") == "user":
                return log.get("content", "")
        
        # Fallback to the task string
        return self.task_config.task_str

    def _reset_context_and_history(self) -> None:
        """Reset context and history, but preserve global turn/statistics/truncation info."""
        self._debug_print("Resetting context and history due to context too long error")
        
        # Save important info from context
        session_id = self.shared_context.get("_session_id")
        history_dir = self.shared_context.get("_history_dir")
        agent_workspace = self.shared_context.get("_agent_workspace")
        context_limit = self.shared_context.get("_context_limit")
        
        # Save accumulative info from meta
        meta = self.shared_context.get("_context_meta", {})
        current_turn = meta.get("current_turn", 0)
        total_turns_ever = meta.get("total_turns_ever", 0)
        truncated_turns = meta.get("truncated_turns", 0)
        truncation_history = meta.get("truncation_history", [])
        started_at = meta.get("started_at", datetime.datetime.now().isoformat())
        
        turns_in_current_sequence = meta.get("turns_in_current_sequence", 0)
        new_truncated_turns = truncated_turns + turns_in_current_sequence
        
        # Update truncation history
        new_truncation_history = truncation_history.copy()
        new_truncation_history.append({
            "at_turn": current_turn,
            "method": "force_reset_context",
            "value": "all_current_sequence",
            "deleted_turns": turns_in_current_sequence,
            "timestamp": datetime.datetime.now().isoformat(),
            "reason": "Context too long error"
        })
        
        # Reset shared_context, preserving selected info
        self.shared_context = {
            "_agent_workspace": agent_workspace,
            "_session_id": session_id,
            "_history_dir": history_dir,
            "_context_meta": {
                "session_id": session_id,
                "history_dir": history_dir,
                "started_at": started_at,
                "current_turn": current_turn,
                "total_turns_ever": total_turns_ever,
                "turns_in_current_sequence": 0,
                "mini_turns_in_current_sequence": 0,
                "boundary_in_current_sequence": [],
                "truncated_turns": new_truncated_turns,
                "truncation_history": new_truncation_history,
                "context_reset": True,
                "reset_timestamp": datetime.datetime.now().isoformat()
            },
            "_context_limit": context_limit
        }
        
        # Clear logs
        self.logs = []

    def _default_termination_checker(self, content: str, recent_tools: List[Dict], check_target: str = "user") -> bool:
        """Default termination checker."""
        if check_target == 'user':
            return '#### STOP' in content
        return False
    
    def _get_checkpoint_path(self) -> str:
        """Get checkpoint file path."""
        if self.checkpoint_file is None:
            self.checkpoint_file = os.path.join(self.task_config.task_root, "checkpoint.pkl")
        return self.checkpoint_file
    
    async def _save_checkpoint(self) -> None:
        """Save current state to checkpoint."""
        if not self.allow_resume:
            return
            
        checkpoint_data = {
            'logs': self.logs.copy(),
            'logs_to_record': self.logs_to_record.copy(),
            'all_tools': self.all_tools.copy(),
            'stats': self.stats.copy(),
            'usage': {
                'input_tokens': self.usage.input_tokens,
                'output_tokens': self.usage.output_tokens,
                'requests': self.usage.requests
            },
            'user_simulator_state': self.user_simulator.get_state() if hasattr(self.user_simulator, 'get_state') else {
                'conversation_history': self.user_simulator.conversation_history if self.user_simulator else []
            },
            'session_id': self.session_id,
            'history_dir': self.history_dir,
            'initial_run_time': getattr(self, 'initial_run_time', 'unknown'),
            'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'version': '2.0'
        }
        
        try:
            with open(self._get_checkpoint_path(), 'wb') as f:
                pickle.dump(checkpoint_data, f)
            self._debug_print(f"Checkpoint saved at turn {self.stats['interaction_turns']}")
        except Exception as e:
            self._debug_print(f"Failed to save checkpoint: {e}")

    async def _load_checkpoint(self) -> bool:
        """Restore state from checkpoint, if possible."""
        if not self.allow_resume:
            return False
            
        checkpoint_path = self._get_checkpoint_path()
        if not os.path.exists(checkpoint_path):
            self._debug_print("No checkpoint found")
            return False
            
        try:
            with open(checkpoint_path, 'rb') as f:
                checkpoint_data = pickle.load(f)
            
            # Version check
            version = checkpoint_data.get('version', '1.0')
            if version == '1.0':
                self._debug_print("Old checkpoint version detected, cannot resume")
                return False
            
            # Restore state
            self.logs = checkpoint_data['logs']
            self.logs_to_record = checkpoint_data['logs_to_record']
            self.all_tools = checkpoint_data['all_tools']
            self.stats = checkpoint_data['stats']
            
            # Restore session info
            self.session_id = checkpoint_data.get('session_id')
            self.history_dir = checkpoint_data.get('history_dir')
            self.initial_run_time = checkpoint_data.get('initial_run_time', 'unknown')
            
            # Restore usage object
            usage_data = checkpoint_data['usage']
            self.usage.input_tokens = usage_data['input_tokens']
            self.usage.output_tokens = usage_data['output_tokens']
            self.usage.requests = usage_data['requests']
            
            # Restore user simulator state
            if self.user_simulator:
                if hasattr(self.user_simulator, 'set_state'):
                    self.user_simulator.set_state(checkpoint_data['user_simulator_state'])
                else:
                    self.user_simulator.conversation_history = checkpoint_data['user_simulator_state'].get('conversation_history', [])
            
            self._debug_print(f"Checkpoint loaded from {checkpoint_data['timestamp']}")
            self._debug_print(f"Resuming from turn {self.stats['interaction_turns']}")
            self._debug_print(f"Session ID: {self.session_id}")
            return True
            
        except Exception as e:
            self._debug_print(f"Failed to load checkpoint: {e}")
            return False
    
    def _remove_checkpoint(self) -> None:
        """Remove checkpoint file."""
        checkpoint_path = self._get_checkpoint_path()
        if os.path.exists(checkpoint_path):
            try:
                os.remove(checkpoint_path)
                self._debug_print("Checkpoint removed")
            except Exception as e:
                self._debug_print(f"Failed to remove checkpoint: {e}")

    async def initialize_workspace(self, show_traceback=False) -> bool:
        """Initialize workspace."""
        self._debug_print(f"\n\nStarting to initialize workspace for {self.task_config.id} ...")
        
        log_file = self.task_config.log_file
        agent_workspace = self.task_config.agent_workspace
        initial_state_workspace = self.task_config.initialization.workspace

        try:
            # If resume is allowed and checkpoint exists, skip reinitializing
            if self.allow_resume and os.path.exists(agent_workspace) and os.path.exists(self._get_checkpoint_path()):
                self._debug_print("Found existing workspace and checkpoint, will attempt to resume")
                return True
            
            # Otherwise do a standard workspace init
            if os.path.exists(agent_workspace):
                self._debug_print("Reset/Remove an existing agent workspace.")
                shutil.rmtree(agent_workspace)

            if os.path.exists(log_file):
                self._debug_print("Reset/Remove an existing log file.")
                os.remove(log_file)
            
            # Remove old checkpoint
            self._remove_checkpoint()
            
            # Copy initial state files
            await copy_folder_contents(initial_state_workspace, agent_workspace, self.debug)

            # Pre-processing command if any
            if self.task_config.initialization.process_command is not None:
                args = f"--agent_workspace {self.task_config.agent_workspace} --launch_time \"{self.task_config.launch_time}\""
                command = f"{self.task_config.initialization.process_command} {args}"
                output, error, returncode = await run_command(command, debug=self.debug)
                if self.debug:
                    print_color("== PreProcess STDOUT ==", "red")
                self._debug_print(output)
                if self.debug:
                    print_color("== PreProcess STDERR ==", "red")
                self._debug_print(error)
                if returncode != 0:
                    raise RuntimeError(f"PreProcess command failed! returncode: {returncode}")
                
            # MCP-specific workspace initialization
            await specifical_inialize_for_mcp(self.task_config)

        except Exception as e:
            # Always print the error reason, not just in debug mode
            print_color(f"[ERROR] Workspace initialization failed!", "red")
            print_color(f"[ERROR] Reason: {type(e).__name__}: {e}", "red")
            if show_traceback or self.debug:
                traceback.print_exc()
            return False

        self._debug_print(f"Successfully initialize workspace for {self.task_config.id}!")
        return True

    async def setup_mcp_servers(self, local_token_key_session: Dict) -> None:
        """Setup and connect to MCP servers."""

        if self.debug:
            print_color("\n=== Starting to setup MCP servers ===", "blue")

        self.mcp_manager = MCPServerManager(
            agent_workspace=self.task_config.agent_workspace,
            config_dir=self.mcp_config.server_config_path,
            debug=self.debug,
            local_token_key_session=local_token_key_session,
            tool_filter_config=self.tool_filter_config
        )
        await self.mcp_manager.connect_servers(self.task_config.needed_mcp_servers)
    
    async def setup_agent(self) -> None:
        """Initialize Agent."""
        self._debug_print(">>Initializing agent loop")

        # Check if skill cache should be enabled
        enable_skill_cache = (
            self.task_config.global_task_config.get('enable_skill_cache', False)
            if self.task_config.global_task_config else False
        )

        # Check if this is static-skill mode (NO save_skill)
        static_skill_mode = (
            self.task_config.global_task_config.get('static_skill_mode', False)
            if self.task_config.global_task_config else False
        )

        local_tools = []
        if self.task_config.needed_local_tools is not None:
            for tool_name in self.task_config.needed_local_tools:
                # Filter out skill_cache tools when not in skill mode
                if tool_name == 'skill_cache' and not enable_skill_cache:
                    self._debug_print(f"[INFO] Skipping skill_cache tools (enable_skill_cache={enable_skill_cache})")
                    continue
                
                # In static-skill mode, skip skill_cache from needed_local_tools
                # The correct toolset (without save_skill) will be auto-loaded later
                if tool_name == 'skill_cache' and static_skill_mode:
                    self._debug_print(f"[INFO] Skipping skill_cache from needed_local_tools (static_skill_mode=True, will auto-load correct toolset)")
                    continue

                tool_or_toolsets = local_tool_mappings[tool_name]
                if isinstance(tool_or_toolsets, list):
                    local_tools.extend(tool_or_toolsets)
                else:
                    local_tools.append(tool_or_toolsets)

        # Auto-load skill_cache tools when enable_skill_cache=true
        # This ensures tools match the system prompt guidance
        if enable_skill_cache:
            # Check if this is cross-task mode (includes get_skill and list_skills)
            cross_task_mode = (
                self.task_config.global_task_config.get('cross_task_mode', False)
                if self.task_config.global_task_config else False
            )
            
            # Check if skill_cache tools are already loaded
            existing_tool_names = {tool.name for tool in local_tools if hasattr(tool, 'name')}
            
            # Core tools that should always be present (except static-skill which skips save_skill)
            core_skill_tools = {'local-save_skill', 'local-execute_skill'}
            # Extra tools for cross-task mode
            cross_task_extra_tools = {'local-get_skill', 'local-list_skills'}

            if not core_skill_tools.intersection(existing_tool_names):
                # No skill_cache tools loaded yet - load the appropriate set
                if static_skill_mode:
                    # Static-skill mode: NO save_skill, only execute/get/list
                    tools_to_load = skill_cache_tools_static
                    mode_desc = "static-skill mode (no save_skill)"
                elif cross_task_mode:
                    tools_to_load = skill_cache_tools_full
                    mode_desc = "cross-task mode (with get/list)"
                else:
                    tools_to_load = skill_cache_tools
                    mode_desc = "standard mode"
                local_tools.extend(tools_to_load)
                self._debug_print(f"✓ Auto-loaded skill_cache tools ({mode_desc})")
            elif cross_task_mode and not cross_task_extra_tools.intersection(existing_tool_names):
                # Core tools exist but cross-task extra tools are missing - add them
                # Import the specific tools we need
                from utils.aux_tools.skill_cache import tool_get_skill, tool_list_skills
                local_tools.extend([tool_get_skill, tool_list_skills])
                self._debug_print("✓ Added get_skill and list_skills for cross-task mode")
            else:
                self._debug_print("✓ Skill_cache tools already in needed_local_tools")
        
        # Auto-load direct_exec tools when enable_direct_exec=true
        # This ensures tools match the system prompt guidance (mutually exclusive with skill_cache)
        enable_direct_exec = (
            self.task_config.global_task_config.get('enable_direct_exec', False)
            if self.task_config.global_task_config else False
        )
        
        if enable_direct_exec and not enable_skill_cache:
            # Reset exec history for new task
            reset_exec_history()
            self._debug_print("✓ Reset direct_exec history for new task")
            
            # Check if direct_exec tools are already loaded
            existing_tool_names = {tool.name for tool in local_tools if hasattr(tool, 'name')}
            
            # Core direct_exec tool
            direct_exec_tool_name = 'local-exec_script'
            
            if direct_exec_tool_name not in existing_tool_names:
                local_tools.extend(direct_exec_tools)
                self._debug_print("✓ Auto-loaded direct_exec tools (exec_script)")
            else:
                self._debug_print("✓ Direct_exec tools already in needed_local_tools")
        
        # Auto-load chunked file writing tools whenever claim_done is available
        # These help avoid truncation issues when writing large JSON outputs
        existing_tool_names = {tool.name for tool in local_tools if hasattr(tool, 'name')}
        if 'local-claim_done' in existing_tool_names:
            chunked_write_tools = {'local-file_append', 'local-file_write_json_chunk'}
            if not chunked_write_tools.intersection(existing_tool_names):
                local_tools.append(tool_file_append)
                local_tools.append(tool_file_write_json_chunk)
                self._debug_print("✓ Auto-loaded chunked file writing tools (for truncation handling)")
        
        # Save local_tools for skill_cache to use
        self._local_tools = local_tools

        # Create model and store reference for cost tracking
        self._agent_model = self.agent_model_provider.get_model(
            self.agent_config.model.real_name, 
            debug=self.debug,
            short_model_name=self.agent_config.model.short_name
        )
        
        self.agent = Agent(
            name="Assistant",
            instructions=self.task_config.system_prompts.agent,
            model=self._agent_model,
            mcp_servers=[*self.mcp_manager.get_all_connected_servers()],
            tools=local_tools,
            hooks=self.agent_hooks,
            model_settings=ModelSettings(
                temperature=self.agent_config.generation.temperature,
                top_p=self.agent_config.generation.top_p,
                max_tokens=self.agent_config.generation.max_tokens,
                tool_choice=self.agent_config.tool.tool_choice,
                parallel_tool_calls=self.agent_config.tool.parallel_tool_calls,
                extra_body=self.agent_config.generation.extra_body,
            ),
        )
        
        # Get all available tools
        available_tools = await self.agent.get_all_tools()
        for tool in available_tools:
            self.all_tools.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.params_json_schema
                }
            })
    
    async def setup_user_simulator(self) -> None:
        """Initialize user simulator."""
        user_runtime_config = UserRuntimeConfig(
            global_config=self.user_config,
            starting_system_prompt=self.task_config.system_prompts.user,
        )
        self.user_simulator = User(
            client=self.user_client,
            user_config=user_runtime_config
        )
        self.user_simulator.initialize_conversation()

    async def process_agent_response(self, result) -> List[Dict]:
        """Process the agent's response, returning a list of tool calls (simplified version)."""
        tool_calls_in_response = []
        has_save_skill = False
        
        # Extract tool call info for termination check
        for item in result.new_items:
            if isinstance(item, ToolCallItem):
                tool_item = item.to_input_item()
                tool_call = {
                    "id": tool_item['call_id'],
                    "type": "function",
                    "function": {
                        "name": tool_item["name"],
                        "arguments": tool_item["arguments"]
                    }
                }
                tool_calls_in_response.append(tool_call)
                
                # Check if this is a save_skill call
                if 'save_skill' in tool_item["name"]:
                    has_save_skill = True
        
        # Track save_skill calls for later cost estimation
        if has_save_skill:
            self._current_turn_has_save_skill = True
            self.stats["save_skill_call_count"] += 1
        
        # Update tool call statistics
        self.stats["tool_calls"] += len(tool_calls_in_response)
        
        # Record simplified log
        if result.final_output:
            self.logs_to_record.append({
                "role": "assistant",
                "content": result.final_output,
                "tool_calls_count": len(tool_calls_in_response)
            })
        
        return tool_calls_in_response

    async def run_interaction_loop(self,
                                   abs_original_task_root: str) -> None:
        """Run the main interaction loop."""
        # Use a fixed session_id
        self.session_id = f"task_{self.task_config.id}_session"
        self.history_dir = os.path.join(abs_original_task_root, "conversation_history")
        
        # Ensure conversation_history directory exists early, even if task fails
        # This ensures the directory structure is preserved even for failed tasks
        os.makedirs(self.history_dir, exist_ok=True)
        
        # Initialize incremental usage tracker for robust token tracking
        self._incremental_tracker = IncrementalUsageTracker(
            tracking_dir=Path(self.history_dir),
            session_id=self.session_id
        )
        self._debug_print(f"[USAGE TRACKER] Initialized incremental tracker at {self.history_dir}")
        
        # Initialize chat logs
        self.logs = []
        
        # Check if cross-task mode is enabled
        cross_task_mode = (
            self.task_config.global_task_config.get('cross_task_mode', False)
            if self.task_config.global_task_config else False
        )
        
        # Get skill nesting configuration from global_task_config
        allow_skill_nesting = (
            self.task_config.global_task_config.get('allow_skill_nesting', cross_task_mode)
            if self.task_config.global_task_config else cross_task_mode
        )
        max_skill_nesting_depth = (
            self.task_config.global_task_config.get('max_skill_nesting_depth', 10)
            if self.task_config.global_task_config else 5
        )
        
        # Get shared skill cache path for cross-task mode
        shared_skill_cache_path = (
            self.task_config.global_task_config.get('shared_skill_cache_path')
            if self.task_config.global_task_config else None
        )
        
        # Initialize shared context (important!)
        self.shared_context = {
            "_agent_workspace": self.task_config.agent_workspace,
            "_session_id": self.session_id,
            "_history_dir": self.history_dir,
            "_mcp_manager": self.mcp_manager,  # Add MCP manager for skill_cache tool access
            "_local_tools": getattr(self, '_local_tools', []),  # Add local tools for skill_cache
            "_cross_task_mode": cross_task_mode,  # Enable skill nesting in cross-task mode
            # Shared skill cache path for cross-task mode (allows list_skills/get_skill to read shared cache)
            "_skill_cache_path": shared_skill_cache_path,
            # Skill nesting configuration
            "_allow_skill_nesting": allow_skill_nesting,
            "_max_skill_nesting_depth": max_skill_nesting_depth,
            "_current_skill_nesting_depth": 0,  # Start at depth 0 (top level)
            "_context_meta": {
                "session_id": self.session_id,
                "history_dir": self.history_dir,
                "started_at": datetime.datetime.now().isoformat(),
                "current_turn": -1,
                "total_turns_ever": 0,
                "turns_in_current_sequence": 0,
                "mini_turns_in_current_sequence": 0,
                "boundary_in_current_sequence": [],
                "truncated_turns": 0,
                "truncation_history": []
            },
            "_context_limit": get_context_window(self.agent_config.model.short_name)
        }

        # Attempt load from checkpoint if allowed
        resumed = False
        if self.allow_resume:
            resumed = await self._load_checkpoint()
        
        history_file = os.path.join(self.history_dir, f"{self.session_id}_history.jsonl")
        
        if resumed:
            # If resumed, try to rebuild logs from history
            self.logs = self._rebuild_logs_from_history(history_file)
            self._debug_print(f"Resuming session {self.session_id} with {len(self.logs)} messages")
        else:
            self.initial_run_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            if os.path.exists(history_file):
                self._debug_print(f"Removing old history file for session {self.session_id}")
                os.remove(history_file)
            
            self.logs = []
        
        real_max_turns = 1 if self.single_turn_mode else self.task_config.max_turns

        if self.debug:
            print_color("=== Starting interaction loop ===", "blue")

        print_color(f"[DEBUG] Interaction loop: max_turns={real_max_turns}, single_turn_mode={self.single_turn_mode}", "cyan")

        while self.stats["interaction_turns"] < real_max_turns:
            # CRITICAL: Check termination at the very start of each outer loop iteration
            # This catches cases where the flag was set but the break didn't execute
            if self.agent_called_claim_done:
                print_color(f"[DEBUG] agent_called_claim_done=True at start of outer loop, breaking!", "green")
                break
            if self.shared_context.get('_claim_done_called', False):
                print_color(f"[DEBUG] _claim_done_called=True at start of outer loop, breaking!", "green")
                self.agent_called_claim_done = True
                self.shared_context['_claim_done_called'] = False
                break
            
            try:
                print_color(f"\n[DEBUG] ===== Turn {self.stats['interaction_turns'] + 1}/{real_max_turns} =====", "cyan")
                # Reset cumulative inner assistant steps for this round
                self.cumulative_inner_steps = 0

                # Get user input
                print_color("[DEBUG] Getting user input...", "cyan")
                if self.single_turn_mode:
                    user_query = self.task_config.task_str
                    print_color(f"[DEBUG] Single-turn mode - using task string (length: {len(user_query)} chars)", "cyan")
                elif self.manual:
                    user_query = await self.ainput("USER: ")
                else:
                    user_query = await self.user_simulator.interact()
                    self._debug_print(f"USER: {user_query}")

                # Save first user input for context reset
                if self.first_user_input is None:
                    self.first_user_input = user_query

                # Append to logs
                self.logs.append({"role": "user", "content": user_query})

                # Update per-turn stats in context meta
                current_turn_in_seq = self.shared_context["_context_meta"]["turns_in_current_sequence"]
                mini_turns_in_current_sequence = self.shared_context["_context_meta"]["mini_turns_in_current_sequence"]
                self.shared_context["_context_meta"]["boundary_in_current_sequence"].append((mini_turns_in_current_sequence, 
                                                                                             mini_turns_in_current_sequence+1))
                
                self.shared_context["_context_meta"]["turns_in_current_sequence"] = current_turn_in_seq + 1
                self.shared_context["_context_meta"]["mini_turns_in_current_sequence"] += 1
                self.shared_context["_context_meta"]["total_turns_ever"] += 1
                self.shared_context["_context_meta"]["current_turn"] += 1

                # Save user input to file history
                current_turn = self.shared_context["_context_meta"]["current_turn"]
                ContextManagedRunner._save_user_input_to_history(
                    session_id=self.session_id,
                    user_input=user_query,
                    history_dir=self.history_dir,
                    turn_number=current_turn
                )

                # Add to logs (to be recorded in results)
                self.logs_to_record.append({"role": "user", "content": user_query})
                
                # Increase interaction turn
                self.stats["interaction_turns"] += 1
                
                # Check user input for termination
                if self.termination_checker(user_query, [], 'user'):
                    self._debug_print("Termination condition met by user input")
                    break
                
                # Agent response: context reset etc handled with inner loop
                max_inner_steps = self.agent_config.tool.max_inner_turns if not self.single_turn_mode else self.task_config.max_steps_under_single_turn_mode
                result = None

                print_color(f"[DEBUG] Preparing Agent response (max_inner_steps: {max_inner_steps})...", "cyan")

                while self.cumulative_inner_steps < max_inner_steps:
                    # CRITICAL: Check termination at start of inner loop
                    if self.agent_called_claim_done or self.shared_context.get('_claim_done_called', False):
                        print_color(f"[DEBUG] Termination flag detected at start of inner loop, breaking!", "green")
                        if self.shared_context.get('_claim_done_called', False):
                            self.agent_called_claim_done = True
                            self.shared_context['_claim_done_called'] = False
                        break
                    
                    remaining_steps = max_inner_steps - self.cumulative_inner_steps
                    print_color(f"[DEBUG] Agent inner loop: step {self.cumulative_inner_steps}/{max_inner_steps}, remaining: {remaining_steps}", "cyan")

                    try:
                        print_color(f"[DEBUG] Calling ContextManagedRunner.run()...", "cyan")
                        turn_before = self.shared_context["_context_meta"]["current_turn"]
                        result = await ContextManagedRunner.run(
                            starting_agent=self.agent,
                            input=self.logs,
                            context=self.shared_context,
                            run_config=RunConfig(model_provider=self.agent_model_provider),
                            hooks=self.run_hooks,
                            max_turns=remaining_steps,
                            history_dir=self.history_dir,
                            session_id=self.session_id,
                        )
                        print_color(f"[DEBUG] ContextManagedRunner.run() completed successfully", "green")
                        
                        # DEBUG: Inspect result object for token stats
                        print_color(f"[DEBUG RESULT] result type: {type(result)}", "magenta")
                        print_color(f"[DEBUG RESULT] result.raw_responses count: {len(result.raw_responses) if result.raw_responses else 0}", "magenta")
                        if hasattr(result, 'context_wrapper') and hasattr(result.context_wrapper, 'usage'):
                            ctx_usage = result.context_wrapper.usage
                            print_color(f"[DEBUG RESULT] context_wrapper.usage: input={ctx_usage.input_tokens}, output={ctx_usage.output_tokens}, requests={ctx_usage.requests}", "magenta")
                        
                        # CRITICAL: Always collect token stats from context_wrapper.usage immediately after run()
                        # This ensures we capture tokens even if claim_done is never called
                        if hasattr(result, 'context_wrapper') and hasattr(result.context_wrapper, 'usage'):
                            ctx_usage = result.context_wrapper.usage
                            if ctx_usage.input_tokens > 0 or ctx_usage.output_tokens > 0:
                                # Update our usage tracker with the cumulative values from context_wrapper
                                # context_wrapper.usage contains cumulative totals across all turns
                                if ctx_usage.input_tokens > self.usage.input_tokens:
                                    self.usage.input_tokens = ctx_usage.input_tokens
                                if ctx_usage.output_tokens > self.usage.output_tokens:
                                    self.usage.output_tokens = ctx_usage.output_tokens
                                if ctx_usage.requests > self.usage.requests:
                                    self.usage.requests = ctx_usage.requests
                                    self.stats["agent_llm_requests"] = ctx_usage.requests
                                # Update last_input_tokens to the most recent value
                                # For cumulative tracking, we use total input as approximation
                                if self.stats.get("last_input_tokens", 0) == 0:
                                    self.stats["last_input_tokens"] = ctx_usage.input_tokens
                                print_color(f"[DEBUG] Token stats updated from context_wrapper: input={self.usage.input_tokens}, output={self.usage.output_tokens}", "green")
                                
                                # ROBUST TRACKING: Update incremental tracker immediately
                                self._update_incremental_tracker()
                        
                        # Check token limits - force terminate if exceeded
                        if self.task_config.max_input_tokens and self.usage.input_tokens > self.task_config.max_input_tokens:
                            print_color(f"[TOKEN LIMIT] Cumulative input tokens ({self.usage.input_tokens:,}) exceeded limit ({self.task_config.max_input_tokens:,}). Force terminating task.", "red")
                            self._token_limit_exceeded = True
                            self._token_limit_reason = f"Cumulative input tokens exceeded: {self.usage.input_tokens:,} > {self.task_config.max_input_tokens:,}"
                            should_terminate = True
                            break
                        
                        if self.task_config.max_output_tokens and self.usage.output_tokens > self.task_config.max_output_tokens:
                            print_color(f"[TOKEN LIMIT] Cumulative output tokens ({self.usage.output_tokens:,}) exceeded limit ({self.task_config.max_output_tokens:,}). Force terminating task.", "red")
                            self._token_limit_exceeded = True
                            self._token_limit_reason = f"Cumulative output tokens exceeded: {self.usage.output_tokens:,} > {self.task_config.max_output_tokens:,}"
                            should_terminate = True
                            break
                        
                        # Check single request input token limit - prevents runaway context growth
                        # This checks if the LAST request's input tokens exceeded the limit
                        if self.task_config.max_single_request_input_tokens:
                            last_request_input = 0
                            # Try to get from raw_responses (most accurate)
                            if result.raw_responses and len(result.raw_responses) > 0:
                                last_response = result.raw_responses[-1]
                                if hasattr(last_response, 'usage') and last_response.usage:
                                    last_request_input = getattr(last_response.usage, 'input_tokens', 0) or 0
                            # Fallback: use last_input_tokens from stats if available
                            if last_request_input == 0:
                                last_request_input = self.stats.get("last_input_tokens", 0)
                            
                            if last_request_input > self.task_config.max_single_request_input_tokens:
                                print_color(f"[TOKEN LIMIT] Single request input tokens ({last_request_input:,}) exceeded limit ({self.task_config.max_single_request_input_tokens:,}). Context is too large, force terminating task.", "red")
                                self._token_limit_exceeded = True
                                self._token_limit_reason = f"Single request input tokens exceeded: {last_request_input:,} > {self.task_config.max_single_request_input_tokens:,}"
                                should_terminate = True
                                break
                        
                        turn_after = self.shared_context["_context_meta"]["current_turn"]
                        
                        # Count number of agent turns used in the step
                        self.cumulative_inner_steps += turn_after - turn_before
                        self._debug_print(f"\033[92m[INFO] Used {turn_after - turn_before} assistant turns, total: {self.cumulative_inner_steps}/{max_inner_steps}\033[0m")
                        
                        # Check if agent made any tool calls in this response
                        # NOTE: Must check item_type (not item.type) for correct detection
                        # ToolCallItem has item_type='tool_call_item'
                        has_tool_calls = any(
                            isinstance(item, ToolCallItem) or
                            (hasattr(item, 'item_type') and item.item_type == 'tool_call_item') or  
                            (hasattr(item, 'type') and item.type in ('tool_call_item', 'function_call'))
                            for item in (result.new_items if result else [])
                        )
                        
                        # DEBUG: Log tool call detection results
                        print_color(f"[DEBUG] has_tool_calls={has_tool_calls}, new_items count={len(result.new_items) if result else 0}", "cyan")
                        if result and result.new_items:
                            for i, item in enumerate(result.new_items[:5]):  # Log first 5 items
                                item_type = getattr(item, 'type', type(item).__name__)
                                print_color(f"[DEBUG]   item[{i}]: type={item_type}, isinstance(ToolCallItem)={isinstance(item, ToolCallItem)}", "cyan")
                        
                        # In single_turn_mode: if agent sent text-only response, nudge it to continue
                        if self.single_turn_mode and not has_tool_calls:
                            print_color(f"[DEBUG] Agent sent text-only response, adding nudge message and continuing...", "yellow")
                            
                            # Still collect LLM statistics even for text-only responses
                            prev_output_tokens = self.usage.output_tokens
                            if result.raw_responses:
                                for raw_response in result.raw_responses:
                                    self.usage.add(raw_response.usage)
                                    self.stats["agent_llm_requests"] += 1
                                    if raw_response.usage and hasattr(raw_response.usage, 'input_tokens'):
                                        self.stats["last_input_tokens"] = raw_response.usage.input_tokens
                            elif hasattr(result, 'context_wrapper') and hasattr(result.context_wrapper, 'usage'):
                                ctx_usage = result.context_wrapper.usage
                                if ctx_usage.input_tokens > 0 or ctx_usage.output_tokens > 0:
                                    new_input = ctx_usage.input_tokens - self.usage.input_tokens
                                    new_output = ctx_usage.output_tokens - self.usage.output_tokens
                                    if new_input > 0 or new_output > 0:
                                        self.usage.input_tokens = ctx_usage.input_tokens
                                        self.usage.output_tokens = ctx_usage.output_tokens
                                        self.usage.requests = ctx_usage.requests
                                        self.stats["agent_llm_requests"] = ctx_usage.requests
                                        self.stats["last_input_tokens"] = new_input if new_input > 0 else ctx_usage.input_tokens
                                        print_color(f"[DEBUG] Text-only response: using context_wrapper.usage fallback", "yellow")
                            self.stats["total_in_turn_steps"] += len(result.new_items)
                            
                            # ROBUST TRACKING: Update incremental tracker after text-only response
                            self._update_incremental_tracker()
                            
                            # First, update logs with the agent's response so it sees its own message
                            self.logs = self.build_new_logs(result.input, result.new_items)
                            # Then add the nudge message
                            nudge_message = (
                                "[SYSTEM REMINDER] You sent a text-only response without calling any tools. "
                                "The task is NOT complete yet. You MUST either:\n"
                                "1. Continue working by calling the appropriate tools to complete the task, OR\n"
                                "2. Save your final results to a file and call claim_done when finished.\n"
                                "DO NOT just describe what you plan to do - actually DO IT by calling tools.\n"
                                "Please continue with the task NOW."
                            )
                            self.logs.append({"role": "user", "content": nudge_message})
                            print_color(f"[DEBUG] Nudge added, cumulative_inner_steps={self.cumulative_inner_steps}, max_inner_steps={max_inner_steps}", "yellow")
                            print_color(f"[DEBUG] About to CONTINUE inner loop - will call runner again", "green")
                            # Continue inner loop to get another response
                            continue
                        
                        # In single_turn_mode with tool calls: continue inner loop to let agent keep working
                        if self.single_turn_mode:
                            # Stats update and termination check need to happen here
                            # Update LLM statistics - use raw_responses if available, else fallback to context_wrapper.usage
                            prev_output_tokens = self.usage.output_tokens
                            
                            if result.raw_responses:
                                for raw_response in result.raw_responses:
                                    self.usage.add(raw_response.usage)
                                    self.stats["agent_llm_requests"] += 1
                                    if raw_response.usage and hasattr(raw_response.usage, 'input_tokens'):
                                        self.stats["last_input_tokens"] = raw_response.usage.input_tokens
                            elif hasattr(result, 'context_wrapper') and hasattr(result.context_wrapper, 'usage'):
                                # Fallback: use context_wrapper.usage when raw_responses is empty
                                ctx_usage = result.context_wrapper.usage
                                if ctx_usage.input_tokens > 0 or ctx_usage.output_tokens > 0:
                                    # Calculate incremental usage since last update
                                    new_input = ctx_usage.input_tokens - self.usage.input_tokens
                                    new_output = ctx_usage.output_tokens - self.usage.output_tokens
                                    if new_input > 0 or new_output > 0:
                                        self.usage.input_tokens = ctx_usage.input_tokens
                                        self.usage.output_tokens = ctx_usage.output_tokens
                                        self.usage.requests = ctx_usage.requests
                                        self.stats["agent_llm_requests"] = ctx_usage.requests
                                        self.stats["last_input_tokens"] = new_input if new_input > 0 else ctx_usage.input_tokens
                            turn_output_tokens = self.usage.output_tokens - prev_output_tokens
                            self.stats["total_in_turn_steps"] += len(result.new_items)
                            
                            # ROBUST TRACKING: Update incremental tracker in single_turn_mode
                            self._update_incremental_tracker()
                            
                            # Update logs for next iteration
                            self.logs = self.build_new_logs(result.input, result.new_items)
                            
                            # Process tool calls and check for termination
                            recent_tool_calls = await self.process_agent_response(result)
                            
                            # Track skill creation cost
                            if self._current_turn_has_save_skill:
                                self.stats["skill_creation_output_tokens"] += turn_output_tokens
                                self._current_turn_has_save_skill = False
                            
                            # Check if claim_done was called via context flag
                            flag_value = self.shared_context.get('_claim_done_called', False)
                            print_color(f"[DEBUG] Checking _claim_done_called flag: {flag_value}, shared_context id: {id(self.shared_context)}", "cyan")
                            if flag_value:
                                print_color(f"[DEBUG] claim_done detected via context flag!", "green")
                                self.agent_called_claim_done = True
                                self.shared_context['_claim_done_called'] = False
                                break
                            
                            # Check via termination_checker as fallback
                            if self.termination_checker(result.final_output, recent_tool_calls, 'agent'):
                                print_color(f"[DEBUG] claim_done detected via termination_checker!", "green")
                                self.agent_called_claim_done = True
                                break
                            
                            # Continue inner loop
                            continue
                        
                        # Not single_turn_mode: break to get user input
                        print_color(f"[DEBUG] Breaking inner loop (not single_turn_mode)", "cyan")
                        break
                    except MaxTurnsExceeded as e:
                        self._debug_print(f"[THIS IS A TAG FOR MAX TURNS EXCEEDED] Max turns exceeded: {e}")
                        self.task_status = TaskStatus.MAX_TURNS_REACHED
                        break
                    except ContextTooLongError as e:
                        self._debug_print(f"Context too long detected: {e}")
                        
                        executed_steps = 0
                        if self.shared_context and "_force_reset_context" in self.shared_context:
                            reset_info = self.shared_context["_force_reset_context"]
                            executed_steps = reset_info.get("executed_turns", 1)
                        if executed_steps == 0:
                            executed_steps = 1
                        self.cumulative_inner_steps += executed_steps
                        self._debug_print(f"Context reset after {executed_steps} executed steps, total: {self.cumulative_inner_steps}/{max_inner_steps}")
                        
                        # Out of steps
                        if self.cumulative_inner_steps >= max_inner_steps:
                            self._debug_print("No more inner steps available for context reset")
                            raise RuntimeError(
                                f"Context too long and no remaining inner steps to handle reset. "
                                f"Used {self.cumulative_inner_steps}/{max_inner_steps} steps. "
                                f"Original error: {e}"
                            )
                        # Get original prompt
                        first_user_input = self._extract_first_user_input()

                        # Reset context & history
                        self._reset_context_and_history()
                        
                        # Get recent history summary from ContextManagedRunner
                        history_summary = ContextManagedRunner.get_recent_turns_summary(
                            self.history_dir, 
                            self.session_id, 
                            num_turns=10
                        )
                        
                        # Compose reset message (detect language)
                        is_chinese = hasattr(self.task_config, 'language') and self.task_config.language == 'zh'
                        if is_chinese:
                            reset_message = (
                                "[上下文已清空] 先前交互的上下文长度超过模型的可接受长度，已强制清空上下文。"
                                "以下是任务的原始需求和最近的交互历史概览。"
                                "请继续执行任务，必要时可使用历史记录搜索工具查看完整详情。"
                            )
                        else:
                            reset_message = (
                                "[Context reset] The context length of the previous interaction exceeds "
                                "the acceptable length of the model, and the context has been forcibly cleared. "
                                "Below are the original task requirements and a summary of recent interactions. "
                                "Please continue with the task, and use history search "
                                "tools if you need complete details."
                            )
                        
                        new_user_query = f"{reset_message}\n\n=== Original User Task ===\n{first_user_input}\n\n{history_summary}"
                        
                        # Start new conversation (after context reset)
                        self.logs = [{"role": "user", "content": new_user_query}]
                        
                        # Only reset *current sequence* attributes in context meta
                        self.shared_context["_context_meta"]["turns_in_current_sequence"] = 1
                        self.shared_context["_context_meta"]["mini_turns_in_current_sequence"] = 1
                        self.shared_context["_context_meta"]["boundary_in_current_sequence"] = [(0, 1)]
                        self.shared_context["_context_meta"]["total_turns_ever"] += 1
                        
                        current_reset_turn = self.shared_context["_context_meta"]["current_turn"]
                        ContextManagedRunner._save_user_input_to_history(
                            session_id=self.session_id,
                            user_input=new_user_query,
                            history_dir=self.history_dir,
                            turn_number=current_reset_turn
                        )
                        continue
                
                print_color(f"[DEBUG] Exited inner while loop. cumulative_inner_steps={self.cumulative_inner_steps}, max_inner_steps={max_inner_steps}", "cyan")
                
                # CRITICAL: If claim_done was already detected in inner loop, skip remaining processing and break outer loop
                # This prevents the issue where agent continues after claim_done in single_turn_mode
                if self.agent_called_claim_done:
                    print_color(f"[DEBUG] agent_called_claim_done=True, breaking outer loop immediately", "green")
                    break
                
                # CRITICAL: Also check the context flag directly in case it wasn't caught in inner loop
                if self.shared_context.get('_claim_done_called', False):
                    print_color(f"[DEBUG] _claim_done_called flag still set, setting agent_called_claim_done and breaking", "green")
                    self.agent_called_claim_done = True
                    self.shared_context['_claim_done_called'] = False
                    break
                
                # Ensure we got a result
                if result is None:
                    raise RuntimeError(f"Failed to get agent response within {max_inner_steps} inner steps")
                
                if self.cumulative_inner_steps >= max_inner_steps:
                    self._debug_print(f"Warning: Reached maximum inner steps limit ({max_inner_steps})")
                
                # Update LLM statistics
                # Save previous output_tokens to calculate this turn's increment
                prev_output_tokens = self.usage.output_tokens
                
                # Use raw_responses if available, else fallback to context_wrapper.usage
                if result.raw_responses:
                    for raw_response in result.raw_responses:
                        self.usage.add(raw_response.usage)
                        self.stats["agent_llm_requests"] += 1
                        # Track the last LLM request's input tokens
                        if raw_response.usage and hasattr(raw_response.usage, 'input_tokens'):
                            self.stats["last_input_tokens"] = raw_response.usage.input_tokens
                elif hasattr(result, 'context_wrapper') and hasattr(result.context_wrapper, 'usage'):
                    # Fallback: use context_wrapper.usage when raw_responses is empty
                    ctx_usage = result.context_wrapper.usage
                    if ctx_usage.input_tokens > 0 or ctx_usage.output_tokens > 0:
                        # Calculate incremental usage since last update
                        new_input = ctx_usage.input_tokens - self.usage.input_tokens
                        new_output = ctx_usage.output_tokens - self.usage.output_tokens
                        if new_input > 0 or new_output > 0:
                            self.usage.input_tokens = ctx_usage.input_tokens
                            self.usage.output_tokens = ctx_usage.output_tokens
                            self.usage.requests = ctx_usage.requests
                            self.stats["agent_llm_requests"] = ctx_usage.requests
                            self.stats["last_input_tokens"] = new_input if new_input > 0 else ctx_usage.input_tokens

                # Calculate this turn's output tokens as increment (not cumulative)
                turn_output_tokens = self.usage.output_tokens - prev_output_tokens

                self.logs = self.build_new_logs(result.input, result.new_items)
                
                # Count in-turn steps (number of items generated in this turn)
                self.stats["total_in_turn_steps"] += len(result.new_items)
                
                # ROBUST TRACKING: Update incremental tracker after main loop iteration
                self._update_incremental_tracker()
                
                # Store turn output tokens for later skill cost calculation
                self._current_turn_output_tokens = turn_output_tokens
                
                self.user_simulator.receive_message(result.final_output)
                
                # Process agent response to get any recent tool calls
                recent_tool_calls = await self.process_agent_response(result)
                
                # If this turn had save_skill, record the output tokens as skill creation cost
                if self._current_turn_has_save_skill:
                    self.stats["skill_creation_output_tokens"] += self._current_turn_output_tokens
                    self._current_turn_has_save_skill = False
                self._current_turn_output_tokens = 0
                
                # Check if claim_done was called via context flag (set by the tool itself)
                # This works even if the runner processed multiple turns internally
                if self.shared_context.get('_claim_done_called', False):
                    self._debug_print("Termination detected via context flag (claim_done was called)")
                    self.agent_called_claim_done = True
                    # Clear the flag
                    self.shared_context['_claim_done_called'] = False
                    break
                
                # Check for termination on assistant response (fallback check via tool calls)
                if self.termination_checker(result.final_output, recent_tool_calls, 'agent'):
                    self._debug_print("Termination condition met by agent response (claim_done called)")
                    self.agent_called_claim_done = True
                    break
                
                # Save checkpoints periodically
                if self.allow_resume and self.stats["interaction_turns"] % self.checkpoint_interval == 0:
                    await self._save_checkpoint()
                    
            except KeyboardInterrupt:
                # User interrupted
                self._debug_print("\nInterrupted by user")
                if self.allow_resume:
                    await self._save_checkpoint()
                    self.task_status = TaskStatus.INTERRUPTED
                raise
            except Exception as e:
                # Other errors
                self._debug_print(f"\nError during interaction: {e}")
                if self.allow_resume:
                    await self._save_checkpoint()
                raise
        
        # Check stopped due to max turn
        if self.stats["interaction_turns"] >= self.task_config.max_turns:
            self._debug_print(f"Maximum turns ({self.task_config.max_turns}) reached")
            self.task_status = TaskStatus.MAX_TURNS_REACHED

    def build_new_logs(self, input, generated_items):
        input_items = ItemHelpers.input_to_new_input_list(input)
        input_items.extend([generated_item.to_input_item() for generated_item in generated_items])
        return input_items

    def get_cost_summary(self) -> Tuple[Dict, Dict]:
        """Get cost statistics for user and agent."""
        # Add null check for self.user_simulator
        if self.user_simulator is None:
            user_cost = {"total_cost": 0, "total_input_tokens": 0, "total_output_tokens": 0, "total_requests": 0}
        else:
            user_cost = self.user_simulator.get_cost_summary()
        
        # ROBUST TRACKING: Final update to incremental tracker before collecting summary
        self._update_incremental_tracker()
        
        # ROBUST TRACKING: If main tracking failed (all zeros), try to recover from incremental tracker
        recovered_from_incremental = False
        if self.usage.input_tokens == 0 and self.usage.output_tokens == 0:
            if self._incremental_tracker is not None and self._incremental_tracker.has_data():
                tracker_data = self._incremental_tracker.get_summary()
                if tracker_data.get('input_tokens', 0) > 0 or tracker_data.get('output_tokens', 0) > 0:
                    self.usage.input_tokens = tracker_data.get('input_tokens', 0)
                    self.usage.output_tokens = tracker_data.get('output_tokens', 0)
                    self.usage.requests = tracker_data.get('requests', 0)
                    self.stats["agent_llm_requests"] = tracker_data.get('requests', 0)
                    self.stats["tool_calls"] = max(self.stats.get("tool_calls", 0), tracker_data.get('tool_calls', 0))
                    recovered_from_incremental = True
                    self._debug_print(f"[USAGE TRACKER] Recovered token stats from incremental tracker: input={self.usage.input_tokens}, output={self.usage.output_tokens}")
        
        # ROBUST TRACKING: If still no data, try to reconstruct from session history
        if self.usage.input_tokens == 0 and self.usage.output_tokens == 0:
            if self.history_dir and self.session_id:
                session_history_file = Path(self.history_dir) / f"{self.session_id}_session_history.jsonl"
                reconstructed = reconstruct_usage_from_session_history(session_history_file, self.agent_config.model.short_name)
                if reconstructed:
                    # Can only recover structural metrics, not token counts
                    self.usage.requests = reconstructed.get('requests', 0)
                    self.stats["agent_llm_requests"] = reconstructed.get('requests', 0)
                    self.stats["tool_calls"] = max(self.stats.get("tool_calls", 0), reconstructed.get('tool_calls', 0))
                    self._debug_print(f"[USAGE TRACKER] Partially reconstructed from session history: requests={self.usage.requests}, tool_calls={self.stats['tool_calls']}")
        
        _, _, total_cost = calculate_cost(
            self.agent_config.model.short_name,
            self.usage.input_tokens,
            self.usage.output_tokens
        )
        
        # Update token statistics
        self.stats["input_tokens"] = self.usage.input_tokens
        self.stats["output_tokens"] = self.usage.output_tokens
        self.stats["total_tokens"] = self.usage.input_tokens + self.usage.output_tokens
        
        # Calculate skill_creation_output_tokens using estimation based on save_skill calls
        # Each save_skill call typically involves generating a complex script, 
        # estimate ~500 output tokens per save_skill call on average
        # This is more accurate than the previous buggy approach that counted all output tokens
        ESTIMATED_TOKENS_PER_SAVE_SKILL = 500
        save_skill_count = self.stats.get("save_skill_call_count", 0)
        
        # Also calculate from session history for more accuracy if available
        if self.history_dir and self.session_id:
            try:
                # Count turns with save_skill from history
                history_path = Path(self.history_dir) / f"{self.session_id}_history.jsonl"
                if history_path.exists():
                    turns_with_save_skill = set()
                    total_turns = 0
                    with open(history_path, 'r', encoding='utf-8') as f:
                        for line in f:
                            try:
                                entry = json.loads(line)
                                turn = entry.get('turn', 0)
                                total_turns = max(total_turns, turn)
                                if entry.get('item_type') == 'tool_call_item':
                                    raw_content = entry.get('raw_content', {})
                                    name = raw_content.get('name', '')
                                    if 'save_skill' in name:
                                        turns_with_save_skill.add(turn)
                            except:
                                continue
                    
                    # Estimate skill creation cost based on proportion of turns
                    if total_turns > 0 and len(turns_with_save_skill) > 0:
                        # Skill creation turns typically have more output (the script itself)
                        # Use 2x the average as these turns generate scripts
                        avg_output_per_turn = self.usage.output_tokens / (total_turns + 1)
                        self.stats["skill_creation_output_tokens"] = int(
                            len(turns_with_save_skill) * avg_output_per_turn * 2
                        )
                    else:
                        self.stats["skill_creation_output_tokens"] = 0
            except Exception as e:
                # Fallback to simple estimation
                self.stats["skill_creation_output_tokens"] = save_skill_count * ESTIMATED_TOKENS_PER_SAVE_SKILL
        else:
            self.stats["skill_creation_output_tokens"] = save_skill_count * ESTIMATED_TOKENS_PER_SAVE_SKILL
        
        # Ensure skill_creation doesn't exceed total output
        self.stats["skill_creation_output_tokens"] = min(
            self.stats["skill_creation_output_tokens"],
            self.usage.output_tokens
        )
        
        # Calculate output_tokens_without_skill_creation_cost
        self.stats["output_tokens_without_skill_creation_cost"] = (
            self.usage.output_tokens - self.stats["skill_creation_output_tokens"]
        )
        
        # Try to get precise cost from model's OpenRouter usage.cost tracking
        cost_source = "estimated"
        tracking_source = "main_tracker"
        
        if hasattr(self, '_agent_model') and hasattr(self._agent_model, 'get_precise_cost'):
            precise_cost, source = self._agent_model.get_precise_cost()
            if source == "openrouter_api" and precise_cost > 0:
                total_cost = precise_cost
                cost_source = "openrouter_api"
        
        # ROBUST TRACKING: Also try to get cost from incremental tracker if model tracking failed
        if cost_source != "openrouter_api" and self._incremental_tracker is not None:
            tracker_data = self._incremental_tracker.get_summary()
            if tracker_data.get('cost_source') == 'openrouter_api' and tracker_data.get('openrouter_cost', 0) > 0:
                total_cost = tracker_data['openrouter_cost']
                cost_source = "openrouter_api"
                tracking_source = "incremental_tracker"
        
        # Mark tracking source if recovered
        if recovered_from_incremental:
            tracking_source = "recovered_from_incremental"
        
        agent_cost = {
            "total_cost": round(total_cost, 6),
            "total_input_tokens": self.usage.input_tokens,
            "total_output_tokens": self.usage.output_tokens,
            "total_requests": self.usage.requests,
            "cost_source": cost_source,
            "tracking_source": tracking_source,  # New field: where the data came from
        }
        
        return user_cost, agent_cost
    
    async def save_results(self) -> None:
        """Write results to log file."""
        res_log_file = self.task_config.log_file
        
        if not os.path.exists(os.path.dirname(res_log_file)):
            os.makedirs(os.path.dirname(res_log_file))
        
        # Ensure conversation_history directory exists even if no history was recorded
        # This ensures the directory structure is preserved even for failed tasks
        if self.history_dir:
            os.makedirs(self.history_dir, exist_ok=True)
        
        # Use ContextManagedRunner's formatted history
        if self.session_id and self.history_dir:
            complete_messages = ContextManagedRunner.get_formatted_history(
                self.history_dir,
                self.session_id
            )
            session_stats = ContextManagedRunner.get_session_stats(
                self.history_dir,
                self.session_id
            )
        else:
            # Fallback: just use logs_to_record
            complete_messages = self.logs_to_record
            session_stats = {}

        with open(res_log_file, "w", encoding='utf-8') as f:
            result = {
                'config': self.task_config.to_dict(),
                'request_id': str(uuid.uuid4()),
                'initial_run_time': getattr(self, 'initial_run_time', 'unknown'),
                'completion_time': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'tool_calls': {
                    'tools': self.all_tools,
                    'tool_choice': self.agent_config.tool.tool_choice,
                },
                "status": self.task_status.value,
                'messages': complete_messages,
                # Add conversation_history field for compatibility with eval_skill_mode.py
                # This should be the same as messages for evaluation scripts
                'conversation_history': complete_messages,
                'key_stats': {**self.stats, **session_stats},
                'agent_cost': self.agent_cost,
                'user_cost': self.user_cost,
                'resumed': self.allow_resume,
                'session_id': self.session_id,
                'history_file': str(Path(self.history_dir) / f"{self.session_id}_history.jsonl") if self.session_id else None
            }
            
            json_output = json.dumps(result, ensure_ascii=False, cls=CustomJSONEncoder)
            f.write(json_output)

    async def cleanup(self) -> None:
        """Release resources and disconnect MCP servers."""
        if self.mcp_manager:
            await self.mcp_manager.disconnect_servers()
    
    async def run(self) -> TaskStatus:
        """Run the whole task, including initialization, main loop, and saving results."""

        # Cache current working directory
        current_dir = os.path.abspath(os.getcwd())

        try:
            print_color("\n[DEBUG] Starting task execution...", "cyan")
            # Set log file and workspace dir
            self.task_config.log_file = os.path.join(self.task_config.task_root, "traj_log.json")
            self.task_config.agent_workspace = os.path.join(self.task_config.task_root, "workspace")
            print_color(f"[DEBUG] Log file: {self.task_config.log_file}", "cyan")
            print_color(f"[DEBUG] Workspace: {self.task_config.agent_workspace}", "cyan")

            # Preprocess status
            print_color("[DEBUG] Step 1/6: Updating preprocess status...", "cyan")
            self.status_manager.update_preprocess("running")

            # Initialize workspace (skip if checkpoint will be used)
            print_color("[DEBUG] Step 2/6: Initializing workspace...", "cyan")
            if not await self.initialize_workspace():
                print_color("[ERROR] Workspace initialization failed!", "red")
                self.status_manager.update_preprocess("fail")
                return TaskStatus.FAILED
            print_color("[DEBUG] Workspace initialized successfully", "green")

            # Sync static-skill skills AFTER workspace initialization
            if self.task_config.global_task_config:
                static_skill_skills = self.task_config.global_task_config.get('static_skill_skills')
                if static_skill_skills:
                    self._sync_static_skill_skills(static_skill_skills)

            self.status_manager.update_preprocess("done")

            # After preprocess, load task-specific local_token_key_session
            print_color("[DEBUG] Loading local token/key session...", "cyan")
            self.task_config.load_local_token_key_session()

            # Setup MCP servers
            print_color("[DEBUG] Step 3/6: Setting up MCP servers...", "cyan")
            await self.setup_mcp_servers(self.task_config.local_token_key_session)
            print_color("[DEBUG] MCP servers setup complete", "green")

            # Setup agent (LLM assistant)
            print_color("[DEBUG] Step 4/6: Setting up Agent (LLM)...", "cyan")
            await self.setup_agent()
            print_color(f"[DEBUG] Agent setup complete - Model: {self.agent_config.model.real_name}", "green")

            # Setup user simulator
            print_color("[DEBUG] Step 5/6: Setting up User simulator...", "cyan")
            await self.setup_user_simulator()
            print_color("[DEBUG] User simulator setup complete", "green")

            # Switch working dir to agent_workspace
            print_color(f"[DEBUG] Switching to workspace directory...", "cyan")
            os.chdir(self.task_config.agent_workspace)
            self._debug_print(f"Switched working directory to {self.task_config.agent_workspace}")

            # Enter running status
            self.status_manager.update_running("running")

            # Main interaction loop
            print_color("[DEBUG] Step 6/6: Starting main interaction loop...", "cyan")
            await self.run_interaction_loop(os.path.abspath(self.task_config.task_root))

            # Switch back to the original cwd
            os.chdir(current_dir)
            self._debug_print(f"Switched back working directory to {current_dir}")
            
            # Check if token limit was exceeded
            if self._token_limit_exceeded:
                self.task_status = TaskStatus.TOKEN_LIMIT_EXCEEDED
                self.status_manager.update_running("token_limit_exceeded")
                self._debug_print(f"Task terminated: {self._token_limit_reason}")
            # Only mark SUCCESS if agent explicitly called claim_done
            elif self.task_status not in [TaskStatus.MAX_TURNS_REACHED, TaskStatus.INTERRUPTED]:
                if self.agent_called_claim_done:
                    self.task_status = TaskStatus.SUCCESS
                    self.status_manager.update_running("done")
                    self._debug_print("Task completed: agent called claim_done")
                else:
                    # Agent stopped without calling claim_done (e.g., sent pure text message)
                    self.task_status = TaskStatus.INCOMPLETE
                    self.status_manager.update_running("incomplete")
                    self._debug_print("Task incomplete: agent stopped without calling claim_done")
            elif self.task_status == TaskStatus.MAX_TURNS_REACHED:
                self.status_manager.update_running("max_turn_exceeded")
            
            # Remove checkpoint after successful completion
            if self.task_status == TaskStatus.SUCCESS:
                self._remove_checkpoint()
                
        except KeyboardInterrupt:
            print_color("[DEBUG] Task interrupted by user (KeyboardInterrupt)", "red")
            self._debug_print("Task interrupted by user")
            if self.task_status != TaskStatus.INTERRUPTED:
                self.task_status = TaskStatus.INTERRUPTED

        except Exception as e:
            # max-turn logic updates the status in the interaction loop
            # but RuntimeError("Failed to get agent response...") brings us here,
            # so update status here as well
            print_color(f"\n[ERROR] Exception caught during task execution!", "red")
            print_color(f"[ERROR] Exception type: {type(e).__name__}", "red")
            print_color(f"[ERROR] Exception message: {str(e)}", "red")
            self._debug_print("Error when running agent -", e)
            if self.debug:
                traceback.print_exc()
            else:
                # Always print traceback for critical errors
                print_color("[ERROR] Full traceback:", "red")
                traceback.print_exc()
            if self.task_status == TaskStatus.MAX_TURNS_REACHED:
                self.status_manager.update_running("max_turn_exceeded")
            elif self._token_limit_exceeded:
                self.task_status = TaskStatus.TOKEN_LIMIT_EXCEEDED
                self.status_manager.update_running("token_limit_exceeded")
            else:
                self.task_status = TaskStatus.FAILED
                self.status_manager.update_running("fail")
            
        finally:
            # Always restore working dir
            os.chdir(current_dir)
            self._debug_print(f"Switched back working directory to {current_dir}")

            # Gather final cost summary (updates token stats)
            user_cost, agent_cost = self.get_cost_summary()
            self.user_cost = user_cost
            self.agent_cost = agent_cost

            # Print cost/statistics summary (in English)
            self._debug_print(f"=== LLM-simulator ({self.user_config.model.short_name}) Cost Summary ===")
            for k, v in user_cost.items():
                self._debug_print(f"{k} : {v}")
            self._debug_print(f"=== Agent ({self.agent_config.model.short_name}) Cost Summary ===")
            for k, v in agent_cost.items():
                self._debug_print(f"{k} : {v}")
            self._debug_print("=== Key Statistics ===")
            for k, v in self.stats.items():
                self._debug_print(f"{k} : {v}")
            
            # Save final results to file
            await self.save_results()
            # Cleanup/close resources
            await self.cleanup()
            
        return self.task_status
