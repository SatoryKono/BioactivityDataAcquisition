#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
UPDATE_SCRIPT="${SCRIPT_DIR}/update_github_issue.sh"
DEFAULT_OWNER="SatoryKono"
DEFAULT_REPO="BioactivityDataAcquisition"

usage() {
  cat <<'EOF'
Usage:
  bash scripts/ops/update_issue_rescope_bodies.sh [--apply] [--owner NAME] [--repo NAME] [--issue NUMBER]...

Options:
  --apply        Update GitHub issue bodies. Default mode is dry-run.
  --owner NAME   Repository owner (default: SatoryKono)
  --repo NAME    Repository name (default: BioactivityDataAcquisition)
  --issue NUM    Restrict to one issue number; may be repeated.
  -h, --help     Show this help

Environment:
  GITHUB_PERSONAL_ACCESS_TOKEN   Required only with --apply
  GH_TOKEN                       Alternative token env var
  GITHUB_TOKEN                   Alternative token env var

Behavior:
  - replaces prepared issue bodies for issue(s) #2600, #2516, #2515, #2511
  - uses dry-run by default so the PATCH payload can be reviewed safely first

Examples:
  bash scripts/ops/update_issue_rescope_bodies.sh
  bash scripts/ops/update_issue_rescope_bodies.sh --issue 2600 --issue 2516
  GITHUB_PERSONAL_ACCESS_TOKEN=... bash scripts/ops/update_issue_rescope_bodies.sh --apply
EOF
  return 0
}

OWNER="$DEFAULT_OWNER"
REPO="$DEFAULT_REPO"
APPLY=0
declare -a REQUESTED_ISSUES=()

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
    --issue)
      REQUESTED_ISSUES+=("${2:-}")
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

tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT

cat >"$tmpdir/2600.md" <<'EOF'
## Summary

Current control-plane work already introduced `RunManifest` and `RunLedger`
surfaces, but the remaining work is now about finishing replay/resume semantics
and standardizing execution lifecycle events rather than introducing a
brand-new universal execution contract.

## Why

The repository already has:
- `RunManifest` as an immutable control-plane artifact
- append-only ledger entries and inspection surfaces
- file-backed manifest and ledger stores
- CLI and diagnostics around control-plane artifacts

What is still missing is a fully aligned replay/resume model and a stable
lifecycle/event taxonomy across ordinary and composite execution paths.

## Important Clarification

`RunManifest` is a provenance/control-plane artifact.

It does **not** replace `PipelineRunContext` or `PipelineContext` as the runtime
execution descriptor.

This issue should therefore not be treated as “replace all runtime contexts
with one manifest object”.

## Goal

Finish the existing RunManifest/RunLedger replay model and checkpoint
integration without collapsing runtime contexts into a universal manifest
object.

## Scope

### 1. Replay / Resume Contract
- Align checkpoint snapshot loading with ledger replay semantics
- Define the canonical relationship between checkpoint state and ledger state
- Ensure resume behavior is deterministic and documented

### 2. Lifecycle / Event Taxonomy
- Normalize stage and event naming for ordinary execution paths
- Normalize stage and event naming for composite execution paths
- Keep event semantics stable across diagnostics, metrics, and inspection
  tooling

### 3. Control-Plane Coverage
- Ensure supported execution paths emit manifest/ledger artifacts consistently
  when control-plane is enabled
- Remove residual paths where runtime correlation anchors bypass the
  manifest/ledger surface

### 4. Documentation / Contracts
- Document the actual boundary between runtime contexts and control-plane
  artifacts
- Keep inspection and operational runbooks aligned with the implemented model

## Out of Scope
- Replacing runtime execution contexts with `RunManifest`
- Rewriting storage layers unrelated to control-plane behavior
- Broad business-logic changes in pipelines
- A full event-sourcing rewrite of the entire runtime model

## Acceptance Criteria
- [ ] Ordinary and composite runners emit canonical lifecycle events into the
      ledger
