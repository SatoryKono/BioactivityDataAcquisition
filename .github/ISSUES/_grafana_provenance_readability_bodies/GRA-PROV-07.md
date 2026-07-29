## Problem

`6. Run Explorer` has no panel titled `Provenance`. Panel `id=1`, `Run Scope`,
is its functional equivalent but uses the old gray `12px` inline style and
does not match the shared dashboard grammar.

## Proposed change

Preserve stable panel `id=1` and either title it `Provenance · Run Scope` or
document it as the explicit Provenance-equivalent. Apply the shared Data
Quality visual design with:

- headline: **Which exact run should be inspected?**
- scope line:
  `BROWSE = recent runs · SELECTED RUN = identity/accounting/actions`
- ownership line:
  `FULL PATHS = report artifacts, not triage bodies`

Increase the panel to `gridPos.h=4` and shift dependent panels without
changing their stable IDs or browse/selected mode behavior.

## Acceptance criteria

- [ ] Panel `id=1` remains stable.
- [ ] The Provenance-equivalent mapping is explicit and contract-tested.
- [ ] Body is `16px`; headline is `18px`.
- [ ] Browse and selected-run modes remain clearly distinct.
- [ ] `run_id` remains Ops HTTP identity context and is not added to PromQL.
- [ ] No clipping in dark/light, standard, or kiosk renders.
- [ ] Terminal-state and repeat-geometry checks pass.

## Evidence

`RUNTIME_RENDER` + `DASHBOARD_JSON`, confidence `FACT`.

