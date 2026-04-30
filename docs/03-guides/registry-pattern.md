______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-29'

______________________________________________________________________

# Registry Pattern

BioETL uses several registry-style APIs, but they do not all have the same
runtime shape.

- `PipelineRegistry` is an instance-based registry in
  `src/bioetl/composition/registry.py`.
- `ProviderRegistry` is an instance-scoped provider registry in
  `src/bioetl/composition/providers/provider_registry.py`, with a shared
  default-registry compatibility facade exposed through class-level methods.
- `get_data_source_creator()` and `DataSourceFactory` are the canonical data-source
  assembly path over `ProviderRegistry`.

## Canonical Surfaces

| Surface                                           | Kind                                   | Canonical Import                                              | Notes                                                                                                       |
| ------------------------------------------------- | -------------------------------------- | ------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| `PipelineRegistry`                                | Instance-based                         | `bioetl.composition.registry`                                 | Prefer `create_registry()` for tests and isolated flows.                                                    |
| `ProviderRegistry`                                | Instance-scoped + compatibility facade | `bioetl.composition.providers`                                | Prefer explicit instances for isolated/local seams; class-level methods target the shared default registry. |
| `get_data_source_creator()` / `DataSourceFactory` | Canonical creator path                 | `bioetl.composition.factories.datasource.data_source_factory` | Preferred for data-source assembly; backed by `ProviderRegistry`.                                           |

Governance status for the two transition-heavy surfaces:

- `bioetl.composition.registry` is currently a `mixed-module` (canonical instance API +
  transitional shared default-registry compatibility).
- pipeline config loading is now canonical through `bioetl.infrastructure.config` and
  `bioetl.infrastructure.config.pipeline_config_api`; the historical
  `bioetl.infrastructure.config_loader` shim has been removed.

See the curated ledger in
[`docs/02-architecture/07-compatibility-facade-inventory.md`](../02-architecture/07-compatibility-facade-inventory.md)
for status semantics, allowed call sites, and exit criteria.

## Common Operations

| Goal     | `PipelineRegistry`                                                        | `ProviderRegistry`                        | Data-source assembly                             |
| -------- | ------------------------------------------------------------------------- | ----------------------------------------- | ------------------------------------------------ |
| Register | `registry.register(key, factory)` or `registry.register_factory(factory)` | `ProviderRegistry.register(name, config)` | Register provider config in `ProviderRegistry`   |
| Get      | `registry.get(name)`                                                      | `ProviderRegistry.get(name)`              | `get_data_source_creator(name)`                  |
| List     | `registry.list_keys()` or `registry.list_pipelines()`                     | `ProviderRegistry.list_providers()`       | `DataSourceFactory.list_providers()`             |
| Contains | `registry.contains(name)`                                                 | `ProviderRegistry.is_registered(name)`    | `ProviderRegistry.has_data_source_creator(name)` |
| Create   | —                                                                         | `ProviderRegistry.create_adapter(...)`    | `DataSourceFactory.create(...)`                  |

## PipelineRegistry

`PipelineRegistry` is instance-based. Use an explicit registry instance rather
than calling methods on the class itself.

```python
from bioetl.composition.factories.pipeline.registry import register_all_pipelines
from bioetl.composition import create_registry

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

| Legacy Method               | Canonical Method                           |
| --------------------------- | ------------------------------------------ |
| `register_factory(factory)` | `register(factory.pipeline_name, factory)` |
| `list_pipelines()`          | `list_keys()`                              |

## ProviderRegistry

`ProviderRegistry` is the canonical registry for provider configuration and
provider-backed creation. The underlying model is instance-scoped:
`create_provider_registry()` creates an isolated registry, and
`ensure_provider_registry_ready(registry)` hydrates it before use. Class-level
methods remain an approved compatibility facade over the shared default
registry.

Runtime/bootstrap code should call `ensure_providers_loaded()` instead of
calling the registration function directly. The loader is the lifecycle
boundary for shared provider registration state: repeated bootstrap calls stay
idempotent, and stale `_loaded` state is repaired if isolated flows or tests
clear `ProviderRegistry` after an earlier successful load.

```python
from bioetl.composition.providers import (
    ProviderRegistry,
    create_provider_registry,
    ensure_provider_registry_ready,
)

isolated_registry = create_provider_registry()
isolated_registry = ensure_provider_registry_ready(isolated_registry)
providers = isolated_registry.list_providers()

# Shared default-registry compatibility access remains available:
shared_providers = ProviderRegistry.list_providers()

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

## Canonical Datasource Creator Path

`get_data_source_creator()` is the canonical provider-bound creator seam. New
code should use `get_data_source_creator()`, `DataSourceFactory`, or
`ProviderRegistry`.

```python
from bioetl.composition.factories.datasource.data_source_factory import (
    DataSourceFactory,
    get_data_source_creator,
)

providers = DataSourceFactory.list_providers()
creator = get_data_source_creator("chembl")
```

Register new providers through the composition-owned registration flow
(`register_all_providers()` / registration helpers over a target registry)
rather than introducing ad-hoc datasource registry facades.

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
- `get_data_source_creator()` raises `KeyError` for an unknown provider

Write call sites accordingly instead of assuming every registry raises the same
exception type.

## Testing

For tests, prefer isolated registries created with `create_registry()` instead
of mutating private registry state.

```python
import pytest

from bioetl.composition.factories.pipeline.registry import register_all_pipelines
from bioetl.composition import create_registry


@pytest.fixture
def isolated_registry():
    registry = create_registry()
    register_all_pipelines(registry=registry)
    return registry
```

This keeps tests independent and avoids coupling to private attributes such as
`_registry`.
