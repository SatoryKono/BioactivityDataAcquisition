______________________________________________________________________

Version: 1.0.2
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-08-13'

______________________________________________________________________

# Current State Inventory

This inventory is synchronized against the current worktree on 2026-08-27.
Code, configs, domain contracts, ADRs, and tests are the source of
truth; existing documentation is evidence only when it matches those sources.

## Scope

| Surface | Current count | Source of truth | Notes |
| --- | ---: | --- | --- |
| Entity pipeline configs | 27 | `configs/entities/**/*.yaml` | 22 provider configs plus 5 composite entity configs under `configs/entities/composite/`. |
| Composite merge configs | 5 | `configs/composites/*.yaml` | ADR-026 seed/enrich/merge policies for activity, assay, molecule, publication, target. |
| Workflow configs | 27 | `configs/workflows/*.yaml` | Strict `workflow.steps` DAG schema with `pipeline` and `transform` step kinds. |
| Entity data contracts | 27 | `configs/contracts/{chembl,composite,crossref,openalex,pubchem,pubmed,semanticscholar,uniprot}/*.yaml` | One contract per configured entity pipeline surface. |
| Error catalog | 1 | `configs/contracts/errors/error_catalog.yaml` | Canonical error-code taxonomy; not counted as an entity data contract. |
| Provider configs | 7 | `configs/providers/*.yaml` | ChEMBL, CrossRef, OpenAlex, PubChem, PubMed, Semantic Scholar, UniProt. |
| Grafana dashboards | 7 | `grafana/dashboards/*.json` | Trust/control-plane, overview, runtime, provider health, DQ, incident, run-explorer (Silver Reject Explorer removed 2026-07-23). |
| Domain port files | 82 | `src/bioetl/domain/ports/**/*.py` | 73 port modules + 9 package `__init__.py` (inventory: `reports/quality/domain-ports-inventory.json`); 25 top-level `*.py` including `__init__.py` and `_facade_support.py`. |

## Architecture Quality Evidence

Current committed quality artifacts agree on the following architecture evidence:

| Artifact | Current value | Source |
| --- | ---: | --- |
| Architecture quality score | `9.41` (`good_targeted_improvements`) | `reports/quality/debt-governance-gates.json`, `reports/quality/architecture-quality-scorecard.json` |
| Layer violations | `0` | `reports/quality/architecture-quality-scorecard.json`, `.importlinter` |
| Source modules in module coverage inventory | `2467` | `reports/quality/module-coverage-inventory.json` |
| Unmeasured / uncovered modules | `0` / `0` | `reports/quality/module-coverage-inventory.json`, `reports/quality/debt-governance-gates.json` |
| Coverage inventory status counts | `1582` fully covered, `883` partially covered, `2` with no executable lines | `reports/quality/module-coverage-inventory.json` |
| Hotspot family count | `5` | `reports/quality/architecture-quality-scorecard.json` |
| Families at fan-in budget | `1` (`application_services_control_plane` 2/2) | `reports/quality/hotspot-family-baseline.json`, scorecard metrics |
| Debt-governance gates | `45` pass, `0` warn, `0` fail | `reports/quality/debt-governance-gates.json` |
| Full-app duplication hotspot baseline | `0` actionable / `44` raw excluded clusters | `reports/quality/full-app-duplication-baseline.json` |

