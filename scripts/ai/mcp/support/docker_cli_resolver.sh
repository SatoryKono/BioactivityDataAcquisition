#!/usr/bin/env bash
set -euo pipefail

resolve_docker_bin() {
  local candidates=()
  local docker_desktop_default="/mnt/c/Program Files/Docker/Docker/resources/bin/docker.exe"

  local docker_linux
  if command -v docker >/dev/null 2>&1; then
    docker_linux="$(command -v docker)"
  fi

  # Prefer the Linux docker binary when running inside WSL/Unix so we hit the Unix socket
  if [[ -n "${docker_linux}" ]]; then
    candidates+=("${docker_linux}")
  fi

  if [[ -x "${docker_desktop_default}" ]]; then
    candidates+=("${docker_desktop_default}")
  fi

  if command -v docker.exe >/dev/null 2>&1; then
    candidates+=("$(command -v docker.exe)")
  fi
  if command -v docker >/dev/null 2>&1; then
    candidates+=("$(command -v docker)")
  fi
  if command -v cmd.exe >/dev/null 2>&1 && command -v wslpath >/dev/null 2>&1; then
    local docker_win_path
    docker_win_path="$(
      cmd.exe /c where docker 2>/dev/null | tr -d '\r' | grep -m1 'docker' || true
    )"
    if [[ -n "${docker_win_path}" ]]; then
      candidates+=("$(wslpath -u "${docker_win_path}")")
    fi
  fi

  local candidate
  for candidate in "${candidates[@]}"; do
    if "${candidate}" version >/dev/null 2>&1; then
      printf '%s\n' "${candidate}"
      return
    fi
  done

  printf "Docker CLI not found or not working. Install Docker Desktop or enable WSL integration.\n" >&2
  exit 1
}
