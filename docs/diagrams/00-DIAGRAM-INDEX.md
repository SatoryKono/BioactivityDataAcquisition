# BioETL Architecture Diagrams

## Overview

This directory contains Mermaid diagrams for understanding the BioETL architecture, file structure, and implementation. All diagrams are organized by category.

## Directory Structure

```
docs/diagrams/
├── 00-DIAGRAM-INDEX.md          # This file
├── overview/                     # High-level architecture diagrams
│   ├── hexagonal-architecture.mmd
│   ├── layer-dependencies.mmd
│   ├── data-flow.mmd
│   └── system-context.mmd
├── layers/                       # Layer-level component diagrams
│   ├── 01-domain-layer.mmd
│   ├── 02-application-layer.mmd
│   ├── 03-infrastructure-layer.mmd
│   └── 04-interfaces-layer.mmd
├── packages/                     # Package-level component diagrams
│   ├── domain/                   # Domain layer packages (13 diagrams)
│   │   ├── aggregates.mmd
│   │   ├── clients.mmd
│   │   ├── configs.mmd
│   │   ├── entities.mmd
│   │   ├── observability.mmd
│   │   ├── output.mmd
│   │   ├── pipelines.mmd
│   │   ├── ports.mmd
│   │   ├── schemas.mmd
│   │   ├── services.mmd
│   │   ├── transform.mmd
│   │   ├── validation.mmd
│   │   └── value-objects.mmd
│   ├── application/              # Application layer packages (14 diagrams)
│   │   ├── config.mmd
│   │   ├── factories.mmd
│   │   ├── files.mmd
│   │   ├── helpers.mmd
│   │   ├── mappers.mmd
│   │   ├── metadata.mmd
│   │   ├── pipelines.mmd
│   │   ├── ports.mmd
│   │   ├── providers.mmd
│   │   ├── runtime.mmd
│   │   ├── services.mmd
│   │   ├── sources.mmd
│   │   ├── transform.mmd
│   │   └── use-cases.mmd
│   ├── infrastructure/           # Infrastructure layer packages (12 diagrams)
│   │   ├── adapters.mmd
│   │   ├── chembl.mmd
│   │   ├── clients.mmd
│   │   ├── config.mmd
│   │   ├── files.mmd
│   │   ├── http.mmd
│   │   ├── logging.mmd
│   │   ├── observability.mmd
│   │   ├── output.mmd
│   │   ├── settings.mmd
│   │   ├── transform.mmd
│   │   └── validation.mmd
│   └── interfaces/               # Interfaces layer packages (4 diagrams)
│       ├── cli.mmd
│       ├── factories.mmd
│       ├── monitoring.mmd
│       └── rest.mmd
├── classes/                      # Class diagrams by object type (14 diagrams)
│   ├── 01-factories.mmd
│   ├── 02-services.mmd
│   ├── 03-ports-abc.mmd
│   ├── 04-adapters.mmd
│   ├── 05-pipelines.mmd
│   ├── 06-validators.mmd
│   ├── 07-transformers.mmd
│   ├── 08-writers.mmd
│   ├── 09-http-clients.mmd
│   ├── 10-record-sources.mmd
│   ├── 11-error-policies.mmd
│   ├── 12-domain-entities.mmd
│   ├── 13-value-objects.mmd
│   └── 14-configs.mmd
├── component/                    # Component diagrams (11 diagrams)
│   ├── 01-application-components.mmd
│   ├── 02-domain-components.mmd
│   ├── 03-infrastructure-components.mmd
│   ├── 04-interfaces-components.mmd
│   ├── 05-system-context-bioetl.mmd
│   ├── 06-hexagonal-architecture.mmd
│   ├── 07-physical-layer-mapping.mmd
│   ├── 08-key-modules-overview.mmd
│   ├── 09-architecture-rules.mmd
│   ├── 10-cli-architecture.mmd
│   └── 11-test-suite-structure.mmd
├── flow/                         # Flow diagrams (17 diagrams)
│   ├── api-to-storage-dataflow.mmd
│   ├── chembl-pipeline-dependency-graph.mmd
│   ├── ci-workflow.mmd
│   ├── cli-extension-flow.mmd
│   ├── cli-option-mapping.mmd
│   ├── config-loading-flow.mmd
│   ├── csv-input-flow.mmd
│   ├── ddd-layered-architecture.mmd
│   ├── domain-services-transform.mmd
│   ├── error-policy-flow.mmd
│   ├── etl-stage-dag.mmd
│   ├── external-enrichment-flow.mmd
│   ├── high-level-architecture.mmd
│   ├── layer-dependency-graph.mmd
│   ├── pagination-flow.mmd
│   ├── pipeline-error-flowchart.mmd
│   ├── project-package-structure.mmd
│   ├── rate-limiter-timeline.mmd
│   ├── retry-policy-flow.mmd
│   └── testing-pyramid.mmd
└── sequence/                     # Sequence diagrams (5 diagrams)
    ├── chembl-api-request-sequence.mmd
    ├── cli-run-sequence.mmd
    ├── manual-di-assembly-sequence.mmd
    ├── pipeline-hooks-sequence.mmd
    └── pipeline-run-sequence.mmd
```