The full-app duplication baseline distinguishes actionable clusters from raw
excluded visibility: current actionable duplication is zero, while the retained
raw excluded count remains visible for audit traceability. Generated artifact
drift is currently clear (`stale_artifacts` are all false in
`reports/quality/debt-governance-gates.json`). The debt gate rollup now includes
`module_coverage_source_tree_hash_current`, so stale
`reports/quality/module-coverage-inventory.json` source-tree hashes are fail-fast
release-gate failures rather than hidden warning-only coverage drift. Module
coverage currently reports `0` unmeasured and zero uncovered source modules
from the committed coverage inventory (debt-governance gates). That is a module-inventory fact, not
a blanket line/branch coverage guarantee: `883` modules
remain partially covered and line/branch coverage must be read from the
`coverage-verify` artifacts. Read-only
audit evidence should use
`python -m scripts.engineering.qa run-architecture-audit-read-only`, which runs
check-only architecture diagnostics and fails if tracked governance surfaces
mutate.
Baseline refreshes must preserve or lower scorecard budgets, hotspot family
caps, SCC budgets, and exemption limits; if refreshed evidence hits a budget,
reduce scope or debt instead of increasing the budget.

## Workflow Inventory

Full workflow catalog: [Workflow Catalog](../04-reference/workflow-catalog.md).

Observed facts:

- The config root is `WorkflowConfig` in `src/bioetl/domain/workflow/config.py`.
- Strict YAML validation is owned by `WorkflowConfigFileSchema` and
  `WorkflowConfigSchema` in `src/bioetl/infrastructure/schemas/workflow_config.py`.
- DAG invariants are enforced in `src/bioetl/domain/workflow/dag.py`.
- Runtime execution and mutable state-transition orchestration are owned by
  `src/bioetl/application/services/workflow/`.
- Immutable manifest, append-only ledger, and inspection services remain in
  `src/bioetl/application/services/control_plane/workflow/`.

| Object family | Files | Purpose | Dependencies | Layer |
| --- | --- | --- | --- | --- |
| Workflow config model | `src/bioetl/domain/workflow/config.py` | Immutable workflow definition, defaults, and step models. | `topologically_sorted_step_ids` from `domain.workflow.dag`; no I/O. | Domain |
| Workflow schema validation | `src/bioetl/infrastructure/schemas/workflow_config.py` | Pydantic strict YAML contract and conversion to domain model. | Domain workflow config classes. | Infrastructure |
| Workflow execution | `src/bioetl/application/services/workflow/**` | Executes workflow DAG steps and owns execution-state preparation, resume, and recording transitions. | Domain workflow config, control-plane ports, pipeline run services, transform services. | Application |
| Workflow control plane | `src/bioetl/application/services/control_plane/workflow/*.py` | Immutable manifest, append-only ledger, and inspection services. | Domain control-plane ports and infrastructure stores via DI. | Application |
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
| `PipelineRun` | `src/bioetl/domain/aggregates/pipeline_run.py`, `_pipeline_run_mixins.py` | Pipeline run state machine and stage result projection. | `PipelineRunState`, `StageResult`, `StageStatus`. | Domain |
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

Infrastructure -> Domain imports use BioETL's pragmatic Domain contract model:
infrastructure implementations may depend on Domain ports, exceptions,
entities, value objects, schema/config/lineage/control-plane contracts, and pure
Domain behavior helpers when implementing adapters, persistence, observability,
quality, export, or config loading. That scope is explicit and enforced by
`tests/architecture/test_layer_matrix_guards.py`; adding a new imported
`bioetl.domain.*` top-level package from Infrastructure requires policy review.
Policy id: `pragmatic_domain_contract_model`.
The existing outer-layer constraints remain unchanged: Infrastructure must not
import Application, Composition, or Interfaces, and Domain must not import
Infrastructure.

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
| Trust (Control Plane) | `grafana/dashboards/bioetl-control-plane-v1.json` | Manifest/ledger/control-plane status. | Observability |
| Overview | `grafana/dashboards/bioetl-overview-v2.json` | Operator summary, L0 status, Alert/SLO triage. | Observability |
| Pipeline Diagnostics (Runtime) | `grafana/dashboards/bioetl-runtime.json` | Runtime execution, blockers, workflow band. | Observability |
| Provider Health | `grafana/dashboards/bioetl-provider-health-v2.json` | Provider health and adapter status. | Observability |
| Data Quality | `grafana/dashboards/bioetl-dq-v2.json` | DQ scores, failures, quarantine metrics. | Observability |
| Incident Workspace | `grafana/dashboards/bioetl-incident-v1.json` | Multi-domain suspects + ALERTS support. | Observability |
| Run Explorer | `grafana/dashboards/bioetl-run-explorer-v1.json` | Exact-run Ops HTTP identity (no Prom `run_id` labels). | Observability |
| Prometheus rules | `grafana/prometheus-rules/*.yml` | Recording and alerting rules. | Observability |
| Datasource provisioning | `grafana/provisioning/datasources-core/*.yml` | Prometheus + BioETL Ops HTTP (Infinity → `:8000`). | Observability |

