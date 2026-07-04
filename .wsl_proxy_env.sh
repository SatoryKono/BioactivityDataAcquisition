#!/usr/bin/env bash
# Root compatibility shim for the canonical Codex WSL proxy helper.

_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
_CANONICAL_HELPER="${_SCRIPT_DIR}/scripts/ai/codex/helper/wsl_proxy_env.sh"

if [[ ! -f "${_CANONICAL_HELPER}" ]]; then
  echo "[root-wsl-proxy] ERROR: canonical helper not found: ${_CANONICAL_HELPER}" >&2
  return 1 2>/dev/null || exit 1
fi

# shellcheck source=/dev/null
source "${_CANONICAL_HELPER}"
