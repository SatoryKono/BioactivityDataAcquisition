#!/usr/bin/env bash
# MCP memory server with branch/commit/worktree-scoped local persistence.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
memory_mode_is_explicit=0
requested_memory_mode=""
if [[ -n "${BIOETL_AI_MEMORY_MODE:-}" ]]; then
  memory_mode_is_explicit=1
  requested_memory_mode="${BIOETL_AI_MEMORY_MODE}"
fi
source "${SCRIPT_DIR}/support/load_repo_env.sh"
export BIOETL_SKIP_ENV_LOCAL=1
load_repo_env_if_present
unset BIOETL_SKIP_ENV_LOCAL
if [[ "${memory_mode_is_explicit}" == "1" ]]; then
  export BIOETL_AI_MEMORY_MODE="${requested_memory_mode}"
fi
source "${SCRIPT_DIR}/support/token_validation.sh"

mcp_exit_if_validate_only "memory"

memory_mode="${BIOETL_AI_MEMORY_MODE:-}"
if [[ "${memory_mode_is_explicit}" == "0" ]]; then
  case "$memory_mode" in
    \"*\"|\'*\') memory_mode="${memory_mode:1:-1}" ;;
    *) ;;
  esac
fi
memory_mode="${memory_mode#"${memory_mode%%[![:space:]]*}"}"
memory_mode="${memory_mode%"${memory_mode##*[![:space:]]}"}"
memory_mode="${memory_mode:-off}"
case "${memory_mode}" in
  read-write|readwrite|rw)
    ;;
  off|disabled|read-only|readonly|ro)
    printf '%s\n' \
      "Persistent MCP memory is disabled by BIOETL_AI_MEMORY_MODE=${memory_mode}" >&2
    exit 78
    ;;
  *)
    printf '%s\n' \
      "Invalid BIOETL_AI_MEMORY_MODE; expected off, read-only, or read-write" >&2
    exit 64
    ;;
esac

if [[ -n "${BIOETL_WSL_VENV_DIR:-}" && -x "${BIOETL_WSL_VENV_DIR}/bin/python" ]]; then
  MEMORY_PYTHON="${BIOETL_WSL_VENV_DIR}/bin/python"
elif [[ -x "${REPO_ROOT}/.venv/bin/python" ]]; then
  MEMORY_PYTHON="${REPO_ROOT}/.venv/bin/python"
elif [[ -x "${REPO_ROOT}/.venv-win/Scripts/python.exe" ]]; then
  # Native Windows Git Bash: .mcp.json launches this .sh, not the .ps1 (#9712).
  MEMORY_PYTHON="${REPO_ROOT}/.venv-win/Scripts/python.exe"
elif command -v python3 >/dev/null 2>&1; then
  MEMORY_PYTHON="$(command -v python3)"
else
  printf '%s\n' "Memory MCP requires a project Python interpreter" >&2
  exit 69
fi

export PYTHONPATH="${REPO_ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}"
scope_args=()
if [[ -n "${MEMORY_FILE_PATH:-}" ]]; then
  scope_args+=(--target "${MEMORY_FILE_PATH}")
fi
export MEMORY_REPO_ROOT="${REPO_ROOT}"
if ! MEMORY_FILE_PATH="$(
    "${MEMORY_PYTHON}" -m memory.mcp_scope \
      --repo-root "${REPO_ROOT}" \
      --seed "${MEMORY_SEED_PATH:-${REPO_ROOT}/docs/00-project/ai/memory/mcp-memory.json}" \
      "${scope_args[@]}"
  )"; then
  printf '%s\n' "Memory MCP could not scope its store. Regenerate the MCP configuration with a store under .cache/mcp-memory." >&2
  exit 78
fi
export MEMORY_FILE_PATH
exec "${MEMORY_PYTHON}" -m memory.mcp_server "$@"