**Retired (not shipped JSON, 2026-07-23+):** `bioetl-workflow-overview`,
`bioetl-alerts-slo`, `bioetl-silver-reject-explorer`; Loki/Tempo /
`datasources-tracing` / Quarantine Explorer UI. Canonical inventory:
`docs/03-guides/dashboards/dashboard-inventory.md`. Removal record:
`docs/05-operations/runbooks/monitoring-surface-reduction-2026-07-23.md`.

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

### Control-Plane Application Role Map

The application control-plane package is organized by use-case role rather than
by storage technology. Current owner boundaries:

| Role | Source files | Responsibility |
| --- | --- | --- |
| Manifest service orchestration | `src/bioetl/application/services/control_plane/manifest/service.py`, `models.py`, `validation.py` | Create/inspect immutable run manifests and enforce application-level manifest validation. |
| Manifest diagnostics aggregation | `src/bioetl/application/services/control_plane/manifest/diagnostics/base.py`, `summary.py`, `finalization.py` | Aggregate operator-facing diagnostics by delegating to narrower projection/materialization helpers. |
| Provenance projection | `src/bioetl/application/services/control_plane/manifest/diagnostics/base_provenance_payloads.py` | Build code-provenance state and code-provenance payload sections for diagnostics summaries. |
| Replay context and projection | `src/bioetl/application/services/control_plane/manifest/diagnostics/base_replay_context.py`, `replay_projection.py`, `replay_invariants/**` | Resolve replay/resume context, exact-replay blockers, and operator replay projections. |
| Snapshot materialization | `src/bioetl/application/services/control_plane/manifest/diagnostics/snapshot_*.py` | Project input-snapshot IDs, hashes, materialization mode, and ledger-derived snapshot summaries. |
| Ledger recording | `src/bioetl/application/services/control_plane/ledger/**` | Append and inspect run-ledger events through domain control-plane ports. |
| Historical replay services | `src/bioetl/application/services/control_plane/replay/**` | Historical replay closure, corpus/universe policy, certification, and reproducibility scorecards. |
| Workflow state transitions | `src/bioetl/application/services/workflow/control_plane/**` | Workflow execution preparation, resume, recording, and mutable execution-state coordination. |
| Workflow control-plane services | `src/bioetl/application/services/control_plane/workflow/**` | Workflow manifest, append-only ledger, and inspection. |

## Documentation Drift Resolved In This Update

