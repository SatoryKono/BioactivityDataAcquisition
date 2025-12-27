# Domain Types

Core type definitions, enumerations, and type aliases used throughout BioETL.

## Identifiers

### RunID

UUID-based unique identifier for pipeline runs.

::: bioetl.domain.types.RunID
    options:
        show_root_heading: true
        show_source: false

### BatchID

UUID-based unique identifier for record batches.

::: bioetl.domain.types.BatchID
    options:
        show_root_heading: true
        show_source: false

## Enumerations

### RunType

Pipeline execution mode.

::: bioetl.domain.types.RunType
    options:
        show_root_heading: true
        show_source: true
        members:
            - INCREMENTAL
            - BACKFILL
            - REBUILD

| Value | Description | Lock Type |
|-------|-------------|-----------|
| `INCREMENTAL` | Delta updates (production default) | Shared |
| `BACKFILL` | Historical data loading | Exclusive |
| `REBUILD` | Full table refresh | Exclusive |

### HealthStatus

Component health state.

::: bioetl.domain.types.HealthStatus
    options:
        show_root_heading: true
        show_source: true
        members:
            - HEALTHY
            - DEGRADED
            - UNHEALTHY

### WriteMode

Silver layer write strategy.

::: bioetl.domain.types.WriteMode
    options:
        show_root_heading: true
        show_source: true

| Value | Description |
|-------|-------------|
| `MERGE` | Upsert by primary key (default) |
| `APPEND` | Append-only |
| `OVERWRITE` | Replace partition/table |

### CircuitBreakerState

Circuit breaker state machine.

::: bioetl.domain.types.CircuitBreakerState
    options:
        show_root_heading: true
        show_source: true
        members:
            - CLOSED
            - OPEN
            - HALF_OPEN

## Record Types

### BronzeRecord

Raw record from data source (unprocessed).

```python
BronzeRecord = dict[str, Any]
```

### SilverRecord

Normalized record with metadata.

```python
SilverRecord = dict[str, Any]
# Required fields: _run_id, _run_type, _ingestion_ts, _content_hash
```

### GoldRecord

Validated, analytics-ready record.

```python
GoldRecord = dict[str, Any]
# Schema-validated, flattened structure
```

## Validation Types

### ValidationResult

Result of schema validation.

::: bioetl.domain.types.ValidationResult
    options:
        show_root_heading: true
        show_source: false

## Configuration Types

### RuntimeConfig

Pipeline runtime configuration.

::: bioetl.domain.config.RuntimeConfig
    options:
        show_root_heading: true
        show_source: false
        members:
            - run_type
            - resume
            - limit
            - dry_run

### PipelineConfig

Pipeline-specific configuration.

::: bioetl.domain.config.PipelineConfig
    options:
        show_root_heading: true
        show_source: false
        members:
            - pipeline_name
            - provider
            - entity_type
            - primary_keys
            - batch_size

## Usage Example

```python
from bioetl.domain.types import RunType, HealthStatus, RunID
from bioetl.domain.config import RuntimeConfig
from uuid import uuid4

# Create runtime configuration
config = RuntimeConfig(
    run_type=RunType.INCREMENTAL,
    resume=True,
    limit=1000,
)

# Generate run ID
run_id: RunID = RunID(uuid4())

# Check health status
if status == HealthStatus.UNHEALTHY:
    raise InfrastructureError("Component unhealthy")
```

## See Also

- [Ports](ports.md) - Port interfaces using these types
- [Entities](entities.md) - Domain entity dataclasses
