## Problem

The seven shipped Grafana dashboards do not share an enforceable Provenance
readability contract. Existing text panels use `font-size:12px` (about 9 pt),
while the target operator size is 12–14 pt. Styling and scope grammar also
drift between dashboards.

Runtime evidence:

- complete 12-profile render matrix:
  `reports/observability/grafana/gra-rt-closeout/matrix/matrix-manifest.json`
- standard viewports: 1366×768, 1440×900, 1920×1080
- kiosk viewports: 2560×1440, 3840×2160
- dark and light themes
- terminal-state validation and repeat geometry: `ok`

## Scope

Define and enforce a shared Provenance panel contract based on the shipped
`4. Data Quality` design:

- orange accent `border-left:4px solid #ff9830`
- background `rgba(255,152,48,0.08)`
- body text `16px` (12 pt equivalent)
- headline `18px` (13.5 pt equivalent), weight 700
- `line-height:1.35`
- normal wrapping, `overflow-wrap:anywhere`, no internal scrollbar
- readable line length in kiosk mode (target `max-width:96ch`)
- two-level content: operator question, then explicit scope semantics
- Provenance and adjacent Status panels use `gridPos.h >= 4`

Keep CSS sizes in pixels because Grafana/Playwright layout is CSS-pixel based.

## Acceptance criteria

- [ ] A repo-backed contract test covers every shipped dashboard.
- [ ] Body text is at least `16px`; headline is `18px`.
- [ ] The Data Quality accent/background/padding pattern is canonical.
- [ ] No Provenance-equivalent panel uses `white-space:nowrap`.
- [ ] Every shipped dashboard has a Provenance or explicitly mapped
      Provenance-equivalent panel.
- [ ] JSON validation and dashboard visual-semantics checks pass.
- [ ] Runtime render matrix passes dark/light, standard/kiosk, full-page, and
      repeat-consistency profiles.
- [ ] No clipping, horizontal overflow, missing panel, or terminal-state error
      is present.

## Validation

```bash
python -m json.tool grafana/dashboards/<dashboard>.json
python -m scripts.engineering.qa check-dashboard-visual-semantics
pytest -q tests/integration/test_grafana_config.py
python -m scripts.ops render-grafana-matrix \
  --output-dir reports/observability/grafana/provenance-readability-closeout \
  --timeout-seconds 120
```

