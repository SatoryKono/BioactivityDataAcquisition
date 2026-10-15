# Stream 2 — Trust anchors, latency legend, fleet Severity, nav chrome

Issues: #10247 (T2/T3), #10248 (T4), #10252 (H2), #10257 (C3)
Parent: #10258
Branch: `fix/grafana-vis-stream2-layout`

## What landed

| Issue | Panel / surface | Change |
| --- | --- | --- |
| #10247 T2 | control-plane `9406/9408/9409` | Operator columns Parameter / Current / Result / Action; hide `copy_mode`/`copy_value`; inspect for full IDs |
| #10247 T3 | control-plane `9405/9407` | `value_short` as Current; `value_full` hidden; height ≤ 8 |
| #10248 T4 | control-plane `111` + var `read_latency_quantile` | Single p95 series by default; p50/p99 via selector; table legend last/max; reads axis `reads / $__interval` |
| #10252 H2 | provider `9101` | Severity `minWidth` 160, Provider width 130; Non-OK/full-fleet tables stay in collapsed row `y>=18` |
| #10257 C3 | nav bus + background stats | `gap:8px`, chip `padding:0 8px`; background stats `valueSize=20` / `titleSize=14` |

Helper (not a `scripts/` generator): `apply_vis_stream2_layout.py.txt`.

## Tests

```powershell
.\.venv-win\Scripts\python.exe -m pytest --timeout=180 `
  tests/integration/test_dashboard_vis_stream2_layout.py `
  tests/integration/test_dashboard_operator_readability.py `
  tests/integration/test_dashboard_first_window_noscroll.py `
  tests/integration/test_dashboard_visual_semantics.py
```

Static tests do not replace browser acceptance at 1920×1080 and 1600×900.
