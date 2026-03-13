# Registry Pattern

BioETL uses several registry-style APIs, but they do not all have the same
runtime shape.

- `PipelineRegistry` is an instance-based registry in
  `src/bioetl/composition/registry.py`.
- `ProviderRegistry` is the canonical class-based provider registry in
  `src/bioetl/composition/providers/provider_registry.py`.
- `DataSourceRegistry` is a backward-compatible facade over `ProviderRegistry`
  in `src/bioetl/composition/factories/datasource/factory.py`.

## Canonical Surfaces

| Surface | Kind | Canonical Import | Notes |
|---------|------|------------------|-------|
| `PipelineRegistry` | Instance-based | `bioetl.composition.registry` | Prefer `create_registry()` for tests and isolated flows. |
| `ProviderRegistry` | Class-based | `bioetl.composition.providers` | Canonical registry for provider metadata and creation. |
| `DataSourceRegistry` | Compatibility facade | `bioetl.composition.factories.datasource.factory` | Keep for compatibility; new registrations go through `ProviderRegistry`. |

## Common Operations

| Goal | `PipelineRegistry` | `ProviderRegistry` | `DataSourceRegistry` |
|------|--------------------|--------------------|----------------------|
| Register | `registry.register(key, factory)` or `registry.register_factory(factory)` | `ProviderRegistry.register(name, config)` | Removed; use `ProviderRegistry.register(...)` |
| Get | `registry.get(name)` | `ProviderRegistry.get(name)` | `DataSourceRegistry.get(name)` |
| List | `registry.list_keys()` or `registry.list_pipelines()` | `ProviderRegistry.list_providers()` | `DataSourceRegistry.list_keys()` or `list_providers()` |
| Contains | `registry.contains(name)` | `ProviderRegistry.is_registered(name)` | `DataSourceRegistry.contains(name)` |
| Clear (tests only) | `registry.clear()` | `ProviderRegistry.clear()` | `DataSourceRegistry.clear()` clears only its local facade cache |

## PipelineRegistry

`PipelineRegistry` is instance-based. Use an explicit registry instance rather
than calling methods on the class itself.

```python
from bioetl.composition.factories.pipeline.registry import register_all_pipelines
from bioetl.composition.registry import create_registry

registry = create_registry()
register_all_pipelines(registry=registry)

pipelines = registry.list_keys()

if registry.contains("chembl_activity"):
    definition = registry.get("chembl_activity")
    factory = definition.factory
```

Use `get_default_registry()` only when you intentionally need the shared
composition-layer compatibility instance.

```python
from bioetl.composition.registry import get_default_registry

registry = get_default_registry()
```

Canonical runtime/bootstrap assembly paths do not rely on that shared
compatibility instance anymore. `bootstrap_pipeline_runner()`,
`build_pipeline_runner()`, and `RunnerFactory` now create or receive an explicit
runtime `PipelineRegistry` instance and pass it through the execution path.

### Legacy Aliases

`PipelineRegistry` still exposes compatibility aliases:

| Legacy Method | Canonical Method |
|---------------|------------------|
| `register_factory(factory)` | `register(factory.pipeline_name, factory)` |
| `list_pipelines()` | `list_keys()` |

## ProviderRegistry

`ProviderRegistry` is the canonical registry for provider configuration and
provider-backed creation.

Runtime/bootstrap code should call `ensure_providers_loaded()` instead of
calling `register_all_providers()` directly. The loader is the lifecycle
boundary for shared provider registration state: repeated bootstrap calls stay
idempotent, and stale `_loaded` state is repaired if isolated flows or tests
clear `ProviderRegistry` after an earlier successful load.

```python
from bioetl.composition.providers import ProviderRegistry

providers = ProviderRegistry.list_providers()

if ProviderRegistry.is_registered("chembl"):
    config = ProviderRegistry.get("chembl")
```

When a provider exposes a `data_source_creator`, `ProviderRegistry` can also
create a configured data source directly:

```python
from bioetl.composition.providers import ProviderRegistry

data_source = ProviderRegistry.create_data_source(
    "chembl",
    settings=settings,
    pipeline_config=pipeline_config,
    logger=logger,
)
```

## DataSourceRegistry

`DataSourceRegistry` remains available for backward compatibility, but new code
should prefer `ProviderRegistry`.

```python
from bioetl.composition.factories.datasource.factory import DataSourceRegistry

providers = DataSourceRegistry.list_providers()

if DataSourceRegistry.contains("chembl"):
    creator = DataSourceRegistry.get("chembl")
```

`DataSourceRegistry.register()` is no longer part of the supported API. Register
new providers through `ProviderRegistry.register(...)`.

The broader module-level status and deprecation plan for compatibility facades
is tracked in
[`docs/02-architecture/07-compatibility-facade-inventory.md`](../02-architecture/07-compatibility-facade-inventory.md).

## Protocols And Types

There is no generic `RegistryProtocol` defined in
`src/bioetl/composition/registry.py`.

The current canonical protocol surfaces are:

- `PipelineRegistryPort` and `RegistryAccessorPort` in
  `src/bioetl/domain/ports/runtime/registry_port.py`
- public re-exports in `src/bioetl/composition/types.py`

These protocols are used for dependency inversion around pipeline-registry
access, while `PipelineRegistry` provides the concrete composition-layer
implementation.

## Error Handling

Registry error behavior is not fully uniform:

- `PipelineRegistry.get()` raises:
  - `RuntimeError` when the registry is empty
  - `ValueError` when the requested pipeline name is unknown
- `ProviderRegistry.get()` raises `KeyError` for an unknown provider
- `DataSourceRegistry.get()` raises `KeyError` for an unknown provider

Write call sites accordingly instead of assuming every registry raises the same
exception type.

## Testing

For tests, prefer isolated registries created with `create_registry()` instead
of mutating private registry state.

```python
import pytest

from bioetl.composition.factories.pipeline.registry import register_all_pipelines
from bioetl.composition.registry import create_registry


@pytest.fixture
def isolated_registry():
    registry = create_registry()
    register_all_pipelines(registry=registry)
    return registry
```

This keeps tests independent and avoids coupling to private attributes such as
`_registry`.
