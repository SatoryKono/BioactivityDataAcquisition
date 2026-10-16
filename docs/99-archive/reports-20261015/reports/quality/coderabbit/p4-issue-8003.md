## Source

- Epic: #7688
- Wave parent: #7691
- Wave: **B**
- Path cluster: `src/bioetl/infrastructure/storage/metadata_writer.py`
- Severity counts: `{'major': 1}`

## Findings (top)

- **major** `src/bioetl/infrastructure/storage/metadata_writer.py`: In @src/bioetl/infrastructure/storage/metadata_writer.py around lines 30 - 56, Remove the temporary _helpers.atomic_write_text reassignment and restoration from _execute_prepared_metadata_write_operation. Thread the facade’s atomic_write_text writer explicitly through _execute...

## Acceptance

- [ ] Confirm each finding against current `main` (code wins)
- [ ] Fix or reject with evidence (arch test / import-linter / basedpyright)
- [ ] Do **not** grow tech-debt / quality budgets
- [ ] Prefer one root-cause PR

## Notes

Auto-filed from CodeRabbit CLI residual campaign (agent NDJSON).
De-dupe against open ARCH-CR / prior packs before implementing.

