# Dependency Flow Documentation

This document describes the dependency injection flow and composition patterns
used in BioETL after the refactoring to eliminate global state.

## Overview

BioETL follows the Composition Root pattern where all dependencies are assembled
in a single location (`CompositionRoot`). This eliminates global mutable state
and makes the system more testable and maintainable.

## Dependency Graph

```
┌─────────────────────────────────────────────────────────────────────┐
│                         INTERFACES LAYER                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  CompositionRoot                                                    │
│  ├── ObservabilityFactory → Logger, Metrics                        │
│  ├── InfrastructureFactory → Loader, Validator, MetadataBuilder    │
│  ├── ProviderRegistry                                              │
│  └── SchemaContractProvider                                        │
│           │                                                        │
│           ▼                                                        │
│  SchemaContractLoader ──────────────────┐                          │
│           │                             │                          │
│           ▼                             ▼                          │
│  PipelineContainer ◄─────────── PipelineConfig                     │
│  ├── ValidationService                                             │
│  ├── ExtractionService                                             │
│  ├── NormalizationService                                          │
│  ├── HashService                                                   │
│  ├── IndexGenerator                                                │
│  ├── TimestampProvider                                             │
│  ├── SchemaContract ←──────── get_schema_contract()                │
│  └── Loader                                                        │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         APPLICATION LAYER                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  PipelineFactory.create(container)                                  │
│           │                                                        │
│           ▼                                                        │
│  PipelineBase                                                       │
│  ├── config: PipelineConfig                                        │
│  ├── logger: LoggingPortABC                                        │
│  ├── validation_service: ValidationService                         │
│  ├── loader: LoaderABC                                             │
│  ├── schema_contract: PipelineSchemaModel  ←── INJECTED           │
│  ├── extractor: ExtractorABC                                       │
│  ├── transformer: TransformerABC                                   │
│  └── post_transformer: TransformerABC                              │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                           DOMAIN LAYER                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  PipelineSchemaModel (Immutable data class)                        │
│  ├── pipeline_code: str                                            │
│  ├── schema_out: str                                               │
│  ├── schema_in: str | None                                         │
│  └── output_schema: str | None                                     │
│                                                                     │
│  PIPELINE_CONTRACTS (Static registry - read-only)                  │
│  get_pipeline_contract() → PipelineSchemaModel                     │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## Key Changes from Refactoring

### 1. Global State Elimination

**Before:**
```python
# Global mutable state (REMOVED)
_SCHEMA_CONTRACT_PROVIDER: SchemaContractProviderABC | None = None

def set_schema_contract_provider(provider):
    global _SCHEMA_CONTRACT_PROVIDER
    _SCHEMA_CONTRACT_PROVIDER = provider
```

**After:**
```python
# Explicit dependency injection via CompositionRoot
root = CompositionRoot()
provider = root.get_schema_contract_provider()
loader = SchemaContractLoader(provider)
```

### 2. Schema Contract Injection

**Before:**
```python
class PipelineBase:
    def __init__(self, config, ...):
        # Called domain function directly
        self._schema_contract = get_pipeline_contract(config.id)
```

**After:**
```python
class PipelineBase:
    def __init__(self, config, schema_contract: PipelineSchemaModel, ...):
        # Schema contract is injected
        self._schema_contract = schema_contract

# Container provides schema contract
container.get_schema_contract()  # Returns PipelineSchemaModel
```

### 3. CompositionRoot Simplification

**Before:**
```python
root = CompositionRoot(
    logger=mock_logger,      # Direct instance injection
    metrics=mock_metrics,    # Direct instance injection
)
```

**After:**
```python
# Use factory pattern
class MockObservabilityFactory(ObservabilityFactoryABC):
    def create_logger(self) -> LoggingPortABC:
        return mock_logger
    def create_metrics(self) -> MetricsPortABC:
        return mock_metrics

root = CompositionRoot(observability_factory=MockObservabilityFactory())
```

## Dependency Resolution Order

1. **CompositionRoot** creates infrastructure factories
2. **Factories** create services (Logger, Metrics, Loader, etc.)
3. **PipelineContainer** assembles pipeline-specific dependencies
4. **PipelineFactory** creates pipeline with all dependencies injected
5. **Pipeline** runs with fully resolved dependency graph

## Testing

For testing, create mock implementations of factory protocols:

```python
from bioetl.interfaces.factories import ObservabilityFactoryABC

class TestObservabilityFactory(ObservabilityFactoryABC):
    def __init__(self, logger: LoggingPortABC, metrics: MetricsPortABC):
        self._logger = logger
        self._metrics = metrics

    def create_logger(self) -> LoggingPortABC:
        return self._logger

    def create_metrics(self) -> MetricsPortABC:
        return self._metrics

# Usage in tests
root = CompositionRoot(
    observability_factory=TestObservabilityFactory(mock_logger, mock_metrics)
)
```

## Migration Guide

### For Legacy Code

Use the adapter function for backward compatibility:

```python
from bioetl.interfaces.legacy_adapters import create_composition_root_with_legacy

# Deprecated but still works
root = create_composition_root_with_legacy(
    logger=mock_logger,
    metrics=mock_metrics,
)
```

### For New Code

Use the factory-based API:

```python
from bioetl.interfaces.composition_root import CompositionRoot
from bioetl.interfaces.factories import ObservabilityFactoryABC

class MyFactory(ObservabilityFactoryABC):
    ...

root = CompositionRoot(observability_factory=MyFactory())
```

## Architecture Principles

1. **No Global State**: All state is encapsulated in instances
2. **Explicit Dependencies**: All dependencies are passed explicitly
3. **Composition Root**: Single assembly point for dependency graph
4. **Factory Pattern**: Factories create instances, not direct construction
5. **Immutable Domain**: Domain objects are immutable data classes
