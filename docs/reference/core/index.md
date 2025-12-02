# Core Components

Core components of the BioETL framework.

## Core Concepts (Abstract Base Classes)

These are the foundational abstractions that define contracts for the framework:

- **[Pipeline Base](00-pipeline-base.md)** — Base pipeline architecture and orchestration
- **[Base External Data Client](01-base-external-data-client.md)** — Base client for external APIs (deprecated, use UnifiedAPIClient)

## Core Services (Implementations)

These are concrete services that implement the core functionality:

### Data Processing

- **[Unified API Client](03-unified-api-client.md)** — Unified HTTP client infrastructure for external APIs
- **[Unified Output Writer](04-unified-output-writer.md)** — Unified writer for writing results atomically

### Validation

- **[Schema Registry](05-schema-registry.md)** — Schema registry for data validation (Pandera schemas)
- **[Validation Service](06-validation-service.md)** — Data validation service using Pandera

### Artifact Management

- **[Pipeline Output Service](00-pipeline-output-service.md)** — Service for managing pipeline outputs
- **[Write Artifacts](01-write-artifacts.md)** — Artifact writing utilities and planning

### Client Management

- **[Client Factory Registry](02-client-factory-registry.md)** — Registry for client factories

## Component Contracts

All components follow the ABC (Abstract Base Class) pattern. See [ABC Contracts](../abc/) for interface definitions:

- **PipelineBase** — Pipeline orchestration contract
- **SourceClientABC** — External API client contract
- **TransformerABC** — Data transformation contract
- **ValidatorABC** — Data validation contract
- **WriterABC** — Data writing contract

## Related Documentation

- **[Infrastructure](../infrastructure/)** — HTTP, config, logging infrastructure
- **[Pipelines](../pipelines/)** — Specific pipeline implementations
- **[ABC Contracts](../abc/)** — Abstract base class contracts
- **[Data Flow](../../architecture/data-flow.md)** — End-to-end data flow description
