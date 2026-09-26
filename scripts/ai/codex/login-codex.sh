#!/usr/bin/env bash
# Quick login script for Codex using API key from a local env file.
# The key is passed via env / stdin fd — never interpolated into process argv.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${CODEX_ENV_FILE:-$SCRIPT_DIR/.env.codex}"

if [[ ! -f "$ENV_FILE" ]]; then
    echo "ERROR: env file not found at $ENV_FILE" >&2
    echo "hint: set CODEX_ENV_FILE or create a local untracked .env.codex" >&2
    exit 1
fi

# Source the env file without printing it.
set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

if [[ -z "${OPENAI_API_KEY:-}" ]]; then
    echo "ERROR: OPENAI_API_KEY not found in $ENV_FILE" >&2
    exit 1
fi

echo "Logging in to Codex using API key from env (value not printed)..."
if codex login --with-api-key >/dev/null <<EOF
${OPENAI_API_KEY}
EOF
then
    echo ""
    echo "SUCCESS: Logged in to Codex"
    codex login status
else
    echo ""
    echo "ERROR: Failed to login to Codex" >&2
    exit 1
fi
