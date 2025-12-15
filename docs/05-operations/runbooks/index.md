# Operations Runbooks (Playbooks)
*Aligned with RULES.md v5.0, Appendix C*

This section contains playbooks for handling common alerts and operational tasks.

## Incident Response

| Runbook | Description | Priority |
|---|---|---|
| [Incident Response](incident-response.md) | General guide for handling any production alert. | - |
| [Data Recovery](data-recovery.md) | Steps to recover from data corruption or loss (DR). | P0/P1 |
| [Pipeline Failure: Critical Error](pipeline-failure-critical.md) | How to handle non-recoverable pipeline crashes. | P1 |
| [Pipeline Failure: High DQ Rate](pipeline-failure-dq.md) | What to do when a batch fails due to >20% bad records. | P2 |
| [Stale Lock Detected](stale-lock.md) | How to safely release a lock from a crashed pipeline. | P2 |

## Routine Operations

| Runbook | Description |
|---|---|
| [Scaling and Performance Tuning](scaling.md) | Guide for scaling workers and tuning Delta Lake. |
| [Backfill and Rebuild](backfill-rebuild.md) | How to perform historical data loads. |
| [Quarantine Management](quarantine-management.md) | How to inspect, replay, or purge quarantined data. |
| [Schema Evolution](schema-evolution.md) | Procedure for updating Gold data contracts. |

---
*To add a new runbook, create a markdown file and link it here.*
