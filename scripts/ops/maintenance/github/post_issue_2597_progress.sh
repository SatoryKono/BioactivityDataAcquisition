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
  bash scripts/ops/maintenance/post_issue_2597_progress.sh [--apply] [--owner NAME] [--repo NAME]

Options:
  --apply        Send the comment to GitHub. Default mode is dry-run.
  --owner NAME   Repository owner (default: SatoryKono)
  --repo NAME    Repository name (default: BioactivityDataAcquisition)
  -h, --help     Show this help

Environment:
  GITHUB_PERSONAL_ACCESS_TOKEN   Required only with --apply

Examples:
  bash scripts/ops/maintenance/post_issue_2597_progress.sh
  GITHUB_PERSONAL_ACCESS_TOKEN=... bash scripts/ops/maintenance/post_issue_2597_progress.sh --apply
EOF
  return 0
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
Progress update on #2597:

Completed a first bounded implementation slice for the pure transformation unit-test baseline.

Done:
- documented a published baseline for pure transformation logic in `docs/03-guides/testing.md`
- made the expected edge-case coverage explicit: empty inputs, malformed inputs, Unicode values, and `null` / missing semantics
- documented the supported targeted local/CI execution path for pure transformation suites
- strengthened unit coverage for existing pure helpers in:
  - `tests/unit/domain/transformations/test_coercion.py`
  - `tests/unit/domain/test_transformations.py`
  - `tests/unit/domain/test_normalization.py`
  - `tests/unit/application/core/test_dict_transformers.py`

Validation run:
- targeted unit suites: green
- `tests/architecture/test_domain_unit_test_purity.py`: green
- `scripts/docs/check_doc_links.py`: green

Scope intentionally stayed narrow:
- no runtime behavior changes
- no new architecture/runtime surfaces
- no integration/VCR policy work (that stays with #2598)

Remaining work, if we want to extend this issue further, is mostly optional polish (for example, deciding whether a very low-noise guardrail for pure `application/core` helpers is worth adding separately).
EOF

ARGS=(
  --issue "$ISSUE_NUMBER"
  --owner "$OWNER"
  --repo "$REPO"
  --comment-file "$COMMENT_FILE"
)

if [[ "$APPLY" -eq 0 ]]; then
  ARGS+=(--dry-run)
fi

printf '[INFO] Preparing issue #%s progress comment for %s/%s\n' \
  "$ISSUE_NUMBER" "$OWNER" "$REPO"

bash "$UPDATE_SCRIPT" "${ARGS[@]}"
