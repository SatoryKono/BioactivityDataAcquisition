#!/usr/bin/env bash
# Recover optional Grafana image renderer without restarting Grafana UI.
# Prefers Python SSOT (same as runtime_manager recover-renderer).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
cd "${ROOT}"

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.monitoring.yml}"
PROJECT="${PROJECT:-bioetl-monitoring}"
WAIT_SECONDS="${WAIT_SECONDS:-90}"

if command -v python3 >/dev/null 2>&1 || command -v python >/dev/null 2>&1; then
  PY="$(command -v python3 || command -v python)"
  export PYTHONPATH="${ROOT}${PYTHONPATH:+:${PYTHONPATH}}"
  exec "${PY}" scripts/ops/observability/grafana/recover_renderer.py \
    --project "${PROJECT}" \
    --compose-file "${COMPOSE_FILE}" \
    --wait "${WAIT_SECONDS}"
fi

echo "=== Grafana renderer recovery (UI stays up; python SSOT unavailable) ==="
docker compose -p "${PROJECT}" -f "${COMPOSE_FILE}" up -d --force-recreate --no-deps renderer

deadline=$((SECONDS + WAIT_SECONDS))
while (( SECONDS < deadline )); do
  cid="$(docker compose -p "${PROJECT}" -f "${COMPOSE_FILE}" ps -q renderer 2>/dev/null || true)"
  if [[ -n "${cid}" ]]; then
    status="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "${cid}" 2>/dev/null || true)"
    echo "  renderer=${status}"
    if [[ "${status}" == "healthy" ]]; then
      echo "OK: renderer recovered"
      exit 0
    fi
  fi
  sleep 3
done

echo "Renderer not healthy within ${WAIT_SECONDS}s; do NOT restart Grafana for renderer" >&2
exit 1
