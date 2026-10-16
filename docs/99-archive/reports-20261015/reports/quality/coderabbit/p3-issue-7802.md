## Source

- Epic: #7688
- Wave parent: #7690
- Wave: **A**
- Path cluster: `src/bioetl/application/core/_record_normalization_hash_support.py`
- Severity counts: `{'major': 1}`

## Findings (top)

- **major** `src/bioetl/application/core/_record_normalization_hash_support.py`: In @src/bioetl/application/core/_record_normalization_hash_support.py around lines 56 - 58, Update `_resolve_hash_exclude_fields` to reuse `_TECHNICAL_HASH_POLICY_FIELDS` instead of repeating the technical field names, keeping hash scope consistent with the policy definition. ...

## Acceptance

- [ ] Confirm each finding against current `main` (code wins)
- [ ] Fix or reject with evidence (arch test / import-linter / basedpyright)
- [ ] Do **not** grow tech-debt / quality budgets
- [ ] Prefer one root-cause PR

## Notes

Auto-filed from CodeRabbit CLI residual campaign (agent NDJSON).
De-dupe against open ARCH-CR / prior packs before implementing.

