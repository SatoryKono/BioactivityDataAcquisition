______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-06-03'

______________________________________________________________________

# Current State Inventory

This inventory is synchronized against the current `main` worktree on
2026-06-03. Code, configs, domain contracts, ADRs, and tests are the source of
truth; existing documentation is evidence only when it matches those sources.

## Scope

| Surface | Current count | Source of truth | Notes |
| --- | ---: | --- | --- |
| Entity pipeline configs | 27 | `configs/entities/**/*.yaml` | 22 provider configs plus 5 composite entity configs under `configs/entities/composite/`. |
| Composite merge configs | 5 | `configs/composites/*.yaml` | ADR-026 seed/enrich/merge policies for activity, assay, molecule, publication, target. |
| Workflow configs | 27 | `configs/workflows/*.yaml` | Strict `workflow.steps` DAG schema with `pipeline` and `transform` step kinds. |
| Data contracts | 27 | `configs/contracts/**/*.yaml` | One contract per configured entity pipeline surface. |
| Provider configs | 7 | `configs/providers/*.yaml` | ChEMBL, CrossRef, OpenAlex, PubChem, PubMed, Semantic Scholar, UniProt. |
| Grafana dashboards | 8 | `grafana/dashboards/*.json` | Overview, runtime, provider health, DQ, workflow, control-plane, alerts/SLO, silver reject explorer. |
| Domain port files | 73 | `src/bioetl/domain/ports/**/*.py` | 18 top-level files plus nested config, control-plane, metadata, observability, quality, runtime, and storage packages. |

## Workflow Inventory

Full workflow catalog: [Workflow Catalog](../04-reference/workflow-catalog.md).

Observed facts:

- The config root is `WorkflowConfig` in `src/bioetl/domain/workflow/config.py`.
- Strict YAML validation is owned by `WorkflowConfigFileSchema` and
  `WorkflowConfigSchema` in `src/bioetl/infrastructure/schemas/workflow_config.py`.
- DAG invariants are enforced in `src/bioetl/domain/workflow/dag.py`.
- Runtime execution is owned by
  `src/bioetl/application/services/workflow_runner_service.py`.
- Workflow control-plane services are in
  `src/bioetl/application/services/control_plane/workflow/`.

| Object family | Files | Purpose | Dependencies | Layer |
| --- | --- | --- | --- | --- |
| Workflow config model | `src/bioetl/domain/workflow/config.py` | Immutable workflow definition, defaults, and step models. | `topologically_sorted_step_ids` from `domain.workflow.dag`; no I/O. | Domain |
| Workflow schema validation | `src/bioetl/infrastructure/schemas/workflow_config.py` | Pydantic strict YAML contract and conversion to domain model. | Domain workflow config classes. | Infrastructure |
| Workflow runner | `src/bioetl/application/services/workflow_runner_service.py` | Executes workflow DAG steps and returns step-level result projection. | Domain workflow config, pipeline run services, transform services. | Application |
| Workflow control plane | `src/bioetl/application/services/control_plane/workflow/*.py` | Manifest, ledger, execution-state preparation, recording, and inspection. | Domain control-plane ports and infrastructure stores via DI. | Application |
| Workflow stores | `src/bioetl/infrastructure/control_plane/file_workflow_*_store.py` | File-backed manifest, ledger, and mutable execution-state persistence. | Domain control-plane ports; local filesystem. | Infrastructure |

## Pipeline Inventory

Full pipeline catalog: [Pipeline Catalog](../04-reference/pipeline-catalog.md).

| Object family | Files | Purpose | Dependencies | Layer |
| --- | --- | --- | --- | --- |
| Provider entity configs | `configs/entities/{provider}/{entity}.yaml` | Pipeline identity, schema, DQ, sink, and rollout policy. | Loaded by `src/bioetl/infrastructure/config/pipeline_config_api.py`; consumed by composition factories. | Config |
| Composite entity configs | `configs/entities/composite/*.yaml` | Entity-level composite pipeline contract and Gold sink enablement. | Same unified entity config path as provider pipelines. | Config |
| Composite merge configs | `configs/composites/*.yaml` | Seed, enrichers, merge, cross-validation, lineage, and execution policy. | Loaded by `src/bioetl/infrastructure/config/composite_config_api.py`. | Config |
| Pipeline factory registry | `src/bioetl/composition/factories/pipeline/registry.py` | Registers provider/composite factories for composition-time lookup. | Composition registry API and pipeline factories. | Composition |
| Generic pipeline factory | `src/bioetl/composition/factories/pipeline/assembler.py` | Builds pipeline instances from config, transformer, datasource, storage, and services. | Domain ports, application pipeline classes, infrastructure adapters. | Composition |
| Pipeline runner | `src/bioetl/application/core/runner.py` | Orchestrates lock, preflight, execution, postrun, observability, and cleanup. | Application services and domain ports only. | Application |
| Composite runner | `src/bioetl/application/composite/runner_pkg/runner.py` | Executes ADR-026 seed -> enrich -> merge flow. | Composite config, checkpoint service, coordinator, merger. | Application |

