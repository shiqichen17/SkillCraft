#!/usr/bin/env bash
# run.sh - SkillCraft single-task runner (base/skill/direct-exec + special mode delegates)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Load environment defaults
export TOOLATHLON_QUIET=1
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/prefix.sh"
unset TOOLATHLON_QUIET

cd "${TOOLATHLON_ROOT}"

TASK_PATH="${1:-scaled_tasks/cat-facts-collector/e1}"
MODE="${2:-base}"

AGENT_MODEL="${TOOLATHLON_MODEL:-claude-4.5-sonnet-0929}"
AGENT_PROVIDER="${TOOLATHLON_PROVIDER:-openrouter}"

MODEL_A="${TOOLATHLON_MODEL_A:-}"
PROVIDER_A="${TOOLATHLON_PROVIDER_A:-}"
MODEL_B="${TOOLATHLON_MODEL_B:-}"
PROVIDER_B="${TOOLATHLON_PROVIDER_B:-}"

SKILL_SOURCE=""
SOURCE_LEVELS=""
TARGET_LEVELS=""
SCALED_BASE=""
SCALED_LEVEL=""
CONTINUE_RUN=""
ENABLE_PARALLEL_TOOLS=0
ALLOW_SKILL_NESTING=0

if [ $# -ge 2 ]; then
  shift 2
elif [ $# -ge 1 ]; then
  shift 1
fi

while [[ $# -gt 0 ]]; do
  case "$1" in
    --model)
      AGENT_MODEL="$2"
      shift 2
      ;;
    --provider)
      AGENT_PROVIDER="$2"
      shift 2
      ;;
    --model-a)
      MODEL_A="$2"
      shift 2
      ;;
    --provider-a)
      PROVIDER_A="$2"
      shift 2
      ;;
    --model-b)
      MODEL_B="$2"
      shift 2
      ;;
    --provider-b)
      PROVIDER_B="$2"
      shift 2
      ;;
    --skill-source)
      SKILL_SOURCE="$2"
      shift 2
      ;;
    --source-levels)
      SOURCE_LEVELS="$2"
      shift 2
      ;;
    --target-levels)
      TARGET_LEVELS="$2"
      shift 2
      ;;
    --scaled-base)
      SCALED_BASE="$2"
      shift 2
      ;;
    --scaled-level)
      SCALED_LEVEL="$2"
      shift 2
      ;;
    --continue-run)
      CONTINUE_RUN="$2"
      shift 2
      ;;
    --enable-parallel-tools)
      ENABLE_PARALLEL_TOOLS=1
      shift 1
      ;;
    --allow-skill-nesting)
      ALLOW_SKILL_NESTING=1
      shift 1
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

TASK_PATH="${TASK_PATH#tasks/}"

run_standard_single_task() {
  local selected_mode="$1"
  local dump_path=""
  local enable_skill_cache=false
  local enable_direct_exec=false

  if [[ "$selected_mode" == "base" ]]; then
    dump_path="${TOOLATHLON_DUMP_BASE}/"
    enable_skill_cache=false
    enable_direct_exec=false
    echo "Running in BASE mode"
  elif [[ "$selected_mode" == "skill" ]]; then
    dump_path="${TOOLATHLON_DUMP_SKILL}/"
    enable_skill_cache=true
    enable_direct_exec=false
    echo "Running in SKILL mode"
  elif [[ "$selected_mode" == "direct-exec" ]]; then
    dump_path="${TOOLATHLON_DUMP_DIRECT_EXEC:-${TOOLATHLON_ROOT}/dumps_direct_exec}/"
    enable_skill_cache=false
    enable_direct_exec=true
    echo "Running in DIRECT-EXEC mode"
  else
    echo "Internal error: unsupported standard mode: $selected_mode"
    exit 1
  fi

  local temp_config
  temp_config="$(mktemp /tmp/eval_config_${selected_mode}_XXXXXX.json)"
  cleanup() {
    rm -f "$temp_config"
  }
  trap cleanup EXIT

  cat > "$temp_config" <<EOF_JSON
{
  "global_task_config": {
    "max_turns": ${TOOLATHLON_MAX_TURNS:-50},
    "max_steps_under_single_turn_mode": ${TOOLATHLON_MAX_STEPS:-50},
    "dump_path": "${dump_path}",
    "enable_skill_cache": ${enable_skill_cache},
    "enable_direct_exec": ${enable_direct_exec},
    "max_input_tokens": ${TOOLATHLON_MAX_INPUT_TOKENS:-4000000},
    "max_output_tokens": ${TOOLATHLON_MAX_OUTPUT_TOKENS:-150000}
  },
  "mcp": {
    "server_config_path": "${TOOLATHLON_MCP_CONFIG_DIR}"
  },
  "agent": {
    "model": {
      "short_name": "${AGENT_MODEL}",
      "provider": "${AGENT_PROVIDER}"
    },
    "generation": {
      "temperature": ${TOOLATHLON_AGENT_TEMPERATURE:-0.0},
      "top_p": 1.0,
      "max_tokens": ${TOOLATHLON_AGENT_MAX_TOKENS:-4096}
    },
    "tool": {
      "tool_choice": "auto",
      "parallel_tool_calls": true,
      "max_inner_turns": 2000
    }
  },
  "user": {
    "model": {
      "short_name": "gpt-5",
      "provider": "openrouter"
    },
    "generation": {
      "temperature": ${TOOLATHLON_USER_TEMPERATURE:-1.0},
      "top_p": 1.0,
      "max_tokens": ${TOOLATHLON_USER_MAX_TOKENS:-1024}
    }
  }
}
EOF_JSON

  echo "Task: $TASK_PATH"
  echo "Model: ${AGENT_MODEL} (${AGENT_PROVIDER})"

  uv run python main.py \
    --eval_config "$temp_config" \
    --task_dir "$TASK_PATH"
}

