# 18 Domain Layer Audit

## Executive Summary

- The current domain layer mixes execution plumbing, provider wiring, and infrastructure ports with very few actual domain entities; most data is still handled as Pandas dataframes instead of aggregates.
- Several duplicate or deprecated constructs (e.g. two hash services, legacy logging shims, config re-exports) add noise and make it unclear which model is canonical.
- Most ABC/Protocol definitions have a single (or zero) implementation, signalling speculative generality without proven variability.
- Documentation (glossary and schema overview) references concepts such as `TestItem` that are not backed by code, leading to mismatched bounded contexts.

## 1. Model inventory

### 1.1 Core runtime/config models

| Model | File | Type | Key data / responsibility | Domain area |
| --- | --- | --- | --- | --- |
| `StageResult` | `src/bioetl/domain/models.py` | dataclass | Stage name, success flag, record/chunk counters, duration, error list | Pipeline runtime telemetry |
| `RunContext` | `src/bioetl/domain/models.py` | dataclass | `run_id`, `entity_name`, `provider`, `started_at`, opaque `config`/`metadata` dicts | Pipeline orchestration |
| `RunResult` | `src/bioetl/domain/models.py` | dataclass | Aggregated run outcome (`row_count`, `output_path`, per-stage metrics) | Pipeline orchestration |
| `StageDescriptor` | `src/bioetl/domain/models.py` | descriptor | Binds stage `name` to callable, `skip_on_dry_run`, `required` flags | Pipeline wiring |
| `PipelineConfig` (+ nested sections) | `src/bioetl/domain/configs/pipeline.py` | Pydantic aggregate | Canonical pipeline config plus HTTP client, storage paths, logging, metrics, determinism, hashing, normalization | Configuration (cross-layer) |
| `ProviderDefinition` | `src/bioetl/domain/providers.py` | dataclass | Links `ProviderId`, provider config type, and component factory protocol | Provider registry |
| `InMemoryProviderRegistry` | `src/bioetl/domain/provider_registry.py` | mutable registry | Register/list/restore provider definitions, throws specific errors | Provider registry |
| `RawRecord` / `RecordSource` / `ApiRecordSource` | `src/bioetl/domain/record_source.py` | TypedDict + Protocol + concrete class | Describe batches of raw provider records and wrap `ExtractionServiceABC.iter_extract` with optional adapters | Extraction ports |
| `ValidationResult` | `src/bioetl/domain/validation/contracts.py` | dataclass | `is_valid`, `errors`, `warnings`, optional `validated_df` | Validation |
| `WriteResult` | `src/bioetl/domain/clients/base/output/contracts.py` | dataclass | Output `Path`, `row_count`, duration, checksum | Output/IO port |

Other notable configuration/value objects include `HashingConfig`, `NormalizationConfig`, `DefaultsConfig`, and the schema registry singleton in `src/bioetl/domain/schemas/registry.py`.

### 1.2 Entity schemas per bounded context

| Bounded context | Schema class | File | Highlights |
| --- | --- | --- | --- |
| Activity | `ActivityTableSchema` | `src/bioetl/domain/schemas/chembl/activity.py` | ~45 business columns (activity IDs, assay/document links, measurement values) plus deterministic metadata columns via `build_output_column_order`. |
| Assay | `AssayTableSchema` | `src/bioetl/domain/schemas/chembl/assay.py` | Captures assay metadata (category, organism, BAO IDs/labels, classifications, strain/tissue, target IDs). |
| Document | `DocumentTableSchema` | `src/bioetl/domain/schemas/chembl/document.py` | Publication-level data (DOI/PubMed, journal info, doc type, score). |
| Molecule (acts as “TestItem”) | `MoleculeTableSchema` | `src/bioetl/domain/schemas/chembl/molecule.py` | Molecule hierarchies, properties, clinical phase, availability flags, synonyms. |
| Target | `TargetTableSchema` | `src/bioetl/domain/schemas/chembl/target.py` | Target identifiers, taxonomy, organism, type, UniProt linkage, cross references. |

### 1.3 Bounded context coverage

- ChEMBL entities (`activity`, `assay`, `document`, `molecule`, `target`) have Pandera schemas registered via `bioetl.domain.schemas.register_schemas`.
- Documentation still references `TestItem` as a separate concept, but code only exposes `MoleculeTableSchema`; there are no domain objects or schemas for `cell`, `tissue`, `test_item`, despite CSV fixtures existing under `data/input`.
- All entities are handled as Pandas dataframes; there are no aggregate/domain classes per entity, so the bounded contexts are defined solely by schema names.

