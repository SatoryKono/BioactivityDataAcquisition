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

# Prefer a writable npm cache: machine-local .env may point at a foreign home
# (e.g. /home/ubuntu/...) that is not creatable for the current user.
_default_npm_cache="${REPO_ROOT}/.cache/npm-cache"
if [[ -z "${NPM_CONFIG_CACHE:-}" ]]; then
  export NPM_CONFIG_CACHE="${_default_npm_cache}"
elif ! mkdir -p "${NPM_CONFIG_CACHE}" 2>/dev/null; then
  export NPM_CONFIG_CACHE="${_default_npm_cache}"
  mkdir -p "${NPM_CONFIG_CACHE}"
fi
export npm_config_cache="${NPM_CONFIG_CACHE}"
export DEJA_AUTO_RECALL_PATH="${REPO_ROOT}/AGENTS.md"

mcp_exit_if_validate_only "deja"

# Prefer a preinstalled binary (managed install or go install) so launch does
# not depend on npx resolving optional platform packages on every cold start.
if command -v deja >/dev/null 2>&1; then
  exec deja mcp
fi

# Package: @vshulcz/deja-vu (bin: deja). MCP transport is the `mcp` subcommand.
# Keep pin aligned with the optional linux-amd64 package version used in setup.
exec npx -y "@vshulcz/deja-vu@0.17.0" mcp
