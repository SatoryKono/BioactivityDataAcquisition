# Operations Runbooks (Playbooks)
*Synced with RULES.md v5.24 (2026-03-13)*

This section contains playbooks for handling common alerts and operational tasks.

> Runtime profile for all runbooks: Local-Only single-instance (ADR-010), local filesystem storage, `MemoryLock`.

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
| [Scaling and Performance Tuning](scaling.md) | Local-only performance tuning (vertical scaling + Delta maintenance) | P3 |

### Monitoring
| Runbook | Description | Priority |
|---------|-------------|----------|
| [Observability Checklist](observability-checklist.md) | Metrics, logging, and alerting verification | - |
| [Run Manifest Inspection](run-manifest-inspection.md) | Inspect run control-plane provenance, config, and ledger history | P1 |
| [Traceability Signal Ownership](traceability-signal-ownership.md) | Signal ownership matrix for alert -> diagnostics -> escalation | P1 |
| [Traceability Tabletop Drills](traceability-tabletop-drills.md) | Tabletop scenarios and scoring for operator adoption | P2 |
| [Traceability Adoption Checklist](traceability-adoption-checklist.md) | Exit-gate checklist and session evidence log for operator adoption | P2 |

---

## See Also
- [RULES.md](../../00-project/RULES.md) - Project rules and governance
- [ADR-008: Graceful Shutdown](../../02-architecture/decisions/ADR-008-graceful-shutdown-strategy.md)

---
*Last updated: 2026-03-25*
