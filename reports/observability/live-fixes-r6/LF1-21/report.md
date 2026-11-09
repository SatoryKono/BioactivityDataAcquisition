# LF1-21 Report

## Status Panels Matrix

| Panel ID | Title | Source | noValue | Thresholds | Mappings |
|----------|-------|--------|---------|------------|----------|
| 9406 | Compare Checkpoint Anchors | bioetl-ops-http | SELECT RUN if no Run ID is selected. QUERY ERROR if the request failed. | {} | [] |
| 9408 | Review Replay Evidence | bioetl-ops-http | UNKNOWN | {} | [] |
| 9413 | Review Checkpoint Validation | bioetl-ops-http | SELECT RUN if no Run ID is selected. QUERY ERROR if the request failed. | {} | [] |
| 9414 | Review Manifest Validation | bioetl-ops-http | SELECT RUN if no Run ID is selected. QUERY ERROR if the request failed. | {} | [] |
| 9415 | Review Lineage Validation | bioetl-ops-http | SELECT RUN if no Run ID is selected. QUERY ERROR if the request failed. | {} | [] |
| 9416 | Review Retention Compliance | bioetl-ops-http | SELECT RUN if no Run ID is selected. QUERY ERROR if the request failed. HTTP 504 is a query error, not an empty result. | {} | [] |
| 9418 | Review Selected-Run Trust | bioetl-ops-http | SELECT RUN if no Run ID is selected. QUERY ERROR if the request failed. | {} | [] |
| 9422 | Review Exact Replay Readiness | -- Dashboard -- | UNKNOWN | {"mode": "absolute", "steps": [{"color": "#555555", "value": null}]} | [{"type": "value", "options": {"READY": {"text": "READY", "color": "green"}, "BLOCKED": {"text": "BLOCKED", "color": "red"}, "INSUFFICIENT": {"text": "INSUFFICIENT", "color": "orange"}, "UNSUPPORTED": {"text": "UNSUPPORTED", "color": "#555555"}, "SELECT RUN": {"text": "SELECT RUN", "color": "#555555"}, "QUERY ERROR": {"text": "QUERY ERROR", "color": "red"}, "UNKNOWN": {"text": "UNKNOWN", "color": "#555555"}, "INCOMPLETE": {"text": "INCOMPLETE", "color": "#555555"}, "\u041d\u0415\u0422 \u0417\u0410\u041f\u0423\u0421\u041a\u041e\u0412": {"text": "\u041d\u0415\u0422 \u0417\u0410\u041f\u0423\u0421\u041a\u041e\u0412", "color": "gray"}}}, {"type": "special", "options": {"match": "null", "result": {"text": "UNKNOWN", "color": "#555555"}}}] |
| 9423 | Review Exact Replay Checks | -- Dashboard -- | — | {} | [] |

## Audit Status

Running live audit...
Audit failed: Command '['uv', 'run', 'python', '-m', 'scripts.ops.observability.grafana.audit_live_grafana_panels', '--output', 'reports/observability/live-fixes-r6/LF1-21/live-panel-audit.json']' returned non-zero exit status 1.