## Domain Model

### Aggregates

| Aggregate | Source files | Purpose | Key dependencies | Layer |
| --- | --- | --- | --- | --- |
| `Batch` | `src/bioetl/domain/aggregates/_batch_aggregate.py`, `batch.py` | Batch lifecycle and batch-level record accounting. | `BatchRecord`, `BatchStatus`, domain events. | Domain |
| `PipelineRun` | `src/bioetl/domain/aggregates/pipeline_run.py`, `_pipeline_run_mixins.py`, `_pipeline_run_read_model_mixin.py` | Pipeline run state machine and stage result projection. | `PipelineRunState`, `StageResult`, `StageStatus`. | Domain |
| `QuarantineEntry` | `src/bioetl/domain/aggregates/_quarantine_aggregate.py`, `quarantine_entry.py` | Quarantine lifecycle, review, ignore, reprocess, and expiry transitions. | `QuarantineStatus`, `ResolutionInfo`. | Domain |

### Domain Events

| Event family | Source file | Events |
| --- | --- | --- |
| Pipeline lifecycle | `src/bioetl/domain/aggregates/events.py` | `PipelineCompleted`, `PipelineFailed`, `PipelineShutdown` |
| Batch lifecycle | `src/bioetl/domain/aggregates/events.py` | `BatchCreated`, `BatchSealed`, `BatchWritten`, `BatchFailed`, `RecordQuarantined` |
| Quarantine lifecycle | `src/bioetl/domain/aggregates/events.py` | `QuarantineEntryCreated`, `QuarantineEntryResolved` |
| Generic pipeline event | `src/bioetl/domain/events.py` | `PipelineEvent` |

### Value Object Families

| Family | Source files | Purpose | Layer |
| --- | --- | --- | --- |
| Chemical identifiers | `src/bioetl/domain/value_objects/_chemical_identifiers.py`, `identifiers.py`, `inchi.py` | ChEMBL, PubChem, SMILES, InChI, InChIKey identifiers. | Domain |
| Molecular descriptors | `src/bioetl/domain/value_objects/_molecular_weight.py`, `molecular_descriptors.py` | Bounded molecular numeric value objects. | Domain |
| Activity values | `src/bioetl/domain/value_objects/activity_*.py`, `pchembl_value.py` | Concentration, relation, type, confidence, and pChEMBL values. | Domain |
| Publication identifiers | `src/bioetl/domain/value_objects/publications.py`, `academic_ids.py`, `_publication_year.py` | DOI, PMID, OpenAlex, Semantic Scholar, ISSN, ORCID, publication year. | Domain |
| DQ result model | `src/bioetl/domain/value_objects/dq_*.py` | DQ metrics, report result objects, anomalies, and evaluation status. | Domain |
| Runtime context/result | `src/bioetl/domain/value_objects/run_context.py`, `_run_context_models.py`, `bronze_result.py`, `silver_result.py` | Immutable run context and write result value objects. | Domain |
| Taxonomy/protein class | `src/bioetl/domain/value_objects/taxonomy_id.py`, `protein_class_hierarchy.py` | Taxonomy and protein classification value objects. | Domain |

### Ports

