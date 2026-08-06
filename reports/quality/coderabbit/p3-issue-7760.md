            ## Source

            - Epic: #7688
            - Wave parent: #7690
            - Wave: **A**
            - Path cluster: `src/bioetl/application/core/postrun`
            - Severity counts: `{'major': 3}`

            ## Findings (top)

            - **major** `src/bioetl/application/core/postrun/_metadata_writes.py`: In @src/bioetl/application/core/postrun/_metadata_writes.py around lines 109 - 114, Update the Silver metadata flow around silver_table and finalize_silver_metadata to return early unless storage.is_table_initialized(silver_table, layer="silver") is true, before calling get_ta...
- **major** `src/bioetl/application/core/postrun/_service_collaborators.py`: In @src/bioetl/application/core/postrun/_service_collaborators.py around lines 33 - 67, Add unit tests for resolve_postrun_collaborators covering complete services and the case where services.logger is absent and context.logger is returned. Assert all resolved collaborators, i...
- **major** `src/bioetl/application/core/postrun/_service_support.py`: In @src/bioetl/application/core/postrun/_service_support.py around lines 64 - 96, Replace the cast(Any, None) host declarations in the mixin with a typed host contract, preferably a Protocol or abstract properties, covering the required configuration, runtime/context, services...

            ## Acceptance

            - [ ] Confirm each finding against current `main` (code wins)
            - [ ] Fix or reject with evidence (arch test / import-linter / basedpyright)
            - [ ] Do **not** grow tech-debt / quality budgets
            - [ ] Prefer one root-cause PR

            ## Notes

            Auto-filed from CodeRabbit CLI residual campaign (agent NDJSON).
            De-dupe against open ARCH-CR / prior packs before implementing.

