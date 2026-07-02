#!/usr/bin/env bash
# Repository root compatibility shim for the canonical WSL Codex setup helper.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CANONICAL_SETUP="${SCRIPT_DIR}/scripts/ai/codex/helper/setup-wsl-complete.sh"

if [[ ! -x "${CANONICAL_SETUP}" ]]; then
    echo "[root-codex-setup] ERROR: canonical setup helper not found: ${CANONICAL_SETUP}" >&2
    exit 1
fi

exec bash "${CANONICAL_SETUP}" "$@"
