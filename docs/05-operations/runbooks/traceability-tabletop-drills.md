______________________________________________________________________

Version: 1.1.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Priority: P2
  Runtime profile: Local-Only single-instance (ADR-010), local filesystem storage, MemoryLock.
  Last verified: '2026-04-02'

______________________________________________________________________

# Traceability Tabletop Drills

## Trigger

- Run this procedure when conducting operator tabletop drills for traceability scenarios.
- Escalate according to the priority declared in metadata when operator ownership is unclear.

## Impact

- Priority: P2.
- Delayed handling can extend service disruption, data correctness risk, or operator response time.

## Preconditions

- `run-manifest` CLI is available.
- Control-plane artifacts are present for the scenario (`manifest` and
- `run_ledger`).
- Incident ticket template contains response contract fields (see
- [Traceability Signal Ownership](traceability-signal-ownership.md)).

## Procedure

### Purpose

- Validate operator adoption for Traceability Fabric by running short tabletop drills. Goal: confirm that on-call engineers can complete the path:

- `alert -> run_id -> manifest -> diagnostics -> artifact/lineage evidence -> decision`

### Role Boundary

- This page defines the recurring drill catalog, cadence, scenario design, and
  scoring model.
- Use [Traceability Adoption Checklist](traceability-adoption-checklist.md) to
  log outcomes and enforce the exit gate.
- Use [Traceability Wave 5 Closeout Pack](traceability-wave5-closeout-pack.md)
  when running the final bundled Wave 5 validation.

### Cadence

- Weekly: one P1 scenario (30-45 minutes)
- Bi-weekly: one P2 scenario (20-30 minutes)
- Monthly: one mixed scenario with handover (45-60 minutes)

### Drill Template

1. Facilitator announces synthetic alert and gives `run_id`.
1. Operator runs:

- `bioetl run-manifest show <run-id> --format json`

3. Operator extracts:

- `manifest_id`, `latest_status`, `latest_event_type`, `event_family_counts`,
  `artifact_refs`, `artifact_refs[*].artifact_id`, `missing_artifact_links`.

4. Operator classifies incident type:

- control-plane, DQ, lineage, checkpoint, or composite degradation.

5. Operator proposes decision:

- retry, quarantine, rollback, monitor, escalate.

6. Facilitator records timing and evidence completeness.

### Scenarios

### Scenario A: Missing Manifest Link

- Injected symptom: `run-manifest show <run-id>` not found.
- Expected operator decision: immediate control-plane escalation.
- Pass criteria: escalation decision in \<= 10 minutes with explicit `run_id`.

### Scenario B: Artifact Linkage Regression

- Injected symptom: `artifact_published` events exist and
- `missing_artifact_links > 0`.
- Expected decision: treat as traceability regression, block blind retry until
- linkage diagnosis is complete.
- Pass criteria: operator references both `artifact_refs` /
  `artifact_refs[*].artifact_id` and
- `missing_artifact_links`.

### Scenario C: DQ-Driven Failure with Good Control Plane

- Injected symptom: `latest_status=failed`, manifest and ledger present.
- Expected decision: DQ owner path with policy outcome (`quarantine` vs fail).
- Pass criteria: operator reports full correlation anchors and chosen disposition.

### Scoring

- Score each drill from 0 to 2 per category:

- Identification speed (time-to-first-diagnosis)

- Evidence completeness (all required anchors captured)

- Correct routing (owner/escalation path)

- Decision quality (safe and policy-consistent)

- Total score:

- 7-8: pass

- 5-6: conditional pass with action items

- \<=4: fail, follow-up coaching required

### Post-Drill Actions

- Record one improvement item per failed/conditional category.
- Update related runbook sections if diagnostic steps were ambiguous.
- Re-run the same scenario within 7 days if score \<= 6.

## Compliance

- This runbook MUST be executed within the priority and runtime profile declared in the YAML header.
- Operators SHOULD preserve evidence, commands, and follow-up actions in the Verification and Post-incident sections.

## Verification

- Confirm the triggering condition is cleared or understood with evidence.
- Verify logs, manifests, datasets, or alerts reflect the expected post-procedure state.

## Rollback

- Revert partial changes made during mitigation, including config overrides, restored checkpoints, or rewritten data, if they worsen the situation.
- Return to the last known good state before attempting an alternate recovery path.

## Post-incident

- Record timeline, commands executed, evidence reviewed, and follow-up owners.
- Update related alerts, dashboards, or runbooks when operator gaps or ambiguous steps are discovered.
