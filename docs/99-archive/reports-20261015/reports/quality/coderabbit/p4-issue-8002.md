## Source

- Epic: #7688
- Wave parent: #7691
- Wave: **B**
- Path cluster: `src/bioetl/infrastructure/storage/metadata_artifact_details.py`
- Severity counts: `{'major': 1}`

## Findings (top)

- **major** `src/bioetl/infrastructure/storage/metadata_artifact_details.py`: In @src/bioetl/infrastructure/storage/metadata_artifact_details.py around lines 109 - 126, Update serialize_input_snapshot_ref so last_modified receives the same datetime-to-ISO-8601 normalization as captured_at. Preserve non-datetime values according to the existing contract,...

## Acceptance

- [ ] Confirm each finding against current `main` (code wins)
- [ ] Fix or reject with evidence (arch test / import-linter / basedpyright)
- [ ] Do **not** grow tech-debt / quality budgets
- [ ] Prefer one root-cause PR

## Notes

Auto-filed from CodeRabbit CLI residual campaign (agent NDJSON).
De-dupe against open ARCH-CR / prior packs before implementing.

