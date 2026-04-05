______________________________________________________________________

Version: 1.0.0
Status: Accepted
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-30'

______________________________________________________________________

# ADR-031: Loading Strategy Formalization

**Date:** 2026-01-26
**Status:** Accepted
**Decision makers:** @BioETL-Team

## Context

### Problem Statement

Publication pipelines currently have implicit loading behavior:

1. They **look like** incremental pipelines (same config structure)
1. They **behave as** full-scan pipelines (via `force-full-scan: true`)
1. There is **no explicit policy** documenting this distinction

This creates confusion:

- New team members assume checkpoint resume works for publications
- The boolean `force-full-scan` flag doesn't clearly communicate intent
- No formalized extension point for future watermark-based loading

### Current State (ADR-030)

ADR-030 introduced `force-full-scan: bool` to disable checkpoint resume:

```yaml
# Publication pipeline
force-full-scan: true  # But why? What's the strategy?
```

This works but has limitations:

- Boolean flag doesn't scale to multiple strategies
- No explicit documentation of loading semantics in the config
- No type-safe validation of strategy-specific constraints

## Decision

Introduce explicit `LoadingStrategy` enum and formalize loading behavior:

### 1. LoadingStrategy Enum

```python
class LoadingStrategy(StrEnum):
    """Loading strategy for pipeline data extraction."""

    FULL - SCAN - ONLY = "full-scan-only"
    """Each run performs full scan. Checkpoint resume disabled."""
```

