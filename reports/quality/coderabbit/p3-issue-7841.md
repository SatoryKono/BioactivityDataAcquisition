## Source

- Epic: #7688
- Wave parent: #7690
- Wave: **A**
- Path cluster: `src/bioetl/application/core/config.py`
- Severity counts: `{'major': 1}`

## Findings (top)

- **major** `src/bioetl/application/core/config.py`: In @src/bioetl/application/core/config.py around lines 84 - 87, Add unit tests covering the adaptive TTL logic in the configuration path: no batch_size_hint, a hint whose computed TTL is below lock_ttl, a hint that raises the TTL, and a hint capped at 600 seconds. Assert the r...

## Acceptance

- [ ] Confirm each finding against current `main` (code wins)
- [ ] Fix or reject with evidence (arch test / import-linter / basedpyright)
- [ ] Do **not** grow tech-debt / quality budgets
- [ ] Prefer one root-cause PR

## Notes

Auto-filed from CodeRabbit CLI residual campaign (agent NDJSON).
De-dupe against open ARCH-CR / prior packs before implementing.

