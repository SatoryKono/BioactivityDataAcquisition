#!/usr/bin/env bash
# Check or regenerate the transformed docs mirror and Codex-Devin parity.
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
  bash scripts/ai/codex/check_skills_mirror.sh --check
  bash scripts/ai/codex/check_skills_mirror.sh --sync

Modes:
  --check  Read-only validation of docs mirror and Codex-Devin parity.
  --sync   Regenerate the transformed docs mirror, then validate parity.

Requires python3 or python on PATH. Preferred:
  python -m scripts.ai.sync.governance --root . --only skill-mirrors --check
EOF
}

PYTHON_BIN="$(resolve_python)"

case "$MODE" in
  --check)
    exec "$PYTHON_BIN" "$REPO_ROOT/scripts/ai/sync/governance.py" \
      --root "$REPO_ROOT" --only skill-mirrors --check
    ;;
  --sync)
    exec "$PYTHON_BIN" "$REPO_ROOT/scripts/ai/sync/governance.py" \
      --root "$REPO_ROOT" --only skill-mirrors
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
