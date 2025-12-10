# Contributing to BioETL

## Class Naming Convention

This project follows a strict naming convention for classes to ensure consistency and clarity.

### Rules

#### 1. `*Impl` Suffix - Interface Implementations

Use the `Impl` suffix **only** for classes that implement an abstract base class (ABC) interface.

**Correct:**
```python
class ChemblHttpClientImpl(DataClientABC):
    """Implements DataClientABC for ChEMBL API."""
    pass

class StructuredLoggerImpl(LoggingPortABC):
    """Implements LoggingPortABC using structlog."""
    pass
```

**Incorrect:**
```python
# Wrong: No ABC interface exists
class BaseWriterImpl:  # Should be: BaseWriter
    pass
```

#### 2. `*Factory` Suffix - Factory Classes

Use the `Factory` suffix for classes that create other objects. Factories may or may not have an ABC interface.

```python
class PipelineHookFactory:
    """Creates pipeline hook instances."""

    @staticmethod
    def create_logging_hook() -> PipelineHookABC:
        return LoggingPipelineHookImpl()
```

#### 3. `*ABC` Suffix - Abstract Base Classes

Use the `ABC` suffix for abstract base classes that define interfaces.

```python
from abc import ABC, abstractmethod

class DataClientABC(ABC):
    """Abstract interface for data clients."""

    @abstractmethod
    def fetch(self, url: str) -> dict:
        pass
```

#### 4. No Suffix - Standalone Classes

Classes without abstraction should have no suffix.

```python
class HttpTransport:
    """HTTP transport utility (no ABC interface)."""
    pass

class CircuitBreaker:
    """Circuit breaker pattern implementation."""
    pass
```

### Summary Table

| Suffix | When to Use | Example |
|--------|-------------|---------|
| `*Impl` | Implements an `*ABC` interface | `ChemblHttpClientImpl(DataClientABC)` |
| `*Factory` | Creates other objects | `PipelineHookFactory` |
| `*ABC` | Defines an abstract interface | `DataClientABC(ABC)` |
| (none) | Standalone class without abstraction | `HttpTransport` |

### Backward Compatibility

When renaming classes, always provide a deprecated alias:

```python
class NewClassName:
    """The actual implementation."""
    pass

# Deprecated alias for backward compatibility (will be removed in next major version)
OldClassName = NewClassName

__all__ = ["NewClassName", "OldClassName"]
```

### Breaking Changes

Class renames are breaking changes and should be:
1. Planned for major releases
2. Documented in CHANGELOG
3. Accompanied by deprecated aliases for one major version

## Code Style

- Follow PEP 8
- Use type hints
- Write docstrings for public APIs
- Keep functions focused and small

## Testing

- Write tests for new functionality
- Ensure all tests pass before submitting PR
- Aim for high test coverage

## Pull Request Process

1. Create a feature branch
2. Make your changes
3. Write/update tests
4. Update documentation if needed
5. Submit PR with clear description
