# Operations Documentation

*Synced with RULES.md v5.24 (2026-02-24)*

> Runtime profile: Local-Only single-instance (ADR-010), local filesystem storage, `MemoryLock`.

## Overview

This section contains operational documentation for managing BioETL in production.

## Navigation

| Section | Description |
|---------|-------------|
| [Runbooks](runbooks/index.md) | Operational playbooks for incident response |
| [Performance Baselines](performance-baselines.md) | Expected performance metrics |
| [VACUUM Retention](vacuum-retention.md) | Delta Lake vacuum retention policies |
| [Release Checklist](release-checklist.md) | Pre-release verification checklist |
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

## Related Documentation

- [RULES.md](../00-project/RULES.md) §5 — Operations and DR policies
- [ADR-008](../02-architecture/decisions/ADR-008-graceful-shutdown-strategy.md) — Graceful shutdown (**Superseded**, historical context)
- [Pipeline Lifecycle](../03-guides/pipeline-lifecycle.md) — Current lifecycle and shutdown behavior
- [ADR-010](../02-architecture/decisions/ADR-010-local-only-deployment.md) — Local deployment
