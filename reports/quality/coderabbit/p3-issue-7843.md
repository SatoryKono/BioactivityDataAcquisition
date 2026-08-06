## Source

- Epic: #7688
- Wave parent: #7690
- Wave: **A**
- Path cluster: `src/bioetl/application/core/normalization_fallbacks.py`
- Severity counts: `{'major': 1}`

## Findings (top)

- **major** `src/bioetl/application/core/normalization_fallbacks.py`: In @src/bioetl/application/core/normalization_fallbacks.py around lines 7 - 17, Add "normalize_plain_text" to the module’s __all__ export list in normalization_fallbacks.py, preserving the existing ordering and leaving the helper implementation unchanged.

## Acceptance

- [ ] Confirm each finding against current `main` (code wins)
- [ ] Fix or reject with evidence (arch test / import-linter / basedpyright)
- [ ] Do **not** grow tech-debt / quality budgets
- [ ] Prefer one root-cause PR

## Notes

Auto-filed from CodeRabbit CLI residual campaign (agent NDJSON).
De-dupe against open ARCH-CR / prior packs before implementing.

