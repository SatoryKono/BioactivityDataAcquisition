#!/usr/bin/env bash
set -euo pipefail

OWNER="SatoryKono"
REPO="BioactivityDataAcquisition"
API="https://api.github.com/repos/${OWNER}/${REPO}"

usage() {
  cat <<'EOF'
Usage:
  bash scripts/ops/maintenance/triage_cleanup_issue_wave.sh [--dry-run]

Environment:
  GITHUB_PERSONAL_ACCESS_TOKEN   Fine-grained or classic token with issue write access

Behavior:
  - closes issues #2506, #2510, #2512, #2513
  - updates title/body for #2511, #2515, #2516
  - adds explanatory comments to those issues
  - assumes follow-up issues #2593, #2594, #2595 already exist
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

json_patch_from_files() {
  local title_file="$1"
  local body_file="$2"
  local state="${3:-}"
  python3 - "$title_file" "$body_file" "$state" <<'PY'
import json
import pathlib
import sys

title = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8").strip()
body = pathlib.Path(sys.argv[2]).read_text(encoding="utf-8")
state = sys.argv[3]

payload = {"title": title, "body": body}
if state:
    payload["state"] = state

print(json.dumps(payload, ensure_ascii=False))
PY
  return 0
}

patch_state_only() {
  local issue="$1"
  local state="$2"
  local payload
  payload="$(python3 - <<PY
import json
print(json.dumps({"state": "${state}"}))
PY
)"
  api PATCH "/issues/${issue}" "$payload"
  return 0
}

tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT

cat >"$tmpdir/2511_title.txt" <<'EOF'
Testing Roadmap: unit standards, VCR integration, contract drift, data validation gates
EOF

cat >"$tmpdir/2511_body.md" <<'EOF'
## Summary

Track the next practical testing improvements as a phased roadmap instead of a single platform-wide testing umbrella.

## Why

The original issue is directionally correct, but too broad to execute as one deliverable. This rewritten version keeps the intent while narrowing the work into concrete tracks that can be delivered incrementally.

## Scope

### 1. Unit test standards
- Define and document expectations for unit tests around pure transformation logic.
- Improve coverage in the highest-value areas rather than targeting blanket coverage in one pass.
- Capture edge-case expectations for empty data, malformed inputs, Unicode, and null handling where relevant.

### 2. Integration and VCR policy
- Tighten conventions for integration and e2e coverage.
- Clarify fixture and cassette expectations.
- Make the supported local and CI execution paths explicit.

### 3. Contract drift checks
- Identify a minimal contract-testing approach for external providers where drift risk is real.
- Prefer focused schema or field drift checks over a platform-wide framework rollout.

### 4. Data validation gates
- Define where Pandera or equivalent validation belongs in the existing quality model.
- Add small, high-signal validation gates before attempting broad platform coverage.

## Out of Scope

- Delivering the complete testing strategy for every provider and pipeline in one issue.
- Blanket coverage enforcement across the whole repository as part of this single task.
- Immediate rollout of every possible testing framework mentioned in the original issue.

## Acceptance Criteria

- [ ] A documented phased testing roadmap exists in-repo or in linked issues.
- [ ] Follow-up issues exist for the concrete workstreams that should be implemented next.
- [ ] At least one near-term improvement from each chosen track is clearly scoped for execution.
- [ ] The resulting plan aligns with the current governance and maintenance model.

## Related

- Related to #2506
- Related to #2515
- Related to #2516
EOF

cat >"$tmpdir/2515_title.txt" <<'EOF'
Lineage Metadata MVP for Bronze -> Silver -> Gold flows
EOF

cat >"$tmpdir/2515_body.md" <<'EOF'
## Problem

The repository does not yet have a lightweight, standard way to propagate lineage metadata across key Bronze -> Silver -> Gold flows for debugging, reproducibility, and governance.

## Goal

Deliver a minimal lineage metadata MVP that fits the current architecture and can be extended later without committing the project to a full lineage platform rollout immediately.

## Scope

- Define a minimal lineage metadata model for selected flows.
- Propagate lineage identifiers and run metadata through representative Bronze -> Silver -> Gold paths.
- Record enough metadata to support practical debugging and provenance lookup for those paths.
- Add a small helper or query path that can trace the lineage of a selected output record or batch back to its upstream run context.
- Document the conventions so future pipelines can adopt the same pattern.

## Out of Scope

- A full lineage graph store for the whole platform.
- Long-term retention or storage policy design for raw payloads.
- External UI or integration work as part of the MVP.
- Solving every composite-pipeline lineage scenario in the same issue.

## Acceptance Criteria

- [ ] Minimal lineage metadata is defined and documented.
- [ ] Representative Bronze -> Silver -> Gold flows propagate that metadata correctly.
- [ ] A practical trace or debug path exists for the covered flows.
- [ ] Tests verify propagation and lookup behavior for the MVP scope.

