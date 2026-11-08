#!/usr/bin/env bash
set -euo pipefail

# Optional host route is resolved before env/cache/Docker side effects.
mcp_host_marker="${PC_AGENT_MCP_ROUTES_FILE:-${HOME}/.config/pc-agent/mcp-routes.json}"
if [[ -n "${PC_AGENT_MCP_ROUTES_FILE:-}" || -e "${mcp_host_marker}" || -L "${mcp_host_marker}" ]]; then
  mcp_host_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
  mcp_host_root="$(cd -- "${mcp_host_dir}/../../.." && pwd)"
  if command -v cygpath >/dev/null 2>&1; then
    mcp_host_root="$(cygpath -w "${mcp_host_root}")"
  fi
  if node "${mcp_host_dir}/support/host_transport.mjs" --root "${mcp_host_root}" --server brave-search -- "$@"; then
    exit 0
  else
    mcp_host_status=$?
    if [[ "${mcp_host_status}" -ne 78 ]]; then exit "${mcp_host_status}"; fi
  fi
fi
unset mcp_host_marker

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./support/docker_cli_resolver.sh
source "${script_dir}/support/docker_cli_resolver.sh"
# shellcheck source=./support/load_repo_env.sh
export BIOETL_SKIP_ENV_LOCAL=1
source "${script_dir}/support/load_repo_env.sh"
# shellcheck source=./support/token_validation.sh
source "${script_dir}/support/token_validation.sh"

load_repo_env_if_present
unset BIOETL_SKIP_ENV_LOCAL

mcp_validate_required_token "BRAVE_API_KEY" 31 "Brave Search MCP"
mcp_exit_if_validate_only "brave-search"

# shellcheck source=./support/mcp_docker_prune.sh
source "${script_dir}/support/mcp_docker_prune.sh"
remove_mcp_exited_containers "mcp/brave-search"

docker_bin="$(resolve_docker_bin)"
exec "${docker_bin}" run --rm -i \
  --label "bioetl.mcp=brave-search" \
  -e BRAVE_API_KEY \
  mcp/brave-search "$@"
