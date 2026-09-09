#!/usr/bin/env bash
# Official github/github-mcp-server launch policy for BioETL GitHub MCP (#10262).
# The retired npx package @modelcontextprotocol/server-github is not a fallback.

# Explicit toolsets: do not use `default` (it includes copilot) or `all`.
BIOETL_GITHUB_MCP_DEFAULT_TOOLSETS="context,issues,pull_requests,repos,users,actions,code_security,dependabot,notifications"
# Remote file writes, merge, and workflow trigger stay off even if a toolset is widened.
BIOETL_GITHUB_MCP_DEFAULT_EXCLUDE_TOOLS="create_or_update_file,push_files,delete_file,fork_repository,create_repository,merge_pull_request,actions_run_trigger"

bioetl_github_mcp_apply_policy_env() {
  export GITHUB_TOOLSETS="${BIOETL_GITHUB_MCP_DEFAULT_TOOLSETS}"
  export GITHUB_EXCLUDE_TOOLS="${BIOETL_GITHUB_MCP_DEFAULT_EXCLUDE_TOOLS}"
  export GITHUB_LOCKDOWN_MODE="true"
}

bioetl_github_mcp_resolve_token() {
  # Tokens must come from the repository environment loader; never use local CLI credentials.
  if [[ -n "${GITHUB_PERSONAL_ACCESS_TOKEN:-}" ]]; then
    printf 'github MCP token path: %s\n' "${BIOETL_GITHUB_TOKEN_SOURCE:-GITHUB_PERSONAL_ACCESS_TOKEN}" >&2
    return 0
  fi
  if [[ -n "${GITHUB_TOKEN:-}" ]]; then
    export GITHUB_PERSONAL_ACCESS_TOKEN="${GITHUB_TOKEN}"
    printf 'github MCP token path: GITHUB_TOKEN alias\n' >&2
    return 0
  fi
  mcp_fail "GitHub MCP requires GITHUB_PERSONAL_ACCESS_TOKEN from the repository environment. Do not commit secrets."
  return 1
}

bioetl_github_mcp_resolve_bin() {
  local candidate
  if [[ -n "${BIOETL_GITHUB_MCP_SERVER:-}" ]]; then
    candidate="${BIOETL_GITHUB_MCP_SERVER}"
    if [[ -x "${candidate}" ]]; then
      printf '%s\n' "${candidate}"
      return 0
    fi
    mcp_fail "BIOETL_GITHUB_MCP_SERVER is set but not an executable file: ${candidate}"
    return 1
  fi
  if [[ -n "${GITHUB_MCP_SERVER_BIN:-}" ]]; then
    candidate="${GITHUB_MCP_SERVER_BIN}"
    if [[ -x "${candidate}" ]]; then
      printf '%s\n' "${candidate}"
      return 0
    fi
    mcp_fail "GITHUB_MCP_SERVER_BIN is set but not an executable file: ${candidate}"
    return 1
  fi

  local -a candidates=()
  if command -v github-mcp-server >/dev/null 2>&1; then
    candidates+=("$(command -v github-mcp-server)")
  fi
  if command -v github-mcp-server.exe >/dev/null 2>&1; then
    candidates+=("$(command -v github-mcp-server.exe)")
  fi
  candidates+=(
    "${HOME}/tools/bin/github-mcp-server"
    "${HOME}/tools/bin/github-mcp-server.exe"
    "${USERPROFILE:-}/tools/bin/github-mcp-server.exe"
    "${LOCALAPPDATA:-}/Programs/github-mcp-server/github-mcp-server.exe"
  )
  for candidate in "${candidates[@]}"; do
    [[ -n "${candidate}" ]] || continue
    if [[ -x "${candidate}" ]]; then
      printf '%s\n' "${candidate}"
      return 0
    fi
  done
  mcp_fail "official github-mcp-server binary not found. Install https://github.com/github/github-mcp-server and set BIOETL_GITHUB_MCP_SERVER. The retired npx package @modelcontextprotocol/server-github is not used."
  return 1
}
