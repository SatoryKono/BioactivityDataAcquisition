# P1 DDD Consolidation (2026-03-06)

## Scope
- Exception taxonomy augmented with bounded-context classification.
- Unified domain<->infrastructure exception mapping layer introduced.
- Domain complexity debt reduced by removing stale exemptions.

## Domain Exception Taxonomy (Bounded Context)
Added `DomainExceptionContext` and resolver:
- `external_integration`
- `storage`
- `orchestration`
- `validation`
- `data_quality`
- `platform`

Module: `src/bioetl/domain/exceptions/bounded_context.py`

## Unified Mapping Layer
Added central mapper:
- `DomainInfraExceptionMapper`
- `DomainErrorMappingInput`
- `InfraErrorDisposition`

Module: `src/bioetl/infrastructure/errors/exception_mapper.py`

Backward compatibility preserved via adapter facade:
- `src/bioetl/infrastructure/adapters/adapter_error_mapper.py`

## Risk Control
- Added contract tests for bounded-context taxonomy and mapper behavior.
- Existing adapter mapper tests remain valid through facade compatibility.

## Debt Burndown
- `domain_complexity` exemptions reduced from 35 to 25.
