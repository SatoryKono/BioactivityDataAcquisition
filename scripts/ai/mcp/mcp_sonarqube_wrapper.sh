#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./support/docker_cli_resolver.sh
source "${script_dir}/support/docker_cli_resolver.sh"
# shellcheck source=./support/load_repo_env.sh
source "${script_dir}/support/load_repo_env.sh"

load_repo_env_if_present

if [[ -z "${SONARQUBE_TOKEN:-}" ]]; then
  printf "SONARQUBE_TOKEN is required for sonarqube MCP.\n" >&2
  exit 1
fi

if [[ -z "${SONARQUBE_ORG:-}" && -z "${SONARQUBE_URL:-}" ]]; then
  printf "Set SONARQUBE_ORG for SonarQube Cloud or SONARQUBE_URL for SonarQube Server.\n" >&2
  exit 1
fi

docker_bin="$(resolve_docker_bin)"
docker_args=(
  run
  --rm
  -i
  --init
  --pull=always
  -e
  SONARQUBE_TOKEN
)

if [[ -n "${SONARQUBE_ORG:-}" ]]; then
  docker_args+=(-e SONARQUBE_ORG)
fi

if [[ -n "${SONARQUBE_URL:-}" ]]; then
  docker_args+=(-e SONARQUBE_URL)
fi

if [[ -n "${TELEMETRY_DISABLED:-}" ]]; then
  docker_args+=(-e TELEMETRY_DISABLED)
fi

docker_args+=(mcp/sonarqube)

exec "${docker_bin}" "${docker_args[@]}" "$@"
