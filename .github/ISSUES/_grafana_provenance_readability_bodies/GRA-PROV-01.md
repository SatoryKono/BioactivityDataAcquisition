## Problem

`0. Trust` panel `id=9400` renders its question, decision path, selected
variables, and UNKNOWN guidance as dense inline text at `12px`. The content is
terminal and stable, but it requires unnecessary scanning.

## Proposed change

Apply the shared Data Quality Provenance design with:

- headline: **Can this run be replayed safely?**
- scope line:
  `CURRENT = replay status/reason/action · SELECTED RUN = identity evidence`
- evidence warning:
  `UNKNOWN = incomplete evidence — not OK`

Do not enumerate long selector values on canvas; selectors already expose that
context, while the full provenance description remains available in panel
metadata.

Increase Provenance and adjacent Status to `gridPos.h=4`, then shift dependent
panels without changing their widths or stable IDs.

## Acceptance criteria

- [ ] Panel `9400` keeps its stable ID and `Provenance` title.
- [ ] Body is `16px`; headline is `18px`; line height is at least `1.35`.
- [ ] Data Quality orange accent/background pattern is used.
- [ ] Question, scope, and UNKNOWN semantics are visually separate.
- [ ] No clipping at 1366×768 in dark or light theme.
- [ ] No excessive line length or layout shift at kiosk viewports.
- [ ] Terminal-state and repeat-geometry checks pass.

## Evidence

`RUNTIME_RENDER` + `DASHBOARD_JSON`, confidence `FACT`.

