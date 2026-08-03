## Summary

Run Explorer **Browse · Recent pipeline runs** is empty for pipelines with no `reports/run-reports/pipeline/<name>/` artifacts (e.g. `chembl_activity` count=0), while live Processed Records still show bronze metrics — looks like a broken ID/Browse fill.

## Evidence

- `list_pipeline_run_report_payloads(pipeline=chembl_activity)` → count 0 (fast)
- `list_pipeline_run_report_payloads(pipeline=None)` → finds chembl_publication/target reports (~1.8s)
- Concurrent forensic load previously timed out some HTTP panels under 0.25s queue budget

## Fix direction

1. Empty-state copy: **No run reports on disk for this pipeline** (not NO DATA / backend error)
2. Prefer `_latest.json` / index scan optimization if full-tree list is slow under load
3. Document that Browse requires written pipeline-run-report artifacts, not only Prometheus current metrics

## Acceptance

- Browse empty state distinguishes no-artifacts vs backend timeout (504 forensic_endpoint_error_v1)
- At least one chembl_* pipeline with reports shows rows in Browse when selected

## Related

#7158
