#!/bin/sh
# Grafana datasource bootstrap (Prometheus + BioETL Ops HTTP).
# Loki, Tempo, and Quarantine Explorer were removed from the shipping surface.
set -eu

TARGET_DIR="/etc/grafana/provisioning/datasources"
CORE_DIR="/etc/bioetl-grafana/datasources-core"
RENDERING_SERVER_URL="${GF_RENDERING_SERVER_URL:-}"
STALE_RENDERER_PLUGIN_DIR="/var/lib/grafana/plugins/grafana-image-renderer"

mkdir -p "${TARGET_DIR}"
rm -f "${TARGET_DIR}"/*.yml
cp "${CORE_DIR}"/*.yml "${TARGET_DIR}/"

# Explicitly drop retired datasources that may still exist in grafana-data volume.
cat > "${TARGET_DIR}/retired-prune.yml" <<'EOF'
apiVersion: 1

deleteDatasources:
  - name: Loki
  - name: Tempo
  - name: Quarantine Explorer
EOF

echo "[bioetl-grafana] provisioned Prometheus + BioETL Ops HTTP (no Loki/Tempo/Quarantine Explorer)"

if [ -n "${RENDERING_SERVER_URL}" ] && [ -d "${STALE_RENDERER_PLUGIN_DIR}" ]; then
  rm -rf "${STALE_RENDERER_PLUGIN_DIR}"
  echo "[bioetl-grafana] removed stale local grafana-image-renderer plugin for remote renderer mode"
fi

exec /run.sh
