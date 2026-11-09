#!/usr/bin/env bash
# Official github/github-mcp-server launch policy for BioETL GitHub MCP (#10262).
# The retired npx package @modelcontextprotocol/server-github is not a fallback.
# After project policy checks, an optional machine-local shared transport may run
# via scripts/ai/mcp/support/github_project_transport.mjs when
# PC_AGENT_GITHUB_PROJECT_ROUTES or ~/.config/pc-agent/github-project-route.json
# is present; exit 78 falls back to the native binary.

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
# Never overwrite a configured PAT, never print the secret, and never export
# GITHUB_TOKEN from PAT (parent gh must keep hosts.yml; #10298).
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

# Caller exclusions can tighten the mandatory deny set, never remove it.
if [[ "${GITHUB_EXCLUDE_TOOLS}" != "${BIOETL_GITHUB_MCP_DEFAULT_EXCLUDE_TOOLS}" ]]; then
  export GITHUB_EXCLUDE_TOOLS="${GITHUB_EXCLUDE_TOOLS},${BIOETL_GITHUB_MCP_DEFAULT_EXCLUDE_TOOLS}"
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

if [[ "${BIOETL_GITHUB_MCP_ACCESS:-read-only}" == "read-write" && -z "${BIOETL_GITHUB_MCP_SHA256:-}" ]]; then
  mcp_fail "read-write requires an explicitly approved BIOETL_GITHUB_MCP_SHA256"
  exit 64
fi
if [[ -n "${BIOETL_GITHUB_MCP_SHA256:-}" ]]; then
  if [[ ! "${BIOETL_GITHUB_MCP_SHA256}" =~ ^[a-fA-F0-9]{64}$ ]]; then
    mcp_fail "BIOETL_GITHUB_MCP_SHA256 must be a SHA-256 digest"; exit 64
  fi
  actual_digest="$(sha256sum -- "${GITHUB_MCP_BIN}")"
  actual_digest="${actual_digest%% *}"
  if [[ "${actual_digest,,}" != "${BIOETL_GITHUB_MCP_SHA256,,}" ]]; then
    mcp_fail "GitHub MCP executable digest does not match approved identity"; exit 64
  fi
fi
stdio_args=(stdio --toolsets "${GITHUB_TOOLSETS}")
case "${BIOETL_GITHUB_MCP_ACCESS:-read-only}" in
  read-only) stdio_args+=(--read-only) ;;
  read-write) ;;
  *) mcp_fail "BIOETL_GITHUB_MCP_ACCESS must be read-only or read-write"; exit 64 ;;
esac
if [[ -n "${GITHUB_EXCLUDE_TOOLS:-}" ]]; then
  stdio_args+=(--exclude-tools "${GITHUB_EXCLUDE_TOOLS}")
fi
case "${GITHUB_LOCKDOWN_MODE:-true}" in
  0|false|FALSE|False|no|NO|off|OFF) ;;
  *) stdio_args+=(--lockdown-mode) ;;
esac

# Do not pass unrelated integration credentials to this server.
github_env=()
for key in PATH HOME USERPROFILE SYSTEMROOT WINDIR TEMP TMP TMPDIR \
  LANG LC_ALL SSL_CERT_FILE SSL_CERT_DIR HTTP_PROXY HTTPS_PROXY NO_PROXY \
  http_proxy https_proxy no_proxy GITHUB_PERSONAL_ACCESS_TOKEN GITHUB_HOST; do
  if [[ -n "${!key:-}" ]]; then
    github_env+=("${key}=${!key}")
  fi
done
# Optional machine-local shared GitHub transport, after all project policy checks.
github_route_file="${PC_AGENT_GITHUB_PROJECT_ROUTES:-${HOME}/.config/pc-agent/github-project-route.json}"
if [[ -n "${PC_AGENT_GITHUB_PROJECT_ROUTES:-}" || -f "${github_route_file}" ]]; then
  github_transport="${SCRIPT_DIR}/support/github_project_transport.mjs"
  [[ -f "${github_transport}" ]] || { mcp_fail "Managed GitHub transport helper missing"; exit 1; }
  command -v node >/dev/null 2>&1 || { mcp_fail "Managed GitHub transport requires node"; exit 1; }
  if node "${github_transport}" --root "${REPO_ROOT}" --binary "${GITHUB_MCP_BIN}" --approved-sha "${BIOETL_GITHUB_MCP_SHA256:--}" -- "${stdio_args[@]}"; then
    exit 0
  else
    github_transport_result=$?
  fi
  [[ "${github_transport_result}" == "78" ]] || exit "${github_transport_result}"
fi

exec env -i "${github_env[@]}" "${GITHUB_MCP_BIN}" "${stdio_args[@]}"
