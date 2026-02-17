# ADR-035: Composite Decomposition Strategy

- **Status**: Accepted
- **Date**: 2026-02-17
- **Related**: ADR-026, ADR-029, ADR-034

## Context

`composite_publication` historically exposed a single denormalized record containing:

- canonical publication attributes;
- provider-qualified enrichment attributes;
- merge lineage and orchestration metadata.

This shape is convenient for migration-free reads, but it mixes distinct concerns and makes data contracts harder to evolve. Provider-agnostic fields and provider-specific evidence have different lifecycle and validation semantics, while lineage metadata is operational data rather than domain data.

## The Decision

Composite publication output is decomposed into three logical table families plus one temporary compatibility surface:

1. **Core table** (`composite_publication_core`)

   - one row per `publication_id`;
   - canonical provider-agnostic publication attributes;
   - no provider-qualified columns;
   - no lineage/merge orchestration fields.

1. **Provider extension tables** (`composite_publication_ext_<provider>`)

   - one row per `(publication_id, provider)` or provider-native key;
   - provider-qualified attributes preserved without flattening into core;
   - source-specific optionality and drift isolated per provider.

1. **Lineage table** (`composite_publication_lineage`)

   - one row per merge event;
   - `_composite_*`, `_source_providers`, `_enrichment_status`, `_lineage_*` and merge diagnostics;
   - explicitly treated as operational metadata.

1. **Compatibility view** (`composite_publication_compat_vw`)

   - SQL view that reproduces current denormalized composite interface;
   - built by joining `core + extensions + lineage`;
   - transitional artifact for downstream consumers during migration window.

## Justification

- Separates canonical semantics from provider evidence and operational provenance.
- Reduces schema-churn blast radius when one provider evolves.
- Enables targeted quality rules by table family.
- Preserves backward compatibility through a stable migration bridge (compat view).

## Consequences

### Positive

- Clear contracts per concern (core / extension / lineage).
- Easier provider onboarding and deprecation.
- Safer evolution of lineage metadata without changing analytical schemas.

### Negative

- More physical datasets and joins in write/read paths.
- Temporary duplication while compatibility view is maintained.
- Requires migration communication and sunset policy for legacy interface.

## Migration Notes

- New consumers SHOULD read `core` plus explicit extension tables.
- Legacy consumers MAY continue reading `composite_publication_compat_vw` during migration.
- Compatibility view retirement requires deprecation notice and adoption audit.

## Related ADRs

- [ADR-026](ADR-026-composite-pipeline-pattern.md): Composite orchestration and merge behavior.
- [ADR-029](ADR-029-output-metadata-unification.md): Metadata field standardization.
- [ADR-034](ADR-034-schema-domain-pairs.md): Externalized schema management discipline.