## 2. Duplicate / divergent definitions

1. **Hash service duplication** – `src/bioetl/domain/transform/hash_service.py` implements `HashService` while `src/bioetl/infrastructure/transform/impl/hash_service_impl.py` re-implements the same API (hash columns, index, metadata) against the same `HashServiceABC`. Keeping both causes drift risk and confuses consumers about the canonical entry point.
2. **Logging/observability shims** – `src/bioetl/domain/observability/contracts.py` defines the current logging/tracing ports, yet `src/bioetl/domain/clients/base/logging/contracts.py` (deprecated) still exposes `ProgressReporterABC` and emits runtime `DeprecationWarning`. Both modules are exported from the domain layer, which means new code can still import the legacy shim accidentally.
3. **Config re-export layer** – `src/bioetl/domain/configs/base.py` is a purely duplicative module that re-imports everything from `pipeline.py` for “legacy compatibility”. It keeps stale import paths alive and hides the real source of truth.
4. **Extraction contract shim** – `src/bioetl/domain/contracts.py` re-exports `ExtractionServiceABC` and `BatchAdapterABC` from `domain.ports.extraction` with a `Deprecated shim` banner, adding another dangling alias.
5. **Domain glossary vs code** – `docs/domain/01-glossary.md` and `docs/domain/schemas/00-schemas-overview.md` describe `TestItem`/`TestitemSchema`, but the codebase only has `MoleculeTableSchema`. Two names for the same business concept lead to fragmented documentation.

#### Duplicate cleanup checklist

- [ ] Merge `HashService` and `HashServiceImpl` into one canonical implementation (keep tests + DI wiring in a single place).
- [ ] Remove/replace `bioetl.domain.clients.base.logging.contracts` exports; migrate remaining imports to `bioetl.domain.observability`.
- [ ] Drop `bioetl.domain.configs.base` and update callers to import directly from `pipeline.py`.
- [ ] Remove `bioetl.domain.contracts` shim and fix imports to use `bioetl.domain.ports.extraction`.
- [ ] Update glossary/schema docs to rename `TestItem` → `Molecule` (or introduce an actual `TestItem` model) so code and documentation agree.

## 3. ABC / Protocol audit

| Port / ABC | Location | Implementations today | Observation | Suggested action |
| --- | --- | --- | --- | --- |
| `RequestBuilderABC` | `domain/clients/base/contracts.py` | Only `ChemblRequestBuilderImpl` via `default_request_builder` (requires `base_url`) | No evidence of alternative providers; factory raises without URL | Collapse into provider-specific builder or keep interface only if another provider is imminent. |
| `ResponseParserABC` | same | Only `ChemblResponseParserImpl` | Currently redundant abstraction | Inline into ChemBL client or stub explicit reason for polymorphism. |
| `PaginatorABC` | same | Only `ChemblPaginatorImpl` | No non-ChemBL paginator | Replace with simple strategy enum or postpone until we add a second provider. |
| `RateLimiterABC` | same | Only `TokenBucketRateLimiterImpl` | Abstraction around a single implementation | Keep only if we expect to inject e.g. noop limiter in tests; otherwise expose concrete helper. |
| `RetryPolicyABC` | same | Only `ExponentialBackoffRetryImpl` | Same as above | Consider collapsing into plain dataclass/config-driven helper. |
| `CacheABC` | same | `MemoryCacheImpl`, `FileCacheImpl` | Two variants exist; abstraction justified | Keep. |
| `SecretProviderABC` | same | `EnvSecretProvider` | Only env-backed provider, but extension is plausible (vault) | Keep but move out of “domain” namespace into infrastructure-facing package. |
| `SideInputProviderABC` | same | No implementation (`default_side_input_provider` raises) | Classic speculative generality | Remove until a real provider exists. |
| `BatchAdapterABC` | `domain/ports/extraction.py` | Only `PandasBatchAdapter` | Could be replaced with `Callable[[Any], list[RawRecord]]` | Downgrade to simple callable type alias. |
| `HashServiceABC` | `domain/transform/contracts.py` | `HashService` (domain) + `HashServiceImpl` (infra) | Two parallel trees implement same thing | Keep the ABC but delete one concrete implementation. |

#### Abstraction cleanup checklist

