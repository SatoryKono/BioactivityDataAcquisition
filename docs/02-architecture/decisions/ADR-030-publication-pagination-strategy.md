# ADR-030: Publication Pagination Strategy (force-full-scan)

**Status:** Accepted
**Date:** 2026-01-26
**Decision makers:** @BioETL-Team
**Relates to:** ADR-011 (Remove Watermark), ADR-009 (Paginated Fetcher Mixin)

## Context

Publication entities (documents, works, papers) from external APIs present unique challenges for incremental extraction:

### Problem Statement

1. **Offset instability**: Publication APIs (ChEMBL `/document`, CrossRef Works, PubMed) frequently update their datasets
2. **Offset-based resume fails**: When resuming from offset N after API data changes:
   - Records may shift positions, causing **duplicates** (same record fetched twice)
   - Records may be skipped entirely, causing **data loss**
   - Results are **non-reproducible** across runs

### Current Behavior (Before ADR-030)

```
Run 1: Fetch records 0-1000, checkpoint offset=1000
[API data changes]
Run 2 (resume): Fetch records 1000-2000
  - Records 900-1000 may have shifted to 1001-1100 → MISSED
  - Records 1001-1050 may have shifted to 950-1000 → DUPLICATED
```

### Affected Pipelines

| Pipeline | Provider | Entity Type | Primary Key |
|----------|----------|-------------|-------------|
| `chembl-publication` | ChEMBL | publication | document-chembl-id |
| `chembl-publication-term` | ChEMBL | publication-term | entity-id |
| `chembl-publication-similarity` | ChEMBL | publication-similarity | sim-id |
| `pubmed-publication` | PubMed | publication | pmid |
| `crossref-publication` | CrossRef | work | doi |
| `openalex-publication` | OpenAlex | publication | openalex-id |
| `semanticscholar-publication` | SemanticScholar | publication | paper-id |

## Decision

Introduce `force-full-scan` flag for publication entities that:

1. **Disables checkpoint-based resume** for the pipeline
2. **Each run performs a full scan** of the data source
3. **Deduplication is handled on Silver layer** via `content-hash`

### Configuration

Add `force-full-scan: bool` to `PipelineConfig`:

```python
@dataclass(frozen=True, slots=True)
class PipelineConfig:
    # ... existing fields ...

    # Pagination strategy (ADR-030)
    force-full-scan: bool = False
```

### YAML Configuration

```yaml
# configs/entities/chembl/publication.yaml
pipeline-name: chembl-publication
provider: chembl
entity-type: publication

# Pagination strategy (ADR-030)
force-full-scan: true
```

### Runtime Behavior

When `force-full-scan=True` and `resume=True` is requested:

1. **Warning logged** with explanation
2. **Checkpoint loading is skipped**
3. **Full extraction proceeds** from offset 0

```python
# CheckpointManager.load-checkpoint()
if self.-resume and self.-force-full-scan:
    self.-logger.warning(
        "Checkpoint resume blocked for force-full-scan pipeline. "
        "Each run performs a full scan; deduplication via content-hash on Silver. "
        "See ADR-030 for details.",
        extra={"pipeline": self.-pipeline-name, "force-full-scan": True},
    )
    return None
```

### Deduplication Strategy

Silver layer merge handles duplicates via:

```python
# Silver write uses MERGE with content-hash
write-mode = SilverWriteMode.MERGE  # Upsert by primary key
```

Records with identical `content-hash` are deduplicated during merge.

## Consequences

### Positive

1. **Reproducible runs**: Each execution produces consistent results
2. **No data loss**: Full scan guarantees all current records are captured
3. **No duplicates in Silver**: Merge deduplication handles repeated records
4. **Simple mental model**: "Run = full dataset snapshot"
5. **Resilient to API changes**: No dependency on stable offsets

### Negative

1. **Longer run times**: Full scan vs incremental requires more API calls
2. **Higher API load**: May increase rate limiting on some providers
3. **Cannot resume mid-run**: Interruption requires restart from beginning

### Mitigations

- **Batch processing**: Large datasets processed in batches with checkpoints for fault tolerance during single run
- **Rate limiting**: Built-in rate limiters prevent API overload
- **Content hash**: Deduplication makes repeated full scans idempotent

### Neutral

- Non-publication pipelines (activity, compound, target) are unaffected
- `force-full-scan=False` (default) preserves existing behavior

## Alternatives Considered

### Alternative 1: Cursor-based Pagination

**Rejected** because:
- Not all APIs support stable cursors (ChEMBL, PubMed use offset)
- Cursor state is opaque and cannot be validated after API changes

### Alternative 2: Timestamp-based Incremental

**Rejected** because:
- APIs don't provide reliable `updated-at` for all records
- Historical records may be modified without timestamp update

### Alternative 3: API-specific Sync Tokens

**Rejected** because:
- Would require per-provider implementation
- Most publication APIs don't support sync tokens

## Implementation

### Files Modified

**Domain:**
- `src/bioetl/domain/config.py` — Add `force-full-scan` field to `PipelineConfig`

**Application:**
- `src/bioetl/application/core/checkpoint-manager.py` — Block resume when `force-full-scan=True`

**Infrastructure:**
- `src/bioetl/infrastructure/schemas/pipeline-config.py` — Add `force-full-scan` to YAML schema
- `src/bioetl/infrastructure/config/-base.py` — Pass `force-full-scan` in `yaml-config-to-domain`

**Composition:**
- `src/bioetl/composition/factories/services-factory.py` — Pass `force-full-scan` to `CheckpointManager`
- `src/bioetl/composition/factories/pipeline-factory.py` — Use `config.force-full-scan`

**Configs:**
- `configs/entities/chembl/publication.yaml` — `force-full-scan: true`
- `configs/entities/chembl/publication-term.yaml` — `force-full-scan: true`
- `configs/entities/chembl/publication-similarity.yaml` — `force-full-scan: true`
- `configs/entities/pubmed/publication.yaml` — `force-full-scan: true`
- `configs/entities/crossref/publication.yaml` — `force-full-scan: true`
- `configs/entities/openalex/publication.yaml` — `force-full-scan: true`
- `configs/entities/semanticscholar/publication.yaml` — `force-full-scan: true`

### Tests

- `tests/unit/application/core/test-checkpoint-manager.py` — Test `force-full-scan` behavior
- `tests/architecture/test-force-full-scan-configs.py` — Verify publication configs have flag set

## References

- RULES.md §3 — Medallion Architecture (Silver deduplication via content-hash)
- ADR-011 — Remove Watermark Mechanism (rationale for abandoning offset tracking)
- ADR-009 — Paginated Fetcher Mixin (pagination abstraction)
- ChEMBL API Documentation — `/document` endpoint pagination
