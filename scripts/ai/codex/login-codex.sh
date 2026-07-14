#!/bin/bash
# Quick login script for Codex using API key

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/.env.codex"

if [ ! -f "$ENV_FILE" ]; then
    echo "ERROR: .env.codex not found at $ENV_FILE"
    exit 1
fi

# Source the env file
source "$ENV_FILE"

if [ -z "$OPENAI_API_KEY" ]; then
    echo "ERROR: OPENAI_API_KEY not found in $ENV_FILE"
    exit 1
fi

echo "Logging in to Codex using API key..."
echo "$OPENAI_API_KEY" | codex login --with-api-key

if [ $? -eq 0 ]; then
    echo ""
    echo "SUCCESS: Logged in to Codex"
    codex login status
else
    echo ""
    echo "ERROR: Failed to login to Codex"
    exit 1
fi