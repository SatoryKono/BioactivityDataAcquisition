______________________________________________________________________

Version: 1.1.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Priority: P1
  Runtime profile: Local-Only single-instance (ADR-010), local filesystem storage, MemoryLock.
  Last verified: '2026-05-26'

______________________________________________________________________

# DQ Failure Investigation Runbook (Duplicate Notice)

> This page is retained as a compatibility pointer.
>
> **Canonical runbook:** [Pipeline Failure: High DQ Rate (P1)](pipeline-failure-dq.md)

Use the canonical page for all current operator procedures, thresholds, and
recovery steps.

## Trigger

Use this compatibility page only when an older link points to
`dq-failure-investigation.md`. Active DQ failure triage starts at
[Pipeline Failure: High DQ Rate (P1)](pipeline-failure-dq.md).

## Impact

No independent procedure is defined here. Following this page as a standalone
runbook risks missing the current DQ thresholds, quarantine commands, and
verification steps from the canonical P1 runbook.

## Preconditions

- Local-Only runtime profile from ADR-010.
- Access to the canonical DQ failure runbook:
  [pipeline-failure-dq.md](pipeline-failure-dq.md).

## Procedure

1. Open [Pipeline Failure: High DQ Rate (P1)](pipeline-failure-dq.md).
1. Follow the canonical trigger, impact, precondition, triage, recovery, and
   verification sections from that page.
1. Do not duplicate or fork DQ recovery steps in this compatibility pointer.

## Verification

Verification is complete when the canonical DQ runbook has been followed and
the operator has recorded the outcome in the relevant incident or run notes.

## Rollback/Recovery

Recovery is delegated to [pipeline-failure-dq.md](pipeline-failure-dq.md).
This page has no separate rollback path.

## Post-incident

If an incident or issue still links here, update the reference to the canonical
runbook after the incident is closed.

## Compliance

This duplicate pointer is compliant only when it remains a thin redirect and
does not define independent DQ recovery behavior.
