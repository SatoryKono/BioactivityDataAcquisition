#!/bin/sh
# Grafana datasource bootstrap (Prometheus + optional BioETL Ops HTTP).
# Loki, Tempo, and Quarantine Explorer were removed from the shipping surface.
#
# Fallback contract (default):
# - Grafana UI MUST start (exec /run.sh) even when Ops HTTP / identity / plugin
#   steps fail. Those failures only defer trust datasources.
# - Hard exit 1 only when BIOETL_GRAFANA_REQUIRE_OPS_HTTP=1 and Ops trust cannot
#   be proven (audit/render fail-closed).
# - Ops ready poll default 30×2s (~60s). Override via
#   BIOETL_GRAFANA_OPS_READY_ATTEMPTS / BIOETL_GRAFANA_OPS_READY_SLEEP_SEC.
# - BIOETL_OPS_HTTP_URL is validated before any HTTP probe.
#
# shellcheck disable=SC2039,SC3043
set -u

TARGET_DIR="/etc/grafana/provisioning/datasources"
CORE_DIR="/etc/bioetl-grafana/datasources-core"
STATUS_FILE="${BIOETL_GRAFANA_BOOTSTRAP_STATUS_FILE:-/var/lib/grafana/bioetl-bootstrap-status.json}"
RENDERING_SERVER_URL="${GF_RENDERING_SERVER_URL:-}"
STALE_RENDERER_PLUGIN_DIR="/var/lib/grafana/plugins/grafana-image-renderer"
EXPECTED_RUNTIME_SOURCE_ID="${BIOETL_EXPECTED_RUNTIME_SOURCE_ID:-unmanaged}"
REQUIRE_OPS_HTTP="${BIOETL_GRAFANA_REQUIRE_OPS_HTTP:-0}"
OPS_READY_ATTEMPTS="${BIOETL_GRAFANA_OPS_READY_ATTEMPTS:-30}"
OPS_READY_SLEEP_SEC="${BIOETL_GRAFANA_OPS_READY_SLEEP_SEC:-2}"

if [ -z "${BIOETL_OPS_HTTP_URL:-}" ]; then
  # Docker-internal compose service name on the monitoring network (ADR-010 local-only).
  BIOETL_OPS_HTTP_URL="http://bioetl:8000"  # NOSONAR - docker-internal service URL
fi
export BIOETL_OPS_HTTP_URL

OPS_HTTP_STATE="deferred"
OPS_HTTP_REASON="not_checked"
OPS_HTTP_URL_VALID=0
SOURCE_ID_MATCHED=0
IDENTITY_VALID=0
BOOTSTRAP_ERRORS=0

log() { echo "[bioetl-grafana] $*"; }
log_warn() { echo "[bioetl-grafana] WARN: $*" >&2; }
log_err() { echo "[bioetl-grafana] ERROR: $*" >&2; }

note_error() {
  BOOTSTRAP_ERRORS=$((BOOTSTRAP_ERRORS + 1))
  log_warn "$1"
}

# Validate Ops HTTP base URL before any wget/HTTP call.
is_valid_ops_http_url() {
  _url="$1"
  if [ -z "${_url}" ]; then
    return 1
  fi
  if printf '%s' "${_url}" | grep -Eq '[[:space:]]'; then
    return 1
  fi
  case "${_url}" in
    http://|https://|http:///|https:///) return 1 ;;
  esac
  if ! printf '%s' "${_url}" | grep -Eq \
    '^https?://([A-Za-z0-9._-]+|\[[0-9a-fA-F:.]+\])(:[0-9]{1,5})?(/[^[:space:]]*)?$'; then
    return 1
  fi
  if printf '%s' "${_url}" | grep -Eq '^https?://[^/]*@'; then
    return 1
  fi
  return 0
}

