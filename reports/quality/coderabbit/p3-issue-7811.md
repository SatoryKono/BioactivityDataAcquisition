## Source

- Epic: #7688
- Wave parent: #7690
- Wave: **A**
- Path cluster: `src/bioetl/application/core/base_transformer_dependency_helpers_mixin.py`
- Severity counts: `{'major': 1}`

## Findings (top)

- **major** `src/bioetl/application/core/base_transformer_dependency_helpers_mixin.py`: In @src/bioetl/application/core/base_transformer_dependency_helpers_mixin.py around lines 144 - 175, Update _apply_hash_policy in BaseTransformerDependencyHelpersMixin to determine whether an explicit identity hash policy exists through the public EntityIdentityGenerator colla...

## Acceptance

- [ ] Confirm each finding against current `main` (code wins)
- [ ] Fix or reject with evidence (arch test / import-linter / basedpyright)
- [ ] Do **not** grow tech-debt / quality budgets
- [ ] Prefer one root-cause PR

## Notes

Auto-filed from CodeRabbit CLI residual campaign (agent NDJSON).
De-dupe against open ARCH-CR / prior packs before implementing.

