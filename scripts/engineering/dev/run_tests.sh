#!/usr/bin/env bash
# Thin facade for backward compatibility.
# Canonical implementation: scripts/engineering/dev/run_tests.py
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$PROJECT_DIR"

detect_python() {
    local cmd
    for cmd in py python python3; do
        if command -v "$cmd" >/dev/null 2>&1; then
            echo "$cmd"
            return 0
        fi
    done
    return 1
}

PYTHON_BIN="$(detect_python)" || {
    echo "[FAIL] Python executable not found in PATH" >&2
    exit 1
}

exec "$PYTHON_BIN" scripts/engineering/dev/run_tests.py "$@"