write_bootstrap_status() {
  status_dir="$(dirname "${STATUS_FILE}")"
  if ! mkdir -p "${status_dir}" 2>/dev/null; then
    log_warn "cannot create status dir ${status_dir}"
    return 0
  fi
  cat > "${STATUS_FILE}" <<EOF || log_warn "cannot write ${STATUS_FILE}"
{
  "ops_http": "${OPS_HTTP_STATE}",
  "reason": "${OPS_HTTP_REASON}",
  "ops_url": "${BIOETL_OPS_HTTP_URL}",
  "ops_url_valid": "${OPS_HTTP_URL_VALID}",
  "require_ops_http": "${REQUIRE_OPS_HTTP}",
  "expected_runtime_source_id_valid": "${IDENTITY_VALID}",
  "source_id_matched": "${SOURCE_ID_MATCHED}",
  "ready_attempts": "${OPS_READY_ATTEMPTS}",
  "ready_sleep_sec": "${OPS_READY_SLEEP_SEC}",
  "bootstrap_errors": "${BOOTSTRAP_ERRORS}"
}
EOF
  log "bootstrap status written to ${STATUS_FILE} (ops_http=${OPS_HTTP_STATE})"
}

fail_or_defer_ops() {
  OPS_HTTP_REASON="$1"
  OPS_HTTP_STATE="deferred"
  if [ "${REQUIRE_OPS_HTTP}" = "1" ]; then
    OPS_HTTP_STATE="failed"
    write_bootstrap_status
    log_err "Ops HTTP required but unavailable (${OPS_HTTP_REASON})"
    exit 1
  fi
  log_warn "Ops HTTP deferred (${OPS_HTTP_REASON}); continuing with Prometheus-only fallback"
}

provision_prometheus_only() {
  if ! mkdir -p "${TARGET_DIR}" 2>/dev/null; then
    note_error "cannot create ${TARGET_DIR}"
    return 1
  fi
  rm -f "${TARGET_DIR}"/*.yml 2>/dev/null || true
  if [ -f "${CORE_DIR}/prometheus.yml" ]; then
    if ! cp "${CORE_DIR}/prometheus.yml" "${TARGET_DIR}/prometheus.yml" 2>/dev/null; then
      note_error "failed to copy prometheus.yml"
      return 1
    fi
  else
    note_error "missing ${CORE_DIR}/prometheus.yml"
    return 1
  fi
  cat > "${TARGET_DIR}/00-retired-prune.yml" <<'EOF' || note_error "failed to write prune yaml"
apiVersion: 1

deleteDatasources:
  - name: Loki
  - name: Tempo
  - name: Quarantine Explorer
  - name: BioETL Ops HTTP
    orgId: 1
EOF
  return 0
}

provision_ops_http() {
  OPS_HTTP_YML="${TARGET_DIR}/bioetl-ops-http.yml"
  cat > "${OPS_HTTP_YML}" <<EOF || return 1
apiVersion: 1

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
  return 0
}

ensure_infinity_plugin() {
  INFINITY_PLUGIN_ID="yesoreyeram-infinity-datasource"
  INFINITY_PLUGIN_DIR="/var/lib/grafana/plugins/${INFINITY_PLUGIN_ID}"
  INFINITY_PLUGIN_VERSION="${BIOETL_INFINITY_PLUGIN_VERSION:-3.8.0}"
  INFINITY_INSTALLED_VERSION=""
  if [ -f "${INFINITY_PLUGIN_DIR}/plugin.json" ]; then
    INFINITY_INSTALLED_VERSION="$(
      sed -n 's/^[[:space:]]*"version":[[:space:]]*"\([^"]*\)".*/\1/p' \
        "${INFINITY_PLUGIN_DIR}/plugin.json" 2>/dev/null | head -n 1
    )" || INFINITY_INSTALLED_VERSION=""
  fi
  if [ "${INFINITY_INSTALLED_VERSION}" = "${INFINITY_PLUGIN_VERSION}" ]; then
    return 0
  fi
  log "installing ${INFINITY_PLUGIN_ID} ${INFINITY_PLUGIN_VERSION} (found ${INFINITY_INSTALLED_VERSION:-missing})"
  rm -rf -- "${INFINITY_PLUGIN_DIR}" 2>/dev/null || true
  if grafana cli --pluginsDir /var/lib/grafana/plugins plugins install \
    "${INFINITY_PLUGIN_ID}" "${INFINITY_PLUGIN_VERSION}"; then
    return 0
  fi
  return 1
}

# --- URL gate: never issue HTTP without a validated base URL ---
if is_valid_ops_http_url "${BIOETL_OPS_HTTP_URL}"; then
  OPS_HTTP_URL_VALID=1
else
  OPS_HTTP_URL_VALID=0
  note_error "invalid BIOETL_OPS_HTTP_URL (refusing HTTP probe)"
  fail_or_defer_ops "invalid_ops_http_url"
