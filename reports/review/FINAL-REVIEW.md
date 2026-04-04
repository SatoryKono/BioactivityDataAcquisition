# BioETL — Full Project Review Report
**Date**: 2026-04-04
**RULES.md Version**: 5.22
**Project Version**: 1.0.0
**Reviewed by**: Hierarchical AI Review System (L1 + L2 + L3 agents)
**Total files reviewed**: 5037
**Total LOC reviewed**: 695465
---
## Executive Summary
**Overall Status**: PASS
**Overall Score**: 9.2/10.0
Overall project health is reviewed.

### Key Metrics
| Metric | Value |
|--------|-------|
| Total issues found | 11175 |
| Critical issues | 0 |
| High issues | 10371 |
| Medium issues | 4 |
| Low issues | 800 |
| Sectors reviewed | 8 |
---
## Sector Scores
| Sector | Scope | Files | LOC | Score | Status |
|--------|-------|-------|-----|-------|--------|
| S1 Domain Layer | src/bioetl/domain | 412 | 42012 | 9.8 | PASS |
| S2 Application Layer | src/bioetl/application | 372 | 49705 | 9.6 | PASS |
| S3 Infrastructure Layer | src/bioetl/infrastructure | 392 | 48601 | 9.8 | PASS |
| S4 Composition+Ifaces | ['src/bioetl/composition', 'src/bioetl/interfaces'] | 251 | 26056 | 9.0 | WARN |
| S5 Cross-cutting Concerns | src/bioetl | 1429 | 166494 | 6.0 | WARN |
| S6 Tests | tests | 1269 | 272152 | 8.6 | WARN |
| S7 Configs | configs | 67 | 9998 | 10.0 | PASS |
| S8 Documentation | docs | 845 | 80447 | 10.0 | PASS |
---
## Category Scores (aggregated across all sectors)
| Category | Weight | Score | Issues | Status |
|----------|--------|-------|--------|--------|
| Architecture | -- | 0.0 | 41 | FAIL |
| Anti-Patterns | -- | 9.0 | 1 | PASS |
| DI Violations | -- | 10.0 | 0 | PASS |
| Naming | -- | 0.0 | 800 | FAIL |
| Types | -- | 0.0 | 10329 | FAIL |
| Testing | -- | 10.0 | 0 | PASS |
---
## Critical Issues (блокируют merge/release)
---
## High Issues (требуют исправления)
### DI-005
- **File**: `src/bioetl/domain/ports/data_source.py`
- **Description**: Factory class DataSourceFactoryPort outside composition/tests

### DI-005
- **File**: `src/bioetl/domain/ports/runtime/runner.py`
- **Description**: Factory class RunnerFactoryPort outside composition/tests

### DI-005
- **File**: `src/bioetl/domain/ports/runtime/runner.py`
- **Description**: Factory class PipelineFactoryPort outside composition/tests

### DI-005
- **File**: `src/bioetl/composition/providers/_registration_contracts.py`
- **Description**: Factory class ProviderHttpClientFactoryProtocol outside composition/tests

### DI-005
- **File**: `src/bioetl/composition/providers/_registration_contracts.py`
- **Description**: Factory class ProviderAdapterFactoryProtocol outside composition/tests

### DI-005
- **File**: `src/bioetl/composition/factories/services/factory.py`
- **Description**: Factory class BaseServicesFactory outside composition/tests

### DI-005
- **File**: `src/bioetl/composition/factories/pipeline/runner.py`
- **Description**: Factory class RunnerFactory outside composition/tests

### DI-005
- **File**: `src/bioetl/composition/factories/pipeline/assembler.py`
- **Description**: Factory class GenericPipelineFactory outside composition/tests

### DI-005
- **File**: `src/bioetl/composition/factories/pipeline/factory_method_helpers.py`
- **Description**: Factory class _PipelineFactoryContext outside composition/tests

### DI-005
- **File**: `src/bioetl/composition/factories/pipeline/factory_method_helpers.py`
- **Description**: Factory class _BuildFactoryServicesRequest outside composition/tests

### DI-005
- **File**: `src/bioetl/composition/factories/pipeline/config_types.py`
- **Description**: Factory class PipelineFactoryConfig outside composition/tests

### DI-005
- **File**: `src/bioetl/composition/factories/pipeline/registry.py`
- **Description**: Factory class _PipelineFactoryRegistrationState outside composition/tests

### DI-005
- **File**: `src/bioetl/composition/factories/pipeline/run_context_factory.py`
- **Description**: Factory class RunContextFactory outside composition/tests

### DI-005
- **File**: `src/bioetl/composition/factories/datasource/data_source_factory.py`
- **Description**: Factory class DataSourceFactory outside composition/tests

### DI-005
- **File**: `src/bioetl/composition/factories/datasource/adapter_helpers.py`
- **Description**: Factory class AdapterHelpersFactory outside composition/tests

### DI-005
- **File**: `src/bioetl/composition/factories/datasource/http_client.py`
- **Description**: Factory class HttpClientFactory outside composition/tests

### DI-005
- **File**: `src/bioetl/composition/factories/storage/factory.py`
- **Description**: Factory class StorageFactory outside composition/tests

### DI-005
- **File**: `src/bioetl/composition/factories/dq/factory.py`
- **Description**: Factory class DQServicesFactory outside composition/tests

### DI-005
- **File**: `src/bioetl/composition/bootstrap/runtime/runner_factory_builder_service.py`
- **Description**: Factory class RunnerFactoryBuilderService outside composition/tests

### DI-005
- **File**: `src/bioetl/composition/bootstrap/runtime/composite_support_services_factory.py`
- **Description**: Factory class CompositeSupportServicesFactory outside composition/tests

---
## Verification Commands
```bash
pytest tests/architecture/ -v
rg "from bioetl\.infrastructure" src/bioetl/application -g "*.py" | rg -v "TYPE_CHECKING"
rg "from bioetl\.application" src/bioetl/infrastructure -g "*.py" | rg -v "TYPE_CHECKING"
mypy src/bioetl/ --strict
pytest --cov=src/bioetl --cov-fail-under=85
make lint
```
