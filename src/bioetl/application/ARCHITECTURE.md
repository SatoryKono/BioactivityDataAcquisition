# Application Layer Architecture

This document describes the architectural rules and allowed dependencies for the
application layer in the BioETL project.

## Overview

The application layer orchestrates domain logic and coordinates use cases. It is
responsible for:
- Assembling pipelines via dependency injection containers
- Orchestrating pipeline execution flow
- Providing application-level services (schema bootstrap, config resolution)
- Implementing mappers between external data and domain models

## Layer Dependency Rules

The application layer acts as the bridge between interfaces and domain layers.
It coordinates domain services but must not contain business logic or infrastructure
implementation details.

### Allowed Domain Imports

Application layer **MAY** import from the following domain modules:

| Module Pattern | Description |
|----------------|-------------|
| `domain.ports.*` | Port interfaces (ABCs) defining contracts |
| `domain.configs.*` | Configuration models (Pydantic models) |
| `domain.errors.*` | Exception classes |
| `domain.observability.*` | Logging/metrics ports and contracts |
| `domain.transform.contracts` | Transformation contracts |
| `domain.validation` | Validation contracts and types |
| `domain.pipelines.contracts` | Pipeline contracts |
| `domain.provider_registry` | Provider registry types |
| `domain.providers` | Provider definitions |
| `domain.models` | Domain models (RunContext, RunResult, etc.) |
| `domain.record_source` | Record source contracts |
| `domain.clients.base.contracts` | Base client contracts |
| `domain.clients.base.output.contracts` | Output contracts (RunMetadataBuilderProtocol) |

### Forbidden Imports

Application layer **MUST NOT** import at module level:

| Module Pattern | Reason | Alternative |
|----------------|--------|-------------|
| `domain.schemas.chembl.raw_models.*` | Raw API response models | Use application mappers (`application.mappers`) |
| `domain.schemas.registry` (direct class) | Implementation detail | Use `SchemaContractProviderABC` port |
| `infrastructure.*` | Infrastructure implementations | Inject via dependency injection from interfaces layer |

### Why These Rules?

1. **Raw models isolation**: `domain.schemas.chembl.raw_models` contains models
   specific to ChEMBL API response structure. Application layer should work with
   domain entities, not raw API payloads. Mappers handle the translation.

2. **Schema registry indirection**: Direct use of `SchemaRegistry` couples
   application to a specific implementation. Use `SchemaContractProviderABC`
   to maintain testability and flexibility.

3. **Infrastructure isolation**: Application layer must not know how HTTP requests
   are made, how files are written, etc. These details are injected from the
   interfaces layer via `CompositionRoot`.

## Allowed Import Patterns

When application code needs types from forbidden modules, use these patterns:

### 1. TYPE_CHECKING for Type Hints

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.domain.schemas.chembl.raw_models import ActivityRawModel

def map_activity(data: "ActivityRawModel") -> ActivityEntity:
    ...
```

### 2. Lazy Import in Mappers

```python
class ChemblRecordMapper:
    """Mapper that bridges raw API models to domain entities."""

    def map_to_domain(self, raw_data: dict) -> DomainEntity:
        # Lazy import inside method - acceptable for mappers
        from bioetl.domain.schemas.chembl.raw_models import ActivityRawModel

        raw_model = ActivityRawModel.model_validate(raw_data)
        return self._convert(raw_model)
```

### 3. Dependency Injection for Infrastructure

```python
class PipelineContainer:
    """Container that receives infrastructure via DI."""

    def __init__(
        self,
        config: PipelineConfig,
        *,
        http_transport_factory: Callable[[], HttpTransportABC] | None = None,
        file_writer_factory: Callable[[], FileWriterABC] | None = None,
    ) -> None:
        self._config = config
        # Infrastructure injected, not imported
        self._http_transport_factory = http_transport_factory
        self._file_writer_factory = file_writer_factory

    def get_http_transport(self) -> HttpTransportABC:
        if self._http_transport_factory is None:
            raise RuntimeError("HTTP transport not configured")
        return self._http_transport_factory()
```

### 4. Factory Callbacks for Deferred Resolution

```python
class ApplicationBootstrap:
    """Bootstrap that uses factories for infrastructure integration."""

    def __init__(
        self,
        *,
        config_loader_factory: ConfigLoaderFactory | None = None,
        provider_injector: ProviderInjector | None = None,
    ) -> None:
        # Factories allow infrastructure to be wired later
        self._config_loader_factory = config_loader_factory
        self._provider_injector = provider_injector
