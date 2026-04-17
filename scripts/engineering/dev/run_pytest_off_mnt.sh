#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
TEMP_ROOT="/tmp/bioetl-run"
WORK_DIR="$TEMP_ROOT/src"

rm -rf "$TEMP_ROOT"
mkdir -p "$WORK_DIR"
rsync -a --delete --exclude ".git" "$REPO_ROOT/" "$WORK_DIR/"

cd "$WORK_DIR"

python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip setuptools wheel >/dev/null
.venv/bin/python -m pip install -e ".[dev,tests,tracing]"

bash "$WORK_DIR/scripts/engineering/dev/run_pytest_sharded.sh" "$@"
