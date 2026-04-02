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

if [[ -z "${BRAVE_API_KEY:-}" ]]; then
  printf "BRAVE_API_KEY is required for brave-search MCP.\n" >&2
  exit 1
fi

docker_bin="$(resolve_docker_bin)"
exec "${docker_bin}" run --rm -i \
  -e "BRAVE_API_KEY=${BRAVE_API_KEY}" \
  mcp/brave-search "$@"
