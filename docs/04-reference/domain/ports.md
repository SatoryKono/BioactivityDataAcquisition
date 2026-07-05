______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-07-05'

______________________________________________________________________

# Domain Ports

## Purpose

`src/bioetl/domain/ports/` is the transport-neutral contract boundary for the
Ports & Adapters architecture in BioETL.

This page is the semantic catalog of port families and the complete module
inventory for `src/bioetl/domain/ports/**`. For module-by-module API
lookup, use [API Reference: domain ports](../api/domain/ports.md).

## Import Policy

- Sanctioned import surface: `bioetl.domain.ports`
- Internal modules under `domain/ports/**` are implementation structure, not
  the primary import path for first-party layers.

## Port Family Catalog

| Family | Representative modules | Purpose |
| --- | --- | --- |
| Config | `config/config_loader_port.py`, `config/config_port.py`, `config/publication_vocabulary_port.py` | Declarative config loading, settings, and vocabulary contracts. |
| Control plane | `control_plane/run_manifest.py`, `control_plane/run_ledger.py`, `control_plane/workflow_manifest.py`, `control_plane/workflow_ledger.py`, `control_plane/workflow_execution_state.py`, `control_plane/lineage.py` | Manifest, ledger, execution-state, lineage, and effective-config artifact contracts. |
| Metadata | `metadata/coordinator.py`, `metadata/writer.py` | Output metadata projection and coordination contracts. |
| Observability | `observability/logging.py`, `observability/metrics.py`, `observability/tracing.py`, `observability/dq_monitor.py` | Logging, metrics, tracing, and DQ-monitor emission seams. |
| Quality | `quality/validation.py`, `quality/quarantine.py`, `quality/dq_report.py`, `quality/contract_policy.py`, `quality/fallback_policy.py` | Validation, quarantine, contract-policy, and DQ reporting boundaries. |
| Runtime | `runtime/checkpoint.py`, `runtime/locking.py`, `runtime/runner.py`, `runtime/clock.py`, `runtime/shutdown.py`, `runtime/registry_port.py`, `runtime/composite_checkpoint.py` | Execution-time control contracts for checkpoints, locks, clocks, runners, shutdown, and registry lookups. |
| Storage | `storage/bronze_port.py`, `storage/silver_port.py`, `storage/gold_port.py`, `storage/merged_port.py`, `storage/lifecycle_port.py` | Storage-layer contracts for medallion and merged surfaces. |
| Cross-cutting flat ports | `data_source.py`, `filtering.py`, `health_check.py`, `serialization.py`, `resilience.py`, `publication_strategy.py`, `workflow_foreign_key_reconciliation.py`, `storage_maintenance.py`, `idmapping.py`, `protein_classification.py` | Narrow contracts that do not belong to a larger nested port family. |
| NoOp surfaces | `noop/_metrics.py`, `noop/_tracing.py`, `noop/_audit_pii.py`, `noop/_memory_metadata.py` | Safe optional-dependency fallbacks that preserve the domain contract without introducing infrastructure assumptions. |

## Complete Module Catalog

Every active module under `src/bioetl/domain/ports/**` (74 Python files).
`__init__.py` modules are package boundaries; protocol definitions live in the
named modules below.

