# Domain Layer Architecture

This document describes the architectural rules and conventions for the `bioetl.domain` layer.

## Overview

The domain layer contains pure business logic without external dependencies. It defines:

- **Ports (ABCs/Protocols)**: Interfaces that infrastructure adapters implement
- **Domain Models**: Core business entities and value objects
- **Errors**: Domain-specific exceptions
- **Contracts**: Type definitions and protocols
- **Services**: Pure business logic services

## Layer Dependencies

### Forbidden Imports

The domain layer must NOT import from:

```python
# FORBIDDEN - Infrastructure concerns
from bioetl.infrastructure import *
from bioetl.application import *
from bioetl.interfaces import *

# FORBIDDEN - External libraries (infrastructure concerns)
import pandas
import pandera
import requests
import httpx
import yaml
import boto3
import sqlalchemy

# FORBIDDEN - Framework-specific
from pydantic import *  # Use only for configs, not domain models
```

### Allowed Imports

```python
# Standard library only
from typing import Any, Protocol, Iterator
from abc import ABC, abstractmethod
from dataclasses import dataclass
from collections.abc import Mapping, Sequence
from pathlib import Path
from datetime import datetime
import re

# Domain internal imports
from bioetl.domain.ports import *
from bioetl.domain.errors import *
from bioetl.domain.models import *
from bioetl.domain.types import *
```

## Module Structure

```
domain/
├── clients/           # Client contracts (DataClientABC, etc.)
│   ├── base/         # Base client contracts
│   ├── contracts.py  # Main client ABCs
│   └── resilience.py # Retry/timeout policies
├── configs/          # Configuration models (Pydantic allowed here)
├── data.py           # TabularData protocol, RecordBatch
├── errors.py         # Domain exceptions
├── models/           # Domain models (RunContext, RunResult, etc.)
├── observability/    # Logging/metrics ports
├── pipelines/        # Pipeline contracts and types
├── ports/            # Port interfaces (hexagonal boundaries)
│   ├── extraction.py
│   ├── parsing.py
│   ├── request_building.py
│   └── ...
├── providers/        # Provider definitions
├── schemas/          # Pipeline contracts and validation schemas
├── services/         # Pure domain services
├── transform/        # Transformation contracts
├── types.py          # Type aliases
├── validation/       # Validation contracts
└── value_objects.py  # Immutable value objects
```

## Key Contracts

### Ports (Hexagonal Architecture)

| Port | Location | Purpose |
|------|----------|---------|
| `ExtractionServiceABC` | `ports/extraction.py` | Data extraction contract |
| `ResponseParserPortABC` | `ports/parsing.py` | Response parsing contract |
| `RequestBuilderPortABC` | `ports/request_building.py` | Request building contract |
| `LoaderABC` | `pipelines/contracts.py` | Data loading contract |
| `LoggingPortABC` | `observability/contracts.py` | Logging contract |

### Data Abstractions

| Type | Location | Purpose |
|------|----------|---------|
| `TabularData` | `data.py` | Protocol for tabular data (abstracts pandas) |
| `RecordBatch` | `data.py` | Type alias for list[dict] records |
| `ApiPayload` | `types.py` | Type alias for API response data |

### Exceptions

| Exception | Purpose |
|-----------|---------|
| `BioetlError` | Base exception |
| `ClientError` | Client communication errors |
| `ClientNetworkError` | Network failures |
| `ClientRateLimitError` | Rate limit errors |
| `MetadataFetchError` | Metadata retrieval failures |
| `ParseError` | Response parsing failures |
| `PipelineStageError` | Pipeline stage failures |

## Design Principles

### 1. Dependency Inversion

The domain defines interfaces (ports), infrastructure provides implementations (adapters).

```python
# Domain defines the contract
class ExtractionServiceABC(ABC):
    @abstractmethod
    def extract_all(self, entity: str, **filters) -> RecordBatch: ...

# Infrastructure implements it
class ChemblExtractionServiceImpl(ExtractionServiceABC):
    def extract_all(self, entity: str, **filters) -> RecordBatch:
        # Implementation with HTTP client, etc.
        ...
```

### 2. No Business Logic Leakage

Domain logic must not depend on:
- HTTP status codes
- Database schemas
- File formats
- API response structures

### 3. Immutability

Value objects should be immutable:

```python
@dataclass(frozen=True, slots=True)
class EntityName:
    value: str
```

### 4. Type Safety

Use explicit types, avoid `Any`:

```python
# Good
def process(data: RecordBatch) -> RecordBatch: ...

# Avoid
def process(data: Any) -> Any: ...
```

## Architectural Tests

Domain boundaries are enforced by tests in `tests/architecture/`:

- `test_domain_boundaries.py`: Verifies no forbidden imports
- `test_layer_dependencies.py`: Verifies layer isolation
- `test_architecture_rules.py`: Verifies ABC implementations

Run architectural tests:
```bash
pytest tests/architecture/ -v
```

## Migration Guide

### Adding New Ports

1. Create ABC in `domain/ports/`
2. Add to `domain/ports/__init__.py` exports
3. Create infrastructure adapter
4. Wire in `CompositionRoot`

### Adding New Exceptions

1. Add to `domain/errors.py`
2. Update `__all__` exports
3. Inherit from appropriate base (`BioetlError`, `ClientError`, etc.)

## Related Documentation

- [Application Layer](../application/ARCHITECTURE.md)
- [Infrastructure Layer](../infrastructure/ARCHITECTURE.md)
- [Interfaces Layer](../interfaces/ARCHITECTURE.md)
