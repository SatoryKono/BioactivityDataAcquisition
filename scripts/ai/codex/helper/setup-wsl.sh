#!/usr/bin/env bash
# WSL Codex setup — install dependencies and configure environment
# Run from WSL: bash ./scripts/ai/codex/helper/setup-wsl.sh

set -euo pipefail
SEPARATOR_LINE="=========================================="
echo "${SEPARATOR_LINE}"
echo "  WSL Codex Setup"
echo "${SEPARATOR_LINE}"
echo ""

# Check if running in WSL
if ! grep -qi microsoft /proc/version 2>/dev/null; then
    echo "[WARNING] Not running in WSL. This script is designed for WSL2."
    echo "[INFO] Run from WSL Ubuntu distro: wsl -- bash ./scripts/ai/codex/helper/setup-wsl.sh"
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${REPO_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || (cd "${SCRIPT_DIR}/../../.." && pwd))}"
ENSURE_SCRIPT="${SCRIPT_DIR}/ensure-codex-cli.sh"

# Step 1: Update package manager (with retry logic)
echo "[1/5] Updating package manager..."
for i in {1..5}; do
    if sudo apt-get update -qq 2>/dev/null; then
        echo "✓ Package manager updated"
        break
    elif [[ $i -lt 5 ]]; then
        echo "  → Retrying (attempt $((i+1))/5)..."
        sleep 5
    else
        echo "[WARNING] apt-get update had issues, continuing anyway..."
    fi
done
echo ""

# Step 2: Install Node.js and npm (if not present)
echo "[2/5] Checking Node.js installation..."
if ! command -v node &>/dev/null; then
    echo "  → Installing Node.js and npm..."
    sudo apt-get install -y -qq nodejs npm 2>/dev/null || sudo apt-get install -y nodejs npm
    echo "✓ Node.js $(node --version) installed"
else
    echo "✓ Node.js $(node --version) already installed"
fi
echo ""

# Step 3: Install/update Codex CLI in a writable local prefix
echo "[3/5] Installing Codex CLI..."
"${ENSURE_SCRIPT}" --update >/dev/null
"${ENSURE_SCRIPT}" --install-command-shim >/dev/null
CODEX_PREFIX="$("${ENSURE_SCRIPT}" --print-prefix)"
echo "✓ Codex CLI installed in ${CODEX_PREFIX}"
echo ""

# Step 4: Verify Codex installation
echo "[4/5] Verifying Codex installation..."
CODEX_BIN="$("${ENSURE_SCRIPT}" --print-bin)"
CODEX_VERSION=$("${CODEX_BIN}" --version 2>/dev/null || echo "unknown")
echo "✓ Codex CLI verified: ${CODEX_VERSION}"
echo ""

# Step 5: Configure WSL proxy (for API access)
echo "[5/5] Configuring WSL proxy..."

# Get Windows host IP
WIN_HOST_IP=$(/sbin/ip route show default 2>/dev/null | awk '{print $3}' || echo "")

if [[ -z "$WIN_HOST_IP" ]]; then
    echo "[WARNING] Could not determine Windows host IP"
    echo "[INFO] Run this command manually to configure proxy:"
    # Local WSL->Windows host CONNECT proxy only (not a public clear-text endpoint).
    echo "  export http_proxy=http://<windows-host-ip>:3128"  # NOSONAR - local WSL host proxy
    echo "  export https_proxy=http://<windows-host-ip>:3128"  # NOSONAR - local WSL host proxy
else
    # Check if proxy is accessible
    if timeout 2 bash -c "echo > /dev/tcp/$WIN_HOST_IP/3128" 2>/dev/null; then
        echo "✓ Windows proxy available at $WIN_HOST_IP:3128"
    else
        echo "[INFO] Windows proxy not accessible at $WIN_HOST_IP:3128"
        echo "[INFO] Ensure WSL proxy is running on Windows:"
        echo "  PowerShell: python .\scripts\ops\wsl_proxy.py"
        echo "  or: .\scripts\ops\start-wsl-proxy.bat"
    fi
fi

# Suggest adding proxy to bashrc
BASHRC="$HOME/.bashrc"
WSL_PROXY_RC="$REPO_ROOT/scripts/engineering/dev/bash/.wsl_proxy_env.sh"
if ! grep -q "wsl_proxy_env.sh" "$BASHRC" 2>/dev/null; then
    echo "[INFO] To auto-configure proxy on shell login, add to $BASHRC:"
    echo "  source $WSL_PROXY_RC"
    echo ""
    echo "Run: echo \"source $WSL_PROXY_RC\" >> $BASHRC"
fi

echo ""
echo "${SEPARATOR_LINE}"
echo "  Setup Complete!"
echo "${SEPARATOR_LINE}"
echo ""
echo "Quick start:"
echo "  • Interactive:  $REPO_ROOT/scripts/ops/launchers/codex/codex.sh"
echo "  • With prompt:  $REPO_ROOT/scripts/ops/launchers/codex/codex.sh \"analyze the pipeline\""
echo "  • Auto-exec:    $REPO_ROOT/scripts/ops/launchers/codex/codex-exec.sh \"refactor ChemBL parser\""
echo ""
echo "For more info, see: $REPO_ROOT/scripts/ai/codex/README.md"
echo ""
