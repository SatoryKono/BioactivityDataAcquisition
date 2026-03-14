#!/usr/bin/env bash
# setup_plugins.sh - Configure development plugins for BioETL.
# Usage:
#   bash scripts/setup_plugins.sh
#   bash scripts/setup_plugins.sh --pytest-only

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$REPO_ROOT"

PYTEST_ONLY=false
if [[ "${1:-}" == "--pytest-only" ]]; then
    PYTEST_ONLY=true
elif [[ -n "${1:-}" ]]; then
    echo "[setup-plugins][error] Unknown argument: $1"
    echo "[setup-plugins][hint] Supported arguments: --pytest-only"
    exit 2
fi

BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[setup-plugins]${NC} $1"; }
log_ok() { echo -e "${GREEN}[setup-plugins]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[setup-plugins]${NC} $1"; }

USE_UV=false
PYTHON_BIN=""

if command -v uv >/dev/null 2>&1; then
    USE_UV=true
elif [[ -x ".venv/bin/python" ]]; then
    PYTHON_BIN=".venv/bin/python"
elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
else
    log_warn "Python runtime not found."
    log_warn "Install uv or activate a Python environment, then rerun:"
    echo "  uv sync --extra dev --extra tests --extra tracing"
    exit 1
fi

run_python() {
    if [[ "$USE_UV" == true ]]; then
        uv run python "$@"
    else
        "$PYTHON_BIN" "$@"
    fi
}

install_dev_dependencies() {
    if [[ "$USE_UV" == true ]]; then
        log_info "Syncing dev/test dependencies via uv..."
        uv sync --extra dev --extra tests --extra tracing
    else
        log_info "Installing dev/test dependencies via pip..."
        "$PYTHON_BIN" -m pip install -e ".[dev,tests,tracing]"
    fi
}

check_pytest_plugins() {
    run_python - <<'PY'
import importlib.util

required = {
    "pytest_asyncio": "pytest-asyncio",
    "pytest_cov": "pytest-cov",
    "xdist": "pytest-xdist",
    "pytest_timeout": "pytest-timeout",
    "pytest_vcr": "pytest-vcr",
}
missing = [pkg for module, pkg in required.items() if importlib.util.find_spec(module) is None]
if missing:
    print("[setup-plugins][error] Missing pytest plugins:", ", ".join(missing))
    raise SystemExit(1)

print("[setup-plugins][ok] pytest plugins are available")
PY
}

install_precommit() {
    if [[ "$PYTEST_ONLY" == true ]]; then
        return 0
    fi

    if [[ ! -f ".pre-commit-config.yaml" ]]; then
        log_warn ".pre-commit-config.yaml not found, skipping hook installation"
        return 0
    fi

    log_info "Ensuring pre-commit is installed..."
    if [[ "$USE_UV" == true ]]; then
        if ! uv run python -m pre_commit --version >/dev/null 2>&1; then
            uv run python -m pip install pre-commit
        fi
        if git rev-parse --git-dir >/dev/null 2>&1; then
            uv run python -m pre_commit install --install-hooks
            log_ok "pre-commit hooks installed"
        else
            log_warn "Not a git repository, skipping pre-commit install"
        fi
    else
        if ! "$PYTHON_BIN" -m pre_commit --version >/dev/null 2>&1; then
            "$PYTHON_BIN" -m pip install pre-commit
        fi
        if git rev-parse --git-dir >/dev/null 2>&1; then
            "$PYTHON_BIN" -m pre_commit install --install-hooks
            log_ok "pre-commit hooks installed"
        else
            log_warn "Not a git repository, skipping pre-commit install"
        fi
    fi
}

if ! check_pytest_plugins; then
    install_dev_dependencies
    check_pytest_plugins
fi

install_precommit
log_ok "Plugin setup completed"
