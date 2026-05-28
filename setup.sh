#!/usr/bin/env bash
# BioETL Environment Setup Script for Linux/WSL
# This script sets up the complete development environment for BioETL on Linux/WSL.
# Run with: bash setup.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR" && pwd)"

echo "=== BioETL Linux/WSL Environment Setup ==="
echo "[INFO] Repository root: $REPO_ROOT"

# Set UV environment variables
export UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/uv-cache}"
export UV_LINK_MODE="${UV_LINK_MODE:-copy}"
export UV_HTTP_TIMEOUT="${UV_HTTP_TIMEOUT:-180}"

VENV_DIR="${BIOETL_WSL_VENV_DIR:-$HOME/.venvs/bioetl}"
VENV_PYTHON="$VENV_DIR/bin/python"

# Check for conflicting venv
if [[ -e "$REPO_ROOT/.venv-wsl" ]]; then
    echo "[WARN] Found a repository-local .venv-wsl. Remove it to avoid Windows conflicts."
fi

if [[ -d "$REPO_ROOT/.venv" && ! -x "$REPO_ROOT/.venv/bin/python" ]]; then
    echo "[WARN] Found a non-WSL .venv. It will be ignored in favor of an external WSL venv."
fi

# Step 1: Check prerequisites
echo ""
echo "=== Step 1: Checking Prerequisites ==="

HAS_UV=0
HAS_PYTHON3=0
HAS_PYTHON=0

if command -v uv >/dev/null 2>&1; then
    HAS_UV=1
    echo "[OK] Found uv package manager"
elif command -v python3 >/dev/null 2>&1; then
    HAS_PYTHON3=1
    echo "[OK] Found python3"
elif command -v python >/dev/null 2>&1; then
    HAS_PYTHON=1
    echo "[OK] Found python"
else
    echo "[ERROR] Neither uv, python3, nor python is available. Please install Python 3.12+ or uv."
    exit 1
fi

# Step 2: Create virtual environment
echo ""
echo "=== Step 2: Creating Virtual Environment ==="

mkdir -p "$(dirname "$VENV_DIR")"

if [[ $HAS_UV -eq 1 ]]; then
    echo "[INFO] Creating venv with uv (Python 3.13)..."
    uv venv "$VENV_DIR" --python 3.13 --allow-existing
else
    if [[ ! -x "$VENV_PYTHON" ]]; then
        if [[ $HAS_PYTHON3 -eq 1 ]]; then
            echo "[INFO] Creating venv with python3..."
            python3 -m venv "$VENV_DIR"
        else
            echo "[INFO] Creating venv with python..."
            python -m venv "$VENV_DIR"
        fi
    else
        echo "[INFO] Reusing existing venv at $VENV_DIR"
    fi
fi

echo "[OK] Virtual environment ready at $VENV_DIR"

# Step 3: Install dependencies
echo ""
echo "=== Step 3: Installing Dependencies ==="

if [[ $HAS_UV -eq 1 ]]; then
    echo "[INFO] Syncing dependencies with uv (dev + tracing extras)..."
    export VIRTUAL_ENV="$VENV_DIR"
    export PATH="$VENV_DIR/bin:$PATH"
    uv sync --active --extra dev --extra tracing || {
        echo "[ERROR] uv sync failed."
        echo "[HINT] Retry with the same command; UV_HTTP_TIMEOUT defaults to $UV_HTTP_TIMEOUT seconds."
        exit 1
    }
else
    echo "[INFO] Upgrading pip, setuptools, wheel..."
    "$VENV_PYTHON" -m pip install --upgrade pip setuptools wheel

    echo "[INFO] Installing package with dev + tracing extras..."
    "$VENV_PYTHON" -m pip install -e '.[dev,tracing]'
fi

echo "[OK] Dependencies installed"

# Step 4: Setup pytest plugins
echo ""
echo "=== Step 4: Setting Up Pytest Plugins ==="

SETUP_PLUGINS_SCRIPT="$REPO_ROOT/scripts/ops/launchers/codex/setup_plugins.sh"
if [[ -f "$SETUP_PLUGINS_SCRIPT" ]]; then
    echo "[INFO] Running setup_plugins.sh (pytest-only mode)..."
    bash "$SETUP_PLUGINS_SCRIPT" --pytest-only
    echo "[OK] Pytest plugins configured"
else
    echo "[WARN] setup_plugins.sh not found; skipping plugin setup"
fi

# Step 5: Setup pre-commit hooks (optional)
echo ""
echo "=== Step 5: Setting Up Pre-Commit Hooks (Optional) ==="

echo "[INFO] Installing pre-commit hooks..."
"$VENV_PYTHON" -m pre_commit install --hook-type pre-commit --hook-type pre-push || {
    echo "[WARN] Pre-commit hooks installation failed (optional)"
}
echo "[OK] Pre-commit hooks installed"

# Step 6: Setup MCP (optional)
echo ""
echo "=== Step 6: Setting Up MCP (Optional) ==="

SETUP_MCP_SCRIPT="$REPO_ROOT/scripts/ai/codex/setup_mcp.py"
if [[ -f "$SETUP_MCP_SCRIPT" ]]; then
    echo "[INFO] Running setup_mcp.py..."
    "$VENV_PYTHON" "$SETUP_MCP_SCRIPT" || {
        echo "[WARN] MCP setup failed (optional)"
    }
    echo "[OK] MCP configured"
else
    echo "[WARN] setup_mcp.py not found; skipping MCP setup"
fi

# Step 7: Setup Codex skills (optional)
echo ""
echo "=== Step 7: Setting Up Codex Skills (Optional) ==="

SETUP_SKILLS_SCRIPT="$REPO_ROOT/scripts/ai/codex/setup_skills.sh"
if [[ -f "$SETUP_SKILLS_SCRIPT" ]]; then
    echo "[INFO] Running setup_skills.sh..."
    bash "$SETUP_SKILLS_SCRIPT" || {
        echo "[WARN] Codex skills setup failed (optional)"
    }
    echo "[OK] Codex skills synced"
else
    echo "[WARN] setup_skills.sh not found; skipping skills setup"
fi

# Step 8: Environment configuration
echo ""
echo "=== Step 8: Environment Configuration ==="

ENV_EXAMPLE="$REPO_ROOT/.env.example"
ENV_FILE="$REPO_ROOT/.env"

if [[ ! -f "$ENV_FILE" ]]; then
    echo "[INFO] Copying .env.example to .env..."
    cp "$ENV_EXAMPLE" "$ENV_FILE"
    echo "[OK] .env file created from .env.example"
    echo "[WARN] Please edit .env to add your API keys and configuration"
else
    echo "[INFO] .env file already exists; skipping"
fi

# Final summary
echo ""
echo "=== Setup Complete ==="
echo ""
echo "[OK] Environment is ready!"
echo ""
echo "Next steps:"
echo "1. Activate the virtual environment:"
echo "   source \"$VENV_DIR/bin/activate\""
echo ""
echo "2. Run tests:"
echo "   bash scripts/engineering/dev/run_pytest.sh tests/unit --narrow --timeout=120 --lf"
echo ""
echo "3. Run linting:"
echo "   \"$VENV_PYTHON\" -m ruff check src tests"
echo "   \"$VENV_PYTHON\" -m ruff format src tests"
echo ""
echo "4. Run type checking:"
echo "   bash scripts/engineering/dev/run_mypy.sh"
echo ""
echo "5. Edit .env to add your API keys (see .env.example for reference)"
echo ""
echo "For more information, see README.md"
