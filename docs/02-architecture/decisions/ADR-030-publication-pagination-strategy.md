______________________________________________________________________

Version: 1.0.0
Status: Accepted
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-30'

______________________________________________________________________

# ADR-030: Publication Pagination Strategy (force-full-scan)

**Date:** 2026-01-26
**Status:** Accepted
**Decision makers:** @BioETL-Team

## Context

Publication entities (documents, works, papers) from external APIs present unique challenges for incremental extraction:

### Problem Statement

1. **Offset instability**: Publication APIs (ChEMBL `/document`, CrossRef Works, PubMed) frequently update their datasets
1. **Offset-based resume fails**: When resuming from offset N after API data changes:
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

| Pipeline                        | Provider        | Entity Type            | Primary Key        |
| ------------------------------- | --------------- | ---------------------- | ------------------ |
| `chembl_publication`            | ChEMBL          | publication            | document-chembl-id |
| `chembl_publication_term`       | ChEMBL          | publication-term       | entity-id          |
| `chembl_publication_similarity` | ChEMBL          | publication-similarity | sim-id             |
| `pubmed_publication`            | PubMed          | publication            | pmid               |
| `crossref_publication`          | CrossRef        | work                   | doi                |
| `openalex_publication`          | OpenAlex        | publication            | openalex-id        |
| `semanticscholar_publication`   | SemanticScholar | publication            | paper-id           |

## Decision

Introduce `force-full-scan` flag for publication entities that:

1. **Disables checkpoint-based resume** for the pipeline
1. **Each run performs a full scan** of the data source
1. **Deduplication is handled on Silver layer** via `content-hash`

### Configuration

Add `force-full-scan: bool` to `PipelineConfig`:

```python
@dataclass(frozen=True, slots=True)
class PipelineConfig:
    # ... existing fields ...

    # Pagination strategy (ADR-030)
    force - full - scan: bool = False
```

### YAML Configuration

```yaml
# configs/entities/chembl/publication.yaml
pipeline-name: chembl_publication
provider: chembl
entity_type: publication

# Pagination strategy (ADR-030)
force-full-scan: true
```

### Runtime Behavior

When `force-full-scan=True` and `resume=True` is requested:

1. **Warning logged** with explanation
1. **Checkpoint loading is skipped**
1. **Full extraction proceeds** from offset 0

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
write_mode = SilverWriteMode.MERGE  # Upsert by primary key
```

Records with identical `content-hash` are deduplicated during merge.

## Consequences

### Positive

1. **Reproducible runs**: Each execution produces consistent results
1. **No data loss**: Full scan guarantees all current records are captured
1. **No duplicates in Silver**: Merge deduplication handles repeated records
1. **Simple mental model**: "Run = full dataset snapshot"
1. **Resilient to API changes**: No dependency on stable offsets

### Negative

1. **Longer run times**: Full scan vs incremental requires more API calls
1. **Higher API load**: May increase rate limiting on some providers
1. **Cannot resume mid-run**: Interruption requires restart from beginning

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

- `src/bioetl/application/core/lifecycle/checkpoint_manager.py` — Block resume when `force-full-scan=True`

**Infrastructure:**

- `src/bioetl/infrastructure/schemas/pipeline_config.py` — Add `force-full-scan` to YAML schema
- `src/bioetl/infrastructure/config/_base.py` — Pass `force-full-scan` in `yaml_config_to_domain`

**Composition:**

- `src/bioetl/composition/factories/services_factory.py` — Pass `force-full-scan` to `CheckpointManager`
- `src/bioetl/composition/factories/pipeline_factory.py` — Use `config.force-full-scan`

**Configs:**

- `configs/entities/chembl/publication.yaml` — `force-full-scan: true`
- `configs/entities/chembl/publication_term.yaml` — `force-full-scan: true`
- `configs/entities/chembl/publication_similarity.yaml` — `force-full-scan: true`
- `configs/entities/pubmed/publication.yaml` — `force-full-scan: true`
- `configs/entities/crossref/publication.yaml` — `force-full-scan: true`
- `configs/entities/openalex/publication.yaml` — `force-full-scan: true`
- `configs/entities/semanticscholar/publication.yaml` — `force-full-scan: true`

### Tests

- `tests/unit/application/core/test_checkpoint_manager.py` — Test `force-full-scan` behavior
- `tests/architecture/test_force_full_scan_publication.py` — Verify publication configs have flag set

## References

- RULES.md §3 — Medallion Architecture (Silver deduplication via content-hash)
- ADR-011 — Remove Watermark Mechanism (rationale for abandoning offset tracking)
- ADR-009 — Paginated Fetcher Mixin (pagination abstraction)
- ChEMBL API Documentation — `/document` endpoint pagination

## Compliance

| Control      | Requirement                                                                | Status | Evidence                                     |
| ------------ | -------------------------------------------------------------------------- | ------ | -------------------------------------------- |
| Format       | ADR MUST use standard metadata and normalized section headings             | `pass` | `ADR-030-publication-pagination-strategy.md` |
| Status       | ADR status MUST be explicit and consistent                                 | `pass` | `Accepted`                                   |
| Supersession | Superseded or superseding ADRs SHOULD be linked explicitly when applicable | `n/a`  | `metadata block`                             |
| Verification | Implementation and validation expectations MUST be documented              | `pass` | `Verification / Acceptance Criteria`         |
| References   | Related ADRs, docs, or artifacts SHOULD be linked                          | `pass` | `References`                                 |

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
