# Infrastructure Layer Architecture

This document describes the architectural rules and allowed dependencies for the
infrastructure layer in the BioETL project.

## Layer Dependency Rules

The infrastructure layer implements technical concerns (HTTP clients, file I/O,
database access, etc.) and must follow strict dependency rules to maintain clean
architecture.

### Allowed Domain Imports

Infrastructure layer **MAY** import from the following domain modules:

| Module Pattern | Description |
|----------------|-------------|
| `domain.ports.*` | Port interfaces (ABCs) defining contracts |
| `domain.configs.*` | Configuration models (Pydantic models) |
| `domain.errors.*` | Exception classes |
| `domain.observability.*` | Logging/metrics ports and contracts |
| `domain.clients.base.contracts` | Base client contracts |
| `domain.clients.contracts` | Client-specific contracts |
| `domain.transform.contracts` | Transformation contracts |
| `domain.transform.merge` | Deep merge utilities |
| `domain.transform.normalizers` | Normalization utilities |
| `domain.transform.serializers` | Serialization utilities |
| `domain.validation` | Validation contracts and types |
| `domain.pipelines.contracts` | Pipeline contracts |
| `domain.provider_registry` | Provider registry types |
| `domain.providers` | Provider definitions |
| `domain.models` | Domain models (RunContext, etc.) |

### Forbidden Domain Imports

Infrastructure layer **MUST NOT** import at module level:

| Module Pattern | Reason | Alternative |
|----------------|--------|-------------|
| `domain.schemas.chembl.raw_models.*` | Domain-specific data models | Use application layer mappers |
| `domain.schemas.pipeline_contracts.*` | Pipeline contracts | Use `SchemaContractProviderABC` port |
| `domain.schemas.registry` (direct class import) | Implementation detail | Use `get_default_schema_registry()` via lazy import or DI |

### Allowed Import Patterns

When infrastructure needs to reference domain schemas, use these patterns:

#### 1. TYPE_CHECKING for Type Hints

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.domain.schemas.chembl.raw_models import ActivityRawModel

def process(data: "ActivityRawModel") -> None:
    ...
```

#### 2. Lazy Import for Backward Compatibility

```python
def deprecated_factory() -> SomeType:
    """Deprecated factory with lazy import."""
    warnings.warn("Use new_factory() instead", DeprecationWarning)
    # Lazy import inside function - acceptable for backward compatibility
    from bioetl.domain.schemas.chembl.raw_models import ActivityRawModel
    return SomeType(ActivityRawModel)
```

#### 3. Dependency Injection

```python
class MyFactory:
    def __init__(
        self,
        schema_provider_factory: Callable[[], SchemaProviderABC] | None = None,
    ) -> None:
        self._schema_provider_factory = schema_provider_factory

    def create(self) -> SchemaProviderABC:
        if self._schema_provider_factory is not None:
            return self._schema_provider_factory()
        # Lazy import as fallback
        from bioetl.domain.schemas.registry import get_default_schema_registry
        return get_default_schema_registry()
```

## Architectural Tests

These rules are enforced by automated tests in:

- `tests/architecture/test_layer_dependencies.py`

Key tests:

| Test | Description |
|------|-------------|
| `test_domain_has_no_outer_dependencies` | Domain must not depend on infrastructure or application |
| `test_infrastructure_does_not_depend_on_application` | Infrastructure must not import application layer |
| `test_infrastructure_does_not_import_domain_schemas_at_module_level` | Enforces forbidden domain schema imports |
| `test_infrastructure_impls_are_not_cross_used` | Implementation modules must not cross-reference |

## Rationale

These rules support:

1. **Testability**: Infrastructure can be easily mocked/stubbed via ports
2. **Flexibility**: Domain schemas can evolve without breaking infrastructure
3. **Separation of Concerns**: Business logic (domain) stays separate from technical details (infrastructure)
4. **Dependency Inversion**: High-level modules (domain) don't depend on low-level modules (infrastructure)

## Migration Guide

If you find code that violates these rules:

1. **Module-level schema import** -> Move to `TYPE_CHECKING` block or use lazy import
2. **Direct `SchemaRegistry()` creation** -> Use `get_default_schema_registry()` or inject via constructor
3. **Runtime schema usage** -> Create a port/ABC in domain and implement in infrastructure
