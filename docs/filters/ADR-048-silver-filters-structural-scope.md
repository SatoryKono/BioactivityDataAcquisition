______________________________________________________________________

Version: 0.1.0
Status: Proposed (Draft)
Class: draft
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-05-12'

______________________________________________________________________

# ADR-048: Silver Filters Structural Scope

**Date:** 2026-05-12
**Status:** Proposed (Draft)
**Decision makers:** @BioETL-Team
**Related:** ADR-002, ADR-018, ADR-027, ADR-028, ADR-045
**Amends:** ADR-028 (Filter Rules Externalization)

> NOTE: This is a DRAFT located in `docs/filters/`. After review and acceptance
> it MUST be moved to `docs/02-architecture/decisions/` and renumbered if a
> higher ADR has been merged in the meantime.

## Context

ADR-028 externalized filter rules into a hierarchical configuration system with
four sections: `input_filter`, `silver_filters`, `gold_filters`, and
`extraction_params`. The `silver_filters` and `gold_filters` sections share the
same `BaseFilterConfig` shape (`columns`, `ranges`, `list_length_filters`,
`list_contains_filters`, `required_fields`, `exclude_if_present`) but apply at
different pipeline stages:

- **silver_filters**: applied via `apply_silver_filter()` in
  `src/bioetl/application/core/_base_transformer_structural_support.py`
  BEFORE writing to Silver layer. Rejections raise `FilteredOutError` and are
  quarantined with `error_code=FILTERED_OUT_SILVER`.
- **gold_filters**: applied via `should_write_gold()` (used in pipeline
  callbacks) AFTER `transform_for_gold()` removes JSON fields, BEFORE writing
  to Gold layer.

This dual-stage filtering creates issues:

1. **Configuration duplication**: Entity configs frequently repeat the same
   semantic rules in `silver_filters` and `gold_filters`. Example
   (`configs/entities/chembl/activity.yaml`):

   ```yaml
   silver_filters:
     columns:
       standard_type: [IC50, Ki]
       standard_units: [nM]
     ranges:
       standard_value: { min: 0, include_min: false }
   gold_filters:
     columns:
       standard_type: [IC50, Ki]   # DUPLICATE
       standard_units: [nM]        # DUPLICATE
     ranges:
       standard_value: { min: 0, include_min: false }  # DUPLICATE
   ```

