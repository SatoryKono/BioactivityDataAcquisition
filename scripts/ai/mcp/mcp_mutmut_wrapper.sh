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

UV_CACHE_DIR="${UV_CACHE_DIR:-${REPO_ROOT}/.cache/uv-cache}"
UV_TOOL_DIR="${UV_TOOL_DIR:-${REPO_ROOT}/.cache/uv-tools}"
export UV_CACHE_DIR UV_TOOL_DIR
export MUTMUT_PROJECT_PATH="${REPO_ROOT}"

mcp_exit_if_validate_only "mutmut"

if command -v uvx >/dev/null 2>&1; then
  exec uvx --from "git+https://github.com/wdm0006/mutmut-mcp" mutmut-mcp --stdio "$@"
fi

if command -v python3 >/dev/null 2>&1; then
  if python3 -c "import importlib.util; raise SystemExit(0 if importlib.util.find_spec('uv') else 1)"; then
    exec python3 -m uv tool run --from "git+https://github.com/wdm0006/mutmut-mcp" mutmut-mcp --stdio "$@"
  fi
fi

printf '%s\n' "mutmut MCP requires uvx (or python -m uv). Install uv: https://docs.astral.sh/uv/getting-started/installation/" >&2
exit 1
