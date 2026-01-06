# Operations Runbooks (Playbooks)
*Synced with RULES.md v5.10 (2026-01-04)*

This section contains playbooks for handling common alerts and operational tasks.

## Available Runbooks

### Incident Response
| Runbook | Description | Priority |
|---------|-------------|----------|
| [Incident Response](incident-response.md) | General guide for handling any production alert | - |
| [Pipeline Failure - Critical](pipeline-failure-critical.md) | Critical pipeline failure handling | P0 |
| [Pipeline Failure - DQ](pipeline-failure-dq.md) | Data Quality failure handling | P1 |
| [Pipeline Failure Recovery](pipeline-failure-recovery.md) | General pipeline recovery procedures | P1 |

### Data Management
| Runbook | Description | Priority |
|---------|-------------|----------|
| [Data Recovery](data-recovery.md) | Steps to recover from data corruption or loss (DR) | P0/P1 |
| [Quarantine Management](quarantine-management.md) | Managing quarantined records | P2 |
| [DQ Failure Investigation](dq-failure-investigation.md) | Investigating data quality failures | P1 |
| [Backfill/Rebuild](backfill-rebuild.md) | Data backfill and rebuild procedures | P2 |
| [Schema Evolution](schema-evolution.md) | Handling schema changes | P2 |

### Infrastructure
| Runbook | Description | Priority |
|---------|-------------|----------|
| [Checkpoint Debugging](checkpoint-debugging.md) | Debugging checkpoint issues | P2 |
| [Stale Lock](stale-lock.md) | Handling stale lock situations | P1 |
| [Vacuum Procedures](vacuum-procedures.md) | Delta Lake vacuum maintenance | P2 |
| [Scaling and Performance Tuning](scaling.md) | Guide for scaling workers and tuning Delta Lake | P3 |

### Monitoring
| Runbook | Description | Priority |
|---------|-------------|----------|
| [Observability Checklist](observability-checklist.md) | Metrics, logging, and alerting verification | - |

---

## See Also
- [README](README.md) - Overview and quick links
- [RULES.md](../../RULES.md) - Project rules and governance
- [ADR-008: Graceful Shutdown](../../02-architecture/decisions/ADR-008-graceful-shutdown-strategy.md)

---
*Last updated: 2026-01-04*
