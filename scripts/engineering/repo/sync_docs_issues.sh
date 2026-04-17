#!/usr/bin/env bash
set -euo pipefail

# Bash wrapper for the docs-sync issue metadata updater.
# Keeps the operator workflow shell-friendly while delegating the payload
# assembly and GitHub API handling to the Python implementation.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="${SCRIPT_DIR}/sync_docs_issues.py"

if [[ ! -f "${PYTHON_SCRIPT}" ]]; then
  echo "[FAIL] Missing companion script: ${PYTHON_SCRIPT}" >&2
  exit 1
fi

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  cat <<'EOF'
Usage:
  bash scripts/engineering/repo/sync_docs_issues.sh
  bash scripts/engineering/repo/sync_docs_issues.sh --json
  GITHUB_PERSONAL_ACCESS_TOKEN=... bash scripts/engineering/repo/sync_docs_issues.sh --apply --skip-milestone
  GITHUB_PERSONAL_ACCESS_TOKEN=... bash scripts/engineering/repo/sync_docs_issues.sh --apply --create-milestone

Notes:
  - Dry-run is the default mode.
  - Real GitHub writes require --apply plus a token in
    GITHUB_PERSONAL_ACCESS_TOKEN, unless --token-env points to another env var.
  - Use --skip-milestone if the token cannot manage milestones but can still
    update issues and post comments.
  - All arguments are forwarded to scripts/engineering/repo/sync_docs_issues.py.
EOF
  exit 0
fi

if command -v python3 >/dev/null 2>&1; then
  exec python3 "${PYTHON_SCRIPT}" "$@"
fi

if command -v python >/dev/null 2>&1; then
  exec python "${PYTHON_SCRIPT}" "$@"
fi

echo "[FAIL] python3 or python is required to run ${PYTHON_SCRIPT}" >&2
exit 1
