# Registry Pattern

All registries in BioETL follow the unified `RegistryProtocol` for consistent API across the codebase.

## Standard Methods

| Method | Description |
|--------|-------------|
| `register(key, value)` | Register an item |
| `get(key)` | Get item (raises `KeyError` if missing) |
| `list_keys()` | List all registered keys |
| `contains(key)` | Check if key is registered |
| `clear()` | Clear all registrations (testing only) |

## Implementations

### PipelineRegistry

Registry for pipeline factories. Located in `src/bioetl/composition/registry.py`.

```python
from bioetl.composition.registry import PipelineRegistry

# List all registered pipelines
pipelines = PipelineRegistry.list_keys()

# Check if pipeline exists
if PipelineRegistry.contains("chembl_activity"):
    definition = PipelineRegistry.get("chembl_activity")
```

### DataSourceRegistry

Registry for data source creators. Located in `src/bioetl/composition/factories/data_source_registry.py`.

```python
from bioetl.composition.factories.data_source_registry import DataSourceRegistry

# List all registered providers
providers = DataSourceRegistry.list_keys()

# Check if provider exists
if DataSourceRegistry.contains("chembl"):
    creator = DataSourceRegistry.get("chembl")
```

## Legacy Aliases

For backward compatibility, the following legacy methods are available:

| Registry | Legacy Method | Unified Method |
|----------|---------------|----------------|
| `PipelineRegistry` | `register_factory(factory)` | `register(key, factory)` |
| `PipelineRegistry` | `list_pipelines()` | `list_keys()` |
| `DataSourceRegistry` | `list_providers()` | `list_keys()` |

## Protocol Definition

The base protocol is defined in `src/bioetl/composition/base_registry.py`:

```python
from typing import Protocol, TypeVar, runtime_checkable

K = TypeVar("K")  # Key type
V = TypeVar("V")  # Value type

@runtime_checkable
class RegistryProtocol(Protocol[K, V]):
    @classmethod
    def register(cls, key: K, value: V) -> None: ...

    @classmethod
    def get(cls, key: K) -> V: ...

    @classmethod
    def list_keys(cls) -> list[K]: ...

    @classmethod
    def contains(cls, key: K) -> bool: ...

    @classmethod
    def clear(cls) -> None: ...
```

## Error Handling

All registries raise `KeyError` when accessing non-existent keys:

```python
try:
    creator = DataSourceRegistry.get("unknown_provider")
except KeyError as e:
    print(f"Provider not found: {e}")
```

**Note:** `PipelineRegistry.get()` raises `RuntimeError` if the registry is empty (registration not called), and `ValueError` for unknown pipeline names. This is for backward compatibility and provides more helpful error messages.

## Testing

When writing tests that modify registries, use the `clear()` method in teardown:

```python
@pytest.fixture(autouse=True)
def reset_registries():
    backup = PipelineRegistry._registry.copy()
    yield
    PipelineRegistry._registry.clear()
    PipelineRegistry._registry.update(backup)
```
