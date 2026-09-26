#!/usr/bin/env bash
# Portable entrypoint for BioETL memory.tooling.workflow (pre-task / post-task / smoke).
# Restores a reliable agent invocation path:
#   - prefers repo .venv
#   - always sets PYTHONPATH=src:<repo>
#   - does not alter BIOETL_AI_MEMORY_MODE (callers control off|read-only|read-write)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "${REPO_ROOT}"

if [[ -x "${REPO_ROOT}/.venv-win/Scripts/python.exe" ]]; then
  PYTHON_BIN="${REPO_ROOT}/.venv-win/Scripts/python.exe"
elif [[ -x "${REPO_ROOT}/.venv/bin/python" ]]; then
  PYTHON_BIN="${REPO_ROOT}/.venv/bin/python"
elif [[ -x "${REPO_ROOT}/.venv/Scripts/python.exe" ]]; then
  PYTHON_BIN="${REPO_ROOT}/.venv/Scripts/python.exe"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="$(command -v python3)"
else
  PYTHON_BIN="$(command -v python)"
fi

export PYTHONPATH="${REPO_ROOT}/src:${REPO_ROOT}${PYTHONPATH:+:${PYTHONPATH}}"

if ! "${PYTHON_BIN}" -c "import memory.tooling.workflow" >/dev/null 2>&1; then
  echo "error: cannot import memory.tooling.workflow with ${PYTHON_BIN}" >&2
  echo "hint: create/sync the project venv first, e.g.:" >&2
  echo "  uv sync" >&2
  echo "  # or: python -m venv .venv && .venv/bin/pip install -e ." >&2
  exit 2
fi

if [[ $# -eq 0 ]]; then
  set -- smoke --json
fi

exec "${PYTHON_BIN}" -m memory.tooling.workflow "$@"
