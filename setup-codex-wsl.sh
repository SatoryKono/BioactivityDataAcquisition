#!/usr/bin/env bash
# Docker/sbx Codex setup (optional). For native WSL Codex CLI use setup-codex-wsl.bat instead.

set -e

echo "[INFO] This script configures Docker Sandboxes (sbx) Codex."
echo "[INFO] For the canonical WSL Codex CLI launcher, run from repo root:"
echo "       .\\setup-codex-wsl.bat"
echo "       or: bash ./scripts/ai/codex/helper/setup-wsl-complete.sh"
echo ""

read -r -p "Continue with Docker/sbx setup? [y/N] " confirm
if [[ ! "${confirm}" =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 0
fi

echo "Setting up Docker Codex in WSL..."

echo "✓ Docker version:"
docker --version

echo ""
echo "Installing sbx (Docker Sandboxes CLI)..."
curl -sSL https://releases.docker.com/docker-sbx/install.sh | sh

echo ""
echo "✓ sbx version:"
sbx --version

echo ""
echo "Setting up OpenAI authentication..."
echo "Choose authentication method:"
echo "1) OAuth (recommended - browser-based)"
echo "2) API Key"
read -p "Enter choice (1 or 2): " choice

if [ "$choice" = "1" ]; then
    echo "Starting OAuth flow..."
    sbx secret set -g openai --oauth
elif [ "$choice" = "2" ]; then
    read -sp "Enter your OpenAI API Key: " api_key
    echo "$api_key" | sbx secret set -g openai
else
    echo "Invalid choice. Skipping authentication setup."
fi

echo ""
echo "✓ Docker/sbx setup complete!"
echo ""
echo "Quick start:"
echo "  sbx run codex ~/my-project"
echo "  sbx run codex . -- --dangerously-bypass-approvals-and-sandbox \"fix this bug\""
echo ""
echo "More info: https://docs.docker.com/ai/sandboxes/agents/codex/"
