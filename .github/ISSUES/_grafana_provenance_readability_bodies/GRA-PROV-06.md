## Problem

`5. Incident Workspace` panel `id=9400` mixes incident question, confidence
path, selectors, and empty-domain semantics in dense `12px` text.

## Proposed change

Apply the shared Data Quality Provenance design with:

- headline: **What is the highest-confidence active suspect?**
- scope line:
  `CURRENT = Status/active suspects · SELECTED RUN = exact-run proof`
- empty-state line:
  `EMPTY DOMAIN = no active suspects, not a healthy-fleet verdict`

Increase Provenance and adjacent Status to `gridPos.h=4`; preserve stable IDs
and labelled-status semantics.

## Acceptance criteria

- [ ] Body is `16px`; headline is `18px`.
- [ ] Empty-domain semantics remain explicit.
- [ ] Status labels remain authoritative; bare numeric verdicts are not added.
- [ ] Data Quality accent/background pattern is used.
- [ ] No clipping in dark/light or kiosk renders.
- [ ] Terminal-state and repeat-geometry checks pass.

## Evidence

`RUNTIME_RENDER` + `DASHBOARD_JSON`, confidence `FACT`.