```

## Public API

The application layer exports these components via `bioetl.application`:

| Component | Module | Description |
|-----------|--------|-------------|
| `PipelineContainer` | `container.py` | Dependency injection container for pipelines |
| `PipelineOrchestrator` | `orchestrator.py` | High-level pipeline execution coordinator |
| `PipelineContainerABC` | `contracts.py` | Abstract base class for containers |
| `PipelineFactoryABC` | `contracts.py` | Abstract factory for creating pipelines |
| `ApplicationBootstrap` | `bootstrap.py` | Central entry point for application initialization |
| `ApplicationContext` | `bootstrap.py` | Context of an initialized application |

### Additional Submodules

| Submodule | Purpose |
|-----------|---------|
| `application.config` | Runtime configuration resolution |
| `application.mappers` | Data mappers (raw models -> domain entities) |
| `application.pipelines` | Pipeline implementations and factories |
| `application.services` | Application services (schema bootstrap, contract provider) |
| `application.use_cases` | Use case implementations |
| `application.factories` | Factory implementations for services |

## Testing Guidelines

### 1. Mock Infrastructure Dependencies

Application tests should mock infrastructure, not import it:

```python
def test_orchestrator_runs_pipeline():
    # Create mock container
    mock_container = Mock(spec=PipelineContainerABC)
    mock_container.config = sample_config
    mock_container.get_logger.return_value = MockLogger()

    # Inject mock via factory
    orchestrator = PipelineOrchestrator(
        "test_pipeline",
        sample_config,
        container_factory=lambda *args, **kwargs: mock_container,
        provider_registry=mock_registry,
    )

    result = orchestrator.run_pipeline(dry_run=True)
    assert result.success
```

### 2. Use ApplicationBootstrap for Integration Tests

```python
def test_bootstrap_initializes_services():
    # Pure application layer test - no infrastructure
    bootstrap = ApplicationBootstrap()
    context = bootstrap.start()

    assert context.schema_provider is not None
    assert context.contract_provider is not None

    bootstrap.shutdown()
```

### 3. Test Mappers with Raw Model Fixtures

```python
def test_activity_mapper():
    # Mapper tests may use raw models directly
    from bioetl.application.mappers.chembl import ChemblRecordMapper

    mapper = ChemblRecordMapper()
    raw_data = load_fixture("chembl_activity_response.json")

    result = mapper.map_to_domain(raw_data)

    assert result.activity_id == "CHEMBL12345"
```

### 4. Avoid Testing Business Logic in Application Layer

Application layer should only coordinate - test business logic in domain layer:

```python
# Good: Test coordination
def test_orchestrator_calls_stages_in_order():
    ...

# Bad: Test business logic here (belongs in domain)
def test_validation_rules():  # <- Move to domain tests
    ...
```

## Architectural Tests

These rules are enforced by automated tests in:

- `tests/architecture/test_layer_dependencies.py`

Key tests:

| Test | Description |
|------|-------------|
| `test_domain_has_no_outer_dependencies` | Domain must not depend on infrastructure or application |
| `test_application_does_not_depend_on_interfaces` | Application must not import interfaces layer |
| `test_application_uses_ports_not_implementations` | Application should use ABCs, not concrete classes |

## Module Structure

```
application/
├── __init__.py              # Public exports
├── ARCHITECTURE.md          # This file
├── bootstrap.py             # ApplicationBootstrap, ApplicationContext
├── container.py             # PipelineContainer implementation
├── contracts.py             # PipelineContainerABC, PipelineFactoryABC
├── executor.py              # Pipeline execution utilities
├── memory_registry.py       # In-memory provider registry
├── orchestrator.py          # PipelineOrchestrator
├── config/
│   ├── resolution.py        # Config resolution utilities
│   └── runtime.py           # Runtime configuration
├── factories/
│   ├── hooks.py             # Hook factories
│   ├── noop.py              # No-op implementations
│   ├── record_source.py     # Record source factories
│   ├── runtime_factory.py   # Runtime factory
│   ├── service_factory.py   # Service factories
│   ├── services.py          # Service implementations
│   └── transform_factory.py # Transform factories
├── mappers/
│   ├── contracts.py         # Mapper contracts
│   └── chembl/              # ChEMBL-specific mappers
├── pipelines/
│   ├── base.py              # PipelineBase
│   ├── contracts.py         # Pipeline contracts
│   ├── registry.py          # Pipeline factory registry
│   └── chembl/              # ChEMBL pipeline implementations
├── services/
│   ├── schema_bootstrap.py      # Schema initialization
│   └── schema_contract_provider.py  # Contract provider impl
├── sources/
│   └── api_record_source.py # API record source
└── use_cases/
    └── run_pipeline.py      # Run pipeline use case
```

## See Also

- `bioetl/interfaces/ARCHITECTURE.md` - Interfaces layer architecture
- `bioetl/infrastructure/ARCHITECTURE.md` - Infrastructure layer architecture
- `tests/architecture/test_layer_dependencies.py` - Architectural enforcement tests
