#!/bin/sh
set -e

# Load datasources based on environment
if [ "$BIOETL_ENABLE_TRACING_DATASOURCES" = "auto" ] || [ "$BIOETL_ENABLE_TRACING_DATASOURCES" = "true" ]; then
  export GF_PATHS_PROVISIONING=/etc/bioetl-grafana
else
  # Use only core datasources
  export GF_PATHS_PROVISIONING=/etc/bioetl-grafana
fi

# Call the original Grafana entrypoint
exec /run.sh
