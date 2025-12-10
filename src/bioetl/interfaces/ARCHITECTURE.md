# Interfaces Layer Architecture

## Overview

The interfaces layer is the outermost layer of the application, responsible for:
- Adapting external requests (HTTP, CLI) to application use cases
- Presenting results in format appropriate for each interface
- Assembling dependencies via CompositionRoot

## Design Principles

### 1. Thin Adapters
Interfaces should only:
- Parse input (CLI args, HTTP requests)
- Call application layer (use cases)
- Format output (console, JSON responses)

❌ **Don't:**
```python
@app.command()
def run(pipeline_name: str):
    # Business logic in CLI - WRONG
    config = load_config(pipeline_name)
    orchestrator = PipelineOrchestrator(config)
    result = orchestrator.run()
```

✅ **Do:**
```python
@app.command()
def run(pipeline_name: str):
    # Delegate to use case
    use_case = get_run_pipeline_use_case()
    response = use_case.execute(RunPipelineRequest(pipeline_name))
    present_result(response)
```

### 2. Single Composition Root
All dependency creation happens in `CompositionRoot`:
```python
root = CompositionRoot()
container = root.create_pipeline_container(config)
logger = root.get_logger()
```

### 3. No Domain Logic
Interfaces must not:
- Validate business rules
- Transform domain entities
- Access repositories directly

### 4. Interface-Specific DTOs
Each interface has its own request/response models:
```python
# REST (Pydantic models)
class PipelineRunRequest(BaseModel):
    pipeline_name: str
    dry_run: bool = False

# Application (shared dataclasses)
@dataclass
class RunPipelineRequest:
    pipeline_name: str
    dry_run: bool = False
```

## Module Structure

```
interfaces/
├── __init__.py           # Public exports (CompositionRoot, ObservabilityStack, etc.)
├── composition_root.py   # Dependency assembly and wiring
├── bootstrap_factory.py  # ApplicationBootstrap factory functions
├── simple_container.py   # Legacy container (deprecated)
├── cli/
│   ├── __init__.py       # Exports: app
│   └── app.py            # Typer commands (list, validate, run, smoke_run)
├── rest/
│   ├── __init__.py       # Exports: create_rest_app, PipelineRunRequest/Response
│   └── server.py         # FastAPI endpoints (/pipelines/run)
└── monitoring/
    └── __init__.py       # Prometheus metrics export helpers
```

## Dependency Flow

```
[CLI/REST/Monitoring]
        ↓
[CompositionRoot] ← Single assembly point
        ↓
[Application Use Cases]
        ↓
[Domain / Infrastructure]
```

## Key Components

### CompositionRoot
The central dependency injection container. All concrete implementations are
instantiated here.

**Key methods:**
- `get_logger()` / `get_metrics()` - Observability components
- `get_observability_stack()` - Combined observability access
- `create_pipeline_container(config)` - Assemble full pipeline with all dependencies
- `create_config_loader()` - Configuration loading with schema validation
- `create_http_transport(provider, config)` - HTTP client with retry/metrics

**Usage patterns:**
```python
# Production (singleton)
from bioetl.interfaces import get_composition_root

root = get_composition_root()
container = root.create_pipeline_container(config)

# Testing (explicit mocks)
from bioetl.interfaces import CompositionRoot

root = CompositionRoot(
    logger=mock_logger,
    metrics=mock_metrics,
    schema_contract_provider=mock_provider,
)
```

### ObservabilityStack
Immutable container for observability dependencies:
```python
@dataclass(frozen=True)
class ObservabilityStack:
    logger: LoggingPortABC
    metrics: MetricsPortABC
```

### CLI Module (`cli/app.py`)
Typer-based CLI with commands:
- `list-pipelines` - Show available pipelines
- `validate-config` - Validate YAML configuration
- `run` - Execute a pipeline
- `smoke-run` - Quick test run (limit=10, dry_run=True)

### REST Module (`rest/server.py`)
FastAPI server with endpoints:
- `POST /pipelines/run` - Execute pipeline via HTTP

### Monitoring Module (`monitoring/__init__.py`)
Prometheus metrics integration:
- `create_prometheus_metrics_port()` - Factory for metrics port
- `start_metrics_server_once()` - Start HTTP metrics server

## Testing Guidelines

1. **Reset singletons between tests:**
   ```python
   from bioetl.interfaces import reset_composition_root

   @pytest.fixture(autouse=True)
   def reset_root():
       yield
       reset_composition_root()
   ```

2. **Inject mocks via CompositionRoot:**
   ```python
   root = CompositionRoot(
       logger=MockLogger(),
       metrics=MockMetrics(),
   )
   ```

3. **Don't test business logic here** - interfaces should be thin adapters,
   test the use cases in the application layer instead.

## See Also

- `bioetl/application/ARCHITECTURE.md` - Application layer architecture
- `bioetl/domain/ARCHITECTURE.md` - Domain layer architecture
- `bioetl/infrastructure/ARCHITECTURE.md` - Infrastructure layer architecture
