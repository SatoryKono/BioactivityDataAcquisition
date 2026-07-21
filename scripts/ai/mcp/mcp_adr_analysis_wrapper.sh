#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../../.." && pwd)"

# shellcheck source=./support/load_repo_env.sh
export BIOETL_SKIP_ENV_LOCAL=1
source "${SCRIPT_DIR}/support/load_repo_env.sh"
load_repo_env_if_present
unset BIOETL_SKIP_ENV_LOCAL

# ADR analysis configuration
export PROJECT_PATH="${REPO_ROOT}"
export ADR_PATH="${REPO_ROOT}/docs/02-architecture/decisions"

exec npx -y @modelcontextprotocol/server-adr-analysis --stdio
