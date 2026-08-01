#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./support/docker_cli_resolver.sh
source "${script_dir}/support/docker_cli_resolver.sh"
# shellcheck source=./support/load_repo_env.sh
source "${script_dir}/support/load_repo_env.sh"
# shellcheck source=./support/token_validation.sh
source "${script_dir}/support/token_validation.sh"

load_repo_env_if_present

prometheus_url="${PROMETHEUS_URL:-http://host.docker.internal:9090}"
mcp_validate_optional_token "PROMETHEUS_TOKEN" 20 "Prometheus MCP" "eyJ"
mcp_exit_if_validate_only "prometheus"

docker_bin="$(resolve_docker_bin)"
docker_args=(
  run
  --rm
  -i
  -e "PROMETHEUS_URL=${prometheus_url}"
)

if [[ -n "${PROMETHEUS_USERNAME:-}" ]]; then
  docker_args+=(-e "PROMETHEUS_USERNAME=${PROMETHEUS_USERNAME}")
fi
if [[ -n "${PROMETHEUS_PASSWORD:-}" ]]; then
  docker_args+=(-e "PROMETHEUS_PASSWORD=${PROMETHEUS_PASSWORD}")
fi
if [[ -n "${PROMETHEUS_TOKEN:-}" ]]; then
  docker_args+=(-e "PROMETHEUS_TOKEN=${PROMETHEUS_TOKEN}")
fi

exec "${docker_bin}" "${docker_args[@]}" \
  ghcr.io/pab1it0/prometheus-mcp-server \
  "$@"
