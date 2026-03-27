#!/bin/sh
set -eu

TARGET_DIR="/etc/grafana/provisioning/datasources"
CORE_DIR="/etc/bioetl-grafana/datasources-core"
TRACING_DIR="/etc/bioetl-grafana/datasources-tracing"
PRUNE_FILE="${TARGET_DIR}/tracing-prune.yml"
TRACING_FLAG="$(printf '%s' "${BIOETL_ENABLE_TRACING_DATASOURCES:-false}" | tr -d '\r' | xargs)"

mkdir -p "${TARGET_DIR}"
rm -f "${TARGET_DIR}"/*.yml
cp "${CORE_DIR}"/*.yml "${TARGET_DIR}/"

if [ "${TRACING_FLAG}" = "true" ]; then
  cp "${TRACING_DIR}"/*.yml "${TARGET_DIR}/"
  echo "[bioetl-grafana] tracing datasources enabled"
else
  cat > "${PRUNE_FILE}" <<'EOF'
apiVersion: 1

deleteDatasources:
  - name: Loki
  - name: Tempo
EOF
  echo "[bioetl-grafana] tracing datasources disabled"
fi

exec /run.sh
