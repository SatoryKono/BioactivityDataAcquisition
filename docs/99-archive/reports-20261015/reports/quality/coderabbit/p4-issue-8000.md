## Source

- Epic: #7688
- Wave parent: #7691
- Wave: **B**
- Path cluster: `src/bioetl/infrastructure/storage/gold_writer.py`
- Severity counts: `{'major': 1}`

## Findings (top)

- **major** `src/bioetl/infrastructure/storage/gold_writer.py`: In @src/bioetl/infrastructure/storage/gold_writer.py around lines 142 - 149, Restrict GOLD_WRITE_RETRY_ERRORS to transient failures by removing ValueError, TypeError, KeyError, and broad RuntimeError from the tuple unless a documented transient RuntimeError case is explicitly ...

## Acceptance

- [ ] Confirm each finding against current `main` (code wins)
- [ ] Fix or reject with evidence (arch test / import-linter / basedpyright)
- [ ] Do **not** grow tech-debt / quality budgets
- [ ] Prefer one root-cause PR

## Notes

Auto-filed from CodeRabbit CLI residual campaign (agent NDJSON).
De-dupe against open ARCH-CR / prior packs before implementing.

