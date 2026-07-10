#!/usr/bin/env bash
# Codex compatibility source for the shared WSL proxy helper.

_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
_REPO_ROOT="$(cd "${_SCRIPT_DIR}/../../../.." && pwd)"
_SHARED_HELPER="${_REPO_ROOT}/scripts/engineering/dev/bash/.wsl_proxy_env.sh"

if [[ ! -f "${_SHARED_HELPER}" ]]; then
  echo "[codex-wsl-proxy] ERROR: shared helper not found: ${_SHARED_HELPER}" >&2
  return 1 2>/dev/null || exit 1
fi

# shellcheck source=/dev/null
source "${_SHARED_HELPER}"

if [[ -f "/mnt/c/Windows/System32/cmd.exe" ]]; then
  export BROWSER='/mnt/c/Windows/System32/cmd.exe /c start'
fi
