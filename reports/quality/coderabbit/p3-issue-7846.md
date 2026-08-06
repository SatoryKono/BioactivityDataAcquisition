## Source

- Epic: #7688
- Wave parent: #7690
- Wave: **A**
- Path cluster: `src/bioetl/application/core/publication_term_runtime.py`
- Severity counts: `{'major': 1}`

## Findings (top)

- **major** `src/bioetl/application/core/publication_term_runtime.py`: In @src/bioetl/application/core/publication_term_runtime.py around lines 18 - 42, Type-validate MeSH fields in the MeSH processing branch before calling create_term_record: accept only non-whitespace strings for mesh_heading and mesh_qualifier, and validate mesh_id and any emi...

## Acceptance

- [ ] Confirm each finding against current `main` (code wins)
- [ ] Fix or reject with evidence (arch test / import-linter / basedpyright)
- [ ] Do **not** grow tech-debt / quality budgets
- [ ] Prefer one root-cause PR

## Notes

Auto-filed from CodeRabbit CLI residual campaign (agent NDJSON).
De-dupe against open ARCH-CR / prior packs before implementing.

