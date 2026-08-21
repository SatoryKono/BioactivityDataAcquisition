# Step 4 — grafana-audit.data-integrity

**MONITORING=true.** Stack already running (`bioetl-grafana`, `bioetl-prometheus`, `bioetl`). Did **not** start `docker-compose.monitoring.yml` again.

## Live probes (FACT)

| Probe | Result |
| --- | --- |
| `GET :3000/api/health` | database ok, version 12.0.0 |
| `GET :9090/api/v1/query?query=up` | success, grafana/renderer/pushgateway up=1 |
| `bioetl_provider_current_status` | series present (`provider=chembl` value `3` at query time) |
| `GET :8000/health/ready` | healthy; report-root aligned |
| `GET :8000/ops/observability/pipeline-run-reports?pipeline=chembl_assay&limit=3` | `index_state=ok`, count=3 |

**Class:** populated/normal for Run Explorer index (not TREE_MISSING, not valid zero). Provider status **3** is live telemetry — do not invent enum meaning here; 9104 expr is `max(...) * 0` so PRESENT encodes existence.

**DASH-AUTO-011 FAIL** in scanner for type `BioETL Ops HTTP` — false positive (allowed Ops HTTP / Infinity). Not a defect.

No new data-integrity GitHub issues.