| Port family | Source files | Purpose | Implemented by |
| --- | --- | --- | --- |
| Data source and filtering | `src/bioetl/domain/ports/data_source.py`, `filtering.py` | Fetch/filter contracts for provider adapters. | `src/bioetl/infrastructure/adapters/**` |
| Storage | `src/bioetl/domain/ports/storage/*.py`, `storage_maintenance.py` | Narrow Bronze/Silver/Gold/Merged/lifecycle storage contracts. | `src/bioetl/infrastructure/storage/**` |
| Runtime control | `src/bioetl/domain/ports/runtime/*.py` | Lock, checkpoint, clock, runner, registry, shutdown, debug, memory. | Application/composition/infrastructure runtime services. |
| Observability | `src/bioetl/domain/ports/observability/*.py`, `logger_port.py` | Logger, metrics, tracing, DQ monitor contracts. | `src/bioetl/infrastructure/observability/**` and NoOp ports. |
| Quality | `src/bioetl/domain/ports/quality/*.py` | DQ config, analyzers, reports, quarantine, validation, fallback/error policy. | `src/bioetl/application/services/dq/**`, `src/bioetl/infrastructure/quality/**`. |
| Control plane | `src/bioetl/domain/ports/control_plane/*.py` | Run/workflow manifest, ledger, effective config, lineage, artifact comparison stores. | `src/bioetl/infrastructure/control_plane/**`. |
| Config/metadata/export | `src/bioetl/domain/ports/config/*.py`, `metadata/*.py`, `export.py` | Config loading, metadata writing/coordinating, export catalog/writer. | Infrastructure config, metadata, and export adapters. |

`PipelineStorageProtocol` is intentionally not a domain port. It is an
application-owned aggregate protocol in
`src/bioetl/application/core/pipeline_runtime_service_protocols.py` that combines
the narrow domain storage ports for one pipeline service bundle.

## Application Layer

| Component | Source files | Purpose | Dependencies | Layer |
| --- | --- | --- | --- | --- |
| Core execution | `src/bioetl/application/core/{runner.py,batch_executor.py,batch_writer.py,record_processor.py}` | Pipeline lifecycle, batch execution, record normalization, medallion writes. | Domain ports and value objects. | Application |
| Pipeline implementations | `src/bioetl/application/pipelines/**` | Provider-specific transformers and pipeline behaviors. | Domain entities/value objects and injected ports. | Application |
| Composite pattern | `src/bioetl/application/composite/**` | ADR-026 seed/enrich/merge orchestration and merge support. | Composite config and injected pipeline/runtime services. | Application |
| Control-plane services | `src/bioetl/application/services/control_plane/**` | RunManifest, RunLedger, effective config, replay, workflow state, diagnostics. | Domain control-plane artifacts and ports. | Application |
| DQ services | `src/bioetl/application/services/dq/**`, `data_quality_service.py`, `dq_report_service.py` | Bronze/Silver/Gold analyzers, DQ report generation, thresholds, anomalies. | Domain DQ VOs and quality ports. | Application |
| Operator services | `src/bioetl/application/services/{checkpoint_service.py,quarantine_service.py,metrics_service.py,health_service.py}` | CLI/admin inspection and runtime-adjacent orchestration. | Domain ports; concrete stores through DI. | Application |

## Infrastructure Layer

| Component | Source files | Purpose | Dependencies | Layer |
| --- | --- | --- | --- | --- |
| Provider adapters | `src/bioetl/infrastructure/adapters/{chembl,crossref,openalex,pubchem,pubmed,semanticscholar,uniprot}/` | External API clients, health probes, parsing, fallback, and response mapping. | Domain ports/entities; HTTP client/resilience helpers. | Infrastructure |
| Common HTTP/resilience | `src/bioetl/infrastructure/adapters/http/**`, `decorators/**`, `common/**` | Unified HTTP client, rate limiting, circuit breaker, retry, fallback/title matching. | Domain resilience and health ports. | Infrastructure |
| Config loaders | `src/bioetl/infrastructure/config/**` | Unified entity, composite, workflow, DQ, contract, provider config loading. | Config YAML and domain/application config models. | Infrastructure |
| Storage | `src/bioetl/infrastructure/storage/**` | Bronze/Silver/Gold/metadata/quarantine/checkpoint/local file and Delta-backed persistence. | Domain storage/runtime ports. | Infrastructure |
| Control-plane stores | `src/bioetl/infrastructure/control_plane/**` | File-backed manifests, ledgers, effective config, lineage, workflow stores, replay artifacts. | Domain control-plane ports. | Infrastructure |
| Observability | `src/bioetl/infrastructure/observability/**` | Prometheus metrics, metrics server, tracing/logging adapters, Pushgateway publication. | Domain observability ports. | Infrastructure |
| Quality/export | `src/bioetl/infrastructure/quality/**`, `export/**` | DQ config/runtime support, debt scorecards, export adapters. | Domain quality/export ports. | Infrastructure |

## DQ Validators

