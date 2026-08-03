#!/usr/bin/env bash
set -euo pipefail

_resolve_first_working_docker() {
  local capability="$1"
  shift
  local candidates=("$@")
  local candidate
  for candidate in "${candidates[@]}"; do
    [[ -n "${candidate}" ]] || continue
    if [[ "${capability}" == "engine" ]]; then
      if "${candidate}" version >/dev/null 2>&1; then
        printf '%s\n' "${candidate}"
        return 0
      fi
    elif "${candidate}" version >/dev/null 2>&1 \
      && "${candidate}" mcp gateway --help >/dev/null 2>&1; then
      printf '%s\n' "${candidate}"
      return 0
    fi
  done
  return 1
}

resolve_docker_engine_bin() {
  local candidates=()
  local docker_desktop_default="/mnt/c/Program Files/Docker/Docker/resources/bin/docker.exe"

  if command -v docker >/dev/null 2>&1; then
    candidates+=("$(command -v docker)")
  fi
  if command -v docker.exe >/dev/null 2>&1; then
    candidates+=("$(command -v docker.exe)")
  fi
  if [[ -x "${docker_desktop_default}" ]]; then
    candidates+=("${docker_desktop_default}")
  fi
  if _resolve_first_working_docker engine "${candidates[@]}"; then
    return 0
  fi
  printf "Docker Engine CLI not found or not working. Install Docker or enable WSL integration.\n" >&2
  return 1
}

resolve_docker_mcp_gateway_bin() {
  local candidates=()
  local docker_desktop_default="/mnt/c/Program Files/Docker/Docker/resources/bin/docker.exe"
  [[ -x "${docker_desktop_default}" ]] && candidates+=("${docker_desktop_default}")
  command -v docker.exe >/dev/null 2>&1 && candidates+=("$(command -v docker.exe)")
  if _resolve_first_working_docker mcp-gateway "${candidates[@]}"; then
    return 0
  fi
  printf "Docker Desktop MCP gateway is unavailable; no incompatible Linux CLI fallback was used.\n" >&2
  return 1
}

# Compatibility alias for ordinary engine consumers. Gateway wrappers must use
# resolve_docker_mcp_gateway_bin explicitly.
resolve_docker_bin() {
  resolve_docker_engine_bin
}
