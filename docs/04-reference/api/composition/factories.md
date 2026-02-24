# Factories

Component factories for Dependency Injection.

## Pipeline Factory

### GenericPipelineFactory

Creates pipeline runners with proper dependency injection.

::: bioetl.composition.factories.pipeline_factory.GenericPipelineFactory
    options:
        show_root_heading: true
        show_source: false
        members:
            - --init--
            - create-runner
            - create-executor

### create-pipeline_factory

Factory function to create GenericPipelineFactory instances.

::: bioetl.composition.factories.pipeline_factory.create_pipeline_factory
    options:
        show_root_heading: true
        show_source: false

### assemble-runner

Assemble a PipelineRunner with all dependencies.

::: bioetl.composition.factories.pipeline_factory.assemble_runner
    options:
        show_root_heading: true
        show_source: false

### build-pipeline-services

Build PipelineServices bundle.

::: bioetl.composition.factories.pipeline_factory.build_pipeline_services
    options:
        show_root_heading: true
        show_source: false

## Services Factory

### BaseServicesFactory

Base factory for creating service bundles.

::: bioetl.composition.factories.services_factory.BaseServicesFactory
    options:
        show_root_heading: true
        show_source: false

### ServicesBuilder

Builder pattern for constructing service bundles.

::: bioetl.composition.factories.services_factory.ServicesBuilder
    options:
        show_root_heading: true
        show_source: false

<!-- RunnerServices and build_runner_services: planned, not yet implemented -->

## Data Source Factory

### DataSourceFactory

Creates data source adapters.

::: bioetl.composition.factories.data_source_factory.DataSourceFactory
    options:
        show_root_heading: true
        show_source: false

### DataSourceRegistry

Registry for data source creators.

::: bioetl.composition.factories.data_source_factory.DataSourceRegistry
    options:
        show_root_heading: true
        show_source: false

### DataSourceCreator

Protocol for data source creator functions.

::: bioetl.composition.factories.data_source_factory.DataSourceCreator
    options:
        show_root_heading: true
        show_source: false

## Storage Factory

### StorageFactory

Creates storage adapters (Bronze, Silver, Gold writers).

::: bioetl.composition.factories.storage.StorageFactory
    options:
        show_root_heading: true
        show_source: false

### StorageAdapter

Unified storage adapter interface.

::: bioetl.composition.factories.storage.StorageAdapter
    options:
        show_root_heading: true
        show_source: false

### StorageContext

Context for storage operations.

::: bioetl.composition.factories.storage.StorageContext
    options:
        show_root_heading: true
        show_source: false

## Transformer Factory

### register-transformer

Register a transformer class for an entity type.

::: bioetl.composition.factories.transformer_factory.register_transformer
    options:
        show_root_heading: true
        show_source: false

### get-transformer-class

Get transformer class for entity type.

::: bioetl.composition.factories.transformer_factory.get_transformer_class
    options:
        show_root_heading: true
        show_source: false

### create-transformer

Create transformer instance with dependencies.

::: bioetl.composition.factories.transformer_factory.create_transformer
    options:
        show_root_heading: true
        show_source: false

### register-all-transformers

Register all available transformers.

::: bioetl.composition.factories.transformer_factory.register_all_transformers
    options:
        show_root_heading: true
        show_source: false

## HTTP Client Factory

### HttpClientFactory

Factory for creating HTTP clients.

::: bioetl.composition.factories.http_client_factory.HttpClientFactory
    options:
        show_root_heading: true
        show_source: false

## Pipeline Factories

Pre-configured factory functions for each pipeline.

### chembl_activity_factory

Factory for ChEMBL activity pipeline.

::: bioetl.composition.factories.pipeline_factories.chembl_activity_factory
    options:
        show_root_heading: true
        show_source: false

### pubchem_compound_factory

Factory for PubChem compound pipeline.

::: bioetl.composition.factories.pipeline_factories.pubchem_compound_factory
    options:
        show_root_heading: true
        show_source: false

### uniprot_protein_factory

Factory for UniProt protein pipeline.

::: bioetl.composition.factories.pipeline_factories.uniprot_protein_factory
    options:
        show_root_heading: true
        show_source: false

### pubmed_publication_factory

Factory for PubMed publication pipeline.

::: bioetl.composition.factories.pipeline_factories.pubmed_publication_factory
    options:
        show_root_heading: true
        show_source: false

## Factory Pattern

```mermaid
classDiagram
    class GenericPipelineFactory {
        +create-runner() PipelineRunner
        +create-executor() BatchExecutor
    }

    class DataSourceFactory {
        +create() DataSourcePort
    }

    class StorageFactory {
        +create() StorageAdapter
    }

    class ServicesBuilder {
        +with-logger() ServicesBuilder
        +with-metrics() ServicesBuilder
        +build() RunnerServices
    }

    GenericPipelineFactory --> DataSourceFactory
    GenericPipelineFactory --> StorageFactory
    GenericPipelineFactory --> ServicesBuilder
```

## Usage Example

```python
from bioetl.composition.factories import (
    GenericPipelineFactory,
    DataSourceFactory,
    StorageFactory,
    build-runner-services,
)

# Create factories
data-source_factory = DataSourceFactory()
storage_factory = StorageFactory()

# Create pipeline factory
# factory = GenericPipelineFactory(
#     data-source_factory=data-source_factory,
#     storage_factory=storage_factory,
#     config=pipeline-config,
# )

# Create runner
# runner = factory.create-runner(
#     ctx=ctx,
#     services=services,
#     checkpoint-manager=checkpoint-manager,
# )

# Or use the pre-configured factory
from bioetl.composition.factories import chembl_activity_factory

# runner = chembl_activity_factory(ctx)
# await runner.run()
```

## See Also

- [Bootstrap](bootstrap.md) - Composition root
- [Application Core](../application/core.md) - PipelineRunner, Executor
- [Infrastructure](../infrastructure.md) - Adapter implementations
