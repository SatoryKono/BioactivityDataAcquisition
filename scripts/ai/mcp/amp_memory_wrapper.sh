#!/usr/bin/env bash
# Discard foreign orb environment overrides before starting shared memory MCP.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
if [[ -n "${MEMORY_FILE_PATH:-}" ]]; then
  resolved_target="$(realpath -m -- "${MEMORY_FILE_PATH}")"
  case "${resolved_target}" in
    "${REPO_ROOT}/.cache/mcp-memory"|"${REPO_ROOT}/.cache/mcp-memory"/*) ;;
    *)
      printf '%s\n' 'Amp memory: ignoring inherited MEMORY_FILE_PATH outside the repository MCP cache' >&2
      unset MEMORY_FILE_PATH
      ;;
  esac
fi
exec bash "${SCRIPT_DIR}/mcp_memory_wrapper.sh" "$@"