> **Note:** `WATERMARK-BASED` strategy is planned but not yet implemented.
> See [Future Work](#future-work) for prerequisites and implementation plan.

### 2. PipelineConfig Field

```python
@dataclass(frozen=True, slots=True)
class PipelineConfig:
    # ... existing fields ...

    # Pagination strategy (ADR-030)
    force - full - scan: bool = False

    # Loading strategy (ADR-031) - explicit formalization
    loading - strategy: LoadingStrategy | str | None = None
```

### 3. YAML Configuration

```yaml
# configs/entities/chembl/publication.yaml
pipeline-name: chembl_publication
provider: chembl
entity_type: publication

# Loading strategy (ADR-030, ADR-031)
# Explicit strategy declaration
force-full-scan: true
loading-strategy: full-scan-only
```

### 4. WatermarkStrategyPort (Future Work)

> **NOT YET IMPLEMENTED.** The `WatermarkStrategyPort` and `WATERMARK-BASED` enum value
> will be added when watermark-based incremental loading is needed.
> See [Future Work](#future-work) for the planned interface and prerequisites.

### 5. Validation Rules

| Strategy          | Checkpoint Resume | Watermark | Deduplication             |
| ----------------- | ----------------- | --------- | ------------------------- |
| `full-scan-only`  | BLOCKED           | N/A       | content-hash on Silver    |
| `watermark-based` | ALLOWED           | REQUIRED  | watermark field filtering |

### 6. Backward Compatibility

- `force-full-scan: true` continues to work
- When `loading-strategy` is not set, it's derived from `force-full-scan`
- Explicit `loading-strategy` takes precedence over `force-full-scan`

## Consequences

### Positive

1. **Explicit semantics**: Config clearly states loading strategy
1. **Type safety**: Enum prevents invalid strategy values
1. **Extensible**: Easy to add new strategies (e.g., cursor-based)
1. **Self-documenting**: Strategy name communicates intent
1. **Validation**: Can enforce strategy-specific constraints

### Negative

1. **Migration effort**: Existing configs need `loading-strategy` field
1. **Two fields**: Both `force-full-scan` and `loading-strategy` exist (temporary)

### Mitigations

- **Migration**: All publication configs updated with `loading-strategy: full-scan-only`
- **Two fields**: `loading-strategy` takes precedence; `force-full-scan` maintained for compatibility

## Why Publication !== Activity

| Aspect                   | Activity Pipelines         | Publication Pipelines          |
| ------------------------ | -------------------------- | ------------------------------ |
| **API behavior**         | Stable offset pagination   | Offset shifts on updates       |
| **Update frequency**     | Rare (assay data static)   | Frequent (citations, metadata) |
| **Checkpoint safety**    | Safe to resume from offset | Unsafe (data loss/duplicates)  |
| **Recommended strategy** | `watermark-based` (future) | `full-scan-only`               |

## Implementation

### Files Modified

**Domain:**

- `src/bioetl/domain/medallion.py` — Add `LoadingStrategy` enum (currently: `FULL-SCAN-ONLY` only)
- `src/bioetl/domain/config/pipeline.py` — Add `loading-strategy` field to `PipelineConfig`

**Application:**

- `src/bioetl/application/core/lifecycle/checkpoint_manager.py` — Use `LoadingStrategy` for validation

**Infrastructure:**

- `src/bioetl/infrastructure/schemas/pipeline_config.py` — Add `loading-strategy` to YAML schema
- `src/bioetl/infrastructure/config/converters.py` — Pass `loading-strategy` in conversion

**Composition:**

- `src/bioetl/composition/factories/services_factory.py` — Pass `loading-strategy` to CheckpointManager
- `src/bioetl/composition/factories/pipeline_factory.py` — Use `config.loading-strategy`

**Configs:**

- `configs/entities/chembl/publication.yaml` — Add `loading-strategy: full-scan-only`
- `configs/entities/chembl/publication_term.yaml` — Add `loading-strategy: full-scan-only`
- `configs/entities/chembl/publication_similarity.yaml` — Add `loading-strategy: full-scan-only`
- `configs/entities/pubmed/publication.yaml` — Add `loading-strategy: full-scan-only`
- `configs/entities/crossref/publication.yaml` — Add `loading-strategy: full-scan-only`
- `configs/entities/openalex/publication.yaml` — Add `loading-strategy: full-scan-only`
- `configs/entities/semanticscholar/publication.yaml` — Add `loading-strategy: full-scan-only`

### Tests

- `tests/unit/domain/test_medallion.py` — Test `LoadingStrategy` enum
- `tests/unit/application/core/test_checkpoint_manager.py` — Test loading-strategy validation
- `tests/architecture/test_force_full_scan_publication.py` — Verify publication configs

## Future Work

### Watermark Implementation (When Ready)

Prerequisites:

1. Confirm API provides reliable `updated-at` or version field
1. Verify field is monotonically increasing
1. Ensure API supports filtering by watermark

Steps:

1. Add `WATERMARK-BASED = "watermark-based"` to `LoadingStrategy` enum
1. Create `src/bioetl/domain/ports/watermark.py` with `WatermarkStrategyPort`:
   ```python
   @runtime-checkable
   class WatermarkStrategyPort(Protocol):
       async def get-watermark(self, pipeline-name: str) -> datetime | int | str | None: ...
       async def update-watermark(self, pipeline-name: str, watermark: ...) -> None: ...
       async def clear-watermark(self, pipeline-name: str) -> None: ...
   ```
1. Export `WatermarkStrategyPort` from `src/bioetl/domain/ports/__init__.py`
1. Implement `LocalWatermarkStorage` adapter
1. Add `watermark-field` to pipeline config
1. Update fetchers to use watermark filtering
1. Add integration tests with VCR

### Strategy Migration

Once watermark is implemented:

1. Activity pipelines: Switch to `watermark-based`
1. Publication pipelines: Keep `full-scan-only`
1. Deprecate `force-full-scan` field

## References

- RULES.md §3 — Medallion Architecture
- ADR-030 — Publication Pagination Strategy
- ADR-011 — Remove Watermark Mechanism
- ChEMBL API Documentation — Offset pagination behavior

## Compliance

| Control      | Requirement                                                                | Status | Evidence                                    |
| ------------ | -------------------------------------------------------------------------- | ------ | ------------------------------------------- |
| Format       | ADR MUST use standard metadata and normalized section headings             | `pass` | `ADR-031-loading-strategy-formalization.md` |
| Status       | ADR status MUST be explicit and consistent                                 | `pass` | `Accepted`                                  |
| Supersession | Superseded or superseding ADRs SHOULD be linked explicitly when applicable | `n/a`  | `metadata block`                            |
| Verification | Implementation and validation expectations MUST be documented              | `pass` | `Verification / Acceptance Criteria`        |
| References   | Related ADRs, docs, or artifacts SHOULD be linked                          | `pass` | `References`                                |

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
