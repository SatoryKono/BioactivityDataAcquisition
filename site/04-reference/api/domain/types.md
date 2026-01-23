# Domain Types

Core domain types and value objects.

## Identifiers

### RunID

Unique identifier for a pipeline run (UUID).

::: bioetl.domain.types.RunID
    options:
        show_root_heading: true
        show_source: false

### EntityID

Business key for an entity (e.g., 'CHEMBL123').

::: bioetl.domain.types.EntityID
    options:
        show_root_heading: true
        show_source: false

### ContentHash

SHA256 hash of canonical record representation.

::: bioetl.domain.types.ContentHash
    options:
        show_root_heading: true
        show_source: false

### BatchID

Unique identifier for a data batch.

::: bioetl.domain.types.BatchID
    options:
        show_root_heading: true
        show_source: false

## Enums

### RunType

Type of pipeline run (incremental, backfill, rebuild).

::: bioetl.domain.types.RunType
    options:
        show_root_heading: true
        show_source: false

### DriftLevel

Schema drift severity levels.

::: bioetl.domain.types.DriftLevel
    options:
        show_root_heading: true
        show_source: false

### HealthStatus

Provider health status.

::: bioetl.domain.types.HealthStatus
    options:
        show_root_heading: true
        show_source: false

### CircuitBreakerState

Circuit breaker state machine states.

::: bioetl.domain.types.CircuitBreakerState
    options:
        show_root_heading: true
        show_source: false

### DataClassification

Data sensitivity classification.

::: bioetl.domain.types.DataClassification
    options:
        show_root_heading: true
        show_source: false

### ErrorType

Error classification for handling strategy.

::: bioetl.domain.types.ErrorType
    options:
        show_root_heading: true
        show_source: false

### DQStatus

Quarantine record status.

::: bioetl.domain.types.DQStatus
    options:
        show_root_heading: true
        show_source: false

### WriteMode

Write mode for data operations.

::: bioetl.domain.medallion.WriteMode
    options:
        show_root_heading: true
        show_source: false

## Records

### BronzeRecord

Untyped dictionary representing a raw record.

::: bioetl.domain.types.BronzeRecord
    options:
        show_root_heading: true
        show_source: false

### SilverRecord

Normalized record for Silver layer.

::: bioetl.domain.types.SilverRecord
    options:
        show_root_heading: true
        show_source: false

## Reports

### ValidationResult

Result of record validation.

::: bioetl.domain.types.ValidationResult
    options:
        show_root_heading: true
        show_source: false

### ConfigValidationError

Single configuration validation error.

::: bioetl.domain.types.ConfigValidationError
    options:
        show_root_heading: true
        show_source: false

### ComponentHealthResult

Result of a single component health check.

::: bioetl.domain.types.ComponentHealthResult
    options:
        show_root_heading: true
        show_source: false

### HealthReport

Aggregated health check report.

::: bioetl.domain.types.HealthReport
    options:
        show_root_heading: true
        show_source: false

### PreflightReport

Preflight validation report.

::: bioetl.domain.types.PreflightReport
    options:
        show_root_heading: true
        show_source: false

## Usage Example

```python
from bioetl.domain.types import RunType, HealthStatus

# Using enums
run_type = RunType.INCREMENTAL
status = HealthStatus.HEALTHY

# Using NewType
from uuid import uuid4
run_id = RunID(uuid4())
```

## See Also

- [Entities](entities.md) - Domain entities
- [Exceptions](exceptions.md) - Domain exceptions
