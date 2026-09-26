# Migration Script Lifecycle Policy

## Overview

Oneoff migration scripts in `scripts/ops/migrations/oneoff/` are temporary scripts designed for specific migration tasks. To prevent accumulation of dead code, all migration scripts must have sunset dates and follow this lifecycle policy.

## Sunset Date Requirements

All oneoff migration scripts MUST include:

```python
"""Script description.

SUNSET_DATE: YYYY-MM-DD
DEPRECATED: This oneoff migration script should be removed after the sunset date.
RATIONALE: Explanation of why this script is temporary and when it can be removed.
"""
```

### Sunset Date Calculation

- **Default sunset:** 6 months from script creation date
- **Short-lived migrations:** 3 months for simple, low-risk migrations
- **Complex migrations:** 12 months for complex, high-impact migrations
- **Format:** YYYY-MM-DD (ISO 8601)

## Lifecycle Stages

### Stage 1: Active (0 - 3 months)
- Script is actively maintained
- May be updated if bugs are found
- Should be tested before use
- Monitored for usage and effectiveness

### Stage 2: Deprecated (3 - 6 months)
- Script is marked as DEPRECATED
- No new features or changes
- Existing bugs may not be fixed
- Users warned about deprecation
- Sunset date approaching

### Stage 3: Sunset (after sunset date)
- Script should be removed from repository
- Move to `docs/99-archive/oneoff-migrations/` if reference needed
- Update migration history documentation
- Remove from scripts inventory

## Sunset Date Validation

### Automated Checks

CI should include validation for expired sunset dates:

```bash
# Check for expired migration scripts
python scripts/ops/migrations/validate_sunset_dates.py
```

### Manual Review

Before removing a script:
1. Verify script is no longer needed
2. Check migration history documentation
3. Confirm no active references in codebase
4. Archive script if reference needed
5. Update scripts inventory

## Archive Policy

Scripts that should be preserved for reference:

- **Complex migrations** with historical value
- **Significant schema changes** affecting data lineage
- **Breaking changes** requiring future reference
- **Custom migrations** with unique patterns

Archive location: `docs/99-archive/oneoff-migrations/`

## Scripts Inventory

The scripts inventory should track:

- Script name and purpose
- Creation date
- Sunset date
- Current lifecycle stage
- Dependencies and requirements
- Last execution date (if tracked)

## Exceptions

Scripts without sunset dates require:

- **Explicit approval** from maintainers
- **Documentation** of long-term purpose
- **Regular review** every 6 months
- **Justification** in code review

## Related Documentation

- `scripts/ops/migrations/README.md` - Migration scripts overview
- `docs/99-archive/oneoff-migrations/` - Archived migration scripts
- `configs/quality/scripts_lifecycle_registry.json` - Scripts lifecycle registry

## Maintenance

This policy should be reviewed:

- **Annually** or when migration patterns change
- **When new migration script patterns** are introduced
- **When sunset date validation** is added to CI
- **When archive policy** needs adjustment