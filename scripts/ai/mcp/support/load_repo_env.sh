#!/usr/bin/env bash

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../../../.." && pwd)"

# shellcheck source=../../../ops/support/load_repo_env.sh
source "${REPO_ROOT}/scripts/ops/support/load_repo_env.sh"
