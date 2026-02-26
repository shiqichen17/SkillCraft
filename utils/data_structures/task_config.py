from dataclasses import dataclass, field
import importlib.util
from typing import List, Dict, Optional, Union
from pathlib import Path
from datetime import datetime

from utils.general.helper import path_to_module, read_json
import os

@dataclass
class SystemPrompts:
    """System prompt messages."""
    agent: Union[str, Dict]
    user: Union[str, Dict]
    
    @classmethod
    def build(cls, task_dir: str, cn_mode: bool=False):
        if cn_mode:
            agent_sp_path = Path("tasks") / task_dir / "docs" / "agent_system_prompt_cn.md"
            user_sp_path = Path("tasks") / task_dir / "docs" / "user_system_prompt_cn.md"
        else:
            agent_sp_path = Path("tasks") / task_dir / "docs" / "agent_system_prompt.md"
            user_sp_path = Path("tasks") / task_dir / "docs" / "user_system_prompt.md"
        if agent_sp_path.exists():
            with open(agent_sp_path, 'r', encoding='utf-8') as f:
                agent_sp = f.read()
        else:
            agent_sp = None
        if user_sp_path.exists():
            with open(user_sp_path, 'r', encoding='utf-8') as f:
                user_sp = f.read()
        else:
            user_sp = None
        return cls(agent=agent_sp, user=user_sp)

    def apply(self, agent_workspace: str,
              task_str: str,
              time: str,
              single_turn_mode: bool=False,
              cn_mode: bool=False,
              enable_skill_cache: bool=False,
              cross_task_skills_summary: str=None,
              cross_task_mode: bool=False,
              allow_skill_nesting: bool=False,
              enable_direct_exec: bool=False,
              static_skill_mode: bool=False):

        # Initialize agent prompt if None
        if self.agent is None:
            self.agent = ""

        # Apply variable replacements
        self.agent = self.agent.replace("!!<<<<||||current_working_dir||||>>>>!!", os.getcwd())
        self.agent = self.agent.replace("!!<<<<||||workspace_dir||||>>>>!!", os.path.abspath(agent_workspace))
        self.agent = self.agent.replace("!!<<<<||||workspace_dir_rela||||>>>>!!", os.path.relpath(agent_workspace))
        self.agent = self.agent.replace("!!<<<<||||time||||>>>>!!", time)

        if single_turn_mode:
            if not cn_mode:
                self.agent += "\nPlease complete the given task independently. Do not seek confirmation or additional feedback from the user. You should handle all situations on your own, as the user will not provide any further information."
            else:
                self.agent += "\nPlease complete the given task independently. Do not seek confirmation or additional feedback from the user. You should handle all situations on your own, as the user will not provide any further information."

        # Add skill cache guidance if enabled
        if enable_skill_cache:
            # Check if cross-task mode - use explicit flag, not just skill summary presence
            # This ensures cross-task features are enabled even for the first task (e1) which has no inherited skills
            is_cross_task = cross_task_mode
            
            # Check if static-skill mode (read-only skills, no save_skill)
            is_static_skill = static_skill_mode
            
            # Check if skill nesting is allowed (cross-task mode OR iteration mode)
            # iteration mode: allow_skill_nesting=True but cross_task_mode=False
            can_nest_skills = allow_skill_nesting or is_cross_task or is_static_skill
            
            # Base prompt - tools available (differs by mode)
            if is_static_skill:
                # Static-skill mode: NO save_skill, only execute/browse existing skills
                tools_section = """
## Skill Execution Mode (Static Reuse)

You have access to pre-loaded skills that were created by previous tasks. You can browse and execute these skills, but **cannot create new skills**.

Available tools:
- `local-execute_skill`: Execute a loaded skill with different arguments
- `local-list_skills`: List all available skills (use if you need execution history or updated status)
- `local-get_skill`: View a skill's full script code (use if you need to see implementation details)

**Important:** This is a static-skill mode. The skills listed below are pre-loaded and ready to use. Use them to complete your task efficiently.

**How to use skills:**
1. Review available skills with `local-list_skills` or check the list below
2. Use `local-get_skill` to view a skill's implementation if needed
3. Execute skills with `local-execute_skill({"skill_name": "...", "args": {...}})`
"""
            elif is_cross_task:
                tools_section = """
## Tool Reuse and Composition Optimization (Cross-Task Mode)

You have access to skill cache tools to save, browse, and execute reusable scripts:
- `local-save_skill`: Save an executable script as a reusable skill
- `local-execute_skill`: Execute a saved skill with different arguments
- `local-list_skills`: List all available skills (use if you need execution history or updated status)
- `local-get_skill`: View a skill's full script code (use if you need to see implementation details)

**Cross-Task Mode Active:** Skills from previous tasks are listed below (if any). You can use them directly with `local-execute_skill`.

**When to use:** For repetitive operations (processing multiple items, files, etc.), create a skill to encapsulate the workflow, then execute it for all items. You can create skills based on tool schemas without calling the tool first - especially efficient when tools return large data.

**Optional Schema (recommended for cross-task):** When saving skills, you can include `input_schema` and `output_schema` to help future tasks understand how to use them:
```
local-save_skill({
  "skill_name": "analyze_project",
  "parameters": ["project_path"],
  "input_schema": "{\\"project_path\\": \\"str\\"}",
  "output_schema": "{\\"name\\": \\"str\\", \\"stats\\": {\\"stars\\": \\"int\\", \\"forks\\": \\"int\\"}}",
  "script_code": "...",
  "description": "..."
})
```
"""
            else:
                tools_section = """
## Tool Reuse and Composition Optimization

You have access to skill cache tools to save and execute reusable scripts:
- `local-save_skill`: Save an executable script as a reusable skill
- `local-execute_skill`: Execute a saved skill with different arguments

**When to use:** For repetitive operations (processing multiple items, files, etc.), create a skill to encapsulate the workflow, then execute it for all items. You can create skills based on tool schemas without calling the tool first - especially efficient when tools return large data.
"""
            
            # Rules section differs based on mode:
            # - static-skill: execute only, no skill creation
            # - cross-task: full skill nesting with inherited skills
            # - iteration (can_nest_skills but not cross_task): skill nesting without inheritance
            # - skill mode (neither): no skill nesting
            if is_static_skill:
                # Static-skill mode: only execute existing skills, NO save_skill
                rules_section = """
### Skill Execution Rules

You can execute the pre-loaded skills listed below. **Do NOT attempt to create new skills** - you only have access to `execute_skill`, `list_skills`, and `get_skill`.

**CRITICAL: execute_skill Return Format**
```python
response = call_tool('local-execute_skill', skill_name='...', args={...})
# response is: {"status": "success", "result": <actual_data>}
# ALWAYS access via response['result'] or response.get('result', {})
data = response['result']  # <-- The actual data is here!
```

**Workflow:**
1. Review the available skills listed below
2. Call `local-execute_skill` with appropriate arguments for each item you need to process
3. Aggregate results and save to output file
4. Call `claim_done` to complete the task

**Fallback Strategy:**
- If a skill fails, you can call the underlying tools directly
- Use `local-get_skill` to see the skill's implementation for debugging
"""
            elif is_cross_task:
                # Cross-task mode: allow skill nesting and encourage composition with inherited skills
                rules_section = """
### Skill Script Rules

1. **Use `call_tool()` for ALL tool calls**: `call_tool('server-tool_name', arg1=val1, ...)`
   - call_tool('pdf-tools-read_pdf_pages', file_path=path)
2. **`call_tool()` returns DIRECT result** - use it directly without `.get("result")` wrapper
3. **MUST set `result` variable** - this is what gets returned from execute_skill
4. **Modules available**: re, json, os are pre-imported; import others inside script

### Skill Composition (Cross-Task Feature)

In cross-task mode, you can **call existing skills from within new skills** using `call_tool('local-execute_skill', ...)`. This enables powerful skill composition!

**CRITICAL: execute_skill Return Format**
```python
response = call_tool('local-execute_skill', skill_name='...', args={...})
# response is: {"status": "success", "result": <actual_data>}
# ALWAYS access via response['result'] or response.get('result', {})
data = response['result']  # <-- The actual data is here!
```

**Example: Building on inherited skills**

If a previous task created `get_pokemon_details` skill, you can create a more complex skill that reuses it:

```python
local-save_skill({
  "skill_name": "compare_two_pokemon",
  "script_code": \"\"\"
# Reuse existing skill for each Pokemon
pokemon1 = call_tool('local-execute_skill', skill_name='get_pokemon_details', args={'pokemon_id': pokemon_id_1})
pokemon2 = call_tool('local-execute_skill', skill_name='get_pokemon_details', args={'pokemon_id': pokemon_id_2})

# IMPORTANT: Extract actual results from 'result' key!
p1_data = pokemon1.get('result', {})
p2_data = pokemon2.get('result', {})

# Compare and return
result = {
    'pokemon1': p1_data.get('name'),
    'pokemon2': p2_data.get('name'),
    'stat_difference': p1_data.get('stat_total', 0) - p2_data.get('stat_total', 0),
    'winner': p1_data.get('name') if p1_data.get('stat_total', 0) > p2_data.get('stat_total', 0) else p2_data.get('name')
}
\"\"\",
  "parameters": ["pokemon_id_1", "pokemon_id_2"],
  "description": "Compare two Pokemon using inherited get_pokemon_details skill"
})
```

**When to compose skills:**
- When an existing skill does 70%+ of what you need
- When you need to combine results from multiple existing skills
- When building more complex workflows on top of simpler ones

### Best Practices

**Token Efficiency:**
- Extract only fields needed for final output - don't return raw tool responses
- Reuse existing skills instead of recreating similar logic

**Skill Mode Priority:**
1. If a matching skill exists in the list below, use it directly with `local-execute_skill`
2. If you need slight modifications, create a new skill that calls the existing one
3. Only create from scratch if no suitable skill exists

**Fallback Strategy:**
- If skill fails 2-3 times, stop and process items directly
"""
            elif can_nest_skills:
                # Iteration mode: allow skill nesting within this task (no inherited skills)
                rules_section = """
### Skill Script Rules

1. **Use `call_tool()` for ALL tool calls**: `call_tool('server-tool_name', arg1=val1, ...)`
   - call_tool('pdf-tools-read_pdf_pages', file_path=path)
2. **`call_tool()` returns DIRECT result** - use it directly without `.get("result")` wrapper
3. **MUST set `result` variable** - this is what gets returned from execute_skill
4. **Modules available**: re, json, os are pre-imported; import others inside script

### Skill Composition (Iteration Mode)

In iteration mode, you can **call skills from within other skills** using `call_tool('local-execute_skill', ...)`. This enables building complex workflows from simpler skills!

**CRITICAL: execute_skill Return Format**
```python
response = call_tool('local-execute_skill', skill_name='...', args={...})
# response is: {"status": "success", "result": <actual_data>}
# ALWAYS access via response['result'] or response.get('result', {})
data = response['result']  # <-- The actual data is here!
```

**Example: Creating a nested skill**

First create a simple skill:
```python
local-save_skill({
  "skill_name": "get_item_details",
  "script_code": \"\"\"
info = call_tool('local-api_get_info', item_id=item_id)
result = {'id': item_id, 'name': info.get('name'), 'data': info.get('data')}
\"\"\",
  "parameters": ["item_id"],
  "description": "Get details for a single item"
})
```

Then create a skill that calls it:
```python
local-save_skill({
  "skill_name": "compare_items",
  "script_code": \"\"\"
# Call the simpler skill for each item
item1 = call_tool('local-execute_skill', skill_name='get_item_details', args={'item_id': id1})
item2 = call_tool('local-execute_skill', skill_name='get_item_details', args={'item_id': id2})

# Extract results and compare
d1 = item1.get('result', {})
d2 = item2.get('result', {})

result = {
    'item1': d1,
    'item2': d2,
    'comparison': d1.get('data', 0) - d2.get('data', 0)
}
\"\"\",
  "parameters": ["id1", "id2"],
  "description": "Compare two items using nested skill calls"
})
```

**When to use nested skills:**
- When you can break a complex task into reusable sub-skills
- When the same sub-operation is needed in multiple skills
- To build hierarchical workflows (high-level skills calling low-level ones)

**Fallback Strategy:**
- If skill fails 2-3 times, stop and process items directly
"""
            else:
                # Skill mode: no skill nesting allowed
                rules_section = """
### Skill Script Rules

1. **Use `call_tool()` for ALL tool calls**: `call_tool('server-tool_name', arg1=val1, ...)`
   - call_tool('pdf-tools-read_pdf_pages', file_path=path)
2. **`call_tool()` returns DIRECT result** - use it directly without `.get("result")` wrapper
3. **MUST set `result` variable** - this is what gets returned from execute_skill
4. **Modules available**: re, json, os are pre-imported; import others inside script
5. **No recursion**: Cannot call skill tools within skills

### Example: Multi-Tool Skill

Task: Analyze GitLab projects for 10 repos

**Step 1**: Create skill based on tool schemas
```python
local-save_skill({
  "skill_name": "analyze_gitlab_project",
  "script_code": "# Get project data
project_info = call_tool('local-gitlab_get_project_info', project_path=project_path)
project = project_info.get('project', {})

# Get contributors
contributors_data = call_tool('local-gitlab_get_contributors', project_path=project_path)
contributors = contributors_data.get('contributors', [])[:5]

# Calculate activity score
score = len(contributors) * 10 + project.get('stars', 0)

# MUST set result variable!
result = {
    'path': project_path,
    'name': project.get('name'),
    'stars': project.get('stars', 0),
    'top_contributors': [c.get('name') for c in contributors],
    'activity_score': score
}",
  "parameters": ["project_path"],
  "description": "Analyze GitLab project with contributors and score"
})
```
**Step 2+**: Execute for all items
```python
local-execute_skill({"skill_name": "analyze_gitlab_project", "args": {"project_path": "org/repo1"}})
```

### Best Practices

**Token Efficiency:**
- Extract only fields needed for final output - don't return raw tool responses
- Skill should be a "data transformer": fetch detailed data, return only essentials

**Maximize ROI:**
- Create skill early, execute for ALL items (beneficial when N >= 3-5 items)

**Fallback Strategy:**
- If skill fails 2-3 times, stop and process items directly
"""
            # Combine tools section and rules section
            skill_cache_prompt = tools_section + rules_section
            self.agent += skill_cache_prompt
            
            # Add cross-task skills summary if available (for cross-task mode)
            if cross_task_skills_summary:
                self.agent += cross_task_skills_summary

        # Add direct exec guidance if enabled (mutually exclusive with skill_cache)
        if enable_direct_exec and not enable_skill_cache:
            direct_exec_prompt = """
## Direct Script Execution Mode

You have access to a direct script execution tool:
- `local-exec_script`: Execute a Python script directly and get the result

**When to use:** For repetitive operations or batch processing, write a complete Python script that handles everything in one execution. This is more efficient than making individual tool calls.

### Script Rules

1. **Use `call_tool()` for ALL tool calls**: `call_tool('server-tool_name', arg1=val1, ...)`
   - Example: `call_tool('local-gitlab_get_project_info', project_path='org/repo')`
2. **`call_tool()` returns DIRECT result** - use it directly without JSON parsing
3. **MUST set `result` variable** - this is what gets returned from exec_script
4. **Modules available**: `re`, `json`, `os` are pre-imported; import others inside script
5. **Parameters are HARDCODED** - embed all values directly in the script code

### Example: Process Multiple Items

**Task:** Analyze 3 GitLab projects and collect their info

```python
local-exec_script({
  "script_code": \"\"\"
# Hardcode the projects to analyze
projects = [
    'gitlab-org/gitlab-runner',
    'gitlab-org/gitaly', 
    'gitlab-org/gitlab-pages'
]

results = []
for project_path in projects:
    # Fetch project info
    info = call_tool('local-gitlab_get_project_info', project_path=project_path)
    
    # Fetch contributors
    contributors = call_tool('local-gitlab_get_contributors', project_path=project_path)
    
    # Extract relevant data (info is already a dict)
    project_data = {
        'path': project_path,
        'name': info.get('project', {}).get('name', 'Unknown'),
        'stars': info.get('project', {}).get('star_count', 0),
        'top_contributors': [c.get('name') for c in contributors.get('contributors', [])[:3]]
    }
    results.append(project_data)

# MUST set result variable!
result = {
    'total_projects': len(results),
    'projects': results
}
\"\"\"
})
```

### Best Practices

**Token Efficiency:**
- Process ALL items in a single exec_script call
- Extract only fields needed for final output
- Avoid returning raw tool responses

**Error Handling:**
- Use `.get()` with defaults for missing keys
- Wrap risky operations in try/except if needed

**When to use exec_script:**
- Processing 3+ similar items
- Complex data transformations
- When you want to minimize context token usage
"""
            self.agent += direct_exec_prompt

        # Add workspace directory clarification (always added for single turn tasks)
        if single_turn_mode:
            workspace_clarification = """

## 📁 Workspace Directory Information

**Your current working directory IS your workspace.** All file operations should be performed directly in this directory.

### Important:
- **DO NOT create a nested `workspace/` directory** - you are ALREADY in the workspace
- Save files directly to the current directory, e.g., `results.json` not `workspace/results.json`
- Use `filesystem-list_directory` with path `"."` to see what's in your current workspace
- When the task says "save to workspace", it means save to the current directory

"""
            self.agent += workspace_clarification

        # Add mandatory save-before-done reminder (always added for single turn tasks)
        if single_turn_mode:
            save_before_done_prompt = """

## ⚠️ CRITICAL: Save Results BEFORE Completion

**You MUST save all results to the required output file(s) BEFORE calling `claim_done`.**

### Mandatory Workflow:
1. **Complete all data collection/processing** - gather all required information
2. **Save results to file** - use `filesystem-write_file` to save the complete JSON/data
3. **Verify the file was saved** - optionally read back or check the file exists
4. **THEN call `claim_done`** - only after successful save

### Common Mistake to AVOID:
```
❌ WRONG: Process data → call claim_done (forgot to save!)
✅ CORRECT: Process data → write_file(results.json) → claim_done
```

### Checklist Before Calling claim_done:
- [ ] Have I saved ALL results to the required output file?
- [ ] Is the output file in the correct location (workspace directory)?
- [ ] Does the file contain all processed items, not just partial data?
- [ ] Is the JSON/data format correct and complete?

**If you call `claim_done` without saving results, the task will FAIL evaluation.**

### ⛔ IMPORTANT: claim_done is FINAL
- `claim_done` MUST be your **last action** - the interaction ends immediately after it
- Do NOT call any tools, send messages, or perform any operations after `claim_done`
- Do NOT call `claim_done` in parallel with other tools - always call it alone as the final step
"""
            self.agent += save_before_done_prompt

        # Initialize user prompt if None and apply replacements
        if self.user is None:
            self.user = ""

        if self.user:  # Only process if not empty
            self.user = self.user.replace("!!<<<<||||task_description||||>>>>!!", task_str)

        return self

