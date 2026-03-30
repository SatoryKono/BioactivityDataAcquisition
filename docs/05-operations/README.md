---
Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:
- BioETL Team
Last verified: '2026-03-29'
---

# Operations Documentation

*Synced with RULES.md v5.24 (2026-03-13)*

> Runtime profile: Local-Only single-instance (ADR-010), local filesystem storage, `MemoryLock`.

## Overview

This section contains operational documentation for managing BioETL in production.

Default operational guidance in this section assumes the supported ADR-010
runtime profile: single-instance, filesystem-backed, Local-Only execution.
Experimental deployment material and auxiliary tooling setup live under
[`deployment/`](deployment/README.md) and are intentionally excluded from the
standard runbook path.

## Navigation

| Section | Description |
|---------|-------------|
| [Runbooks](runbooks/index.md) | Operational playbooks for incident response |
| [Performance Baselines](performance-baselines.md) | Expected performance metrics |
| [VACUUM Retention](vacuum-retention.md) | Delta Lake vacuum retention policies |
| [Historical Release Checklist (v5.9)](release-checklist.md) | Historical example only; not the current release procedure |
| [Deployment & Tooling Extras](deployment/README.md) | Internal / Extended material for experimental Kubernetes and auxiliary Neo4j/MCP setup notes |
| [VCR Provider Rebalancing](verification/vcr-provider-rebalancing.md) | Recording and validation workflow for provider cassette balance |

## Quick Links

### Incident Response

- [Pipeline Failure - Critical](runbooks/pipeline-failure-critical.md)
- [Pipeline Failure - DQ](runbooks/pipeline-failure-dq.md)
- [Data Recovery](runbooks/data-recovery.md)

### Maintenance

- [VACUUM Procedures](runbooks/vacuum-procedures.md)
- [Backfill/Rebuild](runbooks/backfill-rebuild.md)
- [Quarantine Management](runbooks/quarantine-management.md)

### Monitoring

- [Observability Checklist](runbooks/observability-checklist.md)
- [Checkpoint Debugging](runbooks/checkpoint-debugging.md)
- [Run Manifest Inspection](runbooks/run-manifest-inspection.md)

### Extended / Non-Default Material

- [Deployment & Tooling Extras](deployment/README.md) (Internal / Extended)

## Related Documentation

- [RULES.md](../00-project/RULES.md) §5 — Operations and DR policies
- [ADR-008](../02-architecture/decisions/ADR-008-graceful-shutdown-strategy.md) — Graceful shutdown (**Superseded**, historical context)
- [Pipeline Lifecycle](../03-guides/pipeline-lifecycle.md) — Current lifecycle and shutdown behavior
- [ADR-010](../02-architecture/decisions/ADR-010-local-only-deployment.md) — Local deployment
