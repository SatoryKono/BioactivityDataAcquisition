#!/usr/bin/env bash
# INTERNAL: WSL non-interactive launch
# Called by: WSL launchers
# DO NOT invoke directly
# Codex WSL Launcher Helper
# Non-interactive wrapper to prevent hanging on update prompts

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${REPO_ROOT:-$(cd "${SCRIPT_DIR}/../../../.." && pwd)}"

# Silence npm update notifications
export NPM_CONFIG_UPDATE_NOTIFIER=false
export FORCE_COLOR=1
export CI=true

# Load optional API-key env; ChatGPT device auth is also accepted.
if [[ -f "${SCRIPT_DIR}/../.env.codex" ]]; then
    set -a
    # shellcheck disable=SC1091
    source "${SCRIPT_DIR}/../.env.codex"
    set +a
elif [[ -f "${SCRIPT_DIR}/.env.codex" ]]; then
    set -a
    # shellcheck disable=SC1091
    source "${SCRIPT_DIR}/.env.codex"
    set +a
fi

# shellcheck source=codex-auth-lib.sh
source "${SCRIPT_DIR}/codex-auth-lib.sh"
if ! codex_has_usable_auth; then
    echo "[ERROR] No usable Codex auth (ChatGPT session or OPENAI_API_KEY)." >&2
    echo "[INFO] Run: bash scripts/ai/codex/run-codex.sh device-login" >&2
    echo "[INFO] Or set OPENAI_API_KEY in scripts/ai/codex/.env.codex" >&2
    exit 1
fi

# Run the main launcher without interactive mode
exec bash "${SCRIPT_DIR}/../run-codex.sh" "$@" < /dev/null
