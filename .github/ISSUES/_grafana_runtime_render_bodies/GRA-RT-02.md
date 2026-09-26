Parent: #7167

Task ID: `GRA-RT-02`
Priority: `P1`

## Problem

The server-side Render API produced all required first-viewport PNGs, but it
cannot prove datasource completion or panel terminal states. Consequently,
`Missing Panels` remains `UNKNOWN` for the standard 1366×768, 1440×900, and
1920×1080 groups. Only the 1440×900 full-page Playwright group established
193/193 required non-row panels.

## Evidence

- `reports/observability/grafana/render-audit-20260729/AUDIT.md`
- six standard Render API manifests under
  `reports/observability/grafana/render-audit-20260729/`
- Playwright manifest under `1440x900-dark-full/`

Evidence source: `RUNTIME_RENDER`, `BROWSER_INSPECTION`

Confidence: `FACT`

## Scope

Extend the canonical Playwright renderer to:

- capture first viewport and full page for 1366×768, 1440×900, and 1920×1080;
- support Dark and Light render groups;
- wait for datasource requests and explicit panel terminal states;
- record loading markers, error markers, rendered panel count, missing panel
  IDs, actual theme, actual viewport, and browser zoom;
- classify explicit empty/incomplete states separately from render failure;
- keep manifests free of credentials and sensitive values.

## Acceptance criteria

- [ ] Every standard browser render group records a verified terminal-state
      status.
- [ ] `Missing Panels` is a checked list or `None`, not an unsupported
      assertion.
- [ ] First-viewport and full-page artifacts share one render-group identity.
- [ ] Actual viewport, theme, zoom, time range, variables, and timestamp are
      persisted in the manifest.
- [ ] `UNKNOWN`/`INCOMPLETE`/`No data` terminal panels are not classified as
      render failures.
- [ ] All seven dashboard UIDs complete the matrix in Dark and Light.
- [ ] Existing server-side rendering remains available as a fast path.

## Validation

```bash
.venv/bin/python -m scripts.ops check-grafana-audit-preflight
.venv/bin/python -m scripts.ops rerender-grafana
.venv/bin/python -m scripts.ops audit-live-grafana
.venv/bin/python -m pytest -q tests/integration/test_grafana_render_*.py
```

## Out of scope

- dashboard redesign;
- new metrics;
- replacing runtime rendering with static image inspection.

