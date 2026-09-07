______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-08-05'

______________________________________________________________________

# Current State Diagrams

These Mermaid diagrams summarize the current BioETL architecture from code and
configuration evidence. Canonical rendered historical diagram bundles remain in
`docs/02-architecture/diagrams/`; this page is the compact current-state view
used by documentation audits.

Evidence anchors:

- Layers: `src/bioetl/domain/`, `src/bioetl/application/`,
  `src/bioetl/infrastructure/`, `src/bioetl/composition/`,
  `src/bioetl/interfaces/`.
- Runtime control plane:
  `src/bioetl/domain/control_plane/`,
  `src/bioetl/application/services/control_plane/`,
  `src/bioetl/infrastructure/control_plane/`.
- Workflow model:
  `src/bioetl/domain/workflow/config.py`,
  `src/bioetl/infrastructure/schemas/workflow_config.py`,
  `configs/workflows/*.yaml`.
- Pipeline/config model:
  `configs/entities/**/*.yaml`, `configs/composites/*.yaml`,
  entity data contracts under `configs/contracts/{provider}/*.yaml`, and the
  separate error catalog at `configs/contracts/errors/error_catalog.yaml`.
- Observability (optional local stack per ADR-010 / ADR-053):
  `src/bioetl/infrastructure/observability/`, optional
  `grafana/dashboards/*.json`, optional `grafana/prometheus-rules/*.yml`.
  Default BioETL remains local-only; Prometheus/Grafana are **not** required.
  Loki, Tempo, and Quarantine Explorer UI are **not** part of the current
  default shipping surface (historical / retired from main Docker compose).

## C4 Context

<!-- diagram-audit:summary-only -->

```mermaid
C4Context
    title BioETL C4 Context
    Person(operator, "Operator / Developer", "Runs local ETL, diagnostics, replay, and documentation checks")
    System(bioetl, "BioETL", "Local-first ETL platform for bioactivity data")
    System_Ext(chembl, "ChEMBL API", "Activity, assay, molecule, target, publication, reference data")
    System_Ext(pubchem, "PubChem API", "Compound data")
    System_Ext(uniprot, "UniProt API", "Protein and ID mapping data")
    System_Ext(publication, "Publication APIs", "PubMed, CrossRef, OpenAlex, Semantic Scholar")
    System_Ext(grafana, "Grafana / Prometheus (optional)", "Optional local metrics UI per ADR-010/ADR-053")
    System_Ext(files, "Local filesystem", "Data, checkpoints, manifests, ledgers, config artifacts")

    Rel(operator, bioetl, "Runs CLI commands and diagnostics")
    Rel(bioetl, chembl, "Fetches provider data through adapters")
    Rel(bioetl, pubchem, "Fetches compounds")
    Rel(bioetl, uniprot, "Fetches proteins and mappings")
    Rel(bioetl, publication, "Enriches publication metadata")
    Rel(bioetl, files, "Writes medallion data and control-plane artifacts")
    Rel(grafana, bioetl, "Optionally scrapes metrics when monitoring is enabled")
```

## C4 Container

<!-- diagram-audit:summary-only -->

```mermaid
C4Container
    title BioETL C4 Container View
    Person(operator, "Operator")
    System_Boundary(bioetl, "BioETL") {
        Container(cli, "ETL CLI process", "Python / Click", "Pipeline and workflow execution; five architecture layers inside one process")
        Container(health, "Health and ops backend (optional)", "Python / HTTP", "python -m bioetl health server; separate local process")
        ContainerDb(localdata, "Local Data Root", "Filesystem/Delta/JSONL", "Bronze/Silver/Gold, checkpoints, manifests, ledgers")
    }
    System_Ext(providers, "External Provider APIs")
    System_Ext(obs, "Prometheus/Grafana (optional)")

    Rel(operator, cli, "Runs bioetl commands")
    Rel(operator, health, "Local health and ops GET requests")
    Rel(cli, providers, "HTTP/API calls through injected adapters")
    Rel(cli, localdata, "Reads/writes data, state and run reports")
    Rel(health, localdata, "Reads configured local artifact roots")
    Rel(obs, health, "Optionally scrapes exposed metrics")
```

