            ## Source

            - Epic: #7688
            - Wave parent: #7690
            - Wave: **A**
            - Path cluster: `src/bioetl/application/core/pre_silver_finalization_flow.py`
            - Severity counts: `{'major': 2}`

            ## Findings (top)

            - **major** `src/bioetl/application/core/pre_silver_finalization_flow.py`: In @src/bioetl/application/core/pre_silver_finalization_flow.py around lines 66 - 90, Collapse the duplicated normalization, content-hash, record-building, and projection sequence shared by _finalize_staged_business_data and _finalize_normalized_business_data into one private ...
- **major** `src/bioetl/application/core/pre_silver_finalization_flow.py`: In @src/bioetl/application/core/pre_silver_finalization_flow.py around lines 44 - 64, Reuse the injected self._record_normalizer in _normalize_business_data and _project_pre_silver_findings instead of calling _build_record_normalizer, so findings stored during normalization re...

            ## Acceptance

            - [ ] Confirm each finding against current `main` (code wins)
            - [ ] Fix or reject with evidence (arch test / import-linter / basedpyright)
            - [ ] Do **not** grow tech-debt / quality budgets
            - [ ] Prefer one root-cause PR

            ## Notes

            Auto-filed from CodeRabbit CLI residual campaign (agent NDJSON).
            De-dupe against open ARCH-CR / prior packs before implementing.

