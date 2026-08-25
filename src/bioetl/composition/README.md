# Composition Layer — Navigation Map

The composition layer is the **only place** where concrete implementations are wired
together. No business logic lives here — only assembly, factory, and registration code.

## Package Structure

```
composition/
├── entrypoints.py              # First-party runtime seam (run/create/resolve)
├── execution_api.py            # External compatibility shim → entrypoints / _pipeline_execution
├── control_plane_runtime.py    # Control-plane runtime seam (not *_api)
├── health_api.py               # External compatibility shim → health_service_access / _services
├── maintenance_api.py          # External compatibility shim → owner CLI / _services
├── resources_runtime.py        # Resource-management runtime seam (not *_api)
├── registry_api.py             # Typed PipelineRegistry contract (lazy re-export of registry_core)
├── builders.py                 # High-level builder helpers for CLI/orchestration
├── types.py                    # Shared type aliases for composition
├── observability.py            # ObservabilityBundle dataclass
├── bootstrap_contexts.py       # Bootstrap context containers
├── bootstrap_logger.py         # Early-stage logger before DI is ready
│
├── bootstrap/                  # Assembly of runtime components
│   ├── assembly/               # Low-level assembly: storage, checkpoint
│   ├── cli/                    # CLI-specific bootstrap: config, health, lock, metrics, noop, storage
│   └── runtime/                # Pipeline runtime assembly (see below)
│
├── factories/                  # Factory classes — one per concern
│   ├── datasource/             # DataSourceFactory, HttpClientFactory, adapter helpers
│   ├── dq/                     # DQServicesFactory — Bronze/Silver/Gold DQ wiring
│   ├── pipeline/               # GenericPipelineFactory, PipelineAssembler, runner assembly
│   ├── services/               # BaseServicesFactory, ServiceBundleDependencies, port factories
│   ├── storage/                # StorageFactory — Bronze/Silver/Gold/Merged writers
│   ├── transformer_factory.py  # TransformerBuilder
│   └── transformer_dependencies.py
│
├── providers/                  # ProviderRegistry — adapter creation per provider
│   ├── provider_registry.py    # Class-based registry with create_adapter()/create_data_source()
│   ├── registration.py         # register_all_providers()
│   ├── registration_biblio.py  # CrossRef, OpenAlex, PubMed, SemanticScholar
│   ├── registration_bio.py     # ChEMBL, PubChem, UniProt
│   └── _registration_contracts.py  # Leaf contracts for provider assembly support
│
├── runtime_builders/           # Late-stage runtime assembly
│   ├── runner_builder.py       # RunnerBuilder — assembles PipelineRunner
│   ├── inputs_resolver.py      # Resolves RunnerInputs from config
│   └── observability_builder.py # Wires logger + tracer + metrics
│
└── services/                   # Composition-level service wiring
    ├── effective_config_serializer.py  # Effective-config serialization helpers
    └── versioning.py           # Version info assembly
```

## Production run path (single story, #7606)

Prefer this production wiring path:

1. **CLI** builds an **explicit** `PipelineRegistry` via
   `interfaces/cli/registry_helpers.build_cli_registry()` (create +
   `register_all_pipelines(registry=…)`).
2. CLI orchestration resolves `PipelineRunnerService` through
   `composition.entrypoints` / `_services.get_pipeline_runner_service`.
3. Direct library callers use `composition.entrypoints.run_pipeline()` /
   `create_pipeline_runner()` with an explicit registry when possible.

`get_default_registry()` remains a **test-only compatibility** export.
Production composition must use a caller-provided registry or create a fresh
isolated registry; architecture guards reject production calls to the shared
compatibility instance.

## Key Entry Points

