______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-06-15'

______________________________________________________________________

# Domain Ports

## Purpose

`src/bioetl/domain/ports/` is the transport-neutral contract boundary for the
Ports & Adapters architecture in BioETL.

This page is the semantic catalog of port families. For module-by-module API
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
