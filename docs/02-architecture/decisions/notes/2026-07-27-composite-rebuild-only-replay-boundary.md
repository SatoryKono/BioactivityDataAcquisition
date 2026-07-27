# Decision note: Composite exact-replay vs rebuild_only

**Date:** 2026-07-27
**Code:** ARCH-QA-08 / #6747
**Status:** Accepted (document existing runtime boundary)
**Option selected:** **A — Keep rebuild_only for composite families**

## Context

Independent architecture audit (2026-07-27) observed that composite
reproducibility profiles intentionally set:

- `strict_exact_replay_supported=False`
- `support_state="rebuild_only"`
- `replay_family_contract="rebuild_only"`

Evidence:
`src/bioetl/domain/control_plane/_reproducibility_profile_builders.py`
(`_build_composite_reproducibility_family_profile`).

## Decision

Composite launches remain **outside** the strict exact-replay boundary.

Operators and control-plane consumers **MUST** treat composite runs as:

- lineage-closure capable where implemented
- **rebuild/resume/debug** support scope only
- not certified for post-capture exact parent promotion unless a future
  product decision expands certified composite families (Option B)

## Rationale

1. Runtime already fail-closes exact-replay claims for composite.
2. Expanding exact-replay requires product scope, certified lineage evidence,
   and dedicated tests — not a silent scorecard interpretation change.
3. Source-pipeline exact-replay remains the supported boundary.

## Consequences

- Docs/runbooks should say “rebuild_only” for composite, not “exact replay”.
- Scorecard determinism category may stay high only if it measures enforced
  boundaries rather than “all families exact-replayable”.
- Option B (certified composite exact-replay) requires a new ADR + tests and
  is **out of scope** for ARCH-QA-08 closeout.

## References

- ADR-044 / ADR-046 / ADR-047 (control-plane / replay family)
- Epic #6740
