            ## Source

            - Epic: #7688
            - Wave parent: #7691
            - Wave: **B**
            - Path cluster: `src/bioetl/infrastructure/storage/delta`
            - Severity counts: `{'major': 2}`

            ## Findings (top)

            - **major** `src/bioetl/infrastructure/storage/delta/arrow_converter.py`: In @src/bioetl/infrastructure/storage/delta/arrow_converter.py around lines 297 - 311, Update the nested cast handling in the schema-conversion branch to catch both pa.ArrowInvalid and pa.ArrowNotImplementedError. Ensure the fallback array type matches new_schema: either const...
- **major** `src/bioetl/infrastructure/storage/delta/resilience.py`: In @src/bioetl/infrastructure/storage/delta/resilience.py around lines 37 - 52, The deterministic jitter currently depends only on retry_count, causing concurrent writes to share identical delays. Add a unique operation identity to _DeltaWriteRequest, propagate it through calc...

            ## Acceptance

            - [ ] Confirm each finding against current `main` (code wins)
            - [ ] Fix or reject with evidence (arch test / import-linter / basedpyright)
            - [ ] Do **not** grow tech-debt / quality budgets
            - [ ] Prefer one root-cause PR

            ## Notes

            Auto-filed from CodeRabbit CLI residual campaign (agent NDJSON).
            De-dupe against open ARCH-CR / prior packs before implementing.

