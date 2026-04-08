#!/usr/bin/env bash
# Install the official Mistral Vibe CLI into the current WSL user profile.

set -euo pipefail

if command -v vibe >/dev/null 2>&1; then
    echo "[setup-mistral-vibe] vibe is already installed: $(command -v vibe)"
    exit 0
fi

if command -v curl >/dev/null 2>&1; then
    echo "[setup-mistral-vibe] Installing via official installer"
    exec bash -lc 'curl -LsSf https://mistral.ai/vibe/install.sh | bash'
fi

echo "[setup-mistral-vibe] curl not found; falling back to pip --user"
exec python3 -m pip install --user mistral-vibe
