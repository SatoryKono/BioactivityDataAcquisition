#!/usr/bin/env bash
# Verify or regenerate the transformed docs mirror and Codex-Devin parity.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
MODE="${1:---check}"

usage() {
  cat <<'EOF'
Usage:
  bash scripts/ai/codex/check_skills_mirror.sh --check
  bash scripts/ai/codex/check_skills_mirror.sh --sync

Modes:
  --check  Read-only validation of docs mirror and Codex-Devin parity.
  --sync   Regenerate the transformed docs mirror, then validate parity.
EOF
}

case "$MODE" in
  --check)
    exec python3 "$REPO_ROOT/scripts/ai/sync_ai_governance.py" \
      --root "$REPO_ROOT" --only skill-mirrors --check
    ;;
  --sync)
    exec python3 "$REPO_ROOT/scripts/ai/sync_ai_governance.py" \
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
