# Infrastructure-Domain Isolation

## Status
Accepted

## Context
Infrastructure layer (clients, parsers, config loaders) directly imported and used
domain models (ActivityRawModel, schema registration functions). This violated
hexagonal architecture principles and made testing infrastructure without domain
knowledge impossible.

Specific violations:
- `response_parser.py` imported `ActivityRawModel`
- `extraction_service_impl.py` returned typed `RawRecord` models
- `config/loader.py` called `register_schemas()` directly

## Decision
Introduce strict layer boundaries:
1. Infrastructure returns generic types (`dict[str, Any]`)
2. Application layer handles domain model mapping via `RecordMapperABC`
3. Schema registration moved to `SchemaBootstrapService` in application
4. Ports define contracts for cross-layer communication

## Consequences
- Infrastructure can be tested in isolation
- Domain models can change without affecting infrastructure
- Clear data flow: API → dict → application mapper → domain model
- Requires explicit bootstrap sequence in application startup
