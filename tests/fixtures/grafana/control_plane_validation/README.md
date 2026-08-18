# Trust validation fixtures (panels 9413–9418)

**Issues:** #8576 (visual baseline), #8578 (Trust validation close-ups), #8976 (first-screen `reasons_text`)

Contract: `control_plane_validation_evidence_v1`  
Generator: `scripts/ops/observability/grafana/generate_trust_validation_fixtures.py`  
Mock server: `scripts/ops/observability/grafana/serve_trust_validation_fixtures.py`

## Panel → endpoint map

| Panel ID | Title | Endpoint |
| ---: | --- | --- |
| 9413 | Review Checkpoint Validation | `checkpoint-validation` |
| 9414 | Review Manifest Validation | `manifest-validation` |
| 9415 | Review Lineage Validation | `lineage-validation` |
| 9416 | Review Retention Compliance | `retention-compliance` |
| 9417 | Review Bounded Failure Reasons | `failure-reasons` |
| 9418 | Review Selected-Run Trust | `manifest-validation` |

Live Grafana Infinity URL pattern:

```text
/ops/control-plane/{endpoint}?pipeline=${pipeline}&run_type=${run_type:csv}&run_id=${run_id}
```

## Fixture states

| State | Visual intent | HTTP | Body `status` |
| --- | --- | --- | --- |
| `populated` | Readable OK rows for exact run | 200 | `OK` |
| `valid_empty_or_unknown` | Scope missing / evidence absent | 200 | `UNKNOWN` |
| `zero_failures` | failure-reasons only: counts=0 | 200 | `OK` |
| `backend_error` | Source parse/read failure | 200 | `ERROR` |
| `service_unavailable` | Evidence service down (QUERY_ERROR path) | **503** | `ERROR` |
| `empty_rows` | Synthetic `rows=[]` for Infinity `noValue` | 200 | `UNKNOWN` |
| `incomplete_reasons` | manifest-validation only: INCOMPLETE trust, `reasons_text` capped at 3 lines | 200 | `UNKNOWN` |
| `aggregate_scope_unknown` | checkpoint only: aggregate scope | 200 | `UNKNOWN` |

**Do not** treat `UNKNOWN` or empty as green OK.  
**Do not** invent Prometheus labels for run/manifest IDs.

## Regenerate

```powershell
$env:PYTHONPATH='src'
.\.venv-win\Scripts\python.exe scripts/ops/observability/grafana/generate_trust_validation_fixtures.py
```

## Serve for close-up capture

```powershell
$env:PYTHONPATH='src'
# terminal A
.\.venv-win\Scripts\python.exe scripts/ops/observability/grafana/serve_trust_validation_fixtures.py --port 18080 --default-state populated

# terminal B — switch state without restart:
$env:BIOETL_TRUST_FIXTURE_STATE='backend_error'
# or per-request: ?fixture_state=valid_empty_or_unknown
```

Point a **temporary** local Infinity / reverse-proxy at `http://127.0.0.1:18080` (do not commit production datasource URL changes).

Then capture with:

```powershell
node scripts/ops/observability/grafana/_capture_trust_closeups.cjs `
  --output-dir reports/observability/grafana/visual-baseline-20260811/trust-closeups-$env:BIOETL_TRUST_FIXTURE_STATE
```

Or open solo panels:

```text
http://localhost:3000/d/bioetl-control-plane-v1/0-trust?kiosk=1&viewPanel=9413&...
```

## Fixture selector identity

| Field | Value |
| --- | --- |
| pipeline | `chembl_activity` |
| run_type | `incremental` |
| run_id | `00000000-0000-0000-0000-000000008576` |
| manifest_id | `manifest-8576-fixture` |

## Capture matrix for #8578

For each panel 9413–9417, keep **separate** PNG sets:

1. `populated` — OK rows readable  
2. `valid_empty_or_unknown` or `empty_rows` — not green  
3. `backend_error` or `service_unavailable` — ERROR / QUERY_ERROR distinct from empty  

Record state name + fixture path + PNG SHA in the #8576 baseline folder.
