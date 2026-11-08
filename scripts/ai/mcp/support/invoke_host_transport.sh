#!/usr/bin/env bash

run_mcp_host_route() {
  local server="$1"
  shift
  local marker="${PC_AGENT_MCP_ROUTES_FILE:-${HOME}/.config/pc-agent/mcp-routes.json}"
  if [[ -z "${PC_AGENT_MCP_ROUTES_FILE:-}" && ! -e "${marker}" && ! -L "${marker}" ]]; then
    return 78
  fi

  local support_dir root pid status=0 signal_status=0
  local route_file="${PC_AGENT_MCP_ROUTES_FILE:-}"
  support_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)" || return 1
  root="$(cd -- "${support_dir}/../../../.." && pwd)" || return 1
  if command -v cygpath >/dev/null 2>&1; then
    root="$(cygpath -w "${root}")" || return 1
    if [[ "${route_file}" == /* ]]; then
      route_file="$(cygpath -w "${route_file}")" || return 1
    fi
  fi

  # Forward the client's signal and wait for Node to finish stopping its adapter.
  trap 'signal_status=143; if [[ -n "${pid:-}" ]]; then kill -TERM "${pid}" 2>/dev/null || true; fi' TERM
  trap 'signal_status=130; if [[ -n "${pid:-}" ]]; then kill -INT "${pid}" 2>/dev/null || true; fi' INT
  PC_AGENT_MCP_ROUTES_FILE="${route_file}" \
  node "${support_dir}/host_transport.mjs" \
    --root "${root}" --server "${server}" -- "$@" <&0 &
  pid=$!
  if [[ "${signal_status}" -ne 0 ]]; then
    kill -TERM "${pid}" 2>/dev/null || true
  fi
  wait "${pid}" || status=$?
  if [[ "${signal_status}" -ne 0 ]]; then
    wait "${pid}" 2>/dev/null || true
    status="${signal_status}"
  fi
  trap - TERM INT
  return "${status}"
}
