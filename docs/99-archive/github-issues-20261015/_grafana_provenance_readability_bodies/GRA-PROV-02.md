## Problem

`1. Overview` panel `id=99` interpolates a potentially long pipeline selection
inside a fixed-height `12px` banner. The 1366×768 runtime render visibly clips
the selector context at the right edge.

## Proposed change

Apply the shared Data Quality Provenance design with:

- headline: **What is broken or degraded right now?**
- scope line:
  `CURRENT = Status + First Action · SELECTED RUN = exact-run evidence`
- range line:
  `TIME RANGE = Inputs and trends`

Remove the expanded `$pipeline` value list from on-canvas copy. Preserve exact
selector values in Grafana controls and panel description.

Increase Provenance and adjacent Status to `gridPos.h=4`; shift panels below
without changing stable IDs.

## Acceptance criteria

- [ ] Existing clipping is eliminated at 1366×768.
- [ ] Panel `id=99` remains stable.
- [ ] Body is `16px`; headline is `18px`.
- [ ] Data Quality accent/background and two-level hierarchy are used.
- [ ] Default `All` selector state and multi-pipeline state both wrap safely.
- [ ] Dark/light and standard/kiosk render profiles pass.
- [ ] No horizontal overflow or random layout shift occurs.

## Evidence

`RUNTIME_RENDER` + `DASHBOARD_JSON`, confidence `FACT`.