## Related

- Can later integrate with #2506 follow-up lineage work
- Related to #2516 for governance and compatibility concerns
EOF

cat >"$tmpdir/2516_title.txt" <<'EOF'
Gold Schema Compatibility CI Gate (ADR-036 MVP)
EOF

cat >"$tmpdir/2516_body.md" <<'EOF'
## Problem

ADR-036 defines the direction for Gold contract versioning, but the repository still needs a practical CI gate that catches obviously breaking schema changes before merge.

## Goal

Implement a minimal compatibility gate for Gold schema changes in CI, with readable output and clear breaking-change rules.

## Scope

- Establish a baseline representation for current Gold schemas.
- Detect schema changes in PRs that affect Gold outputs.
- Classify obviously compatible vs breaking changes using a small explicit rule set.
- Fail CI on breaking changes unless the approved project process says otherwise.
- Produce human-readable diff output that explains what changed.

## Compatibility Rules to Cover First

- Adding a nullable column: compatible
- Removing a column: breaking
- Renaming a column: breaking
- Narrowing a type: breaking
- Changing nullable to non-nullable: breaking

## Out of Scope

- Consumer registry and downstream ownership tracking.
- Slack or notification automation.
- Full deprecation workflow automation.
- End-to-end schema governance for every layer in one issue.

## Acceptance Criteria

- [ ] Current Gold schema baseline is captured in a maintainable form.
- [ ] CI can detect and classify the initial rule set of schema changes.
- [ ] Breaking changes fail with readable diagnostics.
- [ ] Documentation explains how the gate works and how to extend it.

## Related

- Builds on ADR-036 intent
- Related to #2515 for future governance and provenance interactions
EOF

api POST "/issues/2506/comments" "$(cat <<'EOF' | json_comment
Triage update: closing this issue as an umbrella because it bundles three separable workstreams. Follow-up issues were opened to keep planning and delivery actionable:

- #2593 OpenLineage CI Artifact Emission MVP
- #2594 Pandera Schema Drift Checks for Selected Pipelines
- #2595 Spike: Great Expectations Integration for Data Quality Checks

The narrower split should make prioritization, implementation, and review much easier.
EOF
)"
patch_state_only 2506 closed

api POST "/issues/2510/comments" "$(cat <<'EOF' | json_comment
Closing as not aligned with the current roadmap. This is a broad exploratory platform feature, and it is too large and open-ended for the current repository priorities. If debugging UX becomes a priority later, it should return as a much narrower CLI/TUI MVP with explicit integration boundaries.
EOF
)"
patch_state_only 2510 closed

api POST "/issues/2512/comments" "$(cat <<'EOF' | json_comment
Closing as superseded. Documentation, governance, and onboarding work are already represented much more concretely in the current repository structure and ongoing docs maintenance wave. Keeping this broad umbrella issue open no longer helps execution. If a real gap remains, it should come back as a narrower issue against a specific documentation surface.
EOF
)"
patch_state_only 2512 closed

api POST "/issues/2513/comments" "$(cat <<'EOF' | json_comment
Closing as implemented or superseded by the existing documentation validation and tooling direction already present in the repository. If additional gaps remain, they should be reopened as focused follow-up issues for the missing validation mode rather than as one large umbrella request.
EOF
)"
patch_state_only 2513 closed

api PATCH "/issues/2511" "$(json_patch_from_files "$tmpdir/2511_title.txt" "$tmpdir/2511_body.md")"
api POST "/issues/2511/comments" "$(cat <<'EOF' | json_comment
Retriaged from a broad strategy umbrella into a phased execution roadmap. Concrete follow-up work should now be split and delivered incrementally instead of keeping the entire testing platform vision in one issue.
EOF
)"

api PATCH "/issues/2515" "$(json_patch_from_files "$tmpdir/2515_title.txt" "$tmpdir/2515_body.md")"
api POST "/issues/2515/comments" "$(cat <<'EOF' | json_comment
Retriaged to MVP scope. Full graph-store, retention-policy, and UI ambitions are intentionally out of scope here; this issue should establish the smallest viable lineage metadata path first.
EOF
)"

api PATCH "/issues/2516" "$(json_patch_from_files "$tmpdir/2516_title.txt" "$tmpdir/2516_body.md")"
api POST "/issues/2516/comments" "$(cat <<'EOF' | json_comment
Retriaged to an ADR-036 compatibility-gate MVP. Registry, notifications, and deprecation workflow automation should follow only after the base CI guardrail exists and proves useful.
EOF
)"

printf 'Done.\n'
printf 'Closed: #2506 #2510 #2512 #2513\n'
printf 'Updated: #2511 #2515 #2516\n'
printf 'Created earlier: #2593 #2594 #2595\n'