| What you want to do                             | Start here                                                                                                                           |
| ----------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| Run a single pipeline                           | `entrypoints.run_pipeline()`                                                                                                         |
| Look up a pipeline by provider+entity           | `registry_api.PipelineRegistry` (typed registry contract; first-party also uses `entrypoints`)                                      |
| Bootstrap a composite pipeline runtime          | `entrypoints.load_composite_config()` (stable access seam over `infrastructure.config`) + `entrypoints.bootstrap_composite_runner()` |
| Create an HTTP adapter for a provider           | `providers.provider_registry.ProviderRegistry`                                                                                       |
| Wire storage (Bronze/Silver/Gold)               | `factories/storage/storage_factory.StorageFactory`                                                                                   |
| Wire DQ services                                | `factories/dq/dq_services_factory.DQServicesFactory`                                                                                 |
| Assemble a full pipeline with runner            | `factories/pipeline/pipeline_assembler.GenericPipelineFactory`                                                                       |
| Bootstrap observability (logger+tracer+metrics) | `runtime_builders/observability_builder`                                                                                             |
| Bootstrap CLI commands                          | `bootstrap/cli/` (one module per concern)                                                                                            |

## bootstrap/runtime/ — Detailed Map

This is the most complex sub-package. It handles pipeline runtime assembly:

| Module                                   | Responsibility                                                            |
| ---------------------------------------- | ------------------------------------------------------------------------- |
| `assembly.py`                            | Pure functions: build RuntimeConfig, FilterConfig, ResolvedVacuumSettings |
| `pipeline.py`                            | Assemble BasePipeline subclass instances                                  |
| `runner.py`                              | Assemble PipelineRunner with all dependencies                             |
| `runner_assembly.py`                     | RunnerAssembly helpers                                                    |
| `runner_factory_builder_service.py`      | RunnerFactoryBuilder                                                      |
| `composite.py`                           | Composite pipeline assembly                                               |
| `composite_bootstrap_builders.py`        | Composite-specific builder helpers                                        |
| `composite_support_services_factory.py`  | Support services for composite pipelines                                  |
| `composite_filter_extraction_service.py` | Filter extraction for composites                                          |
| `composite_support_helpers.py`           | Utility helpers for composite support                                     |
| `composite_support_service_builders.py`  | Service builders for composite support                                    |
| `observability.py`                       | Observability bootstrap (logger, tracer, metrics)                         |
| `observability_bundle.py`                | ObservabilityBundle assembly                                              |
| `logger_bootstrap.py`                    | StructlogLogger bootstrap                                                 |
| `tracing_bootstrap.py`                   | OpenTelemetryTracer bootstrap                                             |
| `metrics_bootstrap.py`                   | PrometheusMetrics bootstrap                                               |
| `dq_bootstrap.py`                        | DQ services bootstrap                                                     |
| `classification_init.py`                 | Publication type classification init                                      |
| `runtime_basics.py`                      | CompositeRuntimeBasics container                                          |
| `pipeline_runner_service_bootstrap.py`   | PipelineRunnerService bootstrap                                           |

## factories/storage/ — Mixin Architecture

StorageFactory uses a mixin pattern to compose storage capabilities:

```
StorageFactory
  ├── _bronze.py          → BronzeWriter creation
  ├── _silver.py          → SilverWriter creation (Delta Lake)
  ├── _gold.py            → GoldWriter creation (Delta Lake)
  ├── _resilience.py      → Retry/resilience policies
  ├── _helpers.py         → Shared helper functions
  ├── clear_mixin.py      → clear_silver(), clear_gold() per run type
  ├── write_mixin.py      → write operations
  ├── health_mixin.py     → storage health checks
  ├── maintenance_mixin.py → vacuum, compaction
  ├── merged_mixin.py     → merged storage for composite pipelines
  ├── bundle.py           → StorageBundle (composite of all ports)
  ├── factory.py          → Core factory logic
  └── storage_factory.py  → Public StorageFactory class
```

## Architectural Rules

- **No business logic** in composition — only wiring
- **No imports from interfaces** — composition wires for interfaces, not the reverse
- **Factories only here** — `Factory.create()` calls must not appear in domain/application
- **Bounded module-level state only** — sanctioned process-local state is limited to the default pipeline/provider registry caches and narrow synchronization locks such as `_WORKFLOW_MEMORY_LOCK`; new globals require an explicit governance update.
- **Workflow time is explicit** — control-plane workflow services are wired with `ClockPort`/`SystemClock`, not ad hoc wall-clock calls inside composition.

## Primary API → factory / builder map

