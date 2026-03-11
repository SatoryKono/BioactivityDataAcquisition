#!/usr/bin/env bash
# SessionStart hook for Claude Code.
# Runs once when a new session starts (skipped on resume).
# Ensures the dev environment is ready before Claude begins work.

set -uo pipefail

# ── Resolve repo root reliably ──────────────────────────────────────
# Primary: use script's own location (.claude/setup.sh → parent is repo root)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

# Validate
if [ ! -f "$REPO_ROOT/pyproject.toml" ]; then
    echo "[setup] ERROR: pyproject.toml not found in $REPO_ROOT"
    exit 1
fi
cd "$REPO_ROOT"

# ── Colors ──────────────────────────────────────────────────────────
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m'

info()  { echo -e "${BLUE}[setup]${NC} $*"; }
ok()    { echo -e "${GREEN}[setup]${NC} $*"; }
warn()  { echo -e "${YELLOW}[setup]${NC} $*"; }
fail()  { echo -e "${RED}[setup]${NC} $*"; }

# ── 1. Python version check ────────────────────────────────────────
info "Checking Python version..."
PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
REQUIRED_MINOR=11
ACTUAL_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)
if [ "$ACTUAL_MINOR" -lt "$REQUIRED_MINOR" ]; then
    fail "Python >= 3.11 required (found $PYTHON_VERSION)"
    exit 1
fi
ok "Python $PYTHON_VERSION"

# ── 2. Install / sync dependencies via uv (preferred) or pip ──────
if command -v uv &>/dev/null; then
    info "Syncing dependencies with uv..."
    if uv sync --extra dev --extra tracing --quiet 2>&1; then
        ok "Dependencies synced (uv sync)"
    elif uv venv .venv --python python3 --quiet 2>&1 && \
         uv pip install -e ".[dev,tracing]" --quiet 2>&1; then
        ok "Dependencies synced (uv pip fallback)"
    else
        warn "uv install failed — try 'make install' manually"
    fi
else
    info "uv not found — falling back to pip"
    if [ ! -d ".venv" ]; then
        python3 -m venv .venv
    fi
    # shellcheck disable=SC1091
    . .venv/bin/activate
    pip install --upgrade pip setuptools wheel -q 2>&1
    pip install -e ".[dev,tracing]" -q 2>&1
    ok "Dependencies installed (pip)"
fi

# ── 3. Verify critical imports ─────────────────────────────────────
info "Verifying critical imports..."
VERIFY_CMD='
import bioetl
import httpx, polars, deltalake, pandera, structlog, orjson
import pytest, ruff, mypy
print("OK")
'
if command -v uv &>/dev/null; then
    RESULT=$(uv run python3 -c "$VERIFY_CMD" 2>&1) || true
elif [ -f ".venv/bin/python" ]; then
    RESULT=$(.venv/bin/python -c "$VERIFY_CMD" 2>&1) || true
else
    RESULT=$(python3 -c "$VERIFY_CMD" 2>&1) || true
fi

if [ "$RESULT" = "OK" ]; then
    ok "All critical imports verified"
else
    warn "Some imports failed — run 'make install' to fix"
    echo "$RESULT" | tail -5
fi

# ── 4. Quick lint preflight (non-blocking) ─────────────────────────
info "Running quick lint preflight..."
if command -v uv &>/dev/null; then
    RUN="uv run"
elif [ -f ".venv/bin/python" ]; then
    RUN=".venv/bin/python -m"
else
    RUN="python3 -m"
fi

if $RUN ruff check src/ --quiet --no-fix 2>&1 | tail -3; then
    ok "Ruff lint: clean"
else
    warn "Ruff lint: issues found (non-blocking)"
fi

# ── 5. Summary ─────────────────────────────────────────────────────
echo ""
ok "Session environment ready."
info "Key commands:  make test | make lint | make arch-test"
