#!/usr/bin/env bash
# Gemini Interactive Launcher (WSL)
# Quick entry point for interactive Gemini CLI in WSL
# Usage: bash gemini-interactive.sh [prompt]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${REPO_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || (cd "${SCRIPT_DIR}/../../.." && pwd))}"

# Check if setup is complete
if ! bash "${SCRIPT_DIR}/helper/check-env.sh" 2>/dev/null; then
    echo "[!] Running setup (first time only)..."
    if ! bash "${SCRIPT_DIR}/helper/setup-env.sh"; then
        echo "[X] Setup failed"
        exit 1
    fi
fi

# If argument provided, run with prompt; otherwise interactive
if [[ $# -gt 0 ]]; then
    bash "${SCRIPT_DIR}/run-gemini.sh" "$@"
else
    bash "${SCRIPT_DIR}/run-gemini.sh" start
fi