| Component | Source file | Purpose | Layer |
| --- | --- | --- | --- |
| Bronze analyzer | `src/bioetl/application/services/dq/bronze_analyzer.py` | Bronze DQ report and raw-layer quality checks. | Application |
| Silver analyzer | `src/bioetl/application/services/dq/silver_analyzer.py` | Silver DQ report and normalized-layer quality checks. | Application |
| Gold analyzer | `src/bioetl/application/services/dq/gold_analyzer.py` | Gold DQ report and curated-layer quality checks. | Application |
| Basic/business/integrity/statistical checks | `src/bioetl/application/services/dq/_checks_*.py` | Shared check families used by analyzers. | Application |
| Silver check executor | `src/bioetl/application/services/dq/silver_check_executor.py` | Executes configured Silver checks and projects outcomes. | Application |
| DQ config loader | `src/bioetl/infrastructure/config/dq_config_loader.py` | Reads DQ config from YAML. | Infrastructure |
| Contract DQ loader | `src/bioetl/infrastructure/config/dq_contract_config_loader.py` | Loads contract-aware DQ policy. | Infrastructure |

## Silver/Gold Filter Compatibility

Observed facts:

- `configs/entities/**/*.yaml` contains 27 entity pipeline configs; 22 of them
  currently include `filters.silver_filters`, and active Silver filters are now
  structural-only (`required_fields` and `exclude_if_present`).
- Runtime config loading rejects semantic Silver keys before the domain Silver
  filter is built. The infrastructure boundary validates the payload through
  `src/bioetl/infrastructure/config/silver_filter_migration.py`.
- `FilterConfigFile.reject_semantic_silver_filters()` in
  `src/bioetl/infrastructure/schemas/filter_config.py` and
  `PipelineYamlConfig.reject_semantic_silver_filters()` in
  `src/bioetl/infrastructure/schemas/pipeline_config.py` call
  `validate_no_semantic_silver_filter_payload()` before strict validation.
- `SilverFiltersFileConfig.to_domain()` and
  `SilverFiltersConfig.to_domain()` convert to structural-only
  `SilverFilterConfig` using
  `build_silver_filter_config_for_compatibility()`.

| Surface | File | Current behavior | Layer |
| --- | --- | --- | --- |
| Compatibility mode | `src/bioetl/infrastructure/config/silver_filter_migration.py` | Default mode is `structural_only_compat`; `structural_only_auto_promote` is a historical persisted identity alias only. | Infrastructure |
| Filter file schema | `src/bioetl/infrastructure/schemas/filter_config.py` | Legacy semantic Silver keys fail validation at the file boundary. | Infrastructure |
| Entity pipeline schema | `src/bioetl/infrastructure/schemas/pipeline_config.py` | Entity YAML payloads fail validation when semantic keys appear under `silver_filters`. | Infrastructure |
| Domain Silver filter projection | `src/bioetl/infrastructure/schemas/filter_config.py`, `src/bioetl/infrastructure/schemas/pipeline_config_common_schemas.py` | Domain Silver filter receives only `required_fields` and `exclude_if_present`. | Infrastructure -> Domain boundary |
| Legacy config inventory | `configs/entities/**/*.yaml` | Semantic Silver buckets have been removed from active YAML; reintroduction fails architecture guardrails. | Config |
| Source-profile metadata | `configs/entities/chembl/{activity,assay,molecule,publication,publication_term,target}.yaml` | Current curated ChEMBL extraction_params are versioned as baseline source profiles before any widening. | Config |

## Dashboards And Observability Components

| Dashboard/component | File | Purpose | Layer |
| --- | --- | --- | --- |
| Control Plane | `grafana/dashboards/bioetl-control-plane-v1.json` | Manifest/ledger/control-plane status. | Observability |
| Overview | `grafana/dashboards/bioetl-overview-v2.json` | Operator summary and pipeline health. | Observability |
| Runtime | `grafana/dashboards/bioetl-runtime.json` | Runtime execution and record accounting. | Observability |
| Provider Health | `grafana/dashboards/bioetl-provider-health-v2.json` | Provider health and adapter status. | Observability |
| Data Quality | `grafana/dashboards/bioetl-dq-v2.json` | DQ scores, failures, quarantine metrics. | Observability |
| Workflow Overview | `grafana/dashboards/bioetl-workflow-overview.json` | Workflow step status and rollups. | Observability |
| Alerts/SLO | `grafana/dashboards/bioetl-alerts-slo.json` | Alert and SLO status. | Observability |
| Silver Reject Explorer | `grafana/dashboards/bioetl-silver-reject-explorer.json` | Quarantine/silver reject drilldown. | Observability |
| Prometheus rules | `grafana/prometheus-rules/*.yml` | Recording and alerting rules. | Observability |
| Datasource provisioning | `grafana/provisioning/datasources/*.yml` | Prometheus, Loki, Tempo, Quarantine Explorer datasources. | Observability |

