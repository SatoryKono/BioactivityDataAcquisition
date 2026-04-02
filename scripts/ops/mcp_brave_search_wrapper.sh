#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./docker_cli_resolver.sh
source "${script_dir}/docker_cli_resolver.sh"
# shellcheck source=./load_repo_env.sh
source "${script_dir}/load_repo_env.sh"

load_repo_env_if_present

if [[ -z "${BRAVE_API_KEY:-}" ]]; then
  printf "BRAVE_API_KEY is required for brave-search MCP.\n" >&2
  exit 1
fi

docker_bin="$(resolve_docker_bin)"
exec "${docker_bin}" run --rm -i \
  -e "BRAVE_API_KEY=${BRAVE_API_KEY}" \
  mcp/brave-search "$@"
