#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./support/docker_cli_resolver.sh
source "${script_dir}/support/docker_cli_resolver.sh"

docker_bin="$(resolve_docker_bin)"
exec "${docker_bin}" mcp gateway run --servers mermaid --transport stdio "$@"
