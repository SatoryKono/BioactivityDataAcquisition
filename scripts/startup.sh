#!/usr/bin/env bash
# Compatibility wrapper. MCP servers are on-demand processes.
set -euo pipefail

environment="${1:-dev}"
repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ "${environment}" == "prod" ]]; then
  exec bash "${repo_root}/scripts/ops/docker-setup.sh" start
fi
exec bash "${repo_root}/scripts/ai/mcp/check.sh"
