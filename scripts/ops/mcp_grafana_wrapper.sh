#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./docker_cli_resolver.sh
source "${script_dir}/docker_cli_resolver.sh"
# shellcheck source=./load_repo_env.sh
source "${script_dir}/load_repo_env.sh"

load_repo_env_if_present

docker_bin="$(resolve_docker_bin)"
grafana_url="${GRAFANA_URL:-http://host.docker.internal:3000}"
docker_args=(
  run
  --rm
  -i
  -e "GRAFANA_URL=${grafana_url}"
)

if [[ -n "${GRAFANA_SERVICE_ACCOUNT_TOKEN:-}" ]]; then
  docker_args+=(-e "GRAFANA_SERVICE_ACCOUNT_TOKEN=${GRAFANA_SERVICE_ACCOUNT_TOKEN}")
fi
if [[ -n "${GRAFANA_USERNAME:-}" ]]; then
  docker_args+=(-e "GRAFANA_USERNAME=${GRAFANA_USERNAME}")
fi
if [[ -n "${GRAFANA_PASSWORD:-}" ]]; then
  docker_args+=(-e "GRAFANA_PASSWORD=${GRAFANA_PASSWORD}")
fi
if [[ -n "${GRAFANA_ORG_ID:-}" ]]; then
  docker_args+=(-e "GRAFANA_ORG_ID=${GRAFANA_ORG_ID}")
fi

exec "${docker_bin}" "${docker_args[@]}" mcp/grafana -t stdio "$@"
