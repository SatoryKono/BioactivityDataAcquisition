#!/usr/bin/env bash
set -euo pipefail

export NPM_CONFIG_CACHE="${NPM_CONFIG_CACHE:-/tmp/npm-cache}"
export PROMETHEUS_URL="${PROMETHEUS_URL:-http://localhost:9090}"

exec npx -y "prometheus-mcp@1.1.3" stdio
