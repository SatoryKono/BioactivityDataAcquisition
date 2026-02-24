# Domain Types

Core domain types and value objects.

## Identifiers

### RunID

Unique identifier for a pipeline run (UUID).

::: bioetl.domain.types.RunID
    options:
        show-root-heading: true
        show-source: false

### EntityID

Business key for an entity (e.g., 'CHEMBL123').

::: bioetl.domain.types.EntityID
    options:
        show-root-heading: true
        show-source: false

### ContentHash

SHA256 hash of canonical record representation.

::: bioetl.domain.types.ContentHash
    options:
        show-root-heading: true
        show-source: false

### BatchID

Unique identifier for a data batch.

::: bioetl.domain.types.BatchID
    options:
        show-root-heading: true
        show-source: false

## Enums

### RunType

Type of pipeline run (incremental, backfill, rebuild).

::: bioetl.domain.types.RunType
    options:
        show-root-heading: true
        show-source: false

### DriftLevel

Schema drift severity levels.

::: bioetl.domain.types.DriftLevel
    options:
        show-root-heading: true
        show-source: false

### HealthStatus

Provider health status.

::: bioetl.domain.types.HealthStatus
    options:
        show-root-heading: true
        show-source: false

### CircuitBreakerState

Circuit breaker state machine states.

::: bioetl.domain.types.CircuitBreakerState
    options:
        show-root-heading: true
        show-source: false

### DataClassification

Data sensitivity classification.

::: bioetl.domain.types.DataClassification
    options:
        show-root-heading: true
        show-source: false

### ErrorType

Error classification for handling strategy.

::: bioetl.domain.types.ErrorType
    options:
        show-root-heading: true
        show-source: false

<!-- DQStatus: planned, not yet implemented -->

### WriteMode

Write mode for data operations.

::: bioetl.domain.medallion.WriteMode
    options:
        show-root-heading: true
        show-source: false

## Records

### BronzeRecord

Untyped dictionary representing a raw record.

::: bioetl.domain.types.BronzeRecord
    options:
        show-root-heading: true
        show-source: false

### SilverRecord

Normalized record for Silver layer.

::: bioetl.domain.types.SilverRecord
    options:
        show-root-heading: true
        show-source: false

## Reports

### ValidationResult

Result of record validation.

::: bioetl.domain.types.ValidationResult
    options:
        show-root-heading: true
        show-source: false

### ConfigValidationError

Single configuration validation error.

::: bioetl.domain.types.ConfigValidationError
    options:
        show-root-heading: true
        show-source: false

### ComponentHealthResult

Result of a single component health check.

::: bioetl.domain.types.ComponentHealthResult
    options:
        show-root-heading: true
        show-source: false

### HealthReport

Aggregated health check report.

::: bioetl.domain.types.HealthReport
    options:
        show-root-heading: true
        show-source: false

### PreflightReport

Preflight validation report.

::: bioetl.domain.types.PreflightReport
    options:
        show-root-heading: true
        show-source: false

## Usage Example

```python
from bioetl.domain.types import RunType, HealthStatus

# Using enums
run-type = RunType.INCREMENTAL
status = HealthStatus.HEALTHY

# Using NewType
from uuid import uuid4
run-id = RunID(uuid4())
```

## See Also

- [Entities](entities.md) - Domain entities
- [Exceptions](exceptions.md) - Domain exceptions
