# Composition Layer — Navigation Map

The composition layer is the **only place** where concrete implementations are wired
together. No business logic lives here — only assembly, factory, and registration code.

## Package Structure

```
composition/
├── entrypoints.py              # Retained execution-first seam (+ deprecated legacy lookups)
├── execution_api.py            # Canonical execution API
├── control_plane_api.py        # Canonical control-plane service API
├── health_api.py               # Canonical health/quarantine service API
├── maintenance_api.py          # Canonical maintenance service API
├── services_api.py             # Legacy umbrella service-bootstrap API
├── resources_api.py            # Canonical resource-management API
├── registry.py                 # PipelineRegistry — maps (provider, entity) → pipeline class
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
├── monitoring/                 # Composition-local monitoring support
│   └── deprecation_tracker.py  # Tracks deprecated surface usage during runtime assembly
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

## Key Entry Points

| What you want to do                             | Start here                                                                                                                           |
| ----------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| Run a single pipeline                           | `entrypoints.run_pipeline()`                                                                                                         |
| Bootstrap a composite pipeline runtime          | `entrypoints.load_composite_config()` (stable access seam over `infrastructure.config`) + `entrypoints.bootstrap_composite_runner()` |
| Look up a pipeline by provider+entity           | `registry.PipelineRegistry`                                                                                                          |
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
- **Module-level singletons OK** — `_default_registry` is the only approved module-level instance

## Retained Entrypoint Policy

- `composition.entrypoints` is a sanctioned public seam with execution-focused `__all__`.
- Runtime execution helpers should come from `composition.execution_api`.
- Health and quarantine helpers should come from `composition.health_api`.
- Maintenance helpers should come from `composition.maintenance_api`.
- Administrative and inspection helpers should come from
  `composition.control_plane_api`.
- Resource helpers should come from `composition.resources_api`.
- Registry consumers should use `composition.registry_api` instead of importing
  the `composition` package root.
- Interfaces must not import `composition.registry` or
  `composition.registry_default` directly; `composition.registry_api` is the
  only sanctioned registry seam outside composition internals.
- Pipeline registration from interface entrypoints must also go through
  `composition.registry_api.register_all_pipelines`, not
  `composition.factories.pipeline.registry`.
- Internal modules such as `_pipeline_execution`, `_resource_management`, and `_services`
  stay private to `composition/` plus dedicated entrypoint tests.
- New first-party integration surfaces SHOULD prefer specialized `*_api.py`
  seams over growing `entrypoints.py` or importing `composition.services_api`;
  expand `entrypoints.py` only for explicit backward-compatibility reasons.
- Composite runtime flows should use `load_composite_config()` as the stable
  public access seam over the canonical owner
  `bioetl.infrastructure.config.composite_config_api`, and
  `bootstrap_composite_runner()` instead of inventing a parallel `run_composite()`
  wrapper at the `entrypoints.py` level.
