            ## Source

            - Epic: #7688
            - Wave parent: #7690
            - Wave: **A**
            - Path cluster: `src/bioetl/application/core/publication_term_extraction_mixin.py`
            - Severity counts: `{'major': 2}`

            ## Findings (top)

            - **major** `src/bioetl/application/core/publication_term_extraction_mixin.py`: In @src/bioetl/application/core/publication_term_extraction_mixin.py around lines 23 - 27, Replace self: Any in _yield_terms_from_publications and the additionally referenced mixin methods with a structural protocol describing the composed adapter state, including _data_source...
- **major** `src/bioetl/application/core/publication_term_extraction_mixin.py`: In @src/bioetl/application/core/publication_term_extraction_mixin.py around lines 29 - 44, Update the term-extraction methods containing the shown publication loop and the corresponding sections at the other reported locations to validate limit before fetching publications: ra...

            ## Acceptance

            - [ ] Confirm each finding against current `main` (code wins)
            - [ ] Fix or reject with evidence (arch test / import-linter / basedpyright)
            - [ ] Do **not** grow tech-debt / quality budgets
            - [ ] Prefer one root-cause PR

            ## Notes

            Auto-filed from CodeRabbit CLI residual campaign (agent NDJSON).
            De-dupe against open ARCH-CR / prior packs before implementing.

