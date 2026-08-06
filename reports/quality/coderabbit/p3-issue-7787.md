            ## Source

            - Epic: #7688
            - Wave parent: #7690
            - Wave: **A**
            - Path cluster: `src/bioetl/application/core/subcellular_fraction_support.py`
            - Severity counts: `{'major': 2}`

            ## Findings (top)

            - **major** `src/bioetl/application/core/subcellular_fraction_support.py`: In @src/bioetl/application/core/subcellular_fraction_support.py around lines 62 - 94, Update extract_unique_fraction_records so it always consumes the entire assays stream and completes assay_count and example_assay_id aggregation for collected fractions before yielding. Remov...
- **major** `src/bioetl/application/core/subcellular_fraction_support.py`: In @src/bioetl/application/core/subcellular_fraction_support.py at line 6, Update the raw_fraction annotation in the relevant subcellular-fraction helper to use object instead of Any, and correct the trailing return-type comment to str | None. Preserve the existing None check ...

            ## Acceptance

            - [ ] Confirm each finding against current `main` (code wins)
            - [ ] Fix or reject with evidence (arch test / import-linter / basedpyright)
            - [ ] Do **not** grow tech-debt / quality budgets
            - [ ] Prefer one root-cause PR

            ## Notes

            Auto-filed from CodeRabbit CLI residual campaign (agent NDJSON).
            De-dupe against open ARCH-CR / prior packs before implementing.

