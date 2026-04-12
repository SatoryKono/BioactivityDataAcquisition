#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./support/docker_cli_resolver.sh
source "${script_dir}/support/docker_cli_resolver.sh"
# shellcheck source=./support/load_repo_env.sh
export BIOETL_SKIP_ENV_LOCAL=1
source "${script_dir}/support/load_repo_env.sh"

load_repo_env_if_present
unset BIOETL_SKIP_ENV_LOCAL

if [[ -z "${BRAVE_API_KEY:-}" ]]; then
  printf "BRAVE_API_KEY is required for brave-search MCP.\n" >&2
  exit 1
fi

docker_bin="$(resolve_docker_bin)"
exec "${docker_bin}" run --rm -i \
  -e "BRAVE_API_KEY=${BRAVE_API_KEY}" \
  mcp/brave-search "$@"
