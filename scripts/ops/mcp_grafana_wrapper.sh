#!/usr/bin/env bash
set -euo pipefail

export NPM_CONFIG_CACHE="${NPM_CONFIG_CACHE:-/tmp/npm-cache}"
export GRAFANA_URL="${GRAFANA_URL:-http://localhost:3000}"

if [[ -z "${GRAFANA_SERVICE_ACCOUNT_TOKEN:-}" ]]; then
  export GRAFANA_USERNAME="${GRAFANA_USERNAME:-admin}"
  export GRAFANA_PASSWORD="${GRAFANA_PASSWORD:-${GF_SECURITY_ADMIN_PASSWORD:-change_me}}"
fi

exec npx -y "mcp-grafana-npx@1.0.1"
