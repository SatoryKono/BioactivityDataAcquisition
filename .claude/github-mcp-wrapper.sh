#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../scripts/ops/load_repo_env.sh
export BIOETL_SKIP_ENV_LOCAL=1
source "${script_dir}/../scripts/ops/load_repo_env.sh"

load_repo_env_if_present
unset BIOETL_SKIP_ENV_LOCAL

if [[ -z "${GITHUB_PERSONAL_ACCESS_TOKEN:-}" ]] && command -v gh >/dev/null 2>&1; then
  export GITHUB_PERSONAL_ACCESS_TOKEN
  GITHUB_PERSONAL_ACCESS_TOKEN="$(gh auth token 2>/dev/null || true)"
fi

exec npx -y @modelcontextprotocol/server-github@2025.4.8 "$@"
