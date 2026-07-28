______________________________________________________________________

Version: 1.0.0
Status: Accepted
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-04-24'

______________________________________________________________________

# ADR-026: Composite Pipeline Pattern

**Date:** 2026-01-15
**Status:** Accepted
**Decision makers:** @BioETL-Team

## Context

BioETL uses Hexagonal Architecture + Medallion (Bronze→Silver→Gold) for ETL biоактивных данных. Current pipelines operate independently:

- `chembl_activity`
- `chembl_publication`
- `pubchem_compound`

A common use case requires combining data from multiple sources:

1. **Seed Pipeline** extracts primary entities (e.g., publications from ChEMBL)
1. **Enrichment Pipelines** fetch additional data from other sources (CrossRef, OpenAlex, PubMed, SemanticScholar)
1. **Merge Step** combines all enrichments into a unified Gold entity

### Problem Statement

1. **Manual orchestration** - Users currently must run pipelines sequentially and manually join results
1. **No lineage tracking** - No way to trace which source contributed which fields
1. **Error handling complexity** - Partial enrichment failures require manual recovery
1. **Duplicated configuration** - Join keys and merge logic must be specified repeatedly

### Constraints

| Constraint                 | Source        | Impact                                          |
| -------------------------- | ------------- | ----------------------------------------------- |
| Local-Only Deployment      | ADR-010       | No distributed orchestration (Airflow, Prefect) |
| MemoryLock                 | ADR-003       | Single-process execution only                   |
| Medallion Architecture     | ADR-002       | Must preserve Bronze/Silver/Gold semantics      |
| Content Hash Deduplication | RULES.md §3.1 | Silver merge must use content-hash              |
| DQ Thresholds              | RULES.md §3.1.2 / §4.1 | Hierarchical defaults `0.05/0.50`; Silver request / pipeline-override baseline `0.05/0.20`; composite overrides in `configs/composites/*.yaml` (see [DQ configuration](../../03-guides/dq-configuration.md)) |

**Operationalization note (2026-07-28):** Composite DQ thresholds are not a single
global hard-fail rule. Hierarchical quality defaults in `configs/base/quality.yaml`
use `soft_fail: 0.05` and `hard_fail: 0.50` (RULES / `ThresholdsConfig`).
Contract-backed loader omitted thresholds also resolve to `hard_fail: 0.50`.
Silver request / pipeline-override baselines use `0.05/0.20`. Composite configs
may override per enricher or merge surface in `configs/composites/*.yaml`. See
[DQ configuration](../../03-guides/dq-configuration.md) for precedence.

## Decision

Implement **Composite Pipeline Pattern** with the following architecture:

**Operationalization note (2026-05-14):** canonical semantic field clusters
used by composite `join_keys` and merge surfaces are tracked in
`configs/field_registry/canonical_registry.json`. Composite configs must use
registry canonical names, not provider-prefixed historical aliases.

**Decision Boundary Change (2026-04-24)**:
The original ADR specified CrossRef as a required enricher (`required: true`). However, actual composite configurations show `required: false`. This change reflects the evolution of the composite pattern to prioritize resilience and graceful degradation over strict completeness requirements.

**Superseded Section**: The "CrossRef (required)" specification in the architecture diagram and configuration has been updated to "CrossRef (optional)" to match current implementation reality.

### 1. Orchestration Model: Hybrid (Sequential + Fan-Out)

```
                    ┌─────────────────┐
                    │   Seed Pipeline │
                    │  (chembl-pub)   │
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
    │  (optional) │   │  (optional) │   │  (optional) │
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

| Option     | Pros                          | Cons                     | Decision           |
| ---------- | ----------------------------- | ------------------------ | ------------------ |
| In-Memory  | Fast, no I/O                  | Memory limits, no resume | ❌                 |
| File-Based | Durable, resumable, auditable | Slower, disk I/O         | ✅                 |
| Hybrid     | Best of both                  | Complexity               | Future enhancement |

**Implementation:**

```
1. Seed writes → Silver/chembl/publication/
2. Extract keys → In-memory DataFrame (small)
3. Enrichers write → Silver/{enricher}/publication/
4. Merger reads all → Gold/composite_publication/
```

### 3. Join Strategy: Configurable per Enricher

| Enricher Type | Join  | Behavior on Not Found |
| ------------- | ----- | --------------------- |
| Required      | INNER | Composite fails       |
| Optional      | LEFT  | Null fields, continue |

**Default**: LEFT JOIN (optional enrichers)

**Note**: The original ADR specified CrossRef as a required enricher, but actual composite configurations show `required: false`. This reflects the evolution of the composite pattern to prioritize resilience over completeness.

### 4. Failure Handling

| Scenario                  | Behavior                   | Recovery                           |
| ------------------------- | -------------------------- | ---------------------------------- |
| Seed fails                | Composite fails (Critical) | Re-run composite                   |
| Required enricher fails   | Composite fails            | Re-run composite                   |
| Optional enricher fails   | Log warning, continue      | Re-run with `--enrich-only <name>` |
| Enricher DQ hard-fail breach | Depends on `required` flag and configured `hard_fail` threshold (hierarchical default `0.25`, contract/runtime fallback `0.20`, composite overrides allowed) | Review DQ report |
| Network timeout           | Retry with backoff (3x)    | Automatic                          |
| Partial completion        | Checkpoint saved           | `--resume` flag                    |

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

| Use Case         | Example                                            |
| ---------------- | -------------------------------------------------- |
| Reference tables | `protein-class` hierarchy (~1.5K records)          |
| Derived entities | `publication-term` (MeSH terms from /document API) |
| Chained data     | `protein-class` using IDs from `target-component`  |

#### Chained Dependencies (key-source)

**Problem:** Some dependencies need keys from *another dependency's* output, not from seed.

**Example:** `chembl_protein_class` needs `protein-classification-id` values, but these
come from `chembl_target_component` Silver table, not from seed.

**Solution:** `key-source` field specifies where to read join keys from.

```yaml
dependencies:
  # Standard dependency: uses keys from seed
  - pipeline: chembl_target_component
    join-keys: [component-id]      # Column in seed
    silver-table: silver/chembl/target-component

  # Chained dependency: uses keys from another dependency
  - pipeline: chembl_protein_class
    join-keys: [protein-classification-id]  # Column in key-source table
    filter-field: protein-class-id          # API filter field name
    key-source: chembl_target_component     # Read keys from this Silver table
    silver-table: silver/chembl/protein-class
