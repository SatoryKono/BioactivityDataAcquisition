#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./support/token_validation.sh
source "${SCRIPT_DIR}/support/token_validation.sh"
# shellcheck source=./support/exec_windows_ps1_wrapper.sh
source "${SCRIPT_DIR}/support/exec_windows_ps1_wrapper.sh"
mcp_exit_if_validate_only "filesystem"
mcp_exec_windows_ps1_wrapper \
  "mcp_filesystem_wrapper.ps1" \
  "Filesystem MCP requires the registered Windows owner."
