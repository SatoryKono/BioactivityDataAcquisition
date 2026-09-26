## Source

- Epic: #7688
- Wave parent: #7691
- Wave: **B**
- Path cluster: `src/bioetl/infrastructure/storage/metadata_writer_helpers.py`
- Severity counts: `{'major': 1}`

## Findings (top)

- **major** `src/bioetl/infrastructure/storage/metadata_writer_helpers.py`: In @src/bioetl/infrastructure/storage/metadata_writer_helpers.py around lines 92 - 114, Offload the blocking metadata read and validation performed by `_load_existing_metadata_model` from the event loop. Add an async wrapper in this module that invokes the existing synchronous...

## Acceptance

- [ ] Confirm each finding against current `main` (code wins)
- [ ] Fix or reject with evidence (arch test / import-linter / basedpyright)
- [ ] Do **not** grow tech-debt / quality budgets
- [ ] Prefer one root-cause PR

## Notes

Auto-filed from CodeRabbit CLI residual campaign (agent NDJSON).
De-dupe against open ARCH-CR / prior packs before implementing.

