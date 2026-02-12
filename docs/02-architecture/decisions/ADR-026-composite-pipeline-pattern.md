# ADR-026: Composite Pipeline Pattern

**Status:** Accepted
**Date:** 2026-01-15
**Decision makers:** @BioETL-Team

## Context

BioETL uses Hexagonal Architecture + Medallion (Bronze→Silver→Gold) for ETL biоактивных данных. Current pipelines operate independently:
- `chembl_activity`
- `chembl_publication`
- `pubchem_compound`

A common use case requires combining data from multiple sources:
1. **Seed Pipeline** extracts primary entities (e.g., publications from ChEMBL)
2. **Enrichment Pipelines** fetch additional data from other sources (CrossRef, OpenAlex, PubMed, SemanticScholar)
3. **Merge Step** combines all enrichments into a unified Gold entity

### Problem Statement

1. **Manual orchestration** - Users currently must run pipelines sequentially and manually join results
2. **No lineage tracking** - No way to trace which source contributed which fields
3. **Error handling complexity** - Partial enrichment failures require manual recovery
4. **Duplicated configuration** - Join keys and merge logic must be specified repeatedly

### Constraints

| Constraint | Source | Impact |
|------------|--------|--------|
| Local-Only Deployment | ADR-010 | No distributed orchestration (Airflow, Prefect) |
| MemoryLock | ADR-003 | Single-process execution only |
| Medallion Architecture | ADR-002 | Must preserve Bronze/Silver/Gold semantics |
| Content Hash Deduplication | RULES.md §3.1 | Silver merge must use content_hash |
| DQ Thresholds | RULES.md §4.1 | Soft >5%, Hard >20% apply per-enricher |

## Decision

Implement **Composite Pipeline Pattern** with the following architecture:

### 1. Orchestration Model: Hybrid (Sequential + Fan-Out)

```
                    ┌─────────────────┐
                    │   Seed Pipeline │
                    │  (chembl_pub)   │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │   Extract Keys  │
                    │   (doi, pmid)   │
                    └────────┬────────┘
                             │
           ┌─────────────────┼─────────────────┐
           │                 │                 │
    ┌──────▼──────┐   ┌──────▼──────┐   ┌──────▼──────┐
    │  CrossRef   │   │  OpenAlex   │   │   PubMed    │
    │  (required) │   │  (optional) │   │  (optional) │
    └──────┬──────┘   └──────┬──────┘   └──────┬──────┘
           │                 │                 │
           └─────────────────┼─────────────────┘
                             │
                    ┌────────▼────────┐
                    │   Merge Step    │
                    │ (Left Outer +   │
                    │  conflict res)  │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │   Gold Output   │
                    │ (unified entity)│
                    └─────────────────┘
```

**Rationale:**
- **Sequential seed-first**: Seed must complete before enrichers can query
- **Fan-out enrichers**: Independent API calls can run in parallel (async)
- **Sequential merge**: Must wait for all enrichers to complete

### 2. Data Passing Mechanism: File-Based (Silver Tables)

| Option | Pros | Cons | Decision |
|--------|------|------|----------|
| In-Memory | Fast, no I/O | Memory limits, no resume | ❌ |
| File-Based | Durable, resumable, auditable | Slower, disk I/O | ✅ |
| Hybrid | Best of both | Complexity | Future enhancement |

**Implementation:**
```
1. Seed writes → Silver/chembl/publication/
2. Extract keys → In-memory DataFrame (small)
3. Enrichers write → Silver/{enricher}/publication/
4. Merger reads all → Gold/composite_publication/
```

### 3. Join Strategy: Configurable per Enricher

| Enricher Type | Join | Behavior on Not Found |
|---------------|------|----------------------|
| Required | INNER | Composite fails |
| Optional | LEFT | Null fields, continue |

**Default**: LEFT JOIN (optional enrichers)

### 4. Failure Handling

| Scenario | Behavior | Recovery |
|----------|----------|----------|
| Seed fails | Composite fails (Critical) | Re-run composite |
| Required enricher fails | Composite fails | Re-run composite |
| Optional enricher fails | Log warning, continue | Re-run with `--enrich-only <name>` |
| Enricher >20% DQ failures | Depends on `required` flag | Review DQ report |
| Network timeout | Retry with backoff (3x) | Automatic |
| Partial completion | Checkpoint saved | `--resume` flag |

### 4.1. Dependency Pipelines

**Status:** Added 2026-02-03

Dependencies are pipelines that run **after seed but before enrichers**. Unlike enrichers
which read from pre-populated Silver tables, dependencies execute full API→Bronze→Silver
pipelines to populate Silver tables.

#### Execution Order

```
1. Seed Pipeline      → Populates Silver/seed
2. Dependencies       → Populates Silver/dependency (sequential)
3. Enrichers          → Read from Silver, enrich seed data (parallel)
4. Merge              → Combine all sources
```

#### Use Cases

| Use Case | Example |
|----------|---------|
| Reference tables | `protein_class` hierarchy (~1.5K records) |
| Derived entities | `publication_term` (MeSH terms from /document API) |
| Chained data | `protein_class` using IDs from `target_component` |

#### Chained Dependencies (key_source)

**Problem:** Some dependencies need keys from *another dependency's* output, not from seed.

**Example:** `chembl_protein_class` needs `protein_classification_id` values, but these
come from `chembl_target_component` Silver table, not from seed.

**Solution:** `key_source` field specifies where to read join keys from.

