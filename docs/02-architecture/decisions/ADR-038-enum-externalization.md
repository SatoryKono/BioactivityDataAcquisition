# ADR-038: ChEMBL Enum Values Externalization to YAML

**Status:** Accepted
**Date:** 2026-02-16
**Decision makers:** @BioETL-Team

## Context

ChEMBL enum values (allowed values for `standard-type`, `assay-type`, `molecule-type`,
etc.) were defined in three places:

1. **Python frozensets** in `domain/schemas/constants.py` — used by Pandera schema
   validation (`pa.Field(isin=list(...))`)
2. **Filter YAML sections** in `configs/entities/chembl/*.yaml#filters` — hardcoded
   subsets in `columns:` and `extraction-params:`
3. **DQ YAML sections** in `configs/entities/chembl/*.yaml#quality` — hardcoded
   `allowed:` lists

No single source of truth existed. Updating to a new ChEMBL DB version required
manual edits in 3+ locations with no cross-validation.

## Decision

Create `configs/enums/chembl.yaml` as the **single source of truth** (SSOT) for all
ChEMBL DB enum values. Keep `domain/schemas/constants.py` as pure Python (no I/O) to
preserve domain purity (ARCH-002). Enforce sync between YAML and Python via tests.

### Structure

```
configs/enums/
└── chembl.yaml    # All ChEMBL DB enum values, versioned
```

### Sync mechanism

`domain/schemas/constants.py` contains pure Python frozensets (no file I/O).
`tests/unit/domain/schemas/test-constants-yaml.py` verifies that every Python
constant matches the corresponding YAML value exactly.

**Workflow for ChEMBL version update:**
1. Update `configs/enums/chembl.yaml` (bump version, add/remove values)
2. Run tests — sync tests fail, showing exactly which constants diverge
3. Update `constants.py` to match
4. Tests pass

### What is NOT externalized

- **Regex patterns** (`CHEMBL-ID-PATTERN`, `BAO-ID-PATTERN`, etc.) — format-dependent,
  not DB-version-dependent
- **Domain StrEnums** (`RunType`, `HealthStatus`) — business logic, not external DB data
- **Non-ChEMBL enums** (CrossRef, OpenAlex) — can follow same pattern later

## Alternatives Considered

### A. Runtime YAML loading in constants.py

Load YAML at module import time via `@functools.cache`. Rejected because:
- Violates ARCH-002 (domain purity — no I/O in domain layer)
- `open()` in domain detected by architecture tests

### B. Keep hardcoded Python only (status quo)

Rejected because:
- No declared SSOT for ChEMBL DB version upgrades
- Duplication across Python and YAML configs with no validation

### C. Lazy runtime loading (deferred validation)

Would require rewriting all Pandera schemas to use factory functions instead of
class-level `pa.Field(isin=...)`. Rejected because:
- High migration cost (13 schema files)
- Lose type safety at class definition time
- Pandera class-level validators are idiomatic

### D. Build-time codegen (YAML -> Python)

Generate `constants.py` from YAML via template. Rejected because:
- Adds build step complexity
- Generated files harder to debug
- Overkill for ~80 lines of config

## Consequences

### Positive

- **SSOT**: `configs/enums/chembl.yaml` is the declared authoritative source
- **Domain purity preserved**: `constants.py` has no I/O, passes ARCH-002 checks
- **Zero migration cost**: Public API unchanged, all consumers work as-is
- **Versionable**: `version: "chembl-35"` enables audit and rollback
- **Consistent**: Follows `configs/` hierarchy pattern (ADR-027, ADR-028)
- **Enforced sync**: Tests catch drift between YAML and Python immediately

### Negative

- **Two-step update**: Must update both YAML and Python when values change
  (mitigated by tests that pinpoint exact mismatches)

### Neutral

- Filter and DQ YAML configs continue to hardcode subsets — they select from the
  canonical set for their specific use case. A future enhancement could add
  cross-validation that filter values are subsets of YAML enums.

## Compliance

| Requirement | Status | Notes |
|-------------|--------|-------|
| Domain purity (ARCH-002) | PASS | No I/O in `constants.py` |
| Public API unchanged | PASS | All `__all__` exports identical |
| Types preserved | PASS | `frozenset[str]`, `tuple[float, ...]` |
| Sync enforcement | PASS | 20 sync tests in `test-constants-yaml.py` |

## References

- ADR-027: DQ Rules Externalization
- ADR-028: Filter Rules Externalization
- `configs/enums/chembl.yaml` — SSOT file
- `src/bioetl/domain/schemas/constants.py` — pure Python constants
- `tests/unit/domain/schemas/test-constants-yaml.py` — sync tests
