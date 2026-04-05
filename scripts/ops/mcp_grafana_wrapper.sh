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
grafana_username=""
grafana_password=""

if [[ -n "${GRAFANA_USERNAME:-}" && -n "${GRAFANA_PASSWORD:-}" ]]; then
  grafana_username="${GRAFANA_USERNAME}"
  grafana_password="${GRAFANA_PASSWORD}"
elif [[ -n "${GRAFANA_ADMIN_USER:-}" && -n "${GRAFANA_ADMIN_PASSWORD:-}" ]]; then
  grafana_username="${GRAFANA_ADMIN_USER}"
  grafana_password="${GRAFANA_ADMIN_PASSWORD}"
fi
docker_args=(
  run
  --rm
  -i
  -e "GRAFANA_URL=${grafana_url}"
)

if [[ -n "${GRAFANA_SERVICE_ACCOUNT_TOKEN:-}" ]]; then
  docker_args+=(-e "GRAFANA_SERVICE_ACCOUNT_TOKEN=${GRAFANA_SERVICE_ACCOUNT_TOKEN}")
fi
if [[ -n "${grafana_username}" ]]; then
  docker_args+=(-e "GRAFANA_USERNAME=${grafana_username}")
fi
if [[ -n "${grafana_password}" ]]; then
  docker_args+=(-e "GRAFANA_PASSWORD=${grafana_password}")
fi
if [[ -n "${GRAFANA_ORG_ID:-}" ]]; then
  docker_args+=(-e "GRAFANA_ORG_ID=${GRAFANA_ORG_ID}")
fi

exec "${docker_bin}" "${docker_args[@]}" mcp/grafana -t stdio "$@"