**Total: 100+ Mermaid diagrams**

---

## Diagram Catalog

### 1. Overview Diagrams (`overview/`)

High-level architecture and system context diagrams.

| File | Description |
|------|-------------|
| `hexagonal-architecture.mmd` | Hexagonal architecture pattern overview |
| `layer-dependencies.mmd` | Layer dependency graph |
| `data-flow.mmd` | Data flow through ETL pipeline |
| `system-context.mmd` | System context and external integrations |

---

### 2. Layer Component Diagrams (`layers/`)

One diagram per architectural layer showing all packages.

| File | Description |
|------|-------------|
| `01-domain-layer.mmd` | Domain layer components: entities, ports, schemas, services, value objects |
| `02-application-layer.mmd` | Application layer: factories, services, pipelines, use cases |
| `03-infrastructure-layer.mmd` | Infrastructure layer: adapters, clients, output writers, config loaders |
| `04-interfaces-layer.mmd` | Interface layer: CLI commands, REST API, composition root |

---

### 3. Package Component Diagrams (`packages/`)

Detailed diagrams for each package within a layer.

#### Domain Layer Packages (`packages/domain/`)

| File | Description |
|------|-------------|
| `aggregates.mmd` | Aggregate roots: PipelineIdentity |
| `clients.mmd` | Client base contracts and resilience |
| `configs.mmd` | Configuration models: pipeline, source, sink, execution |
| `entities.mmd` | Domain entities: Activity, Assay, Target, Molecule, Publication |
| `observability.mmd` | Observability contracts: logging, metrics, tracing, progress |
| `output.mmd` | Deterministic output specifications and writers |
| `pipelines.mmd` | Pipeline contracts: ExtractorABC, LoaderABC, PipelineHookABC |
| `ports.mmd` | Abstract ports: extraction, output, config, parsing, filters |
| `schemas.mmd` | Validation schemas: Pandera schemas, field specs, pipeline contracts |
| `services.mmd` | Domain services: entity factory, business key service, version formatter |
| `transform.mmd` | Transform contracts: normalizers, serializers, transformers |
| `validation.mmd` | Validation service contracts |
| `value-objects.mmd` | Value objects: identifiers, temporal, network, crypto |

#### Application Layer Packages (`packages/application/`)

| File | Description |
|------|-------------|
| `config.mmd` | Config resolution and runtime |
| `factories.mmd` | Application factories: service, runtime, hooks, transform, record source |
| `files.mmd` | File-based record sources: CsvRecordSourceImpl, IdListRecordSourceImpl |
| `helpers.mmd` | Utility functions: primary key resolution |
| `mappers.mmd` | Record mappers: ChEMBL mapper |
| `metadata.mmd` | Run metadata builders |
| `pipelines.mmd` | Pipeline components: base, ChEMBL, stages, hooks, context |
| `ports.mmd` | Application-level ports: ObservabilityFactoryPortABC |
| `providers.mmd` | Default field providers |
| `runtime.mmd` | Pipeline runtime support |
| `services.mmd` | Application services: configuration, schema bootstrap, observability |
| `sources.mmd` | Record sources: API, CSV, ID list |
| `transform.mmd` | Batch adapters: PandasBatchAdapter |
| `use-cases.mmd` | Use cases: RunPipelineUseCase |

#### Infrastructure Layer Packages (`packages/infrastructure/`)

| File | Description |
|------|-------------|
| `adapters.mmd` | Port adapters: config loader adapter, pandas tabular adapter |
| `chembl.mmd` | ChEMBL-specific model registry |
| `clients.mmd` | HTTP clients: ChEMBL client, request builder, paginator, response parser |
| `config.mmd` | Config loaders: YAML loader, path resolver, provider loader |
| `files.mmd` | File operations: atomic writer, checksum calculator, path resolver |
| `http.mmd` | HTTP retry policies: ExponentialRetryPolicy |
| `logging.mmd` | Logging: progress reporter, unified logger |
| `observability.mmd` | Observability implementations: structlog, prometheus |
| `output.mmd` | Output writers: CSV, Parquet, metadata, QC reports |
| `settings.mmd` | Configuration constants: timeouts, retry, connection pool |
| `transform.mmd` | Transform implementations: hash service, normalizer, timestamp provider |
| `validation.mmd` | Validation: Pandera validator, schema implementations |

#### Interfaces Layer Packages (`packages/interfaces/`)

| File | Description |
|------|-------------|
| `cli.mmd` | CLI commands: Typer application, command groups |
| `factories.mmd` | Interface factories: infrastructure, observability |
| `monitoring.mmd` | Prometheus metrics integration |
| `rest.mmd` | REST API endpoints |

---

### 4. Class Diagrams by Object Type (`classes/`)

Cross-layer class diagrams organized by object type.

