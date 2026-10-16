## Source

- Epic: #7688
- Wave parent: #7691
- Wave: **B**
- Path cluster: `src/bioetl/infrastructure/storage/delta_reader.py`
- Severity counts: `{'major': 1}`

## Findings (top)

- **major** `src/bioetl/infrastructure/storage/delta_reader.py`: In @src/bioetl/infrastructure/storage/delta_reader.py around lines 111 - 118, Update the unbounded-read branch after _try_native_delta_row_count in the scanner flow so a None row count never uses _FULL_READ_HEAD_LIMIT or truncates results. Use an uncapped scanner read, or expl...

## Acceptance

- [ ] Confirm each finding against current `main` (code wins)
- [ ] Fix or reject with evidence (arch test / import-linter / basedpyright)
- [ ] Do **not** grow tech-debt / quality budgets
- [ ] Prefer one root-cause PR

## Notes

Auto-filed from CodeRabbit CLI residual campaign (agent NDJSON).
De-dupe against open ARCH-CR / prior packs before implementing.

