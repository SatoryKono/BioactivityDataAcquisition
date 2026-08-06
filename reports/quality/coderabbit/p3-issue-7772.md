            ## Source

            - Epic: #7688
            - Wave parent: #7690
            - Wave: **A**
            - Path cluster: `src/bioetl/application/core/_quarantine_metrics_support.py`
            - Severity counts: `{'major': 2}`

            ## Findings (top)

            - **major** `src/bioetl/application/core/_quarantine_metrics_support.py`: In @src/bioetl/application/core/_quarantine_metrics_support.py around lines 41 - 43, Replace the dynamic getattr/callable checks in the quarantine metrics helpers with direct calls to the declared MetricsPort methods track_quarantined_records and track_processed_records; if th...
- **major** `src/bioetl/application/core/_quarantine_metrics_support.py`: In @src/bioetl/application/core/_quarantine_metrics_support.py around lines 94 - 111, Remove the metrics is None early return from record_filtered_quarantine_metrics so pipeline_metrics.record_quarantine_records and _record_silver_removal_accounting always execute for FILTERED...

            ## Acceptance

            - [ ] Confirm each finding against current `main` (code wins)
            - [ ] Fix or reject with evidence (arch test / import-linter / basedpyright)
            - [ ] Do **not** grow tech-debt / quality budgets
            - [ ] Prefer one root-cause PR

            ## Notes

            Auto-filed from CodeRabbit CLI residual campaign (agent NDJSON).
            De-dupe against open ARCH-CR / prior packs before implementing.

