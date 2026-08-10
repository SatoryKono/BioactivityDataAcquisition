#!/bin/sh
# Grafana datasource bootstrap (Prometheus + optional BioETL Ops HTTP).
# Loki, Tempo, and Quarantine Explorer were removed from the shipping surface.
#
# Cold-start contract:
# - Prometheus datasource is always provisioned; Grafana always reaches /run.sh
#   unless BIOETL_GRAFANA_REQUIRE_OPS_HTTP=1 and Ops trust cannot be proven.
# - Ops HTTP (Infinity) is fail-closed for *trust panels*: provisioned only when
#   /ops/control-plane/ready reports the expected runtime_source_id.
# - Default poll budget is 30×2s (~60s). Override via
#   BIOETL_GRAFANA_OPS_READY_ATTEMPTS / BIOETL_GRAFANA_OPS_READY_SLEEP_SEC.
set -eu

TARGET_DIR="/etc/grafana/provisioning/datasources"
CORE_DIR="/etc/bioetl-grafana/datasources-core"
STATUS_FILE="${BIOETL_GRAFANA_BOOTSTRAP_STATUS_FILE:-/var/lib/grafana/bioetl-bootstrap-status.json}"
RENDERING_SERVER_URL="${GF_RENDERING_SERVER_URL:-}"
STALE_RENDERER_PLUGIN_DIR="/var/lib/grafana/plugins/grafana-image-renderer"
EXPECTED_RUNTIME_SOURCE_ID="${BIOETL_EXPECTED_RUNTIME_SOURCE_ID:-unmanaged}"
REQUIRE_OPS_HTTP="${BIOETL_GRAFANA_REQUIRE_OPS_HTTP:-0}"
OPS_READY_ATTEMPTS="${BIOETL_GRAFANA_OPS_READY_ATTEMPTS:-30}"
OPS_READY_SLEEP_SEC="${BIOETL_GRAFANA_OPS_READY_SLEEP_SEC:-2}"

# Empty BIOETL_OPS_HTTP_URL (e.g. from a blank host env export) must NOT wipe
# the YAML default — treat empty as unset.
if [ -z "${BIOETL_OPS_HTTP_URL:-}" ]; then
  # Docker-internal compose service name on the monitoring network (ADR-010 local-only).
  BIOETL_OPS_HTTP_URL="http://bioetl:8000"  # NOSONAR - docker-internal service URL
fi
export BIOETL_OPS_HTTP_URL

OPS_HTTP_STATE="deferred"
OPS_HTTP_REASON="not_checked"
SOURCE_ID_MATCHED=0
IDENTITY_VALID=0

write_bootstrap_status() {
  mkdir -p "$(dirname "${STATUS_FILE}")"
  # Minimal JSON (no jq in Grafana image). Values are controlled tokens only.
  cat > "${STATUS_FILE}" <<EOF
{
  "ops_http": "${OPS_HTTP_STATE}",
  "reason": "${OPS_HTTP_REASON}",
  "ops_url": "${BIOETL_OPS_HTTP_URL}",
  "require_ops_http": "${REQUIRE_OPS_HTTP}",
  "expected_runtime_source_id_valid": "${IDENTITY_VALID}",
  "source_id_matched": "${SOURCE_ID_MATCHED}",
  "ready_attempts": "${OPS_READY_ATTEMPTS}",
  "ready_sleep_sec": "${OPS_READY_SLEEP_SEC}"
}
EOF
  echo "[bioetl-grafana] bootstrap status written to ${STATUS_FILE} (ops_http=${OPS_HTTP_STATE})"
}

fail_or_defer_ops() {
  # $1 = reason token
  OPS_HTTP_REASON="$1"
  OPS_HTTP_STATE="deferred"
  if [ "${REQUIRE_OPS_HTTP}" = "1" ]; then
    OPS_HTTP_STATE="failed"
    write_bootstrap_status
    echo "[bioetl-grafana] ERROR: Ops HTTP required but unavailable (${OPS_HTTP_REASON})" >&2
    exit 1
  fi
  echo "[bioetl-grafana] WARN: Ops HTTP deferred (${OPS_HTTP_REASON}); starting Grafana with Prometheus only" >&2
}

# A reachable backend is insufficient: an old checkout can expose a healthy
# bioetl:8000 while serving stale RunManifest/run-report mounts. Require the
# opaque identity injected by runtime_manager before provisioning Ops HTTP.
if [ "${#EXPECTED_RUNTIME_SOURCE_ID}" -eq 64 ] && \
  ! printf '%s' "${EXPECTED_RUNTIME_SOURCE_ID}" | grep -Eq '[^0-9a-f]'; then
  IDENTITY_VALID=1
else
  IDENTITY_VALID=0
fi

if [ "${IDENTITY_VALID}" -ne 1 ]; then
  fail_or_defer_ops "invalid_or_unmanaged_identity"
