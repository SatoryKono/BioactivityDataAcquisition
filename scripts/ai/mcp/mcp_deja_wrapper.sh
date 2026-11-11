#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./support/token_validation.sh
source "${SCRIPT_DIR}/support/token_validation.sh"
mcp_exit_if_validate_only "deja"

deja_profile="${BIOETL_DEJA_PROFILE:-}"
if [[ ! "$deja_profile" =~ ^[a-z][a-z0-9-]{1,47}$ ]]; then
  printf '%s
' 'Deja MCP requires an explicitly registered isolated profile.' >&2
  exit 1
fi

if command -v cygpath >/dev/null 2>&1; then
  wrapper="$(cygpath -aw "${SCRIPT_DIR}/mcp_deja_wrapper.ps1")"
elif command -v wslpath >/dev/null 2>&1; then
  wrapper="$(wslpath -aw "${SCRIPT_DIR}/mcp_deja_wrapper.ps1")"
else
  printf '%s\n' 'Deja MCP requires an explicitly registered isolated profile.' >&2
  exit 1
fi
if ! command -v powershell.exe >/dev/null 2>&1; then
  printf '%s\n' 'Deja MCP requires an explicitly registered isolated profile.' >&2
  exit 1
fi
exec powershell.exe -NoProfile -NonInteractive -File "${wrapper}" -DejaProfileName "$deja_profile"
