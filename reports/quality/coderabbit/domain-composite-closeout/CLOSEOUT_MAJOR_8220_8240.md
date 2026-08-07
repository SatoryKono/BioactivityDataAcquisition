# domain/composite residual closeout (major pack #8220–#8240)

- Branch: `main`
- Fixed: **12**
- Rejected: **2**
- Total: **14**

## Dispositions

- **#8220** `fixed` — LineageConfig freezes provider_lookup_fields and tuple-normalizes track_source_for_fields.
- **#8221** `fixed` — Unit coverage for DataSchemaConfig layer selection, CompositeDQConfig overrides, EnrichmentResult factories/rates.
- **#8225** `fixed` — CompositeDQConfig validates effective soft < hard per enricher override.
- **#8226** `fixed` — MergeResult freezes field_coverage/lineage_summary and quarantine payloads.
- **#8227** `fixed` — empty column_groups/include_groups treated as explicit empty selection (None remains fallback/unrestricted).
- **#8228** `reject` — CompositeResult export already shipped; public contract governed by ADR-026 (no separate version-bump/ADR for residual).
- **#8229** `fixed` — refreshed reports/quality/module-coverage-inventory.json source_tree_sha256.
- **#8230** `fixed` — CompositeResult nominal + failure path unit tests.
- **#8231** `reject` — coerce/validate_composite_config already public under ADR-026; no additional release ceremony for residual rename.
- **#8232** `fixed` — unit tests for coerce/validate + join-key/duplicate failures.
- **#8234** `fixed` — CompositeResult freezes dependency/enrichment maps via freeze_fields/FrozenDict.
- **#8235** `fixed` — FieldGroupRegistry indexes use enclosing FieldGroupDefinition.group_id.
- **#8237** `fixed` — config_validators public names (require_non_empty/validate_positive/…) with private aliases retained.
- **#8240** `fixed` — composite_to_dict/from_dict lossless for seed/deps/enrichers/merge/dq/execution/lineage/cross_validation.

## Validation
- pytest tests/unit/domain/composite green
- No tech-debt budget growth
