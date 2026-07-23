______________________________________________________________________

Version: 0.2.0
Status: Retired Draft
Class: historical-working-document
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-06-15'

______________________________________________________________________

# Retired Draft: Silver Filters Structural Scope

**Date:** 2026-05-12
**Status:** Retired Draft
**Decision makers:** @BioETL-Team
**Related:** ADR-002, ADR-018, ADR-027, ADR-028, ADR-045
**Amends:** ADR-028 (Filter Rules Externalization)

> NOTE: This file is not an accepted ADR and must not be cited as ADR-048.
> The accepted canonical ADR-048 is
> `docs/02-architecture/decisions/ADR-048-domain-schema-boundary-and-runtime-pandera-compat.md`.
> This file is retained only as historical design rationale for the
> silver_filters -> gold_filters migration. Normative filter-boundary
> governance now lives in
> `docs/02-architecture/decisions/ADR-050-silver-structural-gold-semantic-filter-boundary.md`.

Current implementation snapshot (2026-06-15):

- Semantic Silver filter promotion is implemented in
  `src/bioetl/infrastructure/config/silver_filter_migration.py`.
- `src/bioetl/infrastructure/schemas/filter_config.py` and
  `src/bioetl/infrastructure/schemas/pipeline_config.py` apply normalization
  before validation.
- `SilverFiltersFileConfig.to_domain()` and `SilverFiltersConfig.to_domain()`
  project domain Silver filters as structural-only.
- Active YAML cleanup is complete: `configs/entities/**/*.yaml` no longer
  carries semantic buckets under `filters.silver_filters`; CI guardrails fail
  reintroduction.

## Context

ADR-028 externalized filter rules into a hierarchical configuration system with
four sections: `input_filter`, `silver_filters`, `gold_filters`, and
`extraction_params`. The `silver_filters` and `gold_filters` sections share the
same `BaseFilterConfig` shape (`columns`, `ranges`, `list_lengths`,
`list_contains`, `required_fields`, `exclude_if_present`) but apply at
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
  list_lengths: {...}
  list_contains: {...}
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
1. Normalize config payloads at infrastructure boundaries:
   `FilterConfigFile`, `PipelineYamlConfig`, `FilterConfigLoader.load()`, and
   `FilterConfigLoader.load_as_dict()` auto-promote semantic rules from
   `silver_filters` to `gold_filters` before domain conversion.
1. Keep `SilverFiltersFileConfig` / `SilverFiltersConfig` Pydantic-compatible
   with legacy semantic keys, but make `to_domain()` return structural-only
   Silver config in the default mode.
1. Add runtime identity field `silver_filter_compatibility_mode` so effective
   config, run manifests, execution fingerprints, and checkpoint compatibility
   capture the canonical structural-only Silver behavior explicitly.
1. Add CI invariant for committed inventory artifacts and later harden entity
   configs to reject semantic fields under `silver_filters` after the YAML
   rewrite window closes.
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
  Grafana `bioetl-silver-reject-explorer.json` dashboard was removed 2026-07-23;
  CLI `--silver-filter-only` and DQ aggregates preserved with
  narrowed semantics ("structural rejects").
- 8 transformer classes — receive `SilverFilterConfig` via DI; type-narrowing
  is invisible to them.

## Consequences

### Positive

- **DRY**: Eliminates routine duplication between silver_filters and
  gold_filters (observed in the original 2026-05-12 baseline; cleaned from
  active YAML on 2026-06-15).
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

- **Migration overhead**: active entity configs require per-entity review for
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
1. **Phase 1**: Runtime identity + domain compatibility mode (no breaking
   SilverFilterConfig change).
1. **Phase 2**: Infrastructure schema/loader auto-promotion and structural
   Silver domain conversion.
1. **Phase 3**: Application/checkpoint/control-plane identity alignment.
1. **Phase 4**: Configs migration (auto-script + per-entity review).
1. **Phase 5**: Observability (relabel "structural" semantics).
1. **Phase 6**: Tests.
1. **Phase 7**: Documentation.
1. **Phase 8**: Phased rollout with feature flag.

## Rollout

- Phased: Domain → Infrastructure → Configs → Tests → Observability →
  Hardening.
- Runtime identity stays pinned to `structural_only_compat`; historical
  snapshots with `structural_only_auto_promote` remain readable only as a
  compatibility alias.
- Auto-promotion period: 1-2 release cycles before hardening CI invariant
  from warning to error.

## Rollback

- **Last known good**: pre-retired-filter-draft state with silver_filters accepting
  semantic rules.
- **Triggers**:
  - E2E parity test (`tests/integration/test_silver_to_gold_migration_parity.py`)
    fails for any entity.
  - Performance regression > 20% on Silver write duration.
  - Quarantine analytics break in production.
- **Steps**:
  1. Revert the structural-only normalization change set.
  1. Revert config migration PRs.

## Verification

- `tests/integration/test_silver_to_gold_migration_parity.py` (planned) — for
  each entity, assert: pre-migration silver+gold filter outcome ==
  post-migration silver(structural)+gold(extended) outcome on representative
  sample.
- `tests/architecture/test_silver_filter_boundary_inventory.py` — validates
  committed inventory shape, business-only migration metadata, shadow-analysis
  metadata, and that `inventory-baseline.{csv,json,md}` match generator output.
- `tests/unit/infrastructure/config/test_filter_config_loader.py` — assert
  auto-promotion and legacy rollback behavior.
- `tests/unit/application/core/test_optionality.py` — assert
  `silver_required_fields` source unchanged.

## Acceptance Criteria

- [x] ADR-050 created as normative filter-boundary governance; do not reuse
      accepted ADR-048 or this retired draft
- [x] ADR-028 updated with cross-link to ADR-050
- [x] Inventory baseline captured in `docs/filters/inventory-baseline.md`
- [x] Per-entity migration diff reviewed and approved
- [x] 22 active entity configs with legacy semantic `silver_filters` keys migrated or explicitly justified
- [x] Targeted config guardrail tests added and green
- [x] Architecture boundary test updated and green
- [ ] Observability labels updated (Grafana, CLI, docs)
- [ ] No regression in E2E representative runs
- [ ] Feature flag tested in staging
- [x] CI invariant added for active YAML semantic Silver bucket reintroduction

## Changelog

| Date       | Author      | Change                                  |
| ---------- | ----------- | --------------------------------------- |
| 2026-05-12 | BioETL Team | Initial draft of ADR-048 (variant D)    |
| 2026-06-15 | Codex       | Marked ADR-050 as the canonical replacement for normative filter-boundary governance. |
| 2026-06-15 | Codex       | Recorded active YAML cleanup completion and source-profile baseline split. |