| Drift | Evidence | Current source of truth | Action |
| --- | --- | --- | --- |
| Quality evidence artifacts were stale after source-tree and remote-main drift | `report-module-coverage --check` and `report-debt-governance-gates --check` were previously failing in local audit evidence. | `reports/quality/module-coverage-inventory.json`, `reports/quality/architecture-quality-scorecard.json`, `reports/quality/architecture-debt-remote-main-baseline.json`, `reports/quality/debt-governance-gates.json`. | Refreshed the source-bound `remote_main_baseline` and restored all 45 debt-governance gates without increasing budgets. |
| Architecture audit read-only path was implicit | Existing dev pytest wrappers can run pretest sync before evidence collection. | `python -m scripts.engineering.qa run-architecture-audit-read-only`; `configs/quality/test_matrix.yaml` lane `architecture-read-only-audit`. | Added a diagnostic check-only command and documented its mutation guard in the testing guide. |
| Control-plane diagnostics role ownership was too implicit | `base_payload_sections.py` mixed code-provenance payload assembly with replay/snapshot payload assembly. | `base_provenance_payloads.py` owns provenance state and payload sections; `base_payload_sections.py` composes provenance, replay, and snapshot payloads. | Moved code-provenance payload assembly into the provenance role module and documented the control-plane role map. |
| Duplication baseline still reflected the older manifest-diagnostics cluster shape | `reports/quality/duplication-baseline.md` previously reported `129` total clusters with `application=99`. | `reports/quality/duplication-baseline.json` generated on 2026-06-18 reports `127` total clusters with `application=97`, `composition=30`. | Regenerated the report-only duplication baseline after the targeted control-plane diagnostics split. |
| ADR-048 was missing from MkDocs decision nav before this update | `mkdocs.yml` listed through ADR-047 only. | `docs/02-architecture/decisions/ADR-048-domain-schema-boundary-and-runtime-pandera-compat.md`. | Added ADR-048 to nav and overview. |
| Composite pipeline docs understated entity-config surface | `docs/04-reference/pipelines/README.md` described composite configs only through `configs/composites/*.yaml`. | `configs/entities/composite/*.yaml` plus `configs/composites/*.yaml`. | Documented both entity and merge config surfaces. |
| Domain storage port wording mixed application aggregate protocol into domain ports | `docs/02-architecture/01-domain-layer.md` listed `PipelineStorageProtocol` with domain storage ports. | `src/bioetl/application/core/pipeline_runtime_service_protocols.py`. | Described it as application-owned aggregate protocol. |
| Docs guardrail command used obsolete module wording | `docs/00-project/governance/07-doc-nav-policy.md` and `docs/00-project/RULES.md` used the historical `check_doc_links` name. | `python -m scripts.docs check-links`; dispatch in `scripts/docs/__main__.py`. | Updated active policy wording to the current command/module. |
| README architecture sketch used outdated single-bootstrap wording | `README.md` architecture sketch referenced `bootstrap_pipeline_runner() -> Factories`. | Composition public APIs and runtime bootstrap files under `src/bioetl/composition/`. | Updated README sketch to current composition APIs. |
| Filter migration folder reused the ADR-048 number after canonical ADR-048 was accepted for another decision | A retired filter draft previously used an ADR-like filename; canonical accepted ADR-048 is `docs/02-architecture/decisions/ADR-048-domain-schema-boundary-and-runtime-pandera-compat.md`. | Filter compatibility is implemented in `src/bioetl/infrastructure/config/silver_filter_migration.py`; future filter decisions need a new ADR number. | Renamed the filter draft to `docs/99-archive/filters/retired-silver-filters-structural-scope.md` and kept ADR-050 as the normative filter-boundary decision. |
| Generated artifact drift gate did not include module coverage source-tree hash freshness | `report-module-coverage --check` could fail stale source-tree evidence while `report-debt-governance-gates --check` still passed. | `scripts/engineering/qa/report_debt_governance_gates.py`; `reports/quality/debt-governance-gates.json`. | Added `module_coverage_source_tree_hash_current` as a fail-fast debt-governance gate. |
| Compatibility retained entrypoint inventory still tracked a zero-import maintenance CLI seam | `reports/quality/compatibility-importer-census.json` now reports `retained_entrypoint_count=12` and no retained row for `src/bioetl/interfaces/cli/commands/maintenance.py`. | `configs/quality/compatibility_facade_inventory.yaml`, `configs/quality/debt_scorecard.yaml`. | Removed the zero-import maintenance CLI command from retained-entrypoint debt tracking while leaving normal CLI lazy discovery intact. |
| Composite config compatibility taxonomy retained cross-provider alias leaves | `reports/quality/config-compatibility-legacy-taxonomy-review.json` now reports `composite_runtime.compatibility_legacy_count=0`. | `configs/field_registry/canonical_registry.json`; `bioetl.domain.registry.field_aliases`; `reports/quality/config-discrepancy-baseline.json`. | Removed residual composite `field_aliases` leaves from configs; HBA/HBD/logp/polar_surface_area ownership now remains in canonical registry and domain alias registry. |
| Domain context exposed direct wall-clock creation | `src/bioetl/domain/context.py` no longer defines `current_utc_time`; effective-config domain artifacts use deterministic sentinel defaults. | `src/bioetl/application/runtime_clock.py`, `src/bioetl/infrastructure/time/system_clock.py`, `tests/architecture/test_time_seam_normalization.py`. | Moved runtime clock helpers to application/infrastructure seams and guarded domain defaults against wall-clock regressions. |
| Runtime Gold Pandera strictness had no production-path non-strict guard | `tests/architecture/test_gold_validator_strict_runtime_paths.py` scans `src/bioetl` for `PanderaGoldValidator(..., strict=False)` and `ContractAwareGoldValidator(..., strict=False)`. | `src/bioetl/infrastructure/storage/silver/merged_operations.py`; `src/bioetl/infrastructure/validation/pandera_validator.py`. | Replaced the Silver merged-write non-strict Gold validator with `PanderaSilverValidator(strict=False)` and added the runtime guard. |
| Quarantine payload immutability evidence stopped at aggregate/mock level | `tests/unit/infrastructure/quarantine/test_unified_quarantine.py::TestUnifiedQuarantineUpdateStatus::test_update_status_preserves_persisted_payload_and_hash` writes a real Delta table, updates status, and checks persisted `payload`, `payload_hash`, and `metadata`. | `src/bioetl/infrastructure/quarantine/unified.py`. | Added persisted immutability coverage and a read fallback for Delta string-view filter failures after status updates. |
| Test governance refined assertless residuals are now fully eliminated while compatibility coverage stays bounded | `reports/quality/test-governance-current.json` now reports `assertless_total_candidates=87`, `refined_assertless_tests=0`, `compatibility_test_files=0`, and zero budget violations. | Contract schema tests under `tests/contract/**` plus governance inventory under `tests/architecture/**`. | Tightened observable assertions and governance classification so the refined assertless residual count is zero without regrowing compatibility-test scope. |
| Current-state architecture evidence table lagged live quality reports | `reports/quality/debt-governance-gates.json` reports score `9.41`, `45` passing gates, and zero failing gates; `reports/quality/module-coverage-inventory.json` reports `2467` source modules with zero unmeasured, zero uncovered, and `883` partially covered modules; `reports/quality/full-app-duplication-baseline.json` reports `0` actionable / `44` raw excluded clusters. | Current committed `reports/quality/*.json` artifacts and `reports/quality/total-tech-debt-audit-main-current.md`. | Refreshed the current-state table while keeping module inventory distinct from full line/branch coverage and preserving shrink-only budgets. |

## Open Questions

- Module coverage currently has zero unmeasured and zero uncovered source modules
  in `reports/quality/module-coverage-inventory.json`, while `883` modules remain
  partially covered. The inventory is current release evidence for module
  measurement status; do not describe it as complete line/branch coverage.
- Hotspot family `application_services_control_plane` sits **at**
  `max_internal_fan_in` budget (2/2) on
  `replay.reproducibility_score_cards_types`; `application_core` is
  below budget (6/10). Treat as residual density headroom under RF-023 —
  reduce fan-in via focused extraction, never by raising budgets.
- Diagram bundles and rendered artifacts have been refreshed for the known
  `QuarantineEntry` transition wording drift. `PipelineStorageProtocol` remains
  valid only as an application-owned aggregate protocol and must not be listed as
  a domain storage port.
