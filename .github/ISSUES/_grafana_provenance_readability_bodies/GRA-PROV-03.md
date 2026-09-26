## Problem

`2. Pipeline Diagnostics` panel `id=9400` presents pipeline/stage selectors and
the `SCRAPING` caveat as dense inline `12px` text. The distinction between
execution evidence and delivery outcome is important but visually weak.

## Proposed change

Apply the shared Data Quality Provenance design with:

- headline: **Is the pipeline progressing, and what is blocking delivery?**
- scope line:
  `CURRENT = health/phase/blockers · SELECTED RUN = ID/accounting`
- diagnostic line:
  `STAGE = diagnostic context · SCRAPING does not mean delivery OK`

Increase Provenance and adjacent Status to `gridPos.h=4`; preserve stable IDs
and the 16/8 width split.

## Acceptance criteria

- [ ] Body is `16px`; headline is `18px`.
- [ ] `SCRAPING ≠ delivery OK` is visually distinct and not clipped.
- [ ] Long pipeline/stage selections do not produce horizontal overflow.
- [ ] Data Quality accent/background pattern is used.
- [ ] Dark/light, standard/kiosk, full-page, and repeat renders pass.
- [ ] Terminal-state validation remains `ok`.

## Evidence

`RUNTIME_RENDER` + `DASHBOARD_JSON`, confidence `FACT`.

