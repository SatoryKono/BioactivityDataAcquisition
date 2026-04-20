#!/usr/bin/env bash
set -euo pipefail

OWNER="SatoryKono"
REPO="BioactivityDataAcquisition"
ISSUE_NUMBER="2594"
API="https://api.github.com/repos/${OWNER}/${REPO}"

usage() {
  cat <<'EOF'
Usage:
  bash scripts/ops/maintenance/close_pandera_schema_drift_issue.sh [--dry-run]

Environment:
  GITHUB_PERSONAL_ACCESS_TOKEN   Fine-grained or classic token with issue write access

Behavior:
  - posts a closing comment to issue #2594
  - closes issue #2594
  - references the representative Silver schema drift gate implementation
EOF
  return 0
}

DRY_RUN=0
if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  usage
  exit 0
fi
if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=1
elif [[ -n "${1:-}" ]]; then
  printf 'Unknown argument: %s\n\n' "${1:-}" >&2
  usage >&2
  exit 2
fi

: "${GITHUB_PERSONAL_ACCESS_TOKEN:?Set GITHUB_PERSONAL_ACCESS_TOKEN first}"

api() {
  local method="$1"
  local path="$2"
  local data="${3:-}"
  if [[ "$DRY_RUN" -eq 1 ]]; then
    printf '[DRY-RUN] %s %s\n' "$method" "$path"
    if [[ -n "$data" ]]; then
      printf '%s\n\n' "$data"
    fi
    return 0
  fi

  if [[ -n "$data" ]]; then
    curl -fsS -X "$method" \
      -H "Accept: application/vnd.github+json" \
      -H "Authorization: Bearer ${GITHUB_PERSONAL_ACCESS_TOKEN}" \
      -H "X-GitHub-Api-Version: 2022-11-28" \
      -H "Content-Type: application/json" \
      "${API}${path}" \
      --data "$data" >/dev/null
  else
    curl -fsS -X "$method" \
      -H "Accept: application/vnd.github+json" \
      -H "Authorization: Bearer ${GITHUB_PERSONAL_ACCESS_TOKEN}" \
      -H "X-GitHub-Api-Version: 2022-11-28" \
      "${API}${path}" >/dev/null
  fi
  return 0
}

json_comment() {
  python3 -c 'import json, sys; print(json.dumps({"body": sys.stdin.read()}))'
  return 0
}

json_state_patch() {
  python3 - <<'PY'
import json
print(json.dumps({"state": "closed"}))
PY
  return 0
}

api POST "/issues/${ISSUE_NUMBER}/comments" "$(cat <<'EOF' | json_comment
Implementation completed for the initial Pandera schema drift gate.

Delivered:
- representative Silver schema drift gate for selected pipelines
- shared snapshot assertion helper reused from the existing `silver_schemas` contract suite
- schema governance CI job for the representative subset
- documentation updates for local execution and snapshot update workflow

Representative pipelines covered in the initial gate:
- `chembl_activity`
- `pubchem_compound`
- `pubmed_publication`
- `uniprot_protein`

Validation:
- targeted representative schema drift suite passes locally
- existing schema stability subset for the same representative schemas also passes locally

This closes the initial MVP described in the issue without introducing a second validation framework or a parallel schema drift mechanism.
EOF
)"

api PATCH "/issues/${ISSUE_NUMBER}" "$(json_state_patch)"

printf 'Done.\n'
printf 'Closed: #%s\n' "${ISSUE_NUMBER}"
printf 'Representative gate: tests/contract/silver_schemas/test_selected_pipeline_schema_drift.py\n'
