#!/usr/bin/env bash
# Official github/github-mcp-server launch policy for BioETL GitHub MCP (#10262).
# The retired npx package @modelcontextprotocol/server-github is not a fallback.

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../../.." && pwd)"

# Explicit toolsets: do not use `default` (it includes copilot) or `all`.
BIOETL_GITHUB_MCP_DEFAULT_TOOLSETS="context,issues,pull_requests,repos,users,actions,code_security,dependabot,notifications"
# Remote file writes, merge, and workflow trigger stay off even if a toolset is widened.
BIOETL_GITHUB_MCP_DEFAULT_EXCLUDE_TOOLS="create_or_update_file,push_files,delete_file,fork_repository,create_repository,merge_pull_request,actions_run_trigger"

# shellcheck source=./support/load_repo_env.sh
export BIOETL_SKIP_ENV_LOCAL=1
source "${SCRIPT_DIR}/support/load_repo_env.sh"
load_repo_env_if_present
unset BIOETL_SKIP_ENV_LOCAL
# shellcheck source=./support/token_validation.sh
source "${REPO_ROOT}/scripts/ai/mcp/support/token_validation.sh"

# One token path: existing PAT, else GITHUB_TOKEN alias, else `gh auth token`.
# Never overwrite a configured PAT and never print the secret.
if [[ -n "${GITHUB_PERSONAL_ACCESS_TOKEN:-}" ]]; then
  printf 'github MCP token path: GITHUB_PERSONAL_ACCESS_TOKEN\n' >&2
elif [[ -n "${GITHUB_TOKEN:-}" ]]; then
  export GITHUB_PERSONAL_ACCESS_TOKEN="${GITHUB_TOKEN}"
  printf 'github MCP token path: GITHUB_TOKEN alias\n' >&2
elif command -v gh >/dev/null 2>&1; then
  _github_mcp_token="$(gh auth token 2>/dev/null || true)"
  if [[ -n "${_github_mcp_token}" ]]; then
    export GITHUB_PERSONAL_ACCESS_TOKEN="${_github_mcp_token}"
    printf 'github MCP token path: gh auth token\n' >&2
  fi
  unset _github_mcp_token
fi

mcp_validate_required_token \
  "GITHUB_PERSONAL_ACCESS_TOKEN" \
  20 \
  "GitHub MCP" \
  "ghp_" "github_pat_" "gho_" "ghu_" "ghs_" "ghr_"

if [[ -z "${GITHUB_TOOLSETS:-}" ]]; then
  export GITHUB_TOOLSETS="${BIOETL_GITHUB_MCP_DEFAULT_TOOLSETS}"
fi
if [[ -z "${GITHUB_EXCLUDE_TOOLS:-}" ]]; then
  export GITHUB_EXCLUDE_TOOLS="${BIOETL_GITHUB_MCP_DEFAULT_EXCLUDE_TOOLS}"
fi
if [[ -z "${GITHUB_LOCKDOWN_MODE:-}" ]]; then
  export GITHUB_LOCKDOWN_MODE="true"
fi

mcp_exit_if_validate_only "github"

if [[ -n "${BIOETL_GITHUB_MCP_SERVER:-}" ]]; then
  GITHUB_MCP_BIN="${BIOETL_GITHUB_MCP_SERVER}"
  if [[ ! -x "${GITHUB_MCP_BIN}" ]]; then
    mcp_fail "BIOETL_GITHUB_MCP_SERVER is set but not an executable file: ${GITHUB_MCP_BIN}"
    exit 1
  fi
elif [[ -n "${GITHUB_MCP_SERVER_BIN:-}" ]]; then
  GITHUB_MCP_BIN="${GITHUB_MCP_SERVER_BIN}"
  if [[ ! -x "${GITHUB_MCP_BIN}" ]]; then
    mcp_fail "GITHUB_MCP_SERVER_BIN is set but not an executable file: ${GITHUB_MCP_BIN}"
    exit 1
  fi
else
  GITHUB_MCP_BIN=""
  if command -v github-mcp-server >/dev/null 2>&1; then
    GITHUB_MCP_BIN="$(command -v github-mcp-server)"
  elif command -v github-mcp-server.exe >/dev/null 2>&1; then
    GITHUB_MCP_BIN="$(command -v github-mcp-server.exe)"
  else
    for candidate in \
      "${HOME}/tools/bin/github-mcp-server" \
      "${HOME}/tools/bin/github-mcp-server.exe" \
      "${USERPROFILE:-}/tools/bin/github-mcp-server.exe" \
      "${LOCALAPPDATA:-}/Programs/github-mcp-server/github-mcp-server.exe"
    do
      if [[ -n "${candidate}" && -x "${candidate}" ]]; then
        GITHUB_MCP_BIN="${candidate}"
        break
      fi
    done
  fi
  if [[ -z "${GITHUB_MCP_BIN}" ]]; then
    mcp_fail "official github-mcp-server binary not found. Install https://github.com/github/github-mcp-server and set BIOETL_GITHUB_MCP_SERVER. The retired npx package @modelcontextprotocol/server-github is not used."
    exit 1
  fi
fi

stdio_args=(stdio --toolsets "${GITHUB_TOOLSETS}")
if [[ -n "${GITHUB_EXCLUDE_TOOLS:-}" ]]; then
  stdio_args+=(--exclude-tools "${GITHUB_EXCLUDE_TOOLS}")
fi
case "${GITHUB_LOCKDOWN_MODE:-true}" in
  0|false|FALSE|False|no|NO|off|OFF) ;;
  *) stdio_args+=(--lockdown-mode) ;;
esac

exec "${GITHUB_MCP_BIN}" "${stdio_args[@]}"
