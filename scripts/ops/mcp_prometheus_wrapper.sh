#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./docker_cli_resolver.sh
source "${script_dir}/docker_cli_resolver.sh"
# shellcheck source=./load_repo_env.sh
source "${script_dir}/load_repo_env.sh"

load_repo_env_if_present

docker_bin="$(resolve_docker_bin)"
prometheus_url="${PROMETHEUS_URL:-http://host.docker.internal:9090}"
exec "${docker_bin}" run --rm -i \
  ghcr.io/pab1it0/prometheus-mcp-server \
  --transport stdio \
  --prometheus-url "${prometheus_url}" \
  "$@"