- [ ] Replay semantics for checkpoint resume are documented and covered by
      tests
- [ ] No new execution path bypasses manifest/ledger when control-plane is
      enabled
- [ ] Stage/event taxonomy is stable and consistent across runners
- [ ] Docs reflect the implemented split between runtime context and
      control-plane artifacts

## Related
- ADR-044 Run Manifest / Ledger Control Plane
- Related to lineage and observability follow-up work
EOF

cat >"$tmpdir/2516.md" <<'EOF'
## Summary

The repository already has schema-governance workflows, parity checks, and
selected schema-drift gates. The remaining gap is a Gold-focused compatibility
classifier that can distinguish clearly compatible changes from clearly
breaking ones in CI.

## Why

Existing governance already covers:
- generated schema artifacts freshness
- contract import validation
- Silver ↔ Gold parity checks
- representative Silver schema drift checks

What is still missing is an explicit Gold compatibility gate aligned with
ADR-036 style rules.

## Goal

Add explicit Gold compatibility classification on top of the existing
schema-governance gates.

## Scope

### 1. Gold Compatibility Rule Set
Start with a small, explicit ruleset:
- adding a nullable column = compatible
- removing a column = breaking
- renaming a column = breaking
- narrowing a type = breaking
- changing nullable to non-nullable = breaking

### 2. Gold-Focused Diffing
- Detect Gold schema changes in PRs
- Classify them using the explicit rule set
- Produce readable diagnostics that explain what changed and why it is
  compatible or breaking

### 3. CI Integration
- Add the compatibility classifier on top of the current schema-governance
  workflow
- Fail CI only on breaking Gold contract changes
- Keep the implementation maintainable and easy to extend

### 4. Documentation
- Document the rule set
- Document how to update the baseline
- Document the extension path for intentional, approved changes

## Out of Scope
- Consumer registry / downstream ownership automation
- Slack or notification automation
- Full end-to-end schema governance for every layer in one issue
- Broad deprecation workflow automation

## Acceptance Criteria
- [ ] Adding nullable columns is classified as compatible
- [ ] Removing or renaming columns is classified as breaking
- [ ] Narrowing types is classified as breaking
- [ ] Changing nullable to non-nullable is classified as breaking
- [ ] CI output explains the exact Gold contract diff in human-readable form
- [ ] Documentation explains how the rule set works and how to extend it

## Related
- ADR-036 direction for Gold contract versioning
- Complements existing schema-governance workflow rather than replacing it
EOF

cat >"$tmpdir/2515.md" <<'EOF'
## Summary

A lineage MVP is already partially present in the repository. The remaining
work is to complete and standardize the supported Bronze -> Silver -> Gold
lineage path rather than introducing lineage from zero.

## Why

The repository already has:
- a domain lineage model
- file-backed lineage fragment persistence
- lineage fragment builders
- CLI inspection / trace / explain surfaces
- linkage between lineage and control-plane diagnostics

The open gap is to make the supported lineage flow explicit, complete, and
consistently testable.

## Goal

Complete and standardize the existing lineage MVP for representative Bronze ->
Silver -> Gold flows.

## Scope

### 1. Supported Flow Definition
- Choose one or a small number of representative Bronze -> Silver -> Gold
  pipeline families
- Define those as the supported MVP lineage surface

### 2. Propagation Completeness
- Ensure lineage refs and run metadata propagate correctly through the selected
  flows
- Close gaps in canonical refs, persistence, and lookup behavior

### 3. Trace / Debug Path
- Provide a practical path from an output artifact or dataset ref back to
  upstream run context
- Ensure that path works through the supported inspection surface

### 4. Verification
- Add or tighten tests for lineage propagation and lookup
- Keep docs aligned with what is supported now versus what remains future work

## Out of Scope
- A full lineage graph platform for every pipeline
- External lineage UI work
- Solving every composite lineage scenario in the same issue
- Long-term retention design for all lineage payloads