## Control Plane Components

| Component | Source file | Purpose | Layer |
| --- | --- | --- | --- |
| Run manifest artifact | `src/bioetl/domain/control_plane/run_manifest.py` | Immutable run intent/provenance snapshot. | Domain |
| Run ledger artifact | `src/bioetl/domain/control_plane/run_ledger.py` | Append-only event history. | Domain |
| Manifest service | `src/bioetl/application/services/control_plane/manifest/service.py` | Creates and inspects manifests. | Application |
| Ledger service | `src/bioetl/application/services/control_plane/ledger/service.py` | Appends and inspects ledger entries. | Application |
| Effective config service | `src/bioetl/application/services/control_plane/effective_config/service.py` | Produces semantic and occurrence effective-config artifacts. | Application |
| Replay services | `src/bioetl/application/services/control_plane/replay/**` | Historical replay closure, certification, corpus, universe, scorecards. | Application |
| Manifest stores | `src/bioetl/infrastructure/control_plane/file_run_manifest_store.py` | File-backed manifest persistence. | Infrastructure |
| Ledger stores | `src/bioetl/infrastructure/control_plane/file_run_ledger_store.py` | File-backed ledger persistence. | Infrastructure |
| Workflow stores | `src/bioetl/infrastructure/control_plane/file_workflow_*_store.py` | File-backed workflow manifest, ledger, and state stores. | Infrastructure |
| CLI inspection | `src/bioetl/interfaces/cli/commands/run_manifest.py` | Operator-facing manifest/ledger inspection command. | Interfaces |

## Documentation Drift Resolved In This Update

| Drift | Evidence | Current source of truth | Action |
| --- | --- | --- | --- |
| ADR-048 was missing from MkDocs decision nav before this update | `mkdocs.yml` listed through ADR-047 only. | `docs/02-architecture/decisions/ADR-048-domain-schema-boundary-and-runtime-pandera-compat.md`. | Added ADR-048 to nav and overview. |
| Composite pipeline docs understated entity-config surface | `docs/04-reference/pipelines/README.md` described composite configs only through `configs/composites/*.yaml`. | `configs/entities/composite/*.yaml` plus `configs/composites/*.yaml`. | Documented both entity and merge config surfaces. |
| Domain storage port wording mixed application aggregate protocol into domain ports | `docs/02-architecture/01-domain-layer.md` listed `PipelineStorageProtocol` with domain storage ports. | `src/bioetl/application/core/pipeline_runtime_service_protocols.py`. | Described it as application-owned aggregate protocol. |
| Docs guardrail command used obsolete module wording | `docs/00-project/governance/07-doc-nav-policy.md` and `docs/00-project/RULES.md` used the historical `check_doc_links` name. | `python -m scripts.docs check-links`; dispatch in `scripts/docs/__main__.py`. | Updated active policy wording to the current command/module. |
| README architecture sketch used outdated single-bootstrap wording | `README.md` architecture sketch referenced `bootstrap_pipeline_runner() -> Factories`. | Composition public APIs and runtime bootstrap files under `src/bioetl/composition/`. | Updated README sketch to current composition APIs. |
| Filter migration folder reused the ADR-048 number after canonical ADR-048 was accepted for another decision | `docs/filters/ADR-048-silver-filters-structural-scope.md` was a draft; canonical accepted ADR-048 is `docs/02-architecture/decisions/ADR-048-domain-schema-boundary-and-runtime-pandera-compat.md`. | Filter compatibility is implemented in `src/bioetl/infrastructure/config/silver_filter_migration.py`; future filter decisions need a new ADR number. | Marked the filter draft as retired/non-canonical and updated the filter migration docs to describe current code reality. |

## Open Questions

- The committed `reports/quality/module-coverage-inventory.json` source tree
  hash was observed stale during the current audit; documentation changes in
  this task do not refresh source-code quality artifacts because no
  `src/bioetl/**/*.py` files are changed.
- Existing historical diagram bundles still contain legacy `PipelineStorageProtocol`
  references. They are retained as historical/generated diagram material until a
  dedicated diagram regeneration pass refreshes rendered `.mmd`, SVG, and PNG
  artifacts.