run_test_all_tasks_mode() {
  local selected_mode="$1"
  local cmd=(
    uv run python test_all_tasks.py
    --mode "$selected_mode"
    --model "$AGENT_MODEL"
    --provider "$AGENT_PROVIDER"
  )

  if [[ -n "$CONTINUE_RUN" ]]; then
    cmd+=(--continue-run "$CONTINUE_RUN")
  fi
  if [[ $ENABLE_PARALLEL_TOOLS -eq 1 ]]; then
    cmd+=(--enable-parallel-tools)
  fi
  if [[ $ALLOW_SKILL_NESTING -eq 1 ]]; then
    cmd+=(--allow-skill-nesting)
  fi

  if [[ "$selected_mode" == "cross-task" ]]; then
    if [[ -z "$SCALED_BASE" || -z "$SCALED_LEVEL" ]]; then
      IFS='/' read -r group base level <<<"$TASK_PATH"
      if [[ "$group" != "scaled_tasks" || -z "$base" || -z "$level" ]]; then
        echo "cross-task mode requires scaled task path like scaled_tasks/<base>/<level>"
        echo "or explicit --scaled-base/--scaled-level"
        exit 1
      fi
      SCALED_BASE="${SCALED_BASE:-$base}"
      SCALED_LEVEL="${SCALED_LEVEL:-$level}"
    fi
    cmd+=(--scaled-base "$SCALED_BASE" --scaled-level "$SCALED_LEVEL")
  elif [[ "$selected_mode" == "cross-model" ]]; then
    if [[ -z "$MODEL_A" || -z "$MODEL_B" ]]; then
      echo "cross-model mode requires --model-a and --model-b"
      exit 1
    fi
    cmd+=(
      --task "$TASK_PATH"
      --model-a "$MODEL_A"
      --provider-a "${PROVIDER_A:-$AGENT_PROVIDER}"
      --model-b "$MODEL_B"
      --provider-b "${PROVIDER_B:-$AGENT_PROVIDER}"
    )
  elif [[ "$selected_mode" == "static-reuse" ]]; then
    if [[ -z "$SKILL_SOURCE" ]]; then
      echo "static-reuse mode requires --skill-source"
      exit 1
    fi
    cmd+=(--task "$TASK_PATH" --skill-source "$SKILL_SOURCE")
    if [[ -n "$SOURCE_LEVELS" ]]; then
      cmd+=(--source-levels "$SOURCE_LEVELS")
    fi
    if [[ -n "$TARGET_LEVELS" ]]; then
      cmd+=(--target-levels "$TARGET_LEVELS")
    fi
  else
    echo "Internal error: unsupported delegated mode: $selected_mode"
    exit 1
  fi

  echo "Command: ${cmd[*]}"
  "${cmd[@]}"
}

case "$MODE" in
  base|skill|direct-exec)
    run_standard_single_task "$MODE"
    ;;
  cross-task|cross-model|static-reuse)
    run_test_all_tasks_mode "$MODE"
    ;;
  *)
    echo "Invalid mode: $MODE"
    echo "Supported modes: base, skill, direct-exec, cross-task, cross-model, static-reuse"
    exit 1
    ;;
esac
