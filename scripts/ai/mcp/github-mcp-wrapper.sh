#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../../.." && pwd)"

# shellcheck source=./support/load_repo_env.sh
export BIOETL_SKIP_ENV_LOCAL=1
source "${SCRIPT_DIR}/support/load_repo_env.sh"
load_repo_env_if_present
unset BIOETL_SKIP_ENV_LOCAL

export NPM_CONFIG_CACHE="${NPM_CONFIG_CACHE:-/tmp/npm-cache}"

# Preserve compatibility with local shells that still export the legacy token name.
if [[ -z "${GITHUB_PERSONAL_ACCESS_TOKEN:-}" && -n "${GITHUB_TOKEN:-}" ]]; then
  export GITHUB_PERSONAL_ACCESS_TOKEN="${GITHUB_TOKEN}"
fi

exec npx -y @modelcontextprotocol/server-github --stdio