Here C4 containers describe execution and data-store boundaries, not Docker
containers or Python layers. Composition, Application, Domain and Infrastructure
are in-process components of the package (see Layer Diagram below).

| Element | Implementation anchor |
| --- | --- |
| ETL CLI process | `pyproject.toml` entrypoint `bioetl.interfaces.cli:main`; `src/bioetl/composition/bootstrap/runtime/` |
| Optional health/ops process | `src/bioetl/interfaces/cli/commands/domains/health/observability_backend_process.py` launches `python -m bioetl health server`; `docker-compose.yml` packages the same command |
| Local data and control-plane stores | `src/bioetl/infrastructure/storage/`, `checkpoint/`, `control_plane/`, `quarantine/`; data and reports mounts in `docker-compose.yml` |
| Optional monitoring | `docker-compose.monitoring.yml`; ADR-010 and ADR-053 preserve the local-only default |

The backend has its own lifecycle and shares configured artifact roots with ETL.
Docker and monitoring remain optional packaging/observability choices.

## Layer Diagram

<!-- diagram-audit:summary-only -->

```mermaid
flowchart TB
    subgraph Interfaces["Interfaces: src/bioetl/interfaces"]
        CLI["CLI commands"]
        HTTP["HTTP health server"]
    end

    subgraph Composition["Composition: src/bioetl/composition"]
        APIs["entrypoints / execution_api / registry_api / control_plane_runtime"]
        Boot["bootstrap/runtime, bootstrap/cli"]
        Factories["factories/*"]
    end

    subgraph Application["Application: src/bioetl/application"]
        Core["core runner, executor, writer, processor"]
        Pipelines["provider pipelines and transformers"]
        Composite["composite seed/enrich/merge"]
        Services["DQ, workflow, control-plane, quarantine, checkpoint services"]
    end

    subgraph Domain["Domain: src/bioetl/domain"]
        Aggregates["Batch / PipelineRun / QuarantineEntry"]
        VOs["Value objects"]
        Ports["Ports"]
        Contracts["Control-plane and data contracts"]
    end

    subgraph Infrastructure["Infrastructure: src/bioetl/infrastructure"]
        Adapters["Provider adapters"]
        Storage["Bronze/Silver/Gold/checkpoint/quarantine storage"]
        Config["Config and schema loaders"]
        Obs["Metrics/tracing/logging adapters (optional Prometheus)"]
        Stores["File control-plane stores"]
    end

    CLI --> Composition
    HTTP --> Composition
    Composition --> Application
    Composition --> Infrastructure
    Composition --> Domain
    Application --> Domain
    Infrastructure --> Domain
```

## Dependency Direction

<!-- diagram-audit:summary-only -->

```mermaid
flowchart LR
    Domain["domain"]
    Application["application"]
    Infrastructure["infrastructure"]
    Composition["composition"]
    Interfaces["interfaces"]

    Application --> Domain
    Infrastructure --> Domain
    Composition --> Domain
    Composition --> Application
    Composition --> Infrastructure
    Interfaces --> Domain
    Interfaces --> Application
    Interfaces --> Composition

    Bad1["forbidden: domain -> application/infrastructure/interfaces"]:::bad
    Bad2["forbidden: application -> infrastructure"]:::bad
    Bad3["forbidden: interfaces -> infrastructure"]:::bad

    classDef bad fill:#fee2e2,stroke:#991b1b,color:#7f1d1d;
```

## Medallion Data Flow

<!-- diagram-audit:summary-only -->

