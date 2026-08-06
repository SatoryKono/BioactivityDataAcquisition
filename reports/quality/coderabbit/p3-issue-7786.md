            ## Source

            - Epic: #7688
            - Wave parent: #7690
            - Wave: **A**
            - Path cluster: `src/bioetl/application/core/runner.py`
            - Severity counts: `{'major': 2}`

            ## Findings (top)

            - **major** `src/bioetl/application/core/runner.py`: In @src/bioetl/application/core/runner.py around lines 168 - 199, Record terminal shutdown only in the outer run() shutdown handler: remove the _record_terminal_shutdown() call and shutdown_recorded state from _run_pipeline_lifecycle(), and adjust its return contract and run()...
- **major** `src/bioetl/application/core/runner.py`: In @src/bioetl/application/core/runner.py around lines 183 - 185, Update the finalization block in the runner’s surrounding execution method so both _finalize_debug_export and _cleanup_after_run are individually guarded, ensuring cleanup is attempted even when debug export fin...

            ## Acceptance

            - [ ] Confirm each finding against current `main` (code wins)
            - [ ] Fix or reject with evidence (arch test / import-linter / basedpyright)
            - [ ] Do **not** grow tech-debt / quality budgets
            - [ ] Prefer one root-cause PR

            ## Notes

            Auto-filed from CodeRabbit CLI residual campaign (agent NDJSON).
            De-dupe against open ARCH-CR / prior packs before implementing.

