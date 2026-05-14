#!/bin/sh
set -eu

TARGET_DIR="/etc/grafana/provisioning/datasources"
CORE_DIR="/etc/bioetl-grafana/datasources-core"
TRACING_DIR="/etc/bioetl-grafana/datasources-tracing"
PRUNE_FILE="${TARGET_DIR}/tracing-prune.yml"
TRACING_FLAG="$(printf '%s' "${BIOETL_ENABLE_TRACING_DATASOURCES:-auto}" | tr -d '\r' | xargs)"
AUTO_WAIT_SECONDS=8
AUTO_POLL_SECONDS=1
RENDERING_SERVER_URL="${GF_RENDERING_SERVER_URL:-}"
STALE_RENDERER_PLUGIN_DIR="/var/lib/grafana/plugins/grafana-image-renderer"
ENABLE_LOKI="false"
ENABLE_TEMPO="false"

mkdir -p "${TARGET_DIR}"
rm -f "${TARGET_DIR}"/*.yml
cp "${CORE_DIR}"/*.yml "${TARGET_DIR}/"

probe_ready() {
  wget --quiet --tries=1 --timeout=2 -O /dev/null "$1"
}

wait_for_auto_tracing_ready() {
  elapsed=0

  while [ "${elapsed}" -lt "${AUTO_WAIT_SECONDS}" ]; do
    if [ "${ENABLE_LOKI}" != "true" ] && probe_ready "http://loki:3100/ready"; then
      ENABLE_LOKI="true"
    fi
    if [ "${ENABLE_TEMPO}" != "true" ] && probe_ready "http://tempo:3200/ready"; then
      ENABLE_TEMPO="true"
    fi
    if [ "${ENABLE_LOKI}" = "true" ] && [ "${ENABLE_TEMPO}" = "true" ]; then
      break
    fi
    sleep "${AUTO_POLL_SECONDS}"
    elapsed=$((elapsed + AUTO_POLL_SECONDS))
  done
}

case "${TRACING_FLAG}" in
  true)
    ENABLE_LOKI="true"
    ENABLE_TEMPO="true"
    ;;
  false)
    ;;
  auto|"")
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