@dataclass
class Initialization:
    """Initialization configuration."""
    workspace: str
    process_command: str

    @classmethod
    def build(cls, task_dir: str, cn_mode: bool=False):
        workspace_path = Path("tasks") / task_dir / "initial_workspace"
        process_command_path = Path("tasks") / task_dir / "preprocess" / "main.py"

        # If cn_mode and these paths exist, overwrite them
        if cn_mode:
            if (Path("tasks") / task_dir / "initial_workspace_cn").exists():
                workspace_path = Path("tasks") / task_dir / "initial_workspace_cn"
            if (Path("tasks") / task_dir / "preprocess" / "main_cn.py").exists():
                process_command_path = Path("tasks") / task_dir / "preprocess" / "main_cn.py"

        if process_command_path.exists():
            process_command = f"uv run -m {path_to_module(process_command_path)}"
        else:
            process_command = None
        if workspace_path.exists():
            workspace = str(workspace_path)
        else:
            workspace = None
        return cls(workspace=workspace, process_command=process_command)

@dataclass
class Evaluation:
    """Evaluation configuration."""
    groundtruth_workspace: str
    evaluation_command: str

    @classmethod
    def build(cls, task_dir: str, cn_mode: bool=False):
        groundtruth_workspace_path = Path("tasks") / task_dir / "groundtruth_workspace"
        evaluation_command_path = Path("tasks") / task_dir / "evaluation" / "main.py"

        # If cn_mode and these paths exist, overwrite them
        if cn_mode:
            if (Path("tasks") / task_dir / "groundtruth_workspace_cn").exists():
                groundtruth_workspace_path = Path("tasks") / task_dir / "groundtruth_workspace_cn"
            if (Path("tasks") / task_dir / "evaluation" / "main_cn.py").exists():
                evaluation_command_path = Path("tasks") / task_dir / "evaluation" / "main_cn.py"

        if evaluation_command_path.exists():
            evaluation_command = f"uv run -m {path_to_module(evaluation_command_path)}"
        else:
            evaluation_command = None
        if groundtruth_workspace_path.exists():
            groundtruth_workspace = str(groundtruth_workspace_path)
        else:
            groundtruth_workspace = None
        return cls(groundtruth_workspace=groundtruth_workspace, evaluation_command=evaluation_command)

