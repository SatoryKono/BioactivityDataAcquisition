#!/usr/bin/env bash
# Launch Codex CLI from WSL
# Codex will use the current working directory context
# Usage: ./codex.sh [options] [prompt]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
WSL_DISTRO="Ubuntu"  # Use Ubuntu (change to Debian if preferred)

# Get absolute path in WSL format
get_wsl_path() {
    local path="$1"
    if [[ "$path" =~ ^/mnt/[a-z]/ ]]; then
        echo "$path"
    else
        echo "$path"
    fi
}

REPO_WSL=$(get_wsl_path "$REPO_ROOT")

# Verify Codex is installed
if ! command -v codex &>/dev/null; then
    echo "[ERROR] Codex CLI not found in PATH"
    echo "[INFO] Install: npm install -g @openai/codex"
    exit 1
fi

# Verify npm/node
if ! command -v node &>/dev/null; then
    echo "[ERROR] Node.js not found"
    echo "[INFO] Install Node.js in WSL: apt-get update && apt-get install -y nodejs npm"
    exit 1
fi

# Launch Codex
if [[ $# -eq 0 ]]; then
    echo "[codex] Starting interactive mode..."
    exec codex
else
    echo "[codex] Prompt: $*"
    exec codex "$@"
fi
