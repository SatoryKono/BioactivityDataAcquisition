#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../../.." && pwd)"

# shellcheck source=./support/load_repo_env.sh
export BIOETL_SKIP_ENV_LOCAL=1
source "${SCRIPT_DIR}/support/load_repo_env.sh"
load_repo_env_if_present
unset BIOETL_SKIP_ENV_LOCAL
# shellcheck source=./support/token_validation.sh
source "${SCRIPT_DIR}/support/token_validation.sh"
# shellcheck source=./support/uv_resolver.sh
source "${SCRIPT_DIR}/support/uv_resolver.sh"

UV_CACHE_DIR="${UV_CACHE_DIR:-${REPO_ROOT}/.cache/uv-cache}"
UV_TOOL_DIR="${UV_TOOL_DIR:-${REPO_ROOT}/.cache/uv-tools}"
export UV_CACHE_DIR UV_TOOL_DIR
export MUTMUT_PROJECT_PATH="${REPO_ROOT}"
mkdir -p "${UV_CACHE_DIR}" "${UV_TOOL_DIR}"

mcp_exit_if_validate_only "mutmut"

UVX_BIN="$(bioetl_resolve_uvx_bin || true)"
if ! command -v "${UVX_BIN}" >/dev/null 2>&1 && [[ ! -x "${UVX_BIN}" ]]; then
  printf '%s\n' \
    "mutmut MCP requires uvx." \
    "Install uv (https://docs.astral.sh/uv/) so uvx is on PATH." >&2
  exit 1
fi

bioetl_enable_uvx_network_bypass
exec "${UVX_BIN}" --from "git+https://github.com/wdm0006/mutmut-mcp@1e3b47ccaaa31f4c651d8e424b90d392d1c1ed90" mutmut-mcp --stdio "$@"
