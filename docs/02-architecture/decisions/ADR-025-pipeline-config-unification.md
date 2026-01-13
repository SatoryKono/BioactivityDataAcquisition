# ADR-025: Pipeline Configuration Unification

**Status**: Accepted
**Date**: 2026-01-13
**Authors**: Claude Code
**Reviewers**: -

## Context

BioETL uses YAML configuration files for pipeline definitions. The project has evolved
to include 19 pipeline configs across 7 providers, plus defaults and source configs.

A configuration audit was requested to:
1. Analyze compliance with the reference schema (RULES.md v5.0, Appendix D)
2. Identify inconsistencies and violations
3. Propose a unified configuration structure
4. Create a migration plan

## Decision

After comprehensive analysis of all configuration files, we have decided to:

### 1. Retain the Current Configuration Architecture

The existing three-tier configuration structure is well-designed and follows DRY:

```
configs/
├── pipelines/
│   ├── _defaults.yaml       # Cross-cutting defaults
│   ├── _base.yaml           # Schema documentation (NEW)
│   ├── _providers/          # Provider documentation (NEW)
│   │   ├── chembl.yaml
│   │   ├── pubchem.yaml
│   │   └── ...
│   └── <provider>/
│       └── <entity>.yaml    # Entity-specific configs
└── sources/
    └── <provider>.yaml      # Provider-level API settings
```

**Rationale**: The current architecture already implements:
- Inheritance via `_defaults.yaml`
- Separation of concerns (pipeline vs source configs)
- Consistent parameter naming
- No critical violations

### 2. Document Rather Than Restructure

Instead of migrating to a nested schema (`pipeline.name` vs `pipeline_name`),
we document the chosen flat schema and its rationale.

**Rationale**:
- Current structure is consistent across all 19 configs
- Migration would require code changes with no functional benefit
- Flat keys are equally valid and more concise

### 3. Use Flat Naming Convention: `<provider>_<entity>`

The project uses `chembl_activity` rather than `activity_chembl`.

**Rationale**:
- Consistent across all configs
- Groups pipelines by provider in alphabetical listings
- Matches source file organization (`configs/pipelines/chembl/`)

### 4. Add Documentation Files (Non-Breaking)

New files provide schema documentation without modifying existing configs:

| File | Purpose |
|------|---------|
| `_base.yaml` | Canonical schema with comments |
| `_providers/*.yaml` | Provider-specific documentation |
| `reports/` | Analysis artifacts |

### 5. Defer JSON Schema Validation

JSON Schema validation is recommended but deferred to Phase 2.

**Rationale**:
- Current configs are all compliant
- Schema validation is enhancement, not critical fix
- Can be added incrementally

## Consequences

### Positive

1. **No breaking changes**: Existing configs work unchanged
2. **Clear documentation**: Schema is now fully documented
3. **Provider knowledge captured**: API limits, auth requirements documented
4. **Audit trail**: Analysis artifacts preserved in `reports/`

### Negative

1. **Schema differs from RULES.md Appendix D**: Documented deviation
2. **No automated validation yet**: Deferred to Phase 2

### Neutral

1. **Two sources of truth**: `_defaults.yaml` (runtime) + `_base.yaml` (documentation)
   - Mitigated by clear comments indicating `_base.yaml` is for documentation

## Alternatives Considered

### A. Full Schema Migration

Migrate all configs to nested structure:
```yaml
pipeline:
  name: chembl_activity
  provider: chembl
  entity: activity
```

**Rejected**: High effort, low value. Current structure is equally valid.

### B. YAML Anchors for Inheritance

Use YAML anchors/aliases for config inheritance:
```yaml
<<: *defaults
pipeline_name: chembl_activity
```

**Rejected**: Requires config loader changes. Current file-based inheritance works.

### C. Single Consolidated Config

Merge all provider configs into one large file.

**Rejected**: Reduces maintainability, harder to navigate.

## Compliance

| Requirement | Status | Notes |
|-------------|--------|-------|
| `sink.silver.format: delta` | PASS | All configs inherit from defaults |
| `sink.silver.primary_key` | PASS | All entity configs specify |
| `dq_rules` thresholds | PASS | 0.05/0.20 in defaults |
| `circuit_breaker` settings | PASS | 5/300 in defaults |
| `rate_limit` per provider | PASS | In source configs |
| No hardcoded secrets | PASS | Uses `${ENV_VAR}` syntax |

## References

- [RULES.md v5.0, Appendix D](../../../RULES.md) - Reference schema
- [reports/pipeline-config-matrix.csv](../../../reports/pipeline-config-matrix.csv) - Compliance matrix
- [reports/pipeline-config-issues.md](../../../reports/pipeline-config-issues.md) - Detailed analysis
- [reports/pipeline-config-migration-plan.md](../../../reports/pipeline-config-migration-plan.md) - Migration plan

## Changelog

| Date | Author | Change |
|------|--------|--------|
| 2026-01-13 | Claude Code | Initial version |
