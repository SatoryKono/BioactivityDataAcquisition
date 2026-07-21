#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "${script_dir}/../../.." && pwd)"
# shellcheck source=./support/docker_cli_resolver.sh
source "${script_dir}/support/docker_cli_resolver.sh"

export NPM_CONFIG_CACHE="${NPM_CONFIG_CACHE:-${repo_root}/.cache/npm-cache}"

if docker_bin="$(resolve_docker_mcp_gateway_bin)"; then
  exec "${docker_bin}" mcp gateway run --servers mermaid --transport stdio "$@"
fi

exec npx -y @modelcontextprotocol/server-mermaid --stdio "$@"
