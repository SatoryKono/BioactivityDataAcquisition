______________________________________________________________________

Version: 1.2.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-04-09'

______________________________________________________________________

# Operations Documentation

*Synced with RULES.md v6.1.3 (2026-04-29)*

> Runtime profile: Local-Only single-instance (ADR-010), local filesystem storage, `MemoryLock`.

## Overview

This section contains operational documentation for managing the supported
BioETL runtime, including long-running local and staging-like operator
profiles.

Default operational guidance in this section assumes the supported ADR-010
runtime profile: single-instance, filesystem-backed, Local-Only execution.
Experimental deployment material and auxiliary tooling setup live under
[`deployment/`](deployment/README.md) and are intentionally excluded from the
standard runbook path.

## Navigation

| Section                                               | Description                                                                                     |
| ----------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| [Monitoring Guide](01-monitoring-guide.md)            | Dashboard interpretation, alert-backed signals, and monitoring workflow                         |
| [SLI/SLO Baseline](sli-slo-baseline.md)               | Operational service-level indicators and target baselines for the local runtime                 |
| [Runbooks](runbooks/index.md)                         | Operational playbooks for incident response                                                     |
| [Performance Baselines](performance-baselines.md)     | Expected performance metrics                                                                    |
| [VACUUM Retention](vacuum-retention.md)               | Delta Lake vacuum retention policies                                                            |
| [Control-Plane Lifecycle](control-plane-lifecycle.md) | Dry-run/apply cleanup for manifests, ledgers, checkpoints, lineage, and cached Bronze snapshots |
| [Retention-Sensitive Cleanup](runbooks/retention-sensitive-cleanup.md) | Bounded cleanup gate for protected data, fixtures, reports, archives, and control-plane artifacts |
| [Operations Archive Index](archive-index.md)          | Archive-only operational material, including historical release and verification evidence       |
| [Deployment & Tooling Extras](deployment/README.md)   | Internal / Extended material for experimental Kubernetes and auxiliary Neo4j/MCP setup notes    |

## Quick Links

### Incident Response

- [Pipeline Failure - Critical](runbooks/pipeline-failure-critical.md)
- [Pipeline Failure - DQ](runbooks/pipeline-failure-dq.md)
- [Data Recovery](runbooks/data-recovery.md)

### Maintenance

- [VACUUM Procedures](runbooks/vacuum-procedures.md)
- [Control-Plane Lifecycle](control-plane-lifecycle.md)
- [Retention-Sensitive Cleanup](runbooks/retention-sensitive-cleanup.md)
- [Backfill/Rebuild](runbooks/backfill-rebuild.md)
- [Quarantine Management](runbooks/quarantine-management.md)

### Monitoring

- [Monitoring Guide](01-monitoring-guide.md)
- [SLI/SLO Baseline](sli-slo-baseline.md)
- [Observability Checklist](runbooks/observability-checklist.md)
- [Checkpoint Debugging](runbooks/checkpoint-debugging.md)
- [Run Manifest Inspection](runbooks/run-manifest-inspection.md)

### Extended / Non-Default Material

- [Deployment & Tooling Extras](deployment/README.md) (Internal / Extended)
- [Operations Archive Index](archive-index.md)

## Related Documentation

- [RULES.md](../00-project/RULES.md) §5 — Operations and DR policies
- [ADR-008](../02-architecture/decisions/ADR-008-graceful-shutdown-strategy.md) — Graceful shutdown (**Superseded**, historical context)
- [Pipeline Lifecycle](../03-guides/pipeline-lifecycle.md) — Current lifecycle and shutdown behavior
- [ADR-010](../02-architecture/decisions/ADR-010-local-only-deployment.md) — Local deployment
