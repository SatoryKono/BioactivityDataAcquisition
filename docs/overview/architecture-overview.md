# Architecture Overview

High-level architecture of BioETL framework.

## System Layers

### 1. Pipeline Layer

Pipelines orchestrate the data processing workflow:

```
PipelineBase
  ├── Extract Stage
  ├── Transform Stage
  ├── Validate Stage
  └── Write Stage
```

### 2. Component Layer

Reusable components implement specific responsibilities:

- **Source Clients**: Fetch data from external APIs (ChEMBL, PubMed, etc.)
- **Transformers**: Normalize and transform raw data
- **Validators**: Validate data against Pandera schemas
- **Writers**: Write validated data to storage

### 3. Infrastructure Layer

Cross-cutting concerns:

- **HTTP Infrastructure**: Retry policies, rate limiting, circuit breakers
- **Configuration**: Profile-based config resolution
- **Logging**: Structured logging with UnifiedLogger
- **Caching**: HTTP response caching

## Data Flow

```
External API → SourceClient → Transformer → Validator → Writer → Artifacts
```

## Component Contracts

All components follow the ABC (Abstract Base Class) pattern:

- **ABC**: Defines the contract (interface)
- **Default Factory**: Provides default implementation factory
- **Impl**: Concrete implementation

See [ABC Reference](../reference/abc/index.md) for all contracts.

## Related Documentation

- **[Pipeline Base](../reference/core/pipeline-base.md)** — Base pipeline architecture
- **[Unified API Client](../reference/core/unified-api-client.md)** — HTTP client infrastructure
- **[Schema Registry](../reference/core/schema-registry.md)** — Data validation
- **[Architecture Decisions](../architecture/)** — Detailed design decisions

