#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../../.." && pwd)"
export UV_CACHE_DIR="${UV_CACHE_DIR:-${REPO_ROOT}/.cache/uv-cache}"
export UV_TOOL_DIR="${UV_TOOL_DIR:-${REPO_ROOT}/.cache/uv-tools}"
mkdir -p "${UV_CACHE_DIR}" "${UV_TOOL_DIR}"

# shellcheck source=./support/token_validation.sh
source "${SCRIPT_DIR}/support/token_validation.sh"
# shellcheck source=./support/uv_resolver.sh
source "${SCRIPT_DIR}/support/uv_resolver.sh"
mcp_exit_if_validate_only "fetch"

# Canonical transport: PyPI package via uvx (pinned in repo MCP policy).
# Do NOT use npm package "mcp-server-fetch" — registry copy 0.0.2 is a
# security-research canary, not a production MCP server.
UVX_BIN="$(bioetl_resolve_uvx_bin || true)"
if ! command -v "${UVX_BIN}" >/dev/null 2>&1 && [[ ! -x "${UVX_BIN}" ]]; then
  printf '%s\n' \
    "fetch MCP requires uvx with the PyPI package mcp-server-fetch==2025.4.7." \
    "Install uv (https://docs.astral.sh/uv/) so uvx is on PATH." \
    "Do not use npm package mcp-server-fetch (canary / not production)." >&2
  exit 1
fi

bioetl_enable_uvx_network_bypass
exec "${UVX_BIN}" --python 3.13 --with "mcp<2" \
  --from "mcp-server-fetch==2025.4.7" mcp-server-fetch
