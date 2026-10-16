## Source

- Epic: #7688
- Wave parent: #7691
- Wave: **B**
- Path cluster: `src/bioetl/infrastructure/storage/lineage_persistence.py`
- Severity counts: `{'major': 1}`

## Findings (top)

- **major** `src/bioetl/infrastructure/storage/lineage_persistence.py`: In @src/bioetl/infrastructure/storage/lineage_persistence.py around lines 161 - 166, Update _has_explicit_member to safely inspect instances without __dict__, avoiding a TypeError from vars(target) while preserving detection of instance and class members. Use a guarded instanc...

## Acceptance

- [ ] Confirm each finding against current `main` (code wins)
- [ ] Fix or reject with evidence (arch test / import-linter / basedpyright)
- [ ] Do **not** grow tech-debt / quality budgets
- [ ] Prefer one root-cause PR

## Notes

Auto-filed from CodeRabbit CLI residual campaign (agent NDJSON).
De-dupe against open ARCH-CR / prior packs before implementing.

