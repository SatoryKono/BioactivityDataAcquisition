            ## Source

            - Epic: #7688
            - Wave parent: #7690
            - Wave: **A**
            - Path cluster: `src/bioetl/application/core/_record_normalization_mapping.py`
            - Severity counts: `{'major': 2}`

            ## Findings (top)

            - **major** `src/bioetl/application/core/_record_normalization_mapping.py`: In @src/bioetl/application/core/_record_normalization_mapping.py around lines 37 - 43, The five attributes in the record normalization mapping mixin currently use cast(Any, None), introducing forbidden broad typing and runtime None defaults. In the class containing provider, e...
- **major** `src/bioetl/application/core/_record_normalization_mapping.py`: In @src/bioetl/application/core/_record_normalization_mapping.py around lines 161 - 170, Move the predicate import out of the per-field loop in the record normalization logic and place a single module-scope import in _record_normalization_mapping.py. Replace the private _norma...

            ## Acceptance

            - [ ] Confirm each finding against current `main` (code wins)
            - [ ] Fix or reject with evidence (arch test / import-linter / basedpyright)
            - [ ] Do **not** grow tech-debt / quality budgets
            - [ ] Prefer one root-cause PR

            ## Notes

            Auto-filed from CodeRabbit CLI residual campaign (agent NDJSON).
            De-dupe against open ARCH-CR / prior packs before implementing.

