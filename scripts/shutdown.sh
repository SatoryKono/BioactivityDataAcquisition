#!/usr/bin/env bash
# Compatibility wrapper. On-demand MCP processes have no Compose lifecycle.
set -euo pipefail
repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
exec bash "${repo_root}/scripts/ops/docker-setup.sh" stop
