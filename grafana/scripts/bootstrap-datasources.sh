#!/bin/sh
# Grafana datasource bootstrap (Prometheus + BioETL Ops HTTP).
# Loki, Tempo, and Quarantine Explorer were removed from the shipping surface.
set -eu

TARGET_DIR="/etc/grafana/provisioning/datasources"
CORE_DIR="/etc/bioetl-grafana/datasources-core"
RENDERING_SERVER_URL="${GF_RENDERING_SERVER_URL:-}"
STALE_RENDERER_PLUGIN_DIR="/var/lib/grafana/plugins/grafana-image-renderer"

# Empty BIOETL_OPS_HTTP_URL (e.g. from a blank host env export) must NOT wipe
# the YAML default — treat empty as unset.
if [ -z "${BIOETL_OPS_HTTP_URL:-}" ]; then
  # Docker-internal compose service name on the monitoring network (ADR-010 local-only).
  BIOETL_OPS_HTTP_URL="http://bioetl:8000"  # NOSONAR - docker-internal service URL
fi
export BIOETL_OPS_HTTP_URL

mkdir -p "${TARGET_DIR}"
rm -f "${TARGET_DIR}"/*.yml
cp "${CORE_DIR}"/*.yml "${TARGET_DIR}/"

# Materialize Ops HTTP URL into the provisioned file so Grafana never receives
# an empty ${BIOETL_OPS_HTTP_URL} expansion (stale volume / empty env edge cases).
OPS_HTTP_YML="${TARGET_DIR}/bioetl-ops-http.yml"
if [ -f "${OPS_HTTP_YML}" ]; then
  cat > "${OPS_HTTP_YML}" <<EOF
apiVersion: 1

# HTTP Infinity datasource for control-plane identity helpers on the main
# bioetl health server (:8000). Replaces the removed Quarantine Explorer UI.
# URL is materialized at bootstrap (not left as an empty env expansion).
datasources:
  - name: BioETL Ops HTTP
    type: yesoreyeram-infinity-datasource
    uid: bioetl-ops-http
    access: proxy
    url: ${BIOETL_OPS_HTTP_URL}
    editable: false
    jsonData:
      allowedHosts:
        - ${BIOETL_OPS_HTTP_URL}
      auth_method: none
EOF
fi

# Explicitly drop retired / stale datasources that may still exist in grafana-data.
# Delete Ops HTTP first (filename sorts before bioetl-ops-http.yml) so a previously
# provisioned empty-url row is replaced on the subsequent create.
cat > "${TARGET_DIR}/00-retired-prune.yml" <<'EOF'
apiVersion: 1

deleteDatasources:
  - name: Loki
  - name: Tempo
  - name: Quarantine Explorer
  - name: BioETL Ops HTTP
    orgId: 1
EOF

# docker-internal URL only (BIOETL_OPS_HTTP_URL defaults above; not a public clear-text edge)
echo "[bioetl-grafana] Ops HTTP URL=${BIOETL_OPS_HTTP_URL}"  # NOSONAR - docker-internal URL echo
echo "[bioetl-grafana] provisioned Prometheus + BioETL Ops HTTP (no Loki/Tempo/Quarantine Explorer)"

if [ -n "${RENDERING_SERVER_URL}" ] && [ -d "${STALE_RENDERER_PLUGIN_DIR}" ]; then
  rm -rf "${STALE_RENDERER_PLUGIN_DIR}"
  echo "[bioetl-grafana] removed stale local grafana-image-renderer plugin for remote renderer mode"
fi

exec /run.sh