1. **Mixed responsibilities**: `silver_filters.required_fields` serves
   structural integrity (e.g., "record MUST have `entity_id`"), while
   `silver_filters.columns` serves business filtering (e.g., "only IC50/Ki
   measurements"). These belong to different concerns.

1. **Schema-coupling risk**: `silver_filters` apply to records that still
   contain JSON-string fields (removed by `transform_for_gold()`). A semantic
   rule like `columns.standard_type` works at Silver stage but may target a
   field that has been renamed via `rename_map` by Gold stage, leading to
   subtle bugs when developers naively duplicate rules.

1. **Optionality coupling**: `silver_filters.required_fields` is consumed by
   `ConfigSurfaceOptionalityResolver` (`optionality.py:_collect_silver_required_fields`)
   as a source of field optionality for Silver schema policy. This dual-use
   makes silver_filters' `required_fields` semantically distinct from
   gold_filters' `required_fields`.

1. **Shadow comparison metric**: `bioetl_structural_policy_shadow_comparisons_total`
   compares structural policy outcome with semantic silver_filter outcome to
   detect drift. The semantic side of this comparison is `silver_filters`.

## Decision

Narrow the scope of `silver_filters` to **structural integrity only**:

```yaml
silver_filters:
  required_fields: [...]      # KEEP - structural invariant
  exclude_if_present: [...]   # KEEP - structural exclusion
gold_filters:
  required_fields: [...]      # business-critical fields
  columns: {...}              # semantic value filtering
  ranges: {...}               # semantic range filtering
  list_length_filters: {...}
  list_contains_filters: {...}
  exclude_if_present: [...]
```

**Conceptual mapping:**

- **silver_filters** answers: "Is this record structurally complete enough to
  enter the Silver layer?"
- **gold_filters** answers: "Does this record meet business criteria for the
  Gold dataset?"

### Implementation Approach

**Minimally invasive backward-compatible path:**

1. Keep `SilverFilterConfig` extending `BaseFilterConfig` (no domain breaking
   change).
1. Add validation in `SilverFiltersFileConfig.model_validate` (Pydantic): when
   `columns` / `ranges` / `list_lengths` / `list_contains` are non-empty, emit
   `DeprecationWarning`.
1. In `FilterConfigLoader.load()`, auto-promote semantic rules from
   silver_filters to gold_filters (merge):
   - Log event `silver_semantic_filter_auto_promoted` with structured details.
   - Increment metric `bioetl_silver_filter_auto_promotions_total`.
1. Add CI invariant in `config_ci_contract.py`: warn (later: error) when entity
   configs use semantic fields under `silver_filters`.
1. Provide migration script (`scripts/migrations/migrate_silver_to_gold_filters.py`)
   for one-time YAML rewrite per entity.

### What Stays Unchanged

- `apply_silver_filter()` function — operates on whatever rules remain in
  `SilverFilterConfig`. For empty filters it's a no-op via `is_empty()`.
- `ConfigSurfaceOptionalityResolver._collect_silver_required_fields()` —
  continues to read `silver_filters.required_fields`.
- `evaluate_semantic_shadow_decision()` — semantically narrowed to comparing
  structural policy outcome with `required_fields`/`exclude_if_present`
  outcome. Metric remains, documentation updated.
- `silver_filter_rejects` metric, `FILTERED_OUT_SILVER` error code,
  `quarantine_category=silver_filter`, CLI `--silver-filter-only` flag,
  Grafana `bioetl-silver-reject-explorer.json` dashboard — all preserved with
  narrowed semantics ("structural rejects").
- 8 transformer classes — receive `SilverFilterConfig` via DI; type-narrowing
  is invisible to them.

## Consequences

### Positive

- **DRY**: Eliminates routine duplication between silver_filters and
  gold_filters (observed in 21 entity configs).
- **Clear separation of concerns**: Silver = structural integrity, Gold =
  business rules.
- **Aligned with ADR-002 (Medallion)**: Silver layer responsibility is
  schema-conformant data, not business curation.
- **Optionality resolver intact**: No breaking change to
  `OptionalitySource.silver_required_fields` semantics.
- **Structural policy preserved**: Shadow comparison remains meaningful for
  structural rules.
- **Backward compatible**: Auto-promotion period allows gradual config
  migration.

### Negative

- **Migration overhead**: 21 entity configs require per-entity review for
  semantic conflict resolution.
- **Slight semantic drift period**: During Phase A rollout, both old and new
  config shapes coexist via auto-promotion.
- **Metric label semantics narrows**: `silver_filter_rejects` no longer
  includes semantic rejects; operators must understand the shift.

### Neutral

- **No change to Gold strict validation (ADR-018)**: Gold continues to
  enforce strict Pandera schemas after gold_filters.
- **No change to DQ contracts (ADR-045)**: DQ rules remain orthogonal to
  filtering.

## Alternatives Considered

### A) Full removal of silver_filters

All filtering shifts to Gold; Silver writes everything that survives
transformation. Rejected because:

- Inflates Silver storage (vacuum, compaction overhead).
- Breaks `OptionalitySource.silver_required_fields` source — requires
  rewriting `ConfigSurfaceOptionalityResolver`.
- Breaks structural policy shadow comparison metric.
- Conflicts with ADR-002 (Silver = curated normalized data).

### B) Renaming silver_filters → filters (no semantic change)

Cosmetic unification under one name. Rejected because:

- Masks the actual two-stage filtering reality.
- Creates technical debt for future readers.
- Does not address duplication problem.

### C) Move filter application after `transform_for_gold()`

Apply former silver_filters on `GoldRecord` after transform. Rejected because:

- Rules over JSON-string fields (e.g., `_chembl_metadata`) stop working
  because `transform_for_gold()` removes those fields.
- Rules over renamed fields (via `rename_map`) silently break.
- Requires rewriting many entity configs to align with Gold schema.
- Higher regression risk.

### D) Hybrid: structural in Silver, semantic in Gold (THIS DECISION)

Accepted. See "Decision" section above.

## Migration Plan

See `docs/filters/migration-plan.md` for the detailed phased plan.

Summary of phases:

1. **Phase 0**: ADR + inventory script + baseline measurements.
1. **Phase 1**: Domain layer (no breaking change).
1. **Phase 2**: Infrastructure (Pydantic schema, loader auto-promotion, CI
   invariant).
1. **Phase 3**: Application layer (no code change, only type narrowing).
1. **Phase 4**: Configs migration (auto-script + per-entity review).
1. **Phase 5**: Observability (relabel "structural" semantics).
1. **Phase 6**: Tests.
1. **Phase 7**: Documentation.
1. **Phase 8**: Phased rollout with feature flag.

## Rollout

- Phased: Domain → Infrastructure → Configs → Tests → Observability →
  Hardening.
- Feature flag `BIOETL_LEGACY_SILVER_SEMANTIC=1` disables auto-promotion for
  emergency rollback.
- Auto-promotion period: 1-2 release cycles before hardening CI invariant
  from warning to error.

## Rollback

- **Last known good**: pre-ADR-048 state with silver_filters accepting
  semantic rules.
- **Triggers**:
  - E2E parity test (`tests/integration/test_silver_to_gold_migration_parity.py`)
    fails for any entity.
  - Performance regression > 20% on Silver write duration.
  - Quarantine analytics break in production.
- **Steps**:
  1. Set `BIOETL_LEGACY_SILVER_SEMANTIC=1` in deployment env.
  1. Revert PR introducing auto-promotion.
  1. Revert config migration PRs.

## Verification

- `tests/integration/test_silver_to_gold_migration_parity.py` (NEW) — for each
  entity, assert: pre-migration silver+gold filter outcome == post-migration
  silver(structural)+gold(extended) outcome on representative sample.
- `tests/architecture/test_silver_filter_boundary_inventory.py` — assert that
  no entity config uses semantic fields under `silver_filters` after
  migration.
- `tests/unit/infrastructure/config/test_filter_config_loader.py` — assert
  auto-promotion + deprecation warning behavior.
- `tests/unit/application/core/test_optionality.py` — assert
  `silver_required_fields` source unchanged.

## Acceptance Criteria

- [ ] ADR-048 reviewed and accepted by BioETL Team
- [ ] ADR-048 moved to `docs/02-architecture/decisions/` and indexed in
      `docs/02-architecture/00-overview.md`
- [ ] ADR-028 updated with footer cross-link to ADR-048
- [ ] Inventory baseline captured in `docs/filters/inventory-baseline.md`
- [ ] Per-entity migration diff reviewed and approved
- [ ] 21 entity configs migrated
- [ ] Integration parity test added and green
- [ ] Architecture boundary test updated and green
- [ ] Observability labels updated (Grafana, CLI, docs)
- [ ] No regression in E2E representative runs
- [ ] Feature flag tested in staging
- [ ] CI invariant hardened from warning to error after auto-promotion window

## Changelog

| Date       | Author      | Change                                  |
| ---------- | ----------- | --------------------------------------- |
| 2026-05-12 | BioETL Team | Initial draft of ADR-048 (variant D)    |
