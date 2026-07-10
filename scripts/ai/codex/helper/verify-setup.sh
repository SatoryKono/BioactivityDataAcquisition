#!/usr/bin/env bash
# Installation and usage verification script
# Run this to test your Codex WSL setup

set -euo pipefail

# Constants
readonly SEPARATOR="=========================================="

echo "$SEPARATOR"
echo "  Codex WSL Setup Verification"
echo "$SEPARATOR"
echo ""

ERRORS=0

# Check WSL
echo "[1/5] Checking WSL environment..."
if grep -qi microsoft /proc/version 2>/dev/null; then
    echo "✓ Running in WSL"
else
    echo "⚠ Not running in WSL (this is normal from PowerShell)"
fi
echo ""

# Check Node.js
echo "[2/5] Checking Node.js..."
if command -v node &>/dev/null; then
    NODE_VERSION=$(node --version)
    echo "✓ Node.js $NODE_VERSION installed"
else
    echo "✗ Node.js not found"
    echo "  → Run: sudo apt-get install -y nodejs npm"
    ERRORS=$((ERRORS + 1))
fi
echo ""

# Check npm
echo "[3/5] Checking npm..."
if command -v npm &>/dev/null; then
    NPM_VERSION=$(npm --version)
    echo "✓ npm $NPM_VERSION installed"
else
    echo "✗ npm not found"
    echo "  → Run: sudo apt-get install -y npm"
    ERRORS=$((ERRORS + 1))
fi
echo ""

# Check Codex
echo "[4/5] Checking Codex CLI..."
ENSURE_SCRIPT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/ensure-codex-cli.sh"
if [[ -x "${ENSURE_SCRIPT}" ]]; then
    CODEX_BIN="$("${ENSURE_SCRIPT}" --no-install --print-bin 2>/dev/null || true)"
else
    CODEX_BIN=""
fi

if [[ -n "${CODEX_BIN}" && -x "${CODEX_BIN}" ]]; then
    CODEX_VERSION=$("${CODEX_BIN}" --version 2>/dev/null || echo "unknown")
    CODEX_PREFIX="$("${ENSURE_SCRIPT}" --no-install --print-prefix 2>/dev/null || echo "unknown")"
    echo "✓ Codex CLI installed (${CODEX_VERSION})"
    echo "  → Prefix: ${CODEX_PREFIX}"
else
    echo "✗ Codex CLI not found"
    echo "  → Run: bash ./scripts/ai/codex/helper/setup-wsl.sh"
    ERRORS=$((ERRORS + 1))
fi
echo ""

# Check API connectivity
echo "[5/5] Checking OpenAI API connectivity..."
if timeout 5 curl -s -I https://api.openai.com >/dev/null 2>&1; then
    echo "✓ OpenAI API accessible"
elif grep -q "_WIN_HOST_IP\|http_proxy" ~/.bashrc 2>/dev/null; then
    echo "⚠ Proxy configured but API check failed (may still work)"
    echo "  → Try: curl -I https://api.openai.com"
else
    echo "⚠ OpenAI API not accessible"
    echo "  → If behind VPN/proxy, source the proxy config:"
    echo "    source scripts/engineering/dev/bash/.wsl_proxy_env.sh"
    echo "  → Or start Windows proxy:"
    echo "    .\scripts\ops\start-wsl-proxy.bat"
fi
echo ""

# Summary
echo "$SEPARATOR"
if [[ $ERRORS -eq 0 ]]; then
    echo "  ✓ Setup verification successful!"
    echo "$SEPARATOR"
    echo ""
    echo "You can now use Codex:"
    echo ""
    echo "  Interactive:  ./scripts/ops/launchers/codex/codex.sh"
    echo "  With prompt:  ./scripts/ops/launchers/codex/codex.sh \"analyze the pipeline\""
    echo "  Auto-exec:    ./scripts/ops/launchers/codex/codex-exec.sh \"fix all TODOs\""
    echo ""
else
    echo "  ✗ Setup verification found $ERRORS issue(s)"
    echo "$SEPARATOR"
    echo ""
    echo "Please fix the issues above, then run:"
    echo "  bash ./scripts/ai/codex/helper/setup-wsl.sh"
    echo ""
fi
