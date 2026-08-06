## Source

- Epic: #7688
- Wave parent: #7690
- Wave: **A**
- Path cluster: `src/bioetl/application/core/runner_flow_metrics.py`
- Severity counts: `{'major': 1}`

## Findings (top)

- **major** `src/bioetl/application/core/runner_flow_metrics.py`: In @src/bioetl/application/core/runner_flow_metrics.py around lines 123 - 136, Update the pipeline_metrics parameter types in _record_count_flow_invariants and _record_stage_lag_gauges from object to the existing PipelineMetricsRecorder annotation, then remove the redundant lo...

## Acceptance

- [ ] Confirm each finding against current `main` (code wins)
- [ ] Fix or reject with evidence (arch test / import-linter / basedpyright)
- [ ] Do **not** grow tech-debt / quality budgets
- [ ] Prefer one root-cause PR

## Notes

Auto-filed from CodeRabbit CLI residual campaign (agent NDJSON).
De-dupe against open ARCH-CR / prior packs before implementing.