## Acceptance Criteria
- [ ] At least one representative Bronze -> Silver -> Gold family is covered
      end-to-end
- [ ] Lineage refs are persisted and queryable through the supported
      inspection surface
- [ ] A documented trace/debug path exists from output artifact or dataset back
      to run context
- [ ] Tests verify propagation and lookup behavior for the supported flows
- [ ] Docs clearly define what is supported now versus future lineage
      expansion

## Related
- Related to schema governance and provenance work
- Can later complement external lineage artifact efforts
EOF

cat >"$tmpdir/2511.md" <<'EOF'
## Summary

Track practical testing improvements as a parent roadmap rather than treating
this issue as a single implementation ticket.

## Why

The repository already benefits more from smaller executable child issues than
from one large testing umbrella. This issue should remain the coordination
layer for the testing roadmap.

## Purpose

Parent roadmap for testing governance tracks. Execution should happen in child
issues.

## Tracks

### 1. Unit Test Standards
- Define expectations for pure transformation logic and high-signal unit
  coverage
- Improve coverage in the most valuable areas first
- Keep edge-case expectations explicit

### 2. Integration and VCR Policy
- Tighten conventions for integration and e2e coverage
- Keep fixture and cassette governance explicit
- Keep local and CI execution paths aligned

### 3. Contract Drift Checks
- Add focused external provider drift checks where risk is meaningful
- Prefer small, readable checks over a broad framework rollout

### 4. Data Validation Gates
- Define where Pandera or equivalent validation belongs in the quality model
- Add small, high-signal gates incrementally

## Out of Scope
- Delivering the entire testing strategy in one issue
- Blanket enforcement across the whole repository from one ticket
- Immediate rollout of every possible testing framework

## Coordination Checklist
- [ ] Unit standards track has an executable child issue or completed
      implementation note
- [ ] Integration/VCR policy track is tracked in a child issue
- [ ] Contract drift track is tracked in a child issue
- [ ] Data validation gates track is tracked in a child issue
- [ ] Parent issue links current child issues and marks completed ones
- [ ] Parent body clearly distinguishes roadmap tracking from active
      implementation

## Notes

This issue should stay open only as a coordination/meta artifact.

Concrete work should happen in smaller scoped child issues with explicit
acceptance criteria and bounded blast radius.

## Related
- Links to child issues should be maintained here as the roadmap evolves
EOF

body_file_for_issue() {
  local issue_number="$1"
  case "$issue_number" in
    2600|2516|2515|2511)
      printf '%s/%s.md\n' "$tmpdir" "$issue_number"
      ;;
    *)
      printf ''
      ;;
  esac
  return 0
}

declare -a TARGET_ISSUES
if [[ "${#REQUESTED_ISSUES[@]}" -eq 0 ]]; then
  TARGET_ISSUES=(2600 2516 2515 2511)
else
  TARGET_ISSUES=("${REQUESTED_ISSUES[@]}")
fi

for issue in "${TARGET_ISSUES[@]}"; do
  case "$issue" in
    2600|2516|2515|2511)
      ;;
    *)
      printf '[FAIL] Unsupported issue number: %s\n' "$issue" >&2
      printf 'Supported issues: 2600, 2516, 2515, 2511\n' >&2
      exit 2
      ;;
  esac
done

for issue in "${TARGET_ISSUES[@]}"; do
  body_file="$(body_file_for_issue "$issue")"
  printf '[INFO] Preparing re-scope body for issue #%s in %s/%s\n' \
    "$issue" "$OWNER" "$REPO"

  args=(
    --issue "$issue"
    --owner "$OWNER"
    --repo "$REPO"
    --body-file "$body_file"
  )
  if [[ "$APPLY" -eq 0 ]]; then
    args+=(--dry-run)
  fi

  bash "$UPDATE_SCRIPT" "${args[@]}"
  printf '\n'
done

printf '[INFO] Prepared %s re-scope body update(s).\n' "${#TARGET_ISSUES[@]}"
