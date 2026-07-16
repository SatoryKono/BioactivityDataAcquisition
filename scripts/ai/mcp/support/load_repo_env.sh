#!/usr/bin/env bash

_BIOETL_MCP_SUPPORT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
_BIOETL_MCP_REPO_ROOT="$(cd -- "${_BIOETL_MCP_SUPPORT_DIR}/../../../.." && pwd)"

# shellcheck source=../../../ops/support/load_repo_env.sh
source "${_BIOETL_MCP_REPO_ROOT}/scripts/ops/support/load_repo_env.sh"

unset _BIOETL_MCP_SUPPORT_DIR _BIOETL_MCP_REPO_ROOT
