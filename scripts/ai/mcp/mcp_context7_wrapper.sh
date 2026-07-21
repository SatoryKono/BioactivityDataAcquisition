#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${script_dir}/../../.." && pwd)"
# shellcheck source=./support/docker_cli_resolver.sh
source "${script_dir}/support/docker_cli_resolver.sh"
# shellcheck source=./support/load_repo_env.sh
export BIOETL_SKIP_ENV_LOCAL=1
source "${script_dir}/support/load_repo_env.sh"

load_repo_env_if_present
unset BIOETL_SKIP_ENV_LOCAL
export NPM_CONFIG_CACHE="${NPM_CONFIG_CACHE:-${REPO_ROOT}/.cache/npm-cache}"

if docker_bin="$(resolve_docker_mcp_gateway_bin)"; then
    exec "${docker_bin}" mcp gateway run --servers context7 --transport stdio "$@"
fi

exec npx -y @modelcontextprotocol/server-context7 --stdio "$@"