```yaml
dependencies:
  # Standard dependency: uses keys from seed
  - pipeline: chembl_target_component
    join_keys: [component_id]      # Column in seed
    silver_table: silver/chembl/target_component

  # Chained dependency: uses keys from another dependency
  - pipeline: chembl_protein_class
    join_keys: [protein_classification_id]  # Column in key_source table
    filter_field: protein_class_id          # API filter field name
    key_source: chembl_target_component     # Read keys from this Silver table
    silver_table: silver/chembl/protein_class
```

#### Configuration Fields

| Field | Type | Description |
|-------|------|-------------|
| `pipeline` | string | Dependency pipeline name |
| `join_keys` | list[string] | Column names to extract from key source |
| `key_source` | string? | Source of keys: `null`/`"seed"` = seed, or pipeline name |
| `filter_field` | string? | API filter field (if differs from join_key) |
| `required` | bool | If true, failure stops composite |
| `timeout_seconds` | int | Per-dependency timeout |
| `silver_table` | string? | Path to Silver table |

#### Implementation

- **DependencyCoordinator**: Reads keys from correct source (seed or chained)
- **`DependencyConfig.uses_seed_keys`**: Property to check key source
- **Sequential execution**: Dependencies run in order (chaining requires this)

#### Example: Target Composite Pipeline

```
Seed: chembl_target
  └─ Provides: target_chembl_id, component_id

Dependencies:
  1. chembl_target_component (component_id from seed)
     └─ Populates: Silver with protein_classification_id
  2. chembl_protein_class (protein_classification_id from #1)
     └─ Populates: Silver with protein class hierarchy

Enrichers:
  - uniprot_idmapping (target_chembl_id from seed)
```

### 5. Locking Strategy: Hierarchical Locks

```
lock:composite_publication              # Parent lock (exclusive)
├── lock:chembl_publication             # Seed lock (shared under parent)
├── lock:crossref_publication           # Enricher lock (shared)
├── lock:openalex_publication           # Enricher lock (shared)
└── lock:pubmed_publication             # Enricher lock (shared)
```

**Rationale:**
- Parent lock prevents concurrent composite runs
- Child locks allow inspection of individual pipelines
- No deadlock risk (single-threaded execution)

### 6. Lineage Metadata

Every Gold record includes:
```python
{
    "_composite_run_id": "uuid-of-composite-run",
    "_source_providers": ["chembl", "crossref", "openalex", "pubmed"],
    "_enrichment_status": {
        "crossref": "success",
        "openalex": "success",
        "pubmed": "not_found",
        "semanticscholar": "skipped"  # filter condition not met
    },
    "_enrichment_timestamps": {
        "chembl": "2026-01-15T10:00:00Z",
        "crossref": "2026-01-15T10:05:00Z",
        ...
    },
    "_field_sources": {
        "title": "chembl",
        "citations_count": "crossref",
        "mesh_terms": "pubmed",
        ...
    }
}
```

## Architecture

### Layer Distribution

```
src/bioetl/
├── domain/
│   ├── composite/
│   │   ├── __init__.py
│   │   ├── config.py           # CompositeConfig, EnricherConfig
│   │   ├── result.py           # EnrichmentResult, MergeResult
│   │   ├── state.py            # CompositePipelineState FSM enum
│   │   ├── strategy.py         # MergeStrategy enum
│   │   └── lineage.py          # LineageMetadata value object
│   └── ports/
│       └── composite.py        # CompositeOrchestratorPort (if needed)
│
├── application/
│   ├── composite/
│   │   ├── __init__.py
│   │   ├── runner.py           # CompositePipelineRunner
│   │   ├── coordinator.py      # EnrichmentCoordinator (fan-out logic)
│   │   ├── merger.py           # MergeService (join + conflict resolution)
│   │   ├── key_extractor.py    # KeyExtractorService
│   │   └── checkpoint.py       # CompositeCheckpointManager
│   └── core/
│       └── runner.py           # Existing PipelineRunner (unchanged)
│
├── composition/
│   ├── composite/
│   │   ├── __init__.py
│   │   ├── bootstrap.py        # bootstrap_composite_pipeline()
│   │   └── factory.py          # CompositePipelineFactory
│   └── factories/              # Existing factories (unchanged)
│
├── infrastructure/
│   └── storage/
│       └── silver_reader.py    # SilverReader adapter for key extraction
│
└── interfaces/
    └── cli.py                  # Extended with composite commands
```

### Import Rules

