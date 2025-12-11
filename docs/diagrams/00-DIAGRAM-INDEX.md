# BioETL Architecture Diagrams

## Overview

This directory contains Mermaid diagrams for understanding the BioETL architecture, file structure, and implementation. All diagrams are organized by category.

## Directory Structure

```
docs/diagrams/
├── 00-DIAGRAM-INDEX.md          # This file
├── layers/                       # Layer-level component diagrams
│   ├── 01-domain-layer.mmd
│   ├── 02-application-layer.mmd
│   ├── 03-infrastructure-layer.mmd
│   └── 04-interfaces-layer.mmd
├── packages/                     # Package-level component diagrams
│   ├── domain/                   # Domain layer packages
│   │   ├── entities.mmd
│   │   ├── ports.mmd
│   │   ├── schemas.mmd
│   │   ├── configs.mmd
│   │   ├── services.mmd
│   │   ├── transform.mmd
│   │   ├── validation.mmd
│   │   ├── clients.mmd
│   │   └── value-objects.mmd
│   ├── application/              # Application layer packages
│   │   ├── factories.mmd
│   │   ├── services.mmd
│   │   ├── pipelines.mmd
│   │   ├── sources.mmd
│   │   ├── mappers.mmd
│   │   ├── use-cases.mmd
│   │   └── config.mmd
│   ├── infrastructure/           # Infrastructure layer packages
│   │   ├── clients.mmd
│   │   ├── output.mmd
│   │   ├── config.mmd
│   │   ├── transform.mmd
│   │   ├── validation.mmd
│   │   ├── files.mmd
│   │   ├── logging.mmd
│   │   └── adapters.mmd
│   └── interfaces/               # Interfaces layer packages
│       ├── cli.mmd
│       ├── factories.mmd
│       └── rest.mmd
├── classes/                      # Class diagrams by object type
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
└── overview/                     # High-level architecture diagrams
    ├── hexagonal-architecture.mmd
    ├── layer-dependencies.mmd
    ├── data-flow.mmd
    └── system-context.mmd
```

---

## Diagram Catalog

### 1. Layer Component Diagrams (`layers/`)

| File | Description |
|------|-------------|
| `01-domain-layer.mmd` | Domain layer components: entities, ports, schemas, services, value objects |
| `02-application-layer.mmd` | Application layer: factories, services, pipelines, use cases |
| `03-infrastructure-layer.mmd` | Infrastructure layer: adapters, clients, output writers, config loaders |
| `04-interfaces-layer.mmd` | Interface layer: CLI commands, REST API, composition root |

---

### 2. Package Component Diagrams (`packages/`)

#### Domain Layer Packages (`packages/domain/`)

| File | Description |
|------|-------------|
| `entities.mmd` | Domain entities: Activity, Assay, Target, Molecule, Publication |
| `ports.mmd` | Abstract ports: extraction, output, config, parsing, filters |
| `schemas.mmd` | Validation schemas: Pandera schemas, field specs, pipeline contracts |
| `configs.mmd` | Configuration models: pipeline, source, sink, execution |
| `services.mmd` | Domain services: entity factory, business key service, version formatter |
| `transform.mmd` | Transform contracts: normalizers, serializers, transformers |
| `validation.mmd` | Validation service contracts |
| `clients.mmd` | Client base contracts and resilience |
| `value-objects.mmd` | Value objects: identifiers, temporal, network, crypto |

#### Application Layer Packages (`packages/application/`)

| File | Description |
|------|-------------|
| `factories.mmd` | Application factories: service, runtime, hooks, transform, record source |
| `services.mmd` | Application services: configuration, schema bootstrap, observability |
| `pipelines.mmd` | Pipeline components: base, ChEMBL, stages, hooks, context |
| `sources.mmd` | Record sources: API, CSV, ID list |
| `mappers.mmd` | Record mappers: ChEMBL mapper |
| `use-cases.mmd` | Use cases: RunPipelineUseCase |
| `config.mmd` | Config resolution and runtime |

#### Infrastructure Layer Packages (`packages/infrastructure/`)

| File | Description |
|------|-------------|
| `clients.mmd` | HTTP clients: ChEMBL client, request builder, paginator, response parser |
| `output.mmd` | Output writers: CSV, Parquet, metadata, QC reports |
| `config.mmd` | Config loaders: YAML loader, path resolver, provider loader |
| `transform.mmd` | Transform implementations: hash service, normalizer, timestamp provider |
| `validation.mmd` | Validation: Pandera validator, schema implementations |
| `files.mmd` | File operations: atomic writer, checksum calculator, path resolver |
| `logging.mmd` | Logging: progress reporter, unified logger |
| `adapters.mmd` | Port adapters: config loader adapter, pandas tabular adapter |

#### Interfaces Layer Packages (`packages/interfaces/`)

| File | Description |
|------|-------------|
| `cli.mmd` | CLI commands: Typer application, command groups |
| `factories.mmd` | Interface factories: infrastructure, observability |
| `rest.mmd` | REST API endpoints |

---

### 3. Class Diagrams by Object Type (`classes/`)

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

### 4. Overview Diagrams (`overview/`)

| File | Description |
|------|-------------|
| `hexagonal-architecture.mmd` | Hexagonal architecture pattern overview |
| `layer-dependencies.mmd` | Layer dependency graph |
| `data-flow.mmd` | Data flow through ETL pipeline |
| `system-context.mmd` | System context and external integrations |

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
```

---

## Conventions

### Styling
- **Primary components**: `fill:#f5f5f5,stroke:#444`
- **Secondary components**: `fill:#e3e7ec,stroke:#555`
- **External/Interface**: `fill:#dde7f2,stroke:#44546a`
- **Domain**: `fill:#e8f5e9,stroke:#2e7d32`
- **Application**: `fill:#e3f2fd,stroke:#1565c0`
- **Infrastructure**: `fill:#fff3e0,stroke:#ef6c00`
- **Interfaces**: `fill:#fce4ec,stroke:#c2185b`

### Naming
- Use lowercase with hyphens for filenames
- Prefix layer diagrams with numbers for ordering
- Use descriptive names that indicate content
