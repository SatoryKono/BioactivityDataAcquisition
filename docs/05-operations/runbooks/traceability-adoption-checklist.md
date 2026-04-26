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

# Traceability Adoption Checklist

## Trigger

- Run this checklist when validating operator adoption and readiness for Traceability Fabric workflows.
- Escalate according to the priority declared in metadata when operator ownership is unclear.

## Impact

- Priority: P2.
- Delayed handling can extend service disruption, data correctness risk, or operator response time.

## Preconditions

- Runtime profile: Local-Only single-instance (ADR-010), local filesystem storage, MemoryLock.
- Required access: repository checkout, local shell, logs, configuration, and relevant data/control-plane artifacts.

## Procedure

### Purpose

- Capture objective operator-adoption evidence for Wave 4 Traceability Fabric and the final manual release-readiness gate referenced by Wave 5. This checklist is executed after tabletop drills and incident simulations.

### Role Boundary

- This page is the evidence and exit-gate checklist.
- Use [Traceability Tabletop Drills](traceability-tabletop-drills.md) for the
  recurring scenarios and scoring method.
- Use [Traceability Wave 5 Closeout Pack](traceability-wave5-closeout-pack.md)
  for the canonical bundled closeout flow.
- Use [Traceability Signal Ownership](traceability-signal-ownership.md) when an
  operator needs the owner or escalation route for a detected signal.

### Wave 5 Closeout Expectation

- Before declaring the operator gate passed:

- record at least 3 recent sessions covering scenarios A/B/C from

- [Traceability Tabletop Drills](traceability-tabletop-drills.md);

- use the canonical execution flow from

- [Traceability Wave 5 Closeout Pack](traceability-wave5-closeout-pack.md);

- achieve average score `>= 7`;

- ensure no failed session remains without follow-up within 7 days;

- attach the resulting outcome to the Wave 5 release decision.

### Readiness Checklist

- Mark all items before declaring operator adoption complete:

- [ ] On-call can resolve `run_id -> manifest_id` using `run-manifest show`.

- [ ] On-call can explain `diagnostics.latest_status` and `latest_event_type`.

- [ ] On-call can interpret `event_family_counts` without escalation.

- [ ] On-call can identify artifact linkage gaps from `missing_artifact_links`.

- [ ] On-call can route incident by `alert_signals` to the correct owner.

- [ ] On-call can justify decision using `next_steps` + runbook policy.

- [ ] Escalation path is executed within target SLA for P1 scenarios.

- [ ] Drill evidence is recorded in the session log below.

### Session Log

| Date       | Scenario                                         | Operator | Time to first diagnosis | Time to decision | Score (0-8) | Outcome                   | Notes   |
| ---------- | ------------------------------------------------ | -------- | ----------------------: | ---------------: | ----------: | ------------------------- | ------- |
| YYYY-MM-DD | Missing Manifest / Artifact Linkage / DQ Failure | name     |                      Xm |               Ym |           N | pass / conditional / fail | summary |

### Exit Gate

- Wave 4 / Wave 5 operator adoption gate is considered passed when:

- at least 3 recent sessions are recorded;

- average score is >= 7;

- no failed session remains without a follow-up session in 7 days.

### Related Runbooks

- [Traceability Tabletop Drills](traceability-tabletop-drills.md)
- [Traceability Wave 5 Closeout Pack](traceability-wave5-closeout-pack.md)
- [Traceability Signal Ownership](traceability-signal-ownership.md)
- [Run Manifest Inspection](run-manifest-inspection.md)

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