| From | To | Allowed |
|------|------|---------|
| domain/composite | domain/* | ✅ |
| application/composite | domain/*, application/core | ✅ |
| composition/composite | all layers | ✅ |
| application/composite | infrastructure | ❌ (via ports only) |

### Finite State Machine (FSM) Pattern

The composite pipeline uses a Finite State Machine to manage execution lifecycle.
This ensures predictable execution flow and prevents invalid operations.

#### State Diagram

```
┌─────────────────┐
│   NOT_STARTED   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  SEED_RUNNING   │──────────┐
└────────┬────────┘          │
         │                   │
         ▼                   │
┌─────────────────┐          │
│ SEED_COMPLETED  │          │
└────────┬────────┘          │
         │                   │
         ▼                   │
┌─────────────────┐          │
│   ENRICHING     │──────────┤
└────────┬────────┘          │
         │                   │
         ▼                   │
┌─────────────────┐          │
│ENRICHMENT_COMPL.│          │
└────────┬────────┘          │
         │                   │
         ▼                   │
┌─────────────────┐          │
│    MERGING      │──────────┤
└────────┬────────┘          │
         │                   ▼
         ▼            ┌─────────────┐
┌─────────────────┐   │   FAILED    │
│   COMPLETED     │   │ (terminal)  │
│   (terminal)    │   └─────────────┘
└─────────────────┘
```

#### Layer Separation for FSM

| Component | Layer | Responsibility |
|-----------|-------|----------------|
| `CompositePipelineState` (Enum) | **domain** | Defines states, transition rules, validation |
| `can_transition()`, `validate_transition()` | **domain** | Pure functions for transition logic |
| `CompositeCheckpointState.state` field | **application** | Persists FSM state for resume |
| `CompositePipelineRunner` | **application** | Executes transitions, manages lifecycle |
| `EnrichmentCoordinator` | **application** | No FSM knowledge (delegated service) |
| `MergeService` | **application** | No FSM knowledge (delegated service) |

**Key Principle:** Domain layer defines *what transitions are valid*, Application layer
executes *when transitions happen*. This separation allows:

1. **Testability**: FSM rules can be unit-tested in isolation
2. **Predictability**: Invalid transitions raise `InvalidStateError` immediately
3. **Observability**: Every transition is logged with from/to states
4. **Resumability**: `is_resumable` property enables checkpoint-based recovery

#### FSM in Domain Layer (`domain/composite/state.py`)

```python
class CompositePipelineState(str, Enum):
    NOT_STARTED = "not_started"
    SEED_RUNNING = "seed_running"
    SEED_COMPLETED = "seed_completed"
    ENRICHING = "enriching"
    ENRICHMENT_COMPLETED = "enrichment_completed"
    MERGING = "merging"
    COMPLETED = "completed"  # Terminal
    FAILED = "failed"        # Terminal

    def can_transition_to(self, target: CompositePipelineState) -> bool:
        """Domain logic: check if transition is valid."""
        return target in self.allowed_transitions

    def validate_transition(self, target: CompositePipelineState) -> None:
        """Raises InvalidStateError if transition is invalid."""
        ...
```

#### FSM in Application Layer (`application/composite/runner.py`)

```python
class CompositePipelineRunner:
    async def run(self) -> CompositeResult:
        # Application decides WHEN to transition
        state = state.with_state(CompositePipelineState.SEED_RUNNING)
        self._log_fsm_transition(from_state, to_state, stage="seed_start")

        # ... execute seed ...

        state = state.with_state(CompositePipelineState.SEED_COMPLETED)
        # ... etc.
```

## Domain Models

### CompositeConfig

```python
@dataclass(frozen=True, slots=True)
class DependencyConfig:
    """Configuration for a dependency pipeline.

    Dependencies run after seed but before enrichers to populate Silver tables.
    Supports chained dependencies via key_source field.
    """
    pipeline: str                    # Pipeline name (e.g., "chembl_protein_class")
    join_keys: tuple[str, ...]       # Keys to extract for filtering
    required: bool = False           # If True, failure = composite failure
    timeout_seconds: int = 600       # Per-dependency timeout
    silver_table: str | None = None  # Path to Silver table
    key_source: str | None = None    # None/"seed" = seed keys, or pipeline name
    filter_field: str | None = None  # API filter field (if differs from join_key)

    @property
    def uses_seed_keys(self) -> bool:
        """Check if dependency uses keys from seed."""
        return self.key_source is None or self.key_source == "seed"


@dataclass(frozen=True, slots=True)
class EnricherConfig:
    """Configuration for a single enrichment pipeline."""
    pipeline: str                    # Pipeline name (e.g., "crossref_publication")
    join_keys: tuple[str, ...]       # Keys to join on (e.g., ("doi", "pmid"))
    required: bool = False           # If True, failure = composite failure
    filter_condition: str | None = None  # SQL-like filter (e.g., "pmid IS NOT NULL")
    timeout_seconds: int = 600       # Per-enricher timeout
    fallback_strategy: Literal["skip", "use_cached", "fail"] = "skip"


@dataclass(frozen=True, slots=True)
class MergeConfig:
    """Configuration for merge step."""
    strategy: MergeStrategy          # left_outer, inner, union
    conflict_resolution: ConflictResolution  # seed_priority, latest, explicit
    output_silver_path: str
    output_gold_path: str
    field_mappings: dict[str, str] | None = None  # Rename fields during merge


@dataclass(frozen=True, slots=True)
class CompositeConfig:
    """Complete composite pipeline configuration."""
    name: str                        # e.g., "composite_publication"
    seed: SeedConfig                 # Seed pipeline config
    enrichers: tuple[EnricherConfig, ...]
    merge: MergeConfig
    dq: DQConfig                     # Composite-level DQ thresholds

    def __post_init__(self) -> None:
        self._validate_join_keys()
        self._validate_required_enrichers()
```

### EnrichmentResult

```python
@dataclass(frozen=True, slots=True)
class EnrichmentResult:
    """Result of a single enrichment pipeline execution."""
    enricher_name: str
    status: EnrichmentStatus  # success, partial, failed, skipped
    records_enriched: int
    records_not_found: int
    records_errored: int
    dq_error_rate: float
    duration_seconds: float
    error_message: str | None = None

    @property
    def is_success(self) -> bool:
        return self.status in (EnrichmentStatus.SUCCESS, EnrichmentStatus.PARTIAL)


class EnrichmentStatus(str, Enum):
    SUCCESS = "success"       # All records enriched
    PARTIAL = "partial"       # Some records enriched (below hard threshold)
    FAILED = "failed"         # Above hard threshold or critical error
    SKIPPED = "skipped"       # Filter condition excluded all records
    NOT_RUN = "not_run"       # Pipeline not executed (e.g., resume scenario)
```

### MergeStrategy

```python
class MergeStrategy(str, Enum):
    """Strategy for merging enriched data."""
    LEFT_OUTER = "left_outer"  # All seed records, nullable enrichments
    INNER = "inner"            # Only records found in ALL required enrichers
    UNION = "union"            # All records from any source (with dedup)


class ConflictResolution(str, Enum):
    """Strategy for resolving field conflicts between sources."""
    SEED_PRIORITY = "seed_priority"    # Seed value wins
    ENRICHER_PRIORITY = "enricher"     # Enricher value wins
    LATEST_TIMESTAMP = "latest"        # Most recent value wins
    EXPLICIT_RULES = "explicit"        # Use field_priorities mapping
    COALESCE = "coalesce"              # First non-null value
```

## Column Naming Convention

### Status: Accepted (Updated 2025-01-25)

### Context

При объединении данных из разных источников возникают конфликты имён колонок.
Предыдущая реализация переименовывала только enricher колонки с разными
стратегиями prefix (provider/entity/both), что приводило к:

1. Неконсистентности: seed колонки без prefix, enricher — с prefix
2. Сложной логике определения стратегии
3. Трудностям при coalesce из-за разных форматов

### Decision

**Все** бизнес-колонки (seed и enricher) переименовываются в единый формат:
```
{provider}.{entity}.{field}
```

**Примеры**:
| Source | Original | Qualified |
|--------|----------|-----------|
| chembl_publication (seed) | title | chembl.publication.title |
| crossref_publication (enricher) | title | crossref.publication.title |
| crossref_publication (enricher) | citation_count | crossref.publication.citation_count |

**Исключения** (НЕ переименовываются):
1. **Join keys**: `doi`, `pmid`, `pmc_id` — для совместимости с join операциями
2. **System columns**: колонки с prefix `_` (`_run_id`, `_ingestion_ts`, etc.)
3. **Entity ID columns**: `entity_id`, `content_hash` — системные идентификаторы

### Column Ordering

Колонки в output упорядочены по семантическим группам:

| Order | Group | Examples |
|-------|-------|----------|
| 1 | System | entity_id, content_hash, _run_id, _ingestion_ts |
| 2 | Identifiers | doi, pmid, pmc_id, document_chembl_id |
| 3 | Title | title, chembl.publication.title, crossref.publication.title |
| 4 | Abstract | abstract, chembl.publication.abstract |
| 5 | Authors | authors, first_author, affiliations |
| 6 | Journal | journal, publisher, volume, issue |
| 7 | Dates | publication_date, year, created_at |
| 8 | Metrics | citation_count, reference_count |
| 9 | Classification | mesh_terms, keywords, subjects |
| 10 | URLs | url, pdf_url, landing_page |
| 11 | Other | All remaining fields |

Внутри каждой группы колонки упорядочены по:
1. Provider priority: chembl → crossref → pubmed → openalex
2. Alphabetically для одного провайдера

### Implementation

- `ColumnRenamer`: Переименование колонок в qualified format
- `ColumnOrderer`: Упорядочивание колонок по семантическим группам
- `ColumnQualifier`: Value object для qualified имён
- `ColumnOrderConfig`: Конфигурация семантических групп

### Consequences

**Positive**:
- Единообразный формат всех колонок
- Явная атрибуция источника данных
- Устранение конфликтов имён без сложной логики
- Консистентный порядок колонок в output
- Улучшенная читаемость для downstream consumers

**Negative**:
- **Breaking change** для downstream consumers
- Более длинные имена колонок (3 компонента вместо 1)
- Требуется миграция существующих Silver/Gold таблиц

### References

- ColumnRenamer: `src/bioetl/application/composite/column_renamer.py`
- ColumnOrderer: `src/bioetl/application/composite/column_orderer.py`
- ColumnQualifier: `src/bioetl/domain/value_objects/column_qualifier.py`
- ColumnOrderConfig: `src/bioetl/domain/value_objects/column_order.py`

## Preserve All Sources Feature

### Status: Accepted (Added 2026-01-28)

### Context

During merge, columns with the same semantic meaning from different providers (e.g., `title` from ChEMBL, CrossRef, OpenAlex) are typically **coalesced** into a single column using the configured conflict resolution strategy. This is the default behavior.

However, some use cases require access to **all** provider values for comparison, quality analysis, or ML feature engineering.

### Decision

Add `preserve_all_sources: bool = False` to `MergeConfig`. When enabled:

1. **Skip coalescing** - MergeService does not apply conflict resolution
2. **Keep all qualified columns** - All `{provider}.{entity}.{field}` columns are retained
3. **Full traceability** - Downstream consumers can see exactly what each provider returned

### Configuration

```yaml
# configs/pipelines/composite/publication.yaml
merge:
  strategy: left_outer
  conflict_resolution: seed_priority  # Used when preserve_all_sources=false
  preserve_all_sources: true          # NEW: Keep all provider columns
```

### Behavior Comparison

| Mode | Output Columns | Use Case |
|------|----------------|----------|
| `preserve_all_sources: false` (default) | `title` (single coalesced column) | Production views with "best" value |
| `preserve_all_sources: true` | `chembl.publication.title`, `crossref.publication.title`, etc. | Data quality analysis, ML features |

### Implementation

- **Domain**: `MergeConfig.preserve_all_sources: bool = False` in `domain/composite/config.py`
- **Application**: `MergeService._resolve_conflicts()` skips coalescing when flag is True
- **Schema**: Pydantic schema updated with `preserve_all_sources` field

### Example Output

```python
# preserve_all_sources: false (default)
df.columns = ['entity_id', 'title', 'abstract', 'citation_count', ...]

# preserve_all_sources: true
df.columns = [
    'entity_id',
    'chembl.publication.title',
    'crossref.publication.title',
    'openalex.publication.title',
    'pubmed.publication.title',
    'chembl.publication.abstract',
    ...
]
```

### Consequences

**Positive**:
- Full data visibility for QA and analysis
- No information loss during merge
- Enables cross-provider comparison

**Negative**:
- Wider tables (more columns)
- Downstream consumers must handle multiple columns per field
- Breaking change for consumers expecting coalesced columns

## Field Group Registry

When `preserve_all_sources: true` is enabled, the number of columns grows significantly (94 base fields × up to 5 providers). The **Field Group Registry** (`FieldGroupRegistry`) provides semantic grouping for these columns.

### Purpose

1. **Gold Filtering**: Automatically exclude TRASH-group fields (e.g., `content_hash`, `language`) from Gold output
2. **Column Ordering**: Sort output columns by semantic group (ID_AND_STATUS first, TRASH last) and provider priority
3. **Validation**: Identify unmapped columns for data quality checks

### Domain Models

```
FieldGroupId (enum)          — 8 semantic groups (alias for PublicationFieldGroup)
FieldMapping (frozen)        — base_name → provider_columns + group
FieldGroupDefinition (frozen)— group_id, display_name, include_in_gold, fields
FieldGroupRegistry           — central registry with lookup indices
```

### YAML Configuration

Field groups are defined in `configs/composite/field_groups/publication.yaml`:

```yaml
version: "1.0"
entity: publication
provider_order: [chembl, crossref, openalex, pubmed, semanticscholar]
groups:
  - id: id_and_status
    display_name: "ID & Status"
    include_in_gold: true
    fields:
      - base_name: doi
        columns:
          - chembl.publication.doi
          - crossref.publication.doi
          - openalex.publication.doi
  - id: trash
    display_name: "Trash"
    include_in_gold: false
    fields:
      - base_name: content_hash
        columns: [chembl.publication.content_hash, ...]
```

### Integration with MergeService

During `_write_merged_gold()`, `MergeService` uses the registry to filter out TRASH columns:

```python
if self._field_group_registry is not None:
    trash_cols = self._field_group_registry.get_trash_columns(df.columns)
    if trash_cols:
        df = df.drop(trash_cols)
```

### Graceful Degradation

If no YAML config exists for a composite pipeline, bootstrap continues without the registry. No filtering or ordering is applied — the pipeline works as before.

### Files

| Layer | File | Description |
|-------|------|-------------|
| Domain | `domain/composite/field_groups.py` | Models: FieldMapping, FieldGroupDefinition, FieldGroupRegistry |
| Infrastructure | `infrastructure/config/field_group_loader.py` | YAML → domain object loader |
| Config | `configs/composite/field_groups/publication.yaml` | 8 groups, 94 fields |
| Composition | `composition/bootstrap/runtime/composite.py` | Bootstrap integration |
| Application | `application/composite/merger.py` | Gold filtering integration |

## Application Layer

### CompositePipelineRunner

```python
class CompositePipelineRunner:
    """Orchestrates composite pipeline execution.

    Coordinates seed execution, parallel enrichment, and merge.
    Delegates to existing PipelineRunner for individual pipelines.
    """

    def __init__(
        self,
        config: CompositeConfig,
        runtime: CompositeRuntimeConfig,
        seed_runner_factory: Callable[[], PipelineRunner],  # skip_gold=True
        enricher_runner_factory: Callable[[str], PipelineRunner],  # skip_gold=True
        key_extractor: KeyExtractorService,
        coordinator: EnrichmentCoordinator,
        merger: MergeService,
        checkpoint_manager: CompositeCheckpointManager,
        logger: LoggerPort,
        lock_manager: CompositeLockManager,
    ) -> None:
        ...

    async def run(self) -> CompositeResult:
        """Execute full composite pipeline."""
        async with self._lock_manager:
            # 1. Load checkpoint (for resume)
            state = await self._checkpoint_manager.load()

            # 2. Run seed (if not completed)
            if not state.seed_completed:
                await self._run_seed()
                state = state.with_seed_completed()
                await self._checkpoint_manager.save(state)

            # 3. Extract keys from seed Silver
            keys_df = await self._key_extractor.extract(
                self._config.seed.output_keys
            )

            # 4. Run enrichers (fan-out)
            results = await self._coordinator.run_enrichers(
                keys=keys_df,
                enrichers=self._config.enrichers,
                completed=state.completed_enrichers,
            )

            # 5. Merge results
            merge_result = await self._merger.merge(
                seed_table=self._config.seed.silver_table,
                enricher_tables=[e.pipeline for e in self._config.enrichers],
                results=results,
            )

            # 6. Cleanup
            await self._checkpoint_manager.delete()

            return CompositeResult(
                seed_result=state.seed_result,
                enrichment_results=results,
                merge_result=merge_result,
            )
```

### EnrichmentCoordinator

```python
class EnrichmentCoordinator:
    """Coordinates parallel enrichment pipeline execution.

    Implements fan-out pattern with async gather.
    Handles timeouts, failures, and partial completion.
    """

    async def run_enrichers(
        self,
        keys: pl.DataFrame,
        enrichers: Sequence[EnricherConfig],
        completed: frozenset[str] = frozenset(),
    ) -> dict[str, EnrichmentResult]:
        """Run all enrichers in parallel.

        Args:
            keys: DataFrame with join keys from seed.
            enrichers: Enricher configurations.
            completed: Set of already-completed enrichers (for resume).

        Returns:
            Mapping of enricher name to result.
        """
        tasks = []
        for enricher in enrichers:
            if enricher.pipeline in completed:
                continue  # Skip completed (resume scenario)

            # Filter keys based on enricher condition
            filtered_keys = self._apply_filter(keys, enricher.filter_condition)
            if filtered_keys.is_empty():
                tasks.append(self._create_skipped_result(enricher))
                continue

            tasks.append(
                self._run_single_enricher(enricher, filtered_keys)
            )

        results = await asyncio.gather(*tasks, return_exceptions=True)
        return self._process_results(enrichers, results)

    async def _run_single_enricher(
        self,
        enricher: EnricherConfig,
        keys: pl.DataFrame,
    ) -> EnrichmentResult:
        """Run a single enricher with timeout and error handling."""
        try:
            async with asyncio.timeout(enricher.timeout_seconds):
                runner = self._runner_factory(enricher.pipeline)
                # Pass keys via input filter mechanism
                await runner.run()
                return self._build_success_result(enricher)
        except asyncio.TimeoutError:
            return EnrichmentResult(
                enricher_name=enricher.pipeline,
                status=EnrichmentStatus.FAILED,
                error_message=f"Timeout after {enricher.timeout_seconds}s",
                ...
            )
        except Exception as e:
            if enricher.required:
                raise  # Propagate for required enrichers
            return self._build_error_result(enricher, e)
```

### MergeService

```python
class MergeService:
    """Merges enriched data from multiple sources.

    Implements join strategies and conflict resolution.
    Preserves lineage metadata for traceability.
    """

    async def merge(
        self,
        seed_table: str,
        enricher_tables: Sequence[str],
        results: dict[str, EnrichmentResult],
    ) -> MergeResult:
        """Merge seed and enricher data into unified Gold table.

        Args:
            seed_table: Path to seed Silver table.
            enricher_tables: Paths to enricher Silver tables.
            results: Enrichment results for filtering.

        Returns:
            MergeResult with statistics and lineage.
        """
        # 1. Load seed data
        seed_df = await self._storage.read_silver(seed_table)

        # 2. Apply joins based on strategy
        merged_df = seed_df
        for enricher in enricher_tables:
            result = results.get(enricher)
            if not result or not result.is_success:
                continue

            enricher_df = await self._storage.read_silver(enricher)
            merged_df = self._apply_join(
                merged_df,
                enricher_df,
                join_keys=self._get_join_keys(enricher),
            )

        # 3. Resolve conflicts
        merged_df = self._resolve_conflicts(merged_df)

        # 4. Add lineage metadata
        merged_df = self._add_lineage(merged_df, results)

        # 5. Write to Gold
        await self._storage.write_gold(
            df=merged_df,
            path=self._config.merge.output_gold_path,
        )

        return MergeResult(
            records_merged=len(merged_df),
            sources_used=[...],
            lineage_summary={...},
        )

    def _resolve_conflicts(self, df: pl.DataFrame) -> pl.DataFrame:
        """Apply conflict resolution strategy."""
        match self._config.merge.conflict_resolution:
            case ConflictResolution.SEED_PRIORITY:
                return self._coalesce_prefer_first(df)
            case ConflictResolution.LATEST_TIMESTAMP:
                return self._pick_latest(df)
            case ConflictResolution.COALESCE:
                return self._coalesce_non_null(df)
            case ConflictResolution.EXPLICIT_RULES:
                return self._apply_explicit_rules(df)
```

## Configuration Schema

### YAML Configuration

```yaml
# configs/pipelines/composite/publication.yaml
schema_version: "2.0.0"

composite:
  name: composite_publication
  version: "1.0.0"

  # ---------------------------------------------------------------------------
  # Seed Pipeline Configuration
  # ---------------------------------------------------------------------------
  seed:
    pipeline: chembl_publication
    output_keys:
      - document_id      # ChEMBL document ID
      - doi              # Digital Object Identifier
      - pmid             # PubMed ID
    silver_table: silver/chembl/publication

  # ---------------------------------------------------------------------------
  # Enricher Pipelines
  # ---------------------------------------------------------------------------
  enrichers:
    # CrossRef: Required enricher for citation data
    - pipeline: crossref_publication
      join_keys:
        - doi            # Primary join key
      required: true     # Failure = composite failure
      timeout_seconds: 900

    # OpenAlex: Optional enricher for academic metadata
    - pipeline: openalex_publication
      join_keys:
        - doi            # Primary
        - pmid           # Fallback
      required: false
      filter_condition: "doi IS NOT NULL OR pmid IS NOT NULL"
      timeout_seconds: 600

    # PubMed: Optional enricher for medical metadata
    - pipeline: pubmed_publication
      join_keys:
        - pmid
      required: false
      filter_condition: "pmid IS NOT NULL"
      timeout_seconds: 600

    # Semantic Scholar: Optional enricher for AI/ML features
    - pipeline: semanticscholar_publication
      join_keys:
        - doi
        - pmid
      required: false
      filter_condition: "doi IS NOT NULL OR pmid IS NOT NULL"
      timeout_seconds: 1200
      fallback_strategy: skip  # High rate limits, ok to skip

  # ---------------------------------------------------------------------------
  # Merge Configuration
  # ---------------------------------------------------------------------------
  merge:
    strategy: left_outer         # All seed records preserved
    conflict_resolution: seed_priority

    # Field-level priority overrides (for explicit_rules strategy)
    field_priorities:
      title: [chembl, crossref, openalex]
      abstract: [pubmed, openalex, chembl]
      citations_count: [crossref, openalex]
      mesh_terms: [pubmed]
      concepts: [openalex]

    output:
      silver: silver/composite/publication
      gold: gold/publication_enriched

  # ---------------------------------------------------------------------------
  # Data Quality Configuration
  # ---------------------------------------------------------------------------
  dq_rules:
    # Composite-level thresholds (applied to merge result)
    soft_fail_threshold: 0.10
    hard_fail_threshold: 0.30

    # Per-enricher overrides
    enricher_overrides:
      semanticscholar_publication:
        soft_fail_threshold: 0.20  # Higher tolerance for S2
        hard_fail_threshold: 0.50

    # Required fields in final Gold output
    required_fields:
      - document_id
      - title

  # ---------------------------------------------------------------------------
  # Execution Options
  # ---------------------------------------------------------------------------
  execution:
    # Maximum concurrent enrichers
    max_concurrency: 4

    # Enable checkpointing for resume
    checkpoint_enabled: true

    # Retry configuration for enrichers
    retry:
      max_attempts: 3
      backoff_multiplier: 2.0

  # ---------------------------------------------------------------------------
  # Lineage Configuration
  # ---------------------------------------------------------------------------
  lineage:
    # Track field-level provenance
    track_field_sources: true

    # Include enrichment timestamps
    track_timestamps: true

    # Include enrichment status per record
    track_status: true
```

## Test Strategy

### Unit Tests

```python
# tests/unit/application/composite/test_merger.py

class TestMergeService:
    """Test cases for MergeService."""

    def test_left_outer_join_preserves_all_seed_records(self):
        """LEFT OUTER join should keep all seed records."""
        seed = pl.DataFrame({"doi": ["10.1/a", "10.1/b", "10.1/c"]})
        enricher = pl.DataFrame({"doi": ["10.1/a"], "citations": [100]})

        merged = merge_service.merge(seed, enricher, strategy=LEFT_OUTER)

        assert len(merged) == 3
        assert merged.filter(pl.col("doi") == "10.1/a")["citations"][0] == 100
        assert merged.filter(pl.col("doi") == "10.1/b")["citations"][0] is None

    def test_inner_join_filters_unmatched_records(self):
        """INNER join should only keep matched records."""
        ...

    def test_conflict_resolution_seed_priority(self):
        """Seed values should take precedence with seed_priority."""
        seed = pl.DataFrame({"doi": ["10.1/a"], "title": "Seed Title"})
        enricher = pl.DataFrame({"doi": ["10.1/a"], "title": "Enricher Title"})

        merged = merge_service.merge(
            seed, enricher,
            conflict_resolution=ConflictResolution.SEED_PRIORITY
        )

        assert merged["title"][0] == "Seed Title"

    def test_lineage_metadata_added_correctly(self):
        """Lineage metadata should track all sources."""
        ...


# tests/unit/application/composite/test_coordinator.py

class TestEnrichmentCoordinator:
    """Test cases for EnrichmentCoordinator."""

    async def test_parallel_execution_respects_timeout(self):
        """Enrichers should timeout independently."""
        ...

    async def test_required_enricher_failure_propagates(self):
        """Required enricher failure should raise exception."""
        coordinator = EnrichmentCoordinator(...)
        enricher = EnricherConfig(pipeline="crossref", required=True)

        with pytest.raises(CriticalError):
            await coordinator.run_enrichers(
                keys=test_keys,
                enrichers=[enricher],
            )

    async def test_optional_enricher_failure_continues(self):
        """Optional enricher failure should return error result."""
        ...

    async def test_filter_condition_applied_correctly(self):
        """Filter condition should exclude records before enrichment."""
        ...
```

### Integration Tests

```python
# tests/integration/composite/test_composite_publication.py

@pytest.mark.integration
class TestCompositePublicationPipeline:
    """Integration tests for composite_publication pipeline."""

    @pytest.mark.vcr
    async def test_full_composite_run(self, vcr_cassette):
        """Full composite run with all enrichers."""
        runner = await bootstrap_composite_pipeline(
            "composite_publication",
            limit=10,
        )

        result = await runner.run()

        assert result.seed_result.records_processed > 0
        assert "crossref" in result.enrichment_results
        assert result.merge_result.records_merged > 0

    @pytest.mark.vcr
    async def test_resume_after_enricher_failure(self, vcr_cassette):
        """Resume should skip completed enrichers."""
        # First run with simulated failure
        runner = await bootstrap_composite_pipeline(
            "composite_publication",
            limit=10,
        )
        # Simulate failure after seed
        ...

        # Resume run
        runner = await bootstrap_composite_pipeline(
            "composite_publication",
            resume=True,
        )
        result = await runner.run()

        # Seed should be skipped
        assert result.seed_result.status == "resumed"


# tests/integration/composite/test_enricher_failures.py

@pytest.mark.integration
class TestEnricherFailureScenarios:
    """Test various enricher failure scenarios."""

    @pytest.mark.vcr
    async def test_optional_enricher_timeout(self):
        """Optional enricher timeout should not fail composite."""
        ...

    @pytest.mark.vcr
    async def test_required_enricher_dq_failure(self):
        """Required enricher >20% DQ errors should fail composite."""
        ...
```

### Architecture Tests

```python
# tests/architecture/test_composite_imports.py

def test_composite_domain_has_no_infrastructure_imports():
    """domain/composite should not import from infrastructure."""
    for file in glob.glob("src/bioetl/domain/composite/**/*.py"):
        with open(file) as f:
            content = f.read()
        assert "from bioetl.infrastructure" not in content
        assert "import bioetl.infrastructure" not in content