- [ ] Remove `SideInputProviderABC` (or implement a real provider + tests).
- [ ] Replace `RequestBuilderABC` / `ResponseParserABC` / `PaginatorABC` / `BatchAdapterABC` with simpler callables until a second provider appears.
- [ ] Document an explicit extension plan for `RateLimiterABC` + `RetryPolicyABC`; if none exists, inline them to reduce noise.
- [ ] Keep `CacheABC`, `SecretProviderABC`, `HashServiceABC`, `NormalizationServiceABC`, `SchemaProviderABC` as the vetted ports.

## 4. DDD boundary issues

1. **DataFrame-centric “domain”** – Core contracts such as `NormalizationServiceABC`, `HashServiceABC`, and `ValidationResult` operate directly on `pandas.DataFrame`/`Series` (`src/bioetl/domain/transform/contracts.py`, `src/bioetl/domain/validation/contracts.py`). There are no aggregates for `Activity`, `Assay`, etc., so business logic is expressed as column-level mutations. This makes the domain layer dependent on Pandas internals and hard to unit-test without DataFrames.
2. **Infrastructure-heavy pipeline config** – `PipelineConfig` embeds HTTP timeouts, rate limits, cache paths, logging levels, and feature flags in the same object that carries domain identifiers (`entity`, `provider`). The domain layer therefore knows about networking, observability, and storage (see `src/bioetl/domain/configs/pipeline.py` sections `ClientConfig`, `StorageConfig`, `LoggingConfig`, `MetricsConfig`). Split the structure into a pure domain contract plus infrastructure profiles.
3. **Record source orchestrates extraction** – `ApiRecordSource` (`src/bioetl/domain/record_source.py`) loops over `ExtractionServiceABC.iter_extract`, applies chunking, and batch adaptation. This is orchestration logic that fits better in the application layer; today it lives in the domain package and depends on the extraction service protocol.
4. **Domain-defined IO ports know filesystem semantics** – `WriterABC` / `OutputWriterABC` in `src/bioetl/domain/clients/base/output/contracts.py` require `pathlib.Path`, atomic-write knowledge, and Pandas DataFrames. Those concerns belong to infrastructure; the domain should define an abstract “export table” use case with DTOs instead of file paths.
5. **Documentation vs code boundaries** – Architecture docs still present `TestItem` as a first-class aggregate (`docs/architecture/01-domain-objects.md`), but no such model or schema exists. This misalignment confuses bounded contexts and hides that the “test item” context is currently served by `MoleculeTableSchema`.

Each of these issues dilutes the “pure domain” boundary and makes it harder to enforce deterministic, infrastructure-agnostic business logic.

## 5. Target state for a clean domain layer

- Exactly one canonical model (class or schema) per business concept (`Activity`, `Assay`, `Target`, `Molecule/TestItem`, `Document`, etc.).
- Domain services operate on typed aggregates/value objects rather than raw `pd.DataFrame` instances; adapters handle conversion at the application boundary.
- Only meaningful ports remain; every ABC has at least two real implementations or a clear extension strategy. Legacy shims and speculative abstractions are removed.
- Domain packages no longer expose infrastructure details (paths, HTTP settings, logging flags). Those live in configuration profiles or infrastructure services.
- Docs and diagrams mirror the codebase (matching names, column sets, and dependencies) to keep bounded contexts explicit.

## 6. Refactoring roadmap

| Phase | Focus | Key actions |
| --- | --- | --- |
| Phase 0 – Cleanup (now) | Remove dead weight | Apply the duplicate and abstraction checklists: delete shims, collapse hash service, drop unused ABCs, update documentation terminology. |
| Phase 1 – Domain modeling | Introduce aggregates | Define lightweight dataclasses (or Pydantic models) for `Activity`, `Assay`, `Document`, `Target`, `Molecule` that mirror Pandera schemas; add mappers to/from DataFrames inside the application layer. |
| Phase 2 – Boundary hardening | Separate concerns | Split `PipelineConfig` into domain contract + infrastructure profile, move `ApiRecordSource` and writer abstractions into application/infrastructure namespaces, and keep only pure domain ports (e.g., `ExtractionServiceABC`). |
| Phase 3 – Provider extensibility | Justify abstractions | Once the domain has aggregates, re-introduce only the ports that are needed for multiple providers (e.g., additional request builders, parsers, or normalization services). Document expected variants and ensure tests cover each port. |

Tracking these phases alongside the provided checklists will progressively declutter the domain layer and prepare it for stricter DDD and hexagonal boundaries.

