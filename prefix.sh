#!/bin/bash
# prefix.sh - Toolathlon Unified Configuration Center
# =======================================================
# All environment variables, API keys, and paths are configured here.
# Source this file before running any Toolathlon scripts.
#
# Usage:
#   source prefix.sh          # In shell scripts
#   os.environ.get("VAR")     # In Python code (after sourcing)
#
# To override: export variables BEFORE sourcing this file
#   export TOOLATHLON_MODEL="o4-mini"
#   source prefix.sh

set -a  # Auto-export all variables

# ============================================
# 📁 CORE PATH CONFIGURATION
# ============================================
# Auto-detect script location and project root
_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
_PROJECT_ROOT="${_SCRIPT_DIR}"

# ============================================
# 📄 LOAD .env FILE (if exists)
# ============================================
# Load .env file from project root if it exists.
# Use a tolerant parser instead of `source` so one malformed line does not
# break the whole runtime setup.
_load_env_file() {
    local env_file="$1"
    while IFS= read -r line || [[ -n "$line" ]]; do
        # Skip empty lines and comments
        [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
        [[ "$line" != *"="* ]] && continue

        local key="${line%%=*}"
        local value="${line#*=}"

        # Trim spaces around key/value
        key="$(echo "$key" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"
        value="$(echo "$value" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"

        # Strip optional single/double quotes
        if [[ "$value" =~ ^\".*\"$ || "$value" =~ ^\'.*\'$ ]]; then
            value="${value:1:${#value}-2}"
        fi

        # Export only valid key names
        if [[ "$key" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]]; then
            export "$key=$value"
        fi
    done < "$env_file"
}

if [[ -f "${_SCRIPT_DIR}/.env" ]]; then
    _load_env_file "${_SCRIPT_DIR}/.env"
fi

# Project paths (can be overridden via environment variables)
export TOOLATHLON_ROOT="${TOOLATHLON_ROOT:-${_PROJECT_ROOT}}"
export TOOLATHLON_TASKS_DIR="${TOOLATHLON_TASKS_DIR:-${TOOLATHLON_ROOT}/tasks}"
export TOOLATHLON_CONFIGS_DIR="${TOOLATHLON_CONFIGS_DIR:-${TOOLATHLON_ROOT}/configs}"

# Output directories
export TOOLATHLON_DUMP_DIR="${TOOLATHLON_DUMP_DIR:-${TOOLATHLON_ROOT}/dumps}"
export TOOLATHLON_DUMP_BASE="${TOOLATHLON_DUMP_BASE:-${TOOLATHLON_ROOT}/dumps_base_test}"
export TOOLATHLON_DUMP_SKILL="${TOOLATHLON_DUMP_SKILL:-${TOOLATHLON_ROOT}/dumps_skill_test}"
export TOOLATHLON_DUMP_DIRECT_EXEC="${TOOLATHLON_DUMP_DIRECT_EXEC:-${TOOLATHLON_ROOT}/dumps_direct_exec}"
export TOOLATHLON_DUMP_CROSS_MODEL="${TOOLATHLON_DUMP_CROSS_MODEL:-${TOOLATHLON_ROOT}/dumps_cross_model}"
export TOOLATHLON_SKILL_TEST_DIR="${TOOLATHLON_SKILL_TEST_DIR:-${TOOLATHLON_ROOT}/skill_test}"

# MCP server configurations
export TOOLATHLON_MCP_CONFIG_DIR="${TOOLATHLON_MCP_CONFIG_DIR:-${TOOLATHLON_CONFIGS_DIR}/mcp_servers}"
export TOOLATHLON_LOCAL_SERVERS="${TOOLATHLON_LOCAL_SERVERS:-${TOOLATHLON_ROOT}/local_mcp_servers}"
export TOOLATHLON_LOCAL_BINARIES="${TOOLATHLON_LOCAL_BINARIES:-${TOOLATHLON_ROOT}/local_mcp_binaries}"

# Temp/cache directories (use external storage to avoid filling system disk)
export TOOLATHLON_CACHE_DIR="${TOOLATHLON_CACHE_DIR:-/hy-tmp/toolathlon_cache}"
export TOOLATHLON_HOME="${TOOLATHLON_HOME:-/hy-tmp/toolathlon_home}"

# ============================================
# 🤖 LLM API CONFIGURATION
# ============================================
# OpenRouter (primary endpoint for multi-model access)
export TOOLATHLON_OPENAI_BASE_URL="${TOOLATHLON_OPENAI_BASE_URL:-https://openrouter.ai/api/v1}"
# Keep empty by default; set via .env or shell export before running.
export TOOLATHLON_OPENAI_API_KEY="${TOOLATHLON_OPENAI_API_KEY:-}"

# Alternative endpoints (uncomment to use)
# export TOOLATHLON_OPENAI_BASE_URL="https://api.openai.com/v1"
# export TOOLATHLON_OPENAI_BASE_URL="https://api.anthropic.com/v1"

# Default model configuration
export TOOLATHLON_MODEL="${TOOLATHLON_MODEL:-claude-4.5-sonnet-0929}"
export TOOLATHLON_PROVIDER="${TOOLATHLON_PROVIDER:-openrouter}"

# Model-specific settings
export TOOLATHLON_AGENT_TEMPERATURE="${TOOLATHLON_AGENT_TEMPERATURE:-0.0}"  # Default to 0 for deterministic output
export TOOLATHLON_AGENT_MAX_TOKENS="${TOOLATHLON_AGENT_MAX_TOKENS:-4096}"
export TOOLATHLON_USER_TEMPERATURE="${TOOLATHLON_USER_TEMPERATURE:-1.0}"
export TOOLATHLON_USER_MAX_TOKENS="${TOOLATHLON_USER_MAX_TOKENS:-1024}"

# Task execution limits
export TOOLATHLON_MAX_TURNS="${TOOLATHLON_MAX_TURNS:-50}"
export TOOLATHLON_MAX_STEPS="${TOOLATHLON_MAX_STEPS:-50}"
export TOOLATHLON_TASK_TIMEOUT="${TOOLATHLON_TASK_TIMEOUT:-600}"  # 10 minutes

# ============================================
# 🔑 MCP SERVER API KEYS
# ============================================
# These are used by configs/token_key_session.py
# Set actual values or leave empty to skip those servers

# --- 🟢 SIMPLE SETUP (API Key Only) ---

# HuggingFace (https://huggingface.co/settings/tokens)
export HUGGINGFACE_TOKEN="${HUGGINGFACE_TOKEN:-}"

# Weights & Biases (https://wandb.ai/authorize)
export WANDB_API_KEY="${WANDB_API_KEY:-}"

# GitHub (https://github.com/settings/tokens)
export GITHUB_TOKEN="${GITHUB_TOKEN:-}"
export GITHUB_ALLOWED_REPOS="${GITHUB_ALLOWED_REPOS:-*}"  # "*" for all or "owner/repo1,owner/repo2"
export GITHUB_READ_ONLY="${GITHUB_READ_ONLY:-0}"  # "1" for read-only

# Serper (Google Search API - https://serper.dev/)
export SERPER_API_KEY="${SERPER_API_KEY:-}"

# --- 🟡 MEDIUM SETUP (OAuth/Service Account) ---

# Google Cloud Console API Key (for YouTube, etc.)
# Get from: https://console.cloud.google.com/apis/credentials
export GOOGLE_CLOUD_API_KEY="${GOOGLE_CLOUD_API_KEY:-}"

# Google Cloud Platform (GCP) Service Account
# Create at: https://console.cloud.google.com/iam-admin/serviceaccounts
export GCP_PROJECT_ID="${GCP_PROJECT_ID:-}"
export GCP_SERVICE_ACCOUNT_PATH="${GCP_SERVICE_ACCOUNT_PATH:-${TOOLATHLON_CONFIGS_DIR}/gcp-service_account.keys.json}"

# Google Sheets/Drive (OAuth2 Credentials)
# Create at: https://console.cloud.google.com/apis/credentials (OAuth Client ID)
export GOOGLE_OAUTH2_CREDENTIALS_PATH="${GOOGLE_OAUTH2_CREDENTIALS_PATH:-${TOOLATHLON_CONFIGS_DIR}/google_credentials.json}"
export GOOGLE_OAUTH2_TOKEN_PATH="${GOOGLE_OAUTH2_TOKEN_PATH:-${TOOLATHLON_CONFIGS_DIR}/google_credentials.json}"
export GOOGLE_SHEETS_FOLDER_ID="${GOOGLE_SHEETS_FOLDER_ID:-}"

# Notion Integration (https://www.notion.so/my-integrations)
export NOTION_INTEGRATION_KEY="${NOTION_INTEGRATION_KEY:-}"
export NOTION_INTEGRATION_KEY_EVAL="${NOTION_INTEGRATION_KEY_EVAL:-${NOTION_INTEGRATION_KEY}}"
export NOTION_PAGE_IDS="${NOTION_PAGE_IDS:-}"  # Comma-separated page IDs

# Snowflake (for database tasks)
export SNOWFLAKE_ACCOUNT="${SNOWFLAKE_ACCOUNT:-}"
export SNOWFLAKE_USER="${SNOWFLAKE_USER:-}"
export SNOWFLAKE_PASSWORD="${SNOWFLAKE_PASSWORD:-}"
export SNOWFLAKE_WAREHOUSE="${SNOWFLAKE_WAREHOUSE:-COMPUTE_WH}"
export SNOWFLAKE_ROLE="${SNOWFLAKE_ROLE:-ACCOUNTADMIN}"
export SNOWFLAKE_DATABASE="${SNOWFLAKE_DATABASE:-SNOWFLAKE}"
export SNOWFLAKE_SCHEMA="${SNOWFLAKE_SCHEMA:-PUBLIC}"

# --- 🔴 COMPLEX SETUP (Infrastructure Required) ---

# Kubernetes (path to kubeconfig file)
export KUBECONFIG_PATH="${KUBECONFIG_PATH:-${TOOLATHLON_ROOT}/deployment/k8s/configs/cluster1-config.yaml}"

# ============================================
# 🐳 DOCKER/PODMAN CONFIGURATION
# ============================================
# Set HOME for Docker wrapper (avoids /root permission issues)
export HOME="${TOOLATHLON_HOME}"
mkdir -p "$HOME/bin" 2>/dev/null || true
export PATH="$HOME/bin:$PATH"

# ============================================
# 📦 CACHE DIRECTORIES
# ============================================
# Use external storage to avoid filling system disk
mkdir -p "${TOOLATHLON_CACHE_DIR}" 2>/dev/null || true

export TRITON_CACHE_DIR="${TRITON_CACHE_DIR:-${TOOLATHLON_CACHE_DIR}}"
export TRANSFORMERS_CACHE="${TRANSFORMERS_CACHE:-${TOOLATHLON_CACHE_DIR}}"
export HF_HOME="${HF_HOME:-${TOOLATHLON_CACHE_DIR}}"
export HF_DATASETS_CACHE="${HF_DATASETS_CACHE:-${TOOLATHLON_CACHE_DIR}}"
export HF_ENDPOINT="${HF_ENDPOINT:-https://huggingface.co}"  # Change to https://hf-mirror.com for China

export TMPDIR="${TMPDIR:-${TOOLATHLON_CACHE_DIR}/tmp}"
export TEMP="${TEMP:-${TMPDIR}}"
export TMP="${TMP:-${TMPDIR}}"
mkdir -p "${TMPDIR}" 2>/dev/null || true

# ============================================
# 🐍 PYTHON PATH CONFIGURATION
# ============================================
if [[ ":$PYTHONPATH:" != *":${TOOLATHLON_ROOT}:"* ]]; then
    export PYTHONPATH="${TOOLATHLON_ROOT}:${PYTHONPATH}"
fi

set +a  # Stop auto-export

# ============================================
# 📋 DOCKER WRAPPER SETUP (for Podman compatibility)
# ============================================
_setup_docker_wrapper() {
    local wrapper_path="$HOME/bin/docker"
    
    if [[ -f "$wrapper_path" ]]; then
        return 0  # Already exists
    fi
    
    cat > "$wrapper_path" <<'WRAPPER_EOF'
#!/usr/bin/env bash
set -euo pipefail
filtered=()
name=""
while (( "$#" )); do
  a="$1"; shift
  if [[ "$a" == "--network" ]]; then
    [[ "${1:-}" == "host" ]] && { shift; continue; }
  fi
  if [[ "$a" == "--network=host" ]]; then continue; fi
  if [[ "$a" == "--name" ]]; then name="${1:-}"; filtered+=("--name" "$1"); shift; continue; fi
  if [[ "$a" == --name=* ]]; then name="${a#--name=}"; filtered+=("$a"); continue; fi
  if [[ "$a" == "-v" ]]; then
    m="${1:-}"; shift || true
    [[ "$m" == *docker.sock:* || "$m" == *podman.sock:* ]] && continue
    filtered+=("-v" "$m"); continue
  fi
  if [[ "$a" == -v* ]] && [[ "$a" == *docker.sock:* || "$a" == *podman.sock:* ]]; then continue; fi
  filtered+=("$a")
done
if [[ "${filtered[0]:-}" == "run" ]]; then
  cid=$(command podman "${filtered[@]}")
  if [[ -n "$name" ]]; then
    command podman exec "$name" /bin/sh -lc 'mkdir -p /usr/local/bin;
cat > /usr/local/bin/docker <<EOS
#!/usr/bin/env sh
if [ "\$1" = "info" ]; then echo "Client: Docker Engine (shim)"; exit 0; fi
exit 0
EOS
chmod +x /usr/local/bin/docker'
  fi
  printf "%s\n" "$cid"
  exit 0
fi
exec podman "${filtered[@]}"
WRAPPER_EOF
    chmod +x "$wrapper_path"
}

# Only setup wrapper if podman exists and docker doesn't
if command -v podman &>/dev/null && ! command -v docker &>/dev/null; then
    _setup_docker_wrapper 2>/dev/null || true
fi

# ============================================
# 🔍 VALIDATION & STATUS
# ============================================
_print_status() {
    echo ""
    echo "========================================"
    echo "🛠️  Toolathlon Environment Configuration"
    echo "========================================"
    echo ""
    echo "📁 Paths:"
    echo "   TOOLATHLON_ROOT:              ${TOOLATHLON_ROOT}"
    echo "   TOOLATHLON_DUMP_BASE:       ${TOOLATHLON_DUMP_BASE}"
    echo "   TOOLATHLON_DUMP_SKILL:        ${TOOLATHLON_DUMP_SKILL}"
    echo "   TOOLATHLON_DUMP_DIRECT_EXEC:  ${TOOLATHLON_DUMP_DIRECT_EXEC}"
    echo "   TOOLATHLON_DUMP_CROSS_MODEL:  ${TOOLATHLON_DUMP_CROSS_MODEL}"
    echo ""
    echo "🤖 Model Configuration:"
    echo "   Model:    ${TOOLATHLON_MODEL}"
    echo "   Provider: ${TOOLATHLON_PROVIDER}"
    echo "   API URL:  ${TOOLATHLON_OPENAI_BASE_URL}"
    echo ""
    echo "🔑 API Keys Status:"
    
    # Check each API key
    if [[ -n "${TOOLATHLON_OPENAI_API_KEY}" ]]; then
        echo "   ✅ OpenRouter API Key: Set"
    else
        echo "   ❌ OpenRouter API Key: NOT SET (required)"
    fi
    
    if [[ -n "${HUGGINGFACE_TOKEN}" ]]; then
        echo "   ✅ HuggingFace Token: Set"
    else
        echo "   ⚠️  HuggingFace Token: Not set (optional)"
    fi
    
    if [[ -n "${WANDB_API_KEY}" ]]; then
        echo "   ✅ WandB API Key: Set"
    else
        echo "   ⚠️  WandB API Key: Not set (optional)"
    fi
    
    if [[ -n "${GITHUB_TOKEN}" ]]; then
        echo "   ✅ GitHub Token: Set"
    else
        echo "   ⚠️  GitHub Token: Not set (optional)"
    fi
    
    if [[ -n "${GOOGLE_CLOUD_API_KEY}" ]]; then
        echo "   ✅ Google Cloud API Key: Set"
    else
        echo "   ⚠️  Google Cloud API Key: Not set (optional)"
    fi
    
    if [[ -n "${GCP_PROJECT_ID}" ]] && [[ -f "${GCP_SERVICE_ACCOUNT_PATH}" ]]; then
        echo "   ✅ GCP Service Account: Configured"
    else
        echo "   ⚠️  GCP Service Account: Not configured (optional)"
    fi
    
    if [[ -f "${GOOGLE_OAUTH2_CREDENTIALS_PATH}" ]]; then
        echo "   ✅ Google OAuth2: Configured"
    else
        echo "   ⚠️  Google OAuth2: Not configured (optional)"
    fi
    
    if [[ -n "${NOTION_INTEGRATION_KEY}" ]]; then
        echo "   ✅ Notion Integration: Set"
    else
        echo "   ⚠️  Notion Integration: Not set (optional)"
    fi
    
    if [[ -f "${KUBECONFIG_PATH}" ]]; then
        echo "   ✅ Kubernetes Config: Found"
    else
        echo "   ⚠️  Kubernetes Config: Not found (optional)"
    fi
    
    echo ""
    echo "========================================"
    echo ""
}

# Show status unless TOOLATHLON_QUIET is set
if [[ -z "${TOOLATHLON_QUIET:-}" ]]; then
    _print_status
fi

# ============================================
# 🚀 QUICK REFERENCE
# ============================================
# After sourcing this file, you can run:
#
# Run a single task (base mode):
#   ./run.sh scaled_tasks/cat-facts-collector/e1 base
#
# Run a single task (skill mode):
#   ./run.sh scaled_tasks/cat-facts-collector/e1 skill
#
# Run the scaled-task pipeline (base + skill):
#   uv run python test_all_tasks.py --mode base,skill --model ${TOOLATHLON_MODEL}
#
# Override model for a single run:
#   TOOLATHLON_MODEL=o4-mini ./run.sh scaled_tasks/cat-facts-collector/e1 skill
