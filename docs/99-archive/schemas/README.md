# Historical Schema Archive

## Status: Archived (Not Part of Active Reference)

This directory contains historical schema documentation that has been removed from the active reference surface as part of Issue #3092 (Remove Historical Schema Pages from Active Navigation).

## Purpose

These historical schemas are retained for:

1. **Historical Context**: Understanding the evolution of data contracts
2. **Migration Reference**: Assisting with data migration from legacy formats
3. **Audit Trail**: Maintaining a record of past data structures

## Archived Schema Pages

### ChEMBL Entity Schemas

| Entity | Historical Schema Page | Current Canonical Source |
|--------|------------------------|--------------------------|
| Activity | [activity-schema-historical.md](./domain/chembl/activity-schema-historical.md) | [provider reference](../../04-reference/providers/chembl/activity.md) |
| Assay | [assay-schema-historical.md](./domain/chembl/assay-schema-historical.md) | [provider reference](../../04-reference/providers/chembl/assay.md) |
| Molecule | [molecule-schema-historical.md](./domain/chembl/molecule-schema-historical.md) | [provider reference](../../04-reference/providers/chembl/molecule.md) |
| Target | [target-schema-historical.md](./domain/chembl/target-schema-historical.md) | [provider reference](../../04-reference/providers/chembl/target.md) |

## Migration Notes

### Issue #3092 Implementation (2026-04-24)

**Changes Made:**
- Moved historical schema pages from `docs/04-reference/schemas/domain/chembl/` to `docs/99-archive/schemas/domain/chembl/`
- Updated all schema pages with prominent **⚠️ HISTORICAL CONTENT - ARCHIVED** banners
- Added migration notes and current canonical source references
- Updated project navigator to point to current provider references instead of historical schemas
- Updated "Last verified" dates to 2026-04-24

**Rationale:**
- Historical deep schema pages created ambiguity with current canonical contracts
- Developers were confused about which documentation represented current reality
- Maintenance burden of keeping both historical and current schemas updated
- Documentation quality was degraded by outdated information in active navigation

## Usage Guidelines

### When to Use Historical Schemas

✅ **Appropriate Uses:**
- Understanding legacy data formats during migration
- Historical research and audit purposes
- Comparing evolution of data contracts over time

❌ **Inappropriate Uses:**
- Developing new features (use current provider references)
- Configuring pipelines (use current entity configs)
- Data validation (use current runtime validation)

### Current Canonical Sources

For all development work, use these current sources instead:

1. **Provider References**: `docs/04-reference/providers/{provider}/{entity}.md`
2. **Entity Configs**: `configs/entities/{provider}/{entity}.yaml`
3. **Runtime Validation**: Actual validation code in `src/bioetl/domain/validation/`

## Structure

```
docs/99-archive/schemas/
├── README.md                        # This file
└── domain/
    └── chembl/
        ├── activity-schema-historical.md  # Historical activity schema
        ├── assay-schema-historical.md     # Historical assay schema
        ├── molecule-schema-historical.md   # Historical molecule schema
        └── target-schema-historical.md     # Historical target schema
```

## Related Issues

- **Issue #3092**: Remove Historical Schema Pages from Active Navigation
- **Parent Issue**: Documentation Audit 2026-04-23
- **Implementation Plan**: docs/reports/audit-issues/implementation-plans.md

## Maintenance Policy

- Historical schemas are **frozen** and will not be updated
- No new historical schemas will be added to this archive
- Future schema changes will only affect current canonical sources
- Archive may be pruned in future major version releases

## See Also

- [Documentation Governance Policy](../../00-project/governance/01-documentation-governance-style-guide.md)
- [Current Provider References](../../04-reference/providers/)
- [Entity Configs](../../../configs/entities/)
- [Project Navigator](../../00-project/00-map.md)