```mermaid
flowchart LR
    Provider["Provider API or cached Bronze source"]
    Adapter["Infrastructure adapter<br/>DataSourcePort implementation"]
    Bronze["Bronze<br/>raw provider records"]
    Transformer["Application transformer<br/>Bronze -> Silver"]
    Silver["Silver<br/>normalized records"]
    DQ["DQ analyzers and validators"]
    Quarantine["Quarantine<br/>invalid or filtered records"]
    Gold["Gold<br/>curated contract output"]
    Control["RunManifest / RunLedger / Lineage"]

    Provider --> Adapter
    Adapter --> Bronze
    Bronze --> Transformer
    Transformer --> Silver
    Silver --> DQ
    DQ -->|pass| Gold
    DQ -->|reject / hard fail / filter| Quarantine
    Bronze --> Control
    Silver --> Control
    Gold --> Control
    Quarantine --> Control
```

## Composite Pipeline

<!-- diagram-audit:summary-only -->

```mermaid
flowchart TB
    Config["configs/composites/{entity}.yaml<br/>seed/enrichers/merge/cross_validation"]
    EntityConfig["configs/entities/composite/{entity}.yaml<br/>entity pipeline contract"]
    Seed["Seed pipeline"]
    Keys["KeyExtractorService"]
    Enrichers["EnrichmentCoordinatorService<br/>fan-out enrichers"]
    CrossValidate["EnrichmentCrossValidator"]
    Merge["MergeService"]
    Gold["Composite Gold output"]
    Ledger["Composite checkpoint / lineage / manifest evidence"]

    Config --> Seed
    EntityConfig --> Seed
    Seed --> Keys
    Keys --> Enrichers
    Enrichers --> CrossValidate
    CrossValidate --> Merge
    Merge --> Gold
    Seed --> Ledger
    Enrichers --> Ledger
    Merge --> Ledger
```

## Run Lifecycle

<!-- diagram-audit:summary-only -->

```mermaid
stateDiagram-v2
    [*] --> ResolveConfig
    ResolveConfig --> BuildManifest
    BuildManifest --> AcquireLock
    AcquireLock --> Preflight
    Preflight --> ExecutePipeline
    ExecutePipeline --> WriteBronze
    WriteBronze --> TransformSilver
    TransformSilver --> ValidateDQ
    ValidateDQ --> WriteGold: pass
    ValidateDQ --> Quarantine: reject/filter/hard-fail
    WriteGold --> Postrun
    Quarantine --> Postrun
    Postrun --> AppendLedger
    AppendLedger --> ReleaseLock
    ReleaseLock --> [*]
```

## Quarantine Lifecycle

<!-- diagram-audit:summary-only -->

```mermaid
stateDiagram-v2
    [*] --> NEW
    NEW --> UNDER_REVIEW: start_review()
    NEW --> IGNORED: mark_ignored()
    NEW --> REPROCESSED: mark_reprocessed(new_record_id)
    NEW --> EXPIRED: mark_expired()
    UNDER_REVIEW --> IGNORED: mark_ignored()
    UNDER_REVIEW --> REPROCESSED: mark_reprocessed(new_record_id)
    UNDER_REVIEW --> EXPIRED: mark_expired()
    IGNORED --> [*]
    REPROCESSED --> [*]
    EXPIRED --> [*]
```

## Workflow DAG

<!-- diagram-audit:summary-only -->

```mermaid
flowchart LR
    YAML["configs/workflows/*.yaml"]
    Schema["WorkflowConfigFileSchema<br/>infrastructure/schemas/workflow_config.py"]
    Domain["WorkflowConfig<br/>domain/workflow/config.py"]
    DAG["topologically_sorted_step_ids<br/>domain/workflow/dag.py"]
    Runner["WorkflowRunnerService"]
    PipelineStep["pipeline step<br/>pipeline_name + run_options"]
    TransformStep["transform step<br/>transform_name + config"]
    WorkflowCP["workflow manifest / ledger / execution state"]

    YAML --> Schema
    Schema --> Domain
    Domain --> DAG
    DAG --> Runner
    Runner --> PipelineStep
    Runner --> TransformStep
    Runner --> WorkflowCP
```
