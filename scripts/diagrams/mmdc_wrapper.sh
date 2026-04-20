#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if REPO_ROOT_GIT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null)"; then
  REPO_ROOT="$REPO_ROOT_GIT"
else
  REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
fi

SELF_PATH="$(readlink -f "$0" 2>/dev/null || python3 - <<'PY' "$0"
from pathlib import Path
import sys
print(Path(sys.argv[1]).resolve())
PY
)"

DOCKER_IMAGE="${MMDC_DOCKER_IMAGE:-minlag/mermaid-cli}"
LOCAL_MMDC="/tmp/mermaid-cli-lite/node_modules/.bin/mmdc"
FORCE_DOCKER="${MMDC_FORCE_DOCKER:-0}"

run_with_docker() {
  if ! command -v docker >/dev/null 2>&1; then
    echo "Error: mmdc not found and docker is unavailable for fallback." >&2
    echo "Hint: install @mermaid-js/mermaid-cli or make docker available." >&2
    return 127
  fi

  if ! docker image inspect "$DOCKER_IMAGE" >/dev/null 2>&1; then
    echo "Info: pulling Docker Mermaid CLI image: $DOCKER_IMAGE" >&2
    docker pull "$DOCKER_IMAGE" >/dev/null
  fi

  exec docker run --rm \
    -u "$(id -u):$(id -g)" \
    -v "$REPO_ROOT:$REPO_ROOT" \
    -v /tmp:/tmp \
    -w "$PWD" \
    "$DOCKER_IMAGE" \
    "$@"
}

if [[ "$FORCE_DOCKER" != "1" ]]; then
if [[ -n "${MMDC_BIN:-}" ]]; then
  MMDC_CANDIDATE="$(command -v "$MMDC_BIN" 2>/dev/null || true)"
  if [[ -z "$MMDC_CANDIDATE" && -x "$MMDC_BIN" ]]; then
    MMDC_CANDIDATE="$MMDC_BIN"
  fi
  if [[ -n "$MMDC_CANDIDATE" ]]; then
    MMDC_RESOLVED="$(readlink -f "$MMDC_CANDIDATE" 2>/dev/null || echo "$MMDC_CANDIDATE")"
    if [[ "$MMDC_RESOLVED" != "$SELF_PATH" ]]; then
      exec "$MMDC_CANDIDATE" "$@"
    fi
  fi
fi

SYSTEM_MMDC="$(command -v mmdc 2>/dev/null || true)"
if [[ -n "$SYSTEM_MMDC" ]]; then
  SYSTEM_MMDC_RESOLVED="$(readlink -f "$SYSTEM_MMDC" 2>/dev/null || echo "$SYSTEM_MMDC")"
  if [[ "$SYSTEM_MMDC_RESOLVED" != "$SELF_PATH" ]]; then
    exec "$SYSTEM_MMDC" "$@"
  fi
fi

if [[ -x "$LOCAL_MMDC" ]]; then
  exec "$LOCAL_MMDC" "$@"
fi
fi

run_with_docker "$@"
