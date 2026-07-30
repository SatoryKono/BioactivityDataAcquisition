#!/usr/bin/env bash
# Check or sync parity between .codex/** and .junie/** runtime trees.
#
# Contract: scripts/ai/junie/junie-mirror-contract.json
# Both trees are equal-peer canonical runtime sources; --sync propagates in
# one direction only (.codex → .junie). Bidirectional parity is a governance
# contract, not an automated write policy.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
MODE="${1:---check}"

resolve_python() {
  if command -v python3 >/dev/null 2>&1; then
    command -v python3
    return 0
  fi
  if command -v python >/dev/null 2>&1; then
    command -v python
    return 0
  fi
  echo "Neither python3 nor python found on PATH" >&2
  return 127
}

usage() {
  cat <<'EOF'
Usage:
  bash scripts/ai/junie/check_junie_mirror.sh --check
  bash scripts/ai/junie/check_junie_mirror.sh --sync

Modes:
  --check  Read-only parity validation. Exit 0 on parity, 1 on drift.
  --sync   Copy missing/outdated files from .codex/** into .junie/**.
           Never writes into .codex/**.
EOF
}

case "$MODE" in
  --check|--sync)
    PYTHON_BIN="$(resolve_python)"
    exec "$PYTHON_BIN" "$SCRIPT_DIR/check_junie_mirror.py" "$MODE"
    ;;
  -h|--help)
    usage
    ;;
  *)
    echo "Unknown option: $MODE" >&2
    usage >&2
    exit 2
    ;;
esac
