______________________________________________________________________

Version: 1.0.0
Status: Accepted
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-05-26'

______________________________________________________________________

# ADR-049: Context-Aware LOC Target Policy

## Status

Accepted

## Context

During refactoring work on GitHub issues #5056 and #5057 (LOC reduction targets), we identified that a blanket 250 LOC target for all files is not appropriate. Certain file types are legitimately large by nature and forcing decomposition would be counterproductive.

## Problem

The original 250 LOC target was applied uniformly to all files without considering file type and purpose. This led to:

1. **Import facade files** being flagged as "too large" despite being functionally decomposed
2. **Schema/field definition files** being flagged despite inherently large field definitions
3. **Wasted effort** attempting to decompose files that should remain large
4. **Misguided refactoring** that could fragment legitimate architectural patterns

## Decision

We adopt a **context-aware LOC target policy** that excludes certain file types from the 250 LOC target.

### Files EXCLUDED from 250 LOC target:

#### 1. Import Facade Files

**Pattern**: Files that primarily import and re-export from sub-modules to provide a clean API surface.

**Examples**:
- `metrics_definitions.py` (335 LOC) - imports from 5 sub-modules and re-exports metrics

**Rationale**:
- Legitimate architectural pattern for clean API surface
- Functional decomposition already achieved via sub-modules
- Large LOC is due to import statements and `__all__` export list
- Further decomposition would fragment the API surface without benefit

**Acceptance Criteria**:
- File primarily consists of imports from sub-modules
- File re-exports imported items via `__all__`
- Sub-modules contain the actual implementation
- No business logic in the facade file itself

#### 2. Schema/Field Definition Files

**Pattern**: Files containing Pydantic/PyArrow schema or field definitions.

**Examples**:
- `silver_chembl_core.py` (395 LOC) - PyArrow field definitions
- `pipeline_config_common_schemas.py` (392 LOC) - Pydantic schema definitions

**Rationale**:
- Field definitions are inherently large by nature
- Decomposition would fragment schema definitions
- No functional benefit from breaking up field lists
- Schema definitions should remain cohesive

**Acceptance Criteria**:
- File primarily contains schema/field definitions (Pydantic/PyArrow)
- File contains field lists, type definitions, or validation schemas
- No complex business logic algorithms
- Schema definitions should remain together for coherence

### Files KEPT in 250 LOC target:

#### Business Logic Files

**Pattern**: Files containing actual business logic, algorithms, or complex operations.

**Examples**:
- `fs_adr_service.py` (392 LOC → 146 LOC) ✅
- `config/_base.py` (478 LOC → 266 LOC) ✅
- High-risk persistence files (ledger, lineage, checkpoint)

**Rationale**:
- Contains actual business logic suitable for functional decomposition
- Can be decomposed without breaking contracts
- Decomposition improves testability and maintainability
- Risk of large files is higher for business logic

## Consequences

### Positive

1. **Focused refactoring efforts** on files that actually benefit from decomposition
2. **Preserves legitimate architectural patterns** (import facades, schema definitions)
3. **Reduces wasted effort** on inappropriate refactoring targets
4. **Context-aware quality metrics** that consider file type and purpose

### Negative

1. **More complex quality metrics** that need to understand file type
2. **Requires manual classification** of files for LOC target enforcement
3. **Potential for misclassification** if file types are not clearly defined

## Implementation

1. Update GitHub issues #5056 and #5057 with this policy
2. Update code quality tooling to exclude identified file patterns
3. Document this policy in developer guidelines
4. Consider adding file type markers or conventions for easier classification

## References

- GitHub issue #5056: Control-plane persistence LOC reduction
- GitHub issue #5057: Observability/quarantine/config LOC reduction
- Refactoring analysis from Phase 1 and Phase 2 (June 2026)