@dataclass
class StopConditions:
    """Stop conditions configuration."""
    user_phrases: List[str] = None
    tool_names: List[str] = None

    @classmethod
    def build(cls, stop_conditions: Dict):
        if stop_conditions is None:
            stop_conditions = {}
        if "user_phrases" in stop_conditions:
            user_phrases = stop_conditions["user_phrases"]
        else:
            user_phrases = ["#### STOP"]
        if "tool_names" in stop_conditions:
            tool_names = stop_conditions["tool_names"]
        else:
            tool_names = ['local-claim_done']
        return cls(user_phrases=user_phrases, tool_names=tool_names)

@dataclass
class TaskConfig:
    """Task configuration."""
    # Basic information
    task_dir: str  # Relative path under tasks/
    id: str = None
    needed_mcp_servers: List[str] = None
    needed_local_tools: List[str] = None
    task_root: str = None
    task_str: str = None
    system_prompts: SystemPrompts = None
    initialization: Initialization = None
    evaluation: Evaluation = None
    stop: StopConditions = None
    log_file: Optional[str] = None
    agent_workspace: Optional[str] = None
    max_turns: int = None
    max_steps_under_single_turn_mode: int = None
    single_turn_mode: bool = False
    cn_mode: bool = False
    meta: Dict = field(default_factory=dict)
    launch_time: str = None
    # Token limits to prevent context explosion
    max_input_tokens: int = None  # Maximum cumulative input tokens before force termination
    max_output_tokens: int = None  # Maximum cumulative output tokens before force termination
    max_single_request_input_tokens: int = None  # Maximum input tokens for a single API request

    agent_short_name: str = None
    global_task_config: Dict = None
    raw_config: Dict = field(default_factory=dict)  # Raw task_config.json content

    local_token_key_session: Dict = None

    def __post_init__(self):
        """Automatically set default values after initialization."""
        assert self.task_dir is not None, "task_dir is required"
        # Allow both 2-level (group/task) and 3-level (group/task/variant) paths for scaled tasks
        assert len(Path(self.task_dir).parts) >= 2, "task_dir must be a relative path under tasks/ with at least 2 parts (e.g., 'group/task_name' or 'group/task_name/variant')"

        if self.task_root is None:
            self.task_root = self.task_dir
        
        if self.id is None:
            self.id = '-'.join(Path(self.task_dir).parts)

        prefix = ''
        if self.cn_mode:
            prefix = 'Chinese-'
        if self.single_turn_mode:
            prefix += 'SingleUserTurn-'

        # Add SingleUserTurn- or Chinese- prefixes to the last level of task_root, e.g., xx/yy becomes xx/SingleUserTurn-yy
        task_root_parts = Path(self.task_root).parts
        if len(task_root_parts) >= 1:
            last_part = task_root_parts[-1]
            new_last_part = f"{prefix}{last_part}"
            new_parts = list(task_root_parts[:-1]) + [new_last_part]
            self.task_root = str(Path(*new_parts))

        task_root_path = Path(self.task_root)
        self.task_root = str(task_root_path)

        if self.task_str is None:
            if self.cn_mode:
                task_str_path = Path("tasks") / self.task_dir / "docs" / "task_cn.md"
            else:
                task_str_path = Path("tasks") / self.task_dir / "docs" / "task.md"
            with open(task_str_path, 'r', encoding='utf-8') as f:
                self.task_str = f.read()

        # Update dump_path from global_task_config to task_root_path for isolation on repeated runs
        if self.global_task_config is not None and "dump_path" in self.global_task_config:
            global_dump_path = self.global_task_config['dump_path']
            if global_dump_path.endswith(self.agent_short_name.replace('/', '_')) or global_dump_path.endswith(self.agent_short_name.replace('/', '_') + '/'):
                pass
            else:
                global_dump_path = Path(global_dump_path) / Path(self.agent_short_name.replace('/', '_'))
            self.task_root = str(global_dump_path / task_root_path)
            task_root_path = Path(self.task_root)

        if (
            self.global_task_config is not None
            and self.global_task_config.get('direct_to_dumps', False)
            and "dump_path" in self.global_task_config
        ):
            self.task_root = self.global_task_config['dump_path']
            task_root_path = Path(self.task_root)

        # Ensure absolute path for task_root
        self.task_root = os.path.abspath(self.task_root)

        # Automatically generate log_file if not specified
        if self.log_file is None:
            self.log_file = str(task_root_path / "traj_log.json")
        self.log_file = os.path.abspath(self.log_file)

        # Automatically generate agent_workspace if not specified
        if self.agent_workspace is None:
            self.agent_workspace = str(task_root_path / "workspace")
        self.agent_workspace = os.path.abspath(self.agent_workspace)

        # Not sure if this will contradict with the legacy resume mechanism
        eval_res_filepath = str(task_root_path / "eval_res.json")
        if os.path.exists(eval_res_filepath):
            os.remove(eval_res_filepath)

        if self.global_task_config is not None and "max_turns" in self.global_task_config:
            self.max_turns = self.global_task_config['max_turns']

        if self.global_task_config is not None and "max_steps_under_single_turn_mode" in self.global_task_config:
            self.max_steps_under_single_turn_mode = self.global_task_config['max_steps_under_single_turn_mode']

        # Read token limits from global_task_config
        if self.global_task_config is not None and "max_input_tokens" in self.global_task_config:
            self.max_input_tokens = self.global_task_config['max_input_tokens']
        
        if self.global_task_config is not None and "max_output_tokens" in self.global_task_config:
            self.max_output_tokens = self.global_task_config['max_output_tokens']
        
        # Read single request token limit
        if self.global_task_config is not None and "max_single_request_input_tokens" in self.global_task_config:
            self.max_single_request_input_tokens = self.global_task_config['max_single_request_input_tokens']

        # Check if skill cache is enabled
        enable_skill_cache = self.global_task_config.get('enable_skill_cache', False) if self.global_task_config else False
        
        # Get cross-task skills summary if available (for cross-task mode)
        cross_task_skills_summary = self.global_task_config.get('cross_task_skills_summary') if self.global_task_config else None
        
        # Get cross-task mode flag (explicit flag, not derived from skill summary)
        cross_task_mode = self.global_task_config.get('cross_task_mode', False) if self.global_task_config else False
        
        # Get allow_skill_nesting flag (for iteration mode)
        allow_skill_nesting = self.global_task_config.get('allow_skill_nesting', False) if self.global_task_config else False
        
        # Check if direct exec mode is enabled (mutually exclusive with skill_cache)
        enable_direct_exec = self.global_task_config.get('enable_direct_exec', False) if self.global_task_config else False
        
        # Check if static-skill mode is enabled (execute only, no save_skill)
        static_skill_mode = self.global_task_config.get('static_skill_mode', False) if self.global_task_config else False
        
        self.system_prompts.apply(
            self.agent_workspace,
            self.task_str,
            self.launch_time,
            self.single_turn_mode,
            self.cn_mode,
            enable_skill_cache,
            cross_task_skills_summary,
            cross_task_mode,
            allow_skill_nesting,
            enable_direct_exec,
            static_skill_mode
        )

        # if self.local_token_key_session is None:
        #     # Dynamically load the module if necessary

    def load_local_token_key_session(self) -> None:
        token_key_session_path = str(Path("tasks") / self.task_dir / "token_key_session.py")

        if Path(token_key_session_path).exists():
            spec = importlib.util.spec_from_file_location("token_key_session", token_key_session_path)
            token_key_session_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(token_key_session_module)
            # Get all_token_key_session variable
            self.local_token_key_session = token_key_session_module.all_token_key_session

    # Use Path object property accessors
    @property
    def task_root_path(self) -> Path:
        """Return Path object of task root directory."""
        return Path(self.task_root)
    
    @property
    def log_file_path(self) -> Path:
        """Return Path object of log file."""
        return Path(self.log_file)
    
    @property
    def agent_workspace_path(self) -> Path:
        """Return Path object of agent workspace directory."""
        return Path(self.agent_workspace)
    
    @classmethod
    def from_dict(cls, task_config_dict: dict) -> 'TaskConfig':
        # Reconstruct from a dict produced by to_dict
        # Note evaluation, system_prompts, initialization, stop are None and need to be constructed
        task_config_dict['evaluation'] = Evaluation(**task_config_dict['evaluation'])
        task_config_dict['system_prompts'] = SystemPrompts(**task_config_dict['system_prompts'])
        task_config_dict['initialization'] = Initialization(**task_config_dict['initialization'])
        task_config_dict['stop'] = StopConditions(**task_config_dict['stop'])
        return cls(**task_config_dict)

    @classmethod
    def build(
        cls,
        task_dir: str,
        agent_short_name: str = None,
        global_task_config: dict = None,
        single_turn_mode: bool = False,
        cn_mode: bool = False
    ) -> 'TaskConfig':
        """Build TaskConfig instance from a dictionary."""
        task_config_dict = read_json(Path("tasks") / task_dir / "task_config.json")
        return cls(
            task_dir=task_dir,
            needed_mcp_servers=task_config_dict['needed_mcp_servers'],
            needed_local_tools=task_config_dict['needed_local_tools'],
            max_turns=task_config_dict.get("max_turns"),
            meta=task_config_dict.get('meta', {}),
            agent_short_name=agent_short_name,
            global_task_config=global_task_config,
            raw_config=task_config_dict,  # Store raw config for timeout and other settings
            stop=StopConditions.build(task_config_dict.get('stop')),
            system_prompts=SystemPrompts.build(task_dir, cn_mode),
            initialization=Initialization.build(task_dir, cn_mode),
            evaluation=Evaluation.build(task_dir, cn_mode),
            single_turn_mode=single_turn_mode,
            cn_mode=cn_mode,
            # The following timestamp contains year, month, day, time, and weekday
            launch_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S %A")
        )

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'task_dir': self.task_dir,
            'id': self.id,
            'needed_mcp_servers': self.needed_mcp_servers,
            'needed_local_tools': self.needed_local_tools,
            'task_root': self.task_root,
            'task_str': self.task_str,
            'log_file': self.log_file,
            'agent_workspace': self.agent_workspace,
            'launch_time': self.launch_time,
            'max_turns': self.max_turns,
            'max_steps_under_single_turn_mode': self.max_steps_under_single_turn_mode,
            'single_turn_mode': self.single_turn_mode,
            'cn_mode': self.cn_mode,
            'system_prompts': {
                'agent': self.system_prompts.agent,
                'user': self.system_prompts.user
            },
            'initialization': {
                'workspace': self.initialization.workspace,
                'process_command': self.initialization.process_command
            },
            'stop': {
                'user_phrases': self.stop.user_phrases,
                'tool_names': self.stop.tool_names,
            },
            'evaluation': {
                'groundtruth_workspace': self.evaluation.groundtruth_workspace,
                'evaluation_command': self.evaluation.evaluation_command
            },
            'meta': self.meta,
            'local_token_key_session': self.local_token_key_session,
            'agent_short_name': self.agent_short_name,
            'global_task_config': self.global_task_config
        }

    def ensure_directories(self):
        """Ensure all necessary directories exist."""
        # Create task root directory
        self.task_root_path.mkdir(parents=True, exist_ok=True)

        # Create agent workspace directory
        self.agent_workspace_path.mkdir(parents=True, exist_ok=True)

        # Ensure parent directory of log file exists
        self.log_file_path.parent.mkdir(parents=True, exist_ok=True)

    def clean_workspace(self):
        """Clean the agent workspace (use with caution)."""
        import shutil
        if self.agent_workspace_path.exists():
            shutil.rmtree(self.agent_workspace_path)
        self.agent_workspace_path.mkdir(parents=True, exist_ok=True)

# Example usage
if __name__ == "__main__":
    pass
