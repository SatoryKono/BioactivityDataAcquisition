#!/usr/bin/env bash
set -euo pipefail

resolve_docker_bin() {
  if command -v docker >/dev/null 2>&1; then
    command -v docker
    return
  fi
  if command -v docker.exe >/dev/null 2>&1; then
    command -v docker.exe
    return
  fi
  if command -v cmd.exe >/dev/null 2>&1 && command -v wslpath >/dev/null 2>&1; then
    local docker_win_path
    docker_win_path="$(
      cmd.exe /c where docker 2>/dev/null | tr -d '\r' | grep -m1 'docker' || true
    )"
    if [[ -n "${docker_win_path}" ]]; then
      wslpath -u "${docker_win_path}"
      return
    fi
  fi
  printf "Docker CLI not found. Install Docker Desktop or enable WSL integration.\n" >&2
  exit 1
}

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
