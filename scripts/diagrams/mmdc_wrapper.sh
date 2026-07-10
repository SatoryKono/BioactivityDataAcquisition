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

DOCKER_IMAGE="${MMDC_DOCKER_IMAGE:-minlag/mermaid-cli:10.6.1}"
LOCAL_MMDC="/tmp/mermaid-cli-lite/node_modules/.bin/mmdc"
FORCE_DOCKER="${MMDC_FORCE_DOCKER:-0}"
HOST_PUPPETEER_CACHE_DIR="${PUPPETEER_CACHE_DIR:-${HOME:-}/.cache/puppeteer}"
MMDC_REQUIRED_VERSION="${MMDC_REQUIRED_VERSION:-10.6.1}"
MMDC_ALLOW_VERSION_DRIFT="${MMDC_ALLOW_VERSION_DRIFT:-0}"
MMDC_SKIP_VERSION_CHECK="${MMDC_SKIP_VERSION_CHECK:-0}"

candidate_version() {
  local candidate="$1"
  "$candidate" --version 2>/dev/null | head -n 1 | sed -E 's/.*([0-9]+\.[0-9]+\.[0-9]+).*/\1/'
}

assert_candidate_version() {
  local candidate="$1"
  local version=""

  [[ -z "$MMDC_REQUIRED_VERSION" ]] && return 0
  [[ "$MMDC_ALLOW_VERSION_DRIFT" == "1" ]] && return 0
  [[ "$MMDC_SKIP_VERSION_CHECK" == "1" ]] && return 0

  version="$(candidate_version "$candidate" || true)"
  if [[ "$version" != "$MMDC_REQUIRED_VERSION" ]]; then
    echo "Error: Mermaid CLI version mismatch for $candidate" >&2
    echo "  required: $MMDC_REQUIRED_VERSION" >&2
    echo "  detected: ${version:-unknown}" >&2
    echo "Set MMDC_ALLOW_VERSION_DRIFT=1 only for diagnostics/canary runs." >&2
    return 1
  fi
  return 0
}

exec_candidate() {
  local candidate="$1"
  shift
  assert_candidate_version "$candidate"
  exec "$candidate" "$@"
}

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

  local docker_args=(
    --rm
    -u "$(id -u):$(id -g)"
    -v "$REPO_ROOT:$REPO_ROOT"
    -v /tmp:/tmp
    -w "$PWD"
  )

  # Mount a host Puppeteer cache into the container so Docker fallback can
  # reuse a previously installed chrome-headless-shell runtime.
  if [[ -d "$HOST_PUPPETEER_CACHE_DIR" ]]; then
    docker_args+=(
      -e PUPPETEER_CACHE_DIR=/home/node/.cache/puppeteer
      -v "$HOST_PUPPETEER_CACHE_DIR:/home/node/.cache/puppeteer"
    )
  fi

  exec docker run \
    "${docker_args[@]}" \
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
        exec_candidate "$MMDC_CANDIDATE" "$@"
      fi
    fi
  fi

  SYSTEM_MMDC="$(command -v mmdc 2>/dev/null || true)"
  if [[ -n "$SYSTEM_MMDC" ]]; then
    SYSTEM_MMDC_RESOLVED="$(readlink -f "$SYSTEM_MMDC" 2>/dev/null || echo "$SYSTEM_MMDC")"
    if [[ "$SYSTEM_MMDC_RESOLVED" != "$SELF_PATH" ]]; then
      exec_candidate "$SYSTEM_MMDC" "$@"
    fi
  fi

  if [[ -x "$LOCAL_MMDC" ]]; then
    exec_candidate "$LOCAL_MMDC" "$@"
  fi
fi

run_with_docker "$@"
