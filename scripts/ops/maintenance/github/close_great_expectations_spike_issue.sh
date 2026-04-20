#!/usr/bin/env bash
set -euo pipefail

OWNER="SatoryKono"
REPO="BioactivityDataAcquisition"
ISSUE_NUMBER="2595"
API="https://api.github.com/repos/${OWNER}/${REPO}"
SPIKE_MEMO_PATH="docs/reports/great-expectations-spike-2026-04-01.md"

usage() {
  cat <<'EOF'
Usage:
  bash scripts/ops/maintenance/close_great_expectations_spike_issue.sh [--dry-run]

Environment:
  GITHUB_PERSONAL_ACCESS_TOKEN   Fine-grained or classic token with issue write access

Behavior:
  - posts a closing comment to issue #2595
  - closes issue #2595
  - references the completed repo-native spike memo
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

api POST "/issues/${ISSUE_NUMBER}/comments" "$(cat <<EOF | json_comment
Spike completed.

Outcome: no-go for immediate Great Expectations adoption.

Decision memo:
- \`${SPIKE_MEMO_PATH}\`

Summary:
- Current BioETL quality stack already covers the active needs through Pandera runtime validation, contract tests, DQ thresholds/anomaly handling, and ADR-036-driven contract governance.
- Great Expectations would add a second validation workflow surface with more operational overhead than near-term value.
- Revisit only if the project later needs stakeholder-facing validation reports, persistent checkpoint/action workflows, or warehouse-style multi-asset validation.

No follow-up implementation issue is being opened from this spike.
EOF
)"

api PATCH "/issues/${ISSUE_NUMBER}" "$(json_state_patch)"

printf 'Done.\n'
printf 'Closed: #%s\n' "${ISSUE_NUMBER}"
printf 'Memo: %s\n' "${SPIKE_MEMO_PATH}"
