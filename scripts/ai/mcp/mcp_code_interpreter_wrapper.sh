#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../../.." && pwd)"
export UV_CACHE_DIR="${UV_CACHE_DIR:-${REPO_ROOT}/.cache/uv-cache}"
export UV_TOOL_DIR="${UV_TOOL_DIR:-${REPO_ROOT}/.cache/uv-tools}"
export DENO_DIR="${DENO_DIR:-${HOME}/.cache/deno}"
mkdir -p "${UV_CACHE_DIR}" "${UV_TOOL_DIR}" "${DENO_DIR}"

# shellcheck source=./support/token_validation.sh
source "${SCRIPT_DIR}/support/token_validation.sh"
# shellcheck source=./support/uv_resolver.sh
source "${SCRIPT_DIR}/support/uv_resolver.sh"
mcp_exit_if_validate_only "mcp-code-interpreter"

# 1) Local Python module if installed (no Deno required)
if command -v python3 >/dev/null 2>&1 \
  && python3 -c "import importlib.util; raise SystemExit(0 if importlib.util.find_spec('mcp_server_code_interpreter') else 1)"; then
  exec python3 -m mcp_server_code_interpreter "$@"
fi

# 2) Canonical: PyPI mcp-run-python (sandboxed Python code execution MCP)
# mcp-run-python requires Deno, but the local Python module above does not.
UVX_BIN="$(bioetl_resolve_uvx_bin || true)"
if command -v "${UVX_BIN}" >/dev/null 2>&1 || [[ -x "${UVX_BIN}" ]]; then
  # Deno setup only for mcp-run-python branch
  if [[ -d "${HOME}/.deno/bin" ]]; then
    export PATH="${HOME}/.deno/bin:${PATH}"
  fi

  if ! command -v deno >/dev/null 2>&1; then
    printf '%s\n' \
      "mcp-code-interpreter requires Deno for the mcp-run-python fallback." \
      "Install deno into ~/.deno/bin first." >&2
    exit 1
  fi

  bioetl_enable_uvx_network_bypass
  exec "${UVX_BIN}" --from "mcp-run-python==0.0.22" mcp-run-python stdio
fi

printf '%s\n' \
  "mcp-code-interpreter could not start." \
  "Install uv so uvx is on PATH; wrapper runs mcp-run-python==0.0.22 in stdio mode." >&2
exit 1