| Module | Family | Purpose |
| --- | --- | --- |
| `__init__.py` | Package | Sanctioned public re-export surface (`bioetl.domain.ports`). |
| `adr.py` | Cross-cutting | ADR metadata and governance lookup contracts. |
| `audit.py` | Cross-cutting | Audit-event emission boundary for operator actions. |
| `data_normalization.py` | Cross-cutting | Normalization policy contracts for typed field cleanup. |
| `data_source.py` | Cross-cutting | Provider fetch and source-read contracts. |
| `delta_reader.py` | Cross-cutting | Delta/change-feed read contracts for incremental surfaces. |
| `export.py` | Cross-cutting | Export and artifact handoff contracts. |
| `filtering.py` | Cross-cutting | Record-filter and predicate contracts. |
| `health_check.py` | Cross-cutting | Health/readiness probe contracts. |
| `idmapping.py` | Cross-cutting | Identifier mapping and cross-reference contracts. |
| `logger_port.py` | Cross-cutting | Structured logging port used outside observability package. |
| `pii.py` | Cross-cutting | PII redaction and audit-safe logging contracts. |
| `protein_classification.py` | Cross-cutting | Protein classification vocabulary contracts. |
| `publication_strategy.py` | Cross-cutting | Publication routing and strategy selection contracts. |
| `resilience.py` | Cross-cutting | Retry/backoff/circuit-breaker policy contracts. |
| `serialization.py` | Cross-cutting | Canonical serialization and codec contracts. |
| `storage_maintenance.py` | Cross-cutting | Storage compaction, vacuum, and maintenance contracts. |
| `workflow_foreign_key_reconciliation.py` | Cross-cutting | Workflow FK reconciliation contracts. |
| `workflow_row_reconciliation.py` | Cross-cutting | Workflow row reconciliation contracts. |
| `config/__init__.py` | Config | Config port package boundary. |
| `config/config_loader_port.py` | Config | Declarative config loading contracts. |
| `config/config_port.py` | Config | Runtime settings and config access contracts. |
| `config/publication_vocabulary_port.py` | Config | Publication vocabulary lookup contracts. |
| `control_plane/__init__.py` | Control plane | Control-plane port package boundary. |
| `control_plane/artifact_byte_comparison.py` | Control plane | Byte-level artifact comparison contracts. |
| `control_plane/effective_config_artifact.py` | Control plane | Effective-config artifact write/read contracts. |
| `control_plane/lineage.py` | Control plane | Lineage graph and provenance contracts. |
| `control_plane/run_ledger.py` | Control plane | Run ledger persistence contracts. |
| `control_plane/run_manifest.py` | Control plane | Run manifest persistence contracts. |
| `control_plane/workflow_execution_state.py` | Control plane | Workflow execution-state contracts. |
| `control_plane/workflow_ledger.py` | Control plane | Workflow ledger persistence contracts. |
| `control_plane/workflow_manifest.py` | Control plane | Workflow manifest persistence contracts. |
| `metadata/__init__.py` | Metadata | Metadata port package boundary. |
| `metadata/coordinator.py` | Metadata | Metadata coordination contracts. |
| `metadata/writer.py` | Metadata | Output metadata writer contracts. |
| `noop/__init__.py` | NoOp | NoOp fallback package boundary. |
| `noop/_async_boundary.py` | NoOp | Async-boundary NoOp fallback. |
| `noop/_audit_pii.py` | NoOp | Audit/PII NoOp fallback. |
| `noop/_debug.py` | NoOp | Debug instrumentation NoOp fallback. |
| `noop/_memory_metadata.py` | NoOp | Memory metadata NoOp fallback. |
| `noop/_metrics.py` | NoOp | Metrics NoOp fallback. |
| `noop/_tracing.py` | NoOp | Tracing NoOp fallback. |
| `observability/__init__.py` | Observability | Observability port package boundary. |
| `observability/dq_monitor.py` | Observability | DQ monitor emission contracts. |
| `observability/logging.py` | Observability | Structured logging contracts. |
| `observability/metrics.py` | Observability | Metrics emission contracts. |
| `observability/tracing.py` | Observability | Distributed tracing contracts. |
| `quality/__init__.py` | Quality | Quality port package boundary. |
| `quality/contract_policy.py` | Quality | Contract-policy enforcement contracts. |
| `quality/dq_config.py` | Quality | DQ configuration projection contracts. |
| `quality/dq_report.py` | Quality | DQ report generation contracts. |
| `quality/error_classifier.py` | Quality | Error classification contracts. |
| `quality/error_handler.py` | Quality | Error handling and escalation contracts. |
| `quality/fallback_policy.py` | Quality | Fallback-policy contracts for degraded DQ paths. |
| `quality/quarantine.py` | Quality | Quarantine persistence and replay contracts. |
| `quality/silver_dq_request.py` | Quality | Silver DQ request defaults and threshold contracts. |
| `quality/validation.py` | Quality | Schema and record validation contracts. |
| `runtime/__init__.py` | Runtime | Runtime port package boundary. |
| `runtime/batch_id.py` | Runtime | Batch identifier generation contracts. |
| `runtime/checkpoint.py` | Runtime | Checkpoint persistence contracts. |
| `runtime/clock.py` | Runtime | Injectable clock/time contracts. |
| `runtime/composite_checkpoint.py` | Runtime | Composite checkpoint contracts. |
| `runtime/locking.py` | Runtime | Distributed/local lock contracts. |
| `runtime/memory.py` | Runtime | Memory budget and pressure contracts. |
| `runtime/pipeline_debug.py` | Runtime | Pipeline debug instrumentation contracts. |
| `runtime/registry_port.py` | Runtime | Pipeline/registry lookup contracts. |
| `runtime/runner.py` | Runtime | Pipeline runner execution contracts. |
| `runtime/shutdown.py` | Runtime | Graceful shutdown coordination contracts. |
| `storage/__init__.py` | Storage | Storage port package boundary. |
| `storage/bronze_port.py` | Storage | Bronze write/read contracts. |
| `storage/gold_port.py` | Storage | Gold write/read contracts. |
| `storage/lifecycle_port.py` | Storage | Storage lifecycle management contracts. |
| `storage/merged_port.py` | Storage | Merged-surface write/read contracts. |
| `storage/silver_port.py` | Storage | Silver write/read contracts. |

## Boundary Notes

- Runtime-oriented ports are allowed in the domain because they remain pure
  contracts without concrete I/O implementations.
- Application-owned aggregate DI protocols may compose multiple domain ports,
  but that does not move the port ownership out of the domain layer.
- Control-plane ports and workflow ports are part of the active supported
  runtime surface and must stay aligned with their published contracts and
  runbooks.

## Related References

- [API Reference: domain ports](../api/domain/ports.md)
- [Invariants](invariants.md)
- [Workflow State Machine](workflow-state-machine.md)
