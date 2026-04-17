#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
UPDATE_SCRIPT="${SCRIPT_DIR}/update_github_issue.sh"
DEFAULT_OWNER="SatoryKono"
DEFAULT_REPO="BioactivityDataAcquisition"
ISSUE_NUMBER="2597"

usage() {
  cat <<'EOF'
Usage:
  bash scripts/ops/maintenance/close_issue_2597.sh [--apply] [--owner NAME] [--repo NAME]

Options:
  --apply        Post the closing comment and close the issue. Default mode is dry-run.
  --owner NAME   Repository owner (default: SatoryKono)
  --repo NAME    Repository name (default: BioactivityDataAcquisition)
  -h, --help     Show this help

Environment:
  GITHUB_PERSONAL_ACCESS_TOKEN   Required only with --apply

Behavior:
  - posts the prepared closing comment to issue #2597
  - closes issue #2597
  - keeps the workflow shell-friendly for WSL/bash maintainers
EOF
}

OWNER="$DEFAULT_OWNER"
REPO="$DEFAULT_REPO"
APPLY=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --apply)
      APPLY=1
      shift
      ;;
    --owner)
      OWNER="${2:-}"
      shift 2
      ;;
    --repo)
      REPO="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      printf 'Unknown argument: %s\n\n' "$1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ ! -f "$UPDATE_SCRIPT" ]]; then
  printf '[FAIL] Missing helper script: %s\n' "$UPDATE_SCRIPT" >&2
  exit 1
fi

COMMENT_FILE="$(mktemp)"
trap 'rm -f "$COMMENT_FILE"' EXIT

cat >"$COMMENT_FILE" <<'EOF'
Implementation for the current #2597 scope is complete.

Delivered:
- published baseline for pure transformation logic in `docs/03-guides/testing.md`
- explicit edge-case expectations for empty, malformed, Unicode, and `null` / missing inputs
- documented targeted local/CI execution path for pure transformation suites
- strengthened unit coverage for representative pure helpers in:
  - `tests/unit/domain/transformations/test_coercion.py`
  - `tests/unit/domain/test_transformations.py`
  - `tests/unit/domain/test_normalization.py`
  - `tests/unit/application/core/test_dict_transformers.py`

Validation:
- targeted pure-transformation unit suites: green
- `tests/architecture/test_domain_unit_test_purity.py`: green
- `scripts/docs/check_doc_links.py`: green

This closes the bounded baseline slice for pure transformation logic without expanding into integration/VCR policy work or introducing new runtime surfaces.
EOF

ARGS=(
  --issue "$ISSUE_NUMBER"
  --owner "$OWNER"
  --repo "$REPO"
  --comment-file "$COMMENT_FILE"
  --state closed
)

if [[ "$APPLY" -eq 0 ]]; then
  ARGS+=(--dry-run)
fi

printf '[INFO] Preparing closeout for issue #%s in %s/%s\n' \
  "$ISSUE_NUMBER" "$OWNER" "$REPO"

bash "$UPDATE_SCRIPT" "${ARGS[@]}"
