# ADR-031: Loading Strategy Formalization

**Status:** Accepted
**Date:** 2026-01-26
**Decision makers:** @BioETL-Team
**Relates to:** ADR-030 (Publication Pagination Strategy), ADR-011 (Remove Watermark)

## Context

### Problem Statement

Publication pipelines currently have implicit loading behavior:
1. They **look like** incremental pipelines (same config structure)
2. They **behave as** full-scan pipelines (via `force_full_scan: true`)
3. There is **no explicit policy** documenting this distinction

This creates confusion:
- New team members assume checkpoint resume works for publications
- The boolean `force_full_scan` flag doesn't clearly communicate intent
- No formalized extension point for future watermark-based loading

### Current State (ADR-030)

ADR-030 introduced `force_full_scan: bool` to disable checkpoint resume:

```yaml
# Publication pipeline
force_full_scan: true  # But why? What's the strategy?
```

This works but has limitations:
- Boolean flag doesn't scale to multiple strategies
- No explicit documentation of loading semantics in the config
- No type-safe validation of strategy-specific constraints

## Decision

Introduce explicit `LoadingStrategy` enum and formalize loading behavior:

### 1. LoadingStrategy Enum

```python
class LoadingStrategy(str, Enum):
    """Loading strategy for pipeline data extraction."""

    FULL_SCAN_ONLY = "full_scan_only"
    """Each run performs full scan. Checkpoint resume disabled."""

    WATERMARK_BASED = "watermark_based"
    """Incremental loading via watermark. PLACEHOLDER - NOT YET IMPLEMENTED."""
```

### 2. PipelineConfig Field

```python
@dataclass(frozen=True, slots=True)
class PipelineConfig:
    # ... existing fields ...

    # Pagination strategy (ADR-030)
    force_full_scan: bool = False

    # Loading strategy (ADR-031) - explicit formalization
    loading_strategy: LoadingStrategy | str | None = None
```

### 3. YAML Configuration

```yaml
# configs/pipelines/chembl/publication.yaml
pipeline_name: chembl_publication
provider: chembl
entity_type: publication

# Loading strategy (ADR-030, ADR-031)
# Explicit strategy declaration
force_full_scan: true
loading_strategy: full_scan_only
```

### 4. WatermarkStrategyPort (Placeholder)

```python
@runtime_checkable
class WatermarkStrategyPort(Protocol):
    """Port for watermark-based incremental loading.

    PLACEHOLDER - NOT YET IMPLEMENTED.
    """

    async def get_watermark(self, pipeline_name: str) -> datetime | int | str | None: ...
    async def update_watermark(self, pipeline_name: str, watermark: ...) -> None: ...
    async def clear_watermark(self, pipeline_name: str) -> None: ...
```

### 5. Validation Rules

| Strategy | Checkpoint Resume | Watermark | Deduplication |
|----------|------------------|-----------|---------------|
| `full_scan_only` | BLOCKED | N/A | content_hash on Silver |
| `watermark_based` | ALLOWED | REQUIRED | watermark field filtering |

### 6. Backward Compatibility

- `force_full_scan: true` continues to work
- When `loading_strategy` is not set, it's derived from `force_full_scan`
- Explicit `loading_strategy` takes precedence over `force_full_scan`

## Consequences

### Positive

1. **Explicit semantics**: Config clearly states loading strategy
2. **Type safety**: Enum prevents invalid strategy values
3. **Extensible**: Easy to add new strategies (e.g., cursor-based)
4. **Self-documenting**: Strategy name communicates intent
5. **Validation**: Can enforce strategy-specific constraints

### Negative

1. **Migration effort**: Existing configs need `loading_strategy` field
2. **Two fields**: Both `force_full_scan` and `loading_strategy` exist (temporary)
3. **Unused port**: `WatermarkStrategyPort` is a placeholder

### Mitigations

- **Migration**: All publication configs updated with `loading_strategy: full_scan_only`
- **Two fields**: `loading_strategy` takes precedence; `force_full_scan` maintained for compatibility
- **Unused port**: Clearly marked as placeholder; NoOp implementation provided

## Why Publication !== Activity

| Aspect | Activity Pipelines | Publication Pipelines |
|--------|-------------------|----------------------|
| **API behavior** | Stable offset pagination | Offset shifts on updates |
| **Update frequency** | Rare (assay data static) | Frequent (citations, metadata) |
| **Checkpoint safety** | Safe to resume from offset | Unsafe (data loss/duplicates) |
| **Recommended strategy** | `watermark_based` (future) | `full_scan_only` |

## Implementation

### Files Modified

**Domain:**
- `src/bioetl/domain/medallion.py` — Add `LoadingStrategy` enum
- `src/bioetl/domain/config.py` — Add `loading_strategy` field to `PipelineConfig`
- `src/bioetl/domain/ports/watermark.py` — Add `WatermarkStrategyPort` (placeholder)
- `src/bioetl/domain/ports/__init__.py` — Export new port

**Application:**
- `src/bioetl/application/core/checkpoint_manager.py` — Use `LoadingStrategy` for validation

**Infrastructure:**
- `src/bioetl/infrastructure/schemas/pipeline_config.py` — Add `loading_strategy` to YAML schema
- `src/bioetl/infrastructure/config/_base.py` — Pass `loading_strategy` in conversion

**Composition:**
- `src/bioetl/composition/factories/services_factory.py` — Pass `loading_strategy` to CheckpointManager
- `src/bioetl/composition/factories/pipeline_factory.py` — Use `config.loading_strategy`

**Configs:**
- `configs/pipelines/chembl/publication.yaml` — Add `loading_strategy: full_scan_only`
- `configs/pipelines/chembl/publication_term.yaml` — Add `loading_strategy: full_scan_only`
- `configs/pipelines/chembl/publication_similarity.yaml` — Add `loading_strategy: full_scan_only`
- `configs/pipelines/pubmed/publication.yaml` — Add `loading_strategy: full_scan_only`
- `configs/pipelines/crossref/publication.yaml` — Add `loading_strategy: full_scan_only`
- `configs/pipelines/openalex/publication.yaml` — Add `loading_strategy: full_scan_only`
- `configs/pipelines/semanticscholar/publication.yaml` — Add `loading_strategy: full_scan_only`

### Tests

- `tests/unit/domain/test_medallion.py` — Test `LoadingStrategy` enum
- `tests/unit/application/core/test_checkpoint_manager.py` — Test loading_strategy validation
- `tests/architecture/test_force_full_scan_publication.py` — Verify publication configs

## Future Work

### Watermark Implementation (When Ready)

Prerequisites:
1. Confirm API provides reliable `updated_at` or version field
2. Verify field is monotonically increasing
3. Ensure API supports filtering by watermark

Steps:
1. Implement `LocalWatermarkStorage` adapter
2. Add `watermark_field` to pipeline config
3. Update fetchers to use watermark filtering
4. Add integration tests with VCR

### Strategy Migration

Once watermark is implemented:
1. Activity pipelines: Switch to `watermark_based`
2. Publication pipelines: Keep `full_scan_only`
3. Deprecate `force_full_scan` field

## References

- RULES.md §3 — Medallion Architecture
- ADR-030 — Publication Pagination Strategy
- ADR-011 — Remove Watermark Mechanism
- ChEMBL API Documentation — Offset pagination behavior
