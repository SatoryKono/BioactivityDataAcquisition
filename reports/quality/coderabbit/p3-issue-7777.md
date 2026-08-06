            ## Source

            - Epic: #7688
            - Wave parent: #7690
            - Wave: **A**
            - Path cluster: `src/bioetl/application/core/entity_id.py`
            - Severity counts: `{'major': 2}`

            ## Findings (top)

            - **major** `src/bioetl/application/core/entity_id.py`: In @src/bioetl/application/core/entity_id.py around lines 23 - 29, Update _normalize_publication_term_identity_component to return the uppercased, trimmed value for every term type, including values outside PUBLICATION_TERM_TYPES. Retain the vocabulary check only for validatio...
- **major** `src/bioetl/application/core/entity_id.py`: In @src/bioetl/application/core/entity_id.py around lines 54 - 79, Update compute_publication_term_entity_id and compute_subcellular_fraction_entity_id to preserve the legacy hashing contract, or introduce an explicit versioned ID scheme instead of silently changing existing I...

            ## Acceptance

            - [ ] Confirm each finding against current `main` (code wins)
            - [ ] Fix or reject with evidence (arch test / import-linter / basedpyright)
            - [ ] Do **not** grow tech-debt / quality budgets
            - [ ] Prefer one root-cause PR

            ## Notes

            Auto-filed from CodeRabbit CLI residual campaign (agent NDJSON).
            De-dupe against open ARCH-CR / prior packs before implementing.

