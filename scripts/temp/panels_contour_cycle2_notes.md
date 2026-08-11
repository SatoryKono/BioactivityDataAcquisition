# Panels contour cycle-2 notes

run_id=20260811T180000Z-c205349-dash cycle=2 CONTOUR=panels MONITORING=false

## Method (FACT)

- Shipped JSON only under `grafana/dashboards/*.json` (7 files).
- Panel type counts via `"type": "(stat|…|row|text)"` line matches (includes nested row children).
- PromQL metric names cross-checked against `grafana/prometheus-rules/*.yml` records + emitter defs under `src/bioetl/infrastructure/observability/`.
- Empty-target / empty-expr / `or vector(0)` / deprecated token greps.
- Live Grafana/Prometheus **not** started (MONITORING=false).

## Inventory (FACT)

| uid | panels | match inventory |
| --- | ---: | --- |
| bioetl-control-plane-v1 | 63 | yes |
| bioetl-overview-v2 | 26 | yes |
| bioetl-runtime | 42 | yes |
| bioetl-provider-health-v2 | 31 | yes |
| bioetl-dq-v2 | 36 | yes |
| bioetl-incident-v1 | 12 | yes |
| bioetl-run-explorer-v1 | 13 | yes |
| **total** | **223** | = EXPECTED_PANEL_COUNT |

## Static gates

| gate | result | evidence |
| --- | --- | --- |
| panel count vs matrix contract | pass | 223 |
| empty text content | pass | no `"content": ""` |
| empty panel titles | pass | no `"title": ""` |
| status `or vector(0)` | pass | no matches in SCOPE |
| deprecated `checkpoint_saved_at_epoch_seconds` | pass | no matches |
| empty `targets: []` | OK (text only) | control-plane ids 9410/9411 text guardrails |
| empty `expr: ""` | OK (HTTP) | Infinity targets with `url` set |
| datasource null | OK (text) | same text panels |
| collapsed rows nest children | pass (spot) | collapsed:true with panels arrays |
| expanded rows empty nest | pass | incident 2099, overview 9600 |
| Loki panels | none | no logs/loki uid |
| metric registry alignment | pass (sampled) | l0/l1/runtime/provider/dq/control-plane records present |

## Live

Not Verifiable: render, PromQL execution, Ops HTTP responses, contrast/zoom/DOM.

## PROVEN defects

None from static JSON.

## Script

`scripts/temp/panels_static_audit_cycle2.py` prepared for local re-run when Python available:
`.\.venv-win\Scripts\python.exe scripts\temp\panels_static_audit_cycle2.py reports\audit\dashboard-cycle\20260811T180000Z-c205349-dash\cycle-2`
