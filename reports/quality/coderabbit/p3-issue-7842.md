## Source

- Epic: #7688
- Wave parent: #7690
- Wave: **A**
- Path cluster: `src/bioetl/application/core/data_sources`
- Severity counts: `{'major': 1}`

## Findings (top)

- **major** `src/bioetl/application/core/data_sources/publication_term.py`: In @src/bioetl/application/core/data_sources/publication_term.py around lines 49 - 61, Update _fetch_target_records to preserve checkpoint offsets instead of discarding offset and restarting _fetch_publication_terms at zero. Implement conversion from emitted-term offsets to th...

## Acceptance

- [ ] Confirm each finding against current `main` (code wins)
- [ ] Fix or reject with evidence (arch test / import-linter / basedpyright)
- [ ] Do **not** grow tech-debt / quality budgets
- [ ] Prefer one root-cause PR

## Notes

Auto-filed from CodeRabbit CLI residual campaign (agent NDJSON).
De-dupe against open ARCH-CR / prior packs before implementing.

