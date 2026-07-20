#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../../.." && pwd)"

# shellcheck source=./support/load_repo_env.sh
export BIOETL_SKIP_ENV_LOCAL=1
source "${SCRIPT_DIR}/support/load_repo_env.sh"
load_repo_env_if_present
unset BIOETL_SKIP_ENV_LOCAL

# Check if uvx is available, fallback to python3 -m uv
if command -v uvx &> /dev/null; then
    UV_CMD="uvx"
elif command -v python3 &> /dev/null; then
    UV_CMD="python3 -m uv"
else
    echo "Error: Neither uvx nor python3 with uv module found" >&2
    exit 1
fi

# Mutmut MCP configuration
export MUTMUT_PROJECT_PATH="${REPO_ROOT}"

exec ${UV_CMD} --from "git+https://github.com/wdm0006/mutmut-mcp" mutmut-mcp --stdio