fi

# --- identity / Ops ready gate (soft by default; skipped if URL invalid) ---
if [ "${OPS_HTTP_URL_VALID}" -eq 1 ]; then
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
    if ! printf '%s' "${OPS_READY_URL}" | grep -Eq \
      '^https?://([A-Za-z0-9._-]+|\[[0-9a-fA-F:.]+\])(:[0-9]{1,5})?(/[^[:space:]]*)?$'; then
      note_error "refusing HTTP probe: derived ready URL failed validation"
      fail_or_defer_ops "invalid_ops_ready_url"
    else
      SOURCE_ID_ATTEMPT=1
      SEEN_FOREIGN_IDENTITY=0
      while [ "${SOURCE_ID_ATTEMPT}" -le "${OPS_READY_ATTEMPTS}" ]; do
        # NOSONAR - docker-internal HTTP URL is safe (ADR-010 local-only monitoring network)
        READY_PAYLOAD="$(wget -qO- -T 3 "${OPS_READY_URL}" 2>/dev/null || true)"
        if printf '%s' "${READY_PAYLOAD}" | grep -Eq \
          "\"runtime_source_id\"[[:space:]]*:[[:space:]]*\"${EXPECTED_RUNTIME_SOURCE_ID}\""; then
          SOURCE_ID_MATCHED=1
          break
        fi
        if printf '%s' "${READY_PAYLOAD}" | grep -Eq \
          '"runtime_source_id"[[:space:]]*:[[:space:]]*"[0-9a-f]{64}"'; then
          SEEN_FOREIGN_IDENTITY=1
          log_warn "Ops HTTP ready returned a different runtime_source_id (foreign origin)"
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
        log "Ops HTTP identity matched after ${SOURCE_ID_ATTEMPT} attempt(s)"
      elif [ "${SEEN_FOREIGN_IDENTITY}" -eq 1 ]; then
        fail_or_defer_ops "identity_mismatch"
      else
        fail_or_defer_ops "identity_timeout_or_unreachable"
      fi
    fi
  fi
fi

if ! provision_prometheus_only; then
  note_error "Prometheus provisioning incomplete; Grafana will still start"
fi

if [ "${OPS_HTTP_STATE}" = "ready" ]; then
  if ! provision_ops_http; then
    note_error "failed to materialize Ops HTTP datasource"
    OPS_HTTP_STATE="deferred"
    OPS_HTTP_REASON="ops_http_provision_failed"
  elif ! ensure_infinity_plugin; then
    if [ "${REQUIRE_OPS_HTTP}" = "1" ]; then
      OPS_HTTP_STATE="failed"
      OPS_HTTP_REASON="infinity_plugin_install_failed"
      write_bootstrap_status
      log_err "failed to install yesoreyeram-infinity-datasource"
      exit 1
    fi
    rm -f "${TARGET_DIR}/bioetl-ops-http.yml" 2>/dev/null || true
    OPS_HTTP_STATE="deferred"
    OPS_HTTP_REASON="infinity_plugin_install_failed"
    log_warn "Infinity install failed; Ops HTTP not provisioned (Prometheus-only fallback)"
  fi
fi

log "Ops HTTP URL=${BIOETL_OPS_HTTP_URL}"  # NOSONAR - docker-internal URL echo
if [ "${OPS_HTTP_STATE}" = "ready" ]; then
  log "provisioned Prometheus + BioETL Ops HTTP (no Loki/Tempo/Quarantine Explorer)"
else
  log "provisioned Prometheus-only fallback (Ops HTTP ${OPS_HTTP_STATE}: ${OPS_HTTP_REASON})"
fi

if [ -n "${RENDERING_SERVER_URL}" ] && [ -d "${STALE_RENDERER_PLUGIN_DIR}" ]; then
  rm -rf "${STALE_RENDERER_PLUGIN_DIR}" 2>/dev/null || true
  log "removed stale local grafana-image-renderer plugin for remote renderer mode"
fi

write_bootstrap_status

if [ ! -x /run.sh ] && [ ! -f /run.sh ]; then
  log_err "/run.sh missing; cannot start Grafana"
  exit 1
fi
log "starting Grafana (/run.sh) with ops_http=${OPS_HTTP_STATE}"
exec /run.sh
