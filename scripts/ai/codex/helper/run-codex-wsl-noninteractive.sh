#!/usr/bin/env bash
# Codex WSL Launcher Helper
# Non-interactive wrapper to prevent hanging on update prompts

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${REPO_ROOT:-$(cd "${SCRIPT_DIR}/../../../.." && pwd)}"

# Silence npm update notifications
export NPM_CONFIG_UPDATE_NOTIFIER=false
export FORCE_COLOR=1
export CI=true

# Load .env.codex if it exists
if [[ -f "${SCRIPT_DIR}/.env.codex" ]]; then
    set -a
    source "${SCRIPT_DIR}/.env.codex"
    set +a
fi

# Verify API key is set
if [[ -z "${OPENAI_API_KEY:-}" ]]; then
    echo "[ERROR] OPENAI_API_KEY not set in ${SCRIPT_DIR}/.env.codex" >&2
    echo "[INFO] Get your key from: https://platform.openai.com/api-keys" >&2
    exit 1
fi

# Run the main launcher without interactive mode
exec bash "${SCRIPT_DIR}/run-codex.sh" "$@" < /dev/null
