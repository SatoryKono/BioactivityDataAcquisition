# Domain Layer

Pure business logic without I/O operations.

## Purpose

Contains core business types, ports (interfaces), and pure transformations. No external dependencies except standard library.

## Modules

| Module | Type | Diagram |
|--------|------|---------|
| `ports.py` | port | [ports.mmd](../../../docs/diagrams/domain/ports.mmd) |
| `types.py` | value_object | [types.mmd](../../../docs/diagrams/domain/types.mmd) |
| `transformations.py` | util | [transformations.mmd](../../../docs/diagrams/domain/transformations.mmd) |
| `exceptions.py` | exception | [exceptions.mmd](../../../docs/diagrams/domain/exceptions.mmd) |
| `error_classifier.py` | util | [error_classifier.mmd](../../../docs/diagrams/domain/error_classifier.mmd) |
| `context.py` | value_object | [context.mmd](../../../docs/diagrams/domain/context.mmd) |

## Dependencies

- Uses: Standard library only (typing, datetime, enum, uuid, hashlib)
- Used by: `application`, `infrastructure`

## Key Concepts

### Ports (Protocol)
Abstract interfaces for external systems:
- `DataSourcePort` - Data sources (ChEMBL, PubChem, UniProt)
- `StoragePort` - Medallion storage (Bronze/Silver/Gold)
- `LockPort` - Distributed locking
- `CheckpointPort` - Pipeline state persistence
- `QuarantinePort` - Failed records isolation
- `MetricsPort` - Observability metrics

### Types
Domain value objects:
- `RunID`, `EntityID`, `BatchID`, `ContentHash` - Identifiers
- `RunType`, `DriftLevel`, `HealthStatus`, `ErrorType` - Enums

### Exception Hierarchy
```
BioETLError
├── CriticalError (stop pipeline)
│   ├── LockLostError
│   └── AuthError
├── RecoverableError (retry)
│   ├── RateLimitError
│   └── TimeoutError
└── DataQualityError (skip record)
    ├── SchemaViolationError
    └── MissingRequiredFieldError
```
