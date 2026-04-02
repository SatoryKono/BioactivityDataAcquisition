#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./docker_cli_resolver.sh
source "${script_dir}/docker_cli_resolver.sh"
# shellcheck source=./load_repo_env.sh
source "${script_dir}/load_repo_env.sh"

load_repo_env_if_present

if [[ -z "${DOCKERHUB_USERNAME:-}" ]]; then
  printf "DOCKERHUB_USERNAME is required for dockerhub MCP.\n" >&2
  exit 1
fi
if [[ -z "${HUB_PAT_TOKEN:-}" ]]; then
  printf "HUB_PAT_TOKEN is required for dockerhub MCP.\n" >&2
  exit 1
fi

docker_bin="$(resolve_docker_bin)"
exec "${docker_bin}" run --rm -i \
  -e "HUB_PAT_TOKEN=${HUB_PAT_TOKEN}" \
  mcp/dockerhub \
  --username "${DOCKERHUB_USERNAME}" \
  "$@"
