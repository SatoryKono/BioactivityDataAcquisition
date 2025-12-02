# Adding a New ABC

How to add a new ABC/Default/Impl following the three-layer pattern.

## Three-Layer Pattern

BioETL uses a mandatory three-layer pattern:

1. **ABC (Contract)**: `src/bioetl/clients/<domain>/contracts.py` or `base/contracts.py`
2. **Default Factory**: `src/bioetl/clients/<domain>/factories.py`, function `default_<domain>_<entity>()`
3. **Impl**: `src/bioetl/clients/<domain>/impl/`, classes with `Impl` suffix

## Steps

### 1. Create ABC

Define the abstract base class:

```python
from abc import ABC, abstractmethod

class NewComponentABC(ABC):
    """Brief description.
    
    Public interface:
    - method1(): description
    - method2(): description
    
    Default factory: default_new_component()
    Impl: NewComponentImpl
    """
    
    @abstractmethod
    def method1(self) -> None:
        """Method description."""
        pass
```

### 2. Create Default Factory

Create a default factory (can be a stub if no implementation exists yet):

```python
def default_new_component() -> NewComponentABC:
    """Default factory for NewComponentABC."""
    # Return default implementation or raise NotImplementedError
    raise NotImplementedError("No default implementation available")
```

### 3. Create Implementation

Create concrete implementation:

```python
class NewComponentImpl(NewComponentABC):
    def method1(self) -> None:
        # Implementation
        pass
```

### 4. Update Registries

Update machine-readable registries:

- `src/bioetl/clients/base/abc_registry.yaml` — ABC registry
- `src/bioetl/clients/base/abc_impls.yaml` — Default/Impl mapping

### 5. Create Documentation

Create documentation file:

- `docs/reference/abc/NN-new-component-abc.md` (kebab-case, numbered prefix)
- Update `docs/reference/abc/index.md`

## Rules

- **ABC is mandatory** when creating a new contract
- **Default factory is mandatory** (can be stub with `NotImplementedError`)
- **Impl is optional** initially, can be added later
- **Documentation is mandatory** for all ABCs

## Related Documentation

- **[ABC Index](../reference/abc/index.md)** — Catalog of all ABCs
- **[Project Rules](../project/rules-summary.md)** — Full naming and structure rules

