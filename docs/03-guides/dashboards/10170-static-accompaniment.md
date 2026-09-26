______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Last verified: '2026-09-11'

______________________________________________________________________

# #10170-B static accompaniment (no Grafana)

Parent: #10170. Child: #10358. Static green is **not** contrast PASS and does
**not** close #10170.

## SHA

`fe1b7ea01c87ede7edcac20f8bc65b53ea2d1416` (`origin/main` at pin #10357).

## Command

```text
.\.venv-win\Scripts\python.exe -m pytest `
  tests/integration/test_dashboard_visual_semantics.py `
  tests/integration/test_dashboard_panel_visualization_standards.py `
  tests/integration/test_dashboard_units_decimals.py `
  tests/integration/test_dashboard_operator_readability.py `
  tests/integration/test_dashboard_first_window_noscroll.py `
  tests/unit/scripts/ops/observability `
  -q --tb=line
```

## Result

- Date: 2026-09-11
- Host: Windows, `.venv-win`
- Exit code: `0`
- Outcome: all selected tests passed

This does not measure DOM contrast, reflow at 200%, or three-viewport PNG.
Capture remains #10359–#10362 after Grafana endpoint approval.