def test_composite_application_has_no_infrastructure_imports():
    """application/composite should not import from infrastructure."""
    ...


def test_composite_port_contracts():
    """Composite ports should follow standard conventions."""
    ...
```

## CLI Interface

### Commands

```bash
# Full composite run
bioetl run --pipeline composite_publication

# With options
bioetl run --pipeline composite_publication \
    --limit 1000 \
    --dry-run

# Re-enrich specific source only
bioetl run --pipeline composite_publication \
    --enrich-only pubmed,openalex

# Skip optional enrichers (fast mode)
bioetl run --pipeline composite_publication \
    --required-only

# Resume after failure
bioetl run --pipeline composite_publication \
    --resume

# Force re-run of specific enricher
bioetl run --pipeline composite_publication \
    --force-enricher crossref

# List composite pipeline status
bioetl status composite_publication
```

### CLI Implementation

```python
# src/bioetl/interfaces/cli.py (extensions)

@cli.command()
@click.option("--enrich-only", help="Run only specified enrichers (comma-separated)")
@click.option("--required-only", is_flag=True, help="Skip optional enrichers")
@click.option("--force-enricher", help="Force re-run of specified enricher")
def run(pipeline: str, enrich_only: str | None, required_only: bool, ...):
    """Run a pipeline (regular or composite)."""
    if pipeline.startswith("composite_"):
        return run_composite(pipeline, enrich_only, required_only, ...)
    else:
        return run_regular(pipeline, ...)
