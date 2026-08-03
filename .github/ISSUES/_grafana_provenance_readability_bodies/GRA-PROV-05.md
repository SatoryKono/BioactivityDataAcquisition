## Problem

`4. Data Quality` panel `id=9400` is the desired visual reference, but its body
still uses `font-size:12px` (about 9 pt). Increasing typography without
increasing panel height would risk wrapping and clipping.

## Proposed change

Keep the current question and `CURRENT / SELECTED RUN / TIME RANGE` grammar.
Update only the shared visual baseline:

- body `16px`
- headline `18px`
- line height `1.35`
- panel padding `6px 10px`
- `overflow-wrap:anywhere`
- Provenance and Status `gridPos.h=4`

Use this updated panel as the canonical reference for the other dashboards.

## Acceptance criteria

- [ ] Existing operator question and scope semantics are unchanged.
- [ ] Body is `16px`; headline is `18px`.
- [ ] No text clipping at 1366×768.
- [ ] Status remains aligned with Provenance.
- [ ] Current, selected-run, and time-range evidence remain non-peer scopes.
- [ ] Dark/light, standard/kiosk, and repeat renders pass.

## Evidence

`RUNTIME_RENDER` + `DASHBOARD_JSON`, confidence `FACT`.