```

#### Configuration Fields

| Field             | Type         | Description                                              |
| ----------------- | ------------ | -------------------------------------------------------- |
| `pipeline`        | string       | Dependency pipeline name                                 |
| `join-keys`       | list[string] | Column names to extract from key source                  |
| `key-source`      | string?      | Source of keys: `null`/`"seed"` = seed, or pipeline name |
| `filter-field`    | string?      | API filter field (if differs from join-key)              |
| `required`        | bool         | If true, failure stops composite                         |
| `timeout-seconds` | int          | Per-dependency timeout                                   |
| `silver-table`    | string?      | Path to Silver table                                     |

#### Implementation

- **DependencyCoordinator**: Reads keys from correct source (seed or chained)
- **`DependencyConfig.uses-seed-keys`**: Property to check key source
- **Sequential execution**: Dependencies run in order (chaining requires this)

#### Example: Target Composite Pipeline

```
Seed: chembl_target
  └─ Provides: target-chembl-id, component-id

Dependencies:
  1. chembl_target_component (component-id from seed)
     └─ Populates: Silver with protein-classification-id
  2. chembl_protein_class (protein-classification-id from #1)
     └─ Populates: Silver with protein class hierarchy

Enrichers:
  - uniprot_idmapping (target-chembl-id from seed)
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
    "-composite_run_id": "uuid-of-composite-run",
    "-source-providers": ["chembl", "crossref", "openalex", "pubmed"],
    "-enrichment-status": {
        "crossref": "success",
        "openalex": "success",
        "pubmed": "not-found",
        "semanticscholar": "skipped"  # filter condition not met
    },
    "-enrichment-timestamps": {
        "chembl": "2026-01-15T10:00:00Z",
        "crossref": "2026-01-15T10:05:00Z",
        ...
    },
    "-field-sources": {
        "title": "chembl",
        "citations-count": "crossref",
        "mesh-terms": "pubmed",
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
│   └── ports/                  # Existing shared ports package (no dedicated composite.py)
│
├── application/
│   ├── composite/
│   │   ├── __init__.py
│   │   ├── runner_pkg/         # Decomposed runner package (refactored)
│   │   │   └── runner.py       # CompositePipelineRunner
│   │   ├── coordinator.py      # EnrichmentCoordinator (fan-out logic)
│   │   ├── merger.py           # MergeService (join + conflict resolution)
│   │   ├── key_extractor.py    # KeyExtractorService
│   │   └── checkpoint/         # CompositeCheckpointService (package)
│   │       └── service.py
│   └── core/
│       └── runner.py           # Existing PipelineRunner (unchanged)
│
├── composition/
│   ├── bootstrap/
│   │   └── runtime/
│   │       └── composite.py    # bootstrap_composite_runner()
│   ├── composite_api.py        # Public composite composition API
│   └── factories/              # Existing factories (unchanged)
│
├── infrastructure/
│   └── storage/                # Existing storage adapters (Bronze/Silver/Gold writers)
│
└── interfaces/
    └── cli/main.py             # Extended with run-composite command family
```

### Import Rules

| From                  | To                          | Allowed             |
| --------------------- | --------------------------- | ------------------- |
| domain/composite      | domain/\*                   | ✅                  |
| application/composite | domain/\*, application/core | ✅                  |
| composition/composite | all layers                  | ✅                  |
| application/composite | infrastructure              | ❌ (via ports only) |

### Finite State Machine (FSM) Pattern

The composite pipeline uses a Finite State Machine to manage execution lifecycle.
This ensures predictable execution flow and prevents invalid operations.

#### State Diagram

```
┌─────────────────┐
│   NOT-STARTED   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  SEED-RUNNING   │──────────┐
└────────┬────────┘          │
         │                   │
         ▼                   │
┌─────────────────┐          │
│ SEED-COMPLETED  │          │
└────────┬────────┘          │
         │                   │
         ▼                   │
┌─────────────────┐          │
│   ENRICHING     │──────────┤
└────────┬────────┘          │
         │                   │
         ▼                   │
┌─────────────────┐          │
│ENRICHMENT-COMPL.│          │
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

| Component                                   | Layer           | Responsibility                               |
| ------------------------------------------- | --------------- | -------------------------------------------- |
| `CompositePipelineState` (Enum)             | **domain**      | Defines states, transition rules, validation |
| `can-transition()`, `validate-transition()` | **domain**      | Pure functions for transition logic          |
| `CompositeCheckpointState.state` field      | **application** | Persists FSM state for resume                |
| `CompositePipelineRunner`                   | **application** | Executes transitions, manages lifecycle      |
| `EnrichmentCoordinator`                     | **application** | No FSM knowledge (delegated service)         |
| `MergeService`                              | **application** | No FSM knowledge (delegated service)         |

**Key Principle:** Domain layer defines *what transitions are valid*, Application layer
executes *when transitions happen*. This separation allows:

1. **Testability**: FSM rules can be unit-tested in isolation
1. **Predictability**: Invalid transitions raise `InvalidStateError` immediately
1. **Observability**: Every transition is logged with from/to states
1. **Resumability**: `is-resumable` property enables checkpoint-based recovery

#### FSM in Domain Layer (`domain/composite/state.py`)

```python
class CompositePipelineState(str, Enum):
    NOT-STARTED = "not-started"
    SEED-RUNNING = "seed-running"
    SEED-COMPLETED = "seed-completed"
    ENRICHING = "enriching"
    ENRICHMENT-COMPLETED = "enrichment-completed"
    MERGING = "merging"
    COMPLETED = "completed"  # Terminal
    FAILED = "failed"        # Terminal

    def can-transition-to(self, target: CompositePipelineState) -> bool:
        """Domain logic: check if transition is valid."""
        return target in self.allowed-transitions

    def validate-transition(self, target: CompositePipelineState) -> None:
        """Raises InvalidStateError if transition is invalid."""
        ...
```

#### FSM in Application Layer (`application/composite/runner_pkg/runner.py`)

```python
class CompositePipelineRunner:
    async def run(self) -> CompositeResult:
        # Application decides WHEN to transition
        state = state.with-state(CompositePipelineState.SEED-RUNNING)
        self.-log-fsm-transition(from-state, to-state, stage="seed-start")

        # ... execute seed ...

        state = state.with-state(CompositePipelineState.SEED-COMPLETED)
        # ... etc.
```

## Domain Models

### CompositeConfig

```python
@dataclass(frozen=True, slots=True)
class DependencyConfig:
    """Configuration for a dependency pipeline.

    Dependencies run after seed but before enrichers to populate Silver tables.
    Supports chained dependencies via key-source field.
    """
    pipeline: str                    # Pipeline name (e.g., "chembl_protein_class")
    join-keys: tuple[str, ...]       # Keys to extract for filtering
    required: bool = False           # If True, failure = composite failure
    timeout-seconds: int = 600       # Per-dependency timeout
    silver-table: str | None = None  # Path to Silver table
    key-source: str | None = None    # None/"seed" = seed keys, or pipeline name
    filter-field: str | None = None  # API filter field (if differs from join-key)

    @property
    def uses-seed-keys(self) -> bool:
        """Check if dependency uses keys from seed."""
        return self.key-source is None or self.key-source == "seed"

@dataclass(frozen=True, slots=True)
class EnricherConfig:
    """Configuration for a single enrichment pipeline."""
    pipeline: str                    # Pipeline name (e.g., "crossref_publication")
    join-keys: tuple[str, ...]       # Keys to join on (e.g., ("doi", "pmid"))
    required: bool = False           # If True, failure = composite failure
    filter-condition: str | None = None  # SQL-like filter (e.g., "pmid IS NOT NULL")
    timeout-seconds: int = 600       # Per-enricher timeout
    fallback-strategy: Literal["skip", "use-cached", "fail"] = "skip"

@dataclass(frozen=True, slots=True)
class MergeConfig:
    """Configuration for merge step."""
    strategy: MergeStrategy          # left-outer, inner, union
    conflict-resolution: ConflictResolution  # seed-priority, latest, explicit
    output-silver-path: str
    output-gold-path: str
    field-mappings: dict[str, str] | None = None  # Rename fields during merge

@dataclass(frozen=True, slots=True)
class CompositeConfig:
    """Complete composite pipeline configuration."""
    name: str                        # e.g., "composite_publication"
    seed: SeedConfig                 # Seed pipeline config
    enrichers: tuple[EnricherConfig, ...]
    merge: MergeConfig
    dq: DQConfig                     # Composite-level DQ thresholds

    def --post-init--(self) -> None:
        self.-validate-join-keys()
        self.-validate-required-enrichers()
```

### EnrichmentResult

```python
@dataclass(frozen=True, slots=True)
class EnrichmentResult:
    """Result of a single enrichment pipeline execution."""
    enricher-name: str
    status: EnrichmentStatus  # success, partial, failed, skipped
    records-enriched: int
    records-not-found: int
    records-errored: int
    dq-error-rate: float
    duration-seconds: float
    error-message: str | None = None

    @property
    def is-success(self) -> bool:
        return self.status in (EnrichmentStatus.SUCCESS, EnrichmentStatus.PARTIAL)

class EnrichmentStatus(str, Enum):
    SUCCESS = "success"       # All records enriched
    PARTIAL = "partial"       # Some records enriched (below hard threshold)
    FAILED = "failed"         # Above hard threshold or critical error
    SKIPPED = "skipped"       # Filter condition excluded all records
    NOT-RUN = "not-run"       # Pipeline not executed (e.g., resume scenario)
```

### MergeStrategy

```python
class MergeStrategy(str, Enum):
    """Strategy for merging enriched data."""

    LEFT - OUTER = "left-outer"  # All seed records, nullable enrichments
    INNER = "inner"  # Only records found in ALL required enrichers
    UNION = "union"  # All records from any source (with dedup)


class ConflictResolution(str, Enum):
    """Strategy for resolving field conflicts between sources."""

    SEED - PRIORITY = "seed-priority"  # Seed value wins
    ENRICHER - PRIORITY = "enricher"  # Enricher value wins
    LATEST - TIMESTAMP = "latest"  # Most recent value wins
    EXPLICIT - RULES = "explicit"  # Use field-priorities mapping
    COALESCE = "coalesce"  # First non-null value
```

## Column Naming Convention

### Status: Accepted (Updated 2025-01-25)

### Context

При объединении данных из разных источников возникают конфликты имён колонок.
Предыдущая реализация переименовывала только enricher колонки с разными
стратегиями prefix (provider/entity/both), что приводило к:

1. Неконсистентности: seed колонки без prefix, enricher — с prefix
1. Сложной логике определения стратегии
1. Трудностям при coalesce из-за разных форматов

### Decision

**Все** бизнес-колонки (seed и enricher) переименовываются в единый формат:

```
{provider}.{entity}.{field}
```

**Примеры**:

| Source                          | Original       | Qualified                           |
| ------------------------------- | -------------- | ----------------------------------- |
| chembl_publication (seed)       | title          | chembl.publication.title            |
| crossref_publication (enricher) | title          | crossref.publication.title          |
| crossref_publication (enricher) | citation-count | crossref.publication.citation-count |

**Исключения** (НЕ переименовываются):

1. **Join keys**: `doi`, `pmid`, `pmc-id` — для совместимости с join операциями
1. **System columns**: колонки с prefix `-` (`_run_id`, `_ingestion_ts`, etc.)
1. **Entity ID columns**: `entity-id`, `content-hash` — системные идентификаторы

### Column Ordering

Колонки в output упорядочены по семантическим группам:

| Order | Group          | Examples                                                    |
| ----- | -------------- | ----------------------------------------------------------- |
| 1     | System         | entity-id, content-hash, \_run_id, \_ingestion_ts           |
| 2     | Identifiers    | doi, pmid, pmc-id, document-chembl-id                       |
| 3     | Title          | title, chembl.publication.title, crossref.publication.title |
| 4     | Abstract       | abstract, chembl.publication.abstract                       |
| 5     | Authors        | authors, first-author, affiliations                         |
| 6     | Journal        | journal, publisher, volume, issue                           |
| 7     | Dates          | publication-date, year, created-at                          |
| 8     | Metrics        | citation-count, reference-count                             |
| 9     | Classification | mesh-terms, keywords, subjects                              |
| 10    | URLs           | url, pdf-url, landing-page                                  |
| 11    | Other          | All remaining fields                                        |

Внутри каждой группы колонки упорядочены по:

1. Provider priority: chembl → crossref → pubmed → openalex
1. Alphabetically для одного провайдера

### Implementation

- `ColumnRenamer`: Переименование колонок в qualified format
- `ColumnOrderService`: Каноническое упорядочивание колонок по семантическим группам и source-priority rules
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
- ColumnOrderService: `src/bioetl/application/composite/column_service.py`
- ColumnQualifier: `src/bioetl/domain/value_objects/column_qualifier.py`
- ColumnOrderConfig: `src/bioetl/domain/value_objects/column_order.py`

## Preserve All Sources Feature

### Status: Accepted (Added 2026-01-28)

### Context

During merge, columns with the same semantic meaning from different providers (e.g., `title` from ChEMBL, CrossRef, OpenAlex) are typically **coalesced** into a single column using the configured conflict resolution strategy. This is the default behavior.

However, some use cases require access to **all** provider values for comparison, quality analysis, or ML feature engineering.

### Decision

Add `preserve-all-sources: bool = False` to `MergeConfig`. When enabled:

1. **Skip coalescing** - MergeService does not apply conflict resolution
1. **Keep all qualified columns** - All `{provider}.{entity}.{field}` columns are retained
1. **Full traceability** - Downstream consumers can see exactly what each provider returned

### Configuration

```yaml
# configs/composites/publication.yaml
merge:
  strategy: left-outer
  conflict-resolution: seed-priority  # Used when preserve-all-sources=false
  preserve-all-sources: true          # NEW: Keep all provider columns
```

### Behavior Comparison

| Mode                                    | Output Columns                                                 | Use Case                           |
| --------------------------------------- | -------------------------------------------------------------- | ---------------------------------- |
| `preserve-all-sources: false` (default) | `title` (single coalesced column)                              | Production views with "best" value |
| `preserve-all-sources: true`            | `chembl.publication.title`, `crossref.publication.title`, etc. | Data quality analysis, ML features |

### Implementation

- **Domain**: `MergeConfig.preserve-all-sources: bool = False` in `domain/composite/config.py`
- **Application**: `MergeService.-resolve-conflicts()` skips coalescing when flag is True
- **Schema**: Pydantic schema updated with `preserve-all-sources` field

### Example Output

```python
# preserve-all-sources: false (default)
df.columns = ["entity-id", "title", "abstract", "citation-count", ...]

# preserve-all-sources: true
df.columns = [
    "entity-id",
    "chembl.publication.title",
    "crossref.publication.title",
    "openalex.publication.title",
    "pubmed.publication.title",
    "chembl.publication.abstract",
    ...,
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

When `preserve-all-sources: true` is enabled, the number of columns grows significantly (94 base fields × up to 5 providers). The **Field Group Registry** (`FieldGroupRegistry`) provides semantic grouping for these columns.

### Purpose

1. **Gold Filtering**: Automatically exclude TRASH-group fields (e.g., `content-hash`, `language`) from Gold output
1. **Column Ordering**: Sort output columns by semantic group (ID-AND-STATUS first, TRASH last) and provider priority
1. **Validation**: Identify unmapped columns for data quality checks

### Domain Models

```
FieldGroupId (enum)          — 8 semantic groups (alias for PublicationFieldGroup)
FieldMapping (frozen)        — base-name → provider-columns + group
FieldGroupDefinition (frozen)— group-id, display-name, include-in-gold, fields
FieldGroupRegistry           — central registry with lookup indices
```

### YAML Configuration

Field groups are defined in `configs/composites/field_groups/publication.yaml`:

```yaml
version: "1.0"
entity: publication
provider-order: [chembl, crossref, openalex, pubmed, semanticscholar]
groups:
  - id: id-and-status
    display-name: "ID & Status"
    include-in-gold: true
    fields:
      - base-name: doi
        columns:
          - chembl.publication.doi
          - crossref.publication.doi
          - openalex.publication.doi
  - id: trash
    display-name: "Trash"
    include-in-gold: false
    fields:
      - base-name: content-hash
        columns: [chembl.publication.content-hash, ...]
```

### Integration with MergeService

During `_write_merged_gold()`, `MergeService` uses the registry to filter out TRASH columns:

```python
if self.-field-group-registry is not None:
    trash-cols = self.-field-group-registry.get-trash-columns(df.columns)
    if trash-cols:
        df = df.drop(trash-cols)
```

### Graceful Degradation

If no YAML config exists for a composite pipeline, bootstrap continues without the registry. No filtering or ordering is applied — the pipeline works as before.

### Files

| Layer          | File                                               | Description                                                    |
| -------------- | -------------------------------------------------- | -------------------------------------------------------------- |
| Domain         | `domain/composite/field_groups.py`                 | Models: FieldMapping, FieldGroupDefinition, FieldGroupRegistry |
| Infrastructure | `infrastructure/config/field_group_loader.py`      | YAML → domain object loader                                    |
| Config         | `configs/composites/field_groups/publication.yaml` | 8 groups, 94 fields                                            |
| Composition    | `composition/bootstrap/runtime/composite.py`       | Bootstrap integration                                          |
| Application    | `application/composite/merger.py`                  | Gold filtering integration                                     |

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
        seed-runner-factory: Callable[[], PipelineRunner],  # skip-gold=True
        enricher-runner-factory: Callable[[str], PipelineRunner],  # skip-gold=True
        key-extractor: KeyExtractorService,
        coordinator: EnrichmentCoordinator,
        merger: MergeService,
        checkpoint-service: CompositeCheckpointService,
        logger: LoggerPort,
        lock-manager: CompositeLockCoordinator,
    ) -> None:
        ...

    async def run(self) -> CompositeResult:
        """Execute full composite pipeline."""
        async with self.-lock-manager:
            # 1. Load checkpoint (for resume)
            state = await self.-checkpoint-manager.load()

            # 2. Run seed (if not completed)
            if not state.seed-completed:
                await self.-run-seed()
                state = state.with-seed-completed()
                await self.-checkpoint-manager.save(state)

            # 3. Extract keys from seed Silver
            keys-df = await self.-key-extractor.extract(
                self.-config.seed.output-keys
            )

            # 4. Run enrichers (fan-out)
            results = await self.-coordinator.run-enrichers(
                keys=keys-df,
                enrichers=self.-config.enrichers,
                completed=state.completed-enrichers,
            )

            # 5. Merge results
            merge-result = await self.-merger.merge(
                seed-table=self.-config.seed.silver-table,
                enricher-tables=[e.pipeline for e in self.-config.enrichers],
                results=results,
            )

            # 6. Cleanup
            await self.-checkpoint-manager.delete()

            return CompositeResult(
                seed-result=state.seed-result,
                enrichment-results=results,
                merge-result=merge-result,
            )
```

### EnrichmentCoordinator

```python
class EnrichmentCoordinator:
    """Coordinates parallel enrichment pipeline execution.

    Implements fan-out pattern with async gather.
    Handles timeouts, failures, and partial completion.
    """

    async def run-enrichers(
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
            filtered-keys = self.-apply-filter(keys, enricher.filter-condition)
            if filtered-keys.is-empty():
                tasks.append(self.-create-skipped-result(enricher))
                continue

            tasks.append(
                self.-run-single-enricher(enricher, filtered-keys)
            )

        results = await asyncio.gather(*tasks, return-exceptions=True)
        return self.-process-results(enrichers, results)

    async def -run-single-enricher(
        self,
        enricher: EnricherConfig,
        keys: pl.DataFrame,
    ) -> EnrichmentResult:
        """Run a single enricher with timeout and error handling."""
        try:
            async with asyncio.timeout(enricher.timeout-seconds):
                runner = self.-runner-factory(enricher.pipeline)
                # Pass keys via input filter mechanism
                await runner.run()
                return self.-build-success-result(enricher)
        except asyncio.TimeoutError:
            return EnrichmentResult(
                enricher-name=enricher.pipeline,
                status=EnrichmentStatus.FAILED,
                error-message=f"Timeout after {enricher.timeout-seconds}s",
                ...
            )
        except Exception as e:
            if enricher.required:
                raise  # Propagate for required enrichers
            return self.-build-error-result(enricher, e)
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
        seed-table: str,
        enricher-tables: Sequence[str],
        results: dict[str, EnrichmentResult],
    ) -> MergeResult:
        """Merge seed and enricher data into unified Gold table.

        Args:
            seed-table: Path to seed Silver table.
            enricher-tables: Paths to enricher Silver tables.
            results: Enrichment results for filtering.

        Returns:
            MergeResult with statistics and lineage.
        """
        # 1. Load seed data
        seed-df = await self.-storage.read-silver(seed-table)

        # 2. Apply joins based on strategy
        merged-df = seed-df
        for enricher in enricher-tables:
            result = results.get(enricher)
            if not result or not result.is-success:
                continue

            enricher-df = await self.-storage.read-silver(enricher)
            merged-df = self.-apply-join(
                merged-df,
                enricher-df,
                join-keys=self.-get-join-keys(enricher),
            )

        # 3. Resolve conflicts
        merged-df = self.-resolve-conflicts(merged-df)

        # 4. Add lineage metadata
        merged-df = self.-add-lineage(merged-df, results)

        # 5. Write to Gold
        await self.-storage.write-gold(
            df=merged-df,
            path=self.-config.merge.output-gold-path,
        )

        return MergeResult(
            records-merged=len(merged-df),
            sources-used=[...],
            lineage-summary={...},
        )

    def -resolve-conflicts(self, df: pl.DataFrame) -> pl.DataFrame:
        """Apply conflict resolution strategy."""
        match self.-config.merge.conflict-resolution:
            case ConflictResolution.SEED-PRIORITY:
                return self.-coalesce-prefer-first(df)
            case ConflictResolution.LATEST-TIMESTAMP:
                return self.-pick-latest(df)
            case ConflictResolution.COALESCE:
                return self.-coalesce-non-null(df)
            case ConflictResolution.EXPLICIT-RULES:
                return self.-apply-explicit-rules(df)
```

## Configuration Schema

### YAML Configuration

```yaml
# configs/composites/publication.yaml
schema-version: "2.0.0"

composite:
  name: composite_publication
  version: "1.0.0"

  # ---------------------------------------------------------------------------
  # Seed Pipeline Configuration
  # ---------------------------------------------------------------------------
  seed:
    pipeline: chembl_publication
    output-keys:
      - document-id      # ChEMBL document ID
      - doi              # Digital Object Identifier
      - pmid             # PubMed ID
    silver-table: silver/chembl/publication

  # ---------------------------------------------------------------------------
  # Enricher Pipelines
  # ---------------------------------------------------------------------------
  enrichers:
    # CrossRef: Optional enricher for citation data
    - pipeline: crossref_publication
      join-keys:
        - doi            # Primary join key
      required: false    # Changed from required to optional
      timeout-seconds: 900

    # OpenAlex: Optional enricher for academic metadata
    - pipeline: openalex_publication
      join-keys:
        - doi            # Primary
        - pmid           # Fallback
      required: false
      filter-condition: "doi IS NOT NULL OR pmid IS NOT NULL"
      timeout-seconds: 600

    # PubMed: Optional enricher for medical metadata
    - pipeline: pubmed_publication
      join-keys:
        - pmid
      required: false
      filter-condition: "pmid IS NOT NULL"
      timeout-seconds: 600

    # Semantic Scholar: Optional enricher for AI/ML features
    - pipeline: semanticscholar_publication
      join-keys:
        - doi
        - pmid
      required: false
      filter-condition: "doi IS NOT NULL OR pmid IS NOT NULL"
      timeout-seconds: 1200
      fallback-strategy: skip  # High rate limits, ok to skip

  # ---------------------------------------------------------------------------
  # Merge Configuration
  # ---------------------------------------------------------------------------
  merge:
    strategy: left-outer         # All seed records preserved
    conflict-resolution: seed-priority

    # Field-level priority overrides (for explicit-rules strategy)
    field-priorities:
      title: [chembl, crossref, openalex]
      abstract: [pubmed, openalex, chembl]
      citations-count: [crossref, openalex]
      mesh-terms: [pubmed]
      concepts: [openalex]

    output:
      silver: silver/composite/publication
      gold: gold/publication-enriched

  # ---------------------------------------------------------------------------
  # Data Quality Configuration
  # ---------------------------------------------------------------------------
  dq-overrides:
    # Composite-level thresholds (applied to merge result)
    soft-fail-threshold: 0.10
    hard-fail-threshold: 0.30

    # Per-enricher overrides
    enricher-overrides:
      semanticscholar_publication:
        soft-fail-threshold: 0.20  # Higher tolerance for S2
        hard-fail-threshold: 0.50

    # Required fields in final Gold output
    required-fields:
      - document-id
      - title

  # ---------------------------------------------------------------------------
  # Execution Options
  # ---------------------------------------------------------------------------
  execution:
    # Maximum concurrent enrichers
    max-concurrency: 4

    # Enable checkpointing for resume
    checkpoint-enabled: true

    # Retry configuration for enrichers
    retry:
      max-attempts: 3
      backoff-multiplier: 2.0

  # ---------------------------------------------------------------------------
  # Lineage Configuration
  # ---------------------------------------------------------------------------
  lineage:
    # Track field-level provenance
    track-field-sources: true

    # Include enrichment timestamps
    track-timestamps: true

    # Include enrichment status per record
    track-status: true
```

## Test Strategy

### Unit Tests

```python
# tests/unit/application/composite/test_merger.py

class TestMergeService:
    """Test cases for MergeService."""

    def test-left-outer-join-preserves-all-seed-records(self):
        """LEFT OUTER join should keep all seed records."""
        seed = pl.DataFrame({"doi": ["10.1/a", "10.1/b", "10.1/c"]})
        enricher = pl.DataFrame({"doi": ["10.1/a"], "citations": [100]})

        merged = merge-service.merge(seed, enricher, strategy=LEFT-OUTER)

        assert len(merged) == 3
        assert merged.filter(pl.col("doi") == "10.1/a")["citations"][0] == 100
        assert merged.filter(pl.col("doi") == "10.1/b")["citations"][0] is None

    def test-inner-join-filters-unmatched-records(self):
        """INNER join should only keep matched records."""
        ...

    def test-conflict-resolution-seed-priority(self):
        """Seed values should take precedence with seed-priority."""
        seed = pl.DataFrame({"doi": ["10.1/a"], "title": "Seed Title"})
        enricher = pl.DataFrame({"doi": ["10.1/a"], "title": "Enricher Title"})

        merged = merge-service.merge(
            seed, enricher,
            conflict-resolution=ConflictResolution.SEED-PRIORITY
        )

        assert merged["title"][0] == "Seed Title"

    def test-lineage-metadata-added-correctly(self):
        """Lineage metadata should track all sources."""
        ...

# tests/unit/application/composite/test_coordinator.py

class TestEnrichmentCoordinator:
    """Test cases for EnrichmentCoordinator."""

    async def test-parallel-execution-respects-timeout(self):
        """Enrichers should timeout independently."""
        ...

    async def test-required-enricher-failure-propagates(self):
        """Required enricher failure should raise exception."""
        coordinator = EnrichmentCoordinator(...)
        enricher = EnricherConfig(pipeline="crossref", required=True)

        with pytest.raises(CriticalError):
            await coordinator.run-enrichers(
                keys=test-keys,
                enrichers=[enricher],
            )

    async def test-optional-enricher-failure-continues(self):
        """Optional enricher failure should return error result."""
        ...

    async def test-filter-condition-applied-correctly(self):
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
    async def test-full-composite-run(self, vcr-cassette):
        """Full composite run with all enrichers."""
        runner = await bootstrap-composite-pipeline(
            "composite_publication",
            limit=10,
        )

        result = await runner.run()

        assert result.seed-result.records-processed > 0
        assert "crossref" in result.enrichment-results
        assert result.merge-result.records-merged > 0

    @pytest.mark.vcr
    async def test-resume-after-enricher-failure(self, vcr-cassette):
        """Resume should skip completed enrichers."""
        # First run with simulated failure
        runner = await bootstrap-composite-pipeline(
            "composite_publication",
            limit=10,
        )
        # Simulate failure after seed
        ...

        # Resume run
        runner = await bootstrap-composite-pipeline(
            "composite_publication",
            resume=True,
        )
        result = await runner.run()

        # Seed should be skipped
        assert result.seed-result.status == "resumed"

# tests/integration/composite/test_enricher_failures.py

@pytest.mark.integration
class TestEnricherFailureScenarios:
    """Test various enricher failure scenarios."""

    @pytest.mark.vcr
    async def test-optional-enricher-timeout(self):
        """Optional enricher timeout should not fail composite."""
        ...

    @pytest.mark.vcr
    async def test-required-enricher-dq-failure(self):
        """Required enricher >20% DQ errors should fail composite."""
        ...
```

### Architecture Tests

```python
# tests/architecture/test_composite_imports.py

def test-composite-domain-has-no-infrastructure-imports():
    """domain/composite should not import from infrastructure."""
    for file in glob.glob("src/bioetl/domain/composite/**/*.py"):
        with open(file) as f:
            content = f.read()
        assert "from bioetl.infrastructure" not in content
        assert "import bioetl.infrastructure" not in content

def test-composite-application-has-no-infrastructure-imports():
    """application/composite should not import from infrastructure."""
    ...

def test-composite-port-contracts():
    """Composite ports should follow standard conventions."""
    ...
```

## CLI Interface

### Commands

```bash
# Full composite run
bioetl run-composite --composite publication

# With options
bioetl run-composite --composite publication \
    --seed-limit 1000 \
    --dry-run

# Re-enrich specific source only
bioetl run-composite --composite publication \
    --enrich-only pubmed,openalex

# Skip optional enrichers (fast mode)
bioetl run-composite --composite publication \
    --required-only

# Resume after failure
bioetl run-composite --composite publication \
    --resume

# Force re-run of specific enricher
bioetl run-composite --composite publication \
    --force-enricher crossref

# List composite pipeline status
bioetl run-composite --composite publication --dry-run
```

### CLI Implementation

```python
# src/bioetl/interfaces/cli/commands/run_composite.py

@cli.command()
@click.option("--enrich-only", help="Run only specified enrichers (comma-separated)")
@click.option("--required-only", is-flag=True, help="Skip optional enrichers")
@click.option("--force-enricher", help="Force re-run of specified enricher")
def run_composite_command(composite: str, enrich_only: str | None, required_only: bool, ...):
    """Run a composite pipeline."""
    return run_composite(composite, enrich_only=enrich_only, required_only=required_only, ...)
```

## Consequences

### Positive

1. **Unified data enrichment** - Single command to run multi-source pipelines
1. **Graceful degradation** - Optional enricher failures don't block composite
1. **Full lineage** - Every field traceable to source
1. **Resume capability** - Checkpoint-based recovery from failures
1. **Configurable flexibility** - YAML-based orchestration without code changes
1. **No redundant Gold writes** - Sub-pipelines run with `skip-gold=True`,
   writing only Bronze+Silver; the composite merge phase produces the unified Gold output

### Negative

1. **Increased complexity** - New components (Coordinator, Merger, etc.)
1. **Configuration learning curve** - YAML schema is more complex
1. **Debugging difficulty** - Multi-source issues harder to trace
1. **Storage overhead** - Intermediate Silver tables for each enricher

### Risks

| Risk                                    | Mitigation                               |
| --------------------------------------- | ---------------------------------------- |
| Memory pressure from parallel enrichers | `max-concurrency` limit, adaptive sizing |
| Lock contention with many enrichers     | Hierarchical lock strategy               |
| Inconsistent data on partial failures   | Checkpoint + resume mechanism            |
| Configuration errors                    | Schema validation via Pydantic           |

## Rollout

### Phase 1: Foundation (v1.0)

- [ ] Domain models (CompositeConfig, EnrichmentResult, MergeStrategy)
- [ ] CompositePipelineRunner basic implementation
- [ ] EnrichmentCoordinator with sequential execution
- [ ] MergeService with LEFT OUTER join only
- [ ] CLI extensions for composite pipelines

### Phase 2: Parallelism (v1.1)

- [ ] Parallel enricher execution (asyncio.gather)
- [ ] Timeout handling per enricher
- [ ] CompositeCheckpointService for resume

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
- RULES.md v6.1 §2.4 (Backfill/Replay)
- RULES.md v6.1 §3.3 (Concurrency & Locks)

**Current Composite Configurations**:

- `configs/composites/publication.yaml` (shows `required: false` for CrossRef)
- `configs/composites/target.yaml` (reference for dependency chaining)
- `configs/composites/field_groups/publication.yaml` (field group registry)

## Compliance

| Control      | Requirement                                                                | Status | Evidence                                |
| ------------ | -------------------------------------------------------------------------- | ------ | --------------------------------------- |
| Format       | ADR MUST use standard metadata and normalized section headings             | `pass` | `ADR-026-composite-pipeline-pattern.md` |
| Status       | ADR status MUST be explicit and consistent                                 | `pass` | `Accepted`                              |
| Supersession | Superseded or superseding ADRs SHOULD be linked explicitly when applicable | `n/a`  | `metadata block`                        |
| Verification | Implementation and validation expectations MUST be documented              | `pass` | `Verification / Acceptance Criteria`    |
| References   | Related ADRs, docs, or artifacts SHOULD be linked                          | `pass` | `References`                            |

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
