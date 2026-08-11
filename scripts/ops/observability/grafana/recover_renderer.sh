#!/usr/bin/env bash
# Recover optional Grafana image renderer without restarting Grafana UI.
# See recover_renderer.ps1 for the full strategy.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
cd "${ROOT}"

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.monitoring.yml}"
PROJECT="${PROJECT:-bioetl-monitoring}"
WAIT_SECONDS="${WAIT_SECONDS:-90}"

echo "=== Grafana renderer recovery (UI stays up) ==="
docker compose -p "${PROJECT}" -f "${COMPOSE_FILE}" up -d --force-recreate --no-deps renderer

deadline=$((SECONDS + WAIT_SECONDS))
healthy=0
while (( SECONDS < deadline )); do
  cid="$(docker compose -p "${PROJECT}" -f "${COMPOSE_FILE}" ps -q renderer 2>/dev/null || true)"
  if [[ -n "${cid}" ]]; then
    status="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "${cid}" 2>/dev/null || true)"
    echo "  renderer=${status}"
    if [[ "${status}" == "healthy" ]]; then
      healthy=1
      break
    fi
    oom="$(docker inspect --format '{{.State.OOMKilled}}' "${cid}" 2>/dev/null || true)"
    if [[ "${oom}" == "true" ]]; then
      echo "WARN: renderer OOMKilled — free host RAM before retry" >&2
      break
    fi
  fi
  sleep 3
done

if curl -fsS -m 5 http://127.0.0.1:3000/api/health >/dev/null 2>&1; then
  echo "  Grafana /api/health -> ok (UI independent of renderer)"
else
  echo "WARN: Grafana UI probe failed" >&2
fi

if [[ "${healthy}" -eq 1 ]]; then
  echo "OK: renderer recovered"
  exit 0
fi

echo "Renderer not healthy within ${WAIT_SECONDS}s; UI should still work (render fail-fast)." >&2
exit 1
