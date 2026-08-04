#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
package="mcp-mermaid@0.4.1"

# WSL uses the Windows-native browser payload, avoiding Linux system-package
# installation while keeping protocol traffic on stdio for portable configs.
if command -v powershell.exe >/dev/null 2>&1 && command -v wslpath >/dev/null 2>&1; then
  wrapper="$(wslpath -w "${script_dir}/mcp_mermaid_wrapper.ps1")"
  exec powershell.exe -NoLogo -NonInteractive -NoProfile -ExecutionPolicy Bypass \
    -File "${wrapper}" -Transport stdio "$@"
fi

cache_home="${XDG_CACHE_HOME:-${HOME}/.cache}"
export NPM_CONFIG_CACHE="${NPM_CONFIG_CACHE:-${cache_home}/bioetl-mcp/npm-cache}"
export npm_config_ignore_scripts=true
exec npx -y "${package}" --transport stdio "$@"
