#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
VENV_DIR="${BIOETL_WSL_VENV_DIR:-$HOME/.venvs/bioetl}"

mkdir -p "$VENV_DIR"

"$VENV_DIR/bin/python" -m pip install --upgrade pip setuptools wheel >/dev/null
"$VENV_DIR/bin/python" -m pip install -e "$REPO_ROOT[dev,tests,tracing]"

export BIOETL_WSL_VENV_DIR="$VENV_DIR"

bash "$REPO_ROOT/scripts/engineering/dev/run_pytest_sharded.sh" "$@"