| File | Description |
|------|-------------|
| `01-factories.mmd` | All factory classes across layers |
| `02-services.mmd` | All service classes: domain, application, infrastructure |
| `03-ports-abc.mmd` | All abstract base classes and ports |
| `04-adapters.mmd` | All adapter implementations |
| `05-pipelines.mmd` | Pipeline class hierarchy |
| `06-validators.mmd` | Validation classes and schemas |
| `07-transformers.mmd` | Transformer and normalizer classes |
| `08-writers.mmd` | Output writer classes |
| `09-http-clients.mmd` | HTTP client classes |
| `10-record-sources.mmd` | Record source implementations |
| `11-error-policies.mmd` | Error handling policy classes |
| `12-domain-entities.mmd` | Domain entity classes |
| `13-value-objects.mmd` | Value object classes |
| `14-configs.mmd` | Configuration model classes |

---

### 5. Component Diagrams (`component/`)

C4-style component diagrams showing system structure.

| File | Description |
|------|-------------|
| `01-application-components.mmd` | Application layer component diagram |
| `02-domain-components.mmd` | Domain layer component diagram |
| `03-infrastructure-components.mmd` | Infrastructure layer component diagram |
| `04-interfaces-components.mmd` | Interfaces layer component diagram |
| `05-system-context-bioetl.mmd` | System context diagram |
| `06-hexagonal-architecture.mmd` | Hexagonal architecture overview |
| `07-physical-layer-mapping.mmd` | Directory to layer mapping |
| `08-key-modules-overview.mmd` | Key modules overview |
| `09-architecture-rules.mmd` | Architecture constraints and rules |
| `10-cli-architecture.mmd` | CLI architecture |
| `11-test-suite-structure.mmd` | Test suite structure |

---

### 6. Flow Diagrams (`flow/`)

Process flows, data flows, and decision diagrams.

| File | Description |
|------|-------------|
| `api-to-storage-dataflow.mmd` | Complete data flow from API to storage |
| `chembl-pipeline-dependency-graph.mmd` | ChEMBL pipeline dependencies |
| `ci-workflow.mmd` | CI/CD workflow |
| `cli-extension-flow.mmd` | CLI extension flow |
| `cli-option-mapping.mmd` | CLI option mapping |
| `config-loading-flow.mmd` | Configuration loading process |
| `csv-input-flow.mmd` | CSV input processing flow |
| `ddd-layered-architecture.mmd` | DDD layered architecture |
| `domain-services-transform.mmd` | Domain services transform flow |
| `error-policy-flow.mmd` | Error policy decision flow |
| `etl-stage-dag.mmd` | ETL stage directed acyclic graph |
| `external-enrichment-flow.mmd` | External data enrichment flow |
| `high-level-architecture.mmd` | High-level architecture overview |
| `layer-dependency-graph.mmd` | Layer dependency graph |
| `pagination-flow.mmd` | Pagination mechanism flow |
| `pipeline-error-flowchart.mmd` | Pipeline error handling flowchart |
| `project-package-structure.mmd` | Project package structure |
| `rate-limiter-timeline.mmd` | Rate limiter timeline |
| `retry-policy-flow.mmd` | Retry policy decision flow |
| `testing-pyramid.mmd` | Testing pyramid |

---

### 7. Sequence Diagrams (`sequence/`)

Interaction diagrams showing message flows.

| File | Description |
|------|-------------|
| `chembl-api-request-sequence.mmd` | ChEMBL API request sequence |
| `cli-run-sequence.mmd` | CLI run command sequence |
| `manual-di-assembly-sequence.mmd` | Manual dependency injection assembly |
| `pipeline-hooks-sequence.mmd` | Pipeline hooks execution sequence |
| `pipeline-run-sequence.mmd` | Pipeline run sequence |

---

## Viewing Diagrams

### Option 1: VS Code Extension
Install the "Markdown Preview Mermaid Support" extension.

### Option 2: GitHub
GitHub renders Mermaid diagrams natively in markdown files.

### Option 3: Mermaid Live Editor
Copy diagram content to https://mermaid.live/

### Option 4: Generate PNG/SVG
```bash
# Install mermaid-cli
npm install -g @mermaid-js/mermaid-cli

# Generate PNG
mmdc -i diagram.mmd -o diagram.png

# Generate SVG
mmdc -i diagram.mmd -o diagram.svg

# Batch convert all diagrams
find . -name "*.mmd" -exec sh -c 'mmdc -i "$1" -o "${1%.mmd}.png"' _ {} \;
```

---

## Conventions

### Styling
- **Domain**: `fill:#e8f5e9,stroke:#2e7d32`
- **Application**: `fill:#e3f2fd,stroke:#1565c0`
- **Infrastructure**: `fill:#fff3e0,stroke:#ef6c00`
- **Interfaces**: `fill:#fce4ec,stroke:#c2185b`
- **Abstract/Ports**: `fill:#a5d6a7,stroke:#43a047`
- **External**: `fill:#dde7f2,stroke:#44546a`

### Naming
- Use lowercase with hyphens for filenames
- Prefix numbered diagrams for ordering (e.g., `01-`, `02-`)
- Use descriptive names that indicate content

### Diagram Types
- **Class diagrams**: Show class relationships and hierarchies
- **Component diagrams**: Show system structure (C4-style)
- **Flow diagrams**: Show processes and data flows
- **Sequence diagrams**: Show message interactions