Package-root public seams only. Nested `factories/*` modules are implementation
detail unless re-exported here. **Freeze:** do not add a new package-root
`*_api.py` (or expand the sanctioned CLI `public-entrypoint` inventory past
scorecard `sanctioned_public_entrypoint_governance.public_entrypoint_count`,
currently **12**) without an explicit scorecard / inventory review
(`tests/architecture/test_composition_public_entrypoint_freeze.py`, issues #7708 / #7733).

| Public seam | Primary symbols / role | Factories / builders / internal owners |
| --- | --- | --- |
| `entrypoints` | First-party run/create/resolve, vacuum, contract migration, composite bootstrap | `_pipeline_execution`, `_service_registry`, `_services`, `composite_catalog`, `resources_runtime` |
| `execution_api` | External shim: `run_pipeline`, `create_pipeline_runner`, metrics helpers | `_pipeline_execution`, `_services.get_pipeline_runner_service` |
| `health_api` | External shim: health/quarantine getters | `_services`, `_resource_management` |
| `maintenance_api` | External shim: bronze cleanup, vacuum, contract migration | `_services` |
| `registry_api` | Typed `PipelineRegistry` contract | `factories/pipeline/registry_core` |
| `health_service_access` | First-party health/quarantine/bronze-cleanup | `_services`, `_resource_management` |
| `control_plane_service_access` | First-party workflow / forensic / ADR / config / lock / manifest | `_services`, `_workflow_services`, `bootstrap/cli` |
| `resources_runtime` | First-party archive/vacuum/lifecycle/checkpoint | `_resource_management` |
| `observability_runtime` | First-party metrics/audit/checkpoint inspection | `_services`, `bootstrap/cli` |

Supporting (not package-root freezes, still composition-owned):

| Area | Use for | Typical owners |
| --- | --- | --- |
| `factories/datasource/*` | HTTP adapters / data sources | `DataSourceFactory`, `HttpClientFactory`, provider helpers |
| `factories/storage/*` | Bronze/Silver/Gold/Merged writers | `StorageFactory` mixins + `bundle.StorageBundle` |
| `factories/dq/*` | DQ service wiring | `DQServicesFactory` |
| `factories/pipeline/*` | Full pipeline + runner assembly | `GenericPipelineFactory` / `PipelineAssembler`, `runner` assembly |
| `factories/services/*` | Port/service bundles | `BaseServicesFactory`, `port_factories` |
| `providers/*` | ProviderRegistry adapter creation | `registration_bio` / `registration_biblio` |
| `runtime_builders/*` | Late runner inputs, run manifest, observability bundle | `RunnerBuilder`, `inputs_resolver`, `observability_builder`, run-manifest builders |
| `bootstrap/runtime/*` | Pipeline/composite/observability runtime assembly | `pipeline`, `runner`, `composite*`, `*_bootstrap` |
| `bootstrap/cli/*` | CLI command service construction | one module per concern (config, health, lock, metrics, …) |

## Retained Entrypoint Policy

- First-party runtime uses `composition.entrypoints` plus owner modules
  (`health_service_access`, `control_plane_service_access`, CLI registry helpers).
  Bronze cleanup is on `health_service_access` (ops contract lives under
  `composition.contracts.health`); it is not re-exported from `entrypoints`.
- `execution_api`, `health_api`, and `maintenance_api` are logic-free lazy
  re-export shims for **external** compatibility only. Do not add new first-party
  imports of those modules in `src/`.
- `registry_api` is the typed `PipelineRegistry` contract (lazy re-export of
  `factories.pipeline.registry_core`). First-party registry consumers use this
  seam; do not import retired `composition.registry`.
- Retired package-root names `control_plane_api`, `resources_api`,
  `observability_api`, and `services_api` must stay absent.
- Internal modules such as `_pipeline_execution`, `_resource_management`, and
  `_services` stay private to `composition/` plus dedicated entrypoint tests.
- Do not add an 11th `*_api.py`. Architecture freeze is the four files above.
- Composite runtime flows should use `load_composite_config()` as the stable
  public access seam over the canonical owner
  `bioetl.infrastructure.config.composite_config_api`, and
  `bootstrap_composite_runner()` instead of inventing a parallel `run_composite()`
  wrapper at the `entrypoints.py` level.