```

## Consequences

### Positive

1. **Unified data enrichment** - Single command to run multi-source pipelines
2. **Graceful degradation** - Optional enricher failures don't block composite
3. **Full lineage** - Every field traceable to source
4. **Resume capability** - Checkpoint-based recovery from failures
5. **Configurable flexibility** - YAML-based orchestration without code changes
6. **No redundant Gold writes** - Sub-pipelines run with `skip_gold=True`,
   writing only Bronze+Silver; the composite merge phase produces the unified Gold output

### Negative

1. **Increased complexity** - New components (Coordinator, Merger, etc.)
2. **Configuration learning curve** - YAML schema is more complex
3. **Debugging difficulty** - Multi-source issues harder to trace
4. **Storage overhead** - Intermediate Silver tables for each enricher

### Risks

| Risk | Mitigation |
|------|------------|
| Memory pressure from parallel enrichers | `max_concurrency` limit, adaptive sizing |
| Lock contention with many enrichers | Hierarchical lock strategy |
| Inconsistent data on partial failures | Checkpoint + resume mechanism |
| Configuration errors | Schema validation via Pydantic |

## Migration Path

### Phase 1: Foundation (v1.0)
- [ ] Domain models (CompositeConfig, EnrichmentResult, MergeStrategy)
- [ ] CompositePipelineRunner basic implementation
- [ ] EnrichmentCoordinator with sequential execution
- [ ] MergeService with LEFT OUTER join only
- [ ] CLI extensions for composite pipelines

### Phase 2: Parallelism (v1.1)
- [ ] Parallel enricher execution (asyncio.gather)
- [ ] Timeout handling per enricher
- [ ] CompositeCheckpointManager for resume

### Phase 3: Advanced Features (v1.2)
- [ ] All merge strategies (INNER, UNION)
- [ ] All conflict resolution strategies
- [ ] Field-level lineage tracking
- [ ] `--enrich-only` and `--required-only` CLI options

### Phase 4: Optimization (v1.3)
- [ ] Adaptive batch sizing for enrichers
- [ ] Caching of enrichment results
- [ ] Incremental composite runs (delta mode)

## Alternatives Considered

### 1. External Orchestrator (Prefect/Dagster)

**Pros:** Battle-tested, rich UI, distributed execution
**Cons:** Violates ADR-010 (Local-Only), operational overhead
**Decision:** Rejected - architectural constraint

### 2. DAG-Based Internal Orchestrator

**Pros:** Flexible dependencies, cycle detection
**Cons:** Over-engineered for linear seed→enrich→merge flow
**Decision:** Rejected - YAGNI for v1

### 3. Pipeline Composition via Code

**Pros:** Maximum flexibility
**Cons:** Requires code changes for new composites
**Decision:** Rejected - YAML configuration preferred

## References

- ADR-002: Medallion Architecture
- ADR-003: In-Memory Locking
- ADR-010: Local-Only Deployment
- ADR-015: Pipeline Services Lifecycle
- ADR-020: BasePipeline Decomposition
- RULES.md v5.17 §2.4 (Backfill/Replay)
- RULES.md v5.17 §3.3 (Concurrency & Locks)
