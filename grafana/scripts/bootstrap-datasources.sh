#!/bin/sh
set -eu

TARGET_DIR="/etc/grafana/provisioning/datasources"
CORE_DIR="/etc/bioetl-grafana/datasources-core"
TRACING_DIR="/etc/bioetl-grafana/datasources-tracing"
PRUNE_FILE="${TARGET_DIR}/tracing-prune.yml"
TRACING_FLAG="$(printf '%s' "${BIOETL_ENABLE_TRACING_DATASOURCES:-auto}" | tr -d '\r' | xargs)"
# Loki intentionally keeps /ready false while its ingester settles after startup.
AUTO_WAIT_SECONDS=30
AUTO_POLL_SECONDS=1
RENDERING_SERVER_URL="${GF_RENDERING_SERVER_URL:-}"
STALE_RENDERER_PLUGIN_DIR="/var/lib/grafana/plugins/grafana-image-renderer"
ENABLE_LOKI="false"
ENABLE_TEMPO="false"

# probe_ready checks whether a URL is reachable within the requested timeout, capped at two seconds.
probe_ready() {
  requested_timeout="${2:-2}"
  probe_timeout=2
  if [ "${requested_timeout}" -lt "${probe_timeout}" ]; then
    probe_timeout="${requested_timeout}"
  fi
  wget --quiet --tries=1 --timeout="${probe_timeout}" -O /dev/null "$1"
}

remaining_auto_wait_seconds() {
  now="$(date +%s)"
  remaining=$((deadline - now))
  if [ "${remaining}" -gt 0 ]; then
    printf '%s\n' "${remaining}"
  else
    printf '%s\n' 0
  fi
}

# wait_for_auto_tracing_ready detects Loki and Tempo readiness within the automatic detection window and updates their enablement flags.
wait_for_auto_tracing_ready() {
  deadline=$(($(date +%s) + AUTO_WAIT_SECONDS))

  while :; do
    remaining="$(remaining_auto_wait_seconds)"
    [ "${remaining}" -gt 0 ] || break
    if [ "${ENABLE_LOKI}" != "true" ] && probe_ready "http://loki:3100/ready" "${remaining}" 2>/dev/null; then
      ENABLE_LOKI="true"
      echo "[bioetl-grafana] detected Loki ready"
    fi

    remaining="$(remaining_auto_wait_seconds)"
    [ "${remaining}" -gt 0 ] || break
    if [ "${ENABLE_TEMPO}" != "true" ] && probe_ready "http://tempo:3200/ready" "${remaining}" 2>/dev/null; then
      ENABLE_TEMPO="true"
      echo "[bioetl-grafana] detected Tempo ready"
    fi
    if [ "${ENABLE_LOKI}" = "true" ] && [ "${ENABLE_TEMPO}" = "true" ]; then
      break
    fi

    remaining="$(remaining_auto_wait_seconds)"
    [ "${remaining}" -gt 0 ] || break
    sleep_seconds="${AUTO_POLL_SECONDS}"
    if [ "${remaining}" -lt "${sleep_seconds}" ]; then
      sleep_seconds="${remaining}"
    fi
    sleep "${sleep_seconds}"
  done
}

# Behavioral test seam for the bounded probe helper. Production invocations do
# not set this flag and continue into normal datasource provisioning below.
if [ "${BIOETL_BOOTSTRAP_PROBE_ONLY:-}" = "1" ]; then
  probe_ready "$@"
  exit 0
fi

mkdir -p "${TARGET_DIR}"
rm -f "${TARGET_DIR}"/*.yml
cp "${CORE_DIR}"/*.yml "${TARGET_DIR}/"

case "${TRACING_FLAG}" in
  true)
    ENABLE_LOKI="true"
    ENABLE_TEMPO="true"
    echo "[bioetl-grafana] enabled Loki and Tempo (explicit mode)"
    ;;
  false)
    echo "[bioetl-grafana] disabled Loki and Tempo (explicit mode)"
    ;;
  auto|"")
    echo "[bioetl-grafana] auto-detecting Loki and Tempo..."
    wait_for_auto_tracing_ready
    ;;
  *)
    echo "[bioetl-grafana] unknown tracing datasource mode '${TRACING_FLAG}', falling back to auto-detect"
    wait_for_auto_tracing_ready
    ;;
esac

if [ "${ENABLE_LOKI}" = "true" ]; then
  cp "${TRACING_DIR}/loki.yml" "${TARGET_DIR}/"
fi

if [ "${ENABLE_TEMPO}" = "true" ]; then
  cp "${TRACING_DIR}/tempo.yml" "${TARGET_DIR}/"
fi

if [ "${ENABLE_LOKI}" != "true" ] || [ "${ENABLE_TEMPO}" != "true" ]; then
  {
    printf '%s\n' 'apiVersion: 1'
    printf '\n'
    printf '%s\n' 'deleteDatasources:'
    if [ "${ENABLE_LOKI}" != "true" ]; then
      printf '%s\n' '  - name: Loki'
    fi
    if [ "${ENABLE_TEMPO}" != "true" ]; then
      printf '%s\n' '  - name: Tempo'
    fi
  } > "${PRUNE_FILE}"
fi

echo "[bioetl-grafana] tracing datasources mode=${TRACING_FLAG} loki=${ENABLE_LOKI} tempo=${ENABLE_TEMPO}"

if [ -n "${RENDERING_SERVER_URL}" ] && [ -d "${STALE_RENDERER_PLUGIN_DIR}" ]; then
  rm -rf "${STALE_RENDERER_PLUGIN_DIR}"
  echo "[bioetl-grafana] removed stale local grafana-image-renderer plugin for remote renderer mode"
fi

exec /run.sh
