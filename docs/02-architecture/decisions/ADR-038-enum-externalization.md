---
Version: 1.0.0
Status: Accepted
Class: published
Owner: BioETL Team
Reviewers:
- BioETL Team
Last verified: '2026-04-23'
---

# ADR-038: ChEMBL Enum Values Externalization to YAML

**Date:** 2026-02-16
**Status:** Accepted
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

Create `configs/enums/chembl.yaml` as the **single source of truth** (SSOT)
for ChEMBL DB enum values used by schemas, normalization profiles, DQ
configuration, filters, and observed-value governance. Keep
`domain/schemas/constants.py` as pure Python (no I/O) to preserve domain purity
(ARCH-002). Enforce sync between YAML and Python via tests.

### Structure

```
configs/enums/
└── chembl.yaml    # All ChEMBL DB enum values, versioned
```

### Sync mechanism

`domain/schemas/constants.py` contains pure Python frozensets (no file I/O).
`tests/unit/domain/schemas/test_constants_yaml.py` verifies that every Python
constant matches the corresponding YAML value exactly.

**Workflow for ChEMBL version or governed-vocabulary update:**
1. Update `configs/enums/chembl.yaml` (bump version, add/remove values)
2. Run tests — sync tests fail, showing exactly which constants diverge
3. Update `constants.py` to match
4. Update DQ/filter/profile surfaces that consume the vocabulary
5. Regenerate normalization matrix artifacts when profile or DQ semantics change
6. Tests pass

### What is NOT externalized

- **Regex patterns** (`CHEMBL-ID-PATTERN`, `BAO-ID-PATTERN`, etc.) — format-dependent,
  not DB-version-dependent
- **Domain StrEnums** (`RunType`, `HealthStatus`) — business logic, not external DB data
- **Cross-provider publication classification taxonomy** — governed by
  `configs/enums/publication_type_classification.csv` and the
  `publication_type_unified` / `publication_subclass` / `publication_class`
  derived fields, not by raw provider publication-type fields
- **Non-ChEMBL provider enums** (CrossRef, OpenAlex, PubMed, Semantic Scholar) —
  can follow this YAML pattern only when the provider owns a stable finite
  vocabulary; free-form raw values must remain raw sidecars

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

- Filter and DQ YAML configs continue to declare subsets for their specific use
  case, but subset governance is now enforced by
  `tests/integration/config/test_chembl_enum_parity.py` for covered fields.
- Representative observed-value fixtures under
  `tests/fixtures/normalization/chembl_observed_values.yaml` verify that
  sampled runtime-like values remain within the same SSOT or approved derived
  vocabulary surfaces without requiring live ChEMBL network calls.

## Compliance

| Requirement | Status | Notes |
|-------------|--------|-------|
| Domain purity (ARCH-002) | PASS | No I/O in `constants.py` |
| Public API unchanged | PASS | All `__all__` exports identical |
| Types preserved | PASS | `frozenset[str]`, `tuple[float, ...]` |
| Sync enforcement | PASS | Sync tests in `test_constants_yaml.py` |
| DQ/filter subset governance | PASS | Covered by `test_chembl_enum_parity.py` |
| Observed-value governance | PASS | Covered by `test_chembl_observed_value_fixtures.py` |
| Derived publication taxonomy | PASS | Raw provider values preserved; derived fields validated through `publication_type_classification.csv` |

## References

- ADR-027: DQ Rules Externalization
- ADR-028: Filter Rules Externalization
- `configs/enums/chembl.yaml` — SSOT file
- `configs/enums/publication_type_classification.csv` — cross-provider publication classification taxonomy
- `src/bioetl/domain/schemas/constants.py` — pure Python constants
- `tests/unit/domain/schemas/test_constants_yaml.py` — sync tests
- `tests/integration/config/test_chembl_enum_parity.py` — subset governance tests
- `tests/integration/config/test_chembl_observed_value_fixtures.py` — offline observed-value governance tests

## Rollout

- Rollout steps MUST be sequenced before broad adoption.
- Documentation, configuration, and test surfaces SHOULD be updated in the same change set when the decision is implemented.
- Breaking or migration-sensitive adoption SHOULD include an explicit transition window.

## Rollback

- Rollback MUST identify the last known-good behavior or artifact set.
- If the decision changes contracts, configuration, or storage semantics, rollback SHOULD include data and compatibility checks.
- Rollback triggers SHOULD be observable through tests, runtime signals, or regression symptoms.

## Verification

- Verify architecture, configuration, and documentation changes against the current codebase.
- Run the relevant tests, validators, or parity checks before considering the ADR fully adopted.
- Confirm downstream docs and contracts reflect the same decision boundaries.

## Acceptance Criteria

- [ ] The decision is documented with current status, date, and owner metadata.
- [ ] The implementation path or adoption boundary is testable and linked from the ADR.
- [ ] Supersession or migration impact is documented when the decision changes an earlier posture.
- [ ] Related docs, contracts, and operational guidance are aligned with this ADR.
