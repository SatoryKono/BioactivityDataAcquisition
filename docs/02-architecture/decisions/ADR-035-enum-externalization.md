# ADR-035: ChEMBL Enum Values Externalization to YAML

**Status:** Accepted
**Date:** 2026-02-16
**Decision makers:** @BioETL-Team

## Context

ChEMBL enum values (allowed values for `standard_type`, `assay_type`, `molecule_type`,
etc.) were defined in three places:

1. **Python frozensets** in `domain/schemas/constants.py` — used by Pandera schema
   validation (`pa.Field(isin=list(...))`)
2. **Filter YAML configs** in `configs/filters/entities/chembl/*.yaml` — hardcoded
   subsets in `columns:` and `extraction_params:`
3. **DQ YAML configs** in `configs/quality/entities/chembl/*.yaml` — hardcoded
   `allowed:` lists

No single source of truth existed. Updating to a new ChEMBL DB version required
manual edits in 3+ locations with no cross-validation.

## Decision

Create `configs/enums/chembl.yaml` as the **single source of truth** (SSOT) for all
ChEMBL DB enum values. Modify `domain/schemas/constants.py` to load values from this
YAML file at module import time using `@functools.cache`.

### Structure

```
configs/enums/
└── chembl.yaml    # All ChEMBL DB enum values, versioned
```

### Loading mechanism

```python
# domain/schemas/constants.py
@functools.cache
def _load_chembl_enums() -> dict[str, Any]:
    with _ENUMS_YAML_PATH.open() as f:
        return yaml.safe_load(f)

STANDARD_RELATIONS: frozenset[str] = _fs("activity", "standard_relations")
```

**Key properties:**
- Public API (`STANDARD_RELATIONS`, `ASSAY_TYPES`, etc.) is unchanged
- All consumers import from `constants.py` as before — zero migration cost
- `@functools.cache` ensures one file read per process
- YAML file is versioned (`version: "chembl_35"`) for audit trail

### What is NOT externalized

- **Regex patterns** (`CHEMBL_ID_PATTERN`, `BAO_ID_PATTERN`, etc.) — format-dependent,
  not DB-version-dependent
- **Domain StrEnums** (`RunType`, `HealthStatus`) — business logic, not external DB data
- **Non-ChEMBL enums** (CrossRef, OpenAlex) — can follow same pattern later

## Alternatives Considered

### A. Keep hardcoded Python frozensets (status quo)

Rejected because:
- Duplication across Python and YAML configs
- No SSOT for ChEMBL DB version upgrades
- Manual sync required between constants.py and filter/DQ configs

### B. Lazy runtime loading (deferred validation)

Would require rewriting all Pandera schemas to use factory functions instead of
class-level `pa.Field(isin=...)`. Rejected because:
- High migration cost (13 schema files)
- Lose type safety at class definition time
- Pandera class-level validators are idiomatic

### C. Build-time codegen (YAML → Python)

Generate `constants.py` from YAML via template. Rejected because:
- Adds build step complexity
- Generated files harder to debug
- Overkill for ~80 lines of config

## Consequences

### Positive

- **SSOT**: One file to update when ChEMBL DB version changes
- **Zero migration cost**: Public API unchanged, all consumers work as-is
- **Versionable**: `version: "chembl_35"` enables audit and rollback
- **Consistent**: Follows `configs/` hierarchy pattern (ADR-027, ADR-028)
- **Cross-validation**: Tests can verify filter/DQ configs reference valid enum values

### Negative

- **File I/O at import**: One `yaml.safe_load()` call when `constants` module loads
  (~1ms, cached). Acceptable: `domain/schemas/` already depends on Pandera (external lib)
- **Path coupling**: `constants.py` uses relative path to `configs/enums/chembl.yaml`.
  Mitigated by test `test_chembl_yaml_exists`

### Neutral

- Filter and DQ YAML configs continue to hardcode subsets — they select from the
  canonical set for their specific use case. A future enhancement could add
  cross-validation that filter values are subsets of YAML enums.

## Compliance

| Requirement | Status | Notes |
|-------------|--------|-------|
| Public API unchanged | PASS | All `__all__` exports identical |
| Types preserved | PASS | `frozenset[str]`, `tuple[float, ...]` |
| Cached loading | PASS | `@functools.cache` — one read per process |
| Tests | PASS | `tests/unit/domain/schemas/test_constants_yaml.py` |

## References

- ADR-027: DQ Rules Externalization
- ADR-028: Filter Rules Externalization
- `configs/enums/chembl.yaml` — SSOT file
- `src/bioetl/domain/schemas/constants.py` — loader
- `tests/unit/domain/schemas/test_constants_yaml.py` — tests
