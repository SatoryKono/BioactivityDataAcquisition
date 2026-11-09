#!/usr/bin/env bash
set -euo pipefail

# shellcheck source=./support/invoke_host_transport.sh
source "$(dirname -- "${BASH_SOURCE[0]}")/support/invoke_host_transport.sh"
if run_mcp_host_route brave-search "$@"; then
  exit 0
else
  mcp_host_status=$?
  if [[ "${mcp_host_status}" -ne 78 ]]; then exit "${mcp_host_status}"; fi
fi

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