else
  OPS_READY_URL="${BIOETL_OPS_HTTP_URL%/}/ops/control-plane/ready"
  SOURCE_ID_ATTEMPT=1
  while [ "${SOURCE_ID_ATTEMPT}" -le "${OPS_READY_ATTEMPTS}" ]; do
    # NOSONAR - docker-internal HTTP URL is safe (ADR-010 local-only monitoring network)
    READY_PAYLOAD="$(wget -qO- -T 3 "${OPS_READY_URL}" 2>/dev/null || true)"
    if printf '%s' "${READY_PAYLOAD}" | grep -Eq \
      "\"runtime_source_id\"[[:space:]]*:[[:space:]]*\"${EXPECTED_RUNTIME_SOURCE_ID}\""; then
      SOURCE_ID_MATCHED=1
      break
    fi
    SOURCE_ID_ATTEMPT=$((SOURCE_ID_ATTEMPT + 1))
    if [ "${SOURCE_ID_ATTEMPT}" -le "${OPS_READY_ATTEMPTS}" ]; then
      sleep "${OPS_READY_SLEEP_SEC}"
    fi
  done
  if [ "${SOURCE_ID_MATCHED}" -eq 1 ]; then
    OPS_HTTP_STATE="ready"
    OPS_HTTP_REASON="identity_matched"
    echo "[bioetl-grafana] Ops HTTP identity matched after ${SOURCE_ID_ATTEMPT} attempt(s)"
  else
    fail_or_defer_ops "identity_mismatch_or_timeout"
  fi
fi

mkdir -p "${TARGET_DIR}"
rm -f "${TARGET_DIR}"/*.yml

# Always provision Prometheus. Ops HTTP only when trust is proven.
if [ -f "${CORE_DIR}/prometheus.yml" ]; then
  cp "${CORE_DIR}/prometheus.yml" "${TARGET_DIR}/prometheus.yml"
fi

OPS_HTTP_YML="${TARGET_DIR}/bioetl-ops-http.yml"
if [ "${OPS_HTTP_STATE}" = "ready" ]; then
  # Materialize Ops HTTP URL so Grafana never receives an empty env expansion.
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
    # NOSONAR - docker-internal HTTP URL is safe (ADR-010 local-only monitoring network)
    url: ${BIOETL_OPS_HTTP_URL}
    editable: false
    jsonData:
      allowedHosts:
        # NOSONAR - docker-internal HTTP URL is safe (ADR-010 local-only monitoring network)
        - ${BIOETL_OPS_HTTP_URL}
      auth_method: none
EOF
fi

# Explicitly drop retired / stale datasources that may still exist in grafana-data.
# Always delete Ops HTTP first so a previously provisioned row is replaced only
# when trust is ready (re-created above) or stays removed when deferred.
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
if [ "${OPS_HTTP_STATE}" = "ready" ]; then
  echo "[bioetl-grafana] provisioned Prometheus + BioETL Ops HTTP (no Loki/Tempo/Quarantine Explorer)"
else
  echo "[bioetl-grafana] provisioned Prometheus only (Ops HTTP ${OPS_HTTP_STATE}: ${OPS_HTTP_REASON})"
fi

if [ -n "${RENDERING_SERVER_URL}" ] && [ -d "${STALE_RENDERER_PLUGIN_DIR}" ]; then
  rm -rf "${STALE_RENDERER_PLUGIN_DIR}"
  echo "[bioetl-grafana] removed stale local grafana-image-renderer plugin for remote renderer mode"
fi

# Infinity is required only when Ops HTTP is provisioned. Skip install on the
# deferred path so cold start does not depend on plugin registry access.
INFINITY_PLUGIN_ID="yesoreyeram-infinity-datasource"
INFINITY_PLUGIN_DIR="/var/lib/grafana/plugins/${INFINITY_PLUGIN_ID}"
INFINITY_PLUGIN_VERSION="${BIOETL_INFINITY_PLUGIN_VERSION:-3.8.0}"
if [ "${OPS_HTTP_STATE}" = "ready" ]; then
  INFINITY_INSTALLED_VERSION=""
  if [ -f "${INFINITY_PLUGIN_DIR}/plugin.json" ]; then
    INFINITY_INSTALLED_VERSION="$(
      sed -n 's/^[[:space:]]*"version":[[:space:]]*"\([^"]*\)".*/\1/p' \
        "${INFINITY_PLUGIN_DIR}/plugin.json" | head -n 1
    )"
  fi
  if [ "${INFINITY_INSTALLED_VERSION}" != "${INFINITY_PLUGIN_VERSION}" ]; then
    echo "[bioetl-grafana] installing ${INFINITY_PLUGIN_ID} ${INFINITY_PLUGIN_VERSION} (found ${INFINITY_INSTALLED_VERSION:-missing})"
    rm -rf -- "${INFINITY_PLUGIN_DIR}"
    if ! grafana cli --pluginsDir /var/lib/grafana/plugins plugins install \
      "${INFINITY_PLUGIN_ID}" "${INFINITY_PLUGIN_VERSION}"; then
      if [ "${REQUIRE_OPS_HTTP}" = "1" ]; then
        OPS_HTTP_STATE="failed"
        OPS_HTTP_REASON="infinity_plugin_install_failed"
        write_bootstrap_status
        echo "[bioetl-grafana] ERROR: failed to install ${INFINITY_PLUGIN_ID}" >&2
        exit 1
      fi
      # Soft path: drop Ops HTTP provision file so Grafana does not reference a
      # missing plugin; keep Prometheus-only UI up.
      rm -f "${OPS_HTTP_YML}"
      OPS_HTTP_STATE="deferred"
      OPS_HTTP_REASON="infinity_plugin_install_failed"
      echo "[bioetl-grafana] WARN: Infinity install failed; Ops HTTP not provisioned" >&2
    fi
  fi
fi

write_bootstrap_status
exec /run.sh
