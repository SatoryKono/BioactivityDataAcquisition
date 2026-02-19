# Operations Documentation

*Synced with RULES.md v5.20 (2026-02-03)*

## Overview

This section contains operational documentation for managing BioETL in production.

## Navigation

| Section | Description |
|---------|-------------|
| [Runbooks](runbooks/index.md) | Operational playbooks for incident response |
| [Performance Baselines](performance-baselines.md) | Expected performance metrics |
| [VACUUM Retention](vacuum-retention.md) | Delta Lake vacuum retention policies |
| [Release Checklist](RELEASE-CHECKLIST.md) | Pre-release verification checklist |

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
- [ADR-008](../02-architecture/decisions/ADR-008-graceful-shutdown-strategy.md) — Graceful shutdown
- [ADR-010](../02-architecture/decisions/ADR-010-local-only-deployment.md) — Local deployment
